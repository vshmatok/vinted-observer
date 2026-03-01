from dataclasses import dataclass
from src.message_bus.queries.query import Query


@dataclass(frozen=True)
class GetTotalListingCountForSearchQuery(Query):
    """Query to get the total count of listings in the repository"""

    search_id: int
