import asyncio
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

from config import CONTEXT_DIRECTORY, UNDER_DEVLOPING_MESSAGE
from handlers.main_menu_handler import main_menu_handler
from handlers.personal_assistant_chat_handler import chatgpt, SYSTEM_MESSAGE
from main_menu_sections.tests.pdf_generator import generate_quiz_pdf
from utils import database
from utils.question_management import get_passage_content, get_questions_by_category
from utils.subscription_management import check_subscription
from utils.user_management import (
    calculate_points,
    update_user_created_questions,
    update_user_points,
    update_user_usage_time,
)

# Configure logging
logger = logging.getLogger(__name__)

# States for the conversation
(
    CHOOSE_QUIZ_TYPE,
    CHOOSE_CATEGORY_TYPE,
    CHOOSE_MAIN_CATEGORY,
    CHOOSE_SUB_CATEGORY,
    CHOOSE_INPUT_TYPE,
    GET_NUMBER_OF_QUESTIONS,
    GET_TIME_LIMIT,
    ANSWER_QUESTIONS,
) = range(8)

CATEGORIES_PER_PAGE = 10
CHATTING = 0


async def handle_tests(update: Update, context: CallbackContext):
    """Handles the 'الاختبارات' option and displays its sub-menu."""

    if not await check_subscription(update, context):
        return
    context.user_data["current_section"] = "tests"  # Set user context
    keyboard = [
        [
            InlineKeyboardButton(
                "بدء اختبار جديد 📝", callback_data="handle_start_new_test"
            )
        ],
        [
            InlineKeyboardButton(
                "قائمة الاختبارات السابقة 📜",
                callback_data="handle_list_previous_tests",
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    await update.callback_query.edit_message_text(
        "الاختبارات 📚", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_start_new_test(update: Update, context: CallbackContext):
    """Handles the 'بدء اختبار جديد' sub-option, now with quiz type choice."""

    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("لفظي 🗣️", callback_data="quiz_type:verbal")],
        [InlineKeyboardButton("كمي 🔢", callback_data="quiz_type:quantitative")],
    ]
    keyboard.append([InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="tests")])
    await update.callback_query.edit_message_text(
        "اختر نوع الاختبار:", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_QUIZ_TYPE  # Start at the quiz type selection state


async def handle_quiz_type_choice(update: Update, context: CallbackContext):
    """Handles the user's choice of quiz type."""
    query = update.callback_query
    await query.answer()
    _, quiz_type = query.data.split(":")
    context.user_data["quiz_type"] = quiz_type

    if quiz_type == "quantitative":
        await query.message.reply_text(UNDER_DEVLOPING_MESSAGE)
        return  # Stop further processing for quantitative

    keyboard = []
    if quiz_type == "quantitative":  # Only show subcategories for Quantitative
        keyboard.append(
            [InlineKeyboardButton("التصنيف الرئيسي 🗂️", callback_data="main_category")]
        )
        keyboard.append(
            [InlineKeyboardButton("التصنيف الفرعي 🗂️", callback_data="sub_category")]
        )
    else:  # Assume "verbal"
        keyboard.append(
            [InlineKeyboardButton("التصنيف الرئيسي 🗂️", callback_data="main_category")]
        )  # Only Main Category

    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="handle_start_new_test")]
    )
    await update.callback_query.edit_message_text(
        "اختر نوع التصنيف: 🧐", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_CATEGORY_TYPE


async def handle_category_type_choice(update: Update, context: CallbackContext):
    """Handles the user's choice of main or sub category."""
    query = update.callback_query
    await query.answer()
    category_type = query.data

    context.user_data["category_type"] = category_type

    if category_type == "main_category":
        await handle_show_main_categories(update, context, 1)
        return CHOOSE_MAIN_CATEGORY
    elif category_type == "sub_category":
        await handle_show_subcategories(update, context, 1)
        return CHOOSE_SUB_CATEGORY
    else:
        logger.error(f"Invalid category type: {category_type}")
        await query.message.reply_text(
            "حدث خطأ أثناء اختيار نوع التصنيف، يرجى المحاولة مرة أخرى."
        )
        return ConversationHandler.END


async def handle_show_main_categories(
    update: Update, context: CallbackContext, page: int
):
    """Displays a paginated list of main categories."""
    try:
        quiz_type = context.user_data.get("quiz_type", "quantitative")

        main_categories = database.get_data(
            """
            SELECT DISTINCT mc.id, mc.name 
            FROM main_categories mc
            JOIN questions q ON mc.id = q.main_category_id
            WHERE q.question_type = ?
            LIMIT ? OFFSET ?
            """,
            (quiz_type, CATEGORIES_PER_PAGE, (page - 1) * CATEGORIES_PER_PAGE),
        )

        # Get the total count for pagination
        total_categories = database.get_data(
            """
            SELECT COUNT(DISTINCT mc.id)
            FROM main_categories mc
            JOIN questions q ON mc.id = q.main_category_id
            WHERE q.question_type = ?
            """,
            (quiz_type,),
        )[0][0]

        total_pages = (
            total_categories + CATEGORIES_PER_PAGE - 1
        ) // CATEGORIES_PER_PAGE

        keyboard = []
        for category_id, category_name in main_categories:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        category_name, callback_data=f"main_category_id:{category_id}"
                    )
                ]
            )

        # Pagination buttons
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    "السابق ⏪", callback_data=f"main_category_page:{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    "التالي ⏩", callback_data=f"main_category_page:{page + 1}"
                )
            )
        if pagination_buttons:
            keyboard.append(pagination_buttons)

        keyboard.append(
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙",
                    callback_data=f"quiz_type:{context.user_data.get('quiz_type', 'quantitative')}",
                )
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            f"اختر التصنيف الرئيسي (الصفحة {page} من {total_pages}):",
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        if str(e) == "Message is not modified":
            await update.callback_query.answer("انت في نفس الصفحة.")
        else:
            logger.error(f"Error in handle_show_main_categories: {e}")
            await update.callback_query.message.reply_text(
                "حدث خطأ أثناء عرض التصنيفات الرئيسية."
            )


async def handle_show_subcategories(
    update: Update, context: CallbackContext, page: int
):
    """Displays a paginated list of subcategories."""
    try:
        subcategories = database.get_data(
            "SELECT id, name FROM subcategories LIMIT ? OFFSET ?",
            (CATEGORIES_PER_PAGE, (page - 1) * CATEGORIES_PER_PAGE),
        )

        total_categories = database.get_data("SELECT COUNT(*) FROM subcategories")[0][0]
        total_pages = (
            total_categories + CATEGORIES_PER_PAGE - 1
        ) // CATEGORIES_PER_PAGE

        keyboard = []
        for category_id, category_name in subcategories:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        category_name, callback_data=f"sub_category_id:{category_id}"
                    )
                ]
            )

        # Pagination buttons
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    "السابق ⏪", callback_data=f"subcategory_page:{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    "التالي ⏩", callback_data=f"subcategory_page:{page + 1}"
                )
            )
        if pagination_buttons:
            keyboard.append(pagination_buttons)

        keyboard.append(
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙",
                    callback_data=f"quiz_type:{context.user_data.get('quiz_type', 'quantitative')}",
                )
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            f"اختر التصنيف الفرعي (الصفحة {page} من {total_pages}):",
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        if str(e) == "Message is not modified":
            await update.callback_query.answer("You're already on this page.")
        else:
            logger.error(f"Error in handle_show_subcategories: {e}")
            await update.callback_query.message.reply_text(
                "حدث خطأ أثناء عرض التصنيفات الفرعية."
            )


async def handle_category_choice(update: Update, context: CallbackContext):
    """Handles the user's choice of category and proceeds to question limit selection."""
    query = update.callback_query
    await query.answer()
    try:
        category_type, category_id = query.data.split(":")
        category_id = int(category_id)

        context.user_data["category_id"] = category_id
        context.user_data["category_type"] = category_type

        # Initiate test with the question/time limit selection:
        keyboard = [
            [
                InlineKeyboardButton(
                    "عدد الأسئلة 🔢", callback_data="number_of_questions"
                )
            ],
            [InlineKeyboardButton("الوقت المتاح ⏱️", callback_data="time_limit")],
            [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data=category_type[:-3])],
        ]
        await update.callback_query.edit_message_text(
            "هل تريدنا أن نقدم لك الاختبار عن طريق سؤالك عددًا معينًا من الأسئلة، أم عن طريق إعطائك اختبارا بمدة زمنية معينة؟ 🤔",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CHOOSE_INPUT_TYPE
    except (ValueError, IndexError) as e:
        logger.error(
            f"Error extracting category_type and category_id from {query.data}: {e}"
        )
        await update.callback_query.message.reply_text(
            "حدث خطأ أثناء اختيار التصنيف، يرجى المحاولة مرة أخرى."
        )
        return ConversationHandler.END


async def handle_number_of_questions_choice(update: Update, context: CallbackContext):
    """Handles the choice of specifying the number of questions."""
    await update.callback_query.edit_message_text(
        "كم عدد الأسئلة التي ترغب في الإجابة عليها؟ ✍️"
    )
    return GET_NUMBER_OF_QUESTIONS


async def handle_time_limit_choice(update: Update, context: CallbackContext):
    """Handles the choice of specifying the time limit."""
    await update.callback_query.edit_message_text("كم دقيقة لديك متاحة للاختبار؟ ⏳")
    return GET_TIME_LIMIT


async def handle_number_of_questions_input(update: Update, context: CallbackContext):
    """Handles the user input for the number of questions."""
    try:
        num_questions = int(update.message.text)
        if num_questions < 10 or num_questions > 100:
            await update.message.reply_text("الرجاء إدخال عدد أسئلة بين 10 و 100. ⚠️")
            return GET_NUMBER_OF_QUESTIONS

        context.user_data["end_time"] = datetime.now() + timedelta(
            minutes=num_questions * 1.5
        )
        context.user_data["num_questions"] = num_questions
        await start_quiz(update, context)
        return ANSWER_QUESTIONS

    except ValueError:
        await update.message.reply_text(
            "الرجاء إدخال عدد صحيح. اكتب الرقم واضغط على إرسال. ✏️"
        )
        return GET_NUMBER_OF_QUESTIONS
    except Exception as e:
        logger.error(f"Error in input handler: {e}")
        await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى. ⚠️")
        return GET_NUMBER_OF_QUESTIONS


async def handle_time_limit_input(update: Update, context: CallbackContext):
    """Handles the user input for the time limit."""
    try:
        time_limit = int(update.message.text)
        if time_limit <= 0:
            await update.message.reply_text("الرجاء إدخال وقت صحيح أكبر من 0. ⚠️")
            return GET_TIME_LIMIT

        context.user_data["end_time"] = datetime.now() + timedelta(minutes=time_limit)
        num_questions = int(time_limit / 1.2)
        context.user_data["num_questions"] = num_questions
        await start_quiz(update, context)
        return ANSWER_QUESTIONS

    except ValueError:
        await update.message.reply_text(
            "الرجاء إدخال عدد صحيح. اكتب الرقم واضغط على إرسال. ✏️"
        )
        return GET_TIME_LIMIT
    except Exception as e:
        logger.error(f"Error in input handler: {e}")
        await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى. ⚠️")
        return GET_TIME_LIMIT


async def start_quiz(update: Update, context: CallbackContext):
    """Starts the quiz, generates PDF, and sends the first question."""
    try:
        user_id = update.effective_user.id
        num_questions = context.user_data["num_questions"]
        category_id = context.user_data["category_id"]
        category_type = context.user_data["category_type"]

        # Retrieve questions based on category type (main or sub)
        questions = get_questions_by_category(
            category_id, num_questions, category_type, context.user_data["quiz_type"]
        )
        if not questions:
            logger.error(
                f"No questions found for category_id: {category_id}, category_type: {category_type}, quiz_type: {context.user_data['quiz_type']}"
            )
            await update.message.reply_text(
                "حدث خطأ أثناء تحميل الأسئلة. يرجى المحاولة مرة أخرى لاحقًا. ⚠️"
            )
            return ConversationHandler.END

        context.user_data["questions"] = questions
        context.user_data["current_question"] = 0
        context.user_data["score"] = 0
        context.user_data["start_time"] = datetime.now()

        # Create a new entry in the previous_tests table using database function
        previous_test_id = database.execute_query_return_id(
            """
            INSERT INTO previous_tests (user_id, timestamp, num_questions, score, time_taken, pdf_path) 
            VALUES (?, ?, ?, 0, 0, '')
            """,
            (user_id, str(datetime.now()), num_questions),
        )

        context.user_data["previous_test_id"] = previous_test_id  # Store in user_data

        await update.message.reply_text(
            "سيتم بدأ الاختبار 🏁.\n"
            "علما بأنه سيتم توضيح وشرح جميع الأسئلة لك خطوة بخطوة في نهاية الاختبار. 💡"
        )

        # Countdown
        for i in range(3, 0, -1):
            await asyncio.sleep(1)
            await update.message.reply_text(f"{i}...")

        # Send the first question
        await send_question(update, context)
    except Exception as e:
        logger.error(f"Error in start_quiz: {e}")
        await update.message.reply_text(
            "حدث خطأ أثناء بدء الاختبار، يرجى المحاولة مرة أخرى."
        )
        return ConversationHandler.END


async def send_question(update: Update, context: CallbackContext):
    """Sends the current question to the user with randomized answer order."""
    questions = context.user_data["questions"]
    current_question_index = context.user_data["current_question"]

    if current_question_index < len(questions):
        question_data = questions[current_question_index]
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
        ) = question_data
        passage_content = ""
        if passage_name != "-":
            passage_content = get_passage_content(CONTEXT_DIRECTORY, passage_name)

        passage_text = f"النص: {passage_content}\n\n" if passage_content else ""
        # Create a list of answer options and shuffle them
        answer_options = [
            (f"أ. {option_a}", f"answer_{question_id}_أ"),
            (f"ب. {option_b}", f"answer_{question_id}_ب"),
            (f"ج. {option_c}", f"answer_{question_id}_ج"),
            (f"د. {option_d}", f"answer_{question_id}_د"),
        ]
        random.shuffle(answer_options)

        # Create the keyboard with shuffled options
        keyboard = []
        for i in range(0, len(answer_options), 2):  # Create rows of 2 buttons
            row = [
                InlineKeyboardButton(text, callback_data=data)
                for text, data in answer_options[i : i + 2]
            ]
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if current_question_index == 0:
                await update.effective_message.reply_text(
                    f"{passage_text}" f"*{current_question_index+1}.* {question_text}",
                    reply_markup=reply_markup,
                )
            else:
                await update.effective_message.edit_text(
                    f"{passage_text}" f"*{current_question_index+1}.* {question_text}",
                    reply_markup=reply_markup,
                )
        except Exception as e:
            logger.error(f"Error sending question: {e}")
            await update.effective_message.reply_text(
                "حدث خطأ أثناء إرسال السؤال، يرجى المحاولة مرة أخرى."
            )
    else:
        await end_quiz(update, context)
        await handle_final_step(update, context)
        return ConversationHandler.END


async def handle_answer(update: Update, context: CallbackContext):
    """Handles answer button presses, checks answers, and sends the next question."""
    # Check if time limit is reached
    if (
        "end_time" in context.user_data
        and datetime.now() > context.user_data["end_time"]
    ):
        await end_quiz(update, context)
        await handle_final_step(update, context)
        return

    query = update.callback_query
    user_id = update.effective_user.id

    try:
        _, question_id, user_answer = query.data.split("_")
        question_id = int(question_id)
    except (ValueError, IndexError) as e:
        logger.error(f"Error extracting data from query: {query.data}, {e}")
        await update.effective_message.reply_text(
            "حدث خطأ أثناء معالجة إجابتك، يرجى المحاولة مرة أخرى."
        )
        return

    # Get the question data
    questions = context.user_data["questions"]
    current_question_index = context.user_data["current_question"]
    question_data = questions[current_question_index]
    question_text = question_data[2]
    max_question_length = 100
    truncated_question_text = (
        question_text[:max_question_length] + "..."
        if len(question_text) > max_question_length
        else question_text
    )
    correct_answer = question_data[1]
    is_correct = user_answer.upper() == correct_answer.upper()

    previous_test_id = context.user_data["previous_test_id"]

    # Record the answer, including the previous_test_id
    await record_user_answer(
        user_id,
        question_id,
        user_answer,
        is_correct,
        previous_test_id,
    )


    if is_correct:
        context.user_data["score"] += 1
        correct_option_text = get_option_text(question_data, correct_answer)

        await query.answer(
            text=f"إجابة صحيحة! ✅ \n"
            f"السؤال: {truncated_question_text} \n"
            f"الإجابة الصحيحة: {correct_option_text}",
            show_alert=True,
        )
    else:
        correct_option_text = get_option_text(question_data, correct_answer)
        user_answer_text = get_option_text(question_data, user_answer)

        await query.answer(
            text=f"إجابة خاطئة ❌ \n"
            f"السؤال: {truncated_question_text} \n"
            f"إجابتك: {user_answer_text} \n"
            f"الإجابة الصحيحة: {correct_option_text}",
            show_alert=True,
        )

    # Move to the next question
    context.user_data["current_question"] += 1
    await send_question(update, context)


async def record_user_answer(
    user_id: int,
    question_id: int,
    user_answer: str,
    is_correct: bool,
    previous_test_id: int,
):
    """Records the user's answer to a question."""
    try:
        database.execute_query(
            """
            INSERT INTO user_answers (user_id, question_id, user_answer, is_correct, previous_tests_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, question_id, user_answer, is_correct, previous_test_id),
        )
    except Exception as e:
        logger.error(
            f"Error recording user answer for user_id: {user_id}, question_id: {question_id}, previous_test_id: {previous_test_id}: {e}"
        )


def get_option_text(question_data: Tuple, correct_answer: str) -> str:
    """Helper function to get the text of the correct option."""
    if correct_answer == "أ":
        return question_data[3]  # option_a
    elif correct_answer == "ب":
        return question_data[4]  # option_b
    elif correct_answer == "ج":
        return question_data[5]  # option_c
    elif correct_answer == "د":
        return question_data[6]  # option_d
    else:
        return "غير محدد"


async def end_quiz(update: Update, context: CallbackContext):
    """Calculates the score and ends the quiz."""
    try:
        end_time = datetime.now()
        start_time = context.user_data["start_time"]
        total_time = (end_time - start_time).total_seconds()  # Time in seconds
        score = context.user_data["score"]
        total_questions = len(context.user_data["questions"])

        questions = context.user_data["questions"]
        user_id = update.effective_user.id
        previous_test_id = context.user_data["previous_test_id"]

        # Update user's total usage time in the database
        update_user_usage_time(user_id, total_time)

        # Update user's total created questions in the database
        update_user_created_questions(user_id, total_questions)

        # Calculate and award points
        points_earned = calculate_points(total_time, score, total_questions)
        update_user_points(user_id, points_earned)

        if (
            "end_time" in context.user_data
            and datetime.now() > context.user_data["end_time"]
        ):
            await update.effective_message.reply_text("لقد انتهى وقتك. ⏱️")

        await update.effective_message.edit_text(
            f"انتهت الأسئلة! 🎉\n"
            f"لقد ربحت {points_earned} نقطة! 🏆\n"
            f"لقد حصلت على {score} من {total_questions} 👏\n"
            f"لقد استغرقت {int(total_time // 60)} دقيقة و{int(total_time % 60)} ثانية. ⏱️"
        )
        await update.effective_message.reply_text(
            "انتظر قليلا جاري إنشاء ملف pdf... 📄"
        )

        category_id = context.user_data["category_id"]
        category_type = context.user_data["category_type"]

        if category_type == "main_category_id":
            category_name = database.get_data(
                "SELECT name FROM main_categories WHERE id = ?", (category_id,)
            )[0][
                0
            ]  # Access the first element of the tuple and then the first element of the list
        elif category_type == "sub_category_id":
            category_name = database.get_data(
                "SELECT name FROM subcategories WHERE id = ?", (category_id,)
            )[0][
                0
            ]  # Access the first element of the tuple and then the first element of the list
        else:
            logger.error(f"Invalid category_type: {category_type}")
            category_name = "غير محدد"

        pdf_filepath = await generate_quiz_pdf(questions, user_id, category_name)

        if pdf_filepath is None:  # Check if PDF generation failed
            await update.effective_message.reply_text("حدث خطأ أثناء إنشاء ملف PDF. ⚠️")

        try:
            # Update the previous_tests entry using database function
            database.execute_query(
                """
                UPDATE previous_tests
                SET score = ?, time_taken = ?, pdf_path = ?
                WHERE id = ?
                """,
                (score, total_time, pdf_filepath, previous_test_id),
            )

        except Exception as e:
            logger.error(f"Error updating level determination in database: {e}")
        
        # Check if pdf_filepath is valid before trying to open it
        if pdf_filepath and os.path.exists(pdf_filepath):
            with open(pdf_filepath, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=f
                )
        else:
            logger.error("PDF file path is None or file does not exist.")
            await update.effective_message.reply_text("تعذر العثور على ملف PDF. ⚠️")

        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in end_quiz: {e}")
        await update.effective_message.reply_text(
            "حدث خطأ أثناء إنهاء الاختبار، يرجى المحاولة مرة أخرى."
        )

async def store_test_data(
    update: Update, context: CallbackContext, total_time: float, score: int
):
    """Stores the test data in the database."""
    user_id = update.effective_user.id
    num_questions = context.user_data["num_questions"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_number = len(os.listdir(f"user_tests/{user_id}")) + 1

    filepath = f"user_tests/{user_id}/{test_number}_{timestamp}.pdf"
    answers_path = f"user_tests/{user_id}/{test_number}_{timestamp}.txt"
    try:
        database.execute_query(
            """
            INSERT INTO previous_tests (user_id, timestamp, num_questions, score, time_taken, pdf_path, answers_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                timestamp,
                num_questions,
                score,
                total_time,
                filepath,
                answers_path,
            ),
        )
    except Exception as e:
        logger.error(
            f"Error storing test data for user_id: {user_id}, test_number: {test_number}: {e}"
        )


async def handle_final_step(update: Update, context: CallbackContext):
    """Handles the final step (asking about AI assistance)."""
    keyboard = [
        [
            InlineKeyboardButton("نعم 👍", callback_data="ai_assistance_yes"),
            InlineKeyboardButton("لا 👎", callback_data="ai_assistance_no"),
        ]
    ]
    await update.effective_message.reply_text(
        "هل تريد استفسار عن أي سؤال بواسطة الذكاء الاصطناعي؟ 🤖",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_ai_assistance_no(update: Update, context: CallbackContext):
    """Handles the 'no' choice for AI assistance."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("شكرًا لك. يمكنك العودة للقائمة الرئيسية. 🏡")
    await main_menu_handler(query, context)
    return ConversationHandler.END


async def handle_ai_assistance_yes(update: Update, context: CallbackContext):
    """Handles the 'yes' choice for AI assistance."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "تفضل، كيف يمكنني مساعدتك في أسئلة الاختبار؟ 💬"
    )

    # Start AI assistance chat
    user_id = update.effective_user.id
    messages = await chatgpt.get_chat_history(user_id)
    context.user_data["messages"] = messages

    return CHATTING


async def chat(update: Update, context: CallbackContext) -> int:
    user_message = update.message.text

    assistant_response = await chatgpt.chat_with_assistant(
        update.effective_user.id,
        user_message,
        update,
        context,
        system_message=SYSTEM_MESSAGE,
    )

    if assistant_response == -1:
        return ConversationHandler.END

    if assistant_response:
        return CHATTING
    else:
        await update.message.reply_text(
            "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقًا. ⚠️"
        )
        return ConversationHandler.END


async def end_chat(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "شكرا لك على الدردشة معي. إذا احتجت إلى مساعدة مرة أخرى، فقط ابدأ دردشة جديدة! 💬"
    )
    return ConversationHandler.END


async def handle_list_previous_tests(update: Update, context: CallbackContext):
    """Handles the 'قائمة الاختبارات السابقة' sub-option."""
    user_id = update.effective_user.id

    # Retrieve test records using database function
    test_records = database.get_data(
        "SELECT id, timestamp, score, num_questions FROM previous_tests WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,),
    )

    if not test_records:
        await update.callback_query.edit_message_text("ليس لديك اختبارات سابقة. 😞")
        return

    # Format and display test list
    keyboard = []
    for i, record in enumerate(test_records):
        test_id, timestamp, score, num_questions = record
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"اختبار {i + 1} - {timestamp} ({score}/{num_questions})",
                    callback_data=f"view_test_details:{test_id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="tests")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        "قائمة اختباراتك السابقة: 📜", reply_markup=reply_markup
    )


async def handle_view_test_details(update: Update, context: CallbackContext):
    """Handles viewing the details of a specific test."""
    query = update.callback_query
    await query.answer()
    try:
        _, test_id = query.data.split(":")
        test_id = int(test_id)
    except (ValueError, IndexError) as e:
        logger.error(f"Error extracting test_id from query data: {query.data}, {e}")
        await query.message.reply_text(
            "حدث خطأ أثناء تحميل تفاصيل الاختبار، يرجى المحاولة مرة أخرى."
        )
        return

    # Retrieve test data using database function
    test_data = database.get_data(
        """
        SELECT timestamp, num_questions, score, time_taken, pdf_path
        FROM previous_tests
        WHERE id = ?
        """,
        (test_id,),
    )

    if not test_data:
        await query.answer("عذراً، لم يتم العثور على بيانات الاختبار. 😞")
        return

    timestamp, num_questions, score, time_taken, pdf_path = test_data[0]

    # Format the message
    message = (
        f"تفاصيل الاختبار:\n"
        f"التاريخ: {timestamp}\n"
        f"عدد الأسئلة: {num_questions}\n"
        f"الدرجة: {score}/{num_questions}\n"
        f"الوقت المستغرق: {int(time_taken // 60)} دقيقة و{int(time_taken % 60)} ثانية\n"
    )

    # Add a button to download the PDF if it exists
    keyboard = [
        [
            InlineKeyboardButton(
                "تحميل ملف PDF ⬇️", callback_data=f"download_pdf:{test_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "الرجوع للخلف 🔙", callback_data="handle_list_previous_tests"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)


async def download_test_pdf(update: Update, context: CallbackContext):
    """Downloads the PDF file for the test."""
    query = update.callback_query
    await query.answer()
    try:
        _, test_id = query.data.split(":")
        test_id = int(test_id)
    except (ValueError, IndexError) as e:
        logger.error(f"Error extracting test_id from {query.data}: {e}")
        await query.message.reply_text(
            "حدث خطأ أثناء تحميل ملف PDF، يرجى المحاولة مرة أخرى."
        )
        return

    # Fetch the pdf_path using the test_id using database function
    pdf_path = database.get_data(
        "SELECT pdf_path FROM previous_tests WHERE id = ?", (test_id,)
    )

    if pdf_path and pdf_path[0][0]:
        try:
            with open(pdf_path[0][0], "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id, document=f
                )
        except FileNotFoundError:
            logger.error(f"PDF file not found at path: {pdf_path[0][0]}")
            await query.message.reply_text(
                "عذراً، لم يتم العثور على ملف PDF. قد يكون قد تم حذفه."
            )
        except Exception as e:
            logger.error(f"Error sending PDF for test_id: {test_id}, {e}")
            await query.message.reply_text(
                "حدث خطأ أثناء إرسال ملف PDF، يرجى المحاولة مرة أخرى."
            )
    else:
        await query.message.reply_text("لم يتم العثور على ملف PDF لهذا الاختبار. 😞")


# Dictionary to map handler names to functions
TESTS_HANDLERS = {
    "tests": handle_tests,
    # "handle_start_new_test": handle_start_new_test,
    "handle_list_previous_tests": handle_list_previous_tests,
    "view_test_details": handle_view_test_details,
}

TESTS_HANDLERS_PATTERN = {
    r"^download_pdf:.+$": download_test_pdf,
    r"^main_category_page:\d+$": lambda update, context: handle_show_main_categories(
        update, context, int(update.callback_query.data.split(":")[1])
    ),  # Pagination handler
    r"^subcategory_page:\d+$": lambda update, context: handle_show_subcategories(
        update, context, int(update.callback_query.data.split(":")[1])
    ),  # Pagination handler
}


test_conv_ai_assistance_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_ai_assistance_yes, pattern="^ai_assistance_yes$")
    ],
    states={
        CHATTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, chat)],
    },
    fallbacks=[CommandHandler("end_chat", end_chat)],
)

tests_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_start_new_test, pattern=r"^handle_start_new_test$"),
        CallbackQueryHandler(handle_quiz_type_choice, pattern=r"^quiz_type:.+$"),
    ],
    states={
        CHOOSE_QUIZ_TYPE: [
            CallbackQueryHandler(handle_quiz_type_choice, pattern=r"^quiz_type:.+$")
        ],
        CHOOSE_CATEGORY_TYPE: [
            CallbackQueryHandler(
                handle_category_type_choice, pattern=r"^(main_category|sub_category)$"
            )
        ],
        CHOOSE_MAIN_CATEGORY: [
            CallbackQueryHandler(
                handle_category_choice, pattern=r"^main_category_id:\d+$"
            ),
        ],
        CHOOSE_SUB_CATEGORY: [
            CallbackQueryHandler(
                handle_category_choice, pattern=r"^sub_category_id:\d+$"
            ),
        ],
        CHOOSE_INPUT_TYPE: [
            CallbackQueryHandler(
                handle_number_of_questions_choice, pattern=r"^number_of_questions$"
            ),
            CallbackQueryHandler(handle_time_limit_choice, pattern=r"^time_limit$"),
        ],
        GET_NUMBER_OF_QUESTIONS: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_number_of_questions_input
            )
        ],
        GET_TIME_LIMIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_limit_input)
        ],
        ANSWER_QUESTIONS: [CallbackQueryHandler(handle_answer, pattern=r"^answer_")],
    },
    fallbacks=[
        CallbackQueryHandler(handle_ai_assistance_no, pattern=r"^ai_assistance_no$"),
        CallbackQueryHandler(handle_start_new_test, pattern=r"^handle_start_new_test$"),
        CallbackQueryHandler(handle_quiz_type_choice, pattern=r"^quiz_type:.+$"),
    ],
)
