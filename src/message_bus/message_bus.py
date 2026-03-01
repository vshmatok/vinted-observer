import logging
from typing import Any
from src.message_bus.events.event import Event
from src.message_bus.commands.command import Command
from src.message_bus.queries.query import Query
from src.message_bus.utility.handlers import EventHandler, CommandHandler, QueryHandler
from src.message_bus.utility.types import TEvent, TCommand, TQuery, TResult

logger = logging.getLogger(__name__)


class MessageBus:
    """
    Message bus for CQRS pattern with type-safe handlers.

    - Events: Fire-and-forget notifications (errors logged, not propagated)
    - Commands: Write operations (errors propagate to caller)
    - Queries: Read operations (errors propagate to caller)
    """

    def __init__(self):
        self._event_handlers: dict[type[Event], EventHandler[Any]] = {}
        self._command_handlers: dict[type[Command], CommandHandler[Any, Any]] = {}
        self._query_handlers: dict[type[Query], QueryHandler[Any, Any]] = {}

    # Events

    def register_event(self, event_type: type[TEvent], handler: EventHandler[TEvent]):
        """
        Register handler for event type.
        Events are fire-and-forget - handler errors are logged but not propagated.
        """

        if event_type in self._event_handlers:
            raise ValueError(
                f"Event handler already registered for {event_type.__name__}"
            )
        self._event_handlers[event_type] = handler

    async def publish(self, event: Event):
        """
        Publish event to registered handler.
        Errors are caught and logged - caller is not notified of failures.
        """

        handler = self._event_handlers.get(type(event))
        if handler is None:
            raise ValueError(f"No event handler registered for {type(event).__name__}")

        try:
            await handler(event)
        except Exception as e:
            logger.error(
                "Error in event handler %s for event %s: %s",
                handler,
                event,
                e,
                exc_info=True,
            )

    # Commands

    def register_command(
        self,
        command_type: type[TCommand],
        handler: CommandHandler[TCommand, TResult],
    ):
        """
        Register handler for command type.

        Commands are write operations - handler errors propagate to caller.
        """

        if command_type in self._command_handlers:
            raise ValueError(
                f"Command handler already registered for {command_type.__name__}"
            )
        self._command_handlers[command_type] = handler

    async def execute(self, command: Command) -> Any:
        """
        Execute command and return result.

        Errors propagate to caller for handling.
        """
        handler = self._command_handlers.get(type(command))
        if handler is None:
            raise ValueError(
                f"No command handler registered for {type(command).__name__}"
            )
        return await handler(command)

    # Queries

    def register_query(
        self, query_type: type[TQuery], handler: QueryHandler[TQuery, TResult]
    ):
        """
        Register handler for query type.

        Queries are read operations - handler errors propagate to caller.
        """

        if query_type in self._query_handlers:
            raise ValueError(
                f"Query handler already registered for {query_type.__name__}"
            )
        self._query_handlers[query_type] = handler

    async def query(self, query: Query) -> Any:
        """
        Execute query and return result.

        Errors propagate to caller for handling.
        """

        handler = self._query_handlers.get(type(query))
        if handler is None:
            raise ValueError(f"No query handler registered for {type(query).__name__}")
        return await handler(query)
