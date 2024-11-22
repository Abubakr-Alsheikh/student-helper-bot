from telegram.ext import (
    Application,
    CallbackQueryHandler,
)

from main_menu_sections.level_determination.level_determination_handler import (
    LEVEL_DETERMINATION_HANDLERS,
    LEVEL_DETERMINATION_HANDLERS_PATTERN,
    level_conv_handler,
    level_conv_ai_assistance_handler,
)
from main_menu_sections.traditional_learning.traditional_learning_handler import (
    TRADITIONAL_LEARNING_HANDLERS,
    TRADITIONAL_LEARNING_HANDLERS_PATTERNS,
)
from main_menu_sections.conversation_learning.conversation_learning_handler import (
    CONVERSATION_LEARNING_HANDLERS,
    conversation_learning_conv_handler,
)
from main_menu_sections.tests.tests_handler import (
    TESTS_HANDLERS,
    TESTS_HANDLERS_PATTERN,
    tests_conv_handler,
    test_conv_ai_assistance_handler,
)
from main_menu_sections.tips_and_strategies.tips_and_strategies_handler import (
    TIPS_AND_STRATEGIES_HANDLERS,
    TIPS_AND_STRATEGIES_HANDLERS_PATTER,
    tips_and_strategies_conv_handler,
)
from main_menu_sections.statistics.statistics_handler import STATISTICS_HANDLERS
from main_menu_sections.help_and_settings.help_and_settings_handler import (
    HELP_AND_SETTINGS_HANDLERS,
    HELP_AND_SETTINGS_HANDLERS_PATTERN,
)
from main_menu_sections.subscription.subscription_handler import (
    SUBSCRIPTION_HANDLERS,
    subscription_conv_handler,
)
from main_menu_sections.rewards.rewards_handler import REWARDS_HANDLERS
from main_menu_sections.design_for_you.design_for_you import (
    register_design_handlers,
)
from utils.section_manager import check_unlocked_sections


# Dictionary for handlers
CALLBACK_DATA_HANDLERS = {
    **LEVEL_DETERMINATION_HANDLERS,
    **TRADITIONAL_LEARNING_HANDLERS,
    **CONVERSATION_LEARNING_HANDLERS,
    **TESTS_HANDLERS,
    **TIPS_AND_STRATEGIES_HANDLERS,
    **STATISTICS_HANDLERS,
    **HELP_AND_SETTINGS_HANDLERS,
    **SUBSCRIPTION_HANDLERS,
    **REWARDS_HANDLERS,
}

# Dictionary for handlers with patterns
PATTERN_BASED_HANDLERS = {
    **LEVEL_DETERMINATION_HANDLERS_PATTERN,
    **TESTS_HANDLERS_PATTERN,
    **HELP_AND_SETTINGS_HANDLERS_PATTERN,
    **TRADITIONAL_LEARNING_HANDLERS_PATTERNS,
    **TIPS_AND_STRATEGIES_HANDLERS_PATTER,
}

# List for converstation handlers
CONVERSATION_HANDLERS = {
    level_conv_handler,
    level_conv_ai_assistance_handler,
    subscription_conv_handler,
    tests_conv_handler,
    test_conv_ai_assistance_handler,
    conversation_learning_conv_handler,
    tips_and_strategies_conv_handler,
}

def register_all_main_menu_handlers(application: Application):
    """Registers all handlers for the bot."""

    application.job_queue.run_repeating(check_unlocked_sections, interval=3600)

    for converstaion_handler in CONVERSATION_HANDLERS:
        application.add_handler(converstaion_handler)

    register_design_handlers(application)

    # Register handlers from CALLBACK_DATA_HANDLERS
    for callback_data, handler in CALLBACK_DATA_HANDLERS.items():
        application.add_handler(CallbackQueryHandler(handler, pattern=callback_data))

    # Register pattern-based handlers
    for pattern, handler in PATTERN_BASED_HANDLERS.items():
        application.add_handler(CallbackQueryHandler(handler, pattern=pattern))
