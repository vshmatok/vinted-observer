import pytest
from unittest.mock import AsyncMock, MagicMock

from src.vinted_network_client.models.vinted_proxy import VintedProxy
from src.vinted_network_client.models.vinted_domain import VintedDomain
from src.vinted_network_client.utils.proxy_manager import ProxyManager
from src.vinted_network_client.vinted_network_client import VintedNetworkClient


@pytest.fixture
def sample_proxy_https():
    return VintedProxy(
        ip="1.2.3.4",
        port="8080",
        username="user",
        password="pass",
        is_https=True,
    )


@pytest.fixture
def sample_proxy_http():
    return VintedProxy(
        ip="5.6.7.8",
        port="3128",
        username=None,
        password=None,
        is_https=False,
    )


@pytest.fixture
def sample_proxy_list(sample_proxy_https, sample_proxy_http):
    return [sample_proxy_https, sample_proxy_http]


@pytest.fixture
def proxy_manager(sample_proxy_list):
    return ProxyManager(sample_proxy_list)


@pytest.fixture
def sample_user_agents():
    return [
        {"ua": "Mozilla/5.0 Chrome"},
        {"ua": "Mozilla/5.0 Safari"},
        {"ua": "Mozilla/5.0 Firefox"},
    ]


@pytest.fixture
def ready_client(sample_user_agents):
    """VintedNetworkClient with session, user_agents, cookie pre-set (bypasses create())."""
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=sample_user_agents)
    session = MagicMock()
    session.close = AsyncMock()
    session.get = MagicMock()  # sync call returning async ctx manager
    client.session = session
    client.selected_user_agent = sample_user_agents[0]["ua"]
    client.session_cookie = "test_cookie_value"
    return client


@pytest.fixture
def ready_client_with_proxy(ready_client, proxy_manager, sample_proxy_https):
    """Ready client with proxy_manager and selected_proxy set."""
    ready_client.proxy_manager = proxy_manager
    ready_client.selected_proxy = sample_proxy_https
    return ready_client


@pytest.fixture
def proxy_a():
    return VintedProxy(
        ip="1.1.1.1", port="8080", username=None, password=None, is_https=True
    )


@pytest.fixture
def proxy_b():
    return VintedProxy(
        ip="2.2.2.2", port="8080", username=None, password=None, is_https=True
    )


@pytest.fixture
def manager(proxy_a, proxy_b):
    return ProxyManager([proxy_a, proxy_b])
