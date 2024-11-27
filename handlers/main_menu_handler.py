from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CallbackContext,
)
from utils.database import get_data
from utils.motivation.button_click_tracker import track_button_clicks


async def main_menu_handler(update_or_query, context: CallbackContext):
    """Handles the /main_menu command and displays the main menu."""
    context.user_data["current_section"] = None

    ## FUTUER: Enabling the subscription

    # Get user_id correctly based on the type of update_or_query
    # if isinstance(update_or_query, Update):
    #     user_id = update_or_query.effective_user.id
    # else:  # Assuming it's a CallbackQuery
    #     user_id = update_or_query.from_user.id

    # subscription_data = get_data(
    #     "SELECT subscription_end_time FROM users WHERE telegram_id = ?", (user_id,)
    # )
    # if (
    #     subscription_data
    #     and subscription_data[0][0] is not None
    #     and datetime.strptime(subscription_data[0][0], "%Y-%m-%d %H:%M:%S")
    #     > datetime.now()
    # ):
    if True:
        # Subscription is active
        keyboard = [
            [
                InlineKeyboardButton(
                    "تحديد المستوى 📝", callback_data="level_determination"
                )
            ],
            [
                InlineKeyboardButton(
                    "التعلم بالطريقة التقليدية 📚", callback_data="traditional_learning"
                )
            ],
            [
                InlineKeyboardButton(
                    "التعلم عبر المحادثة 🗣️", callback_data="conversation_learning"
                )
            ],
            [InlineKeyboardButton("الاختبارات 📝", callback_data="tests")],
            [
                InlineKeyboardButton(
                    "نصائح واستراتيجيات 💡", callback_data="tips_and_strategies"
                )
            ],
            [InlineKeyboardButton("الإحصائيات 📊", callback_data="statistics")],
            [InlineKeyboardButton("خلينا نصمملك 🎨", callback_data="design_for_you")],
            [InlineKeyboardButton("المكافآت 🎁", callback_data="rewards")],
            # [InlineKeyboardButton("الاشتراك 🔄", callback_data="subscription")],
            [
                InlineKeyboardButton(
                    "المساعدة والإعدادات ⚙️", callback_data="help_and_settings"
                )
            ],
        ]

        main_menu_message = "إليك القائمة الرئيسية ☘️:"

    else:
        # Subscription expired or doesn't exist
        keyboard = [
            [InlineKeyboardButton("الاشتراك 🔄", callback_data="subscription")],
        ]

        main_menu_message = (
            "لتتمكن من الوصول إلى جميع الاقسام, يرجى الاشتراك 😊:\n"
            "سارع بالاشتراك الآن  للاستفادة من عروضنا المميزة! ✨"
        )

    if isinstance(update_or_query, Update):
    # Track clicks for motivational messages
        await track_button_clicks(update_or_query, context, called_from="main_menu")

        # Determine whether the update is a message or callback query
        if update_or_query.message:  # Regular message update
            await update_or_query.message.reply_text(
                main_menu_message, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update_or_query.callback_query:  # Button press (CallbackQuery)
            # Respond via callback query's associated message
            await update_or_query.callback_query.message.reply_text(
                main_menu_message, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            # Optionally acknowledge the callback query to avoid client-side loading icons
            await update_or_query.callback_query.answer()
    else:
        if update_or_query.data == "go_back":
            await track_button_clicks(
                update_or_query, context, called_from="go_back"
            )  # Track clicks for motivational messages

            # To go back to the previous menu or step
            await update_or_query.edit_message_text(
                main_menu_message, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # To show the user main menu
            await update_or_query.message.reply_text(
                main_menu_message, reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def handle_main_menu_option(update: Update, context: CallbackContext):
    """Handles the button presses for options in the main menu."""

    query = update.callback_query
    await query.answer()
    callback_data = query.data
    if callback_data == "go_back":
        # Logic to go back to the previous menu or step
        await main_menu_handler(query, context)
        return
    print(callback_data)
