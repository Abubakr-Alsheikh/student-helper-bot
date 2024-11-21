from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    CallbackContext,
)

from config import CONNECT_TELEGRAM_USERNAME
from utils import user_management
from utils.faq_management import (
    get_category_name_by_index,
    get_faq_by_id,
    get_faq_categories,
    get_faqs_by_category,
)
from utils.subscription_management import check_subscription


async def handle_help_and_settings(update: Update, context: CallbackContext):
    """Handles the 'المساعدة والإعدادات' option and displays its sub-menu."""

    if not await check_subscription(update, context):
        return
    context.user_data["current_section"] = "settings"  # Set user context
    keyboard = [
        [
            InlineKeyboardButton(
                "طريقة الاستخدام 📖", callback_data="handle_usage_instructions"
            )
        ],
        [InlineKeyboardButton("الإعدادات ⚙️", callback_data="handle_settings")],
        [InlineKeyboardButton("الأسئلة الشائعة ❓", callback_data="handle_faq")],
        [
            InlineKeyboardButton(
                "التواصل مع الدعم/تقديم الاقتراحات ✉️",
                callback_data="handle_support_contact",
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    await update.callback_query.edit_message_text(
        "المساعدة والإعدادات 🤝", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_usage_instructions(update: Update, context: CallbackContext):
    """Handles the 'طريقة الاستخدام' sub-option."""

    # 1. Prepare Keyboard
    keyboard = [
        [InlineKeyboardButton("نص 📝", callback_data="Text")],
        [InlineKeyboardButton("صوت 🎤", callback_data="Audio")],
        [InlineKeyboardButton("فيديو 🎥", callback_data="Video")],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="help_and_settings")],
    ]

    # 2. Send message with options
    await update.callback_query.edit_message_text(
        "اختر طريقة العرض المفضلة: 👇", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_settings(update: Update, context: CallbackContext):
    """Handles the 'الإعدادات' sub-option."""
    keyboard = [
        [
            InlineKeyboardButton(
                "تعديل إعدادات الإشعارات 🔔", callback_data="edit_notification_settings"
            )
        ],
        [
            InlineKeyboardButton(
                "تعديل إعدادات التذكيرات ⏰", callback_data="reminder_settings"
            )
        ],
        [
            InlineKeyboardButton(
                "تعديل تفضيلات المستخدم لطرق الرد 🗣️",
                callback_data="edit_response_method_settings",
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="help_and_settings")],
    ]

    await update.callback_query.edit_message_text(
        "اختر الإعداد الذي تريد تعديله: 👇", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def edit_notification_settings(update: Update, context: CallbackContext):
    """Handles editing notification settings."""
    user_id = update.effective_user.id

    # Fetch user's notification settings
    try:
        is_enabled = await user_management.get_user_setting(
            user_id, "notifications_enabled"
        )
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"حدث خطأ أثناء جلب إعدادات الإشعارات: {e} ⚠️"
        )
        return

    # Prepare keyboard based on current settings
    keyboard = [
        [
            InlineKeyboardButton(
                "تفعيل الإشعارات ✅" if not is_enabled else "إيقاف الإشعارات ❌",
                callback_data=f"toggle_notifications_{user_id}",
            )
        ],
        # Add other settings options (e.g., frequency) here
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="handle_settings")],
    ]

    await update.callback_query.edit_message_text(
        "إعدادات الإشعارات:\n"
        f"حالة الإشعارات: {'مفعل ✅' if is_enabled else 'معطل ❌'}\n"
        "اختر من الخيارات التالية: 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_toggle_notifications(update: Update, context: CallbackContext):
    """Handle toggling notifications on/off."""
    user_id = int(update.callback_query.data.split("_")[-1])

    try:
        # Get current notification setting
        is_enabled = await user_management.get_user_setting(
            user_id, "notifications_enabled"
        )

        # Toggle the setting
        new_state = not is_enabled

        # Update the setting in the database
        await user_management.update_user_setting(
            user_id, "notifications_enabled", new_state
        )

        # Update reminder schedules
        await context.application.reminder_manager.handle_notification_toggle(
            user_id, new_state
        )

        await update.callback_query.answer("تم تحديث إعدادات الإشعارات ✅")
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"حدث خطأ أثناء تحديث إعدادات الإشعارات: {e} ⚠️"
        )
        return

    await edit_notification_settings(update, context)


async def reminder_settings(update: Update, context: CallbackContext):
    """Handles editing reminder settings (simplified)."""
    user_id = update.effective_user.id

    # Get the current reminder frequency (number of reminders per day)
    try:
        current_frequency = await user_management.get_reminder_frequency(user_id)
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"حدث خطأ أثناء جلب إعدادات التذكير: {e} ⚠️"
        )
        return

    # Prepare message text with current frequency
    reminder_text = f"إعدادات التذكير:\n"
    reminder_text += f"عدد مرات التذكير في اليوم: {current_frequency}\n"

    # Prepare keyboard with options to set the frequency (up to 10 reminders per day)
    keyboard = []
    for i in range(1, 11):  # Allow up to 10 reminders per day
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{i} مرة في اليوم 🗓️", callback_data=f"set_reminder_frequency_{i}"
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="handle_settings")]
    )

    await update.callback_query.edit_message_text(
        reminder_text + "اختر عدد مرات التذكير في اليوم: 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_set_reminder_frequency(update: Update, context: CallbackContext):
    """Handles setting the reminder frequency."""
    user_id = update.effective_user.id
    frequency = int(update.callback_query.data.split("_")[-1])

    try:
        # Update database
        await user_management.update_reminder_frequency(user_id, frequency)

        # Get user details
        # user = await user_management.get_user(user_id)
        user_name, preferred_method, _ = await user_management.get_user_for_reminder(
            user_id
        )

        # Update scheduler
        await context.application.reminder_manager.schedule_user_reminders(
            user_id, user_name, frequency, preferred_method
        )

        success_message = f"تم تعيين عدد مرات التذكير إلى {frequency} مرة في اليوم. ✅"
        await update.callback_query.answer(success_message)

    except Exception as e:
        error_message = f"حدث خطأ أثناء تحديث عدد مرات التذكير: {e} ⚠️"
        await update.callback_query.edit_message_text(error_message)
        return

    await reminder_settings(update, context)


async def edit_response_method_settings(update: Update, context: CallbackContext):
    """Handles editing response method settings."""
    user_id = update.effective_user.id

    # Fetch user's preferred response method
    try:
        preferred_method = await user_management.get_user_setting(
            user_id, "voice_written"
        )
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"حدث خطأ أثناء جلب تفضيلات طرق الرد: {e} ⚠️"
        )
        return

    # Prepare the keyboard
    keyboard = [
        [InlineKeyboardButton("نص 📝", callback_data=f"set_response_method_written")],
        [InlineKeyboardButton("صوت 🎤", callback_data=f"set_response_method_voice")],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="handle_settings")],
    ]

    await update.callback_query.edit_message_text(
        f"اختر طريقة الرد المفضلة:\n\n"
        f"طريقة الرد الحالية: {'صوتي 🎤' if preferred_method == 'voice' else 'مكتوب 📝'}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_set_response_method(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    new_method = update.callback_query.data.split("_")[
        -1
    ]  # Extract 'written' or 'voice'

    # Update in the database
    try:
        await user_management.update_user_setting(user_id, "voice_written", new_method)
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"حدث خطأ أثناء تحديث طريقة الرد: {e} ⚠️"
        )
        return

    await update.callback_query.answer(
        f"تم تغيير طريقة الرد إلى: {'صوتي 🎤' if new_method == 'voice' else 'مكتوب 📝'} ✅"
    )
    await edit_response_method_settings(
        update, context
    )  # Recall the function to refresh the display


async def handle_faq(update: Update, context: CallbackContext):
    """Handles the 'الأسئلة الشائعة' sub-option."""

    # 1. Get FAQ categories from the database
    try:
        categories = await get_faq_categories()
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"حدث خطأ أثناء جلب فئات الأسئلة الشائعة: {e} ⚠️"
        )
        return

    # 2. Create buttons for each category
    keyboard = []
    for index, category in enumerate(categories):
        # Use the row index as callback_data
        keyboard.append(
            [InlineKeyboardButton(category, callback_data=f"faq_category_{index}")]
        )

    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="help_and_settings")]
    )

    # 3. Display categories to the user
    await update.callback_query.edit_message_text(
        "اختر فئة من الأسئلة الشائعة: 👇", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_faq_category(update: Update, context: CallbackContext):
    """Handles clicks on FAQ category buttons."""
    query = update.callback_query
    # Get the category index from callback_data
    selected_category_index = int(query.data.replace("faq_category_", ""))

    selected_category = get_category_name_by_index(selected_category_index)

    try:
        faqs = await get_faqs_by_category(selected_category)
    except Exception as e:
        await query.edit_message_text(f"حدث خطأ أثناء جلب الأسئلة الشائعة: {e} ⚠️")
        return

    keyboard = []
    for question, _, question_id in faqs:  # Get the question_id from the database
        callback_data = f"faq_question_{question_id}"
        keyboard.append([InlineKeyboardButton(question, callback_data=callback_data)])

    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="handle_faq")]
    )

    await query.edit_message_text(
        f"الأسئلة الشائعة في فئة '{selected_category}':",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_faq_question(update: Update, context: CallbackContext):
    """Handles clicks on FAQ question buttons."""

    # 1. Get the question_id from the callback data
    query = update.callback_query
    question_id = int(query.data.replace("faq_question_", ""))

    # 2. Fetch the answer and question (using question_id) from the database
    try:
        question, answer = await get_faq_by_id(question_id)
    except Exception as e:
        await query.edit_message_text(f"حدث خطأ أثناء جلب إجابة السؤال: {e} ⚠️")
        return

    # 3. Display the answer to the user
    await query.message.reply_text(
        text=f"**سؤال:** {question}\n\n**الجواب:** {answer}", parse_mode="Markdown"
    )


async def handle_support_contact(update: Update, context: CallbackContext):
    """Handles the 'التواصل مع الدعم/تقديم الاقتراحات' sub-option."""

    # Create the keyboard with the button
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("تواصل مع الدعم 🤝", url=CONNECT_TELEGRAM_USERNAME)],
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data="help_and_settings"
                )
            ],
        ]
    )

    # Display the message with the button to the user
    await update.callback_query.edit_message_text(
        "للتواصل مع الدعم أو تقديم الاقتراحات، يرجى الضغط على الزر أدناه: 👇",
        reply_markup=keyboard,
    )


# Dictionary to map handler names to functions
HELP_AND_SETTINGS_HANDLERS = {
    # Main Hnalders
    "help_and_settings": handle_help_and_settings,
    "handle_usage_instructions": handle_usage_instructions,
    "handle_settings": handle_settings,
    "handle_faq": handle_faq,
    "handle_support_contact": handle_support_contact,
    # Sub Handler handle_settings
    "edit_notification_settings": edit_notification_settings,
    "reminder_settings": reminder_settings,
    "edit_response_method_settings": edit_response_method_settings,
    "toggle_notifications": handle_toggle_notifications,
    "set_response_method_written": handle_set_response_method,
    "set_response_method_voice": handle_set_response_method,
}

HELP_AND_SETTINGS_HANDLERS_PATTERN = {
    # Sub Hnalder handle_faq
    r"^faq_category_.+$": handle_faq_category,
    r"^faq_question_.+$": handle_faq_question,
    r"^set_reminder_frequency_.+$": handle_set_reminder_frequency,
}
