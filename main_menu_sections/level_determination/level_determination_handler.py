import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from datetime import datetime, timedelta
import os
import random
from typing import Dict, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler,
)

from config import CONTEXT_DIRECTORY, UNDER_DEVLOPING_MESSAGE
from handlers.main_menu_handler import main_menu_handler
from handlers.personal_assistant_chat_handler import chatgpt, SYSTEM_MESSAGE
from main_menu_sections.level_determination.pdf_generator import (
    generate_quiz_pdf,
)
from utils.database import (
    execute_query,
    get_data,
    execute_query_return_id,
)
from utils.question_management import get_passage_content, get_random_questions
from utils.subscription_management import check_subscription
from utils.user_management import (
    calculate_percentage_expected,
    calculate_points,
    update_user_created_questions,
    update_user_percentage_expected,
    update_user_points,
    update_user_usage_time,
)

# Set up logging
logger = logging.getLogger(__name__)

# States for the conversation
(
    CHOOSE_QUIZ_TYPE,
    CHOOSE_INPUT_TYPE,
    GET_NUMBER_OF_QUESTIONS,
    GET_TIME_LIMIT,
    ANSWER_QUESTIONS,
) = range(5)
CHATTING = 0


executor = ThreadPoolExecutor(
    max_workers=2
)


async def handle_level_determination(update: Update, context: CallbackContext):
    """Handles the 'تحديد المستوى' option and displays its sub-menu."""

    if not await check_subscription(update, context):
        return
    context.user_data["current_section"] = "level_determination"
    keyboard = [
        [
            InlineKeyboardButton(
                "اختبر مستواك الحالي 📝", callback_data="test_current_level"
            )
        ],
        [InlineKeyboardButton("تتبع التقدم 📈", callback_data="track_progress")],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    await update.callback_query.edit_message_text(
        "تحديد المستوى 🎯", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_test_current_level(update: Update, context: CallbackContext):
    """Handles the 'اختبر مستواك الحالي' sub-option, now with quiz type choice."""

    keyboard = [
        [InlineKeyboardButton("لفظي 🗣️", callback_data="level_quiz_type:verbal")],
        [InlineKeyboardButton("كمي 🔢", callback_data="level_quiz_type:quantitative")],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="level_determination")],
    ]
    await update.callback_query.edit_message_text(
        "اختر نوع الاختبار:", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_QUIZ_TYPE  # Start at quiz type selection


async def handle_quiz_type_choice(update: Update, context: CallbackContext):
    """Handles the choice of quiz type."""
    query = update.callback_query
    await query.answer()
    try:
        _, quiz_type = query.data.split(":")
        context.user_data["level_quiz_type"] = quiz_type

        if quiz_type == "quantitative":
            await query.message.reply_text(UNDER_DEVLOPING_MESSAGE)
            return  # Stop further processing for quantitative

        # Proceed to the input type selection:
        keyboard = [
            [
                InlineKeyboardButton(
                    "عددًا معينًا من الأسئلة 🔢", callback_data="number_of_questions"
                )
            ],
            [
                InlineKeyboardButton(
                    "عن طريق اختبار بمدة زمنية محددة ⏱️", callback_data="time_limit"
                )
            ],
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data="test_current_level"
                )
            ],
        ]
        await update.callback_query.edit_message_text(
            "هل تريدنا أن نحدد مستواك عن طريق سؤالك عددًا معينًا من الأسئلة، أم عن طريق إعطائك اختبارا بمدة زمنية معينة؟ 🤔",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CHOOSE_INPUT_TYPE
    except Exception as e:
        logger.error(f"Error in handle_quiz_type_choice: {e}")
        await query.message.reply_text(
            "حدث خطأ أثناء اختيار نوع الاختبار. يرجى المحاولة مرة أخرى. ⚠️"
        )
        return ConversationHandler.END


async def handle_number_of_questions_choice(update: Update, context: CallbackContext):
    """Handles the choice of specifying the number of questions."""
    await update.callback_query.edit_message_text(
        "كم عدد الأسئلة التي ترغب في الإجابة عليها؟ 🤔"
    )
    return GET_NUMBER_OF_QUESTIONS


async def handle_time_limit_choice(update: Update, context: CallbackContext):
    """Handles the choice of specifying the time limit."""
    await update.callback_query.edit_message_text("كم دقيقة لديك متاحة للاختبار؟ ⏱️")
    return GET_TIME_LIMIT


async def handle_number_of_questions_input(update: Update, context: CallbackContext):
    """Handles the user input for the number of questions."""
    try:
        num_questions = int(update.message.text)
        if not 10 <= num_questions <= 100:
            await update.message.reply_text("الرجاء إدخال عدد أسئلة بين 10 و 100. ⚠️")
            return GET_NUMBER_OF_QUESTIONS

        context.user_data["end_time"] = datetime.now() + timedelta(
            minutes=num_questions * 1.5
        )
        context.user_data["num_questions"] = num_questions
        await start_quiz(update, context)
        return ANSWER_QUESTIONS

    except ValueError:
        await update.message.reply_text("الرجاء إدخال عدد صحيح. 🔢")
        return GET_NUMBER_OF_QUESTIONS
    except Exception as e:
        logger.error(f"Error in handle_number_of_questions_input: {e}")
        await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى. ⚠️")
        return GET_NUMBER_OF_QUESTIONS


async def handle_time_limit_input(update: Update, context: CallbackContext):
    """Handles the user input for the time limit."""
    try:
        time_limit = int(update.message.text)
        if time_limit <= 0:
            await update.message.reply_text("الرجاء إدخال وقت صحيح أكبر من 0. ⏱️")
            return GET_TIME_LIMIT

        context.user_data["end_time"] = datetime.now() + timedelta(minutes=time_limit)
        num_questions = int(time_limit / 1.2)
        context.user_data["num_questions"] = num_questions
        await start_quiz(update, context)
        return ANSWER_QUESTIONS

    except ValueError:
        await update.message.reply_text("الرجاء إدخال عدد صحيح. 🔢")
        return GET_TIME_LIMIT
    except Exception as e:
        logger.error(f"Error in handle_time_limit_input: {e}")
        await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى. ⚠️")
        return GET_TIME_LIMIT


async def start_quiz(update: Update, context: CallbackContext):
    """Starts the quiz, generates PDF, and sends the first question."""
    user_id = update.effective_user.id
    num_questions = context.user_data["num_questions"]
    question_type = context.user_data["level_quiz_type"]

    try:
        questions = get_random_questions(num_questions, question_type)
    except Exception as e:
        logger.error(f"Error in getting questions: {e}")
        await update.message.reply_text(
            "حدث خطأ أثناء تحميل الأسئلة. يرجى المحاولة مرة أخرى. ⚠️"
        )
        return ConversationHandler.END

    context.user_data["questions"] = questions
    context.user_data["current_question"] = 0
    context.user_data["score"] = 0
    context.user_data["start_time"] = datetime.now()
    context.user_data["answers"] = []
    context.user_data["results"] = []

    try:
        timestamp = datetime.now()
        level_determination_id = execute_query_return_id(
            """
            INSERT INTO level_determinations (user_id, timestamp, num_questions, percentage, time_taken, pdf_path)
            VALUES (?, ?, ?, 0, 0, '')
            """,
            (user_id, timestamp, num_questions),
        )
        context.user_data["level_determination_id"] = level_determination_id
    except Exception as e:
        logger.error(f"Error in database insertion: {e}")
        await update.message.reply_text(
            "حدث خطأ أثناء بدء الاختبار. يرجى المحاولة مرة أخرى. ⚠️"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "سيتم تقييم مستواك من خلال هذه الأسئلة. 📝\n"
        "علما بأنه سيتم توضيح وشرح جميع الأسئلة لك خطوة بخطوة في نهاية الاختبار. 😊"
    )

    # Countdown
    for i in range(3, 0, -1):
        await asyncio.sleep(1)
        await update.message.reply_text(f"{i}...")

    await send_question(update, context)


async def send_question(update: Update, context: CallbackContext):
    """Sends the current question to the user with randomized answer order."""
    if (
        "end_time" in context.user_data
        and datetime.now() > context.user_data["end_time"]
    ):
        await end_quiz(update, context)
        return

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
        answer_options = [
            (f"أ. {option_a}", f"answer_{question_id}_أ"),
            (f"ب. {option_b}", f"answer_{question_id}_ب"),
            (f"ج. {option_c}", f"answer_{question_id}_ج"),
            (f"د. {option_d}", f"answer_{question_id}_د"),
        ]
        random.shuffle(answer_options)

        keyboard = []
        for i in range(0, len(answer_options), 2):
            row = [
                InlineKeyboardButton(text, callback_data=data)
                for text, data in answer_options[i : i + 2]
            ]
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        if current_question_index == 0:
            await update.effective_message.reply_text(
                f"{passage_text}" f"{current_question_index+1}. {question_text}",
                reply_markup=reply_markup,
            )
        else:
            await update.effective_message.edit_text(
                f"{passage_text}" f"{current_question_index+1}. {question_text}",
                reply_markup=reply_markup,
            )
    else:
        await end_quiz(update, context)
        await handle_final_step(update, context)
        return ConversationHandler.END


async def handle_answer(update: Update, context: CallbackContext):
    """Handles answer button presses, checks answers, and sends the next question."""
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
    except Exception as e:
        logger.error(f"Error in parsing answer data: {e}")
        await query.answer(
            text="حدث خطأ أثناء معالجة إجابتك. يرجى المحاولة مرة أخرى. ⚠️",
            show_alert=True,
        )


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

    # Store the user's answer and whether it was correct
    context.user_data["answers"].append(user_answer)
    context.user_data["results"].append(is_correct)

    level_determination_id = context.user_data["level_determination_id"]

    try:
        record_user_answer(
            user_id, question_id, user_answer, is_correct, level_determination_id
        )
    except Exception as e:
        logger.error(f"Error in recording user answer: {e}")
        # Decide whether to continue or halt the quiz based on the severity

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

    context.user_data["current_question"] += 1
    await send_question(update, context)


def record_user_answer(
    user_id, question_id, user_answer, is_correct, level_determination_id
):
    """Records the user's answer in the database, linked to the level determination."""
    try:
        execute_query(
            """
            INSERT INTO level_determination_answers (user_id, question_id, user_answer, is_correct, level_determination_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, question_id, user_answer, is_correct, level_determination_id),
        )
    except Exception as e:
        logger.error(f"Error recording user answer to database: {e}")
        # Handle the exception, potentially retrying the operation or notifying the user


def get_option_text(question_data, correct_answer):
    """Helper function to get the text of the correct option."""
    option_mapping = {
        "أ": question_data[3],
        "ب": question_data[4],
        "ج": question_data[5],
        "د": question_data[6],
    }
    return option_mapping.get(correct_answer, "غير محدد")


async def end_quiz(update: Update, context: CallbackContext):
    """Calculates the score and ends the quiz."""
    end_time = datetime.now()
    start_time = context.user_data["start_time"]
    total_time = (end_time - start_time).total_seconds()
    score = context.user_data["score"]
    total_questions = len(context.user_data["questions"])
    questions = context.user_data["questions"]
    user_id = update.effective_user.id

    level_determination_id = context.user_data["level_determination_id"]

    if (
        "end_time" in context.user_data
        and datetime.now() > context.user_data["end_time"]
    ):
        await update.effective_message.reply_text("لقد انتهى وقتك. ⏱️")

    message = await update.effective_message.edit_text(
        "انتظر قليلا حتى يتم تحليل الاجابتات التي قمت بأختيارها... ⏳",
        parse_mode="Markdown",
    )

    update_user_usage_time(user_id, total_time)
    update_user_created_questions(user_id, total_questions)
    percentage_expected = calculate_percentage_expected(score, total_questions)
    update_user_percentage_expected(user_id, percentage_expected)
    points_earned = calculate_points(total_time, score, total_questions)
    update_user_points(user_id, points_earned)

    percentage = calculate_percentage_expected(score, total_questions)

    # Prepare data for analysis
    quiz_data = []
    for i, question_data in enumerate(questions):
        question_id = question_data[0]
        question_text = question_data[2]
        correct_answer = question_data[1]
        user_answer = context.user_data["answers"][i]
        is_correct = context.user_data["results"][i]

        # Fetch category and question type from the database
        category_name, question_type = await get_question_category_and_type(question_id)

        quiz_data.append(
            {
                "question_text": question_text,
                "correct_answer": correct_answer,
                "user_answer": user_answer,
                "is_correct": is_correct,
                "category": category_name,
                "question_type": question_type,
            }
        )

    # Call the function to generate personalized feedback
    feedback_text = await generate_feedback_with_chatgpt(
        user_id,
        quiz_data,
        score,
        total_questions,
        total_time,
        update=update,
        context=context,
    )

    await message.edit_text(
        f"*انتهت الأسئلة!* 🎉\n"
        f"لقد ربحت *{points_earned}* نقطة! 🏆\n"
        f"لقد حصلت على *{score}* من *{total_questions}* 👏\n"
        f"لقد استغرقت *{int(total_time // 60)}* دقيقة و*{int(total_time % 60)}* ثانية. ⏱️\n"
        f"*إليك بعض الملاحظات حول مستواك وطرق التحسين:*\n{feedback_text}",
        parse_mode="Markdown",
    )

    await update.effective_message.reply_text("انتظر قليلا جاري إنشاء ملف pdf... 📄")

    def generate_pdf_wrapper(questions, user_id):
        try:
            return generate_quiz_pdf(questions, user_id)
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return None

    loop = asyncio.get_running_loop()  # Get the event loop
    pdf_filepath = await loop.run_in_executor(
        executor, generate_pdf_wrapper, questions, user_id
    )

    if pdf_filepath is None:  # Check if PDF generation failed
        await update.effective_message.reply_text("حدث خطأ أثناء إنشاء ملف PDF. ⚠️")

    try:
        execute_query(
            """
            UPDATE level_determinations
            SET percentage = ?, time_taken = ?, pdf_path = ?
            WHERE id = ?
            """,
            (percentage, total_time, pdf_filepath, level_determination_id),
        )
    except Exception as e:
        logger.error(f"Error updating level determination in database: {e}")
        # Handle the error, e.g., log and potentially inform the user

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


async def get_question_category_and_type(question_id: int):
    """Fetches the category name and question type for a given question."""
    query = """
    SELECT main_categories.name, questions.question_type
    FROM questions
    JOIN main_categories ON questions.main_category_id = main_categories.id
    WHERE questions.id = ?
    """
    try:
        result = await asyncio.to_thread(get_data, query, (question_id,))
        if result:
            category_name, question_type = result[0]
            return category_name, question_type
        return "Unknown", "Unknown"
    except Exception as e:
        logger.error(f"Error fetching question details: {e}")
        return "Unknown", "Unknown"


async def generate_feedback_with_chatgpt(
    user_id: int,
    quiz_data: List[Dict],
    score: int,
    total_questions: int,
    total_time: float,
    update: Update,
    context: CallbackContext,
) -> str:
    # Prepare the system message for ChatGPT
    system_message = (
        "You are an intelligent assistant. Analyze the user's quiz performance and provide personalized feedback. "
        "Take into account the categories and types of questions. Suggest areas where the user needs improvement and a recommended study path. "
        "Focus on their weak categories and question types."
        "And importent not your response will be in Arabic"
    )

    # Format the user's quiz data into a prompt for ChatGPT
    user_message = (
        f"The user scored {score} out of {total_questions}. They took {total_time} seconds to complete the quiz. "
        "Here are the details of the questions and answers, including categories and types:\n"
    )
    for i, q in enumerate(quiz_data):
        user_message += (
            f"Question {i+1}: {q['question_text']}\n"
            f"Category: {q['category']}\n"
            f"Type: {q['question_type']}\n"
            f"Correct Answer: {q['correct_answer']}\n"
            f"User's Answer: {q['user_answer']}\n"
            f"Was it correct? {'Yes' if q['is_correct'] else 'No'}\n\n"
        )

    try:
        feedback_text = await chatgpt.chat_with_assistant(
            user_id=user_id,
            user_message=user_message,
            system_message=system_message,
            save_history=False,
            update=update,
            context=context,
            use_response_mode=False,
            return_as_text=True,
        )
        return (
            feedback_text
            if feedback_text
            else "عذرا، لا يمكنني معالجة طلبك في الوقت الحالي."
        )
    except Exception as e:
        logger.error(f"Error generating feedback with ChatGPT: {e}")
        return "حدث خطأ أثناء الحصول على تحليل الأداء. ⚠️"


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
    return ConversationHandler.END


async def handle_ai_assistance_no(update: Update, context: CallbackContext):
    """Handles the 'no' choice for AI assistance."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("شكرًا لك. يمكنك العودة للقائمة الرئيسية. 😊")
    await main_menu_handler(query, context)
    return ConversationHandler.END


async def handle_ai_assistance_yes(update: Update, context: CallbackContext):
    """Handles the 'yes' choice for AI assistance."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "تفضل، كيف يمكنني مساعدتك في أسئلة تحديد المستوى؟ 😊"
    )

    user_id = update.effective_user.id
    messages = await chatgpt.get_chat_history(user_id)
    context.user_data["messages"] = messages

    return CHATTING


async def chat(update: Update, context: CallbackContext) -> int:
    user_message = update.message.text
    user_id = update.effective_user.id
    try:
        assistant_response = await chatgpt.chat_with_assistant(
            user_id, user_message, update, context, system_message=SYSTEM_MESSAGE
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
    except Exception as e:
        logger.error(f"Error in chat with user {user_id}: {e}")
        await update.message.reply_text(
            "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقًا. ⚠️"
        )
        return ConversationHandler.END


async def end_chat(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "شكرا لك على الدردشة معي. إذا احتجت إلى مساعدة مرة أخرى، فقط ابدأ دردشة جديدة! 😊"
    )
    return ConversationHandler.END


async def track_progress(update: Update, context: CallbackContext):
    """Tracks the user's progress in level determination."""
    user_id = update.effective_user.id

    try:
        level_determinations = get_data(
            "SELECT * FROM level_determinations WHERE user_id = ?", (user_id,)
        )
    except Exception as e:
        logger.error(f"Error retrieving level determinations: {e}")
        await update.callback_query.message.reply_text(
            "حدث خطأ أثناء جلب بيانات التقدم. ⚠️"
        )
        return

    if not level_determinations:
        await update.callback_query.message.reply_text(
            "لم تقم بأي اختبارات مستوى بعد. 📝"
        )
        return

    keyboard = []
    for i, level_determination in enumerate(level_determinations):
        timestamp = level_determination[2]
        test_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f").strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"الاختبار {i+1} ({test_date}) 🗓️",
                    callback_data=f"show_level_details_{level_determination[0]}",
                )
            ]
        )

    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="level_determination")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "اختر الاختبار تحديد المستوى لعرض تفاصيله: 🔍", reply_markup=reply_markup
    )


async def show_level_details(update: Update, context: CallbackContext):
    """Shows details of a specific level determination test."""
    query = update.callback_query
    try:
        level_determination_id = int(query.data.split("_")[-1])
    except ValueError as e:
        logger.error(f"Error extracting level_determination_id: {e}")
        await query.message.reply_text("حدث خطأ أثناء عرض تفاصيل الاختبار. ⚠️")
        return

    try:
        level_determination = get_data(
            "SELECT * FROM level_determinations WHERE id = ?",
            (level_determination_id,),
        )
    except Exception as e:
        logger.error(f"Error fetching level determination details: {e}")
        await query.message.reply_text("حدث خطأ أثناء جلب بيانات الاختبار. ⚠️")
        return

    if not level_determination:
        await query.message.reply_text("لم يتم العثور على هذا الاختبار. ⚠️")
        return

    level_determination = level_determination[0]
    timestamp = level_determination[2]
    percentage = level_determination[4]
    time_taken = level_determination[5]
    pdf_path = level_determination[6]

    message = (
        f"تفاصيل اختبار المستوى:\n"
        f"التاريخ: {timestamp} 🗓️\n"
        f"النسبة المئوية: {percentage:.2f}% 📊\n"
        f"الوقت المستغرق: {int(time_taken // 60)} دقيقة و {int(time_taken % 60)} ثانية. ⏱️\n"
    )

    if pdf_path:
        keyboard = [
            [
                InlineKeyboardButton(
                    "تحميل ملف PDF ⬇️",
                    callback_data=f"download_pdf_{level_determination_id}",
                )
            ],
            [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="track_progress")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="track_progress")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)


async def download_pdf(update: Update, context: CallbackContext):
    """Downloads the PDF file for the level determination test."""
    query = update.callback_query
    try:
        _, _, level_determination_id = query.data.split("_")
        level_determination_id = int(level_determination_id)
    except Exception as e:
        logger.error(f"Error extracting level_determination_id: {e}")
        await query.message.reply_text("حدث خطأ أثناء تحميل ملف PDF. ⚠️")
        return

    try:
        result = get_data(
            "SELECT pdf_path FROM level_determinations WHERE id = ?",
            (level_determination_id,),
        )
    except Exception as e:
        logger.error(f"Error fetching PDF path: {e}")
        await query.message.reply_text("حدث خطأ أثناء جلب ملف PDF. ⚠️")
        return

    if result:
        pdf_path = result[0][0]
        try:
            with open(pdf_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id, document=f
                )
        except Exception as e:
            logger.error(f"Error sending PDF: {e}")
            await query.message.reply_text("حدث خطأ أثناء إرسال ملف PDF. ⚠️")
    else:
        await query.message.reply_text("لم يتم العثور على ملف PDF لهذا الاختبار. ⚠️")


LEVEL_DETERMINATION_HANDLERS = {
    "level_determination": handle_level_determination,
    "test_current_level": handle_test_current_level,
    "track_progress": track_progress,
}

LEVEL_DETERMINATION_HANDLERS_PATTERN = {
    r"^show_level_details_.+$": show_level_details,
    r"^download_pdf_.+$": download_pdf,
}


level_conv_ai_assistance_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_ai_assistance_yes, pattern="^ai_assistance_yes$")
    ],
    states={CHATTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, chat)]},
    fallbacks=[CommandHandler("end_chat", end_chat)],
)


level_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_test_current_level, pattern="^test_current_level$")
    ],
    states={
        CHOOSE_QUIZ_TYPE: [
            CallbackQueryHandler(
                handle_quiz_type_choice, pattern="^level_quiz_type:.+$"
            )
        ],
        CHOOSE_INPUT_TYPE: [
            CallbackQueryHandler(
                handle_number_of_questions_choice, pattern="^number_of_questions$"
            ),
            CallbackQueryHandler(handle_time_limit_choice, pattern="^time_limit$"),
        ],
        GET_NUMBER_OF_QUESTIONS: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_number_of_questions_input
            )
        ],
        GET_TIME_LIMIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_limit_input)
        ],
        ANSWER_QUESTIONS: [CallbackQueryHandler(handle_answer, pattern="^answer_")],
    },
    fallbacks=[
        CallbackQueryHandler(handle_ai_assistance_no, pattern="^ai_assistance_no$"),
        CallbackQueryHandler(handle_test_current_level, pattern="^test_current_level$"),
        CommandHandler("end_quiz", end_quiz),
    ],
)
