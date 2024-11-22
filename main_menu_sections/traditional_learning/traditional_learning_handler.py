import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from telegram.error import BadRequest
from config import UNDER_DEVLOPING_MESSAGE
from main_menu_sections.traditional_learning.generating_materials import generate_material_pdf, generate_material_text, generate_material_video
from utils.section_manager import section_manager
from utils.category_mangement import (
    get_main_categories_by_subcategory,
    get_material_path,
    get_subcategories,
    get_subcategories_all,
)
from utils.database import get_data
from utils.subscription_management import check_subscription


async def handle_traditional_learning(update: Update, context: CallbackContext):
    """Handles the 'التعلم بالطريقة التقليدية' option."""
    query = update.callback_query
    await query.answer()
    section_path = query.data
    # Check section availability
    if not section_manager.is_section_available(section_path):
        await query.message.reply_text(section_manager.get_section_message(section_path))
        return

    if not await check_subscription(update, context):
        return

    context.user_data["current_section"] = "traditional_learning"

    keyboard = [
        [InlineKeyboardButton("لفظي 🗣️", callback_data="traditional_learning:verbal")],
        [
            InlineKeyboardButton(
                "كمي 🔢", callback_data="traditional_learning:quantitative"
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]

    await update.callback_query.edit_message_text(
        "التعلم بالطريقة التقليدية, اختر نوع السؤال: 📚",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_traditional_learning_type(update: Update, context: CallbackContext):
    """Handles the question type selection (verbal/quantitative)."""
    query = update.callback_query
    await query.answer()
    section_path = query.data

    # Check section availability
    if not section_manager.is_section_available(section_path):
        await query.message.reply_text(section_manager.get_section_message(section_path))
        return

    question_type = section_path.split(":")[-1]
    context.user_data["question_type"] = question_type

    if question_type == "quantitative":
        await query.message.reply_text(UNDER_DEVLOPING_MESSAGE)
        return  # Stop further processing for quantitative

    if question_type == "verbal":
        keyboard = [
            [
                InlineKeyboardButton(
                    "تصفح حسب التصنيف الرئيسي 🗂️", callback_data="show_main_categories"
                )
            ],
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data="traditional_learning"
                )
            ],
        ]  # Only main category for verbal
    elif question_type == "quantitative":
        keyboard = [
            [
                InlineKeyboardButton(
                    "تصفح حسب التصنيف الرئيسي 🗂️", callback_data="show_main_categories"
                )
            ],
            [
                InlineKeyboardButton(
                    "تصفح حسب التصنيف الفرعي 🗂️", callback_data="show_subcategories"
                )
            ],
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data="traditional_learning"
                )
            ],
        ]
    else:  # Handle invalid input if needed
        await query.message.reply_text("Invalid question type selected.")
        return

    new_text = "اختر طريقة التصفح: 📚" 
    current_text = update.callback_query.message.text 
    if new_text != current_text: 
        await update.callback_query.edit_message_text( new_text, reply_markup=InlineKeyboardMarkup(keyboard) )


async def handle_show_main_categories(update: Update, context: CallbackContext):
    """Displays a paginated list of main categories."""

    callback_data = update.callback_query.data
    parts = callback_data.split(":")
    page = int(parts[1]) if len(parts) > 1 else 1

    categories = get_data(
        "SELECT id, name FROM main_categories LIMIT 10 OFFSET ?", ((page - 1) * 10,)
    )
    keyboard = []
    for category in categories:
        if context.user_data.get("question_type") == "verbal":
            callback_data = f"sel_mat:{category[0]}:0" #  0 for subcategory as it's not used in verbal
        else:
            callback_data = f"s_sub_c:{category[0]}" # Existing logic for quantitative
        keyboard.append(
            [InlineKeyboardButton(category[1], callback_data=callback_data)]
        )

    # Pagination buttons
    if page > 1:
        keyboard.append(
            [InlineKeyboardButton("السابق ⏪", callback_data=f"s_main_c:{page - 1}")]
        )
    if len(categories) == 10:
        keyboard.append(
            [InlineKeyboardButton("التالي ⏩", callback_data=f"s_main_c:{page + 1}")]
        )
    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="traditional_learning")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await update.callback_query.edit_message_text(
            f"اختر التصنيف الرئيسي (الصفحة {page}):", reply_markup=reply_markup
        )
    except BadRequest as e:
        if str(e) == "Message is not modified":
            await update.callback_query.answer("You're already on this page.")
        else:
            print(f"Error in handle_show_main_categories: {e}")
            await update.callback_query.answer(
                "حدث خطأ، يرجى المحاولة مرة أخرى لاحقًا. ⚠️"
            )


async def handle_show_subcategories(update: Update, context: CallbackContext):
    """Displays subcategories and handles main category selection based on context."""

    callback_data = update.callback_query.data
    parts = callback_data.split(":")

    if len(parts) > 1 and parts[0] == "s_sub_c":
        main_category_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 1

        subcategories = get_subcategories(main_category_id, page=page)

        main_category_name = get_data(
            "SELECT name FROM main_categories WHERE id = ?", (main_category_id,)
        )[0][0]

        keyboard = []
        for subcategory in subcategories:
            callback_data = f"sel_mat:{main_category_id}:{subcategory[0]}"
            keyboard.append(
                [InlineKeyboardButton(subcategory[1], callback_data=callback_data)]
            )

        # Pagination buttons
        if page > 1:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "السابق ⏪",
                        callback_data=f"s_sub_c:{main_category_id}:{page - 1}",
                    )
                ]
            )
        if len(subcategories) == 10:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "التالي ⏩",
                        callback_data=f"s_sub_c:{main_category_id}:{page + 1}",
                    )
                ]
            )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data="show_main_categories"
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.callback_query.edit_message_text(
                f"اختر التصنيف الفرعي لـ '{main_category_name}' (الصفحة {page}):",
                reply_markup=reply_markup,
            )
        except BadRequest as e:
            if str(e) == "Message is not modified":
                await update.callback_query.answer("You're already on this page.")
            else:
                print(f"Error in handle_show_subcategories: {e}")
                await update.callback_query.answer(
                    "حدث خطأ، يرجى المحاولة مرة أخرى لاحقًا. ⚠️"
                )

    elif len(parts) > 1 and parts[0] == "show_main_for_sub":
        subcategory_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 1

        main_categories = get_main_categories_by_subcategory(subcategory_id, page=page)

        subcategory_name = get_data(
            "SELECT name FROM subcategories WHERE id = ?", (subcategory_id,)
        )[0][0]

        keyboard = []
        for main_category in main_categories:
            callback_data = f"sel_mat:{main_category[0]}:{subcategory_id}"
            keyboard.append(
                [InlineKeyboardButton(main_category[1], callback_data=callback_data)]
            )

        # Pagination buttons
        if page > 1:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "السابق ⏪",
                        callback_data=f"show_main_for_sub:{subcategory_id}:{page - 1}",
                    )
                ]
            )
        if len(main_categories) == 10:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "التالي ⏩",
                        callback_data=f"show_main_for_sub:{subcategory_id}:{page + 1}",
                    )
                ]
            )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data="show_subcategories"
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.callback_query.edit_message_text(
                f"اختر التصنيف الرئيسي لـ '{subcategory_name}' (الصفحة {page}):",
                reply_markup=reply_markup,
            )
        except BadRequest as e:
            if str(e) == "Message is not modified":
                await update.callback_query.answer("You're already on this page.")
            else:
                print(f"Error in handle_show_main_for_sub: {e}")
                await update.callback_query.answer(
                    "حدث خطأ، يرجى المحاولة مرة أخرى لاحقًا. ⚠️"
                )

    else:
        page = int(parts[1]) if len(parts) > 1 else 1
        subcategories = get_subcategories_all(page=page)

        keyboard = []
        for subcategory in subcategories:
            callback_data = f"show_main_for_sub:{subcategory[0]}"
            keyboard.append(
                [InlineKeyboardButton(subcategory[1], callback_data=callback_data)]
            )

        # Pagination buttons
        if page > 1:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "السابق ⏪", callback_data=f"show_subcategories:{page - 1}"
                    )
                ]
            )
        if len(subcategories) == 10:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "التالي ⏩", callback_data=f"show_subcategories:{page + 1}"
                    )
                ]
            )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "الرجوع للخلف 🔙", callback_data="traditional_learning"
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.callback_query.edit_message_text(
                f"اختر التصنيف الفرعي (الصفحة {page}):", reply_markup=reply_markup
            )
        except BadRequest as e:
            if str(e) == "Message is not modified":
                await update.callback_query.answer("You're already on this page.")
            else:
                print(f"Error in handle_show_subcategories_all: {e}")
                await update.callback_query.answer(
                    "حدث خطأ، يرجى المحاولة مرة أخرى لاحقًا. ⚠️"
                )

async def handle_material_selection(update: Update, context: CallbackContext):
    """Handles material selection and displays questions from the database."""

    callback_data = update.callback_query.data
    parts = callback_data.split(":")
    main_category_id = int(parts[1])
    page = int(parts[3]) if len(parts) > 3 else 1  # Extract page number
    QUESTIONS_PER_PAGE = 10

    main_category_name = get_data(
        "SELECT name FROM main_categories WHERE id = ?", (main_category_id,)
    )[0][0]

    if context.user_data.get("question_type") == "verbal":
        subcategory_id = 0  # Placeholder for verbal
        questions = get_data(
            """
            SELECT id, question_text 
            FROM questions 
            WHERE main_category_id = ? AND question_type = 'verbal'
            LIMIT ? OFFSET ?
            """,
            (main_category_id, QUESTIONS_PER_PAGE, (page - 1) * QUESTIONS_PER_PAGE),
        )
        total_questions = get_data( # Getting the total for pagination of verbal questions.
            """
            SELECT COUNT(*)
            FROM questions
            WHERE main_category_id = ? AND question_type = 'verbal'
            """,
            (main_category_id,),
        )[0][0]

        back_button_data = "traditional_learning:verbal"
    else:
        subcategory_id = int(parts[2])
        subcategory_name = get_data(
            "SELECT name FROM subcategories WHERE id = ?", (subcategory_id,)
        )[0][0]
        questions = get_data(
             """
            SELECT id, question_text 
            FROM questions 
            WHERE main_category_id = ? AND subcategory_id = ?
            LIMIT ? OFFSET ?
            """,
            (main_category_id, subcategory_id, QUESTIONS_PER_PAGE, (page - 1) * QUESTIONS_PER_PAGE),
        )
        total_questions = get_data(
            """
            SELECT COUNT(*)
            FROM questions
            WHERE main_category_id = ? AND subcategory_id = ?
            """,
             (main_category_id, subcategory_id),
        )[0][0]


        back_button_data = "show_subcategories"  # Or appropriate back action


    if not questions:
        await update.callback_query.message.reply_text("لا توجد نماذج لهذا النوع 🚫")
        return

    keyboard = []
    for question_id, question_text in questions:
        # Use question_id as material_number
        callback_data = f"show_format_options:{main_category_id}:{subcategory_id}:{question_id}"
        # Display question text with number
        display_text = f"نموذج {question_id}: {question_text}"
        keyboard.append([InlineKeyboardButton(display_text, callback_data=callback_data)])

    # Pagination buttons
    total_pages = (total_questions + QUESTIONS_PER_PAGE - 1) // QUESTIONS_PER_PAGE
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(
            InlineKeyboardButton(
                "السابق ⏪",
                callback_data=f"sel_mat:{main_category_id}:{subcategory_id}:{page - 1}",
            )
        )
    if page < total_pages:
        pagination_buttons.append(
            InlineKeyboardButton(
                "التالي ⏩",
                callback_data=f"sel_mat:{main_category_id}:{subcategory_id}:{page + 1}",
            )
        )
    if pagination_buttons:
        keyboard.append(pagination_buttons)

    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data=back_button_data)] # Use correct variable
    )

    reply_markup = InlineKeyboardMarkup(keyboard)


    if context.user_data.get("question_type") == "verbal":
        message_text = f"اختر رقم النموذج من '{main_category_name}':"
    else:
        message_text = (f"اختر رقم النموذج من '{main_category_name}' من التصنيف الفرعي '{subcategory_name}':")


    await update.callback_query.edit_message_text(
       f"{message_text} (الصفحة {page} من {total_pages}):", reply_markup=reply_markup
    )

async def handle_show_format_options(update: Update, context: CallbackContext):
    """Displays format options for the selected question."""

    callback_data = update.callback_query.data
    _, main_category_id, subcategory_id, question_id = callback_data.split(":", 3)

    # Store these values in context.user_data for use in handle_send_material
    context.user_data["material_data"] = {
        "main_category_id": main_category_id,
        "subcategory_id": subcategory_id,
        "question_id": question_id,
    }


    keyboard = [
        [
            InlineKeyboardButton("نص 📝", callback_data="send_material:text"),
            InlineKeyboardButton("PDF 📄", callback_data="send_material:pdf"),
            InlineKeyboardButton("فيديو 🎥", callback_data="send_material:video"),
        ],
        [
            InlineKeyboardButton(
                "الرجوع للخلف 🔙",
                callback_data=f"sel_mat:{main_category_id}:{subcategory_id}:1",  # Go back to material selection page 1
            )
        ],

    ]


    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("اختر الصيغة:", reply_markup=reply_markup)



async def handle_send_material(update: Update, context: CallbackContext):
    """Generates and sends the material for the selected question."""

    callback_data = update.callback_query.data
    query = update.callback_query
    await query.answer()
    _, format = callback_data.split(":", 1)

    material_data = context.user_data.get("material_data")
    main_category_id = material_data["main_category_id"]
    subcategory_id = material_data["subcategory_id"]
    question_id = material_data["question_id"]

    await query.message.reply_text("جاري التحضير... ⏳")

    # Here's where you'd implement your file generation logic
    # based on question_id, main_category_id, subcategory_id, and format
    # For now, let's just send a placeholder message

    if format == "pdf":
        file_path = generate_material_pdf(main_category_id, subcategory_id, question_id)
        if file_path:
            with open(file_path, "rb") as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
        else:
            await update.callback_query.message.reply_text("حدث خطأ أثناء إنشاء ملف PDF. ⚠️")
    elif format == "video":
        file_path = generate_material_video(main_category_id, subcategory_id, question_id)
        if file_path:
            with open(file_path, "rb") as f:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
        else:
            await update.callback_query.message.reply_text("جاري العمل على دعم الفيديو قريبا ⚠️")
    elif format == "text":
        text_content = generate_material_text(main_category_id, subcategory_id, question_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text_content)
    else:
        await update.callback_query.message.reply_text("صيغة غير مدعومة. 🚫")


# Dictionary to map handler names to functions (for simple callback data)
TRADITIONAL_LEARNING_HANDLERS = { }

# Dictionary to map patterns to functions (for callback data needing regex)
TRADITIONAL_LEARNING_HANDLERS_PATTERNS = {
    r"^traditional_learning$": handle_traditional_learning,
    r"^traditional_learning:(verbal|quantitative)$": handle_traditional_learning_type,
    r"^show_main_categories$": handle_show_main_categories,
    r"^show_subcategories$": handle_show_subcategories,
    r"^s_main_c:(\d+)$": handle_show_main_categories,
    r"^s_sub_c:(\d+)$": handle_show_subcategories,
    r"^s_sub_c:(\d+):(\d+)$": handle_show_subcategories,
    r"^show_main_for_sub:(\d+)$": handle_show_subcategories,
    r"^show_main_for_sub:(\d+):(\d+)$": handle_show_subcategories,
    r"^sel_mat:(\d+):(\d+)$": handle_material_selection,
    r"^sel_mat:(\d+):(\d+):(\d+)$": handle_material_selection,
    r"^show_format_options:\w+:\w+:\d+$": handle_show_format_options,
    r"^send_material:(text|pdf|video)$": handle_send_material,
}
