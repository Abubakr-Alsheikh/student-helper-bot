from datetime import datetime
from config import POWERPOINT_MAIN_PATH_MATERIAL, WORD_MAIN_PATH_MATERIAL
from template_maker.content_population import find_expression
from utils.category_mangement import get_main_category_name, get_subcategory_name
from utils.database import get_data
from template_maker.file_exports import convert_docx_to_pdf, convert_pptx_to_mp4, generate_main_powerpoint, generate_word_doc
import os
import logging

from utils.user_management import get_user_name, get_user_phone_number

logger = logging.getLogger(__name__)

async def generate_material_pdf(main_category_id, subcategory_id, question_id, user_id):
    """
    Generates a PDF material with a main page containing user info,
    based on the given question.
    """
    try:
        question_data = get_data(
            """
            SELECT question_text, option_a, option_b, option_c, option_d, correct_answer, explanation
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        )

        if not question_data:
            logger.warning(f"No question found with ID: {question_id}")
            return None

        (
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation,
        ) = question_data[0]  # Extract the first tuple

        # Create the directory structure
        base_dir = "user_materials"  # Changed directory name for materials
        user_dir = os.path.join(base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        # Get user data for the main page
        phone_number = await get_user_phone_number(user_id)
        expression_number = find_expression(str(phone_number))
        user_data = {
            "studentName": await get_user_name(user_id),
            "phoneNumber": phone_number,
            "expressionNumber": expression_number,
            "modelNumber": question_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Current date and time
            "materialCategory": await get_main_category_name(main_category_id) if main_category_id else "غير محدد",
            "materialSubcategory": await get_subcategory_name(subcategory_id) if subcategory_id else "غير محدد",
            "questionText": question_text, # Adding question text to the main page
        }

        # --- Create the Main page ---
        timestamp = datetime.now().strftime("%H-%M-%S")
        main_word_filename = os.path.join(
            user_dir, f"material_main_pdf_{question_id}_{timestamp}.docx"
        )
        try:
            await generate_word_doc(WORD_MAIN_PATH_MATERIAL, main_word_filename, user_data)
        except Exception as e:
            logger.error(f"Error generating main Word doc for material: {e}")
            return None

        # --- Convert the main page to PDF ---
        pdf_filename = os.path.join(
            user_dir, f"material_pdf_{question_id}_{timestamp}.pdf"
        )
        try:
            await convert_docx_to_pdf(main_word_filename, pdf_filename)
        except Exception as e:
            logger.error(f"Error converting main material doc to PDF: {e}")
            return None

        # --- Cleanup ---
        os.remove(main_word_filename)

        return pdf_filename
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_material_pdf: {e}")
        return None

async def generate_material_video(main_category_id, subcategory_id, question_id, user_id):
    """Generates a video material with a main page containing user info."""

    try:
        question_data = get_data(
            """
            SELECT question_text, option_a, option_b, option_c, option_d, correct_answer, explanation
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        )

        if not question_data:
            logger.warning(f"No question found with ID: {question_id}")
            return None

        (
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation,
        ) = question_data[0]  # Extract the first tuple

        # Create the directory structure
        base_dir = "user_materials"  # Using the same directory as PDF for consistency
        user_dir = os.path.join(base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        # Get user data for the main page
        phone_number = await get_user_phone_number(user_id)
        expression_number = find_expression(str(phone_number))
        user_data = {
            "studentName": await get_user_name(user_id),
            "phoneNumber": phone_number,
            "expressionNumber": expression_number,
            "modelNumber": question_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Current date and time
            "materialCategory": await get_main_category_name(main_category_id) if main_category_id else "غير محدد",
            "materialSubcategory": await get_subcategory_name(subcategory_id) if subcategory_id else "غير محدد",
            "questionText": question_text, # Adding question text to the main page
        }

        # --- Create the Main page PowerPoint ---
        timestamp = datetime.now().strftime("%H-%M-%S")
        powerpoint_filename = os.path.join(
            user_dir, f"material_main_video_{question_id}_{timestamp}.pptx"
        )

        try:
            await generate_main_powerpoint(POWERPOINT_MAIN_PATH_MATERIAL, powerpoint_filename, user_data)
        except Exception as e:
            logger.error(f"Error generating main PowerPoint for material video: {e}")
            return None

        # --- Convert the main page PowerPoint to MP4 ---
        video_filename = os.path.join(
            user_dir, f"material_video_{question_id}_{timestamp}.mp4"
        )
        try:
            await convert_pptx_to_mp4(powerpoint_filename, video_filename)
        except Exception as e:
            logger.error(f"Error converting main material PowerPoint to video: {e}")
            return None

        # --- Cleanup ---
        if os.path.exists(powerpoint_filename):
            os.remove(powerpoint_filename)

        return video_filename
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_material_video: {e}")
        return None

def generate_material_text(main_category_id, subcategory_id, question_id):
    """Generates text material in HTML format from the database."""

    question_data = get_data(
        """
        SELECT question_text, option_a, option_b, option_c, option_d, correct_answer, explanation
        FROM questions
        WHERE id = ?
        """,
        (question_id,),
    )[0]  # Extract the first tuple

    (
        question_text,
        option_a,
        option_b,
        option_c,
        option_d,
        correct_answer,
        explanation,
    ) = question_data

    # Format the text using HTML for better readability
    # Format text using Telegram Markdown
    plain_text = f"""
السؤال:
{question_text}

الخيارات:
أ. {option_a}
ب. {option_b}
ج. {option_c}
د. {option_d}

الإجابة الصحيحة:{correct_answer}

التفسير:
{explanation}
"""
    return plain_text