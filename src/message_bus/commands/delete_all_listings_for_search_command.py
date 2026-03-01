from dataclasses import dataclass
from src.message_bus.commands.command import Command

@dataclass(frozen=True)
class DeleteAllListingsForSearchCommand(Command):
    """Command to delete all listings for a search in the repository"""

    search_id: int