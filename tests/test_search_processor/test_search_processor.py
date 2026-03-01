import pytest
from unittest.mock import AsyncMock

from src.search_processor.search_processor import SearchProcessor
from src.vinted_network_client.vinted_network_client import VintedNetworkClient
from src.vinted_network_client.models.vinted_domain import VintedDomain
from src.message_bus.events.start_searching_event import StartSearchingEvent
from src.message_bus.events.stop_searching_event import StopSearchingEvent
from src.message_bus.events.new_search_event import NewSearchEvent
from src.message_bus.events.remove_search_event import RemoveSearchEvent
from src.message_bus.events.update_search_event import UpdateSearchEvent
from src.message_bus.queries.get_all_searches_query import GetAllSearchesQuery
from src.message_bus.queries.get_search_by_id_query import GetSearchByIdQuery
from src.telegram_bot.models.search import Search
from tests.test_search_processor.helpers import make_mock_task


class TestSetup:

    async def test_creates_vinted_client(
        self, mock_message_bus, mock_proxy_manager, mock_vinted_client_class
    ):
        """setup() calls VintedNetworkClient.create with correct domain, user_agents and proxy_manager."""
        agents = [{"ua": "TestAgent"}]
        processor = SearchProcessor(
            message_bus=mock_message_bus,
            user_agents=agents,
            proxy_manager=mock_proxy_manager,
            domain=VintedDomain.FR,
        )
        await processor.setup()

        mock_vinted_client_class.assert_called_once_with(
            domain=VintedDomain.FR, user_agents=agents, proxy_manager=mock_proxy_manager
        )

    async def test_loads_searches_from_database(
        self, search_processor, mock_message_bus
    ):
        """setup() queries the database for existing searches."""
        mock_message_bus.query.assert_called_once_with(GetAllSearchesQuery())

    async def test_creates_search_tasks_for_each_search(
        self, mock_message_bus, mock_proxy_manager, mock_vinted_client_class
    ):
        """setup() creates one SearchTask per search returned from DB."""
        search1 = Search(id=1, chat_id="111", query="shoes", price_min=0, price_max=50)
        search2 = Search(id=2, chat_id="222", query="hats", price_min=5, price_max=100)
        mock_message_bus.query.return_value = [search1, search2]

        processor = SearchProcessor(
            message_bus=mock_message_bus,
            user_agents=[{"ua": "TestAgent"}],
            proxy_manager=mock_proxy_manager,
            domain=VintedDomain.PL,
        )
        await processor.setup()

        assert len(processor._tasks) == 2
        assert processor._tasks[0].search_id == 1
        assert processor._tasks[1].search_id == 2

    async def test_with_no_searches_creates_empty_task_list(self, search_processor):
        """setup() with no searches in DB creates an empty tasks list."""
        assert len(search_processor._tasks) == 0

    async def test_propagates_client_creation_error(
        self, mock_message_bus, mock_proxy_manager, mocker
    ):
        """setup() propagates exception from VintedNetworkClient.create."""
        mocker.patch.object(
            VintedNetworkClient,
            "create",
            new_callable=AsyncMock,
            side_effect=RuntimeError("connection failed"),
        )
        processor = SearchProcessor(
            message_bus=mock_message_bus,
            user_agents=[{"ua": "TestAgent"}],
            proxy_manager=mock_proxy_manager,
            domain=VintedDomain.PL,
        )

        with pytest.raises(RuntimeError, match="connection failed"):
            await processor.setup()

    async def test_propagates_query_error(
        self, mock_message_bus, mock_proxy_manager, mock_vinted_client_class
    ):
        """setup() propagates exception when message_bus.query fails."""
        mock_message_bus.query.side_effect = RuntimeError("db unavailable")
        processor = SearchProcessor(
            message_bus=mock_message_bus,
            user_agents=[{"ua": "TestAgent"}],
            proxy_manager=mock_proxy_manager,
            domain=VintedDomain.PL,
        )

        with pytest.raises(RuntimeError, match="db unavailable"):
            await processor.setup()

    async def test_does_not_set_is_running(self, search_processor):
        """setup() leaves _is_running as False."""
        assert search_processor._is_running is False

    async def test_stores_client(self, search_processor, mock_vinted_client):
        """setup() stores the created client as _client."""
        assert search_processor._client is mock_vinted_client


class TestClose:

    async def test_closes_vinted_client(self, search_processor, mock_vinted_client):
        """close() calls _client.close()."""
        await search_processor.close()
        mock_vinted_client.close.assert_called()

    async def test_stops_all_tasks(self, search_processor, running_processor):
        """close() stops every task."""
        task1, task2 = running_processor(1, 2)

        await search_processor.close()

        task1.stop.assert_called_once()
        task2.stop.assert_called_once()

    async def test_clears_task_list(self, search_processor, running_processor):
        """close() empties _tasks after completion."""
        running_processor(1)

        await search_processor.close()

        assert search_processor._tasks == []

    async def test_handles_client_close_error(
        self, search_processor, mock_vinted_client
    ):
        """close() logs but doesn't raise when _client.close() fails."""
        mock_vinted_client.close.side_effect = RuntimeError("close failed")
        task = make_mock_task(1)
        search_processor._tasks = [task]
        search_processor._is_running = True

        await search_processor.close()

        task.stop.assert_called_once()
        assert search_processor._tasks == []

    async def test_handles_task_stop_error(self, search_processor):
        """close() logs but doesn't raise when task.stop() fails, list still cleared."""
        task = make_mock_task(1)
        task.stop.side_effect = RuntimeError("stop failed")
        search_processor._tasks = [task]
        search_processor._is_running = True

        await search_processor.close()

        assert search_processor._tasks == []

    async def test_when_not_running_still_closes_client_and_clears(
        self, search_processor, mock_vinted_client
    ):
        """close() when _is_running=False still closes client and clears tasks."""
        search_processor._tasks = [make_mock_task(1)]
        search_processor._is_running = False

        await search_processor.close()

        mock_vinted_client.close.assert_called()
        assert search_processor._tasks == []

    async def test_handles_both_client_and_tasks_failing(
        self, search_processor, mock_vinted_client
    ):
        """close() clears tasks even when both _client.close() and _stop_all_tasks() fail."""
        mock_vinted_client.close.side_effect = RuntimeError("client close failed")
        task = make_mock_task(1)
        task.stop.side_effect = RuntimeError("stop failed")
        search_processor._tasks = [task]
        search_processor._is_running = True

        await search_processor.close()

        assert search_processor._tasks == []

    async def test_is_idempotent(self, search_processor, running_processor):
        """close() can be called twice without raising."""
        running_processor(1)

        await search_processor.close()
        await search_processor.close()

        assert search_processor._tasks == []


class TestStartSearching:

    async def test_starts_all_tasks(self, search_processor):
        """start_searching() calls start() on all tasks."""
        task1 = make_mock_task(1)
        task2 = make_mock_task(2)
        task3 = make_mock_task(3)
        search_processor._tasks = [task1, task2, task3]

        await search_processor.start_searching(StartSearchingEvent())

        task1.start.assert_called_once()
        task2.start.assert_called_once()
        task3.start.assert_called_once()

    async def test_sets_is_running(self, search_processor):
        """start_searching() sets _is_running to True."""
        search_processor._tasks = [make_mock_task(1)]

        await search_processor.start_searching(StartSearchingEvent())

        assert search_processor._is_running is True

    async def test_already_running_returns_early(
        self, search_processor, running_processor
    ):
        """start_searching() when already running does not call task.start()."""
        (task,) = running_processor(1)

        await search_processor.start_searching(StartSearchingEvent())

        task.start.assert_not_called()

    async def test_no_tasks_returns_early(self, search_processor):
        """start_searching() with no tasks keeps _is_running False."""
        search_processor._tasks = []

        await search_processor.start_searching(StartSearchingEvent())

        assert search_processor._is_running is False

    @pytest.mark.parametrize(
        "fail_indices, task_count",
        [
            ([1], 3),
            ([0, 1], 2),
        ],
        ids=["one_task_fails", "all_tasks_fail"],
    )
    async def test_handles_task_failures(
        self, search_processor, fail_indices, task_count
    ):
        """start_searching() calls start() on all tasks and sets _is_running True even when some fail."""
        tasks = []
        for i in range(task_count):
            task = make_mock_task(i)
            if i in fail_indices:
                task.start.side_effect = RuntimeError(f"fail{i}")
            tasks.append(task)
        search_processor._tasks = tasks

        await search_processor.start_searching(StartSearchingEvent())

        for task in tasks:
            task.start.assert_called_once()
        assert search_processor._is_running is True


class TestStopSearching:

    async def test_stops_all_tasks(self, search_processor, running_processor):
        """stop_searching() stops all tasks and sets _is_running to False."""
        task1, task2 = running_processor(1, 2)

        await search_processor.stop_searching(StopSearchingEvent())

        task1.stop.assert_called_once()
        task2.stop.assert_called_once()
        assert search_processor._is_running is False

    async def test_when_not_running(self, search_processor):
        """stop_searching() when not running does not call stop on tasks."""
        task = make_mock_task(1)
        search_processor._tasks = [task]
        search_processor._is_running = False

        await search_processor.stop_searching(StopSearchingEvent())

        task.stop.assert_not_called()

    async def test_handles_stop_error(self, search_processor):
        """stop_searching() doesn't propagate when _stop_all_tasks raises."""
        task = make_mock_task(1)
        task.stop.side_effect = RuntimeError("stop failed")
        search_processor._tasks = [task]
        search_processor._is_running = True

        await search_processor.stop_searching(StopSearchingEvent())


class TestAddSearch:

    async def test_creates_and_appends_task(self, search_processor):
        """add_search() appends a new task to the list."""
        search = Search(id=10, chat_id="123", query="test", price_min=0, price_max=50)
        event = NewSearchEvent(search=search)

        await search_processor.add_search(event)

        assert len(search_processor._tasks) == 1
        assert search_processor._tasks[0].search_id == 10

    async def test_starts_task_when_running(self, search_processor, mocker):
        """add_search() starts the new task when _is_running is True."""
        search_processor._is_running = True
        search = Search(id=10, chat_id="123", query="test", price_min=0, price_max=50)
        event = NewSearchEvent(search=search)

        mock_task = make_mock_task(10)
        mocker.patch(
            "src.search_processor.search_processor.SearchTask", return_value=mock_task
        )

        await search_processor.add_search(event)

        mock_task.start.assert_called_once()

    async def test_does_not_start_task_when_not_running(self, search_processor, mocker):
        """add_search() does not start the task when _is_running is False."""
        search_processor._is_running = False
        search = Search(id=10, chat_id="123", query="test", price_min=0, price_max=50)
        event = NewSearchEvent(search=search)

        mock_task = make_mock_task(10)
        mocker.patch(
            "src.search_processor.search_processor.SearchTask", return_value=mock_task
        )

        await search_processor.add_search(event)

        mock_task.start.assert_not_called()

    async def test_handles_constructor_exception(self, search_processor, mocker):
        """add_search() doesn't propagate if SearchTask constructor raises, task not added."""
        mocker.patch(
            "src.search_processor.search_processor.SearchTask",
            side_effect=RuntimeError("constructor failed"),
        )
        search = Search(id=10, chat_id="123", query="test", price_min=0, price_max=50)
        event = NewSearchEvent(search=search)

        await search_processor.add_search(event)

        assert len(search_processor._tasks) == 0

    async def test_start_failure_keeps_task_in_list(self, search_processor, mocker):
        """add_search() keeps the task in _tasks even when start() raises."""
        search_processor._is_running = True
        mock_task = make_mock_task(10)
        mock_task.start.side_effect = RuntimeError("start failed")
        mocker.patch(
            "src.search_processor.search_processor.SearchTask", return_value=mock_task
        )
        search = Search(id=10, chat_id="123", query="test", price_min=0, price_max=50)
        event = NewSearchEvent(search=search)

        await search_processor.add_search(event)

        assert len(search_processor._tasks) == 1
        mock_task.start.assert_called_once()

    async def test_uses_correct_search_from_event(self, search_processor, mocker):
        """add_search() passes the Search from the event to SearchTask."""
        search = Search(id=10, chat_id="123", query="test", price_min=0, price_max=50)
        event = NewSearchEvent(search=search)

        mock_cls = mocker.patch(
            "src.search_processor.search_processor.SearchTask",
            return_value=make_mock_task(10),
        )

        await search_processor.add_search(event)

        mock_cls.assert_called_once_with(
            search_processor._client, search_processor._message_bus, search
        )

    async def test_multiple_adds_accumulate(self, search_processor):
        """add_search() called multiple times appends all tasks."""
        for i in range(3):
            search = Search(
                id=i + 1, chat_id="123", query=f"q{i}", price_min=0, price_max=50
            )
            await search_processor.add_search(NewSearchEvent(search=search))

        assert len(search_processor._tasks) == 3
        assert search_processor._tasks[0].search_id == 1
        assert search_processor._tasks[1].search_id == 2
        assert search_processor._tasks[2].search_id == 3


class TestRemoveSearch:

    async def test_stops_and_removes_task(self, search_processor):
        """remove_search() stops the task and removes it from the list."""
        task = make_mock_task(10)
        search_processor._tasks = [task]
        event = RemoveSearchEvent(search_id=10)

        await search_processor.remove_search(event)

        task.stop.assert_called_once()
        assert len(search_processor._tasks) == 0

    async def test_not_found_leaves_existing_tasks(self, search_processor):
        """remove_search() with unknown search_id leaves existing tasks intact."""
        existing_task = make_mock_task(1)
        search_processor._tasks = [existing_task]
        event = RemoveSearchEvent(search_id=999)

        await search_processor.remove_search(event)

        assert search_processor._tasks == [existing_task]
        existing_task.stop.assert_not_called()

    async def test_handles_stop_failure(self, search_processor):
        """remove_search() still removes the task even if stop() fails."""
        task = make_mock_task(10)
        task.stop.side_effect = RuntimeError("stop failed")
        search_processor._tasks = [task]
        event = RemoveSearchEvent(search_id=10)

        await search_processor.remove_search(event)

        assert len(search_processor._tasks) == 0

    async def test_leaves_other_tasks_intact(self, search_processor):
        """remove_search() only removes the target task."""
        task1 = make_mock_task(1)
        task2 = make_mock_task(2)
        search_processor._tasks = [task1, task2]
        event = RemoveSearchEvent(search_id=1)

        await search_processor.remove_search(event)

        assert search_processor._tasks == [task2]

    async def test_with_multiple_tasks_removes_correct_one(self, search_processor):
        """remove_search() removes only the matching task from 3 tasks."""
        task1 = make_mock_task(1)
        task2 = make_mock_task(2)
        task3 = make_mock_task(3)
        search_processor._tasks = [task1, task2, task3]
        event = RemoveSearchEvent(search_id=2)

        await search_processor.remove_search(event)

        assert search_processor._tasks == [task1, task3]
        task2.stop.assert_called_once()
        task1.stop.assert_not_called()
        task3.stop.assert_not_called()

    async def test_from_empty_list(self, search_processor):
        """remove_search() on empty _tasks list does not raise."""
        search_processor._tasks = []
        event = RemoveSearchEvent(search_id=1)

        await search_processor.remove_search(event)

        assert search_processor._tasks == []

    async def test_duplicate_ids_removes_first_match(self, search_processor):
        """remove_search() with duplicate search_ids only removes the first match."""
        task_a = make_mock_task(10)
        task_b = make_mock_task(10)
        search_processor._tasks = [task_a, task_b]
        event = RemoveSearchEvent(search_id=10)

        await search_processor.remove_search(event)

        assert len(search_processor._tasks) == 1
        assert search_processor._tasks[0] is task_b
        task_a.stop.assert_called_once()
        task_b.stop.assert_not_called()


class TestUpdateSearch:

    async def test_queries_database_and_updates_task(
        self, search_processor, mock_message_bus
    ):
        """update_search() queries the DB and calls task.update_search()."""
        task = make_mock_task(10)
        search_processor._tasks = [task]
        updated = Search(
            id=10, chat_id="123", query="updated", price_min=0, price_max=99
        )
        mock_message_bus.query.return_value = updated
        event = UpdateSearchEvent(search_id=10)

        await search_processor.update_search(event)

        task.update_search.assert_called_once_with(updated)

    async def test_task_not_found_logs_warning(
        self, search_processor, mock_message_bus
    ):
        """update_search() with unknown search_id doesn't raise and skips DB query."""
        mock_message_bus.query.reset_mock()
        event = UpdateSearchEvent(search_id=999)

        await search_processor.update_search(event)

        mock_message_bus.query.assert_not_called()

    async def test_search_not_in_database(self, search_processor, mock_message_bus):
        """update_search() doesn't call task.update_search when query returns None."""
        task = make_mock_task(10)
        search_processor._tasks = [task]
        mock_message_bus.query.return_value = None
        event = UpdateSearchEvent(search_id=10)

        await search_processor.update_search(event)

        task.update_search.assert_not_called()

    async def test_handles_query_error(self, search_processor, mock_message_bus):
        """update_search() doesn't propagate when message_bus.query raises."""
        task = make_mock_task(10)
        search_processor._tasks = [task]
        mock_message_bus.query.side_effect = RuntimeError("db error")
        event = UpdateSearchEvent(search_id=10)

        await search_processor.update_search(event)

        task.update_search.assert_not_called()

    async def test_handles_update_error(self, search_processor, mock_message_bus):
        """update_search() doesn't propagate when task.update_search raises and task remains in list."""
        task = make_mock_task(10)
        search_processor._tasks = [task]
        updated = Search(
            id=10, chat_id="123", query="updated", price_min=0, price_max=99
        )
        mock_message_bus.query.return_value = updated
        task.update_search.side_effect = RuntimeError("update failed")
        event = UpdateSearchEvent(search_id=10)

        await search_processor.update_search(event)

        assert search_processor._tasks == [task]

    async def test_passes_correct_search_id_to_query(
        self, search_processor, mock_message_bus
    ):
        """update_search() passes the correct search_id to GetSearchByIdQuery."""
        task = make_mock_task(42)
        search_processor._tasks = [task]
        mock_message_bus.query.reset_mock()
        mock_message_bus.query.return_value = None
        event = UpdateSearchEvent(search_id=42)

        await search_processor.update_search(event)

        mock_message_bus.query.assert_called_once_with(GetSearchByIdQuery(search_id=42))

    async def test_with_multiple_tasks_updates_correct_one(
        self, search_processor, mock_message_bus
    ):
        """update_search() only updates the matching task, others untouched."""
        task1 = make_mock_task(1)
        task2 = make_mock_task(2)
        task3 = make_mock_task(3)
        search_processor._tasks = [task1, task2, task3]
        updated = Search(
            id=2, chat_id="123", query="updated", price_min=0, price_max=99
        )
        mock_message_bus.query.return_value = updated
        event = UpdateSearchEvent(search_id=2)

        await search_processor.update_search(event)

        task2.update_search.assert_called_once_with(updated)
        task1.update_search.assert_not_called()
        task3.update_search.assert_not_called()

    async def test_does_not_remove_task(self, search_processor, mock_message_bus):
        """update_search() keeps all tasks in list after successful update."""
        task = make_mock_task(10)
        search_processor._tasks = [task]
        updated = Search(
            id=10, chat_id="123", query="updated", price_min=0, price_max=99
        )
        mock_message_bus.query.return_value = updated
        event = UpdateSearchEvent(search_id=10)

        await search_processor.update_search(event)

        assert len(search_processor._tasks) == 1
        assert search_processor._tasks[0] is task


class TestStopAllTasks:

    async def test_not_running_returns_early(self, search_processor):
        """_stop_all_tasks() returns immediately when _is_running is False."""
        task = make_mock_task(1)
        search_processor._tasks = [task]
        search_processor._is_running = False

        await search_processor._stop_all_tasks()

        task.stop.assert_not_called()

    async def test_no_tasks_sets_not_running(self, search_processor):
        """_stop_all_tasks() with empty list sets _is_running to False."""
        search_processor._tasks = []
        search_processor._is_running = True

        await search_processor._stop_all_tasks()

        assert search_processor._is_running is False

    async def test_stops_all(self, search_processor, running_processor):
        """_stop_all_tasks() stops all tasks and sets _is_running False."""
        task1, task2 = running_processor(1, 2)

        await search_processor._stop_all_tasks()

        task1.stop.assert_called_once()
        task2.stop.assert_called_once()
        assert search_processor._is_running is False

    @pytest.mark.parametrize(
        "fail_indices, task_count",
        [
            ([1], 3),
            ([0, 1], 2),
        ],
        ids=["one_task_fails", "all_tasks_fail"],
    )
    async def test_handles_failures(self, search_processor, fail_indices, task_count):
        """_stop_all_tasks() stops all tasks and sets _is_running False even when some fail."""
        tasks = []
        for i in range(task_count):
            task = make_mock_task(i)
            if i in fail_indices:
                task.stop.side_effect = RuntimeError(f"fail{i}")
            tasks.append(task)
        search_processor._tasks = tasks
        search_processor._is_running = True

        await search_processor._stop_all_tasks()

        for task in tasks:
            task.stop.assert_called_once()
        assert search_processor._is_running is False
