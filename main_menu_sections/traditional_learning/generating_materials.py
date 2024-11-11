from pathlib import Path
from utils.database import get_data
from template_maker.file_exports import convert_docx_to_pdf, generate_word_doc
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

async def generate_material_pdf(main_category_id, subcategory_id, question_id):
    # Your PDF generation logic here.  Should return the path to the created PDF
    #  For now, just return a dummy path for testing

    template_path = (Path(__file__).parent / '..' / '..' / 'Main Files' / 'Template Files' /'Word' / 'Q&A old.docx').resolve()
    docx_path = (Path(__file__).parent / '..' / '..' / 'temp' / f'{question_id}.docx').resolve()
    pdf_path = (Path(__file__).parent / '..' / '..' / 'temp' / f'{question_id}.pdf').resolve()
    
    try:
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

        print(question_data)
        
        try:
            await generate_word_doc(template_path, docx_path, question_data)
        except Exception as e:
            logger.error(f"Error generating Word doc: {e}")
            return None
        try:
            await convert_docx_to_pdf(docx_path, pdf_path)
        except Exception as e:
            logger.error(f"Error converting to PDF: {e}")
            return None

        # 5. Cleanup the temporary Word file (optional)
        # if os.path.exists(docx_path):
        #     os.remove(docx_path)

        return pdf_path
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_quiz_pdf: {e}")
        return None
    
    return None


def generate_material_video(main_category_id, subcategory_id, question_id):
    """Generates a placeholder video file."""

    # This is a placeholder function - Replace this with your actual video generation logic
    #  For now, we're just returning a dummy path for testing
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

asyncio.run(generate_material_pdf(55, 34, 11))
