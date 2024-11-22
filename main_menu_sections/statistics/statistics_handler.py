from datetime import datetime
from io import BytesIO
import numpy as np
from telegram.ext import CallbackContext
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import arabic_reshaper
from bidi.algorithm import get_display
from utils.database import get_data


async def handle_statistics(update: Update, context: CallbackContext):
    """Handles the 'الإحصائيات' option and displays its sub-menu."""
    context.user_data["current_section"] = "statistics"  # Set user context
    keyboard = [
        [
            InlineKeyboardButton(
                "إحصائيات الأداء 📊", callback_data="handle_performance_statistics"
            )
        ],
        [
            InlineKeyboardButton(
                "التمثيل البياني للتقدم 📈", callback_data="handle_progress_graph"
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="go_back")],
    ]
    await update.callback_query.edit_message_text(
        "الإحصائيات 🎉", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_performance_statistics(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Fetch level determination data
    level_determination_data = get_data(
        """
        SELECT percentage, time_taken, timestamp
        FROM level_determinations
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (user_id,),
    )

    # Fetch previous tests data
    previous_tests_data = get_data(
        """
        SELECT score, time_taken, timestamp
        FROM previous_tests
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (user_id,),
    )

    # Fetch main category performance
    main_category_performance = get_data(
        """
        SELECT mc.name, AVG(ua.is_correct) as avg_correct, COUNT(ua.id) as total_questions
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        JOIN main_categories mc ON q.main_category_id = mc.id
        WHERE ua.user_id = ?
        GROUP BY mc.id
        ORDER BY avg_correct DESC
        """,
        (user_id,),
    )

    # Fetch subcategory performance
    subcategory_performance = get_data(
        """
        SELECT sc.name, AVG(ua.is_correct) as avg_correct, COUNT(ua.id) as total_questions
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        JOIN main_sub_links msl ON q.main_category_id = msl.main_category_id
        JOIN subcategories sc ON msl.subcategory_id = sc.id
        WHERE ua.user_id = ?
        GROUP BY sc.id
        ORDER BY avg_correct DESC
        LIMIT 5
        """,
        (user_id,),
    )

    message = "📊 *إحصائيات الأداء المفصلة* 📊\n\n"

    if level_determination_data:
        recent_ld = level_determination_data[0]
        avg_ld = sum(row[0] for row in level_determination_data) / len(
            level_determination_data
        )
        message += "*تحديد المستوى:*\n"
        message += f"• أحدث نتيجة: {recent_ld[0]:.2f}% (قبل {(datetime.now() - datetime.strptime(recent_ld[2], '%Y-%m-%d %H:%M:%S.%f')).days} أيام)\n"
        message += f"• متوسط آخر 5 محاولات: {avg_ld:.2f}%\n"
        if len(level_determination_data) > 1:
            progress = recent_ld[0] - level_determination_data[-1][0]
            message += (
                f"• التقدم: {'📈' if progress >= 0 else '📉'} {abs(progress):.2f}%\n"
            )
        message += "\n"

    if previous_tests_data:
        recent_pt = previous_tests_data[0]
        avg_pt = sum(row[0] for row in previous_tests_data) / len(previous_tests_data)
        message += "*الاختبارات السابقة:*\n"
        message += f"• أحدث نتيجة: {recent_pt[0]} (قبل {(datetime.now() - datetime.strptime(recent_pt[2], '%Y-%m-%d %H:%M:%S.%f')).days} أيام)\n"
        message += f"• متوسط آخر 5 اختبارات: {avg_pt:.2f}\n"
        if len(previous_tests_data) > 1:
            progress = recent_pt[0] - previous_tests_data[-1][0]
            message += f"• التقدم: {'📈' if progress >= 0 else '📉'} {abs(progress)}\n"
        message += "\n"

    if main_category_performance:
        message += "*أداء الفئات الرئيسية:*\n"
        for category, avg_correct, total_questions in main_category_performance:
            message += (
                f"• {category}: {avg_correct*100:.2f}% صحيحة ({total_questions} سؤال)\n"
            )
        best_category = max(main_category_performance, key=lambda x: x[1])
        worst_category = min(main_category_performance, key=lambda x: x[1])
        message += f"\n🌟 أفضل أداء في: {best_category[0]}\n"
        message += f"🎯 مجال للتحسين: {worst_category[0]}\n\n"

    if subcategory_performance:
        message += "*أفضل 5 فئات فرعية:*\n"
        for subcategory, avg_correct, total_questions in subcategory_performance:
            message += f"• {subcategory}: {avg_correct*100:.2f}% صحيحة ({total_questions} سؤال)\n"
        message += "\n"

    # Add motivational message
    if level_determination_data or previous_tests_data:
        recent_score = (
            level_determination_data[0][0]
            if level_determination_data
            else previous_tests_data[0][0]
        )
        if recent_score > 80:
            message += "🎉 أداء رائع! استمر في العمل الجيد!\n"
        elif recent_score > 60:
            message += "👍 أداء جيد! واصل التقدم!\n"
        else:
            message += "💪 لا تستسلم! مع الممارسة ستتحسن!\n"

    # Add areas for focus
    if main_category_performance:
        focus_areas = [cat for cat, avg, _ in main_category_performance if avg < 0.6]
        if focus_areas:
            message += "\n🔍 *مجالات للتركيز:*\n"
            for area in focus_areas[:3]:  # Show top 3 areas to focus on
                message += f"• {area}\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "تفاصيل الفئات الرئيسية", callback_data="main_categories_details"
            )
        ],
        [
            InlineKeyboardButton(
                "تفاصيل الفئات الفرعية", callback_data="subcategories_details"
            )
        ],
        [InlineKeyboardButton("الرجوع للخلف 🔙", callback_data="statistics")],
    ]

    await update.callback_query.edit_message_text(
        message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_main_categories_details(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    main_category_performance = get_data(
        """
        SELECT mc.name, AVG(ua.is_correct) as avg_correct, COUNT(ua.id) as total_questions
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        JOIN main_categories mc ON q.main_category_id = mc.id
        WHERE ua.user_id = ?
        GROUP BY mc.id
        ORDER BY avg_correct DESC
        """,
        (user_id,),
    )

    message = "*تفاصيل أداء الفئات الرئيسية:*\n\n"
    for category, avg_correct, total_questions in main_category_performance:
        message += f"• {category}:\n"
        message += f"  - نسبة الإجابات الصحيحة: {avg_correct*100:.2f}%\n"
        message += f"  - عدد الأسئلة: {total_questions}\n"
        message += f"  - مستوى الأداء: {get_performance_level(avg_correct)}\n\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "الرجوع للخلف 🔙", callback_data="handle_performance_statistics"
            )
        ]
    ]
    await update.callback_query.edit_message_text(
        message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_subcategories_details(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    subcategory_performance = get_data(
        """
        SELECT sc.name, AVG(ua.is_correct) as avg_correct, COUNT(ua.id) as total_questions
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        JOIN main_sub_links msl ON q.main_category_id = msl.main_category_id
        JOIN subcategories sc ON msl.subcategory_id = sc.id
        WHERE ua.user_id = ?
        GROUP BY sc.id
        ORDER BY avg_correct DESC
        """,
        (user_id,),
    )

    message = "*تفاصيل أداء الفئات الفرعية:*\n\n"
    for subcategory, avg_correct, total_questions in subcategory_performance:
        message += f"• {subcategory}:\n"
        message += f"  - نسبة الإجابات الصحيحة: {avg_correct*100:.2f}%\n"
        message += f"  - عدد الأسئلة: {total_questions}\n"
        message += f"  - مستوى الأداء: {get_performance_level(avg_correct)}\n\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "الرجوع للخلف 🔙", callback_data="handle_performance_statistics"
            )
        ]
    ]
    await update.callback_query.edit_message_text(
        message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


def get_performance_level(avg_correct):
    if avg_correct >= 0.9:
        return "ممتاز 🌟"
    elif avg_correct >= 0.8:
        return "جيد جدا 👍"
    elif avg_correct >= 0.7:
        return "جيد 👌"
    elif avg_correct >= 0.6:
        return "مقبول 🙂"
    else:
        return "يحتاج إلى تحسين 💪"


async def handle_progress_graph(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Fetch data for both level determinations and previous tests
    level_determination_scores = get_data(
        """
        SELECT timestamp, percentage, num_questions
        FROM level_determinations
        WHERE user_id = ?
        ORDER BY timestamp
        """,
        (user_id,),
    )

    previous_tests_scores = get_data(
        """
        SELECT timestamp, score, num_questions
        FROM previous_tests
        WHERE user_id = ?
        ORDER BY timestamp
        """,
        (user_id,),
    )

    # Create a single figure with two subplots
    fig, (ax_level_det, ax_prev_tests) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot Level Determination data (percentage)
    if level_determination_scores:
        timestamps, percentages, num_questions = zip(*level_determination_scores)
        formatted_dates = [
            datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f") for ts in timestamps
        ]
        ax_level_det.plot(
            formatted_dates,
            percentages,
            marker="o",
            label=get_display(arabic_reshaper.reshape("تحديد المستوى")),
            color="blue",
        )
        for i, txt in enumerate(num_questions):
            ax_level_det.annotate(
                get_display(arabic_reshaper.reshape(f"({txt} سؤال)")),
                (mdates.date2num(formatted_dates[i]), percentages[i]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
            )
        ax_level_det.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax_level_det.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax_level_det.set_xlabel(get_display(arabic_reshaper.reshape("التاريخ")))
        ax_level_det.set_ylabel(get_display(arabic_reshaper.reshape("النسبة المئوية")))
        ax_level_det.set_title(
            get_display(arabic_reshaper.reshape("تقدم تحديد المستوى"))
        )
        ax_level_det.legend()

        # Optional: Add a trendline to show overall progress
        z = np.polyfit(mdates.date2num(formatted_dates), percentages, 1)
        p = np.poly1d(z)
        ax_level_det.plot(
            formatted_dates, p(mdates.date2num(formatted_dates)), "r--", label=get_display(arabic_reshaper.reshape("التحسن")
        )
        ax_level_det.legend()

    # Plot Previous Tests data (score)
    if previous_tests_scores:
        timestamps, scores, num_questions = zip(*previous_tests_scores)
        formatted_dates = [
            datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f") for ts in timestamps
        ]
        ax_prev_tests.plot(
            formatted_dates,
            scores,
            marker="x",
            label=get_display(arabic_reshaper.reshape("الاختبارات السابقة")),
            color="green",
        )
        for i, txt in enumerate(num_questions):
            ax_prev_tests.annotate(
                get_display(arabic_reshaper.reshape(f"({txt} سؤال)")),
                (mdates.date2num(formatted_dates[i]), scores[i]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
            )
        ax_prev_tests.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax_prev_tests.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax_prev_tests.set_xlabel(get_display(arabic_reshaper.reshape("التاريخ")))
        ax_prev_tests.set_ylabel(get_display(arabic_reshaper.reshape("الدرجات")))
        ax_prev_tests.set_title(
            get_display(arabic_reshaper.reshape("تقدم الاختبارات السابقة"))
        )
        ax_prev_tests.legend()

        # Optional: Add a trendline to show overall progress
        z = np.polyfit(mdates.date2num(formatted_dates), scores, 1)
        p = np.poly1d(z)
        ax_prev_tests.plot(
            formatted_dates, p(mdates.date2num(formatted_dates)), "r--", label=get_display(arabic_reshaper.reshape("التحسن"))
        )
        ax_prev_tests.legend()

    # Add a summary at the bottom
    if level_determination_scores or previous_tests_scores:
        best_percentage = max(percentages) if level_determination_scores else None
        best_score = max(scores) if previous_tests_scores else None
        message = "**ملخص الأداء 📊:**\n"
        if best_percentage:
            message += f"- أفضل نسبة مئوية في تحديد المستوى: {best_percentage:.2f}%\n"
        if best_score:
            message += f"- أفضل درجة في الاختبارات السابقة: {best_score:.2f}\n"

        # Display motivational messages based on trends
        if best_percentage and best_score:
            message += "أداءك يتحسن مع مرور الوقت! استمر في التحسن! 💪📈\n"
        elif best_percentage:
            message += "تحسن ملحوظ في تحديد المستوى! 🎯\n"
        elif best_score:
            message += "نتائج رائعة في الاختبارات السابقة! 🏆\n"

        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=message, parse_mode="Markdown"
        )

    # Adjust layout for better appearance
    fig.tight_layout()

    # Save the plot to a buffer and send it to the user
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buffer)

    # Close the plot to free memory
    plt.close(fig)


# Dictionary to map handler names to functions
STATISTICS_HANDLERS = {
    "statistics": handle_statistics,
    "handle_performance_statistics": handle_performance_statistics,
    "handle_progress_graph": handle_progress_graph,
    "main_categories_details": handle_main_categories_details,
    "subcategories_details": handle_subcategories_details,
}
