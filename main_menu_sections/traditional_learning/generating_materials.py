
from utils.database import get_data

def generate_material_pdf(main_category_id, subcategory_id, question_id):
     # Your PDF generation logic here.  Should return the path to the created PDF
     #  For now, just return a dummy path for testing
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