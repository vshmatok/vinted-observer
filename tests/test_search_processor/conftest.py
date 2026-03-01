import pytest
from unittest.mock import AsyncMock, MagicMock

from src.search_processor.search_task import SearchTask
from src.search_processor.search_processor import SearchProcessor
from src.message_bus.message_bus import MessageBus
from src.vinted_network_client.utils.proxy_manager import ProxyManager
from src.vinted_network_client.vinted_network_client import VintedNetworkClient
from src.vinted_network_client.models.vinted_domain import VintedDomain
from src.telegram_bot.models.search import Search
from tests.test_search_processor.helpers import make_mock_task


@pytest.fixture
def mock_message_bus():
    bus = AsyncMock(spec=MessageBus)
    bus.query.return_value = []
    return bus


@pytest.fixture
def mock_vinted_client():
    client = AsyncMock(spec=VintedNetworkClient)
    client.search_items.return_value = []
    return client


@pytest.fixture
def sample_nike_search():
    return Search(
        id=1, chat_id="12345", query="nike shoes", price_min=10.0, price_max=100.0
    )


@pytest.fixture
def updated_search():
    return Search(id=2, chat_id="99999", query="adidas", price_min=5.0, price_max=50.0)


@pytest.fixture
async def search_task(mock_vinted_client, mock_message_bus, sample_nike_search):
    task = SearchTask(
        client=mock_vinted_client,
        message_bus=mock_message_bus,
        search=sample_nike_search,
        search_sleep_time=0,
    )
    yield task
    await task.stop()


@pytest.fixture
def mock_proxy_manager():
    pm = MagicMock(spec=ProxyManager)
    pm.proxies = []
    pm.healthy_proxies = []
    pm.failed_proxies = []
    return pm


@pytest.fixture
def mock_vinted_client_class(mocker, mock_vinted_client):
    """Patches VintedNetworkClient.create to return mock_vinted_client."""
    return mocker.patch.object(
        VintedNetworkClient,
        "create",
        new_callable=AsyncMock,
        return_value=mock_vinted_client,
    )


@pytest.fixture
async def search_processor(
    mock_message_bus, mock_proxy_manager, mock_vinted_client_class
):
    """SearchProcessor with mocked dependencies, setup and torn down."""
    processor = SearchProcessor(
        message_bus=mock_message_bus,
        user_agents=[{"ua": "TestAgent"}],
        proxy_manager=mock_proxy_manager,
        domain=VintedDomain.PL,
    )
    await processor.setup()
    yield processor
    await processor.close()


@pytest.fixture
def running_processor(search_processor):
    """Configure search_processor in running state with mock tasks."""

    def _configure(*task_ids):
        tasks = [make_mock_task(tid) for tid in task_ids]
        search_processor._tasks = tasks
        search_processor._is_running = True
        return tasks

    return _configure
