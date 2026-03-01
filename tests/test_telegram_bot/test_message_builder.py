"""Tests for telegram_bot.utility.message_builder."""

import pytest
from aiogram.types import InlineKeyboardMarkup

from src.telegram_bot.utility.message_builder import build_my_search_listing_message


# --- build_my_search_listing_message ---


def test_full_message_format(make_search):
    search = make_search(query="shoes", price_min=10.0, price_max=50.0)
    text, _ = build_my_search_listing_message(search)
    assert text == "\U0001f4cc <b>shoes</b>\n\U0001f4b0 $10.0 - $50.0\n"


def test_contains_query_in_bold(make_search):
    search = make_search(query="nike shoes")
    text, _ = build_my_search_listing_message(search)
    assert "<b>nike shoes</b>" in text


def test_contains_price_range(make_search):
    search = make_search(price_min=10.0, price_max=100.0)
    text, _ = build_my_search_listing_message(search)
    assert "$10.0" in text
    assert "$100.0" in text


def test_keyboard_is_inline_markup_with_edit_and_remove(make_search):
    search = make_search(id=5)
    _, markup = build_my_search_listing_message(search)
    assert isinstance(markup, InlineKeyboardMarkup)
    buttons = markup.inline_keyboard[0]
    assert len(buttons) == 2
    assert buttons[0].callback_data == "edit_5"
    assert buttons[1].callback_data == "remove_5"


def test_uses_correct_search_id(make_search):
    search = make_search(id=99, price_min=0, price_max=50.0)
    _, markup = build_my_search_listing_message(search)
    buttons = markup.inline_keyboard[0]
    assert buttons[0].callback_data == "edit_99"
    assert buttons[1].callback_data == "remove_99"


# --- Edge cases ---


def test_empty_query(make_search):
    search = make_search(query="")
    text, _ = build_my_search_listing_message(search)
    assert "<b></b>" in text


def test_query_with_html_characters(make_search):
    search = make_search(query='<script>alert("xss")</script>')
    text, _ = build_my_search_listing_message(search)
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_price_zero(make_search):
    search = make_search(price_min=0.0, price_max=0.0)
    text, _ = build_my_search_listing_message(search)
    assert "$0.0" in text


def test_price_precision(make_search):
    search = make_search(price_min=9.99, price_max=19.99)
    text, _ = build_my_search_listing_message(search)
    assert "$9.99" in text
    assert "$19.99" in text


def test_price_min_greater_than_max(make_search):
    search = make_search(price_min=100.0, price_max=10.0)
    text, _ = build_my_search_listing_message(search)
    assert "$100.0" in text
    assert "$10.0" in text


def test_large_price_values(make_search):
    search = make_search(price_min=0.0, price_max=999999.99)
    text, _ = build_my_search_listing_message(search)
    assert "$999999.99" in text
