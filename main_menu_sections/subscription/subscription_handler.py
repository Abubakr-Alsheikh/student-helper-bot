from datetime import datetime, timedelta
import sqlite3
import openpyxl
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
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
from config import DATABASE_FILE, SUBSCRIPTION_PLANS
from utils.subscription_management import (
    SERIAL_CODE_DATA,
    activate_free_trial,
    get_subscription_details,
    handle_referral,
)


# Define conversation states
WAITING_FOR_SERIAL_CODE, WAITING_FOR_REFERRAL_YES_NO, WAITING_FOR_REFERRAL_CODE = range(
    3
)


async def handle_subscription(update: Update, context: CallbackContext):
    """Handles the 'الاشتراك' option and displays its sub-menu."""
    context.user_data["current_section"] = "subscription"  # Set user context
    keyboard = [
        [
            InlineKeyboardButton(
                "بدء تجربة مجانية 🎁", callback_data="handle_start_free_trial"
            )
        ],
        [
            InlineKeyboardButton("عرض باقات الاشتراك 📄", callback_data="show_plans")
        ],
        [
            InlineKeyboardButton(
                "عرض تفاصيل الاشتراك 📜",
                callback_data="handle_view_subscription_details",
            )
        ],
        [
            InlineKeyboardButton(
                "تغيير أو إلغاء الاشتراك 🔄",
                callback_data="handle_change_cancel_subscription",
            )
        ],
        [
            InlineKeyboardButton(
                "اكسب اشتراكا عبر دعوة غيرك 🤝",
                callback_data="handle_earn_subscription_referral",
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    await update.callback_query.edit_message_text(
        "الاشتراك 📝", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_start_free_trial(update: Update, context: CallbackContext):
    """Handles the 'بدء تجربة مجانية' sub-option."""
    user_id = update.effective_user.id

    subscription_type, subscription_end_date = await get_subscription_details(user_id)

    if subscription_type == "تجربة مجانية الساعية":
        if await activate_free_trial(user_id):
            new_subscription_type, new_subscription_end_date = (
                await get_subscription_details(user_id)
            )
            # Extract date and time from the new_subscription_end_date string
            end_date_obj = datetime.strptime(
                new_subscription_end_date, "%Y-%m-%d %H:%M:%S"
            )
            end_date_str = end_date_obj.strftime("%Y-%m-%d")
            end_time_str = end_date_obj.strftime("%H:%M:%S")

            await update.callback_query.message.reply_text(
                f"تم تفعيل تجربتك المجانية، وفي الـ6 ساعات القادمة رح أتأكد أني أبهرك ☺️! "
                f"الاشتراك ينتهي في يوم {end_date_str} ، الساعة: {end_time_str}."
            )
        else:
            await update.callback_query.message.reply_text(
                "حدث خطأ أثناء تفعيل التجربة المجانية. يرجى المحاولة لاحقًا."
            )
    else:
        await update.callback_query.message.reply_text(
            "لديك بالفعل اشتراك نشط أو لقد استخدمت تجربتك المجانية من قبل."
        )

async def handle_subscription_plans(update: Update, context: CallbackContext):
    """Sends the subscription plans information to the user."""
    await update.callback_query.message.reply_text(SUBSCRIPTION_PLANS)

async def handle_view_subscription_details(update: Update, context: CallbackContext):
    """Handles the 'عرض تفاصيل الاشتراك' sub-option."""
    user_id = update.effective_user.id

    subscription_type, subscription_end_date = await get_subscription_details(user_id)

    if subscription_end_date is None:
        subscription_end_date = "لقد قمت بألغاء الاشتراك من قبل"
    else:
        # Extract date and time from the new_subscription_end_date string
        end_date_obj = datetime.strptime(subscription_end_date, "%Y-%m-%d %H:%M:%S")
        end_date_str = end_date_obj.strftime("%Y-%m-%d")
        end_time_str = end_date_obj.strftime("%H:%M:%S")

        subscription_end_date = (
            f"الاشتراك ينتهي في يوم {end_date_str} ، الساعة: {end_time_str}."
        )

    if subscription_type:
        await update.callback_query.message.reply_text(
            f"تفاصيل اشتراكك 📜:\n\n"
            f"نوع الاشتراك: {subscription_type}\n"
            f"تاريخ انتهاء الاشتراك: {subscription_end_date}"
        )
    else:
        await update.callback_query.message.reply_text(
            "ليس لديك أي اشتراكات نشطة حاليًا."
        )


async def handle_change_cancel_subscription(update: Update, context: CallbackContext):
    """Handles the 'تغيير أو إلغاء الاشتراك' sub-option."""
    user_id = update.effective_user.id

    subscription_type, subscription_end_date = await get_subscription_details(user_id)

    if subscription_type:
        keyboard = [
            [
                InlineKeyboardButton(
                    "إلغاء الاشتراك 🚫", callback_data="handle_cancel_subscription"
                )
            ],
            [
                InlineKeyboardButton(
                    "تغيير الاشتراك أو تفعيل اشتراك جديد 🔄",
                    callback_data="handle_change_subscription",
                )
            ],
            [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="subscription")],
        ]

        if subscription_end_date is None:
            subscription_end_date = "لقد قمت بألغاء الاشتراك من قبل"
        else:
            # Extract date and time from the new_subscription_end_date string
            end_date_obj = datetime.strptime(subscription_end_date, "%Y-%m-%d %H:%M:%S")
            end_date_str = end_date_obj.strftime("%Y-%m-%d")
            end_time_str = end_date_obj.strftime("%H:%M:%S")
            subscription_end_date = (
                f"الاشتراك ينتهي في يوم {end_date_str} ، الساعة: {end_time_str}."
            )

        await update.callback_query.edit_message_text(
            f"اشتراكك الحالي 📝:\n\n"
            f"نوع الاشتراك: {subscription_type}\n"
            f"تاريخ انتهاء الاشتراك: {subscription_end_date}\n\n"
            "ماذا تريد أن تفعل؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.callback_query.message.reply_text(
            "ليس لديك أي اشتراكات نشطة حاليًا."
        )


async def handle_cancel_subscription(update: Update, context: CallbackContext):
    """Handles the initial cancel request (asks for confirmation)."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("نعم", callback_data="handle_confirm_cancel")],
        [InlineKeyboardButton("لا", callback_data="handle_change_cancel_subscription")],
    ]
    await query.edit_message_text(
        "هل أنت متأكد أنك تريد إلغاء اشتراكك؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_confirm_cancel(update: Update, context: CallbackContext):
    """Handles the cancellation confirmation (if user confirms)."""
    user_id = update.effective_user.id

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET subscription_end_time = NULL WHERE telegram_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    await update.callback_query.edit_message_text("تم إلغاء اشتراكك بنجاح ✅.")


async def handle_cancel_cancel(update: Update, context: CallbackContext):
    """Handles the cancellation cancellation (if user chooses not to cancel)."""
    await update.message.reply_text("لم يتم إلغاء اشتراكك.")


async def handle_change_subscription(update: Update, context: CallbackContext):
    """Handles the change subscription request (asks for serial code)."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("يرجى إدخال رمز الاشتراك التسلسلي:")
    return WAITING_FOR_SERIAL_CODE  # Enter the state for waiting for serial code


async def handle_serial_code(update: Update, context: CallbackContext):
    """Handles the serial code input."""
    user_id = update.effective_user.id
    serial_code = update.message.text

    # 1. Determine code type and load the correct Excel file
    code_prefix = serial_code[:3]  # Get the first 3 characters as the prefix
    code_data = SERIAL_CODE_DATA.get(code_prefix)

    if not code_data:
        await update.message.reply_text("رمز الاشتراك التسلسلي غير صالح.")
        return ConversationHandler.END  # End the conversation

    try:
        workbook = openpyxl.load_workbook(code_data["filename"])
        worksheet = workbook.active
    except FileNotFoundError:
        await update.message.reply_text(
            "حدث خطأ أثناء التحقق من رمز الاشتراك. يرجى المحاولة لاحقًا."
        )
        return ConversationHandler.END  # End the conversation

    # 2. Validate serial code
    found = False
    for row_index, row in enumerate(
        worksheet.iter_rows(values_only=True), start=1
    ):  # Start from row 1
        if row and serial_code in row:
            found = True
            worksheet.delete_rows(row_index)  # Use the row_index to delete
            workbook.save(code_data["filename"])
            break

    if not found:
        await update.message.reply_text(
            "رمز الاشتراك التسلسلي غير صالح أو تم استخدامه من قبل."
        )
        return ConversationHandler.END  # End the conversation

    # 3. Update user's subscription
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT subscription_end_time FROM users WHERE telegram_id = ?", (user_id,)
    )
    row = cursor.fetchone()
    if row and row[0]:
        current_end_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        new_end_date = current_end_date + timedelta(
            days=30 * code_data["duration_months"]
        )
    else:
        new_end_date = datetime.now() + timedelta(
            days=30 * code_data["duration_months"]
        )

    cursor.execute(
        "UPDATE users SET subscription_end_time = ?, type_of_last_subscription = ? WHERE telegram_id = ?",
        (
            new_end_date.strftime("%Y-%m-%d %H:%M:%S"),
            f"مدفوع - {code_data['duration_months']} شهر",
            user_id,
        ),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"تم تفعيل اشتراكك بنجاح لمدة {code_data['duration_months']} شهر! 🎉"
    )

    # 4. Ask about referral
    keyboard = [
        [KeyboardButton("نعم")],
        [KeyboardButton("لا")],
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(
        "هل تمت دعوتك من قبل شخص ما؟", reply_markup=reply_markup
    )
    return WAITING_FOR_REFERRAL_YES_NO


async def handle_referral_yes(update: Update, context: CallbackContext):
    """Handles the 'yes' response to the referral question."""
    await update.message.reply_text(
        "يرجى إدخال رمز الإحالة:", reply_markup=ReplyKeyboardRemove()
    )
    return WAITING_FOR_REFERRAL_CODE


async def handle_referral_no(update: Update, context: CallbackContext):
    """Handles the 'no' response to the referral question."""
    await update.message.reply_text(
        "تم تحديث اشتراكك بنجاح. 🤝", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def handle_referral_code(update: Update, context: CallbackContext):
    """Handles the referral code input."""
    user_id = update.effective_user.id
    referral_code = update.message.text

    if await handle_referral(user_id, referral_code):
        await update.message.reply_text(
            "تم تفعيل الإحالة بنجاح. تمت إضافة 3 أيام إلى اشتراكك واشتراك الشخص الذي قام بدعوتك."
        )
    else:
        await update.message.reply_text("رمز الإحالة غير صالح.")

    return ConversationHandler.END


async def cancel_subscription_change(update: Update, context: CallbackContext):
    """Cancels the subscription change process."""
    await update.message.reply_text("تم إلغاء عملية تغيير الاشتراك.")
    return ConversationHandler.END


async def handle_earn_subscription_referral(update: Update, context: CallbackContext):
    """Handles the 'اكسب اشتراكا عبر دعوة غيرك' sub-option."""
    user_id = update.effective_user.id

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT referral_code FROM users WHERE telegram_id = ?", (user_id,))
    referral_code = cursor.fetchone()
    conn.close()

    if referral_code:
        await update.callback_query.message.reply_text(
            f"يمكنك كسب اشتراك عن طريق دعوة أصدقائك! 🤝\n\n"
            f"رمز الإحالة الخاص بك هو: `{referral_code[0]}`\n\n"
            f"شارك هذا الرمز مع أصدقائك. عندما يشتركون باستخدام رمزك، ستحصل أنت وصديقك على 3 أيام إضافية مجانًا! 🎉\n\n"
            f"**كيفية استخدام رمز الإحالة:**\n"
            f"1. يجب على صديقك الضغط على زر 'تغيير أو تفعيل اشتراك جديد'.\n"
            f"2. بعد إدخال رمز الاشتراك التسلسلي، سيُسأل عما إذا كان قد تمت دعوته.\n"
            f"3. يجب على صديقك إدخال رمز الإحالة الخاص بك (`{referral_code[0]}`) في هذه المرحلة.\n"
            f"4. سيحصل كل منكما على 3 أيام إضافية مجانًا عند نجاح الإحالة!"
        )
    else:
        await update.callback_query.message.reply_text(
            "حدث خطأ أثناء استرداد رمز الإحالة الخاص بك. يرجى المحاولة لاحقًا."
        )


# Create the ConversationHandler
subscription_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            handle_change_subscription, pattern="^handle_change_subscription$"
        )
    ],
    states={
        WAITING_FOR_SERIAL_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_serial_code)
        ],
        WAITING_FOR_REFERRAL_YES_NO: [
            MessageHandler(filters.Regex("^(نعم)$"), handle_referral_yes),
            MessageHandler(filters.Regex("^(لا)$"), handle_referral_no),
        ],
        WAITING_FOR_REFERRAL_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_referral_code)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_subscription_change)],
)


# Dictionary to map handler names to functions
SUBSCRIPTION_HANDLERS = {
    # handler for main button
    "subscription": handle_subscription,
    # handler for sub button
    "handle_start_free_trial": handle_start_free_trial,
    "show_plans": handle_subscription_plans,
    "handle_view_subscription_details": handle_view_subscription_details,
    "handle_change_cancel_subscription": handle_change_cancel_subscription,
    "handle_earn_subscription_referral": handle_earn_subscription_referral,
    # handler for handle_change_cancel_subscription
    "handle_cancel_subscription": handle_cancel_subscription,
    "handle_confirm_cancel": handle_confirm_cancel,
    "handle_cancel_cancel": handle_cancel_cancel,
}
