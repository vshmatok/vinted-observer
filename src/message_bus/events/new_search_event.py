from dataclasses import dataclass
from src.telegram_bot.models.search import Search
from src.message_bus.events.event import Event


@dataclass(frozen=True)
class NewSearchEvent(Event):
    search: Search
