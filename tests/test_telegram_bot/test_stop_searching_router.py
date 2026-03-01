"""Tests for telegram_bot.routers.stop_searching."""

from unittest.mock import MagicMock

from aiogram.exceptions import TelegramAPIError

from src.telegram_bot.routers.stop_searching import cmd_stop_searching
from src.message_bus.events.stop_searching_event import StopSearchingEvent


EXPECTED_ANSWER = (
    "⏸️ Search monitoring paused.\n\n"
    "Your searches are saved.\n"
    "Use /start_searching to resume."
)


# --- cmd_stop_searching ---


async def test_publishes_event_and_sends_confirmation(mock_message, mock_message_bus):
    await cmd_stop_searching(mock_message, mock_message_bus)

    mock_message_bus.publish.assert_called_once_with(StopSearchingEvent())
    mock_message.answer.assert_called_once_with(EXPECTED_ANSWER)


async def test_publish_error_still_sends_message(mock_message, mock_message_bus):
    mock_message_bus.publish.side_effect = Exception("bus error")

    await cmd_stop_searching(mock_message, mock_message_bus)

    mock_message.answer.assert_called_once_with(EXPECTED_ANSWER)


async def test_answer_error_caught(mock_message, mock_message_bus):
    mock_message.answer.side_effect = TelegramAPIError(
        method=MagicMock(), message="send error"
    )

    await cmd_stop_searching(mock_message, mock_message_bus)

    mock_message_bus.publish.assert_called_once_with(StopSearchingEvent())


async def test_both_fail_caught(mock_message, mock_message_bus):
    mock_message_bus.publish.side_effect = Exception("bus error")
    mock_message.answer.side_effect = TelegramAPIError(
        method=MagicMock(), message="send error"
    )

    await cmd_stop_searching(mock_message, mock_message_bus)

    mock_message_bus.publish.assert_called_once_with(StopSearchingEvent())
    mock_message.answer.assert_called_once_with(EXPECTED_ANSWER)


async def test_publish_called_before_answer(mock_message, mock_message_bus):
    call_order = []
    mock_message_bus.publish.side_effect = lambda *_: call_order.append("publish")
    mock_message.answer.side_effect = lambda *_: call_order.append("answer")

    await cmd_stop_searching(mock_message, mock_message_bus)

    assert call_order == ["publish", "answer"]
