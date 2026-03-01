"""Tests for telegram_bot.routers.new_search — FSM create flow."""

import pytest
from unittest.mock import MagicMock
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ReplyKeyboardRemove

from src.telegram_bot.routers.new_search import (
    cmd_new_search,
    cancel_create,
    add_query,
    add_price_min,
    add_price_max,
)
from src.telegram_bot.states.add_search_state import AddSearchState
from src.telegram_bot.models.search import Search
from src.telegram_bot.utility.keyboard_builder import get_cancel_create_reply_keyboard
from src.message_bus.commands.add_new_search_command import AddNewSearchCommand
from src.message_bus.events.new_search_event import NewSearchEvent


@pytest.fixture
def fsm_with_data(mock_fsm_context):
    mock_fsm_context.get_data.return_value = {
        "query": "nike shoes",
        "price_min": 10.0,
    }
    return mock_fsm_context


@pytest.fixture
def successful_execute(fsm_with_data, mock_message_bus):
    """Pre-configured success path: fsm_with_data + execute returns a Search."""
    added_search = Search(
        id=1, chat_id=12345, query="nike shoes", price_min=10.0, price_max=100.0
    )
    mock_message_bus.execute.return_value = added_search
    return added_search


class TestCmdNewSearch:
    async def test_clears_state(self, mock_message, mock_fsm_context):
        await cmd_new_search(mock_message, mock_fsm_context)

        mock_fsm_context.clear.assert_called_once()

    async def test_sets_waiting_for_search_term(self, mock_message, mock_fsm_context):
        await cmd_new_search(mock_message, mock_fsm_context)

        mock_fsm_context.set_state.assert_called_once_with(
            AddSearchState.waiting_for_search_term
        )

    async def test_sends_prompt_with_cancel_keyboard(
        self, mock_message, mock_fsm_context
    ):
        await cmd_new_search(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Enter the search term you want to monitor (e.g., 'vintage jacket'):",
            reply_markup=get_cancel_create_reply_keyboard(),
        )


class TestCancelCreate:
    async def test_clears_state(self, mock_message, mock_fsm_context):
        await cancel_create(mock_message, mock_fsm_context)

        mock_fsm_context.clear.assert_called_once()

    async def test_sends_cancellation_and_removes_keyboard(
        self, mock_message, mock_fsm_context
    ):
        await cancel_create(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Creation cancelled", reply_markup=ReplyKeyboardRemove()
        )


class TestAddQuery:
    async def test_no_text_sends_prompt(self, mock_message, mock_fsm_context):
        mock_message.text = None

        await add_query(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Please enter a valid search term like 'vintage jacket'."
        )
        mock_fsm_context.set_state.assert_not_called()

    async def test_invalid_query_sends_error(self, mock_message, mock_fsm_context):
        mock_message.text = "a"  # too short (min 2 chars)

        await add_query(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Search term must be at least 2 characters long."
        )
        mock_fsm_context.set_state.assert_not_called()

    async def test_min_length_boundary(self, mock_message, mock_fsm_context):
        mock_message.text = "ab"  # exactly 2 chars – minimum valid

        await add_query(mock_message, mock_fsm_context)

        mock_fsm_context.update_data.assert_called_once_with(query="ab")
        mock_fsm_context.set_state.assert_called_once_with(
            AddSearchState.waiting_for_price_min
        )
        mock_message.answer.assert_called_once_with(
            "Enter the minimum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )

    async def test_exceeds_max_length(self, mock_message, mock_fsm_context):
        mock_message.text = "x" * 101  # exceeds 100-char max

        await add_query(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Search term must be at most 100 characters."
        )
        mock_fsm_context.set_state.assert_not_called()

    async def test_whitespace_only_sends_error(self, mock_message, mock_fsm_context):
        mock_message.text = "   "

        await add_query(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Please enter a valid search term like 'vintage jacket'."
        )
        mock_fsm_context.set_state.assert_not_called()

    async def test_valid_query(self, mock_message, mock_fsm_context):
        mock_message.text = "nike shoes"

        await add_query(mock_message, mock_fsm_context)

        mock_fsm_context.update_data.assert_called_once_with(query="nike shoes")
        mock_fsm_context.set_state.assert_called_once_with(
            AddSearchState.waiting_for_price_min
        )
        mock_message.answer.assert_called_once_with(
            "Enter the minimum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )

    async def test_strips_whitespace(self, mock_message, mock_fsm_context):
        mock_message.text = "  nike shoes  "

        await add_query(mock_message, mock_fsm_context)

        mock_fsm_context.update_data.assert_called_once_with(query="nike shoes")
        mock_message.answer.assert_called_once_with(
            "Enter the minimum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )

    async def test_error_clears_state(self, mock_message, mock_fsm_context):
        mock_message.text = "nike shoes"
        mock_message.answer.side_effect = TelegramAPIError(
            method=MagicMock(), message="error"
        )

        await add_query(mock_message, mock_fsm_context)

        mock_fsm_context.clear.assert_called()


class TestAddPriceMin:
    async def test_no_text_sends_prompt(self, mock_message, mock_fsm_context):
        mock_message.text = None

        await add_price_min(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Please enter a valid minimum price like '50'."
        )
        mock_fsm_context.set_state.assert_not_called()

    async def test_non_numeric_sends_error(self, mock_message, mock_fsm_context):
        mock_message.text = "abc"

        await add_price_min(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Please enter a valid minimum price like '50'."
        )
        mock_fsm_context.set_state.assert_not_called()

    async def test_negative_sends_error(self, mock_message, mock_fsm_context):
        mock_message.text = "-5"

        await add_price_min(mock_message, mock_fsm_context)

        mock_message.answer.assert_called_once_with(
            "Minimum price cannot be negative. Please enter a valid minimum price like '50'."
        )
        mock_fsm_context.set_state.assert_not_called()

    async def test_zero_valid(self, mock_message, mock_fsm_context):
        mock_message.text = "0"

        await add_price_min(mock_message, mock_fsm_context)

        mock_fsm_context.update_data.assert_called_once_with(price_min=0.0)
        mock_fsm_context.set_state.assert_called_once_with(
            AddSearchState.waiting_for_price_max
        )
        mock_message.answer.assert_called_once_with(
            "Enter the maximum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )

    async def test_decimal_valid(self, mock_message, mock_fsm_context):
        mock_message.text = "49.99"

        await add_price_min(mock_message, mock_fsm_context)

        mock_fsm_context.update_data.assert_called_once_with(price_min=49.99)
        mock_fsm_context.set_state.assert_called_once_with(
            AddSearchState.waiting_for_price_max
        )
        mock_message.answer.assert_called_once_with(
            "Enter the maximum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )

    async def test_valid(self, mock_message, mock_fsm_context):
        mock_message.text = "50"

        await add_price_min(mock_message, mock_fsm_context)

        mock_fsm_context.update_data.assert_called_once_with(price_min=50.0)
        mock_fsm_context.set_state.assert_called_once_with(
            AddSearchState.waiting_for_price_max
        )
        mock_message.answer.assert_called_once_with(
            "Enter the maximum price",
            reply_markup=get_cancel_create_reply_keyboard(),
        )

    async def test_error_clears_state(self, mock_message, mock_fsm_context):
        mock_message.text = "50"
        mock_message.answer.side_effect = TelegramAPIError(
            method=MagicMock(), message="error"
        )

        await add_price_min(mock_message, mock_fsm_context)

        mock_fsm_context.clear.assert_called()


class TestAddPriceMax:
    async def test_no_text_sends_prompt(
        self, mock_message, fsm_with_data, mock_message_bus
    ):
        mock_message.text = None

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "Please enter a valid maximum price like '200'."
        )

    async def test_non_numeric_sends_error(
        self, mock_message, fsm_with_data, mock_message_bus
    ):
        mock_message.text = "abc"

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "Please enter a valid maximum price like '50'."
        )

    async def test_negative_sends_error(
        self, mock_message, fsm_with_data, mock_message_bus
    ):
        mock_message.text = "-10"

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "Maximum price cannot be negative. Please enter a valid maximum price like '50'."
        )
        mock_message_bus.execute.assert_not_called()

    async def test_invalid_range(self, mock_message, fsm_with_data, mock_message_bus):
        mock_message.text = "5"  # less than min of 10

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "Maximum price must be greater than minimum price. "
            "Please enter a valid maximum price like '200'."
        )
        mock_message_bus.execute.assert_not_called()

    async def test_equal_to_min_rejected(
        self, mock_message, fsm_with_data, mock_message_bus
    ):
        mock_message.text = "10"  # equal to min of 10

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "Maximum price must be greater than minimum price. "
            "Please enter a valid maximum price like '200'."
        )
        mock_message_bus.execute.assert_not_called()

    async def test_missing_query_in_state(
        self, mock_message, mock_fsm_context, mock_message_bus
    ):
        mock_message.text = "100"
        mock_fsm_context.get_data.return_value = {"price_min": 10.0}

        await add_price_max(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()
        mock_message_bus.execute.assert_not_called()

    async def test_missing_price_min_in_state(
        self, mock_message, mock_fsm_context, mock_message_bus
    ):
        mock_message.text = "100"
        mock_fsm_context.get_data.return_value = {"query": "nike shoes"}

        await add_price_max(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()
        mock_message_bus.execute.assert_not_called()

    async def test_empty_state_data(
        self, mock_message, mock_fsm_context, mock_message_bus
    ):
        mock_message.text = "100"
        mock_fsm_context.get_data.return_value = {}

        await add_price_max(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()
        mock_message_bus.execute.assert_not_called()

    async def test_executes_command(
        self, mock_message, fsm_with_data, mock_message_bus, successful_execute
    ):
        mock_message.text = "100"

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message_bus.execute.assert_called_once()
        cmd = mock_message_bus.execute.call_args[0][0]
        assert isinstance(cmd, AddNewSearchCommand)
        assert cmd.query == "nike shoes"
        assert cmd.price_min == 10.0
        assert cmd.price_max == 100.0

    async def test_sends_success_message(
        self, mock_message, fsm_with_data, mock_message_bus, successful_execute
    ):
        mock_message.text = "100"

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        assert mock_message.answer.call_count == 2
        first_call_text = mock_message.answer.call_args_list[0][0][0]
        assert "success" in first_call_text.lower()
        second_call_kwargs = mock_message.answer.call_args_list[1][1]
        assert isinstance(second_call_kwargs["reply_markup"], ReplyKeyboardRemove)

    async def test_publishes_event(
        self, mock_message, fsm_with_data, mock_message_bus, successful_execute
    ):
        mock_message.text = "100"

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message_bus.publish.assert_called_once()
        event = mock_message_bus.publish.call_args[0][0]
        assert isinstance(event, NewSearchEvent)
        assert event.search == successful_execute

    async def test_clears_state_on_success(
        self, mock_message, fsm_with_data, mock_message_bus, successful_execute
    ):
        mock_message.text = "100"

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        fsm_with_data.clear.assert_called()

    async def test_command_error_returns_early(
        self, mock_message, fsm_with_data, mock_message_bus
    ):
        mock_message.text = "100"
        mock_message_bus.execute.side_effect = Exception("db error")

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        mock_message.answer.assert_not_called()

    async def test_build_message_fallback(
        self, mock_message, fsm_with_data, mock_message_bus, successful_execute, mocker
    ):
        mock_message.text = "100"
        mocker.patch(
            "src.telegram_bot.routers.new_search.build_my_search_listing_message",
            side_effect=Exception("build error"),
        )

        await add_price_max(mock_message, fsm_with_data, mock_message_bus)

        # "Search created successfully!" + fallback message
        assert mock_message.answer.call_count == 2

    async def test_outer_exception_clears_state(
        self, mock_message, mock_fsm_context, mock_message_bus
    ):
        mock_message.text = "100"
        mock_fsm_context.get_data.side_effect = RuntimeError("unexpected")

        await add_price_max(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()
