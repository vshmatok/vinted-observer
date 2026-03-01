from dataclasses import dataclass
from src.message_bus.queries.query import Query


@dataclass(frozen=True)
class FilterNewListingsQuery(Query):
    """Query to filter new listings for a search in the repository"""

    search_id: int
    listing_ids: list[int]
