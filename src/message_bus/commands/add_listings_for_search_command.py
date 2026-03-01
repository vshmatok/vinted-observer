from dataclasses import dataclass
from src.message_bus.commands.command import Command

@dataclass(frozen=True)
class AddListingsForSearchCommand(Command):
    """Command to add listings to a search in the repository"""

    search_id: int
    listing_ids: list[int]
    silent: bool = False
