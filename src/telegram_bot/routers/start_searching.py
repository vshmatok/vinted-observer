import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from src.message_bus.message_bus import MessageBus
from src.message_bus.events.start_searching_event import StartSearchingEvent

start_searching_router = Router()
logger = logging.getLogger(__name__)


@start_searching_router.message(Command("start_searching"))
@start_searching_router.message(F.text == "▶️ Start Monitoring")
async def cmd_start_searching(message: Message, message_bus: MessageBus) -> None:
    """Start search monitoring. Logs errors but continues operation."""
    try:
        await message_bus.publish(StartSearchingEvent())
    except Exception as e:
        logger.error(f"Failed to publish start searching event for user {message.chat.id}: {e}", exc_info=True)

    try:
        await message.answer(
            "✅ Search monitoring activated!\n\n"
            "I'll notify you when new results appear.\n"
            "Use /stop_searching to pause."
        )
    except Exception as e:
        logger.error(f"Failed to send start monitoring confirmation to user {message.chat.id}: {e}", exc_info=True)
