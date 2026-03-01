import pytest
from src.message_bus.message_bus import MessageBus


@pytest.fixture
def message_bus():
    """Create message bus instance."""
    return MessageBus()
