"""Tests for telegram_bot.utility.keyboard_builder."""

import pytest
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from src.telegram_bot.utility.keyboard_builder import (
    get_search_actions_keyboard,
    get_edit_keyboard,
    get_cancel_edit_reply_keyboard,
    get_cancel_create_reply_keyboard,
    get_confirmation_keyboard,
)


# --- get_buy_button_keyboard ---


def test_buy_button_returns_inline_keyboard(buy_keyboard):
    assert isinstance(buy_keyboard, InlineKeyboardMarkup)


def test_buy_button_has_one_button(buy_keyboard):
    assert len(buy_keyboard.inline_keyboard) == 1
    assert len(buy_keyboard.inline_keyboard[0]) == 1


def test_buy_button_has_url_and_text(buy_keyboard):
    button = buy_keyboard.inline_keyboard[0][0]
    assert button.url == "https://example.com/buy"
    assert button.text == "🛒 Buy Now"


# --- get_search_actions_keyboard ---


def test_search_actions_returns_inline_keyboard():
    kb = get_search_actions_keyboard(1)
    assert isinstance(kb, InlineKeyboardMarkup)


@pytest.mark.parametrize("search_id", [0, 1, 42, 999])
def test_search_actions_callback_data(search_id):
    kb = get_search_actions_keyboard(search_id)
    buttons = kb.inline_keyboard[0]
    assert len(buttons) == 2
    assert buttons[0].callback_data == f"edit_{search_id}"
    assert buttons[1].callback_data == f"remove_{search_id}"


def test_search_actions_button_texts():
    kb = get_search_actions_keyboard(1)
    buttons = kb.inline_keyboard[0]
    assert buttons[0].text == "✏️ Edit"
    assert buttons[1].text == "🗑️ Remove"


# --- get_edit_keyboard ---


def test_edit_keyboard_returns_inline_keyboard(edit_keyboard):
    assert isinstance(edit_keyboard, InlineKeyboardMarkup)


def test_edit_keyboard_row_layout(edit_keyboard):
    assert len(edit_keyboard.inline_keyboard) == 2
    assert len(edit_keyboard.inline_keyboard[0]) == 3
    assert len(edit_keyboard.inline_keyboard[1]) == 1


def test_edit_keyboard_button_texts(edit_keyboard):
    row1 = edit_keyboard.inline_keyboard[0]
    row2 = edit_keyboard.inline_keyboard[1]
    assert row1[0].text == "✏️ Search term"
    assert row1[1].text == "✏️ Min Price"
    assert row1[2].text == "✏️ Max Price"
    assert row2[0].text == "❌ Cancel"


@pytest.mark.parametrize("search_id", [0, 1, 5, 999])
def test_edit_keyboard_callback_data(search_id):
    kb = get_edit_keyboard(search_id)
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    assert all_buttons[0].callback_data == f"editfield_{search_id}_query"
    assert all_buttons[1].callback_data == f"editfield_{search_id}_min"
    assert all_buttons[2].callback_data == f"editfield_{search_id}_max"
    assert all_buttons[3].callback_data == f"cancel_edit_{search_id}"


# --- get_cancel_edit_reply_keyboard ---


def test_cancel_edit_returns_reply_keyboard():
    kb = get_cancel_edit_reply_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)


def test_cancel_edit_has_one_button_with_text():
    kb = get_cancel_edit_reply_keyboard()
    all_buttons = [btn for row in kb.keyboard for btn in row]
    assert len(all_buttons) == 1
    assert all_buttons[0].text == "❌ Cancel editing"


# --- get_cancel_create_reply_keyboard ---


def test_cancel_create_returns_reply_keyboard():
    kb = get_cancel_create_reply_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)


def test_cancel_create_has_one_button_with_text():
    kb = get_cancel_create_reply_keyboard()
    all_buttons = [btn for row in kb.keyboard for btn in row]
    assert len(all_buttons) == 1
    assert all_buttons[0].text == "❌ Cancel creating"


# --- get_confirmation_keyboard ---


def test_confirmation_returns_inline_keyboard():
    kb = get_confirmation_keyboard(7)
    assert isinstance(kb, InlineKeyboardMarkup)


def test_confirmation_button_texts():
    kb = get_confirmation_keyboard(7)
    buttons = kb.inline_keyboard[0]
    assert buttons[0].text == "✓ Yes, delete"
    assert buttons[1].text == "✗ No, keep it"


@pytest.mark.parametrize("search_id", [0, 1, 7, 999])
def test_confirmation_callback_data(search_id):
    kb = get_confirmation_keyboard(search_id)
    buttons = kb.inline_keyboard[0]
    assert len(buttons) == 2
    assert buttons[0].callback_data == f"confirm_remove_{search_id}"
    assert buttons[1].callback_data == f"cancel_remove_{search_id}"


# --- get_main_menu ---


def test_main_menu_returns_reply_keyboard(main_menu):
    assert isinstance(main_menu, ReplyKeyboardMarkup)


def test_main_menu_has_resize_keyboard(main_menu):
    assert main_menu.resize_keyboard is True


def test_main_menu_row_layout(main_menu):
    assert len(main_menu.keyboard) == 2
    assert len(main_menu.keyboard[0]) == 2
    assert len(main_menu.keyboard[1]) == 2


def test_main_menu_button_texts(main_menu):
    buttons = [btn for row in main_menu.keyboard for btn in row]
    assert buttons[0].text == "🔍 New Search"
    assert buttons[1].text == "📋 My Searches"
    assert buttons[2].text == "▶️ Start Monitoring"
    assert buttons[3].text == "⏸️ Stop Monitoring"
