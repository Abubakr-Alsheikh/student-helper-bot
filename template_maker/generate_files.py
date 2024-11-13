import logging
import os
from datetime import datetime

from config import Q_AND_A_FILE_PATH
from template_maker.file_exports import convert_docx_to_pdf, generate_word_doc
from utils import database

logger = logging.getLogger(__name__)


async def generate_quiz_pdf(questions, user_id, which_quiz, category_name=None) -> str:
    """
    Generates a PDF quiz with the given questions using a Word template.
    Args:
        questions (list): A list of tuples, each containing question data.
    """
    try:
        # Create the directory structure
        base_dir = "user_tests"
        user_dir = os.path.join(base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)  # Create if it doesn't exist

        # Prepare the data for the Word template
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

            if category_name:
                category = category_name
            else:
                category = database.get_data(
                    "SELECT name FROM main_categories WHERE id = ?", (main_category_id,)
                )[0][0]

            quiz_data.append(
                {
                    "QuestionNumber": i + 1,
                    "QuestionText": question_text,
                    "MainCategoryName": category,
                    "OptionA": option_a,
                    "OptionB": option_b,
                    "OptionC": option_c,
                    "OptionD": option_d,
                    "CorrectAnswer": correct_answer,
                    "Explanation": explanation,
                }
            )

        if which_quiz == "tests":
            quiz = "الاختبار"
        elif which_quiz == "level_determination":
            quiz = "تقييم_المستوى"
        else:
            quiz = "ليس_محدد"

        datestamp = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H-%M-%S")

        word_filename = os.path.join(user_dir, f"{quiz}_{timestamp}.docx")
        pdf_filename = os.path.join(
            user_dir, f"{quiz}_يوم_{datestamp}_الوقت_{timestamp}.pdf"
        )

        try:
            await generate_word_doc(Q_AND_A_FILE_PATH, word_filename, quiz_data)
        except Exception as e:
            logger.error(f"Error generating Word doc: {e}")
            return None
        try:
            await convert_docx_to_pdf(word_filename, pdf_filename)
        except Exception as e:
            logger.error(f"Error converting to PDF: {e}")
            return None

        # Cleanup the temporary Word file
        if os.path.exists(word_filename):
            os.remove(word_filename)

        return pdf_filename
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_quiz_pdf: {e}")
        return None


async def generate_quiz_video(
    questions, user_id, which_quiz, category_name=None
) -> str:  # Or None if it fails
    """Placeholder function for video generation.  Implement your video logic here."""
    # TODO: Implement actual video generation logic using questions and user_id

    if which_quiz == "tests":
        quiz = "الاختبار"
    elif which_quiz == "level_determination":
        quiz = "تقييم_المستوى"
    else:
        quiz = "ليس_محدد"

    datestamp = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H-%M-%S")
    # For now, return None (video generation not implemented):
    return None
