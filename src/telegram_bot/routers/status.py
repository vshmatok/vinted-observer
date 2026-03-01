import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from src.message_bus.message_bus import MessageBus
from src.message_bus.queries.get_status_report_query import GetStatusReportQuery

status_router = Router()
logger = logging.getLogger(__name__)


@status_router.message(Command("status"))
async def cmd_status(message: Message, message_bus: MessageBus) -> None:
    """Display bot status information. Logs errors but continues operation."""

    try:
        status_message = await message_bus.query(GetStatusReportQuery())
        await message.answer(status_message)
    except Exception as e:
        logger.error(f"Failed to handle status command for user {message.chat.id}: {e}", exc_info=True)
