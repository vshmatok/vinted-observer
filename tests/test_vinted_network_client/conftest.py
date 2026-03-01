import pytest
from unittest.mock import AsyncMock, MagicMock

from src.vinted_network_client.models.vinted_proxy import VintedProxy
from src.vinted_network_client.models.vinted_domain import VintedDomain
from src.vinted_network_client.utils.proxy_manager import ProxyManager
from src.vinted_network_client.vinted_network_client import VintedNetworkClient


# --- Proxy fixtures ---

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


# --- User agent fixtures ---

@pytest.fixture
def sample_user_agents():
    return [
        {"ua": "Mozilla/5.0 Chrome"},
        {"ua": "Mozilla/5.0 Safari"},
        {"ua": "Mozilla/5.0 Firefox"},
    ]


# --- Client fixtures ---

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


# --- Helpers ---

def make_item_json(**overrides):
    """Builds sample API item JSON dict with defaults."""
    base = {
        "id": 12345,
        "title": "Nike Air Max",
        "view_count": 42,
        "path": "/items/12345-nike-air-max",
        "url": "https://www.vinted.pl/items/12345-nike-air-max",
        "status": "active",
        "brand_title": "Nike",
        "size_title": "M",
        "user": {
            "id": 99,
            "login": "seller123",
            "profile_url": "https://www.vinted.pl/member/99-seller123",
        },
        "photo": {
            "id": 1,
            "image_no": 1,
            "is_main": True,
            "is_suspicious": False,
            "is_hidden": False,
            "full_size_url": "https://images.vinted.net/full/12345.jpg",
            "high_resolution": {
                "id": "hr_1",
                "timestamp": 1700000000,
            },
            "thumbnails": [
                {"type": "thumb", "url": "https://images.vinted.net/thumb/12345.jpg"},
            ],
        },
        "price": {"amount": "25.50", "currency_code": "PLN"},
        "total_item_price": {"amount": "30.00", "currency_code": "PLN"},
    }
    base.update(overrides)
    return base


def make_search_response(items):
    """Wraps items in {"items": [...]}."""
    return {"items": items}


def make_response_ctx(status=200, json_data=None, cookies=None):
    """Builds mock async context manager for session.get()."""
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data or {})
    response.cookies = cookies or {}
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx
