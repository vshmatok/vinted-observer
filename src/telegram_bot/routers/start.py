import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from src.telegram_bot.utility.keyboard_builder import get_main_menu

logger = logging.getLogger(__name__)
start_router = Router()


@start_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command by sending a welcome message and main menu."""

    try:
        await message.answer(
            "👋 <b>Welcome to Vinted listings bot!</b>\n\n"
            "I'll help you monitor vinted and notify you "
            "when new items matching your criteria appear.\n\n"
            "📝 <b>Available commands:</b>\n"
            "/add_search - Create new search\n"
            "/my_searches - View active searches\n"
            "/start_searching - Start monitoring\n"
            "/stop_searching - Stop monitoring\n"
            "/status - View bot status\n\n"
            
            "Get started by creating your first search!",
            reply_markup=get_main_menu(),
        )
    except Exception as e:
        logger.error(f"Failed to send start command response to user {message.chat.id}: {e}", exc_info=True)

