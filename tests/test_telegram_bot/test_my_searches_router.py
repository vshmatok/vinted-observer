"""Tests for telegram_bot.routers.my_searches — list/delete/edit workflows."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.exceptions import TelegramAPIError

from src.telegram_bot.routers.my_searches import (
    cmd_my_searches,
    handle_remove_button,
    confirm_delete,
    cancel_delete,
    handle_edit_button,
    cancel_edit,
    handle_edit_field,
    cancel_editfield,
    edit_query,
    edit_price_min,
    edit_price_max,
    _resolve_search_from_callback,
    _update_message_after_update,
    validate_callback,
)
from src.telegram_bot.models.search import Search
from src.telegram_bot.states.edit_search_state import EditSearchState
from src.telegram_bot.utility.message_builder import build_my_search_listing_message
from src.telegram_bot.utility.keyboard_builder import (
    get_confirmation_keyboard,
    get_edit_keyboard,
    get_cancel_edit_reply_keyboard,
)
from src.message_bus.events.remove_search_event import RemoveSearchEvent
from src.message_bus.events.update_search_event import UpdateSearchEvent
from src.message_bus.commands.delete_search_command import DeleteSearchCommand
from src.message_bus.commands.update_search_command import UpdateSearchCommand
from src.message_bus.queries.get_search_by_id_query import GetSearchByIdQuery


_price_params = pytest.mark.parametrize(
    "handler, valid_text, invalid_range_text, expected_value, cmd_field",
    [
        pytest.param(edit_price_min, "20", "200", 20.0, "price_min", id="min"),
        pytest.param(edit_price_max, "200", "5", 200.0, "price_max", id="max"),
    ],
)


class TestCmdMySearches:
    async def test_query_error(self, mock_message, mock_message_bus):
        mock_message_bus.query.side_effect = Exception("db error")

        await cmd_my_searches(mock_message, mock_message_bus)

        mock_message.answer.assert_not_called()

    async def test_empty_list(self, mock_message, mock_message_bus):
        mock_message_bus.query.return_value = []

        await cmd_my_searches(mock_message, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "📭 You have no active searches yet.\n\nUse /add_search to create one!"
        )

    async def test_empty_list_send_error(self, mock_message, mock_message_bus):
        mock_message_bus.query.return_value = []
        mock_message.answer.side_effect = TelegramAPIError(
            method=MagicMock(), message="send error"
        )

        await cmd_my_searches(mock_message, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "📭 You have no active searches yet.\n\nUse /add_search to create one!"
        )

    async def test_single_search(
        self, mock_message, mock_message_bus, sample_nike_search
    ):
        mock_message_bus.query.return_value = [sample_nike_search]

        await cmd_my_searches(mock_message, mock_message_bus)

        expected_text, expected_markup = build_my_search_listing_message(
            sample_nike_search
        )
        mock_message.answer.assert_called_once_with(
            expected_text, reply_markup=expected_markup
        )

    async def test_sends_listing_per_search(
        self, mock_message, mock_message_bus, sample_nike_search
    ):
        search2 = Search(
            id=2, chat_id=12345, query="adidas", price_min=5.0, price_max=50.0
        )
        mock_message_bus.query.return_value = [sample_nike_search, search2]

        await cmd_my_searches(mock_message, mock_message_bus)

        assert mock_message.answer.call_count == 2

    async def test_error_on_one_continues(
        self, mock_message, mock_message_bus, sample_nike_search
    ):
        search2 = Search(
            id=2, chat_id=12345, query="adidas", price_min=5.0, price_max=50.0
        )
        mock_message_bus.query.return_value = [sample_nike_search, search2]
        mock_message.answer.side_effect = [
            TelegramAPIError(method=MagicMock(), message="error"),
            AsyncMock(),
        ]

        await cmd_my_searches(mock_message, mock_message_bus)

        assert mock_message.answer.call_count == 2

    async def test_build_error_continues(self, mock_message, mock_message_bus, mocker):
        search1 = Search(
            id=1, chat_id=12345, query="nike", price_min=10.0, price_max=100.0
        )
        search2 = Search(
            id=2, chat_id=12345, query="adidas", price_min=5.0, price_max=50.0
        )
        mock_message_bus.query.return_value = [search1, search2]
        mocker.patch(
            "src.telegram_bot.routers.my_searches.build_my_search_listing_message",
            side_effect=[Exception("build error"), ("text", MagicMock())],
        )

        await cmd_my_searches(mock_message, mock_message_bus)

        mock_message.answer.assert_called_once()


class TestHandleRemoveButton:
    async def test_missing_data(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = None

        await handle_remove_button(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()

    async def test_missing_message(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "remove_1"
        mock_callback_query.message = None

        await handle_remove_button(mock_callback_query, mock_message_bus)

        mock_message_bus.query.assert_not_called()

    async def test_invalid_format(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "remove_abc"

        await handle_remove_button(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_message_bus.execute.assert_not_called()

    async def test_query_error(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.side_effect = Exception("db error")

        await handle_remove_button(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()

    async def test_not_found(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.return_value = None

        await handle_remove_button(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()

    async def test_not_message_instance(
        self, mock_callback_query, mock_message_bus, sample_nike_search
    ):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.return_value = sample_nike_search
        mock_callback_query.message = MagicMock()  # Not a Message instance
        mock_callback_query.message.chat.id = 12345

        await handle_remove_button(mock_callback_query, mock_message_bus)

        mock_message_bus.execute.assert_not_called()

    async def test_shows_confirmation(
        self, mock_callback_query, mock_message_bus, sample_nike_search
    ):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_remove_button(mock_callback_query, mock_message_bus)

        mock_callback_query.message.edit_text.assert_called_once()
        text = mock_callback_query.message.edit_text.call_args[0][0]
        assert "delete" in text.lower()
        kwargs = mock_callback_query.message.edit_text.call_args[1]
        assert kwargs["reply_markup"] == get_confirmation_keyboard(1)


class TestConfirmDelete:
    async def test_missing_data(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = None

        await confirm_delete(mock_callback_query, mock_message_bus)

        mock_message_bus.publish.assert_not_called()
        mock_message_bus.execute.assert_not_called()

    async def test_invalid_format(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "confirm_remove_abc"

        await confirm_delete(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_message_bus.execute.assert_not_called()

    async def test_success(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "confirm_remove_1"

        await confirm_delete(mock_callback_query, mock_message_bus)

        mock_message_bus.publish.assert_called_once()
        event = mock_message_bus.publish.call_args[0][0]
        assert isinstance(event, RemoveSearchEvent)
        assert event.search_id == 1
        mock_message_bus.execute.assert_called_once()
        cmd = mock_message_bus.execute.call_args[0][0]
        assert isinstance(cmd, DeleteSearchCommand)
        assert cmd.search_id == 1
        mock_callback_query.message.delete.assert_called_once()
        mock_callback_query.answer.assert_called_once_with(
            "Search deleted successfully!"
        )

    async def test_delete_error(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "confirm_remove_1"
        mock_message_bus.publish.side_effect = Exception("bus error")

        await confirm_delete(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()

    async def test_not_message_instance(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "confirm_remove_1"
        mock_callback_query.message = MagicMock()  # Not a Message instance
        mock_callback_query.message.chat.id = 12345

        await confirm_delete(mock_callback_query, mock_message_bus)

        mock_message_bus.publish.assert_not_called()
        mock_message_bus.execute.assert_not_called()


class TestCancelDelete:
    async def test_missing_data(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = None

        await cancel_delete(mock_callback_query, mock_message_bus)

        mock_message_bus.query.assert_not_called()

    async def test_invalid_format(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "cancel_remove_abc"

        await cancel_delete(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_callback_query.message.edit_text.assert_not_called()

    async def test_query_error(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "cancel_remove_1"
        mock_message_bus.query.side_effect = Exception("db error")

        await cancel_delete(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_callback_query.message.edit_text.assert_not_called()

    async def test_not_found(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "cancel_remove_1"
        mock_message_bus.query.return_value = None

        await cancel_delete(mock_callback_query, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_callback_query.message.edit_text.assert_not_called()

    async def test_restores_message_and_answers(
        self, mock_callback_query, mock_message_bus, sample_nike_search
    ):
        mock_callback_query.data = "cancel_remove_1"
        mock_message_bus.query.return_value = sample_nike_search

        await cancel_delete(mock_callback_query, mock_message_bus)

        expected_text, expected_markup = build_my_search_listing_message(
            sample_nike_search
        )
        mock_callback_query.message.edit_text.assert_called_once_with(
            expected_text, reply_markup=expected_markup
        )
        mock_callback_query.answer.assert_called_once()


class TestHandleEditButton:
    async def test_missing_data(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = None

        await handle_edit_button(
            mock_callback_query, mock_fsm_context, mock_message_bus
        )

        mock_fsm_context.set_state.assert_not_called()
        mock_message_bus.query.assert_not_called()

    async def test_invalid_format(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "edit_abc"

        await handle_edit_button(
            mock_callback_query, mock_fsm_context, mock_message_bus
        )

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.set_state.assert_not_called()

    async def test_query_error(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "edit_1"
        mock_message_bus.query.side_effect = Exception("db error")

        await handle_edit_button(
            mock_callback_query, mock_fsm_context, mock_message_bus
        )

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.set_state.assert_not_called()

    async def test_not_found(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "edit_1"
        mock_message_bus.query.return_value = None

        await handle_edit_button(
            mock_callback_query, mock_fsm_context, mock_message_bus
        )

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.set_state.assert_not_called()

    async def test_success(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "edit_1"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_button(
            mock_callback_query, mock_fsm_context, mock_message_bus
        )

        mock_fsm_context.clear.assert_called_once()
        mock_fsm_context.set_state.assert_called_once_with(
            EditSearchState.selecting_field
        )
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert "nike shoes" in call_args[0][0]
        assert call_args[1]["reply_markup"] == get_edit_keyboard(1)

    async def test_error_clears_state(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "edit_1"
        mock_message_bus.query.return_value = sample_nike_search
        mock_callback_query.message.edit_text.side_effect = TelegramAPIError(
            method=MagicMock(), message="error"
        )

        await handle_edit_button(
            mock_callback_query, mock_fsm_context, mock_message_bus
        )

        # clear called during setup AND during error handling
        assert mock_fsm_context.clear.call_count == 2


class TestCancelEdit:
    async def test_missing_data(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = None

        await cancel_edit(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_not_called()
        mock_message_bus.query.assert_not_called()

    async def test_invalid_format(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "cancel_edit_abc"

        await cancel_edit(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.clear.assert_not_called()

    async def test_query_error(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "cancel_edit_1"
        mock_message_bus.query.side_effect = Exception("db error")

        await cancel_edit(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_callback_query.message.edit_text.assert_not_called()

    async def test_not_found(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "cancel_edit_1"
        mock_message_bus.query.return_value = None

        await cancel_edit(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_callback_query.message.edit_text.assert_not_called()

    async def test_clears_state_and_restores_listing(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "cancel_edit_1"
        mock_message_bus.query.return_value = sample_nike_search

        await cancel_edit(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called_once()
        expected_text, expected_markup = build_my_search_listing_message(
            sample_nike_search
        )
        mock_callback_query.message.edit_text.assert_called_once_with(
            expected_text, reply_markup=expected_markup
        )

    async def test_error_clears_state(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "cancel_edit_1"
        mock_message_bus.query.return_value = sample_nike_search
        mock_callback_query.message.edit_text.side_effect = TelegramAPIError(
            method=MagicMock(), message="error"
        )

        await cancel_edit(mock_callback_query, mock_fsm_context, mock_message_bus)

        # clear called inside try AND inside except
        assert mock_fsm_context.clear.call_count == 2


class TestHandleEditField:
    async def test_missing_data(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = None

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.set_state.assert_not_called()
        mock_message_bus.query.assert_not_called()

    async def test_invalid_format(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "editfield_abc"

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.set_state.assert_not_called()

    async def test_missing_field(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        """Tests IndexError path when field part is absent from callback data."""
        mock_callback_query.data = "editfield_1"

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.set_state.assert_not_called()

    async def test_query_error(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "editfield_1_query"
        mock_message_bus.query.side_effect = Exception("db error")

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.set_state.assert_not_called()

    async def test_not_found(
        self, mock_callback_query, mock_fsm_context, mock_message_bus
    ):
        mock_callback_query.data = "editfield_1_query"
        mock_message_bus.query.return_value = None

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()
        mock_fsm_context.set_state.assert_not_called()

    async def test_invalid_field(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_invalid"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.answer.assert_not_called()

    async def test_sets_state_for_query(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_query"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.set_state.assert_called_once_with(
            EditSearchState.editing_query
        )

    async def test_sets_state_for_min(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_min"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.set_state.assert_called_once_with(
            EditSearchState.editing_price_min
        )

    async def test_sets_state_for_max(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_max"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.set_state.assert_called_once_with(
            EditSearchState.editing_price_max
        )

    async def test_stores_data_in_state(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_query"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.update_data.assert_called_once()
        kwargs = mock_fsm_context.update_data.call_args[1]
        assert kwargs["search_id"] == 1

    async def test_sends_prompt_with_current_query(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_query"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.message.answer.assert_called_once()
        text = mock_callback_query.message.answer.call_args[0][0]
        assert "nike shoes" in text
        kwargs = mock_callback_query.message.answer.call_args[1]
        assert kwargs["reply_markup"] == get_cancel_edit_reply_keyboard()

    async def test_sends_prompt_with_current_min_value(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_min"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.message.answer.assert_called_once()
        text = mock_callback_query.message.answer.call_args[0][0]
        assert "10.0" in text
        kwargs = mock_callback_query.message.answer.call_args[1]
        assert kwargs["reply_markup"] == get_cancel_edit_reply_keyboard()

    async def test_sends_prompt_with_current_max_value(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_max"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_callback_query.message.answer.assert_called_once()
        text = mock_callback_query.message.answer.call_args[0][0]
        assert "100.0" in text
        kwargs = mock_callback_query.message.answer.call_args[1]
        assert kwargs["reply_markup"] == get_cancel_edit_reply_keyboard()

    async def test_cancel_keyboard(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_query"
        mock_message_bus.query.return_value = sample_nike_search

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        kwargs = mock_callback_query.message.answer.call_args[1]
        assert kwargs["reply_markup"] == get_cancel_edit_reply_keyboard()

    async def test_error_clears_state(
        self,
        mock_callback_query,
        mock_fsm_context,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_callback_query.data = "editfield_1_query"
        mock_message_bus.query.return_value = sample_nike_search
        mock_callback_query.message.edit_text.side_effect = TelegramAPIError(
            method=MagicMock(), message="error"
        )

        await handle_edit_field(mock_callback_query, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()


class TestCancelEditField:
    async def test_clears_and_shows_edit(self, mock_message, mock_fsm_context):
        await cancel_editfield(mock_message, mock_fsm_context)

        mock_fsm_context.clear.assert_called_once()
        mock_message.answer.assert_called_once_with(
            "Editing cancelled", reply_markup=ReplyKeyboardRemove()
        )


class TestEditQuery:
    async def test_no_text(self, mock_message, edit_fsm_data, mock_message_bus):
        mock_message.text = None

        await edit_query(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "Please enter a valid search term like 'vintage jacket'."
        )
        mock_message_bus.execute.assert_not_called()

    async def test_invalid_query(self, mock_message, edit_fsm_data, mock_message_bus):
        mock_message.text = "a"

        await edit_query(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_called_once_with(
            "Search term must be at least 2 characters long."
        )
        mock_message_bus.execute.assert_not_called()

    async def test_missing_search_id(
        self, mock_message, mock_fsm_context, mock_message_bus
    ):
        mock_message.text = "new query"
        mock_fsm_context.get_data.return_value = {}

        await edit_query(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()

    async def test_success(self, mock_message, edit_fsm_data, mock_message_bus):
        mock_message.text = "new query"

        await edit_query(mock_message, edit_fsm_data, mock_message_bus)

        mock_message_bus.execute.assert_called_once()
        cmd = mock_message_bus.execute.call_args[0][0]
        assert isinstance(cmd, UpdateSearchCommand)
        assert cmd.query == "new query"
        mock_message_bus.publish.assert_called_once()
        event = mock_message_bus.publish.call_args[0][0]
        assert isinstance(event, UpdateSearchEvent)
        edit_fsm_data.clear.assert_called()
        mock_message.answer.assert_called_once_with(
            "Search query updated successfully.", reply_markup=ReplyKeyboardRemove()
        )

    async def test_update_error(self, mock_message, edit_fsm_data, mock_message_bus):
        mock_message.text = "new query"
        mock_message_bus.execute.side_effect = Exception("db error")

        await edit_query(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_not_called()

    async def test_calls_update_message_helper(
        self, mock_message, edit_fsm_data, mock_message_bus, mocker
    ):
        mock_message.text = "new query"
        helper = mocker.patch(
            "src.telegram_bot.routers.my_searches._update_message_after_update",
            new_callable=AsyncMock,
        )

        await edit_query(mock_message, edit_fsm_data, mock_message_bus)

        helper.assert_called_once()

    async def test_unexpected_error_clears(
        self, mock_message, mock_fsm_context, mock_message_bus
    ):
        mock_message.text = "new query"
        mock_fsm_context.get_data.side_effect = RuntimeError("unexpected")

        await edit_query(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()

    async def test_no_bot_skips_helper(
        self, mock_message, edit_fsm_data, mock_message_bus, mocker
    ):
        mock_message.text = "new query"
        mock_message.bot = None
        helper = mocker.patch(
            "src.telegram_bot.routers.my_searches._update_message_after_update",
            new_callable=AsyncMock,
        )

        await edit_query(mock_message, edit_fsm_data, mock_message_bus)

        helper.assert_not_called()


class TestEditPriceMin:
    @_price_params
    async def test_no_text(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
    ):
        mock_message.text = None

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_called_once()

    @_price_params
    async def test_non_numeric(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
    ):
        mock_message.text = "abc"

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_called_once()

    @_price_params
    async def test_missing_search_id(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        mock_fsm_context,
        mock_message_bus,
    ):
        mock_message.text = "50"
        mock_fsm_context.get_data.return_value = {}

        await handler(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()

    @_price_params
    async def test_query_error(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
    ):
        mock_message.text = "50"
        mock_message_bus.query.side_effect = Exception("db error")

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_not_called()

    @_price_params
    async def test_not_found(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
    ):
        mock_message.text = "50"
        mock_message_bus.query.return_value = None

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_not_called()

    @_price_params
    async def test_invalid_range(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_message.text = invalid_range_text
        mock_message_bus.query.return_value = sample_nike_search

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message_bus.execute.assert_not_called()

    @_price_params
    async def test_executes_update(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_message.text = valid_text
        mock_message_bus.query.return_value = sample_nike_search

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message_bus.execute.assert_called_once()
        cmd = mock_message_bus.execute.call_args[0][0]
        assert isinstance(cmd, UpdateSearchCommand)
        assert getattr(cmd, cmd_field) == expected_value

    @_price_params
    async def test_publishes_event(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_message.text = valid_text
        mock_message_bus.query.return_value = sample_nike_search

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message_bus.publish.assert_called_once()

    @_price_params
    async def test_clears_state(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_message.text = valid_text
        mock_message_bus.query.return_value = sample_nike_search

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        edit_fsm_data.clear.assert_called()

    @_price_params
    async def test_success_message(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_message.text = valid_text
        mock_message_bus.query.return_value = sample_nike_search

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "updated successfully" in text.lower()
        kwargs = mock_message.answer.call_args[1]
        assert isinstance(kwargs["reply_markup"], ReplyKeyboardRemove)

    @_price_params
    async def test_update_error(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
    ):
        mock_message.text = valid_text
        mock_message_bus.query.return_value = sample_nike_search
        mock_message_bus.execute.side_effect = Exception("db error")

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        mock_message.answer.assert_not_called()

    @_price_params
    async def test_calls_helper(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
        mocker,
    ):
        mock_message.text = valid_text
        mock_message_bus.query.return_value = sample_nike_search
        helper = mocker.patch(
            "src.telegram_bot.routers.my_searches._update_message_after_update",
            new_callable=AsyncMock,
        )

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        helper.assert_called_once()

    @_price_params
    async def test_no_bot_skips_helper(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        edit_fsm_data,
        mock_message_bus,
        sample_nike_search,
        mocker,
    ):
        mock_message.text = valid_text
        mock_message.bot = None
        mock_message_bus.query.return_value = sample_nike_search
        helper = mocker.patch(
            "src.telegram_bot.routers.my_searches._update_message_after_update",
            new_callable=AsyncMock,
        )

        await handler(mock_message, edit_fsm_data, mock_message_bus)

        helper.assert_not_called()

    @_price_params
    async def test_unexpected_error_clears(
        self,
        handler,
        valid_text,
        invalid_range_text,
        expected_value,
        cmd_field,
        mock_message,
        mock_fsm_context,
        mock_message_bus,
    ):
        mock_message.text = valid_text
        mock_fsm_context.get_data.side_effect = RuntimeError("unexpected")

        await handler(mock_message, mock_fsm_context, mock_message_bus)

        mock_fsm_context.clear.assert_called()


class TestResolveSearchFromCallback:
    async def test_query_error(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.side_effect = Exception("db error")

        result = await _resolve_search_from_callback(
            mock_callback_query, mock_message_bus, 1, 12345
        )

        assert result is None
        mock_callback_query.answer.assert_not_called()

    async def test_not_found(self, mock_callback_query, mock_message_bus):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.return_value = None

        result = await _resolve_search_from_callback(
            mock_callback_query, mock_message_bus, 1, 12345
        )

        assert result is None
        mock_callback_query.answer.assert_not_called()

    async def test_not_message_instance(
        self, mock_callback_query, mock_message_bus, sample_nike_search
    ):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.return_value = sample_nike_search
        mock_callback_query.message = MagicMock()  # Not a Message instance
        mock_callback_query.message.chat.id = 12345

        result = await _resolve_search_from_callback(
            mock_callback_query, mock_message_bus, 1, 12345
        )

        assert result is None

    async def test_success_returns_tuple(
        self, mock_callback_query, mock_message_bus, sample_nike_search
    ):
        mock_callback_query.data = "remove_1"
        mock_message_bus.query.return_value = sample_nike_search

        result = await _resolve_search_from_callback(
            mock_callback_query, mock_message_bus, 1, 12345
        )

        assert result is not None
        search, msg = result
        assert search == sample_nike_search


class TestUpdateMessageAfterUpdate:
    async def test_success(self, mock_bot, mock_message_bus, sample_nike_search):
        mock_message_bus.query.return_value = sample_nike_search

        await _update_message_after_update(
            bot=mock_bot,
            message_bus=mock_message_bus,
            message_id=100,
            chat_id=12345,
            search_id=1,
        )

        mock_message_bus.query.assert_called_once_with(GetSearchByIdQuery(search_id=1))
        mock_bot.edit_message_text.assert_called_once()
        kwargs = mock_bot.edit_message_text.call_args[1]
        assert kwargs["chat_id"] == 12345
        assert kwargs["message_id"] == 100
        assert "nike shoes" in kwargs["text"]
        _, expected_markup = build_my_search_listing_message(sample_nike_search)
        assert kwargs["reply_markup"] == expected_markup
        assert kwargs["parse_mode"] == "HTML"

    async def test_query_error(self, mock_bot, mock_message_bus):
        mock_message_bus.query.side_effect = Exception("db error")

        await _update_message_after_update(
            bot=mock_bot,
            message_bus=mock_message_bus,
            message_id=100,
            chat_id=12345,
            search_id=1,
        )

        mock_bot.edit_message_text.assert_not_called()

    async def test_not_found(self, mock_bot, mock_message_bus):
        mock_message_bus.query.return_value = None

        await _update_message_after_update(
            bot=mock_bot,
            message_bus=mock_message_bus,
            message_id=100,
            chat_id=12345,
            search_id=1,
        )

        mock_bot.edit_message_text.assert_not_called()

    async def test_build_error(
        self, mock_bot, mock_message_bus, sample_nike_search, mocker
    ):
        mock_message_bus.query.return_value = sample_nike_search
        mocker.patch(
            "src.telegram_bot.routers.my_searches.build_my_search_listing_message",
            side_effect=Exception("build error"),
        )

        await _update_message_after_update(
            bot=mock_bot,
            message_bus=mock_message_bus,
            message_id=100,
            chat_id=12345,
            search_id=1,
        )

        mock_bot.edit_message_text.assert_not_called()


class TestValidateCallback:
    async def test_valid_returns_data_and_message(self, mock_callback_query):
        mock_callback_query.data = "remove_42"

        result = await validate_callback(mock_callback_query, prefix="remove")

        assert result is not None
        data, msg = result
        assert data == "remove_42"
        assert isinstance(msg, Message)

    async def test_valid_double_prefix(self, mock_callback_query):
        mock_callback_query.data = "confirm_remove_7"

        result = await validate_callback(mock_callback_query, prefix="confirm_remove")

        assert result is not None
        data, msg = result
        assert data == "confirm_remove_7"

    async def test_missing_data(self, mock_callback_query):
        mock_callback_query.data = None

        result = await validate_callback(mock_callback_query, prefix="remove")

        assert result is None
        mock_callback_query.answer.assert_not_called()

    async def test_missing_message(self, mock_callback_query):
        mock_callback_query.data = "remove_1"
        mock_callback_query.message = None

        result = await validate_callback(mock_callback_query, prefix="remove")

        assert result is None

    async def test_wrong_prefix(self, mock_callback_query):
        mock_callback_query.data = "edit_1"

        result = await validate_callback(mock_callback_query, prefix="remove")

        assert result is None

    async def test_not_message_instance(self, mock_callback_query):
        mock_callback_query.data = "remove_1"
        mock_callback_query.message = MagicMock()  # Not a Message instance

        result = await validate_callback(mock_callback_query, prefix="remove")

        assert result is None
