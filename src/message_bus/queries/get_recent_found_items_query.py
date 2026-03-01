from dataclasses import dataclass
from src.message_bus.queries.query import Query


@dataclass(frozen=True)
class GetRecentFoundItemsQuery(Query):
    """Query to retrieve items found within a specific timeframe"""

    hours: int
