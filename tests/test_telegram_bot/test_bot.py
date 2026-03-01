"""Tests for TelegramBot class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.exceptions import TelegramAPIError

from src.telegram_bot.bot import TelegramBot
from src.telegram_bot.routers.start import start_router
from src.telegram_bot.routers.start_searching import start_searching_router
from src.telegram_bot.routers.stop_searching import stop_searching_router
from src.telegram_bot.routers.my_searches import my_searches_router
from src.telegram_bot.routers.new_search import new_search_router
from src.telegram_bot.routers.status import status_router
from src.message_bus.events.item_found_event import ItemFoundEvent
from src.vinted_network_client.models.vinted_price import VintedPrice
from tests.test_telegram_bot.helpers import make_vinted_item

# Valid format for aiogram token validation: "<digits>:<alphanumeric>"
TEST_TOKEN = "123456789:ABCDefGHIJKLmnopQRSTuvwxyz"


# --- __init__ ---
# Routers are module-level singletons. Once include_router is called they are
# attached to a dispatcher and cannot be re-attached. We therefore create
# *one* TelegramBot per module and run all __init__ assertions against it.


@pytest.fixture(scope="module")
def telegram_bot_instance():
    """Single TelegramBot instance shared across all init tests."""
    bus = AsyncMock()
    return TelegramBot(message_bus=bus, token=TEST_TOKEN), bus


def test_creates_dispatcher(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    assert bot.dp is not None


def test_creates_bot_with_token(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    assert bot.bot is not None


def test_stores_message_bus(telegram_bot_instance):
    bot, bus = telegram_bot_instance
    assert bot.message_bus is bus


def test_injects_bus_into_dp(telegram_bot_instance):
    bot, bus = telegram_bot_instance
    assert bot.dp["message_bus"] is bus


def test_includes_all_routers(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    registered = bot.dp.sub_routers
    assert len(registered) == 6
    assert start_router in registered
    assert start_searching_router in registered
    assert stop_searching_router in registered
    assert my_searches_router in registered
    assert new_search_router in registered
    assert status_router in registered


# --- start ---


async def test_calls_start_polling(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    with patch.object(bot.dp, "start_polling", new_callable=AsyncMock) as mock_poll:
        await bot.start()
        mock_poll.assert_called_once_with(bot.bot)


async def test_reraises_telegram_api_error(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    with patch.object(
        bot.dp,
        "start_polling",
        new_callable=AsyncMock,
        side_effect=TelegramAPIError(method=MagicMock(), message="api error"),
    ):
        with pytest.raises(TelegramAPIError):
            await bot.start()


async def test_reraises_generic_exception(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    with patch.object(
        bot.dp,
        "start_polling",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected"),
    ):
        with pytest.raises(RuntimeError):
            await bot.start()


# --- send_new_item_notification ---


def _make_event(**item_kwargs) -> ItemFoundEvent:
    item = make_vinted_item(**item_kwargs)
    return ItemFoundEvent(chat_id=12345, item=item)


@pytest.fixture
def notification_bot(telegram_bot_instance):
    bot, _ = telegram_bot_instance
    original_bot = bot.bot
    bot.bot = AsyncMock()
    yield bot
    bot.bot = original_bot


async def test_sends_photo_when_url_present(notification_bot):
    photo = MagicMock()
    photo.full_size_url = "https://photo.url/img.jpg"
    event = _make_event(photo=photo)

    await notification_bot.send_new_item_notification(event)

    notification_bot.bot.send_photo.assert_called_once()
    kwargs = notification_bot.bot.send_photo.call_args[1]
    assert kwargs["chat_id"] == 12345
    assert kwargs["photo"] == "https://photo.url/img.jpg"
    assert "Vintage Jacket" in kwargs["caption"]
    assert kwargs["reply_markup"] is not None
    notification_bot.bot.send_message.assert_not_called()


async def test_sends_message_when_no_photo(notification_bot):
    event = _make_event(photo=None)

    await notification_bot.send_new_item_notification(event)

    notification_bot.bot.send_message.assert_called_once()
    kwargs = notification_bot.bot.send_message.call_args[1]
    assert kwargs["chat_id"] == 12345
    assert "Vintage Jacket" in kwargs["text"]
    assert kwargs["reply_markup"] is not None
    notification_bot.bot.send_photo.assert_not_called()


async def test_sends_message_when_photo_has_no_url(notification_bot):
    photo = MagicMock()
    photo.full_size_url = None
    event = _make_event(photo=photo)

    await notification_bot.send_new_item_notification(event)

    notification_bot.bot.send_message.assert_called_once()
    kwargs = notification_bot.bot.send_message.call_args[1]
    assert kwargs["chat_id"] == 12345
    assert "Vintage Jacket" in kwargs["text"]
    assert kwargs["reply_markup"] is not None
    notification_bot.bot.send_photo.assert_not_called()


# --- caption content (parameterized) ---


@pytest.mark.parametrize(
    "item_kwargs,expected",
    [
        ({"title": "Cool Jacket"}, "Cool Jacket"),
        (
            {"total_item_price": VintedPrice(amount=29.99, currency_code="EUR")},
            "29.99",
        ),
        ({"brand_title": "Nike"}, "Nike"),
        ({"size_title": "L"}, "L"),
        (
            {"url": "https://vinted.pl/items/42"},
            "https://vinted.pl/items/42",
        ),
    ],
    ids=["title", "price", "brand", "size", "url"],
)
async def test_caption_includes_field(notification_bot, item_kwargs, expected):
    event = _make_event(**item_kwargs)

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_message.call_args[1]
    assert expected in kwargs["text"]


async def test_chat_id_forwarded_to_send_message(notification_bot):
    event = _make_event(photo=None)

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_message.call_args[1]
    assert kwargs["chat_id"] == 12345


async def test_chat_id_forwarded_to_send_photo(notification_bot):
    photo = MagicMock()
    photo.full_size_url = "https://photo.url/img.jpg"
    event = _make_event(photo=photo)

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_photo.call_args[1]
    assert kwargs["chat_id"] == 12345


async def test_send_photo_receives_caption_and_reply_markup(notification_bot):
    photo = MagicMock()
    photo.full_size_url = "https://photo.url/img.jpg"
    event = _make_event(
        photo=photo,
        title="Cool Jacket",
        buy_url="https://vinted.pl/buy/42",
    )

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_photo.call_args[1]
    assert "Cool Jacket" in kwargs["caption"]
    assert kwargs["reply_markup"] is not None


async def test_buy_keyboard_present(notification_bot):
    event = _make_event(buy_url="https://vinted.pl/buy/42")

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_message.call_args[1]
    assert kwargs["reply_markup"] is not None


async def test_buy_keyboard_absent_when_no_buy_url(notification_bot):
    event = _make_event(buy_url=None)

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_message.call_args[1]
    assert kwargs["reply_markup"] is None


async def test_minimal_item(notification_bot):
    event = _make_event(
        title=None,
        photo=None,
        price=None,
        total_item_price=None,
        brand_title=None,
        size_title=None,
        url=None,
        buy_url=None,
    )

    await notification_bot.send_new_item_notification(event)

    notification_bot.bot.send_message.assert_called_once()
    kwargs = notification_bot.bot.send_message.call_args[1]
    assert kwargs["chat_id"] == 12345
    assert kwargs["reply_markup"] is None


# --- caption HTML structure ---


async def test_caption_html_bold_title(notification_bot):
    event = _make_event(title="Cool Jacket")

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_message.call_args[1]
    assert "<b>Cool Jacket</b>" in kwargs["text"]


async def test_caption_html_link(notification_bot):
    event = _make_event(url="https://vinted.pl/items/42")

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_message.call_args[1]
    assert '<a href="https://vinted.pl/items/42">View on Vinted</a>' in kwargs["text"]


async def test_caption_ordering(notification_bot):
    event = _make_event(
        title="Cool Jacket",
        total_item_price=VintedPrice(amount=29.99, currency_code="EUR"),
        brand_title="Nike",
        size_title="L",
        url="https://vinted.pl/items/42",
    )

    await notification_bot.send_new_item_notification(event)

    kwargs = notification_bot.bot.send_message.call_args[1]
    text = kwargs["text"]
    lines = text.split("\n")
    assert "<b>Cool Jacket</b>" in lines[0]
    assert "29.99" in lines[1]
    assert "Nike" in lines[2]
    assert "Size: L" in lines[3]


# --- HTML escaping ---


async def test_title_with_html_characters_is_escaped(notification_bot):
    event = _make_event(title='<script>alert("xss")</script>')

    await notification_bot.send_new_item_notification(event)

    text = notification_bot.bot.send_message.call_args[1]["text"]
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


async def test_brand_title_with_html_characters_is_escaped(notification_bot):
    event = _make_event(brand_title="H&M <b>bold</b>")

    await notification_bot.send_new_item_notification(event)

    text = notification_bot.bot.send_message.call_args[1]["text"]
    assert "<b>bold</b>" not in text
    assert "H&amp;M" in text


async def test_size_title_with_html_characters_is_escaped(notification_bot):
    event = _make_event(size_title='<img src="x">')

    await notification_bot.send_new_item_notification(event)

    text = notification_bot.bot.send_message.call_args[1]["text"]
    assert '<img src="x">' not in text
    assert "&lt;img" in text


async def test_url_with_ampersand_is_escaped(notification_bot):
    event = _make_event(url="https://vinted.pl/items/42?a=1&b=2")

    await notification_bot.send_new_item_notification(event)

    text = notification_bot.bot.send_message.call_args[1]["text"]
    assert "a=1&amp;b=2" in text


# --- error handling (parameterized, both send paths) ---




