import asyncio
from datetime import datetime
import json
import os
from typing import List, Dict, Optional
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from openai import OpenAI
from AIModels.tts import generate_tts
from config import OPENAI_API_KEY
from utils.database import execute_query, get_data
from utils.user_management import get_user_setting

client = OpenAI(api_key=OPENAI_API_KEY)

# Constants for subscription tiers (Example - adapt as needed)
FREE_TIER_LIMIT = 10
PAID_TIER_LIMIT = 20


class ChatGPT:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    async def chat_with_assistant(
        self,
        user_id: int,
        user_message: str = "",
        update: Update = None,
        context: CallbackContext = None,
        system_message: str = "",
        save_history: bool = True,
        use_response_mode: bool = True,
        return_as_text: bool = False,
        **kwargs,  # Additional parameters for generate_response
    ) -> Optional[str]:
        """
        Handle chatting with the assistant.

        Args:
            user_id (int): The ID of the user.
            user_message (str): The user's message.
            update (Update, optional): The Telegram Update. Default is None.
            context (CallbackContext, optional): The Telegram CallbackContext. Default is None.
            system_message (str, optional): An optional system message to set the assistant's behavior. Default is "".
            save_history (bool, optional): Whether to save the chat history to the database. Default is True.
            use_response_mode (bool, optional): The desired response mode ("text" or "voice"). Default is True.
            return_as_text (bool, optional): Whether to return the response as text. Default is False.
            **kwargs: Additional keyword arguments to pass to the OpenAI API.

        Returns:
            Optional[str]: The assistant's response (text or audio file path), or None if an error occurred.
        """
        if not return_as_text:
            if not await self.check_usage_limit(user_id):
                await update.message.reply_text(
                    f"لقد وصلت إلى الحد اليومي لاستخدام ChatGPT. انتظر للغد حتى تتجدد استخدامك اليومي. حيث عدد المحدود اليومي حاليا هو {FREE_TIER_LIMIT}"
                )
                return ConversationHandler.END  # Or an appropriate state

        messages = []
        if context:
            messages = context.user_data.get("messages", [])
        if not messages and system_message:
            messages = [{"role": "system", "content": system_message}]
        if user_message:
            messages.append({"role": "user", "content": user_message})

        try:
            message = None
            if not return_as_text:
                message = await update.message.reply_text("جارٍ التفكير في رد... 🤔")

            assistant_response = await self.generate_response(messages, **kwargs)

            if return_as_text:
                return assistant_response

            messages.append({"role": "assistant", "content": assistant_response})

            if save_history:
                await self.save_chat_history(user_id, messages)
            context.user_data["messages"] = messages

            if use_response_mode:
                response_mode = await get_user_setting(user_id, "voice_written")
            else:
                response_mode = "written"

            if response_mode == "voice":
                await _voice_response_processor(assistant_response, message)
            else:
                await _written_response_processor(assistant_response, message)

            await self.increment_usage(
                user_id
            )  # Increment usage AFTER successful response

            return True
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None

    async def generate_response(self, messages, **kwargs) -> str:
        try:
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=self.model,
                messages=messages,
                **kwargs,
            )
            assistant_response = completion.choices[0].message.content
            return assistant_response
        except Exception as e:
            error_message = str(e).lower()
            if "connection" in error_message or "timeout" in error_message:
                print("Connection error encountered. Raising exception...")
                return None
            else:
                print(f"Error calling generate_response: {e}")
                return None

    async def check_usage_limit(self, user_id: int) -> bool:
        """Checks if the user has reached their daily ChatGPT usage limit."""
        today = datetime.now().date()
        usage_data = get_data(
            "SELECT usage_count, last_used FROM chatgpt_usage WHERE user_id = ?",
            (user_id,),
        )

        if usage_data:
            usage_count, last_used_str = usage_data[0]
            last_used = datetime.strptime(last_used_str, "%Y-%m-%d").date()
            if last_used == today:
                # limit = (
                #     PAID_TIER_LIMIT
                #     if await self.is_subscribed(user_id)
                #     else FREE_TIER_LIMIT
                # )  # Check subscription status
                limit = FREE_TIER_LIMIT
                return usage_count < limit
            else:  # Reset count if it's a new day
                await self.reset_daily_usage(user_id)
                return True  # Allow usage as it's reset
        else:  # No usage data yet, create new entry and allow
            execute_query(
                "INSERT INTO chatgpt_usage (user_id, usage_count, last_used) VALUES (?, ?, ?)",
                (user_id, 0, today.strftime("%Y-%m-%d")),
            )
            return True

    async def increment_usage(self, user_id: int):
        """Increments the user's ChatGPT usage count."""
        today = datetime.now().date()
        execute_query(
            "UPDATE chatgpt_usage SET usage_count = usage_count + 1, last_used = ? WHERE user_id = ?",
            (today.strftime("%Y-%m-%d"), user_id),
        )

    async def reset_daily_usage(self, user_id: int):
        """Resets the user's daily usage count."""
        today = datetime.now().date()
        execute_query(
            "UPDATE chatgpt_usage SET usage_count = 0, last_used = ? WHERE user_id = ?",
            (today.strftime("%Y-%m-%d"), user_id),
        )

    async def is_subscribed(self, user_id: int) -> bool:
        """Checks if the user has an active subscription."""
        subscription_end_time_str = await get_user_setting(
            user_id, "subscription_end_time"
        )
        if subscription_end_time_str:
            subscription_end_time = datetime.strptime(
                subscription_end_time_str, "%Y-%m-%d %H:%M:%S.%f"
            )
            return subscription_end_time > datetime.now()
        return False

    @staticmethod
    async def get_chat_history(
        user_id: int,
    ) -> List[Dict[str, str]]:  # Make this asynchronous
        result = await asyncio.to_thread(
            get_data,  # Run database query in a separate thread
            "SELECT messages FROM chat_history WHERE user_id = ?",
            (user_id,),
        )
        return json.loads(result[0][0]) if result else []

    @staticmethod
    async def save_chat_history(
        user_id: int, messages: List[Dict[str, str]]
    ) -> None:  # Make this asynchronous
        existing_history = await ChatGPT.get_chat_history(user_id)
        if existing_history:
            # Update existing chat history
            await asyncio.to_thread(
                execute_query,  # Run database query in a separate thread
                "UPDATE chat_history SET messages = ? WHERE user_id = ?",
                (json.dumps(messages), user_id),
            )
        else:
            # Insert new chat history if it doesn't exist
            await asyncio.to_thread(
                execute_query,  # Run database query in a separate thread
                "INSERT INTO chat_history (user_id, messages) VALUES (?, ?)",
                (user_id, json.dumps(messages)),
            )

    @staticmethod
    async def clear_user_history(user_id: int) -> None:  # Make this asynchronous
        """Clears the chat history for a specific user."""
        await asyncio.to_thread(
            execute_query,  # Run database query in a separate thread
            "DELETE FROM chat_history WHERE user_id = ?",
            (user_id,),
        )


def get_chatgpt_instance(model: Optional[str] = None) -> ChatGPT:
    return ChatGPT(model) if model else ChatGPT()


async def _written_response_processor(response: str, message: Update):
    """Sends the response as a text message."""
    await message.edit_text(response)


async def _voice_response_processor(response: str, message: Update):
    """Sends the response as a voice message."""
    audio_file_path = await generate_tts(response)
    await message.reply_voice(voice=open(audio_file_path, "rb"))
    os.remove(audio_file_path)
