import os
import logging
import zipfile
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

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_ADMIN_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Conversation states
LOGIN, MAIN_MENU, FILE_SELECTION, FILE_ACTION, FOLDER_ACTION = range(5)

# Constants for callback data prefixes
CAT_PREFIX = "CAT:"
FILE_PREFIX = "FILE:"
FOLDER_PREFIX = "FOLDER:"
DOWNLOAD_FILE_PREFIX = "DOWNLOAD_FILE:"
DOWNLOAD_FOLDER_PREFIX = "DOWNLOAD_FOLDER:"
REPLACE_FILE_PREFIX = "REPLACE_FILE:"
REPLACE_FOLDER_PREFIX = "REPLACE_FOLDER:"

# Define file categories structure
FILE_CATEGORIES = {
    'serial_codes': {
        "type": "files",
        "arabic_name": "الأكواد التسلسلية",
        "items": [
            ("serial 1 month", "الأكواد شهر الواحد", config.SERIAL_CODES_1_MONTH),
            ("serial 3 month", "الأكواد ثلاثة شهور", config.SERIAL_CODES_3_MONTH),
            ("serial 1 year", "الأكواد سننة الواحد", config.SERIAL_CODES_1_YEAR),
        ]
    },
    'welcoming': {
        "type": "files",
        "arabic_name": "قسم الترحيب",
        "items": [
            ("Welcoming Text", "نص الترحيب", config.WELCOMING_TEXT_PATH),
            ("Welcoming Audio", "الملف الصوتي للترحيب", config.WELCOMING_AUDIO_PATH),
            ("Welcoming Video", "فيديو الترحيب", config.WELCOMING_VIDEO_PATH),
        ]
    },
    'text_files': {
        "type": "files",
        "arabic_name": "الملفات النصية",
        "items": [
            ("Welcoming Message", "رسالة الترحيب", config.WELCOMING_MESSAGE),
            ("Connect Telegram Username", "اسم المستخدم في تليجرام", config.CONNECT_TELEGRAM_USERNAME),
            ("Subscription Plans", "خطط الاشتراك", config.SUBSCRIPTION_PLANS),
        ]
    },
    'excel_files': {
        "type": "files",
        "arabic_name": "ملفات إكسل",
        "items": [
            ("Quantitative Questions", "الأسئلة الكمية", config.EXCEL_FILE_QUANTITATIVE),
            ("Reminders", "التذكيرات", config.REMINDER_FILE),
            ("FAQ", "الأسئلة الشائعة", config.FAQ_FILE),
            ("Section Config", "إعدادات الأقسام", config.SECTION_CONFIG_FILE),
        ]
    },
    'verbal_files': {
        "type": "files",
        "arabic_name": "الأسئلة الشفهية",
        "items": [
            ("Verbal Questions", "الأسئلة الشفهية", config.VERBAL_FILE),
        ]
    },
    'rewards_files': {
        "type": "mixed",
        "arabic_name": "مكافآت",
        "items": [
            ("Rewards Excel", "ملف مكافآت إكسل", config.REWARDS_EXCEL),
            {"name": "Rewards Folder", "arabic_name": "مجلد المكافآت", "path": config.REWARDS_DAILY_GIFTS},
        ]
    },
    'tips_strategies': {
        "type": "mixed",
        "arabic_name": "نصائح وإستراتيجيات",
        "items": [
            ("General Advice", "نصائح عامة", config.GENERAL_ADVICE_FILE),
            ("Solution Strategies", "استراتيجيات الحل", config.SOLUTION_STRATEGIES_FILE),
            {"name": "Solution Folder", "arabic_name": "مجلد الاستراتيجيات", "path": config.TIPS_AND_STRATEGIES_CONTENT},
        ]
    },
    'design': {
        "type": "mixed",
        "arabic_name": "التصاميم",
        "items": [
            ("Designs for Male", "تصاميم للذكور", config.DESIGNS_FOR_MALE_FILE),
            ("Designs for Female", "تصاميم للإناث", config.DESIGNS_FOR_FEMALE_FILE),
            {"name": "PowerPoint Designs", "arabic_name": "تصاميم باوربوينت", "path": config.DESIGNS_POWER_POINT_FILES},
        ]
    },
    'templates': {
        "type": "files",
        "arabic_name": "القوالب",
        "items": [
            ("Word Main", "قالب وورد الرئيسي", config.WORD_MAIN_PATH),
            ("Q&A", "أسئلة وأجوبة", config.Q_AND_A_FILE_PATH),
            ("PowerPoint Main", "قالب باوربوينت الرئيسي", config.POWERPOINT_MAIN_PATH),
        ]
    },
    'motivation': {
        "type": "files",
        "arabic_name": "رسائل التحفيز",
        "items": [
            ("Male Main Menu Messages", "رسائل القائمة الرئيسية للذكور", config.MALE_MAIN_MENU_MESSAGES_FILE),
            ("Female Main Menu Messages", "رسائل القائمة الرئيسية للإناث", config.FEMALE_MAIN_MENUMESSAGES_FILE),
            ("Male Go Back Messages", "رسائل الرجوع للذكور", config.MALE_GO_BACK_MESSAGES_FILE),
            ("Female Go Back Messages", "رسائل الرجوع للإناث", config.FEMALE_GO_BACK_MESSAGES_FILE),
        ]
    },
}


class AdminBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.file_categories = FILE_CATEGORIES

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Starts the bot and requests the password."""
        await update.message.reply_text("من فضلك أدخل كلمة مرور المدير:")
        return LOGIN

    async def check_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Checks the admin password."""
        if update.message.text == ADMIN_PASSWORD:
            await update.message.reply_text("تم تسجيل الدخول بنجاح!")
            return await self.show_main_menu(update, context)
        else:
            await update.message.reply_text("كلمة مرور غير صحيحة. تم رفض الوصول.")
            return ConversationHandler.END

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Displays the main menu."""
        keyboard = [
            [InlineKeyboardButton(category_data["arabic_name"], callback_data=f"{CAT_PREFIX}{category_en}")]
            for category_en, category_data in self.file_categories.items()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "اختر تصنيفًا:", reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("اختر تصنيفًا:", reply_markup=reply_markup)

        return MAIN_MENU

    def _create_zip(self, source, zip_path):
        """Creates a zip file from a folder or a single file."""
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isdir(source):
                for root, _, files in os.walk(source):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source)
                        zipf.write(file_path, arcname)
            elif os.path.isfile(source):
                zipf.write(source, os.path.basename(source))

    def _extract_zip(self, zip_path, dest_path):
        """Extracts a zip file to a destination folder."""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_path)


    async def handle_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        if not query.data.startswith(CAT_PREFIX):
            return MAIN_MENU

        category = query.data[len(CAT_PREFIX):]
        category_data = self.file_categories.get(category)
        if not category_data:
            await query.edit_message_text("تم اختيار تصنيف غير صالح.")
            return MAIN_MENU

        keyboard = []
        if category_data["type"] in ("files", "mixed"):
            for item in category_data["items"]:
                if isinstance(item, tuple):
                    en_name, ar_name, file_path = item
                    keyboard.append([InlineKeyboardButton(ar_name, callback_data=f"{FILE_PREFIX}{category}:{en_name}")])
                elif isinstance(item, dict):
                    ar_folder_name = item.get("arabic_name", item["name"])
                    keyboard.append([InlineKeyboardButton(
                        f"📁 {ar_folder_name}",
                        callback_data=f"{FOLDER_PREFIX}{category}:{item['name']}"
                    )])
            keyboard.append([InlineKeyboardButton("رجوع", callback_data="MAIN_MENU")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"اختر عنصرًا من {category_data.get('arabic_name', category)}:", reply_markup=reply_markup
            )
            return FILE_SELECTION

        elif category_data["type"] == "folder":
            if category_data["items"] and isinstance(category_data["items"][0], dict):
                folder_item = category_data["items"][0]
                folder_path = folder_item["path"]
                if os.path.exists(folder_path):
                    zip_path = f"{folder_path}.zip"
                    self._create_zip(folder_path, zip_path)
                    await query.message.reply_document(document=open(zip_path, "rb"))
                    os.remove(zip_path)
                    return await self.show_main_menu(update, context)
                else:
                    await query.edit_message_text("لم يتم العثور على المجلد.")
                    return MAIN_MENU
            else:
                await query.edit_message_text("تهيئة المجلد غير صالحة.")
                return MAIN_MENU
        return MAIN_MENU


    async def handle_file_or_folder_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        if query.data == "MAIN_MENU":
            return await self.show_main_menu(update, context)

        parts = query.data.split(":", 2)

        if len(parts) != 3:
            await query.edit_message_text("تنسيق بيانات الاختيار غير صالح.")
            return MAIN_MENU

        prefix, category, item_name = parts

        if prefix == FILE_PREFIX[:len(FILE_PREFIX)-1]:
            current_prefix = FILE_PREFIX
        elif prefix == FOLDER_PREFIX[:len(FOLDER_PREFIX)-1]:
            current_prefix = FOLDER_PREFIX
        else:
            await query.edit_message_text("بادئة الاختيار غير صالحة.")
            return MAIN_MENU

        category_data = self.file_categories.get(category)
        if not category_data:
            await query.edit_message_text("تم اختيار تصنيف غير صالح.")
            return MAIN_MENU

        for item in category_data["items"]:
            if isinstance(item, tuple) and query.data.startswith(current_prefix):
                en_name, ar_name, file_path = item
                if en_name == item_name:
                    keyboard = [
                        [InlineKeyboardButton(f"تحميل {ar_name}", callback_data=f"{DOWNLOAD_FILE_PREFIX}{file_path}")],
                        [InlineKeyboardButton(f"استبدال {ar_name}", callback_data=f"{REPLACE_FILE_PREFIX}{file_path}")],
                        [InlineKeyboardButton("رجوع", callback_data=f"{CAT_PREFIX}{category}")],
                    ]
                    context.user_data["current_path"] = file_path
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"اختر إجراء لـ {ar_name}:", reply_markup=reply_markup)
                    return FILE_ACTION
            elif isinstance(item, dict) and query.data.startswith(current_prefix):
                if item["name"] == item_name:
                    folder_path = item["path"]
                    ar_folder_name = item.get("arabic_name", item["name"])
                    keyboard = [
                        [InlineKeyboardButton(f"تحميل {ar_folder_name} مضغوطًا", callback_data=f"{DOWNLOAD_FOLDER_PREFIX}{folder_path}")],
                        [InlineKeyboardButton(f"استبدال {ar_folder_name}", callback_data=f"{REPLACE_FOLDER_PREFIX}{folder_path}")],
                        [InlineKeyboardButton("رجوع", callback_data=f"{CAT_PREFIX}{category}")],
                    ]
                    context.user_data["current_path"] = folder_path
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"اختر إجراء لـ {ar_folder_name}:", reply_markup=reply_markup)
                    return FOLDER_ACTION
        await query.edit_message_text("لم يتم العثور على العنصر في هذا القسم.")
        return MAIN_MENU


    async def handle_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data.startswith(DOWNLOAD_FILE_PREFIX):
            path = query.data[len(DOWNLOAD_FILE_PREFIX):]
            if os.path.exists(path):
                await query.message.reply_document(document=open(path, "rb"))
            else:
                await query.edit_message_text("لم يتم العثور على الملف.")
        elif query.data.startswith(DOWNLOAD_FOLDER_PREFIX):
            path = query.data[len(DOWNLOAD_FOLDER_PREFIX):]
            if os.path.exists(path):
                zip_path = f"{path}.zip"
                self._create_zip(path, zip_path)
                await query.message.reply_document(document=open(zip_path, "rb"))
                os.remove(zip_path)
            else:
                await query.edit_message_text("لم يتم العثور على المجلد.")


    async def handle_replace(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data.startswith(REPLACE_FILE_PREFIX):
            path = query.data[len(REPLACE_FILE_PREFIX):]
            action_type = "REPLACE_FILE"
        elif query.data.startswith(REPLACE_FOLDER_PREFIX):
            path = query.data[len(REPLACE_FOLDER_PREFIX):]
            action_type = "REPLACE_FOLDER"
        else:
            await query.edit_message_text("إجراء غير صالح.")
            return MAIN_MENU

        context.user_data["action_type"] = action_type
        context.user_data["current_path"] = path
        if action_type == "REPLACE_FILE":
            await query.edit_message_text("يرجى تحميل الملف الجديد للاستبدال.")
        else:
            await query.edit_message_text("يرجى تحميل ملف مضغوط يحتوي على محتويات المجلد الجديد.")
        return FILE_ACTION if action_type == "REPLACE_FILE" else FOLDER_ACTION

    async def handle_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.document:
            await update.message.reply_text("يرجى تحميل ملف صالح.")
            return context.user_data.get("action_type", FILE_ACTION)

        path = context.user_data.get("current_path")
        action_type = context.user_data.get("action_type")

        if not path or not action_type:
            await update.message.reply_text("انتهت الجلسة. يرجى البدء من جديد.")
            return ConversationHandler.END

        new_file = await update.message.document.get_file()

        try:
            if action_type == "REPLACE_FILE":
                await new_file.download_to_drive(path)
                await update.message.reply_text("تم استبدال الملف بنجاح!")
            elif action_type == "REPLACE_FOLDER":
                temp_zip = f"{path}_temp.zip"
                await new_file.download_to_drive(temp_zip)
                self._extract_zip(temp_zip, path)
                os.remove(temp_zip)
                await update.message.reply_text("تم استبدال محتويات المجلد بنجاح!")
            else:
                await update.message.reply_text("نوع الإجراء غير صالح.")
        except Exception as e:
            logger.error(f"Error during replacement: {e}")
            await update.message.reply_text("حدث خطأ أثناء الاستبدال.")

        return await self.show_main_menu(update, context)

    async def set_commands(self, application: Application) -> None:
        commands = [BotCommand("start", "تسجيل الدخول")]
        await application.bot.set_my_commands(commands)

    def build_application(self) -> Application:
        application = Application.builder().token(self.bot_token).post_init(self.set_commands).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)],
                MAIN_MENU: [CallbackQueryHandler(self.handle_category_selection)],
                FILE_SELECTION: [CallbackQueryHandler(self.handle_file_or_folder_selection)],
                FILE_ACTION: [
                    CallbackQueryHandler(self.handle_download, pattern=f"^{DOWNLOAD_FILE_PREFIX}"),
                    CallbackQueryHandler(self.handle_replace, pattern=f"^{REPLACE_FILE_PREFIX}"),
                    CallbackQueryHandler(self.handle_category_selection, pattern=rf"^{CAT_PREFIX}"),
                    MessageHandler(filters.Document.ALL, self.handle_upload),
                ],
                FOLDER_ACTION: [
                    CallbackQueryHandler(self.handle_download, pattern=f"^{DOWNLOAD_FOLDER_PREFIX}"),
                    CallbackQueryHandler(self.handle_replace, pattern=f"^{REPLACE_FOLDER_PREFIX}"),
                    CallbackQueryHandler(self.handle_category_selection, pattern=rf"^{CAT_PREFIX}"),
                    MessageHandler(filters.Document.ALL, self.handle_upload),
                ],
            },
            fallbacks=[CommandHandler("start", self.start)],
        )

        application.add_handler(conv_handler)
        return application


def main():
    admin_bot = AdminBot(bot_token=BOT_TOKEN)
    application = admin_bot.build_application()
    application.run_polling()


if __name__ == "__main__":
    main()