"""Tests for telegram_bot.routers.start — /start command handler."""

from unittest.mock import MagicMock

from aiogram.exceptions import TelegramAPIError

from src.telegram_bot.routers.start import cmd_start
from src.telegram_bot.utility.keyboard_builder import get_main_menu


# --- cmd_start ---


async def test_cmd_start_sends_welcome_with_commands_and_menu(mock_message):
    await cmd_start(mock_message)

    mock_message.answer.assert_called_once()
    text = mock_message.answer.call_args[0][0]
    assert "Welcome" in text
    for cmd in (
        "/add_search",
        "/my_searches",
        "/start_searching",
        "/stop_searching",
        "/status",
    ):
        assert cmd in text, f"{cmd} missing from welcome text"
    kwargs = mock_message.answer.call_args[1]
    assert kwargs["reply_markup"] == get_main_menu()


async def test_telegram_api_error_no_retry(mock_message):
    mock_message.answer.side_effect = TelegramAPIError(
        method=MagicMock(), message="error"
    )

    await cmd_start(mock_message)

    mock_message.answer.assert_called_once()
