from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_buy_button_keyboard(url: str) -> InlineKeyboardMarkup:
    """Single URL button for purchase link"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Buy Now", url=url)
    return builder.as_markup()


def get_search_actions_keyboard(search_id: int) -> InlineKeyboardMarkup:
    """Edit/Remove buttons for each search"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit", callback_data=f"edit_{search_id}")
    builder.button(text="🗑️ Remove", callback_data=f"remove_{search_id}")
    return builder.as_markup()


def get_edit_keyboard(search_id: int) -> InlineKeyboardMarkup:
    """Edit buttons for search item"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Search term", callback_data=f"editfield_{search_id}_query")
    builder.button(text="✏️ Min Price", callback_data=f"editfield_{search_id}_min")
    builder.button(text="✏️ Max Price", callback_data=f"editfield_{search_id}_max")
    builder.button(text="❌ Cancel", callback_data=f"cancel_edit_{search_id}")
    builder.adjust(3, 1)  # 3 fields, then cancel below
    return builder.as_markup()


def get_cancel_edit_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Cancel editing")
    return builder.as_markup()

def get_cancel_create_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Cancel creating")
    return builder.as_markup()

def get_confirmation_keyboard(search_id: int) -> InlineKeyboardMarkup:
    """Confirm/Cancel for destructive actions"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✓ Yes, delete", callback_data=f"confirm_remove_{search_id}")
    builder.button(text="✗ No, keep it", callback_data=f"cancel_remove_{search_id}")
    return builder.as_markup()


def get_main_menu() -> ReplyKeyboardMarkup:
    """Persistent menu with common actions"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 New Search")
    builder.button(text="📋 My Searches")
    builder.button(text="▶️ Start Monitoring")
    builder.button(text="⏸️ Stop Monitoring")
    builder.adjust(2)  # 2x2 grid
    return builder.as_markup(resize_keyboard=True)
