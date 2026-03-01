import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from src.telegram_bot.models.search import Search
from src.telegram_bot.utility.message_builder import build_my_search_listing_message
from src.message_bus.message_bus import MessageBus
from src.message_bus.events.remove_search_event import RemoveSearchEvent
from src.message_bus.events.update_search_event import UpdateSearchEvent
from src.message_bus.queries.get_all_searches_query import GetAllSearchesQuery
from src.message_bus.commands.delete_search_command import DeleteSearchCommand
from src.message_bus.queries.get_search_by_id_query import GetSearchByIdQuery
from src.message_bus.commands.update_search_command import UpdateSearchCommand
from src.telegram_bot.utility.keyboard_builder import (
    get_confirmation_keyboard,
    get_edit_keyboard,
    get_cancel_edit_reply_keyboard,
)
from src.telegram_bot.utility.validators import (
    validate_search_query,
    validate_price,
    validate_edit_price_min,
    validate_edit_price_max,
)
from src.telegram_bot.states.edit_search_state import EditSearchState

my_searches_router = Router()

logger = logging.getLogger(__name__)


# List user's searches


@my_searches_router.message(Command("my_searches"))
@my_searches_router.message(F.text == "📋 My Searches")
async def cmd_my_searches(message: Message, message_bus: MessageBus):
    try:
        searches: list[Search] = await message_bus.query(GetAllSearchesQuery())
    except Exception as e:
        logger.error(
            f"Failed to get searches for user {message.chat.id}: {e}", exc_info=True
        )
        return

    if not searches:
        try:
            return await message.answer(
                "📭 You have no active searches yet.\n\n"
                "Use /add_search to create one!"
            )
        except Exception as e:
            logger.error(
                f"Failed to send no searches message to user {message.chat.id}: {e}",
                exc_info=True,
            )
            return

    # Format each search with action buttons
    for search in searches:
        try:
            message_text, reply_markup = build_my_search_listing_message(search)
            await message.answer(
                message_text,
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(
                f"Error sending search listing for search_id={search.id} to user {message.chat.id}: {e}",
                exc_info=True,
            )
            continue


# Handle "Remove" button press


@my_searches_router.callback_query(F.data.startswith("remove_"))
async def handle_remove_button(callback: CallbackQuery, message_bus: MessageBus):
    result = await validate_callback(callback, prefix="remove")
    if not result:
        return
    data, msg = result

    chat_id = msg.chat.id
    try:
        search_id = int(data.split("_")[1])
    except (IndexError, ValueError) as e:
        logger.error(
            f"Invalid callback data format: {callback.data} for user {chat_id}, error: {e}"
        )
        return

    result = await _resolve_search_from_callback(
        callback, message_bus, search_id, chat_id
    )
    if not result:
        return
    search, msg = result

    try:
        await msg.edit_text(
            f"Are you sure you want to delete:\n\n"
            f"📌 {search.query}\n"
            f"💰 ${search.price_min} - ${search.price_max}\n\n"
            "This cannot be undone.",
            reply_markup=get_confirmation_keyboard(search_id),
        )
        await callback.answer()
    except Exception as e:
        logger.error(
            f"Failed to send confirmation for search {search_id} to user {chat_id}: {e}",
            exc_info=True,
        )


@my_searches_router.callback_query(F.data.startswith("confirm_remove_"))
async def confirm_delete(callback: CallbackQuery, message_bus: MessageBus):
    result = await validate_callback(callback, prefix="confirm_remove")
    if not result:
        return
    data, msg = result

    chat_id = msg.chat.id
    try:
        search_id = int(data.split("_")[2])
    except (IndexError, ValueError) as e:
        logger.error(
            f"Invalid callback data format: {callback.data} for user {chat_id}, error: {e}"
        )
        return

    try:
        await message_bus.publish(RemoveSearchEvent(search_id=search_id))
        await message_bus.execute(DeleteSearchCommand(search_id=search_id))
    except Exception as e:
        logger.error(
            f"Failed to delete search {search_id} for user {chat_id}: {e}",
            exc_info=True,
        )
        return

    try:
        await msg.delete()
        await callback.answer("Search deleted successfully!")
    except Exception as e:
        logger.error(
            f"Failed to delete message or answer callback for search {search_id} for user {chat_id}: {e}",
            exc_info=True,
        )


@my_searches_router.callback_query(F.data.startswith("cancel_remove_"))
async def cancel_delete(callback: CallbackQuery, message_bus: MessageBus):
    result = await validate_callback(callback, prefix="cancel_remove")
    if not result:
        return
    data, msg = result

    chat_id = msg.chat.id
    try:
        search_id = int(data.split("_")[2])
    except (IndexError, ValueError) as e:
        logger.error(
            f"Invalid callback data format: {callback.data} for user {chat_id}, error: {e}"
        )
        return

    result = await _resolve_search_from_callback(
        callback, message_bus, search_id, chat_id
    )
    if not result:
        return
    search, msg = result

    try:
        message_text, reply_markup = build_my_search_listing_message(search)
        await msg.edit_text(
            message_text,
            reply_markup=reply_markup,
        )
        await callback.answer()
    except Exception as e:
        logger.error(
            f"Failed to restore message for search {search_id} for user {chat_id}: {e}",
            exc_info=True,
        )


# Handle "Edit" button press


@my_searches_router.callback_query(F.data.startswith("edit_"))
async def handle_edit_button(
    callback: CallbackQuery, state: FSMContext, message_bus: MessageBus
):
    result = await validate_callback(callback, prefix="edit")
    if not result:
        return
    data, msg = result

    chat_id = msg.chat.id
    try:
        search_id = int(data.split("_")[1])
    except (IndexError, ValueError) as e:
        logger.error(
            f"Invalid callback data format: {callback.data} for user {chat_id}, error: {e}"
        )
        return

    result = await _resolve_search_from_callback(
        callback, message_bus, search_id, chat_id
    )
    if not result:
        return
    search, msg = result

    try:
        await state.clear()  # Clear any previous FSM state
        await state.set_state(EditSearchState.selecting_field)

        await msg.edit_text(
            f"What do you want to edit?:\n\n"
            f"📌 {search.query}\n"
            f"💰 ${search.price_min} - ${search.price_max}\n\n",
            reply_markup=get_edit_keyboard(search_id),
        )
        await callback.answer()
    except Exception as e:
        logger.error(
            f"Failed to show edit options for search {search_id} to user {chat_id}: {e}",
            exc_info=True,
        )
        await state.clear()


@my_searches_router.callback_query(F.data.startswith("cancel_edit_"))
async def cancel_edit(
    callback: CallbackQuery, state: FSMContext, message_bus: MessageBus
):
    result = await validate_callback(callback, prefix="cancel_edit")
    if not result:
        return
    data, msg = result

    chat_id = msg.chat.id
    try:
        search_id = int(data.split("_")[2])
    except (IndexError, ValueError) as e:
        logger.error(
            f"Invalid callback data format: {callback.data} for user {chat_id}, error: {e}"
        )
        return

    result = await _resolve_search_from_callback(
        callback, message_bus, search_id, chat_id
    )
    if not result:
        return
    search, msg = result

    try:
        await state.clear()

        message_text, reply_markup = build_my_search_listing_message(search)
        await msg.edit_text(
            message_text,
            reply_markup=reply_markup,
        )
        await callback.answer()
    except Exception as e:
        logger.error(
            f"Failed to cancel edit for search {search_id} for user {chat_id}: {e}",
            exc_info=True,
        )
        await state.clear()


@my_searches_router.callback_query(
    F.data.startswith("editfield_"), EditSearchState.selecting_field
)
async def handle_edit_field(
    callback: CallbackQuery, state: FSMContext, message_bus: MessageBus
):
    result = await validate_callback(callback, prefix="editfield")
    if not result:
        return
    data, msg = result

    chat_id = msg.chat.id
    try:
        parts = data.split("_")
        search_id = int(parts[1])
        field = parts[2]  # 'query', 'min', or 'max'
    except (IndexError, ValueError) as e:
        logger.error(
            f"Invalid callback data format: {callback.data} for user {chat_id}, error: {e}"
        )
        return

    result = await _resolve_search_from_callback(
        callback, message_bus, search_id, chat_id
    )
    if not result:
        return
    search, msg = result

    prompt_map = {
        "query": "Please enter the new search query:",
        "min": "Please enter the new minimum price:",
        "max": "Please enter the new maximum price:",
    }

    prompt = prompt_map.get(field)
    if not prompt:
        logger.error(f"Invalid field '{field}' for editing for user {chat_id}.")
        return

    try:
        answer_text = f"{prompt}\n\n"
        match field:
            case "query":
                await state.set_state(EditSearchState.editing_query)
                answer_text += f"(Current: {search.query})"
            case "min":
                await state.set_state(EditSearchState.editing_price_min)
                answer_text += f"(Current: {search.price_min})"
            case "max":
                await state.set_state(EditSearchState.editing_price_max)
                answer_text += f"(Current: {search.price_max})"
            case _:
                logger.error(
                    f"Unhandled field '{field}' for editing for user {chat_id}."
                )
                return

        await state.update_data(
            search_id=search_id,
            message_id=msg.message_id,
            chat_id=msg.chat.id,
        )

        message_text, reply_markup = build_my_search_listing_message(search)
        await msg.edit_text(
            message_text,
            reply_markup=reply_markup,
        )
        await msg.answer(answer_text, reply_markup=get_cancel_edit_reply_keyboard())
    except Exception as e:
        logger.error(
            f"Failed to show edit prompt for field '{field}' of search {search_id} to user {chat_id}: {e}",
            exc_info=True,
        )
        await state.clear()


# Do not move this below the edit handlers as they will handle text input first
@my_searches_router.message(F.text == "❌ Cancel editing")
async def cancel_editfield(message: Message, state: FSMContext):
    try:
        await state.clear()
        await message.answer("Editing cancelled", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.error(
            f"Failed to handle cancel editfield for user {message.chat.id}: {e}",
            exc_info=True,
        )


@my_searches_router.message(EditSearchState.editing_query)
async def edit_query(message: Message, state: FSMContext, message_bus: MessageBus):
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

        new_query = message.text.strip()
        data = await state.get_data()
        search_id = data.get("search_id")

        if search_id is None:
            logger.error(
                f"Search ID not found in FSM context for user {message.chat.id}."
            )
            await state.clear()
            return

        try:
            await message_bus.execute(
                UpdateSearchCommand(search_id=search_id, query=new_query)
            )
            await message_bus.publish(UpdateSearchEvent(search_id=search_id))
        except Exception as e:
            logger.error(
                f"Failed to update search query for search {search_id} for user {message.chat.id}: {e}",
                exc_info=True,
            )
            return

        await state.clear()
        await message.answer(
            "Search query updated successfully.", reply_markup=ReplyKeyboardRemove()
        )

        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        if chat_id and message_id and message.bot:
            await _update_message_after_update(
                bot=message.bot,
                message_bus=message_bus,
                message_id=message_id,
                chat_id=chat_id,
                search_id=search_id,
            )
    except Exception as e:
        logger.error(
            f"Failed to handle edit query for user {message.chat.id}: {e}",
            exc_info=True,
        )
        await state.clear()


@my_searches_router.message(EditSearchState.editing_price_min)
async def edit_price_min(message: Message, state: FSMContext, message_bus: MessageBus):
    try:
        if not message.text:
            await message.answer("Please enter a valid minimum price like '50'.")
            return

        result = validate_price(message.text, "minimum price")
        if not result.is_valid:
            await message.answer(result.error_message or "Invalid minimum price.")
            return

        data = await state.get_data()
        search_id = data.get("search_id")

        if search_id is None:
            logger.error(
                f"Search ID not found in FSM context for user {message.chat.id}."
            )
            await state.clear()
            return

        try:
            search = await message_bus.query(GetSearchByIdQuery(search_id=search_id))
        except Exception as e:
            logger.error(
                f"Failed to get search {search_id} for user {message.chat.id}: {e}",
                exc_info=True,
            )
            return

        if not search:
            logger.error(
                f"Search with ID {search_id} not found for editing for user {message.chat.id}."
            )
            return

        range_result = validate_edit_price_min(
            float(message.text.strip()), search.price_max
        )
        if not range_result.is_valid:
            await message.answer(range_result.error_message or "Invalid price range.")
            return

        try:
            await message_bus.execute(
                UpdateSearchCommand(
                    search_id=search_id, price_min=float(message.text.strip())
                )
            )
            await message_bus.publish(UpdateSearchEvent(search_id=search_id))
        except Exception as e:
            logger.error(
                f"Failed to update minimum price for search {search_id} for user {message.chat.id}: {e}",
                exc_info=True,
            )
            return

        await state.clear()
        await message.answer(
            "Minimum price updated successfully.",
            reply_markup=ReplyKeyboardRemove(),
        )

        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        if chat_id and message_id and message.bot:
            await _update_message_after_update(
                bot=message.bot,
                message_bus=message_bus,
                message_id=message_id,
                chat_id=chat_id,
                search_id=search_id,
            )
    except Exception as e:
        logger.error(
            f"Failed to handle edit price min for user {message.chat.id}: {e}",
            exc_info=True,
        )
        await state.clear()


@my_searches_router.message(EditSearchState.editing_price_max)
async def edit_price_max(message: Message, state: FSMContext, message_bus: MessageBus):
    try:
        if not message.text:
            await message.answer("Please enter a valid maximum price like '200'.")
            return

        result = validate_price(message.text, "maximum price")
        if not result.is_valid:
            await message.answer(result.error_message or "Invalid maximum price.")
            return

        data = await state.get_data()
        search_id = data.get("search_id")

        if search_id is None:
            logger.error(
                f"Search ID not found in FSM context for user {message.chat.id}."
            )
            await state.clear()
            return

        try:
            search = await message_bus.query(GetSearchByIdQuery(search_id=search_id))
        except Exception as e:
            logger.error(
                f"Failed to get search {search_id} for user {message.chat.id}: {e}",
                exc_info=True,
            )
            return

        if not search:
            logger.error(
                f"Search with ID {search_id} not found for editing for user {message.chat.id}."
            )
            return

        range_result = validate_edit_price_max(
            float(message.text.strip()), search.price_min
        )
        if not range_result.is_valid:
            await message.answer(range_result.error_message or "Invalid price range.")
            return

        try:
            await message_bus.execute(
                UpdateSearchCommand(
                    search_id=search_id, price_max=float(message.text.strip())
                )
            )
            await message_bus.publish(UpdateSearchEvent(search_id=search_id))
        except Exception as e:
            logger.error(
                f"Failed to update maximum price for search {search_id} for user {message.chat.id}: {e}",
                exc_info=True,
            )
            return

        await state.clear()
        await message.answer(
            "Maximum price updated successfully.",
            reply_markup=ReplyKeyboardRemove(),
        )

        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        if chat_id and message_id and message.bot:
            await _update_message_after_update(
                bot=message.bot,
                message_bus=message_bus,
                message_id=message_id,
                chat_id=chat_id,
                search_id=search_id,
            )
    except Exception as e:
        logger.error(
            f"Failed to handle edit price max for user {message.chat.id}: {e}",
            exc_info=True,
        )
        await state.clear()


async def _update_message_after_update(
    bot: Bot,
    message_bus: MessageBus,
    message_id: int,
    chat_id: int,
    search_id: int,
) -> None:
    """Helper to update the original search message after an edit. Logs errors but doesn't raise."""
    try:
        search = await message_bus.query(GetSearchByIdQuery(search_id=search_id))
    except Exception as e:
        logger.error(f"Failed to get search {search_id}: {e}", exc_info=True)
        return

    if not search:
        logger.error(f"Search with ID {search_id} not found.")
        return

    try:
        message_text, reply_markup = build_my_search_listing_message(search)
    except Exception as e:
        logger.error(
            f"Failed to build message for search {search_id}: {e}", exc_info=True
        )
        return

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to update message {message_id}: {e}", exc_info=True)


async def _resolve_search_from_callback(
    callback: CallbackQuery,
    message_bus: MessageBus,
    search_id: int,
    chat_id: int | str,
) -> Optional[tuple[Search, Message]]:
    """Fetch search by ID, validate callback.message is a Message instance.

    Returns ``(search, message)`` on success, or ``None`` after answering the
    callback with an appropriate error message.
    """
    try:
        search = await message_bus.query(GetSearchByIdQuery(search_id=search_id))
    except Exception as e:
        logger.error(
            f"Failed to get search {search_id} for user {chat_id}: {e}", exc_info=True
        )
        return None

    if not search:
        logger.error(f"Search with ID {search_id} not found for user {chat_id}.")
        return None

    if not isinstance(callback.message, Message):
        logger.error(f"Callback message is not a Message instance for user {chat_id}.")
        return None

    return search, callback.message


async def validate_callback(
    callback: CallbackQuery, prefix: str
) -> Optional[tuple[str, Message]]:
    """Validate callback data and message presence.

    Returns ``(callback.data, callback.message)`` if valid, ``None`` after
    answering the callback with an appropriate error message.
    """
    if (
        not callback.data
        or not callback.message
        or not isinstance(callback.message, Message)
        or not callback.data.startswith(f"{prefix}_")
    ):
        logger.error("Callback data or message is missing.")
        return None

    return callback.data, callback.message
