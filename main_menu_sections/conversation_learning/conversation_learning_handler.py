import json
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler,
)

from AIModels.chatgpt import get_chatgpt_instance
from handlers.main_menu_handler import main_menu_handler
from utils.question_management import (
    get_random_question,
)
from utils.subscription_management import check_subscription
from utils.user_management import get_user_name


# Conversation states
ASK_QUESTION, PROVIDE_FEEDBACK, REVIEW_QUESTION, ASK_ABOUT_ANSWER = range(4)

chatgpt = get_chatgpt_instance()


async def handle_conversation_learning(update: Update, context: CallbackContext):

    if not await check_subscription(update, context):
        return
    context.user_data["current_section"] = "conversation_learning"
    keyboard = [
        [InlineKeyboardButton("ابدأ المحادثة 🗣️", callback_data="handle_conversation")],
        [InlineKeyboardButton("طرح الأسئلة ❔", callback_data="handle_ask_questions")],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    await update.callback_query.edit_message_text(
        "التعلم عبر المحادثة 📚", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def ask_question(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    context.user_data["messages"] = []

    question_data = get_random_question()

    if not question_data:
        await update.callback_query.edit_message_text("لا توجد أسئلة متاحة حاليًا 😞.")
        return ConversationHandler.END
    await query.message.reply_text("حسنا هذا سؤال لك كيف تعتقد سيكون حله 🤔")

    context.user_data["current_question"] = question_data
    formatted_question = f"""
{question_data['question_text']}\n
أ: {question_data['option_a']}
ب: {question_data['option_b']}
ج: {question_data['option_c']}
د: {question_data['option_d']}"""

    await query.edit_message_text(formatted_question)
    return PROVIDE_FEEDBACK


async def provide_feedback(update: Update, context: CallbackContext):
    user_answer = update.message.text.strip()
    question_data = context.user_data["current_question"]

    SYSTEM_MESSAGE = """
You are a helpful and engaging personal assistant for a Telegram bot designed for learning through conversation in Arabic.  You present questions, handle user responses, and provide hints or explanations.  

When the user answers correctly, simply respond with congratulation message that he answer correctly. If they answer incorrectly, guide them towards the correct answer with helpful hints and explanations, but *do not* give away the answer directly unless they specifically ask for it. Keep the conversation fun and light, encouraging the user to learn.

Output your responses as a JSON object with the following structure:

{
  "text": "The Arabic text of your response to the user.",
  "correct": true or false, // Whether the user's answer was correct
  "hint": "A hint if the answer is incorrect (optional)"
}

And also remember don't add "```json" at your response
"""

    chatgpt_prompt = (
        f"The user answered '{user_answer}' to the following question:\n"
        f"Question: {question_data['question_text']}\n"
        f"A: {question_data['option_a']}\n"
        f"B: {question_data['option_b']}\n"
        f"C: {question_data['option_c']}\n"
        f"D: {question_data['option_d']}\n"
        f"The correct answer is '{question_data['correct_answer']}' and make it as reference to let the correct state to be True.\n"
        f"the following explanation from the question's context:\n"
        f"{question_data['explanation']}\n\n"
        f"and also make the conversation fun and engage with the user and don't let the user know of the prompt, have a normal conversation"
        f"And remember *do not* give away the answer directly unless they specifically ask for it and switch the state for the correct to True."
    )
    message = await update.message.reply_text("جارٍ التفكير في رد... 🤔")

    assistant_response = await chatgpt.chat_with_assistant(
        update.effective_user.id,
        user_message=chatgpt_prompt,
        update=update,
        context=context,
        system_message=SYSTEM_MESSAGE,
        save_history=False,
        return_as_text=True,
    )

    if assistant_response == -1:
        return ConversationHandler.END

    try:
        response_data = json.loads(assistant_response)

        await message.edit_text(response_data["text"])

        if response_data["correct"]:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "اسأل عن الإجابة ❔", callback_data="ask_about_answer"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "السؤال التالي ➡️", callback_data="next_question"
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "هل لديك أي استفسارات لتسأل عنها؟ 🙋‍♂️", reply_markup=reply_markup
            )

            # Set state to REVIEW_QUESTION to handle button clicks
            return REVIEW_QUESTION

        else:  # Incorrect answer
            if "hint" in response_data:
                await update.message.reply_text(response_data["hint"])
            return PROVIDE_FEEDBACK  # Stay in this state for further attempts
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing JSON response or missing key: {e}")
        await update.message.reply_text(
            "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقًا 😞."
        )
        return ConversationHandler.END  # Or handle the error more gracefully


async def ask_about_answer(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("ما هو سؤالك حول الإجابة؟")
    return ASK_ABOUT_ANSWER  # New state for asking about the answer


async def handle_ask_about_answer(update: Update, context: CallbackContext):
    user_question = update.message.text
    question_data = context.user_data["current_question"]

    chatgpt_prompt = (
        f"User question about the answer: {user_question}\n\n"
        f"About the previous question: \"{question_data['question_text']}\"\n"
        f"The correct answer was: \"{question_data['correct_answer']}\"\n"
        f"Option A: \"{question_data['option_a']}\"\n"
        f"Option B: \"{question_data['option_b']}\"\n"
        f"Option C: \"{question_data['option_c']}\"\n"
        f"Option D: \"{question_data['option_d']}\"\n"
        f"Please provide a helpful and detailed response to the user's question, focusing on the context of the previous question and its answer. "
    )

    assistant_response = await chatgpt.chat_with_assistant(
        update.effective_user.id,
        user_message=chatgpt_prompt,
        update=update,
        context=context,
        save_history=False,
        return_as_text=True,
    )

    if assistant_response == -1:
        return ConversationHandler.END

    message = await update.message.reply_text("جارٍ التفكير في رد... 🤔")

    try:
        response_data = json.loads(assistant_response)
        await message.edit_text(response_data["text"])

        keyboard = [
            [InlineKeyboardButton("اسأل المزيد 🔄", callback_data="ask_about_answer")],
            [InlineKeyboardButton("السؤال التالي ➡️", callback_data="next_question")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "اختر أحد الخيارات أدناه:", reply_markup=reply_markup
        )  # Giving option to the user to ask more or go to next question

        return REVIEW_QUESTION  # Return to REVIEW_QUESTION to handle button clicks

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing JSON response or missing key: {e}")
        await update.message.reply_text(
            "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقًا 😞."
        )
        return ConversationHandler.END  # Or handle the error more gracefully


async def next_question(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    question_data = get_random_question()

    if not question_data:
        await update.callback_query.edit_message_text("لا توجد أسئلة متاحة حاليًا 😞.")
        return ConversationHandler.END

    context.user_data["current_question"] = question_data
    formatted_question = f"""
{question_data['question_text']}\n
أ: {question_data['option_a']}
ب: {question_data['option_b']}
ج: {question_data['option_c']}
د: {question_data['option_d']}"""

    keyboard = [
        [InlineKeyboardButton("إنهاء المحادثة 🔚", callback_data="end_chat")]
    ]  # End conversation button
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        formatted_question, reply_markup=reply_markup
    )  # Add the markup here
    return PROVIDE_FEEDBACK


async def handle_ask_questions(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    user_name = get_user_name(user_id)
    await query.edit_message_text(
        f"مرحبا {user_name}! اسألني أي شيء تريده عن تعلم المحادثة 💬."
    )

    messages = await chatgpt.get_chat_history(user_id)
    context.user_data["messages"] = messages

    return ASK_QUESTION


async def ask_question_chatgpt(update: Update, context: CallbackContext):
    user_question = update.message.text

    SYSTEM_MESSAGE = """
    You are a helpful personal assistant for a Telegram bot. You have access to user statistics, 
    frequently asked questions, and various documents. Your role is to assist users, provide advice, 
    and answer questions about the bot and associated tests. Be proactive, ask clarifying questions 
    when needed, and always strive to provide accurate and helpful information.
    """

    try:
        assistant_response = await chatgpt.chat_with_assistant(
            update.effective_user.id,
            user_question,
            update,
            context,
            system_message=SYSTEM_MESSAGE,
            save_history=False,
        )

        if assistant_response == -1:
            return ConversationHandler.END

        if assistant_response:
            await update.message.reply_text(assistant_response)
        else:
            await update.message.reply_text(
                "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقًا 😞"
            )
    except Exception as e:
        await update.message.reply_text(
            "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقًا 😞."
        )
        print(f"Error in ask_question_chatgpt: {e}")
    return ASK_QUESTION


async def cancel_learning_converstation(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:  # Check if the call came from a callback query
        await query.answer()

    await update.callback_query.edit_message_text(  # Edit the message to remove the question
        "تم إلغاء التعلم. إذا كنت بحاجة إلى أي شيء آخر، فأعلمني! 👋"
        "اليك القائمة الرئيسية 🏡"
    )
    await main_menu_handler(query, context)

    return ConversationHandler.END


async def cancel_learning(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "تم إلغاء التعلم. إذا كنت بحاجة إلى أي شيء آخر، فأعلمني! 👋"
    )
    return ConversationHandler.END


conversation_learning_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(ask_question, pattern="^handle_conversation$"),
        CallbackQueryHandler(handle_ask_questions, pattern="^handle_ask_questions$"),
    ],
    states={
        ASK_QUESTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_question_chatgpt),
        ],
        PROVIDE_FEEDBACK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, provide_feedback)
        ],
        REVIEW_QUESTION: [
            CallbackQueryHandler(next_question, pattern="^next_question$"),
            CallbackQueryHandler(ask_about_answer, pattern="^ask_about_answer$"),
        ],
        ASK_ABOUT_ANSWER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ask_about_answer)
        ],
    },
    fallbacks=[
        CommandHandler("end_chat", cancel_learning),
        CallbackQueryHandler(cancel_learning_converstation, pattern="^end_chat$"),
    ],
)

CONVERSATION_LEARNING_HANDLERS = {
    "conversation_learning": handle_conversation_learning,
}
