import pytest
from src.message_bus.message_bus import MessageBus
from tests.test_message_bus.models.message_bus_mocks import (
    MockCommand,
    MockEvent,
    MockQuery,
)


# ============================================================================
# Event Tests
# ============================================================================


async def test_register_and_publish_event(message_bus: MessageBus):
    """Test event registration and publishing."""

    handled_events = []

    async def event_handler(event: MockEvent):
        handled_events.append(event)

    message_bus.register_event(MockEvent, event_handler)
    test_event = MockEvent(value=1)

    await message_bus.publish(test_event)

    assert len(handled_events) == 1
    assert handled_events[0] == test_event
    assert handled_events[0].value == 1


async def test_register_already_registered_event(message_bus: MessageBus):
    """Test registering an already registered event raises error."""

    async def event_handler(event: MockEvent):
        pass

    message_bus.register_event(MockEvent, event_handler)
    with pytest.raises(
        ValueError, match=f"Event handler already registered for {MockEvent.__name__}"
    ):
        message_bus.register_event(MockEvent, event_handler)


async def test_publish_unregistered_event(message_bus: MessageBus):
    """Test publishing an unregistered event raises error."""

    test_event = MockEvent(value=1)
    with pytest.raises(
        ValueError, match=f"No event handler registered for {MockEvent.__name__}"
    ):
        await message_bus.publish(test_event)


async def test_publish_event_with_exception_does_not_propagate(message_bus: MessageBus):
    """Test event handler exceptions are caught and do not propagate to caller."""

    async def failing_handler(event: MockEvent):
        raise RuntimeError("Test exception in event handler")

    message_bus.register_event(MockEvent, failing_handler)
    test_event = MockEvent(value=1)

    # Should NOT raise exception - this is the key behavior
    await message_bus.publish(test_event)


async def test_event_handler_receives_correct_type(message_bus: MessageBus):
    """Verify event handler receives correct type instance."""

    received_type = None
    received_instance = None

    async def event_handler(event: MockEvent):
        nonlocal received_type, received_instance
        received_type = type(event)
        received_instance = event

    message_bus.register_event(MockEvent, event_handler)
    test_event = MockEvent(value=42)

    await message_bus.publish(test_event)

    assert received_type == MockEvent
    assert received_instance is test_event
    assert received_instance is not None and received_instance.value == 42


# ============================================================================
# Command Tests
# ============================================================================


async def test_register_and_execute_command(message_bus: MessageBus):
    """Test command registration and execution."""

    handled_commands = []

    async def command_handler(command: MockCommand):
        handled_commands.append(command)

    message_bus.register_command(MockCommand, command_handler)
    test_command = MockCommand(value=1)

    await message_bus.execute(test_command)

    assert len(handled_commands) == 1
    assert handled_commands[0] == test_command
    assert handled_commands[0].value == 1


async def test_register_and_execute_command_with_result(message_bus: MessageBus):
    """Test command registration and execution with result."""

    async def command_handler(command: MockCommand) -> int:
        return command.value * 2

    message_bus.register_command(MockCommand, command_handler)
    test_command = MockCommand(value=1)

    result = await message_bus.execute(test_command)

    assert isinstance(result, int)
    assert result == 2


async def test_register_and_execute_command_with_none_result(message_bus: MessageBus):
    """Test command registration and execution with None result."""

    async def command_handler(command: MockCommand) -> None:
        pass

    message_bus.register_command(MockCommand, command_handler)
    test_command = MockCommand(value=1)

    result = await message_bus.execute(test_command)

    assert result is None


async def test_register_already_registered_command(message_bus: MessageBus):
    """Test registering an already registered command raises error."""

    async def command_handler(command: MockCommand):
        pass

    message_bus.register_command(MockCommand, command_handler)
    with pytest.raises(
        ValueError,
        match=f"Command handler already registered for {MockCommand.__name__}",
    ):
        message_bus.register_command(MockCommand, command_handler)


async def test_execute_unregistered_command(message_bus: MessageBus):
    """Test executing an unregistered command raises error."""

    test_command = MockCommand(value=1)
    with pytest.raises(
        ValueError, match=f"No command handler registered for {MockCommand.__name__}"
    ):
        await message_bus.execute(test_command)


async def test_register_and_execute_command_with_exception(message_bus: MessageBus):
    """Test command handler exceptions propagate to caller."""

    async def command_handler(command: MockCommand):
        raise RuntimeError("Test exception")

    message_bus.register_command(MockCommand, command_handler)
    test_command = MockCommand(value=1)

    with pytest.raises(RuntimeError, match="Test exception"):
        await message_bus.execute(test_command)


async def test_command_handler_receives_correct_type(message_bus: MessageBus):
    """Verify command handler receives correct type instance."""

    received_type = None
    received_instance = None

    async def command_handler(command: MockCommand):
        nonlocal received_type, received_instance
        received_type = type(command)
        received_instance = command

    message_bus.register_command(MockCommand, command_handler)
    test_command = MockCommand(value=42)

    await message_bus.execute(test_command)

    assert received_type == MockCommand
    assert received_instance is test_command
    assert received_instance is not None and received_instance.value == 42


# ============================================================================
# Query Tests
# ============================================================================


async def test_register_and_query_query(message_bus: MessageBus):
    """Test query registration and execution."""

    handled_queries = []

    async def query_handler(query: MockQuery):
        handled_queries.append(query)

    message_bus.register_query(MockQuery, query_handler)
    test_query = MockQuery(value=1)

    await message_bus.query(test_query)

    assert len(handled_queries) == 1
    assert handled_queries[0] == test_query
    assert handled_queries[0].value == 1


async def test_register_and_query_query_with_result(message_bus: MessageBus):
    """Test query registration and execution with result."""

    async def query_handler(query: MockQuery) -> int:
        return query.value * 2

    message_bus.register_query(MockQuery, query_handler)
    test_query = MockQuery(value=1)

    result = await message_bus.query(test_query)

    assert isinstance(result, int)
    assert result == 2


async def test_register_and_query_query_with_none_result(message_bus: MessageBus):
    """Test query registration and execution with None result."""

    async def query_handler(query: MockQuery) -> None:
        pass

    message_bus.register_query(MockQuery, query_handler)
    test_query = MockQuery(value=1)

    result = await message_bus.query(test_query)

    assert result is None


async def test_register_already_registered_query(message_bus: MessageBus):
    """Test registering an already registered query raises error."""

    async def query_handler(query: MockQuery):
        pass

    message_bus.register_query(MockQuery, query_handler)
    with pytest.raises(
        ValueError,
        match=f"Query handler already registered for {MockQuery.__name__}",
    ):
        message_bus.register_query(MockQuery, query_handler)


async def test_query_unregistered_query(message_bus: MessageBus):
    """Test executing an unregistered query raises error."""

    test_query = MockQuery(value=1)
    with pytest.raises(
        ValueError, match=f"No query handler registered for {MockQuery.__name__}"
    ):
        await message_bus.query(test_query)


async def test_register_and_query_with_exception(message_bus: MessageBus):
    """Test query handler exceptions propagate to caller."""

    async def query_handler(query: MockQuery):
        raise RuntimeError("Test exception")

    message_bus.register_query(MockQuery, query_handler)
    test_query = MockQuery(value=1)

    with pytest.raises(RuntimeError, match="Test exception"):
        await message_bus.query(test_query)


async def test_query_handler_receives_correct_type(message_bus: MessageBus):
    """Verify query handler receives correct type instance."""

    received_type = None
    received_instance = None

    async def query_handler(query: MockQuery):
        nonlocal received_type, received_instance
        received_type = type(query)
        received_instance = query

    message_bus.register_query(MockQuery, query_handler)
    test_query = MockQuery(value=42)

    await message_bus.query(test_query)

    assert received_type == MockQuery
    assert received_instance is test_query
    assert received_instance is not None and received_instance.value == 42
