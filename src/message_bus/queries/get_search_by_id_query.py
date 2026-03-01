from dataclasses import dataclass
from src.message_bus.queries.query import Query


@dataclass(frozen=True)
class GetSearchByIdQuery(Query):
    """Query to retrieve a search by its ID from the repository"""

    search_id: int
