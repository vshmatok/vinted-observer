from dataclasses import dataclass
from typing import Optional
from src.message_bus.commands.command import Command


@dataclass(frozen=True)
class UpdateSearchCommand(Command):
    """Command to update a search in the repository"""

    search_id: int
    query: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
