import logging
import os
from datetime import datetime

from config import Q_AND_A_FILE_PATH
from templateMaker.file_exports import convert_to_pdf, generate_word_doc
from utils import database

logger = logging.getLogger(__name__)


async def generate_quiz_pdf(questions, user_id):
    """
    Generates a PDF quiz with the given questions using a Word template.
    Args:
        questions (list): A list of tuples, each containing question data.
        user_id (int): The ID of the user taking the quiz.
    Returns:
        str: The path to the generated PDF file, or None if an error occurred.
    """
    try:
        # 1. Create the directory structure
        base_dir = "user_tests"
        user_dir = os.path.join(base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        # 2. Prepare the data for the Word template
        quiz_data = []
        for i, question_data in enumerate(questions):
            try:
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
                    *_,  # Ignore unused elements
                ) = question_data
                main_category_name = database.get_data(
                    "SELECT name FROM main_categories WHERE id = ?", (main_category_id,)
                )
                if main_category_name:
                    main_category_name = main_category_name[0][0]
                else:
                    main_category_name = "Unknown Category"  # Or handle it differently

                quiz_data.append(
                    {
                        "QuestionNumber": i + 1,
                        "QuestionText": question_text,
                        "MainCategoryName": main_category_name,
                        "OptionA": option_a,
                        "OptionB": option_b,
                        "OptionC": option_c,
                        "OptionD": option_d,
                        "CorrectAnswer": correct_answer,
                        "Explanation": explanation,
                    }
                )
            except Exception as e:
                logger.error(f"Error processing question data: {e}")
                # Handle the error (e.g., skip the question, log it)
                continue  # Continue to the next question

        # 3. Generate the entire quiz Word document

        datestamp = datetime.now().strftime('%Y-%m-%d')  # Formatted timestamp
        timestamp = datetime.now().strftime('%H-%M-%S')  # Formatted timestamp

        word_filename = os.path.join(user_dir, f"تقييم_المستوى_{timestamp}.docx")
        pdf_filename = os.path.join(user_dir, f"تقييم المستوى يوم {datestamp} الوقت {timestamp}.pdf")

        try:
            await generate_word_doc(Q_AND_A_FILE_PATH, word_filename, quiz_data)
        except Exception as e:
            logger.error(f"Error generating Word doc: {e}")
            return None
        try:
            await convert_to_pdf(word_filename, pdf_filename)
        except Exception as e:
            logger.error(f"Error converting to PDF: {e}")
            return None

        # 5. Cleanup the temporary Word file (optional)
        if os.path.exists(word_filename):
            os.remove(word_filename)

        return pdf_filename
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_quiz_pdf: {e}")
        return None