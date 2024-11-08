import docx
import pandas as pd
from pptx import Presentation
from config import EXCEL_FILE_BASHAR, POWERPOINT_MAIN_PATH, WORD_MAIN_PATH


def read_excel_data(file_path=EXCEL_FILE_BASHAR):
    """Reads data from the Excel file."""
    df = pd.read_excel(file_path)
    return df


def load_word_template(template_path=WORD_MAIN_PATH):
    """Loads the Word template."""
    try:
        document = docx.Document(template_path)
        return document
    except FileNotFoundError:
        print(f"Error: Word template not found at '{template_path}'")
        return None


def load_powerpoint_template(template_path=POWERPOINT_MAIN_PATH):
    """Loads the PowerPoint template."""
    try:
        prs = Presentation(template_path)
        return prs
    except FileNotFoundError:
        print(f"Error: PowerPoint template not found at '{template_path}'")
        return None
