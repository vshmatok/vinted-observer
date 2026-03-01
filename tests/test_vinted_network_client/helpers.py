from unittest.mock import AsyncMock, MagicMock

from src.vinted_network_client.models.vinted_proxy import VintedProxy
from src.vinted_network_client.models.vinted_proxy_stats import ProxyStats
from src.vinted_network_client.utils.constants import SESSION_COOKIE_NAME


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


def make_mock_session(get_return=None, get_side_effect=None):
    """Create a properly mocked aiohttp session."""
    session = MagicMock()
    session.close = AsyncMock()
    if get_side_effect is not None:
        session.get = MagicMock(side_effect=get_side_effect)
    elif get_return is not None:
        session.get = MagicMock(return_value=get_return)
    else:
        session.get = MagicMock()
    return session


def make_cookie_ctx(cookie_value="test_cookie"):
    """Make a 200 response ctx with a session cookie."""
    cookie_mock = MagicMock()
    cookie_mock.value = cookie_value
    return make_response_ctx(200, cookies={SESSION_COOKIE_NAME: cookie_mock})


def make_proxy_stats():
    """Create a ProxyStats with a default proxy."""
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
    )
    return ProxyStats(proxy=proxy)
