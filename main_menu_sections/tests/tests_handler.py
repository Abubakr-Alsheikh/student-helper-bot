import asyncio
import logging
import math
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

from config import CONTEXT_DIRECTORY
from handlers.main_menu_handler import main_menu_handler
from handlers.personal_assistant_chat_handler import chatgpt, SYSTEM_MESSAGE
from template_maker.content_population import find_expression, generate_number
from template_maker.generate_files import generate_quiz_pdf, generate_quiz_video
from utils import database
from utils.section_manager import section_manager
from utils.question_management import get_passage_content, get_questions_by_category
from utils.subscription_management import check_subscription
from utils.user_management import (
    calculate_points,
    get_user_name,
    get_user_phone_number,
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
    query = update.callback_query
    await query.answer()
    section_path = query.data

    # Check section availability
    if not section_manager.is_section_available(section_path):
        await query.message.reply_text(section_manager.get_section_message(section_path))
        return

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
    section_path = query.data

    # Check section availability
    if not section_manager.is_section_available(section_path):
        await query.message.reply_text(section_manager.get_section_message(section_path))
        return

    _, quiz_type = query.data.split(":")
    context.user_data["quiz_type"] = quiz_type

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
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data=f"{category_type[:-3]}"
                )
            ],
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
        )[0]
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
            *_,
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
        return ConversationHandler.END


async def handle_answer(update: Update, context: CallbackContext):
    """Handles answer button presses, checks answers, and sends the next question."""
    # Check if time limit is reached
    if (
        "end_time" in context.user_data
        and datetime.now() > context.user_data["end_time"]
    ):
        await end_quiz(update, context)
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
        total_time = (end_time - start_time).total_seconds()
        score = context.user_data["score"]
        total_questions = len(context.user_data["questions"])
        user_id = update.effective_user.id

        # Update user's total usage time in the database
        update_user_usage_time(user_id, total_time)

        # Update user's total created questions in the database
        update_user_created_questions(user_id, total_questions)

        # Calculate and award points
        points_earned = calculate_points(total_time, score, total_questions)
        update_user_points(user_id, points_earned)
        user_id = update.effective_user.id

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
        keyboard = [
            [
                InlineKeyboardButton("PDF 📄", callback_data="output_format_tests:pdf"),
                InlineKeyboardButton(
                    "فيديو 🎬 (تحت التطوير)", callback_data="output_format_tests:video"
                ),
            ],
        ]
        await update.effective_message.reply_text(
            "اختر صيغة الملف النهائي:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in end_quiz: {e}")
        await update.effective_message.reply_text(
            "حدث خطأ أثناء إنهاء الاختبار، يرجى المحاولة مرة أخرى."
        )


async def handle_output_format_choice(update: Update, context: CallbackContext):
    """Handles the user's choice of output format."""
    query = update.callback_query
    await query.answer()
    _, output_format = query.data.split(":")

    await query.message.delete()

    end_time = datetime.now()
    start_time = context.user_data["start_time"]
    total_time = (end_time - start_time).total_seconds()
    score = context.user_data["score"]

    questions = context.user_data["questions"]
    total_questions = len(questions)
    user_id = update.effective_user.id
    previous_test_id = context.user_data["previous_test_id"]

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

    test_number = database.get_data(
        """
        SELECT COUNT(*) 
        FROM previous_tests 
        WHERE user_id = ? AND id <= ?
        """,
        (user_id, previous_test_id),
    )[0][0]

    # Collect user data for the Main page
    phone_number = await get_user_phone_number(user_id)
    expression_number = find_expression(str(phone_number))
    user_data = {
        "studentName": await get_user_name(user_id),
        "phoneNumber": phone_number,
        "expressionNumber": expression_number,
        "modelNumber": test_number,
        "date": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "questionsNumber": str(total_questions),
        "studentsResults": f"{score/total_questions*100:.0f}%" if total_questions else "0%",
    }

    pdf_filepath = None
    video_filepath = None

    if output_format == "pdf":
        await update.effective_message.reply_text(
            "انتظر قليلا جاري إنشاء ملف pdf... 📄"
        )

        pdf_filepath = await generate_quiz_pdf(
            questions, user_id, "tests", str(start_time), test_number, user_data, category_name
        )

        if pdf_filepath is None:  # Check if PDF generation failed
            await update.effective_message.reply_text("حدث خطأ أثناء إنشاء ملف PDF. ⚠️")

        # Check if pdf_filepath is valid before trying to open it
        if pdf_filepath and os.path.exists(pdf_filepath):
            with open(pdf_filepath, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=f
                )
        else:
            logger.error("PDF file path is None or file does not exist.")
            await update.effective_message.reply_text("تعذر العثور على ملف PDF. ⚠️")

    elif output_format == "video":  # Future implementation
        await update.effective_message.reply_text("جاري إنشاء الفيديو... 🎬")
        video_filepath = await generate_quiz_video(
            questions, user_id, "tests", str(start_time), test_number, user_data, category_name
        )

        if (
            video_filepath
        ):  # If video generation was successful (check the actual return)
            try:
                with open(video_filepath, "rb") as f:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id, video=f
                    )

            except FileNotFoundError:
                logger.error(f"Video file not found at path: {video_filepath}")
                await update.effective_message.reply_text(
                    "عذراً، لم يتم العثور على ملف الفيديو."
                )

            except Exception as e:
                logger.error(f"Error sending video: {e}")
                await update.effective_message.reply_text(
                    "حدث خطأ أثناء إرسال الفيديو."
                )

        else:
            await update.effective_message.reply_text(
                "حدث خطأ أثناء إنشاء الفيديو."
            )  # Video generation failed.
    try:
        # Update the previous_tests entry
        database.execute_query(
            """
            UPDATE previous_tests
            SET score = ?, time_taken = ?, pdf_path = ?, video_path = ?
            WHERE id = ?
            """,
            (score, total_time, pdf_filepath, video_filepath, previous_test_id),
        )

    except Exception as e:
        logger.error(f"Error updating level determination in database: {e}")

    await handle_final_step(update, context)  # Continue to the AI assistance step
    return ConversationHandler.END


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


ITEMS_PER_PAGE = 5  # Define the number of items to show per page


async def handle_list_previous_tests(update: Update, context: CallbackContext):
    """Handles the 'قائمة الاختبارات السابقة' sub-option with pagination."""

    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data.split(":") if query.data else ["tests"]
    page = int(data[1]) if len(data) > 1 else 1

    # Retrieve total test count for pagination
    total_tests = database.get_data(
        "SELECT COUNT(*) FROM previous_tests WHERE user_id = ?", (user_id,)
    )[0][0]

    # Calculate offset for pagination
    offset = (page - 1) * ITEMS_PER_PAGE

    # Retrieve test records for the current page
    test_records = database.get_data(
        "SELECT id, timestamp, score, num_questions FROM previous_tests WHERE user_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (user_id, ITEMS_PER_PAGE, offset),
    )

    if not test_records:
        await query.edit_message_text("ليس لديك اختبارات سابقة. 😞")
        return

    # Format and display test list
    keyboard = []
    for i, record in enumerate(test_records):
        test_id, timestamp, score, num_questions = record
        date_time = datetime.fromisoformat(timestamp)
        formatted_date = date_time.strftime("%Y-%m-%d %H:%M")  # Example format
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"اختبار {total_tests - offset - i} - بتاريخ {formatted_date} - النتيجة ({score}/{num_questions})",
                    callback_data=f"view_test_details:{test_id}",
                )
            ]
        )

    # Pagination controls
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "⬅️ السابق", callback_data=f"handle_list_previous_tests:{page - 1}"
            )
        )
    if offset + ITEMS_PER_PAGE < total_tests:
        nav_buttons.append(
            InlineKeyboardButton(
                "التالي ➡️", callback_data=f"handle_list_previous_tests:{page + 1}"
            )
        )

    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="tests")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        f"قائمة اختباراتك السابقة (صفحة {page} من {math.ceil(total_tests / ITEMS_PER_PAGE)}): 📜",  # Indicate current page
        reply_markup=reply_markup,
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

    # Get detailed test information
    test_data = await get_test_data(test_id)

    if not test_data:
        await query.edit_message_text("عذراً، لم يتم العثور على بيانات الاختبار. 😞")
        return

    (
        timestamp,
        num_questions,
        score,
        time_taken,
        pdf_path,
        user_id,
        correct_answers,
        total_answered,
    ) = test_data[0]

    # Format message with detailed statistics
    message = format_test_details_message(
        timestamp, num_questions, score, time_taken, correct_answers, total_answered
    )

    # Get and store user data in context
    context.user_data["user_data"] = await get_user_data_for_test(
        user_id, test_id, timestamp, num_questions, score
    )
    context.user_data["test_id"] = test_id

    keyboard = [
        [
            InlineKeyboardButton(
                "تحميل ملف PDF ⬇️", callback_data=f"download_tests_pdf:{test_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "تحميل الفيديو 🎥", callback_data=f"download_tests_video:{test_id}"
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
    await handle_download_test_file(update, context, "pdf")

async def download_test_video(update: Update, context: CallbackContext):
    """Downloads the video file for the test."""
    await handle_download_test_file(update, context, "video")

# Helper Functions

async def get_test_data(test_id):
    """Retrieves test data from the database."""
    return database.get_data(
        """
        SELECT pt.timestamp, pt.num_questions, pt.score, pt.time_taken, pt.pdf_path, pt.user_id,
               COUNT(CASE WHEN ua.is_correct = 1 THEN 1 END) as correct_answers,
               COUNT(ua.id) as total_answered
        FROM previous_tests pt
        LEFT JOIN user_answers ua ON pt.id = ua.previous_tests_id
        WHERE pt.id = ?
        GROUP BY pt.id
        """,
        (test_id,),
    )

def format_test_details_message(
    timestamp, num_questions, score, time_taken, correct_answers, total_answered
):
    """Formats the test details message."""
    test_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f").strftime(
        "%Y/%m/%d %H:%M"
    )
    percentage = (score / num_questions) * 100 if num_questions > 0 else 0
    return (
        f"📊 تفاصيل الاختبار\n\n"
        f"📅 التاريخ: {test_date}\n"
        f"📝 عدد الأسئلة: {num_questions}\n"
        f"✅ الإجابات الصحيحة: {correct_answers}\n"
        f"📊 النتيجة النهائية: {score}/{num_questions} ({percentage:.1f}%)\n"
        f"⏱ الوقت المستغرق: {int(time_taken // 60)} دقيقة و{int(time_taken % 60)} ثانية\n"
        f"📋 الأسئلة المجاب عليها: {total_answered}/{num_questions}"
    )

async def get_user_data_for_test(user_id, test_id, timestamp, num_questions, score):
    """Gets user data for the test."""
    end_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
    test_number = database.get_data(
        """
        SELECT COUNT(*) 
        FROM previous_tests 
        WHERE user_id = ? AND id <= ?
        """,
        (user_id, test_id),
    )[0][0]

    percentage = (score / num_questions) * 100 if num_questions > 0 else 0

    phone_number = str(await get_user_phone_number(user_id))
    return {
        "studentName": await get_user_name(user_id),
        "phoneNumber": phone_number,
        "expressionNumber": find_expression(phone_number),
        "modelNumber": test_number,
        "date": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "questionsNumber": str(num_questions),
        "studentsResults": f"{percentage:.0f}%",
    }

async def handle_download_test_file(update: Update, context: CallbackContext, file_type: str):
    """Handles downloading either PDF or video for the test."""
    query = update.callback_query
    await query.answer()

    user_data = context.user_data.get("user_data")
    test_id = context.user_data.get("test_id")

    if not user_data or test_id is None:
        logger.error(f"User data or test ID not found in context for {file_type}.")
        await query.message.reply_text(
            f"حدث خطأ أثناء تحميل ملف {file_type.upper()}، يرجى المحاولة مرة أخرى."
        )
        return

    generating_message = await query.message.reply_text(f"جارٍ إنشاء ملف {file_type.upper()}... ⏳")

    test_details = database.get_data(
        f"""
        SELECT user_id, {file_type}_path, timestamp 
        FROM previous_tests 
        WHERE id = ?
        """,
        (test_id,),
    )

    if not test_details:
        await generating_message.edit_text(
            "عذراً، لم يتم العثور على بيانات الاختبار. 😞"
        )
        return

    user_id, file_path, timestamp = test_details[0]
    
    # Check if file needs to be regenerated
    if not file_path or not os.path.exists(file_path):
        await generating_message.edit_text(f"جارٍ إنشاء ملف {file_type.upper()}... 🔄")

        questions = database.get_data(
            """
            SELECT q.* 
            FROM questions q
            JOIN user_answers ua ON q.id = ua.question_id
            WHERE ua.previous_tests_id = ?
            """,
            (test_id,),
        )

        if file_type == "pdf":
            file_path = await generate_quiz_pdf(
                questions,
                user_id,
                "tests",
                timestamp,
                user_data["modelNumber"],
                user_data,
            )
        elif file_type == "video":
            file_path = await generate_quiz_video(
                questions,
                user_id,
                "tests",
                timestamp,
                user_data["modelNumber"],
                user_data=user_data,
            )

        if file_path:
            database.execute_query(
                f"UPDATE previous_tests SET {file_type}_path = ? WHERE id = ?",
                (file_path, test_id),
            )
        else:
            await generating_message.edit_text(f"حدث خطأ أثناء إنشاء ملف {file_type.upper()}. 😞")
            return

    # Send the file
    await generating_message.edit_text(f"جارٍ تحميل ملف {file_type.upper()}... 📄")
    try:
        with open(file_path, "rb") as f:
            if file_type == "pdf":
                await context.bot.send_document(chat_id=query.message.chat_id, document=f)
            elif file_type == "video":
                await context.bot.send_video(chat_id=query.message.chat_id, video=f)
        await generating_message.delete()
    except FileNotFoundError:
        logger.error(f"{file_type.upper()} file not found at path: {file_path}")
        await generating_message.edit_text(
            f"عذراً، لم يتم العثور على ملف {file_type.upper()}. قد يكون قد تم حذفه."
        )
    except Exception as e:
        logger.error(f"Error sending {file_type.upper()} for test_id: {test_id}, {e}")
        await generating_message.edit_text(
            f"حدث خطأ أثناء إرسال ملف {file_type.upper()}، يرجى المحاولة مرة أخرى."
        )


# Dictionary to map handler names to functions
TESTS_HANDLERS = {
    "tests": handle_tests,
    # "handle_start_new_test": handle_start_new_test,
    "handle_list_previous_tests": handle_list_previous_tests,
    "view_test_details": handle_view_test_details,
}

TESTS_HANDLERS_PATTERN = {
    r"^handle_list_previous_tests:\d+$": handle_list_previous_tests,
    r"^output_format_tests:.+$": handle_output_format_choice,
    r"^download_tests_pdf:.+$": download_test_pdf,
    r"^download_tests_video:.+$": download_test_video,
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
            CallbackQueryHandler(
                handle_category_type_choice, pattern=r"^(main_category|sub_category)$"
            ),
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
