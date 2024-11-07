import logging
from docxtpl import DocxTemplate
from docx2pdf import convert
import subprocess
import os
from datetime import datetime
import shutil

from config import Q_AND_A_FILE_PATH
from utils import database
#import pypandoc
logger = logging.getLogger(__name__)


def generate_quiz_pdf(questions, user_id, category_name=None):
    """
    Generates a PDF quiz with the given questions using a Word template.
    Args:
        questions (list): A list of tuples, each containing question data.
    """
    try:
        # 1. Create the directory structure
        base_dir = "user_tests"
        user_dir = os.path.join(base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)  # Create if it doesn't exist

        # 2. Prepare the data for the Word template
        quiz_data = []
        for i, question_data in enumerate(questions):
            (
                question_id,
                correct_answer,
                question_text,
                option_a,
                option_b,
                option_c,
                option_d,
                explanation,
                main_category_id,
                question_type,
                image_path,
                passage_name,
                *_,  # Ignore unused elements
            ) = question_data
            main_category_name = database.get_data(
                "SELECT name FROM main_categories WHERE id = ?", (main_category_id,)
            )

            quiz_data.append(
                {
                    "QuestionNumber": i + 1,
                    "QuestionText": question_text,
                    "MainCategoryName": main_category_name[0][0],
                    "OptionA": option_a,
                    "OptionB": option_b,
                    "OptionC": option_c,
                    "OptionD": option_d,
                    "CorrectAnswer": correct_answer,
                    "Explanation": explanation,
                }
            )

        datestamp = datetime.now().strftime("%Y-%m-%d")  # Formatted timestamp
        timestamp = datetime.now().strftime("%H-%M-%S")  # Formatted timestamp

        word_filename = os.path.join(user_dir, f"الاختبار_{timestamp}.docx")
        pdf_filename = os.path.join(
            user_dir, f"الاختبار_يوم_{datestamp}_الوقت_{timestamp}.pdf"
        )

        generate_word_doc(Q_AND_A_FILE_PATH, word_filename, quiz_data)
        convert_to_pdf(word_filename, pdf_filename)

        # 5. Cleanup the temporary Word file
        if os.path.exists(word_filename):
            os.remove(word_filename)

        return pdf_filename
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_quiz_pdf: {e}")
        return None


def generate_word_doc(template_path, output_path, quiz_data):
    """Generates the Word document."""
    try:
        doc = DocxTemplate(template_path)
        doc.render({"questions": quiz_data})
        doc.save(output_path)
    except Exception as e:
        logger.error(f"Error generating Word document: {e}")
        raise

def convert_to_pdf_using_pandoc(word_file, pdf_file):
    """Converts the Word document to PDF using Pandoc."""
    try:
        pypandoc.convert_file(word_file, 'pdf', outputfile=pdf_file)
    except Exception as e:
        logger.error(f"Error converting to PDF: {e}")
        raise

def convert_to_pdf(word_file, pdf_file=None):
    # Set default output name if pdf_file is not specified
    if pdf_file is None:
        pdf_file = os.path.splitext(word_file)[0] + ".pdf"
    
    # Set a temporary directory for the output to handle custom names
    temp_dir = os.path.dirname(pdf_file)
    temp_pdf_path = os.path.join(temp_dir, os.path.splitext(os.path.basename(word_file))[0] + ".pdf")
    
    # Run the LibreOffice command to convert to PDF in temp directory
    result = subprocess.run([
        "libreoffice", "--headless", "--convert-to", "pdf", "--outdir",
        temp_dir, word_file
    ], check=True)
    
    # Rename to the specified pdf_file name if it differs from temp_pdf_path
    if os.path.exists(temp_pdf_path):
        if temp_pdf_path != pdf_file:
            shutil.move(temp_pdf_path, pdf_file)
        print(f"Conversion successful: {pdf_file}")
        return pdf_file
    else:
        raise FileNotFoundError("PDF conversion failed.")