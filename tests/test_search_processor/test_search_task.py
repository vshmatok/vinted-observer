import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.message_bus.events.item_found_event import ItemFoundEvent
from src.message_bus.queries.filter_new_listings_query import FilterNewListingsQuery
from src.message_bus.queries.get_total_listing_count_for_search_query import (
    GetTotalListingCountForSearchQuery,
)
from src.message_bus.commands.delete_all_listings_for_search_command import (
    DeleteAllListingsForSearchCommand,
)
from src.message_bus.commands.add_listings_for_search_command import (
    AddListingsForSearchCommand,
)


def _make_item(item_id):
    """Helper to create a MagicMock VintedItem with the given id."""
    item = MagicMock()
    item.id = item_id
    return item


def _make_query_side_effect(total_count=0, filtered_ids=None):
    """Helper to build a query side_effect for _execute_iteration tests."""
    if filtered_ids is None:
        filtered_ids = []

    def side_effect(query):
        if isinstance(query, GetTotalListingCountForSearchQuery):
            return total_count
        if isinstance(query, FilterNewListingsQuery):
            return filtered_ids
        return None

    return side_effect


# ============================================================================
# search_id tests
# ============================================================================


def test_search_id_returns_search_id(search_task):
    """search_id returns the id of the internal search object."""
    assert search_task.search_id == 1


# ============================================================================
# is_running tests
# ============================================================================


async def test_is_running_false_before_start(search_task):
    """is_running returns False before start() is called."""
    assert search_task.is_running is False


async def test_is_running_true_after_start(search_task):
    """is_running returns True after start() creates the background task."""
    await search_task.start()
    assert search_task.is_running is True


async def test_is_running_false_after_stop(search_task):
    """is_running returns False after stop() cancels the task."""
    await search_task.start()
    await search_task.stop()
    assert search_task.is_running is False


async def test_is_running_false_when_task_done(search_task):
    """is_running returns False when the internal task has completed."""
    search_task._task = asyncio.ensure_future(asyncio.sleep(0))
    await search_task._task
    assert search_task.is_running is False


# ============================================================================
# start() tests
# ============================================================================


async def test_start_creates_background_task(search_task):
    """start() creates a background asyncio task."""
    await search_task.start()
    assert search_task._task is not None
    assert search_task.is_running is True


async def test_start_twice_is_idempotent(search_task, mocker):
    """Calling start() twice does not create a second task."""
    spy = mocker.patch("asyncio.create_task", wraps=asyncio.create_task)
    await search_task.start()
    await search_task.start()
    spy.assert_called_once()


async def test_start_after_stop_restarts(search_task):
    """start() after stop() creates a new running task."""
    await search_task.start()
    first_task = search_task._task
    await search_task.stop()
    assert search_task.is_running is False

    await search_task.start()
    assert search_task.is_running is True
    assert search_task._task is not first_task


async def test_start_unpauses_previously_paused_task(search_task):
    """start() sets the pause event so a previously paused task runs after restart."""
    await search_task.start()
    search_task.pause()
    assert not search_task._pause_event.is_set()

    await search_task.stop()
    await search_task.start()

    assert search_task._pause_event.is_set()


# ============================================================================
# stop() tests
# ============================================================================


async def test_stop_cancels_running_task(search_task):
    """stop() cancels the running task and is_running becomes False."""
    await search_task.start()
    assert search_task.is_running is True
    await search_task.stop()
    assert search_task.is_running is False


async def test_stop_twice_cancels_only_once(search_task):
    """Calling stop() twice does not cancel the task twice."""
    await search_task.start()
    task = search_task._task
    spy = MagicMock(wraps=task.cancel)
    task.cancel = spy
    await search_task.stop()
    await search_task.stop()
    spy.assert_called_once()


async def test_stop_when_not_running_is_noop(search_task):
    """stop() when not running does nothing and does not raise."""
    await search_task.stop()
    assert search_task.is_running is False


# ============================================================================
# pause() / resume() tests
# ============================================================================


def test_pause_clears_event(search_task):
    """pause() clears the internal event so the loop blocks."""
    assert search_task._pause_event.is_set()
    search_task.pause()
    assert not search_task._pause_event.is_set()


def test_resume_sets_event(search_task):
    """resume() sets the internal event so the loop continues."""
    search_task.pause()
    search_task.resume()
    assert search_task._pause_event.is_set()


def test_pause_twice_is_idempotent(search_task):
    """Calling pause() twice keeps the event cleared."""
    search_task.pause()
    search_task.pause()
    assert not search_task._pause_event.is_set()


def test_resume_when_not_paused_is_idempotent(search_task):
    """Calling resume() when already running keeps the event set."""
    assert search_task._pause_event.is_set()
    search_task.resume()
    assert search_task._pause_event.is_set()


async def test_pause_blocks_execute_iteration(search_task, mocker):
    """_execute_iteration is not called while the task is paused."""
    real_sleep = asyncio.sleep
    spy = mocker.patch.object(search_task, "_execute_iteration", new_callable=AsyncMock)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    await search_task.start()
    search_task.pause()
    await real_sleep(0)

    spy.assert_not_called()


async def test_resume_unblocks_execute_iteration(search_task, mocker):
    """_execute_iteration is called again after resume()."""
    real_sleep = asyncio.sleep
    call_count = 0

    async def counting_iteration():
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError

    mocker.patch.object(
        search_task, "_execute_iteration", side_effect=counting_iteration
    )
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    await search_task.start()
    search_task.pause()
    await real_sleep(0)
    assert call_count == 0

    search_task.resume()
    try:
        await search_task._task
    except asyncio.CancelledError:
        pass

    assert call_count == 2


# ============================================================================
# update_search() tests
# ============================================================================


async def test_update_search_updates_search_object(search_task, updated_search):
    """update_search() replaces the internal _search with the new Search."""
    await search_task.update_search(updated_search)
    assert search_task._search is updated_search


async def test_update_search_executes_delete_command(
    search_task, mock_message_bus, updated_search
):
    """update_search() sends DeleteAllListingsForSearchCommand via message bus."""
    await search_task.update_search(updated_search)
    mock_message_bus.execute.assert_called_once_with(
        DeleteAllListingsForSearchCommand(search_id=2)
    )


async def test_update_search_restarts_if_was_running(search_task, updated_search):
    """update_search() restarts the task if it was running before the update."""
    await search_task.start()
    assert search_task.is_running is True

    await search_task.update_search(updated_search)
    assert search_task.is_running is True


async def test_update_search_stays_stopped_if_was_stopped(search_task, updated_search):
    """update_search() does not start the task if it was stopped."""
    assert search_task.is_running is False
    await search_task.update_search(updated_search)
    assert search_task.is_running is False


async def test_update_search_does_not_raise_on_delete_failure(
    search_task, mock_message_bus, updated_search
):
    """update_search() does not raise if delete command fails."""
    mock_message_bus.execute.side_effect = Exception("db error")

    await search_task.update_search(updated_search)

    assert search_task._search is updated_search


async def test_update_search_restarts_after_delete_failure(
    search_task, mock_message_bus, updated_search, mocker
):
    """update_search() restarts the task even when delete command fails."""
    mocker.patch.object(search_task, "_run_loop", new_callable=AsyncMock)
    await search_task.start()
    mock_message_bus.execute.side_effect = Exception("db error")

    await search_task.update_search(updated_search)

    assert search_task.is_running is True
    assert search_task._search is updated_search


async def test_update_search_while_paused(search_task, updated_search):
    """update_search() on a paused-but-running task restarts it unpaused."""
    await search_task.start()
    search_task.pause()
    assert search_task.is_running is True

    await search_task.update_search(updated_search)

    assert search_task.is_running is True
    assert search_task._pause_event.is_set()


# ============================================================================
# _execute_iteration() tests
# ============================================================================


async def test_first_run_adds_listings_silently(
    search_task, mock_vinted_client, mock_message_bus
):
    """First run (total_count == 0): adds listings with silent=True, no ItemFoundEvent."""
    items = [_make_item(10), _make_item(20)]
    mock_vinted_client.search_items.return_value = items
    mock_message_bus.query.side_effect = _make_query_side_effect(
        total_count=0, filtered_ids=[10, 20]
    )

    await search_task._execute_iteration()

    mock_message_bus.execute.assert_called_once_with(
        AddListingsForSearchCommand(search_id=1, listing_ids=[10, 20], silent=True)
    )
    mock_message_bus.publish.assert_not_called()


async def test_subsequent_run_publishes_events(
    search_task, mock_vinted_client, mock_message_bus
):
    """Subsequent run (total_count > 0): adds with silent=False and publishes ItemFoundEvent."""
    items = [_make_item(10), _make_item(20)]
    mock_vinted_client.search_items.return_value = items
    mock_message_bus.query.side_effect = _make_query_side_effect(
        total_count=5, filtered_ids=[10, 20]
    )

    await search_task._execute_iteration()

    mock_message_bus.execute.assert_called_once_with(
        AddListingsForSearchCommand(search_id=1, listing_ids=[10, 20], silent=False)
    )
    assert mock_message_bus.publish.call_count == 2
    mock_message_bus.publish.assert_any_call(
        ItemFoundEvent(chat_id="12345", item=items[0])
    )
    mock_message_bus.publish.assert_any_call(
        ItemFoundEvent(chat_id="12345", item=items[1])
    )


async def test_items_with_none_id_excluded(
    search_task, mock_vinted_client, mock_message_bus
):
    """Items with id=None are excluded from listing_ids."""
    items = [_make_item(10), _make_item(None), _make_item(30)]
    mock_vinted_client.search_items.return_value = items
    mock_message_bus.query.side_effect = _make_query_side_effect(
        total_count=0, filtered_ids=[10, 30]
    )

    await search_task._execute_iteration()

    filter_call = [
        c
        for c in mock_message_bus.query.call_args_list
        if isinstance(c[0][0], FilterNewListingsQuery)
    ][0]
    assert filter_call[0][0].listing_ids == [10, 30]
    mock_message_bus.execute.assert_called_once_with(
        AddListingsForSearchCommand(search_id=1, listing_ids=[10, 30], silent=True)
    )


async def test_correct_args_passed_to_search_items(
    search_task, mock_vinted_client, mock_message_bus
):
    """search_items is called with correct query, per_page, price_from, price_to."""
    mock_message_bus.query.side_effect = _make_query_side_effect()

    await search_task._execute_iteration()

    mock_vinted_client.search_items.assert_called_once_with(
        "nike shoes",
        per_page=20,
        price_from=10.0,
        price_to=100.0,
    )


async def test_no_items_returned_nothing_added(
    search_task, mock_vinted_client, mock_message_bus
):
    """No items from client — empty listing_ids, nothing published."""
    mock_vinted_client.search_items.return_value = []
    mock_message_bus.query.side_effect = _make_query_side_effect()

    await search_task._execute_iteration()

    mock_message_bus.execute.assert_called_once_with(
        AddListingsForSearchCommand(search_id=1, listing_ids=[], silent=True)
    )
    mock_message_bus.publish.assert_not_called()


async def test_subsequent_run_only_publishes_filtered_items(
    search_task, mock_vinted_client, mock_message_bus
):
    """Only filtered items are published, not all returned items."""
    items = [_make_item(10), _make_item(20), _make_item(30)]
    mock_vinted_client.search_items.return_value = items
    mock_message_bus.query.side_effect = _make_query_side_effect(
        total_count=5, filtered_ids=[10, 30]
    )

    await search_task._execute_iteration()

    assert mock_message_bus.publish.call_count == 2
    published_items = [c[0][0].item for c in mock_message_bus.publish.call_args_list]
    assert published_items == [items[0], items[2]]


async def test_subsequent_run_no_new_items_publishes_nothing(
    search_task, mock_vinted_client, mock_message_bus
):
    """Subsequent run where filter returns empty list — nothing published."""
    items = [_make_item(10), _make_item(20)]
    mock_vinted_client.search_items.return_value = items
    mock_message_bus.query.side_effect = _make_query_side_effect(total_count=5)

    await search_task._execute_iteration()

    mock_message_bus.execute.assert_called_once_with(
        AddListingsForSearchCommand(search_id=1, listing_ids=[], silent=False)
    )
    mock_message_bus.publish.assert_not_called()


async def test_execute_iteration_propagates_search_items_error(
    search_task, mock_vinted_client
):
    """Exception from search_items propagates out of _execute_iteration."""
    mock_vinted_client.search_items.side_effect = RuntimeError("network error")

    with pytest.raises(RuntimeError, match="network error"):
        await search_task._execute_iteration()


async def test_execute_iteration_propagates_query_error(
    search_task, mock_vinted_client, mock_message_bus
):
    """Exception from message_bus.query propagates out of _execute_iteration."""
    mock_vinted_client.search_items.return_value = [_make_item(10)]
    mock_message_bus.query.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError, match="db error"):
        await search_task._execute_iteration()


async def test_execute_iteration_propagates_execute_error(
    search_task, mock_vinted_client, mock_message_bus
):
    """Exception from message_bus.execute propagates out of _execute_iteration."""
    mock_vinted_client.search_items.return_value = [_make_item(10)]
    mock_message_bus.query.side_effect = _make_query_side_effect(filtered_ids=[10])
    mock_message_bus.execute.side_effect = RuntimeError("write error")

    with pytest.raises(RuntimeError, match="write error"):
        await search_task._execute_iteration()


# ============================================================================
# _run_loop() error handling tests
# ============================================================================


async def test_run_loop_cancelled_error_reraises(search_task, mocker):
    """CancelledError is re-raised, causing the loop to exit."""
    mocker.patch.object(
        search_task, "_execute_iteration", side_effect=asyncio.CancelledError
    )
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    with pytest.raises(asyncio.CancelledError):
        await search_task._run_loop()


async def test_run_loop_other_exception_continues(search_task, mocker):
    """Other exceptions are logged but the loop continues."""
    call_count = 0

    async def iteration_with_error():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient error")
        if call_count == 2:
            raise asyncio.CancelledError

    mocker.patch.object(
        search_task, "_execute_iteration", side_effect=iteration_with_error
    )

    with pytest.raises(asyncio.CancelledError):
        await search_task._run_loop()

    assert call_count == 2


async def test_run_loop_sleeps_with_configured_time(search_task, mocker):
    """_run_loop passes search_sleep_time to asyncio.sleep."""
    search_task._search_sleep_time = 42
    call_count = 0

    async def two_iterations():
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError

    mocker.patch.object(search_task, "_execute_iteration", side_effect=two_iterations)
    sleep_mock = mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    with pytest.raises(asyncio.CancelledError):
        await search_task._run_loop()

    sleep_mock.assert_called_with(42)
