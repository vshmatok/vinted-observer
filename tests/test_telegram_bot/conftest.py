"""Shared fixtures for telegram_bot tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Message, CallbackQuery, Chat
from aiogram.fsm.context import FSMContext

from src.message_bus.message_bus import MessageBus
from src.telegram_bot.bot import TelegramBot
from src.telegram_bot.models.search import Search
from src.telegram_bot.utility.keyboard_builder import (
    get_buy_button_keyboard,
    get_edit_keyboard,
    get_main_menu,
)
from tests.test_telegram_bot.helpers import make_vinted_item

# Valid format for aiogram token validation: "<digits>:<alphanumeric>"
TEST_TOKEN = "123456789:ABCDefGHIJKLmnopQRSTuvwxyz"


@pytest.fixture
def mock_message_bus():
    """AsyncMock MessageBus with default empty returns."""
    bus = AsyncMock(spec=MessageBus)
    bus.query.return_value = []
    bus.execute.return_value = None
    bus.publish.return_value = None
    return bus


@pytest.fixture
def mock_chat():
    """MagicMock Chat with id=12345."""
    chat = MagicMock(spec=Chat)
    chat.id = 12345
    return chat


@pytest.fixture
def mock_bot():
    """AsyncMock Bot."""
    bot = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    return bot


@pytest.fixture
def mock_message(mock_chat, mock_bot):
    """AsyncMock Message with async answer() and bot attr."""
    msg = AsyncMock(spec=Message)
    msg.chat = mock_chat
    msg.message_id = 100
    msg.answer = AsyncMock()
    msg.bot = mock_bot
    msg.text = None
    return msg


@pytest.fixture
def mock_callback_query(mock_message):
    """AsyncMock CallbackQuery with answer(), message.edit_text(), message.delete()."""
    callback = AsyncMock(spec=CallbackQuery)
    callback.message = mock_message
    callback.data = None
    callback.answer = AsyncMock()
    # These are on the message, not the callback itself
    mock_message.edit_text = AsyncMock()
    mock_message.delete = AsyncMock()
    return callback


@pytest.fixture
def mock_fsm_context():
    """AsyncMock FSMContext with get_data, set_state, update_data, clear."""
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def sample_nike_search():
    """Standard search fixture for telegram_bot tests."""
    return Search(
        id=1, chat_id=12345, query="nike shoes", price_min=10.0, price_max=100.0
    )


@pytest.fixture
def buy_keyboard():
    return get_buy_button_keyboard("https://example.com/buy")


@pytest.fixture
def edit_keyboard():
    return get_edit_keyboard(5)


@pytest.fixture
def main_menu():
    return get_main_menu()


@pytest.fixture
def edit_fsm_data(mock_fsm_context):
    """FSMContext pre-loaded with standard edit session data."""
    mock_fsm_context.get_data.return_value = {
        "search_id": 1,
        "message_id": 100,
        "chat_id": 12345,
    }
    return mock_fsm_context


@pytest.fixture
def make_search():
    """Factory fixture for creating Search objects with sensible defaults."""

    def _make(
        id: int = 1,
        chat_id: int | str = 123,
        query: str = "test",
        price_min: float = 10.0,
        price_max: float = 100.0,
    ) -> Search:
        return Search(
            id=id,
            chat_id=chat_id,
            query=query,
            price_min=price_min,
            price_max=price_max,
        )

    return _make


@pytest.fixture(scope="module")
def telegram_bot_instance():
    """Single TelegramBot instance shared across all init tests."""
    bus = AsyncMock()
    return TelegramBot(message_bus=bus, token=TEST_TOKEN), bus


@pytest.fixture
def notification_bot(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    original_bot = bot.bot
    bot.bot = AsyncMock()
    yield bot
    bot.bot = original_bot
