from dataclasses import dataclass
from src.message_bus.queries.query import Query


@dataclass(frozen=True)
class GetStatusReportQuery(Query):
    """Query to retrieve the current bot status report"""

    pass
