"""Tests for telegram_bot.routers.start_searching."""

from src.telegram_bot.routers.start_searching import cmd_start_searching
from src.message_bus.events.start_searching_event import StartSearchingEvent


# --- cmd_start_searching ---


async def test_publishes_event_and_sends_confirmation(mock_message, mock_message_bus):
    await cmd_start_searching(mock_message, mock_message_bus)

    mock_message_bus.publish.assert_called_once_with(StartSearchingEvent())
    mock_message.answer.assert_called_once()
    text = mock_message.answer.call_args[0][0]
    assert "Search monitoring activated" in text


async def test_publish_error_still_sends_message(mock_message, mock_message_bus):
    mock_message_bus.publish.side_effect = Exception("bus error")

    await cmd_start_searching(mock_message, mock_message_bus)

    mock_message.answer.assert_called_once()
    text = mock_message.answer.call_args[0][0]
    assert "Search monitoring activated" in text


async def test_answer_error_caught(mock_message, mock_message_bus):
    mock_message.answer.side_effect = RuntimeError("connection lost")

    # Should not raise
    await cmd_start_searching(mock_message, mock_message_bus)

    mock_message_bus.publish.assert_called_once_with(StartSearchingEvent())


async def test_publish_called_before_answer(mock_message, mock_message_bus):
    call_order = []
    mock_message_bus.publish.side_effect = lambda *_: call_order.append("publish")
    mock_message.answer.side_effect = lambda *_: call_order.append("answer")

    await cmd_start_searching(mock_message, mock_message_bus)

    assert call_order == ["publish", "answer"]
