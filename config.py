import os
from dotenv import load_dotenv


# Function to read text from a file
def get_text_from_file(file_path):
    """Reads text from a file and returns it."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return text
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return "حدث خطأ. الرجاء المحاولة مرة أخرى لاحقًا."


# ----------------
# Load environment variables from .env file
load_dotenv()
# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")
# OpenAI key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ----------------
SERIAL_CODES_FOLDER = "serial_codes"
SERIAL_CODES_1_MONTH = os.path.join(SERIAL_CODES_FOLDER, "serial_codes_1month.xlsx")
SERIAL_CODES_3_MONTH = os.path.join(SERIAL_CODES_FOLDER, "serial_codes_3months.xlsx")
SERIAL_CODES_1_YEAR = os.path.join(SERIAL_CODES_FOLDER, "serial_codes_1year.xlsx")

# Main files directory
MAIN_FILES = "Main Files"

# Path to the folder containing welcoming materials
WELCOMING_FOLDER = os.path.join(MAIN_FILES, "Welcoming")
WELCOMING_TEXT_PATH = os.path.join(WELCOMING_FOLDER, "text.txt")
WELCOMING_AUDIO_PATH = os.path.join(WELCOMING_FOLDER, "audio.mp3")
WELCOMING_VIDEO_PATH = os.path.join(WELCOMING_FOLDER, "video.mp4")

IMAGE_FOLDER = os.path.join(MAIN_FILES, "Images")

# Path to Database File
DATABASE_FILE = os.path.join(MAIN_FILES, "database.db")


# ----------------
# Text files directory
TEXT_FILES_DIRECTORY = os.path.join(MAIN_FILES, "Text Files")

WELCOMING_MESSAGE = get_text_from_file(
    os.path.join(TEXT_FILES_DIRECTORY, "رسالة الترحيب عند بدأ البوت.txt")
)
CONNECT_TELEGRAM_USERNAME = get_text_from_file(
    os.path.join(TEXT_FILES_DIRECTORY, "حساب للتواصل و الدعم.txt")
)
SUBSCRIPTION_PLANS = get_text_from_file(
    os.path.join(TEXT_FILES_DIRECTORY, "خطط الاشتراك.txt")
)

# ----------------
# Excel files directory
EXCEL_FILES_DIRECTORY = os.path.join(MAIN_FILES, "Excel Files")

# Excel files
EXCEL_FILE_QUANTITATIVE = os.path.join(EXCEL_FILES_DIRECTORY, "الاسئلة الكمية.xlsx")
REMINDER_FILE = os.path.join(EXCEL_FILES_DIRECTORY, "التذكرات.xlsx")
FAQ_FILE = os.path.join(EXCEL_FILES_DIRECTORY, "الاسئلة الشائعة.xlsx")
SECTION_CONFIG_FILE = os.path.join(EXCEL_FILES_DIRECTORY, "تحكم بالاقسام.xlsx")


# ----------------
# Verbel files directory
VERBEL_FILES_DIRECTORY = os.path.join(MAIN_FILES, "Verbel Files")
VERBAL_FILE = os.path.join(VERBEL_FILES_DIRECTORY, "الاسئلة اللفظية.xlsx")

CONTEXT_DIRECTORY = os.path.join(VERBEL_FILES_DIRECTORY, "القطع")
ARABIC_PARAGHRAPHS_MK_EXCEL_FILE = os.path.join(VERBEL_FILES_DIRECTORY, "All_Arabic_Final_MK2.xlsx")

# ----------------
# Rewards Files directory
REWARDS_FILES_DIRECTORY = os.path.join(MAIN_FILES, "Rewards Files")

REWARDS_EXCEL = os.path.join(REWARDS_FILES_DIRECTORY, "rewards.xlsx")
REWARDS_DAILY_GIFTS = os.path.join(REWARDS_FILES_DIRECTORY, "daily_gifts")


# ----------------
# Tips and strategies files directory
TIPS_AND_STRATEGIES_DIRECTORY = os.path.join(MAIN_FILES, "Tips and strategies files")

TIPS_AND_STRATEGIES_EXCEL_FILES = os.path.join(TIPS_AND_STRATEGIES_DIRECTORY, "Excel")

GENERAL_ADVICE_FILE = os.path.join(TIPS_AND_STRATEGIES_EXCEL_FILES, "نصائح عامة.xlsx")
SOLUTION_STRATEGIES_FILE = os.path.join(
    TIPS_AND_STRATEGIES_EXCEL_FILES, "استراتيجيات الحل.xlsx"
)

TIPS_AND_STRATEGIES_CONTENT = os.path.join(TIPS_AND_STRATEGIES_DIRECTORY, "Content")


# ----------------
# Design files directory
DESIGNS_DIRECTORY = os.path.join(MAIN_FILES, "Desgin Files")

DESIGNS_EXCEL_FILES = os.path.join(DESIGNS_DIRECTORY, "Excel")
DESIGNS_FOR_MALE_FILE = os.path.join(DESIGNS_EXCEL_FILES, "designs_for_male.xlsx")
DESIGNS_FOR_FEMALE_FILE = os.path.join(DESIGNS_EXCEL_FILES, "designs_for_female.xlsx")

DESIGNS_POWER_POINT_FILES = os.path.join(DESIGNS_DIRECTORY, "PowerPoint")

# ----------------
# Template files directory
TEMPLATE_FILES_DIRECTORY = os.path.join(MAIN_FILES, "Template Files")

# Word Files
WORD_FOLDER_PATH = os.path.join(TEMPLATE_FILES_DIRECTORY, "Word")
WORD_MAIN_PATH = os.path.join(WORD_FOLDER_PATH, "Main.docx")
WORD_MAIN_PATH_MATERIAL = os.path.join(WORD_FOLDER_PATH, "Main Material.docx")
Q_AND_A_FILE_PATH = os.path.join(WORD_FOLDER_PATH, "Q&A.docx")

# Power Point Files
POWERPOINT_FOLDER_PATH = os.path.join(TEMPLATE_FILES_DIRECTORY, "Powerpoint")
POWERPOINT_MAIN_PATH = os.path.join(POWERPOINT_FOLDER_PATH, "Main.pptx")
POWERPOINT_MAIN_PATH_MATERIAL = os.path.join(POWERPOINT_FOLDER_PATH, "Main Material.pptx")
Q_AND_A_FILE_PATH_POWERPOINT = os.path.join(POWERPOINT_FOLDER_PATH, "Q&A.pptx")

# ----------------
# Moivation messages directory
MOTIVATIONAL_MESSAGES_PATH = os.path.join(MAIN_FILES, "Motivations Files")

MALE_MAIN_MENU_MESSAGES_FILE = os.path.join(
    MOTIVATIONAL_MESSAGES_PATH, "main_menu/Male Sructure.xlsx"
)
FEMALE_MAIN_MENUMESSAGES_FILE = os.path.join(
    MOTIVATIONAL_MESSAGES_PATH, "main_menu/Female Sructure.xlsx"
)
MALE_GO_BACK_MESSAGES_FILE = os.path.join(
    MOTIVATIONAL_MESSAGES_PATH, "go_back/Male Sructure.xlsx"
)
FEMALE_GO_BACK_MESSAGES_FILE = os.path.join(
    MOTIVATIONAL_MESSAGES_PATH, "go_back/Female Sructure.xlsx"
)
