import os
import sqlite3
import pandas as pd

from config import DATABASE_FILE, EXCEL_FILE_BASHAR, VERBAL_FILE
from utils import database


def generate_questions_with_categories():
    # Check if data already exists in the table
    count = database.get_data("SELECT COUNT(*) FROM questions")
    print(count)
    if count[0][0] == 0:  # If the table is empty, populate it from Excel
        df = pd.read_excel(
            EXCEL_FILE_BASHAR,
            usecols=[
                "الجواب الصحيح",
                "نص السؤال مدقق",
                "الخيار أ مدقق",
                "الخيار ب مدقق",
                "الخيار ج مدقق",
                "الخيار د مدقق",
                "الشرح مدقق",
                "التصنيف الرئيسي مدقق",
                "التصنيفات الفرعية مدققة",
            ],
        )

        for _, row in df.iterrows():
            main_category = row["التصنيف الرئيسي مدقق"]
            subcategories = row["التصنيفات الفرعية مدققة"].split("،")

            # Get or create main category ID
            database.execute_query(
                "INSERT OR IGNORE INTO main_categories (name) VALUES (?)",
                (main_category,),
            )
            main_category_id = database.get_data(
                "SELECT id FROM main_categories WHERE name = ?", (main_category,)
            )[0][0]

            # Link main category to subcategories
            for subcategory in subcategories:
                subcategory = subcategory.strip()
                database.execute_query(
                    "INSERT OR IGNORE INTO subcategories (name) VALUES (?)",
                    (subcategory,),
                )
                subcategory_id = database.get_data(
                    "SELECT id FROM subcategories WHERE name = ?", (subcategory,)
                )[0][0]
                database.execute_query(
                    "INSERT OR IGNORE INTO main_sub_links (main_category_id, subcategory_id) VALUES (?, ?)",
                    (main_category_id, subcategory_id),
                )

            # Now insert the question with the main_category_id
            database.execute_query(
                """
                INSERT INTO questions (correct_answer, question_text, option_a, option_b, option_c, option_d, explanation, main_category_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(row["الجواب الصحيح"]),
                    str(row["نص السؤال مدقق"]),
                    str(row["الخيار أ مدقق"]),
                    str(row["الخيار ب مدقق"]),
                    str(row["الخيار ج مدقق"]),
                    str(row["الخيار د مدقق"]),
                    str(row["الشرح مدقق"]),
                    main_category_id,
                ),
            )


def generate_verbal_questions():
    """Adds verbal questions to the database from an Excel file.

    Args:
        excel_file (str): The path to the Excel file.
    """
    df = pd.read_excel(
        VERBAL_FILE,
        usecols=[
            "الجواب الصحيح",
            "نص السؤال",
            "الخيار أ",
            "الخيار ب",
            "الخيار ج",
            "الخيار د",
            "الشرح",
            "التصنيف الرئيسي",
            "القطعة",
        ],
    )

    for _, row in df.iterrows():
        main_category = row["التصنيف الرئيسي"]
        question_type = "verbal"
        if str(main_category).lower() == "nan":
            continue
        # Get the main category ID (create if it doesn't exist)
        database.execute_query(
            "INSERT OR IGNORE INTO main_categories (name) VALUES (?)",
            (main_category,),
        )
        main_category_id = database.get_data(
            "SELECT id FROM main_categories WHERE name = ?", (main_category,)
        )[0][0]

        # Insert the verbal question
        database.execute_query(
            """
            INSERT INTO questions (correct_answer, question_text, option_a, option_b, 
                                    option_c, option_d, explanation, main_category_id, 
                                    image_path, question_type, passage_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(row["الجواب الصحيح"]),
                str(row["نص السؤال"]),
                str(row["الخيار أ"]),
                str(row["الخيار ب"]),
                str(row["الخيار ج"]),
                str(row["الخيار د"]),
                str(row["الشرح"]),
                main_category_id,
                None,
                question_type,
                str(row["القطعة"]),
            ),
        )


def get_passage_content(context_folder, passage_name):
    """Fetches the passage content based on the passage_name."""
    if passage_name and passage_name != "N/A":
        file_path = os.path.join(context_folder, f"{passage_name}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read().strip()
    return ""


def generate_questions():
    # Check if data already exists in the table
    count = database.get_data("SELECT COUNT(*) FROM questions")
    if count[0][0] == 0:  # If the table is empty, populate it from Excel
        df = pd.read_excel(
            EXCEL_FILE_BASHAR,
            usecols=[
                "الجواب الصحيح",
                "نص السؤال مدقق",
                "الخيار أ مدقق",
                "الخيار ب مدقق",
                "الخيار ج مدقق",
                "الخيار د مدقق",
                "الشرح مدقق",
            ],
        )  # Specify the columns you want to read

        for _, row in df.iterrows():
            database.execute_query(
                """
                INSERT INTO questions (correct_answer, question_text, option_a, option_b, option_c, option_d, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    row["الجواب الصحيح"],
                    row["نص السؤال مدقق"],
                    row["الخيار أ مدقق"],
                    row["الخيار ب مدقق"],
                    row["الخيار ج مدقق"],
                    row["الخيار د مدقق"],
                    row["الشرح مدقق"],
                ),
            )


def get_random_questions(num_questions, question_type):
    """Retrieves a specified number of random questions from the database."""
    # Step 1: Retrieve a random set of questions
    questions = database.get_data(
        """
        SELECT * FROM questions 
        WHERE question_type = ?
        ORDER BY RANDOM() 
        LIMIT ?
        """,
        (question_type, num_questions),
    )
    # Step 2: Group questions by passage name
    grouped_questions = sorted(
        questions, key=lambda x: x[11]
    )  # Sort by passage_name index
    return grouped_questions


def get_questions_by_category(category_id, num_questions, category_type, question_type):
    """Retrieves random questions of a specific type from the specified category.

    Args:
        category_id (int): The ID of the category.
        num_questions (int): The number of questions to retrieve.
        category_type (str): 'main_category_id' or 'sub_category_id'.
        question_type (str): 'verbal' or 'quantitative'.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    if category_type == "main_category_id":
        cursor.execute(
            """
            SELECT * FROM questions
            WHERE main_category_id = ? AND question_type = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (category_id, question_type, num_questions),
        )
    elif category_type == "sub_category_id":
        cursor.execute(
            """
            SELECT q.* FROM questions q
            JOIN main_sub_links msl ON q.main_category_id = msl.main_category_id
            WHERE msl.subcategory_id = ? AND q.question_type = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (category_id, question_type, num_questions),
        )
    else:
        raise ValueError(
            "Invalid category_type. Must be 'main_category_id' or 'sub_category_id'."
        )

    questions = cursor.fetchall()
    conn.close()
    return questions


def connect_db():
    return sqlite3.connect(DATABASE_FILE)


def get_random_question():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 1")
        question_data = cursor.fetchone()

    if question_data:
        column_names = [description[0] for description in cursor.description]
        return dict(zip(column_names, question_data))
    else:
        return None


def get_question_by_id(question_id):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
        question_data = cursor.fetchone()

    if question_data:
        column_names = [description[0] for description in cursor.description]
        return dict(zip(column_names, question_data))
    else:
        return None


def update_learning_progress(user_id, question_id, answered_correctly):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO learning_progress (user_id, question_id, answered_correctly)
            VALUES (?, ?, ?)
        """,
            (user_id, question_id, answered_correctly),
        )
        conn.commit()


def format_question_for_chatgpt(question_data):
    return (
        f"Question: {question_data['question_text']}\n"
        f"A: {question_data['option_a']}\n"
        f"B: {question_data['option_b']}\n"
        f"C: {question_data['option_c']}\n"
        f"D: {question_data['option_d']}\n"
    )


def format_question_for_user(question_data):
    return (
        f"{question_data['question_text']}\n\n"
        f"أ: {question_data['option_a']}\n"
        f"ب: {question_data['option_b']}\n"
        f"ج: {question_data['option_c']}\n"
        f"د: {question_data['option_d']}"
    )


def get_user_questions_for_review(user_id):
    """Retrieves questions the user has answered for review."""
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT q.question_text, q.correct_answer, lp.answered_correctly
            FROM questions q
            JOIN learning_progress lp ON q.id = lp.question_id
            WHERE lp.user_id = ?
        """,
            (user_id,),
        )
        return cursor.fetchall()
