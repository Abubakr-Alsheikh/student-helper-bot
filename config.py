import os


API_PATH = "APIs"

# Bot token
BOT_TOKEN_PATH = os.path.join(API_PATH, "bot_token.txt")
BOT_TOKEN = open(BOT_TOKEN_PATH, "r", encoding="UTF-8").readline()

# OpenAI key
OPENAI_API_PATH = os.path.join(API_PATH, "openai.txt")
OPENAI_API_KEY = open(OPENAI_API_PATH, "r", encoding="UTF-8").readline()

# ----------------
# Main files directory
MAIN_FILES = "Main Files"

# Path to the folder containing welcoming materials
WELCOMING_FOLDER = "welcoming"

IMAGE_FOLDER = "Images"

# Path to Database File
DATABASE_FILE = os.path.join(MAIN_FILES, "database.db")


# ----------------
# Excel files directory
EXCEL_FILES_DIRECTORY = os.path.join(MAIN_FILES, "Excel Files")

# Excel files
EXCEL_FILE_BASHAR = os.path.join(EXCEL_FILES_DIRECTORY, "الاسئلة الكمية.xlsx")
REMINDER_FILE = os.path.join(EXCEL_FILES_DIRECTORY, "reminders.xlsx")
VERBAL_FILE = os.path.join(EXCEL_FILES_DIRECTORY, "الاسئلة اللفظية.xlsx")
FAQ_FILE = os.path.join(EXCEL_FILES_DIRECTORY, "الاسئلة الشائعة.xlsx")


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
Q_AND_A_FILE_PATH = os.path.join(WORD_FOLDER_PATH, "Q&A.docx")

# Power Point Files
POWERPOINT_FOLDER_PATH = os.path.join(TEMPLATE_FILES_DIRECTORY, "Powerpoint")
POWERPOINT_MAIN_PATH = os.path.join(POWERPOINT_FOLDER_PATH, "Main.pptx")


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
