from dataclasses import dataclass
from src.message_bus.commands.command import Command


@dataclass(frozen=True)
class DeleteSearchCommand(Command):
    """Command to delete a search by its ID from the repository"""

    search_id: int
