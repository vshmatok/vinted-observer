import asyncio
import logging

from src.config import Config
from src.vinted_network_client.vinted_network_client import VintedNetworkClient
from src.telegram_bot.models.search import Search
from src.message_bus.message_bus import MessageBus
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

logger = logging.getLogger(__name__)


class SearchTask:

    def __init__(
        self,
        client: VintedNetworkClient,
        message_bus: MessageBus,
        search: Search,
        search_sleep_time: int = Config.SEARCH_SLEEP_TIME,
    ):
        self._client = client
        self._search = search
        self._task = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._message_bus = message_bus
        self._search_sleep_time = search_sleep_time

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def search_id(self) -> int:
        return self._search.id

    async def start(self):
        if self.is_running:
            return

        self._pause_event.set()
        self._task = asyncio.create_task(
            self._run_loop(), name=f"worker_task_{id(self)}"
        )

    async def stop(self):
        if not self.is_running:
            return

        if not self._task:
            return

        self._task.cancel()

        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def update_search(self, search: Search):
        """Update search parameters. Raises on failure."""
        was_running = self.is_running

        await self.stop()

        self._search = search

        try:
            await self._message_bus.execute(
                DeleteAllListingsForSearchCommand(search_id=search.id)
            )
        except Exception as e:
            logger.error(
                f"Failed to delete old listings for search_id={search.id}: {e}",
                exc_info=True,
            )

        if was_running:
            await self.start()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    async def _run_loop(self):
        """Main worker loop - runs until cancelled."""

        while True:
            try:
                await self._pause_event.wait()
                await self._execute_iteration()
                logger.debug(
                    "Starting sleep between iterations for search_id=%s",
                    self._search.id,
                )
                await asyncio.sleep(self._search_sleep_time)
                logger.debug(
                    "SearchTask for search_id=%s completed iteration", self._search.id
                )
            except asyncio.CancelledError:
                logger.debug("Search task worker cancelled")
                raise

            except Exception as e:
                logger.error("Search task worker error: %s", e, exc_info=True)

    async def _execute_iteration(self):
        """Single search iteration."""

        items = await self._client.search_items(
            self._search.query,
            per_page=20,
            price_from=self._search.price_min,
            price_to=self._search.price_max,
        )
        total_count = await self._message_bus.query(
            GetTotalListingCountForSearchQuery(search_id=self._search.id)
        )
        listing_ids = [item.id for item in items if item.id is not None]
        filtered_item_ids = await self._message_bus.query(
            FilterNewListingsQuery(search_id=self._search.id, listing_ids=listing_ids)
        )
        filtered_items = [item for item in items if item.id in filtered_item_ids]

        # If total_count is zero, it means this is the first run - add items silently
        is_first_run = total_count == 0
        await self._message_bus.execute(
            AddListingsForSearchCommand(
                search_id=self._search.id,
                listing_ids=filtered_item_ids,
                silent=is_first_run,
            )
        )

        # Do not send notifications on first run
        if not is_first_run:
            for item in filtered_items:
                await self._message_bus.publish(
                    ItemFoundEvent(chat_id=self._search.chat_id, item=item)
                )
