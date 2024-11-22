import os
from telegram import Update
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from telegram.error import TimedOut

from AIModels.chatgpt import get_chatgpt_instance
from config import (
    GENERAL_ADVICE_FILE,
    SOLUTION_STRATEGIES_FILE,
    TIPS_AND_STRATEGIES_CONTENT,
)
from handlers.personal_assistant_chat_handler import SYSTEM_MESSAGE
from utils.subscription_management import check_subscription
from utils.section_manager import section_manager
from .keyboards import (
    get_tips_and_strategies_keyboard,
    get_general_advice_keyboard,
    get_general_advice_questions_keyboard,
    get_solution_strategies_keyboard,
    get_solution_strategies_questions_keyboard,
    get_format_selection_keyboard,
)
from .excel_handler import ExcelHandler
from .general_advice_model import GeneralAdviceModel
from .solution_strategies_model import SolutionStrategiesModel


async def handle_tips_and_strategies(update: Update, context: CallbackContext):
    """Handles the 'نصائح واستراتيجيات' option and displays its sub-menu."""
    query = update.callback_query
    await query.answer()
    section_path = query.data
    # Check section availability
    if not section_manager.is_section_available(section_path):
        await query.message.reply_text(section_manager.get_section_message(section_path))
        return

    if not await check_subscription(update, context):
        return

    context.user_data["current_section"] = "tips_and_strategies"  # Set user context
    await update.callback_query.edit_message_text(
        "📚 هذا هو قسم النصائح والاستراتيجيات. بماذا يمكنني أن أساعدك؟",
        reply_markup=await get_tips_and_strategies_keyboard(),
    )


async def handle_general_advice(update: Update, context: CallbackContext) -> None:
    """Handles general advice selection and displays sheet names."""
    query = update.callback_query
    await query.answer()

    # await query.edit_message_text(text="⏳ جارٍ تحميل النصائح... 🔄")  # Feedback during loading

    general_advice_excel = ExcelHandler(GENERAL_ADVICE_FILE)
    general_advice_model = GeneralAdviceModel(general_advice_excel)

    await query.edit_message_text(
        text="هنا ستجد مجموعة من النصائح الهامة لمساعدتك في التحضير لاختبار القدرات. تأكد من قراءتها بعناية للحصول على أفضل النتائج.",
        reply_markup=get_general_advice_keyboard(general_advice_model),
    )


async def handle_general_advice_sheet(update: Update, context: CallbackContext) -> None:
    """Handles sheet selection in general advice and displays questions."""
    query = update.callback_query
    await query.answer()
    sheet_name = query.data.replace("sheet_name_", "")

    # await query.edit_message_text(text="⏳ جارٍ تحميل الأسئلة... 📚")  # Feedback during loading

    general_advice_excel = ExcelHandler(GENERAL_ADVICE_FILE)
    general_advice_model = GeneralAdviceModel(general_advice_excel)
    questions = general_advice_model.get_sheet_questions(sheet_name)

    await query.edit_message_text(
        text="❓ اختر سؤالًا:",
        reply_markup=get_general_advice_questions_keyboard(questions, sheet_name),
    )


async def handle_general_advice_question(
    update: Update, context: CallbackContext
) -> None:
    """Handles question selection in general advice and sends the answer."""
    query = update.callback_query
    await query.answer()
    _, _, question_index, sheet_name = query.data.split("_", 3)
    question_index = int(question_index)

    # await query.edit_message_text(text="⏳ جارٍ تحميل الإجابة... 💡")  # Feedback during loading

    general_advice_excel = ExcelHandler(GENERAL_ADVICE_FILE)
    general_advice_model = GeneralAdviceModel(general_advice_excel)
    answer = general_advice_model.get_answer(sheet_name, question_index)

    await query.message.reply_text(text=answer)


# --- Solution Strategies Handlers ---
async def handle_solution_strategies(update: Update, context: CallbackContext) -> None:
    """Handles solution strategies selection and displays sheet names."""
    query = update.callback_query
    await query.answer()

    # await query.edit_message_text(text="⏳ جارٍ تحميل استراتيجيات الحل... 🧠")  # Feedback during loading

    solution_strategies_excel = ExcelHandler(SOLUTION_STRATEGIES_FILE)
    solution_strategies_model = SolutionStrategiesModel(solution_strategies_excel)

    await query.edit_message_text(
        text="تعرف على استراتيجيات الحل المختلفة لكل أنواع الأقسام والأسئلة. سأقدم لك تقنيات تساعدك على التعامل مع مختلف التحديات في الاختبار.",
        reply_markup=get_solution_strategies_keyboard(solution_strategies_model),
    )


async def handle_solution_strategies_sheet(
    update: Update, context: CallbackContext
) -> None:
    """Handles sheet selection in solution strategies and displays questions."""
    query = update.callback_query
    await query.answer()
    _, _, sheet_name = query.data.split("_", 2)

    # await query.edit_message_text(text="⏳ جارٍ تحميل الأسئلة... 📝")  # Feedback during loading

    solution_strategies_excel = ExcelHandler(SOLUTION_STRATEGIES_FILE)
    solution_strategies_model = SolutionStrategiesModel(solution_strategies_excel)
    questions = solution_strategies_model.get_sheet_questions(sheet_name)

    await query.edit_message_text(
        text="❓ اختر سؤالًا:",
        reply_markup=get_solution_strategies_questions_keyboard(questions, sheet_name),
    )


async def handle_solution_strategies_question(
    update: Update, context: CallbackContext
) -> None:
    """Handles question selection and asks for the preferred format."""
    query = update.callback_query
    await query.answer()
    _, _, question_index, sheet_name = query.data.split("_", 3)
    question_index = int(question_index)

    # Store the question index and sheet name in the user's context
    context.user_data["question_index"] = question_index
    context.user_data["sheet_name"] = sheet_name

    await query.edit_message_text(
        text="🎬 كيف تريد التوضيح؟", reply_markup=get_format_selection_keyboard()
    )


async def handle_solution_format(update: Update, context: CallbackContext) -> None:
    """Handles the format selection and sends the appropriate file."""
    query = update.callback_query
    await query.answer()
    file_format = query.data.split("_")[1]
    question_index = context.user_data.get("question_index")
    sheet_name = context.user_data.get("sheet_name")

    solution_strategies_excel = ExcelHandler(SOLUTION_STRATEGIES_FILE)
    solution_strategies_model = SolutionStrategiesModel(solution_strategies_excel)
    file_path = solution_strategies_model.get_file_path(
        sheet_name, question_index, file_format
    )

    file_path = os.path.join(TIPS_AND_STRATEGIES_CONTENT, file_path)

    if os.path.exists(file_path):
        await query.message.reply_text(
            text=f"⏳ جارٍ تحميل {file_format}... 📥"
        )  # Feedback during loading
        try:
            if file_format == "video":
                await context.bot.send_video(
                    chat_id=query.message.chat_id, video=open(file_path, "rb")
                )
            elif file_format == "audio":
                await context.bot.send_audio(
                    chat_id=query.message.chat_id, audio=open(file_path, "rb")
                )
            elif file_format == "text":
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
                await context.bot.send_message(
                    chat_id=query.message.chat_id, text=text_content
                )
            elif file_format == "pdf":
                await context.bot.send_document(
                    chat_id=query.message.chat_id, document=open(file_path, "rb")
                )

            # Optionally, you can send a confirmation message after the file is sent
            await query.message.reply_text(text=f"✅ تم إرسال {file_format} بنجاح! 🎉")
        except TimedOut as e:
            await query.message.reply_text(
                text="⏳ ...سيجهز  الملف في اي لحظة, يرجى الانتظار ⏱️"
            )
        except Exception as e:
            await query.message.reply_text(text=f"❌ حدث خطأ أثناء إرسال الملف: {e} 😥")
    else:
        await query.message.reply_text(text="❌ لم يتم العثور على الملف. 😞")


# Conversation states
CHATTING = 0

chatgpt = get_chatgpt_instance()


async def handle_request_specific_tips(update: Update, context: CallbackContext):
    """Handles the 'طلب نصائح خاصة' sub-option."""
    user = update.effective_user
    await update.callback_query.edit_message_text(
        f"مرحبا {user.first_name}! 👋 أنا هنا لتقديم النصائح خاصة لك. كيف يمكنني مساعدتك اليوم؟"
    )
    messages = await chatgpt.get_chat_history(user.id)
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
            "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقًا."
        )
        return ConversationHandler.END


async def end_chat(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "شكرا لك على الدردشة معي. 😊 إذا احتجت إلى مساعدة مرة أخرى، فقط ابدأ دردشة جديدة!"
    )
    return ConversationHandler.END


# Dictionary to map handler names to functions
TIPS_AND_STRATEGIES_HANDLERS = {
    # Main Hnalders
    "tips_and_strategies": handle_tips_and_strategies,
    "handle_general_tips": handle_general_advice,
    "handle_solving_strategies": handle_solution_strategies,
}

TIPS_AND_STRATEGIES_HANDLERS_PATTER = {
    # Sub Hnalders
    r"^sheet_name_.+$": handle_general_advice_sheet,  # General advice question selection
    r"^ga_q_\d+_.+$": handle_general_advice_question,  # General advice question selection
    r"^ss_sheet_.+$": handle_solution_strategies_sheet,  # Solution strategies sheet selection
    r"^ss_q_\d+_.+$": handle_solution_strategies_question,  # Solution strategies question selection
    r"^format_(video|audio|text|pdf)$": handle_solution_format,  # Solution format selection
}


tips_and_strategies_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            handle_request_specific_tips, "^handle_request_specific_tips$"
        ),
    ],
    states={
        CHATTING: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, chat),
        ],
    },
    fallbacks=[CommandHandler("main_menu", end_chat)],
)
