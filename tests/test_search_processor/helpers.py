from unittest.mock import AsyncMock, MagicMock, PropertyMock

from src.search_processor.search_task import SearchTask
from src.message_bus.queries.filter_new_listings_query import FilterNewListingsQuery
from src.message_bus.queries.get_total_listing_count_for_search_query import (
    GetTotalListingCountForSearchQuery,
)


def make_mock_task(search_id, is_running=False):
    """Create a MagicMock SearchTask with search_id property and async methods."""
    task = MagicMock(spec=SearchTask)
    type(task).search_id = PropertyMock(return_value=search_id)
    type(task).is_running = PropertyMock(return_value=is_running)
    task.start = AsyncMock()
    task.stop = AsyncMock()
    task.update_search = AsyncMock()
    return task


def make_item(item_id):
    """Helper to create a MagicMock VintedItem with the given id."""
    item = MagicMock()
    item.id = item_id
    return item


def make_query_side_effect(total_count=0, filtered_ids=None):
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
