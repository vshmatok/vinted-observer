from dataclasses import dataclass
from src.vinted_network_client.models.vinted_item import VintedItem
from src.message_bus.events.event import Event

@dataclass(frozen=True)
class ItemFoundEvent(Event):
    chat_id: int | str
    item: VintedItem
