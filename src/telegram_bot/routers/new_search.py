import logging
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from src.telegram_bot.utility.message_builder import build_my_search_listing_message
from src.telegram_bot.utility.keyboard_builder import get_cancel_create_reply_keyboard
from src.telegram_bot.utility.validators import (
    validate_search_query,
    validate_price,
    validate_price_range,
)
from src.telegram_bot.states.add_search_state import AddSearchState
from src.message_bus.message_bus import MessageBus
from src.message_bus.events.new_search_event import NewSearchEvent
from src.message_bus.commands.add_new_search_command import AddNewSearchCommand

new_search_router = Router()

logger = logging.getLogger(__name__)


@new_search_router.message(Command("add_search"))
@new_search_router.message(F.text == "🔍 New Search")
async def cmd_new_search(message: Message, state: FSMContext):
    try:
        await state.clear()  # Clear any previous FSM state
        await state.set_state(AddSearchState.waiting_for_search_term)
        await message.answer(
            "Enter the search term you want to monitor (e.g., 'vintage jacket'):",
            reply_markup=get_cancel_create_reply_keyboard(),
        )
    except Exception as e:
        logger.error(
            f"Failed to handle new search command for user {message.chat.id}: {e}",
            exc_info=True,
        )


# Do not move this below the edit handlers as they will handle text input first
@new_search_router.message(F.text == "❌ Cancel creating")
async def cancel_create(message: Message, state: FSMContext):
    try:
        await state.clear()  # Clear FSM state
        await message.answer("Creation cancelled", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.error(
            f"Failed to handle cancel create for user {message.chat.id}: {e}",
            exc_info=True,
        )


@new_search_router.message(AddSearchState.waiting_for_search_term)
async def add_query(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer(
                "Please enter a valid search term like 'vintage jacket'."
            )
            return

        result = validate_search_query(message.text)
        if not result.is_valid:
            await message.answer(result.error_message or "Invalid search query.")
            return

        query = message.text.strip()
        await state.update_data(query=query)
        await state.set_state(AddSearchState.waiting_for_price_min)
        await message.answer(
            "Enter the minimum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )
    except Exception as e:
        logger.error(
            f"Failed to handle add query for user {message.chat.id}: {e}",
            exc_info=True,
        )
        await state.clear()


@new_search_router.message(AddSearchState.waiting_for_price_min)
async def add_price_min(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer("Please enter a valid minimum price like '50'.")
            return

        result = validate_price(message.text, "minimum price")
        if not result.is_valid:
            await message.answer(result.error_message or "Invalid minimum price.")
            return

        # try\except is not needed here because of the previous validation
        min_price = float(message.text.strip())
        await state.update_data(price_min=min_price)
        await state.set_state(AddSearchState.waiting_for_price_max)
        await message.answer(
            "Enter the maximum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )
    except Exception as e:
        logger.error(
            f"Failed to handle add price min for user {message.chat.id}: {e}",
            exc_info=True,
        )
        await state.clear()


@new_search_router.message(AddSearchState.waiting_for_price_max)
async def add_price_max(message: Message, state: FSMContext, message_bus: MessageBus):
    try:
        if not message.text:
            await message.answer("Please enter a valid maximum price like '200'.")
            return

        result = validate_price(message.text, "maximum price")
        if not result.is_valid:
            await message.answer(result.error_message or "Invalid maximum price.")
            return

        # try\except is not needed here because of the previous validation
        max_price = float(message.text.strip())
        data = await state.get_data()
        query = data.get("query")
        price_min = data.get("price_min")

        if price_min is not None:
            range_result = validate_price_range(price_min, max_price)
            if not range_result.is_valid:
                await message.answer(
                    range_result.error_message or "Invalid price range."
                )
                return

        if not query or price_min is None:
            logger.error(
                f"Missing query or price_min in FSM data for user {message.chat.id}."
            )
            await message.answer(
                "An error occurred. Please start the search creation process again."
            )
            await state.clear()
            return

        await state.clear()

        try:
            added_search = await message_bus.execute(
                AddNewSearchCommand(
                    chat_id=message.chat.id,
                    query=query,
                    price_min=price_min,
                    price_max=max_price,
                )
            )
        except Exception as e:
            logger.error(
                f"Failed to add new search for user {message.chat.id}: {e}",
                exc_info=True,
            )
            return

        try:
            message_text, _ = build_my_search_listing_message(added_search)
        except Exception as e:
            logger.error(
                f"Failed to build message for search for user {message.chat.id}: {e}",
                exc_info=True,
            )
            message_text = f"Search created: {escape(query)}"  # Fallback message

        await message.answer("Search created successfully!")
        await message.answer(message_text, reply_markup=ReplyKeyboardRemove())

        try:
            await message_bus.publish(NewSearchEvent(search=added_search))
        except Exception as e:
            logger.error(
                f"Failed to publish new search event for user {message.chat.id}: {e}",
                exc_info=True,
            )

    except Exception as e:
        logger.error(
            f"Failed to handle add price max for user {message.chat.id}: {e}",
            exc_info=True,
        )
        await state.clear()
