import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

from openai import OpenAI
from config import DESIGNS_POWER_POINT_FILES, OPENAI_API_KEY
from main_menu_sections.design_for_you.helper_functions import (
    check_user_ai_limit,
    download_image,
    load_design_options,
    process_powerpoint_design,
    update_user_ai_usage,
)
from handlers.main_menu_handler import (
    main_menu_handler,
)

from utils.subscription_management import check_subscription


# States for ConversationHandler
AI_PROMPT = 0

# OpenAI client initialization
client = OpenAI(api_key=OPENAI_API_KEY)

# Enable logging
logger = logging.getLogger(__name__)


async def start_design(update: Update, context: CallbackContext):
    """Starts the design process."""

    if not await check_subscription(update, context):
        return
    keyboard = [
        [
            InlineKeyboardButton("أنثى 🚺", callback_data="female"),
            InlineKeyboardButton("ذكر 🚹", callback_data="male"),
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "من فضلك، اختر جنسك: 😊", reply_markup=reply_markup
    )


async def gender_selection(update: Update, context: CallbackContext):
    """Handles gender selection and asks for design type."""
    query = update.callback_query
    await query.answer()
    callback_data = query.data

    context.user_data["gender"] = callback_data

    keyboard = [
        [InlineKeyboardButton("استخدام تصاميم جاهزة 🗂️", callback_data="ready_made")],
        [
            InlineKeyboardButton(
                "إنشاء تصميم مخصص باستخدام الذكاء الاصطناعي 🤖",
                callback_data="ai_custom",
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="design_for_you")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "اختر نوع التصميم الذي تريده: 👇", reply_markup=reply_markup
    )


async def design_type_selection(update: Update, context):
    """Handles design type selection."""
    query = update.callback_query
    await query.answer()
    design_type = query.data

    if design_type == "ready_made":
        await query.edit_message_text("جاري تحميل خيارات التصميم... ⏳")
        designs = load_design_options(context.user_data["gender"])
        context.user_data["designs"] = designs
        await display_design_options(update, context, 0)
    else:
        await query.edit_message_text(
            "بلا أمر عليكم، اكتبوا لي وصف التصميم الذي تريدونه ✍️:"
        )
        return AI_PROMPT


async def display_design_options(update: Update, context, start_index: int):
    """Displays design options to the user."""
    designs = context.user_data["designs"]
    keyboard = []
    for i in range(start_index, min(start_index + 5, len(designs))):
        keyboard.append(
            [InlineKeyboardButton(designs[i][0], callback_data=f"design_{i}")]
        )

    nav_buttons = []
    if start_index + 5 < len(designs):
        nav_buttons.append(
            InlineKeyboardButton("التالي 👉", callback_data=f"next_{start_index + 5}")
        )
    if start_index > 0:
        nav_buttons.append(
            InlineKeyboardButton("السابق 👈", callback_data=f"prev_{start_index - 5}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "اختر التصميم الذي تريده: 👍", reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "اختر التصميم الذي تريده: 👍", reply_markup=reply_markup
        )


async def handle_design_selection(update: Update, context):
    """Processes the selected design."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("next_") or query.data.startswith("prev_"):
        start_index = int(query.data.split("_")[1])
        await display_design_options(update, context, start_index)
    else:
        design_index = int(query.data.split("_")[1])
        selected_design = context.user_data["designs"][design_index]
        design_path = os.path.join(DESIGNS_POWER_POINT_FILES, selected_design[1])

        try:
            await query.edit_message_text("جاري معالجة التصميم... ⚙️")
            image_path = await process_powerpoint_design( design_path, update.effective_user.first_name, )

            with open(image_path, "rb") as image_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id, photo=image_file
                )

            os.remove(image_path)

            # Add inline keyboard for continue/cancel option
            keyboard = [
                [InlineKeyboardButton("نعم 👍", callback_data="yes_continue_design")],
                [InlineKeyboardButton("لا 👎", callback_data="no_continue_design")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "إليك تصميمك! 🎉 هل ترغب في إنشاء تصميم آخر؟", reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error processing design: {e}")
            await query.edit_message_text(
                "عذراً، حدث خطأ أثناء معالجة التصميم. يرجى المحاولة مرة أخرى. 😔"
            )


async def handle_continue_design_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "yes_continue_design":
        await query.edit_message_text(
            "اختر نوع التصميم الذي تريده:"
        )  # Redirect to design type selection
        await gender_selection(
            update, context
        )  # Call gender_selection again to choose gender and design type
    elif query.data == "no_continue_design":
        await query.edit_message_text("شكراً لكم! 😊")
        await main_menu_handler(update, context)  # Go back to the main menu


async def handle_ai_prompt(update: Update, context):
    """Handles AI-generated design based on user prompt."""
    prompt = update.message.text

    user_id = update.effective_user.id
    is_allowed, usage_count, images_left, is_not_subscribed = await check_user_ai_limit(
        user_id
    )

    if not is_allowed:
        message = (
            "قم بالاشتراك ليزداد عدد الصور التي يمكن انشاءها 😉"
            if is_not_subscribed
            else ""
        )
        await update.message.reply_text(
            f"لقد وصلت إلى الحد الأقصى اليومي لتصاميم الذكاء الاصطناعي. وقد انشأت {usage_count} صورة اليوم. 🚫\n"
            f"{message}"
        )
        return ConversationHandler.END

    try:
        message = await update.message.reply_text(
            "جاري إنشاء تصميمك باستخدام الذكاء الاصطناعي...  ⏳"
        )

        response = await asyncio.to_thread(
            client.images.generate,
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url

        await message.edit_text("جاري تحميل الصورة... ⬇️")

        image_path = await download_image(image_url)
        with open(image_path, "rb") as image_file:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=image_file
            )

        # os.remove(image_path)

        await update_user_ai_usage(user_id)

        keyboard = [
            [
                InlineKeyboardButton("نعم 👍", callback_data="yes_continue"),
                InlineKeyboardButton("لا 👎", callback_data="no_continue"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"تفضلوا تصميمكم، ودكم بتصميم ثاني؟ و تقبى لديكم {images_left} عدد من المحاولات للتصميم 😊",
            reply_markup=reply_markup,
        )

        return AI_PROMPT
    except Exception as e:
        logger.error(f"Error generating AI image: {e}")
        await update.message.reply_text(
            "عذراً، حدث خطأ أثناء إنشاء التصميم. يرجى المحاولة مرة أخرى لاحقًا. 😞"
        )

    return ConversationHandler.END


async def handle_continue_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "yes_continue":
        await query.edit_message_text(
            "بلا أمر عليكم، اكتبوا لي وصف التصميم الذي تريدونه ✍️:"
        )
        return AI_PROMPT
    elif query.data == "no_continue":
        await query.edit_message_text("شكراً لكم! 😊")
        await main_menu_handler(update, context)
        return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("تم إلغاء عملية التصميم. 😔")
    return ConversationHandler.END


design_for_you_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(design_type_selection, pattern="^ai_custom$")],
    states={
        AI_PROMPT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_prompt),
            CallbackQueryHandler(
                handle_continue_choice, pattern="^(yes_continue|no_continue)$"
            ),
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


def register_design_handlers(application: Application):
    application.add_handler(
        CallbackQueryHandler(start_design, pattern="^design_for_you$")
    )
    application.add_handler(
        CallbackQueryHandler(gender_selection, pattern="^(female|male)$")
    )
    application.add_handler(
        CallbackQueryHandler(design_type_selection, pattern="^(ready_made)$")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_design_selection, pattern="^(design_\d+|next_\d+|prev_\d+)$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_continue_design_choice,
            pattern="^(yes_continue_design|no_continue_design)$",
        )
    )
    application.add_handler(design_for_you_conv_handler)
