from dataclasses import dataclass
from src.message_bus.events.event import Event
from src.message_bus.commands.command import Command
from src.message_bus.queries.query import Query


@dataclass(frozen=True)
class MockEvent(Event):
    """Mock event for testing."""

    value: int = 0


@dataclass(frozen=True)
class MockCommand(Command):
    """Mock command for testing."""

    value: int = 0


@dataclass(frozen=True)
class MockQuery(Query):
    """Mock query for testing."""

    value: int = 0
