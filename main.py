import asyncio
import logging
import os
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.request import HTTPXRequest
from config import BOT_TOKEN, DATABASE_FILE

from handlers.conversation.conversation_handler import (
    register_converstaion_handlers,
    show_main_menu,
)
from handlers.main_menu_handler import handle_main_menu_option
from handlers.main_menu_sections_handlers import register_all_main_menu_handlers
from handlers.personal_assistant_chat_handler import (
    personal_assistant_handler,
)
from handlers.help_support_handler import help_support_handler
from utils.database import create_tables
from utils.motivation.button_click_tracker import load_motivational_messages
from utils.reminders import register_reminders_handlers

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def set_persistent_menu(application):
    """Set up the persistent menu commands."""
    commands = [
        BotCommand("main_menu", "القائمة الرئيسية"),
        BotCommand("help_support", "المساعدة والدعم"),
        BotCommand("personal_assistant_chat", "محادثة المساعد الشخصي"),
        BotCommand("end_chat", "إنهاء المحادثة المساعد الشخصي"),
        BotCommand("clear_history", "مسح ذاكرة محادثة مساعد شخصي"),
    ]
    await application.bot.set_my_commands(commands)


def main():
    """Start the bot."""
    loop = asyncio.get_event_loop()
    # Check if the database file exists
    if not os.path.exists(DATABASE_FILE):
        create_tables()

    request = HTTPXRequest(
        connect_timeout=20.0,  # Increase the connection timeout (default is 5.0)
        read_timeout=30.0,  # Increase the read timeout (default is 5.0)
    )
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .request(request)
        .post_init(set_persistent_menu)
        .build()
    )

    loop.run_until_complete(load_motivational_messages())

    # Add conversation handler
    register_converstaion_handlers(application)

    # Add main menu command handler
    application.add_handler(CommandHandler("main_menu", show_main_menu))
    register_all_main_menu_handlers(application)
    application.add_handler(CallbackQueryHandler(handle_main_menu_option))

    application.add_handler(personal_assistant_handler)
    application.add_handler(CommandHandler("help_support", help_support_handler))

    # Run the reminder setup on the loop
    loop.run_until_complete(register_reminders_handlers(application))

    # Start the bot. This will block until the bot stops.
    application.run_polling(poll_interval=0.5, timeout=15)


if __name__ == "__main__":
    main()
