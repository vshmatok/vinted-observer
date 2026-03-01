import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from src.message_bus.message_bus import MessageBus
from src.message_bus.events.stop_searching_event import StopSearchingEvent

stop_searching_router = Router()
logger = logging.getLogger(__name__)


@stop_searching_router.message(Command("stop_searching"))
@stop_searching_router.message(F.text == "⏸️ Stop Monitoring")
async def cmd_stop_searching(message: Message, message_bus: MessageBus) -> None:
    """Stop search monitoring. Logs errors but continues operation."""
    try:
        await message_bus.publish(StopSearchingEvent())
    except Exception as e:
        logger.error(f"Failed to publish stop searching event for user {message.chat.id}: {e}", exc_info=True)

    try:
        await message.answer(
            "⏸️ Search monitoring paused.\n\n"
            "Your searches are saved.\n"
            "Use /start_searching to resume."
        )
    except Exception as e:
        logger.error(f"Failed to send stop monitoring confirmation to user {message.chat.id}: {e}", exc_info=True)
