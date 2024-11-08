import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from telegram.error import BadRequest
from utils.category_mangement import (
    get_main_categories_by_subcategory,
    get_material_path,
    get_subcategories,
    get_subcategories_all,
)
from utils.database import get_data
from utils.subscription_management import check_subscription


async def handle_traditional_learning(update: Update, context: CallbackContext):
    """Handles the 'التعلم بالطريقة التقليدية' option and displays its sub-menu."""

    if not await check_subscription(update, context):
        return
    context.user_data["current_section"] = "traditional_learning"
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
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    await update.callback_query.edit_message_text(
        "التعلم بالطريقة التقليدية, اختر طريقة التصفح: 📚",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


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
        callback_data = f"s_sub_c:{category[0]}"
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
    """Handles material selection and displays format choices."""

    callback_data = update.callback_query.data
    _, main_category_id, subcategory_id = callback_data.split(":", 2)

    main_category_name = get_data(
        "SELECT name FROM main_categories WHERE id = ?", (main_category_id,)
    )[0][0]

    subcategory_name = get_data(
        "SELECT name FROM subcategories WHERE id = ?", (subcategory_id,)
    )[0][0]

    subcategory_path = os.path.join(
        "template_maker\Main_Classification_Structure",
        main_category_name,
        subcategory_name,
    )

    if not os.path.exists(subcategory_path):
        await update.callback_query.message.reply_text(
            f"لم يتم انشاء النماذج لهذا النوع 🚫"
        )
        return

    material_folders = [
        f
        for f in os.listdir(subcategory_path)
        if os.path.isdir(os.path.join(subcategory_path, f))
    ]

    keyboard = []
    for material_folder in material_folders:
        material_number = material_folder.split(" ")[1]
        callback_data = (
            f"show_format_options:{main_category_id}:{subcategory_id}:{material_number}"
        )
        keyboard.append(
            [InlineKeyboardButton(material_folder, callback_data=callback_data)]
        )
    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="traditional_learning")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        f"اختر رقم النموذج من '{main_category_name}' من التصنيف الفرعي '{subcategory_name}':",
        reply_markup=reply_markup,
    )


async def handle_show_format_options(update: Update, context: CallbackContext):
    """Displays format options (text, PDF, video) for the selected material."""

    callback_data = update.callback_query.data
    _, main_category_id, subcategory_id, material_number = callback_data.split(":", 3)

    keyboard = [
        [
            InlineKeyboardButton(
                "نص 📝",
                callback_data=f"send_material:{main_category_id}:{subcategory_id}:{material_number}:text",
            )
        ],
        [
            InlineKeyboardButton(
                "PDF 📄",
                callback_data=f"send_material:{main_category_id}:{subcategory_id}:{material_number}:pdf",
            )
        ],
        [
            InlineKeyboardButton(
                "فيديو 🎥",
                callback_data=f"send_material:{main_category_id}:{subcategory_id}:{material_number}:video",
            )
        ],
    ]

    keyboard.append(
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="traditional_learning")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "اختر الصيغة:", reply_markup=reply_markup
    )


async def handle_send_material(update: Update, context: CallbackContext):
    """Sends the material in the requested format."""

    callback_data = update.callback_query.data
    _, main_category_id, subcategory_id, material_number, format = callback_data.split(
        ":", 4
    )

    main_category_name = get_data(
        "SELECT name FROM main_categories WHERE id = ?", (main_category_id,)
    )[0][0]

    subcategory_name = get_data(
        "SELECT name FROM subcategories WHERE id = ?", (subcategory_id,)
    )[0][0]

    file_path = get_material_path(
        main_category_name, subcategory_name, material_number, format
    )

    if not os.path.exists(file_path):
        await update.callback_query.answer("عذراً، الملف غير موجود. 😞")
        return

    if format == "pdf":
        await context.bot.send_document(
            chat_id=update.effective_chat.id, document=open(file_path, "rb")
        )
    elif format == "video":
        await context.bot.send_video(
            chat_id=update.effective_chat.id, video=open(file_path, "rb")
        )
    elif format == "text":
        with open(file_path, "r", encoding="utf-8") as file:
            text_content = file.read()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text_content
        )
    else:
        await update.callback_query.answer("صيغة غير مدعومة. 🚫")


# Dictionary to map handler names to functions (for simple callback data)
TRADITIONAL_LEARNING_HANDLERS = {
    "traditional_learning": handle_traditional_learning,
    "show_main_categories": handle_show_main_categories,
    "show_subcategories": handle_show_subcategories,
}

# Dictionary to map patterns to functions (for callback data needing regex)
TRADITIONAL_LEARNING_HANDLERS_PATTERNS = {
    r"^s_main_c:(\d+)$": handle_show_main_categories,
    r"^s_sub_c:(\d+)$": handle_show_subcategories,
    r"^s_sub_c:(\d+):(\d+)$": handle_show_subcategories,
    r"^show_main_for_sub:(\d+)$": handle_show_subcategories,
    r"^show_main_for_sub:(\d+):(\d+)$": handle_show_subcategories,
    r"^sel_mat:(\d+):(\d+)$": handle_material_selection,
    r"^show_format_options:\w+:\w+:\d+$": handle_show_format_options,
    r"^send_material:\w+:\w+:\d+:(text|pdf|video)$": handle_send_material,
}
