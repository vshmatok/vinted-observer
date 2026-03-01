from typing import Protocol
from src.message_bus.utility.types import TEvent, TCommand, TQuery, TResult

# Protocols for type-safe handlers


class EventHandler(Protocol[TEvent]):
    """Protocol for event handlers - must accept event and return None"""

    async def __call__(self, event: TEvent) -> None: ...


class CommandHandler(Protocol[TCommand, TResult]):
    """Protocol for command handlers - must accept command and return result"""

    async def __call__(self, command: TCommand) -> TResult: ...


class QueryHandler(Protocol[TQuery, TResult]):
    """Protocol for query handlers - must accept query and return result"""

    async def __call__(self, query: TQuery) -> TResult: ...
