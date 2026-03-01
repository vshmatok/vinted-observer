from html import escape
from typing import Tuple

from aiogram.types import InlineKeyboardMarkup

from src.telegram_bot.models.search import Search
from src.telegram_bot.utility.keyboard_builder import get_search_actions_keyboard


def build_my_search_listing_message(search: Search) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Build the message text and reply markup for a given search.

    Args:
        search (Search): The search object containing query and price range.

    Returns:
        Tuple[str, dict]: A tuple containing the formatted message text and
                          the reply markup dictionary.
    """
    message_text = (
        f"📌 <b>{escape(search.query)}</b>\n" f"💰 ${search.price_min} - ${search.price_max}\n"
    )
    reply_markup = get_search_actions_keyboard(search.id)
    return message_text, reply_markup
