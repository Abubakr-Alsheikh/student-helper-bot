import random
import string
from datetime import datetime, timedelta

from utils import database


async def generate_referral_code():
    """Generates a unique 6-character referral code."""
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        user_exists = database.get_data(
            "SELECT 1 FROM users WHERE referral_code = ?", (code,)
        )
        if not user_exists:
            return code


async def user_exists(user_id):
    """Checks if a user exists in the database."""
    user_exists = database.get_data(
        "SELECT 1 FROM users WHERE telegram_id = ?", (user_id,)
    )
    return True if user_exists else False


async def user_exists_by_referral_code(referral_code):
    """Checks if a user exists with the given referral code."""
    user_exists = database.get_data(
        "SELECT 1 FROM users WHERE referral_code = ?", (referral_code,)
    )
    return True if user_exists else False


def get_user_data(user_id: int) -> dict:
    """Retrieves user data from the database."""
    conn = database.create_connection()  # Create connection inside the function
    cursor = conn.cursor()  # Create cursor inside the function
    query = "SELECT * FROM users WHERE telegram_id = ?"
    params = (user_id,)
    cursor.execute(query, params)
    user_data = cursor.fetchall()
    conn.close()  # Close the connection before exiting the function

    if user_data:
        return dict(zip([column[0] for column in cursor.description], user_data[0]))
    else:
        return {}


async def save_user_data(user_data, context, user_id):
    """Saves user data to the SQLite database."""
    referral_code = await generate_referral_code()

    database.execute_query(
        "INSERT INTO users (start_time, name, class, voice_written, taking_qiyas_before, last_score, referral_code, gender, telegram_username, telegram_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            context.user_data["name"],
            context.user_data["class"],
            context.user_data["voice_written"],
            context.user_data["qiyas"],
            context.user_data.get("score", 65),
            referral_code,
            context.user_data["gender"],
            user_data.username,
            user_data.id,
        ),
    )
    user_name, preferred_method, _ = await get_user_for_reminder(user_id)

    # Update scheduler
    await context.application.reminder_manager.schedule_user_reminders(
        user_id, user_name, 1, preferred_method
    )


async def update_user_data(user_id, data):
    """Updates user data in the SQLite database."""
    # Build the SET clause for the UPDATE statement dynamically
    set_clause = ", ".join(f"{key} = ?" for key in data)

    database.execute_query(
        f"UPDATE users SET {set_clause} WHERE telegram_id = ?",
        tuple(data.values()) + (user_id,),
    )
    return True


def calculate_points(time_taken, score, total_questions):
    """Calculates points based on time taken, score, and total questions."""
    # You can adjust the weights and formulas here to fine-tune the points system

    # Points for correctness (e.g., 10 points per correct answer)
    correctness_points = score * 10

    # Points for speed (e.g., bonus points for finishing faster)
    time_bonus = 0
    if time_taken < total_questions * 60:  # Assume 1 minute per question as a baseline
        time_bonus = int(
            (total_questions * 60 - time_taken) / 60
        )  # Award 1 point for every 10 seconds saved

    total_points = correctness_points + time_bonus
    return total_points


def update_user_points(user_id, points_earned):
    """Updates the user's points in the database."""
    # Assuming you have a 'points' column in the 'users' table
    database.execute_query(
        "UPDATE users SET points = points + ? WHERE telegram_id = ?",
        (points_earned, user_id),
    )


def calculate_percentage_expected(score, total_questions):
    """Calculates the expected percentage based on the score and total questions."""
    if total_questions == 0:
        return 0  # Avoid division by zero
    return round((score / total_questions) * 100, 2)  # Round to 2 decimal places


def update_user_percentage_expected(user_id, percentage_expected):
    """Updates the user's expected percentage in the database."""
    database.execute_query(
        "UPDATE users SET percentage_expected = ? WHERE telegram_id = ?",
        (percentage_expected, user_id),
    )


def update_user_usage_time(user_id, duration_seconds):
    """Updates the user's total usage time in the database."""
    conn = database.create_connection()
    cursor = conn.cursor()

    # Retrieve current usage time (if any)
    cursor.execute("SELECT usage_time FROM users WHERE telegram_id = ?", (user_id,))
    current_usage_time_str = cursor.fetchone()[0]

    # Convert current usage time to seconds (if it exists)
    if current_usage_time_str:
        hours, minutes, seconds = map(int, current_usage_time_str.split(":"))
        current_usage_time_seconds = hours * 3600 + minutes * 60 + seconds
    else:
        current_usage_time_seconds = 0

    # Calculate new total usage time in seconds
    new_total_usage_time_seconds = current_usage_time_seconds + duration_seconds

    # Convert new total usage time back to HH:MM:SS format
    hours = int(new_total_usage_time_seconds // 3600)
    minutes = int((new_total_usage_time_seconds % 3600) // 60)
    seconds = int(new_total_usage_time_seconds % 60)
    new_total_usage_time_str = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

    # Update usage time in the database
    cursor.execute(
        "UPDATE users SET usage_time = ? WHERE telegram_id = ?",
        (new_total_usage_time_str, user_id),
    )
    conn.commit()
    conn.close()


def update_user_created_questions(user_id, num_questions_created):
    """Updates the user's total number of created questions in the database."""
    database.execute_query(
        "UPDATE users SET total_number_of_created_questions = total_number_of_created_questions + ? WHERE telegram_id = ?",
        (num_questions_created, user_id),
    )


async def get_user_setting(user_id, setting_name):
    """Retrieves a specific setting for a user."""
    query = f"SELECT {setting_name} FROM users WHERE telegram_id = ?"
    result = database.get_data(query, (user_id,))
    return result[0][0] if result else None  # Return the setting value or None


async def get_user_reminder_times_per_week(user_id):
    """Retrieves a specific setting for a user."""
    query = f"SELECT reminder_times_per_week FROM users WHERE telegram_id = ?"
    result = database.get_data(query, (user_id,))
    return result[0][0] if result else None  # Return the setting value or None


async def get_user_name(user_id):
    """Retrieves a specific setting for a user."""
    query = f"SELECT name FROM users WHERE telegram_id = ?"
    result = database.get_data(query, (user_id,))
    return result[0][0] if result else None  # Return the setting value or None

async def get_user_phone_number(telegram_id):
    """retrieves the student phone number."""
    result = database.get_data(
        "SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)
    )

    if result:
        user_phone = result[0][0]
    else:
        user_phone = "Unknown Phone"

    return user_phone

async def get_user_for_reminder(user_id):
    """Retrieves a specific setting for a user."""
    query = f"SELECT name, voice_written, reminder_times_per_week FROM users WHERE telegram_id = ?"
    result = database.get_data(query, (user_id,))
    user_name = result[0][0]
    preferred_method = "written"
    frequency = result[0][2]
    return user_name, preferred_method, frequency


async def update_user_setting(user_id, setting_name, new_value):
    """Updates a specific setting for a user."""
    query = f"UPDATE users SET {setting_name} = ? WHERE telegram_id = ?"
    database.execute_query(query, (new_value, user_id))


async def update_reminder_frequency(user_id, frequency):
    """Updates the user's reminder frequency in the database."""
    query = "UPDATE users SET reminder_times_per_week = ? WHERE telegram_id = ?"
    database.execute_query(query, (frequency, user_id))


async def get_reminder_frequency(user_id):
    """Gets the user's reminder frequency from the database."""
    query = "SELECT reminder_times_per_week FROM users WHERE telegram_id = ?"
    result = database.get_data(query, (user_id,))
    return result[0][0] if result else 0  # Return 0 if no frequency is set


async def get_all_users_with_reminders():
    """Retrieves all users from the database who have a reminder frequency greater than 0."""
    # query = "SELECT * FROM users WHERE reminder_times_per_week > 0"
    query = "SELECT telegram_id, name, reminder_times_per_week, voice_written FROM users WHERE reminder_times_per_week > 0"
    result = database.get_data(query)
    return result
