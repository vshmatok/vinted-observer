from dataclasses import dataclass
from src.message_bus.events.event import Event


@dataclass(frozen=True)
class RemoveSearchEvent(Event):
    search_id: int
