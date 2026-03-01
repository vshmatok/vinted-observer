from dataclasses import dataclass
from src.message_bus.queries.query import Query


@dataclass(frozen=True)
class GetAllSearchesQuery(Query):
    """Query to retrieve all searches from the repository"""

    pass
