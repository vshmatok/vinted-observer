"""Tests for telegram_bot.routers.status — /status command handler."""

from unittest.mock import MagicMock

from aiogram.exceptions import TelegramAPIError

from src.telegram_bot.routers.status import cmd_status
from src.message_bus.queries.get_status_report_query import GetStatusReportQuery


# --- cmd_status: happy path ---


async def test_queries_status_report_and_sends_result(mock_message, mock_message_bus):
    mock_message_bus.query.return_value = "Bot running fine"

    await cmd_status(mock_message, mock_message_bus)

    mock_message_bus.query.assert_called_once()
    query = mock_message_bus.query.call_args[0][0]
    assert isinstance(query, GetStatusReportQuery)
    mock_message.answer.assert_called_once_with("Bot running fine")


# --- cmd_status: errors are caught and logged ---


async def test_telegram_api_error_caught(mock_message, mock_message_bus):
    mock_message_bus.query.return_value = "Status OK"
    mock_message.answer.side_effect = TelegramAPIError(
        method=MagicMock(), message="send error"
    )

    await cmd_status(mock_message, mock_message_bus)

    mock_message.answer.assert_called_once_with("Status OK")


async def test_query_error_caught(mock_message, mock_message_bus):
    mock_message_bus.query.side_effect = Exception("db error")

    await cmd_status(mock_message, mock_message_bus)

    mock_message.answer.assert_not_called()


# --- cmd_status: query returns None ---


async def test_query_returns_none(mock_message, mock_message_bus):
    mock_message_bus.query.return_value = None

    await cmd_status(mock_message, mock_message_bus)

    mock_message.answer.assert_called_once_with(None)
