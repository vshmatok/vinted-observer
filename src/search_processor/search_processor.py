import asyncio
import logging
from typing import Optional

from src.search_processor.search_task import SearchTask
from src.vinted_network_client.vinted_network_client import VintedNetworkClient
from src.message_bus.events.new_search_event import NewSearchEvent
from src.message_bus.events.remove_search_event import RemoveSearchEvent
from src.message_bus.events.update_search_event import UpdateSearchEvent
from src.message_bus.message_bus import MessageBus
from src.message_bus.events.start_searching_event import StartSearchingEvent
from src.message_bus.events.stop_searching_event import StopSearchingEvent
from src.message_bus.queries.get_all_searches_query import GetAllSearchesQuery
from src.message_bus.queries.get_search_by_id_query import GetSearchByIdQuery
from src.config import Config
from src.vinted_network_client.utils.proxy_manager import ProxyManager
from src.vinted_network_client.models.vinted_domain import VintedDomain

logger = logging.getLogger(__name__)


class SearchProcessor:
    def __init__(
        self,
        message_bus: MessageBus,
        user_agents: list[dict],
        proxy_manager: Optional[ProxyManager],
        domain: VintedDomain = Config.VINTED_DOMAIN,
    ):
        self._is_running = False
        self._lock = asyncio.Lock()
        self._tasks = []
        self._message_bus = message_bus
        self._user_agents = user_agents
        self._proxy_manager = proxy_manager
        self._domain = domain

    async def setup(self):
        """Setup Vinted client and load existing searches. Raises on failure."""

        # Setup VintedNetworkClient
        logger.info("Setting up search processor...")
        self._client = await VintedNetworkClient.create(
            domain=self._domain,
            user_agents=self._user_agents,
            proxy_manager=self._proxy_manager,
        )
        logger.info("Vinted network client created successfully")

        # Setup tasks
        searches = await self._message_bus.query(GetAllSearchesQuery())
        for search in searches:
            task = SearchTask(self._client, self._message_bus, search)
            self._tasks.append(task)

        logger.info(f"Loaded {len(self._tasks)} search tasks from database")

    async def close(self):
        """Close search processor and cleanup resources. Logs errors but doesn't raise."""
        async with self._lock:
            try:
                await self._client.close()
                logger.info("Vinted network client closed successfully")
            except Exception as e:
                logger.error(f"Error closing Vinted network client: {e}", exc_info=True)

            try:
                await self._stop_all_tasks()
                logger.info("All search tasks stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping search tasks: {e}", exc_info=True)

            self._tasks.clear()

    async def start_searching(self, event: StartSearchingEvent):
        """Start all search tasks. Handles individual task failures gracefully."""
        async with self._lock:
            if self._is_running:
                logger.debug("Search monitoring already running")
                return

            if not self._tasks:
                logger.warning("No search tasks to start")
                return

            logger.info(f"Starting {len(self._tasks)} search tasks")
            start_tasks = [task.start() for task in self._tasks]
            results = await asyncio.gather(*start_tasks, return_exceptions=True)

            # Log any failures
            failed_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_count += 1
                    logger.error(
                        f"Failed to start search task {i}: {result}", exc_info=result
                    )

            if failed_count > 0:
                logger.warning(
                    f"Started {len(self._tasks) - failed_count}/{len(self._tasks)} "
                    f"search tasks successfully"
                )
            else:
                logger.info(f"All {len(self._tasks)} search tasks started successfully")

            self._is_running = True

    async def stop_searching(self, event: StopSearchingEvent):
        """Stop all search tasks. Handles individual task failures gracefully."""
        async with self._lock:
            logger.info("Stopping search monitoring")
            try:
                await self._stop_all_tasks()
            except Exception as e:
                logger.error(f"Error stopping search tasks: {e}", exc_info=True)

    async def add_search(self, event: NewSearchEvent):
        """Add new search task. Starts it if monitoring is active."""
        async with self._lock:
            try:
                task = SearchTask(self._client, self._message_bus, event.search)
                self._tasks.append(task)
                logger.info(
                    f"Added search task: id={event.search.id}, query='{event.search.query}'"
                )

                if self._is_running:
                    await task.start()
                    logger.debug(f"Started new search task: id={event.search.id}")
            except Exception as e:
                logger.error(
                    f"Failed to add/start search task for id={event.search.id}: {e}",
                    exc_info=True,
                )

    async def remove_search(self, event: RemoveSearchEvent):
        """Remove search task and stop it if running."""
        async with self._lock:
            task = next(
                (t for t in self._tasks if t.search_id == event.search_id), None
            )
            if task is not None:
                try:
                    await task.stop()
                    self._tasks.remove(task)
                    logger.info(f"Removed search task: id={event.search_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to stop/remove search task id={event.search_id}: {e}",
                        exc_info=True,
                    )
                    # Still try to remove from list even if stop failed
                    try:
                        self._tasks.remove(task)
                    except ValueError:
                        pass
            else:
                logger.warning(
                    f"Search task not found for removal: id={event.search_id}"
                )

    async def update_search(self, event: UpdateSearchEvent):
        """Update search task with new parameters."""
        async with self._lock:
            task = next(
                (t for t in self._tasks if t.search_id == event.search_id), None
            )
            if task is not None:
                try:
                    search = await self._message_bus.query(
                        GetSearchByIdQuery(search_id=event.search_id)
                    )
                    if search:
                        await task.update_search(search)
                        logger.info(f"Updated search task: id={event.search_id}")
                    else:
                        logger.warning(
                            f"Search not found in database for update: id={event.search_id}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to update search task id={event.search_id}: {e}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"Search task not found for update: id={event.search_id}"
                )

    async def _stop_all_tasks(self):
        """Stop all search tasks. Handles individual task failures gracefully."""
        if not self._is_running:
            return

        if not self._tasks:
            self._is_running = False
            return

        logger.info(f"Stopping {len(self._tasks)} search tasks")
        stop_tasks = [task.stop() for task in self._tasks]
        results = await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Log any failures
        failed_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(
                    f"Failed to stop search task {i}: {result}", exc_info=result
                )

        if failed_count > 0:
            logger.warning(
                f"Stopped {len(self._tasks) - failed_count}/{len(self._tasks)} "
                f"search tasks successfully"
            )
        else:
            logger.info(f"All {len(self._tasks)} search tasks stopped successfully")

        self._is_running = False
