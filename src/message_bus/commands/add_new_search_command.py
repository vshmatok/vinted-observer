from dataclasses import dataclass
from src.message_bus.commands.command import Command


@dataclass(frozen=True)
class AddNewSearchCommand(Command):
    """Command to add a new search to the repository"""

    chat_id: int | str
    query: str
    price_min: float
    price_max: float
