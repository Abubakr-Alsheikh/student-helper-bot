import logging
import os
from datetime import datetime
import platform

from config import POWERPOINT_MAIN_PATH, Q_AND_A_FILE_PATH, Q_AND_A_FILE_PATH_POWERPOINT, WORD_MAIN_PATH
from template_maker.file_exports import (
    convert_docx_to_pdf,
    convert_pptx_to_mp4,
    generate_powerpoint,
    generate_word_doc,
    merge_word_documents,
)
from utils import database

logger = logging.getLogger(__name__)


async def generate_quiz_pdf(
    questions, user_id, which_quiz, quiz_timestamp, quiz_number, user_data, category_name=None
) -> str:
    """
    Generates a PDF quiz with the given questions using a Word template.
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

        # Use the test timestamp instead of current date
        try:
            # Parse the timestamp to extract date and time
            timestamp_obj = datetime.strptime(quiz_timestamp, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            # Fallback to parsing without microseconds
            timestamp_obj = datetime.strptime(quiz_timestamp, "%Y-%m-%d %H:%M:%S")

        datestamp = timestamp_obj.strftime("%Y-%m-%d")
        timestamp = timestamp_obj.strftime("%H-%M-%S")

        # --- Create the Main page ---
        main_word_filename = os.path.join(
            user_dir, f"main_{quiz_number}_{timestamp}.docx"
        )
        await generate_word_doc(WORD_MAIN_PATH, main_word_filename, user_data)

        # --- Create the Q\&A page ---
        q_and_a_word_filename = os.path.join(
            user_dir, f"q_and_a_{quiz_number}_{timestamp}.docx"
        )
        quiz_data = {"questions": quiz_data}  # Wrap in a dictionary as before
        await generate_word_doc(Q_AND_A_FILE_PATH, q_and_a_word_filename, quiz_data)

        # --- Merge the documents ---
        merged_word_filename = os.path.join(
            user_dir, f"{quiz_number}_رقم_{quiz}_{timestamp}.docx"
        )
        await merge_word_documents(
            main_word_filename, q_and_a_word_filename, merged_word_filename
        )

        # --- Convert to PDF ---
        pdf_filename = os.path.join(
            user_dir, f"{quiz}_رقم_{quiz_number}_يوم_{datestamp}_الوقت_{timestamp}.pdf"
        )

        try:
            await convert_docx_to_pdf(merged_word_filename, pdf_filename)
        except Exception as e:
            logger.error(f"Error converting to PDF: {e}")
            return None

        # --- Cleanup ---
        os.remove(main_word_filename)
        os.remove(q_and_a_word_filename)
        os.remove(merged_word_filename)  # Remove the merged Word file

        return pdf_filename
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_quiz_pdf: {e}")
        return None


async def generate_quiz_video(
    questions, user_id, which_quiz, quiz_timestamp, quiz_number, user_data, category_name=None
) -> str:  # Or None if it fails
    """Placeholder function for video generation."""

    try:
        base_dir = "user_tests"
        user_dir = os.path.join(base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)  # Create if it doesn't exist

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

        # Use the test timestamp instead of current date
        try:
            # Parse the timestamp to extract date and time
            timestamp_obj = datetime.strptime(quiz_timestamp, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            # Fallback to parsing without microseconds
            timestamp_obj = datetime.strptime(quiz_timestamp, "%Y-%m-%d %H:%M:%S")

        datestamp = timestamp_obj.strftime("%Y-%m-%d")
        timestamp = timestamp_obj.strftime("%H-%M-%S")

        powerpoint_filename = os.path.join(
            user_dir, f"{quiz_number}_رقم_{quiz}_{timestamp}.pptx"
        )

        video_filename = os.path.join(
            user_dir, f"{quiz}_رقم_{quiz_number}_يوم_{datestamp}_الوقت_{timestamp}.mp4"
        )

        quiz_data = {"questions": quiz_data}

        try:
            await generate_powerpoint(
                POWERPOINT_MAIN_PATH, Q_AND_A_FILE_PATH_POWERPOINT, powerpoint_filename, quiz_data, user_data
            )
        except Exception as e:
            logger.error(f"Error generating PowerPoint: {e}")
            return None

        try:
            await convert_pptx_to_mp4(powerpoint_filename, video_filename)
        except Exception as e:
            logger.error(f"Error converting to Video: {e}")
            return None

        # Cleanup the temporary Word file
        if os.path.exists(powerpoint_filename):
            os.remove(powerpoint_filename)

        return video_filename
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_quiz_video: {e}")
        return None
