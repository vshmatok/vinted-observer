from typing import TypeVar
from src.message_bus.events.event import Event
from src.message_bus.commands.command import Command
from src.message_bus.queries.query import Query

# Bounded TypeVars - constrained to base classes

TEvent = TypeVar("TEvent", bound=Event, contravariant=True)
TCommand = TypeVar("TCommand", bound=Command, contravariant=True)
TQuery = TypeVar("TQuery", bound=Query, contravariant=True)
TResult = TypeVar("TResult", covariant=True)
