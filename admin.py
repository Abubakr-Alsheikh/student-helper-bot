import os
import logging
from dotenv import load_dotenv
from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config

load_dotenv()

# Admin bot configuration
BOT_TOKEN = os.getenv("BOT_ADMIN_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(
    LOGIN,
    MAIN_MENU,
    TEXT_FILES_MENU,
    EXCEL_FILES_MENU,
    VERBAL_FILES_MENU,
    REWARDS_FILES_MENU,
    TIPS_STRATEGIES_MENU,
    DESIGNS_MENU,
    TEMPLATES_MENU,
    MOTIVATION_MENU,
    FILE_SELECTION,
    FILE_ACTION,
) = range(12)


class AdminBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.file_categories = {
            'welcoming': {
                ("Welcoming Text", config.WELCOMING_TEXT_PATH),
                ("Welcoming Audio", config.WELCOMING_AUDIO_PATH),
                ("Welcoming Video", config.WELCOMING_VIDEO_PATH)
            },
            'text_files': [
                ("Welcoming Message", config.WELCOMING_MESSAGE),
                ("Connect Telegram Username", config.CONNECT_TELEGRAM_USERNAME),
                ("Subscription Plans", config.SUBSCRIPTION_PLANS)
            ],
            'excel_files': [
                ("Quantitative Questions", config.EXCEL_FILE_QUANTITATIVE),
                ("Reminders", config.REMINDER_FILE),
                ("FAQ", config.FAQ_FILE),
                ("Section Config", config.SECTION_CONFIG_FILE)
            ],
            'verbal_files': [
                ("Verbal Questions", config.VERBAL_FILE),
                ("Arabic Paragraphs MK Excel", config.ARABIC_PARAGHRAPHS_MK_EXCEL_FILE)
            ],
            'rewards_files': [
                ("Rewards Excel", config.REWARDS_EXCEL)
            ],
            'tips_strategies': [
                ("General Advice", config.GENERAL_ADVICE_FILE),
                ("Solution Strategies", config.SOLUTION_STRATEGIES_FILE)
            ],
            'design': [
                ("Designs for Male", config.DESIGNS_FOR_MALE_FILE),
                ("Designs for Female", config.DESIGNS_FOR_FEMALE_FILE)
            ],
            'templates': [
                ("Word Main", config.WORD_MAIN_PATH),
                ("Q&A", config.Q_AND_A_FILE_PATH),
                ("PowerPoint Main", config.POWERPOINT_MAIN_PATH)
            ],
            'motivation': [
                ("Male Main Menu Messages", config.MALE_MAIN_MENU_MESSAGES_FILE),
                ("Female Main Menu Messages", config.FEMALE_MAIN_MENUMESSAGES_FILE),
                ("Male Go Back Messages", config.MALE_GO_BACK_MESSAGES_FILE),
                ("Female Go Back Messages", config.FEMALE_GO_BACK_MESSAGES_FILE)
            ]
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the admin bot and request password."""
        await update.message.reply_text("من فضلك أدخل كلمة مرور:")
        return LOGIN

    async def check_password(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Verify admin password."""
        if update.message.text == ADMIN_PASSWORD:
            await update.message.reply_text("تم تسجيل الدخول بنجاح! اختر تصنيفًا:")
            return await self.show_main_menu(update, context)
        else:
            await update.message.reply_text("كلمة مرور غير صحيحة. تم رفض الوصول.")
            return ConversationHandler.END

    async def show_main_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Display main menu categories."""
        keyboard = [
            [InlineKeyboardButton("الترحيب", callback_data="WELCOMING")],
            [InlineKeyboardButton("ملفات نصية", callback_data="TEXT_FILES")],
            [InlineKeyboardButton("ملفات Excel", callback_data="EXCEL_FILES")],
            [InlineKeyboardButton("ملفات شفوية", callback_data="VERBAL_FILES")],
            [InlineKeyboardButton("ملفات المكافآت", callback_data="REWARDS_FILES")],
            [InlineKeyboardButton("نصائح واستراتيجيات", callback_data="TIPS_STRATEGIES")],
            [InlineKeyboardButton("التصاميم", callback_data="DESIGNS")],
            [InlineKeyboardButton("القوالب", callback_data="TEMPLATES")],
            [InlineKeyboardButton("رسائل التحفيز", callback_data="MOTIVATION")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "اختر تصنيفًا:", reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "اختر تصنيفًا:", reply_markup=reply_markup
            )

        return MAIN_MENU

    async def handle_category_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle category selection and show files."""
        query = update.callback_query
        await query.answer()

        category = query.data
        category_map = {
            "WELCOMING": "welcoming",
            "TEXT_FILES": "text_files",
            "EXCEL_FILES": "excel_files",
            "VERBAL_FILES": "verbal_files",
            "REWARDS_FILES": "rewards_files",
            "TIPS_STRATEGIES": "tips_strategies",
            "DESIGNS": "design",
            "TEMPLATES": "templates",
            "MOTIVATION": "motivation"
        }

        selected_category = category_map.get(category)
        if not selected_category:
            await query.edit_message_text("تم اختيار تصنيف غير صالح.")
            return MAIN_MENU

        files = self.file_categories.get(selected_category, [])

        keyboard = [
            [
                InlineKeyboardButton(
                    file_name, callback_data=f"FILE:{selected_category}:{file_name}"
                )
            ]
            for file_name, _ in files
        ]
        keyboard.append(
            [InlineKeyboardButton("العودة إلى القائمة الرئيسية", callback_data="MAIN_MENU")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"اختر ملفًا في {selected_category}:", reply_markup=reply_markup
        )

        return FILE_SELECTION

    async def handle_file_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle file selection and provide actions."""
        query = update.callback_query
        await query.answer()

        if query.data == "MAIN_MENU":
            return await self.show_main_menu(update, context)

        if query.data.startswith("FILE:"):
            _, category, file_name = query.data.split(":")
            file_path = next(
                path
                for name, path in self.file_categories[category]
                if name == file_name
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "تنزيل الملف",
                        callback_data=f"DOWNLOAD:{category}:{file_name}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "استبدال الملف", callback_data=f"REPLACE:{category}:{file_name}"
                    )
                ],
                [InlineKeyboardButton("العودة إلى الملفات", callback_data=category)],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"إجراءات {file_name}:", reply_markup=reply_markup
            )

            context.user_data["current_file"] = file_path
            return FILE_ACTION

    async def download_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Download the selected file."""
        query = update.callback_query
        await query.answer()

        file_path = context.user_data.get("current_file")
        if file_path and os.path.exists(file_path):
            await query.message.reply_document(document=file_path)
        else:
            await query.edit_message_text("الملف غير موجود.")

    async def replace_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiate file replacement process."""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "يرجى تحميل الملف الجديد لاستبدال الملف الحالي."
        )
        return FILE_ACTION

    async def handle_file_upload(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle file upload for replacement."""
        file_path = context.user_data.get("current_file")

        if update.message.document:
            new_file = await update.message.document.get_file()
            await new_file.download_to_drive(file_path)
            await update.message.reply_text("تم استبدال الملف بنجاح!")
            return await self.show_main_menu(update, context)
        else:
            await update.message.reply_text("يرجى تحميل ملف صالح.")
            return FILE_ACTION

    async def set_commands(self, application: Application) -> None:
        """Define bot commands."""
        commands = [
            BotCommand("start", "تسجيل الدخول"),
        ]
        await application.bot.set_my_commands(commands)

    def build_application(self) -> Application:
        """Build the Telegram bot application."""
        application = Application.builder().token(self.bot_token).post_init(self.set_commands).build()
        templst = [key.upper() for key, value in self.file_categories.items()]
        joined_list = "|".join(templst)
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                LOGIN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)
                ],
                MAIN_MENU: [CallbackQueryHandler(self.handle_category_selection)],
                FILE_SELECTION: [CallbackQueryHandler(self.handle_file_selection)],
                FILE_ACTION: [
                    CallbackQueryHandler(self.download_file, pattern="^DOWNLOAD:"),
                    CallbackQueryHandler(self.replace_file, pattern="^REPLACE:"),
                    CallbackQueryHandler(self.handle_category_selection, pattern=rf"^({joined_list})&"),
                    MessageHandler(filters.Document.ALL, self.handle_file_upload),
                ],
            },
            fallbacks=[CommandHandler("start", self.start)],
        )

        application.add_handler(conv_handler)
        return application


def main():
    """Main function to run the admin bot."""
    admin_bot = AdminBot(bot_token=BOT_TOKEN)
    application = admin_bot.build_application()
    application.run_polling(poll_interval=0.1)


if __name__ == "__main__":
    main()
