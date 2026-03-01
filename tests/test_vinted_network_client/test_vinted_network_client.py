import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from src.vinted_network_client.vinted_network_client import VintedNetworkClient
from src.vinted_network_client.models.vinted_domain import VintedDomain
from src.vinted_network_client.models.vinted_item import VintedItem
from src.vinted_network_client.exceptions.vinted_cookie_request_error import (
    VintedCookieRequestError,
)
from src.vinted_network_client.exceptions.vinted_search_request_error import (
    VintedSearchRequestError,
)
from src.vinted_network_client.exceptions.vinted_setup_error import VintedSetupError
from src.vinted_network_client.exceptions.vinted_validation_error import (
    VintedValidationError,
)
from src.vinted_network_client.utils.constants import (
    SESSION_COOKIE_NAME,
    TIMEOUT_SECONDS,
)
from src.vinted_network_client.utils.middlewares import logging_middleware

from tests.test_vinted_network_client.conftest import (
    make_item_json,
    make_search_response,
    make_response_ctx,
)


def _make_mock_session(get_return=None, get_side_effect=None):
    """Helper to create a properly mocked aiohttp session."""
    session = MagicMock()
    session.close = AsyncMock()
    if get_side_effect is not None:
        session.get = MagicMock(side_effect=get_side_effect)
    elif get_return is not None:
        session.get = MagicMock(return_value=get_return)
    else:
        session.get = MagicMock()
    return session


def _cookie_ctx(cookie_value="test_cookie"):
    """Make a 200 response ctx with a session cookie."""
    cookie_mock = MagicMock()
    cookie_mock.value = cookie_value
    return make_response_ctx(200, cookies={SESSION_COOKIE_NAME: cookie_mock})


# ============================================================================
# __init__
# ============================================================================


def test_init_session_is_none():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=[])
    assert client.session is None


def test_init_base_url_pl():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=[])
    assert client.base_url == "https://www.vinted.pl"


def test_init_base_url_co_uk():
    client = VintedNetworkClient(domain=VintedDomain.CO_UK, user_agents=[])
    assert client.base_url == "https://www.vinted.co.uk"


def test_init_user_agents_stored(sample_user_agents):
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=sample_user_agents)
    assert client.user_agents is sample_user_agents


def test_init_proxy_manager_stored(proxy_manager):
    client = VintedNetworkClient(
        domain=VintedDomain.PL, user_agents=[], proxy_manager=proxy_manager
    )
    assert client.proxy_manager is proxy_manager


def test_init_selected_proxy_is_none():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=[])
    assert client.selected_proxy is None


# ============================================================================
# create()
# ============================================================================


@patch("src.vinted_network_client.vinted_network_client.aiohttp.ClientSession")
async def test_create_returns_client_with_session(mock_session_cls):
    mock_session_cls.return_value = _make_mock_session(get_return=_cookie_ctx())

    client = await VintedNetworkClient.create(VintedDomain.PL, [{"ua": "Mozilla/5.0"}])
    assert client.session is not None
    await client.close()


@patch("src.vinted_network_client.vinted_network_client.aiohttp.ClientSession")
async def test_create_configures_session_timeout_and_middleware(mock_session_cls):
    mock_session_cls.return_value = _make_mock_session(get_return=_cookie_ctx())

    client = await VintedNetworkClient.create(VintedDomain.PL, [{"ua": "Agent1"}])

    call_kwargs = mock_session_cls.call_args[1]
    assert call_kwargs["timeout"].total == TIMEOUT_SECONDS
    assert len(call_kwargs["middlewares"]) == 1
    assert call_kwargs["middlewares"][0] is logging_middleware
    await client.close()


@patch("src.vinted_network_client.vinted_network_client.aiohttp.ClientSession")
async def test_create_stores_user_agents(mock_session_cls):
    agents = [{"ua": "Agent1"}, {"ua": "Agent2"}]
    mock_session_cls.return_value = _make_mock_session(get_return=_cookie_ctx())

    client = await VintedNetworkClient.create(VintedDomain.PL, agents)
    assert client.user_agents is agents
    await client.close()


@patch("src.vinted_network_client.vinted_network_client.aiohttp.ClientSession")
async def test_create_gets_proxy_when_proxy_manager(mock_session_cls, proxy_manager):
    mock_session_cls.return_value = _make_mock_session(get_return=_cookie_ctx())

    client = await VintedNetworkClient.create(
        VintedDomain.PL, [{"ua": "Agent1"}], proxy_manager=proxy_manager
    )
    assert client.selected_proxy is not None
    await client.close()


@patch("src.vinted_network_client.vinted_network_client.aiohttp.ClientSession")
async def test_create_no_proxy_when_no_manager(mock_session_cls):
    mock_session_cls.return_value = _make_mock_session(get_return=_cookie_ctx())

    client = await VintedNetworkClient.create(VintedDomain.PL, [{"ua": "Agent1"}])
    assert client.proxy_manager is None
    await client.close()


@patch("src.vinted_network_client.vinted_network_client.aiohttp.ClientSession")
async def test_create_sets_selected_user_agent_and_cookie(mock_session_cls):
    mock_session_cls.return_value = _make_mock_session(
        get_return=_cookie_ctx("cookie_val")
    )

    client = await VintedNetworkClient.create(VintedDomain.PL, [{"ua": "Agent1"}])
    assert client.selected_user_agent is not None
    assert client.session_cookie == "cookie_val"
    await client.close()


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
@patch("src.vinted_network_client.vinted_network_client.aiohttp.ClientSession")
async def test_create_wraps_setup_failure_in_setup_error(mock_session_cls, _mock_sleep):
    mock_session = _make_mock_session()
    mock_session.get.return_value = make_response_ctx(status=500)
    mock_session_cls.return_value = mock_session

    with pytest.raises(VintedSetupError) as exc_info:
        await VintedNetworkClient.create(VintedDomain.PL, [{"ua": "Agent1"}])

    assert exc_info.value.underlying_error is not None
    mock_session.close.assert_awaited_once()


# ============================================================================
# close()
# ============================================================================


async def test_close_calls_session_close(ready_client):
    await ready_client.close()
    ready_client.session.close.assert_awaited_once()


async def test_close_noop_when_session_none():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=[])
    await client.close()
    assert client.session is None


# ============================================================================
# search_items - validation
# ============================================================================


async def test_search_raises_when_session_none(sample_user_agents):
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=sample_user_agents)
    client.session_cookie = "cookie"
    with pytest.raises(VintedValidationError):
        await client.search_items("test")


async def test_search_raises_when_user_agents_empty():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=[])
    client.session = MagicMock()
    client.session_cookie = "cookie"
    with pytest.raises(VintedValidationError):
        await client.search_items("test")


async def test_search_raises_when_session_cookie_none(sample_user_agents):
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=sample_user_agents)
    client.session = MagicMock()
    with pytest.raises(VintedValidationError):
        await client.search_items("test")


# ============================================================================
# search_items - successful request (200)
# ============================================================================


async def test_search_returns_list_of_vinted_items(ready_client):
    items_json = [make_item_json(id=1), make_item_json(id=2)]
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response(items_json)
    )
    result = await ready_client.search_items("nike")
    assert len(result) == 2
    assert all(isinstance(i, VintedItem) for i in result)


async def test_search_correct_url(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike")
    call_args = ready_client.session.get.call_args
    assert "api/v2/catalog/items" in call_args[0][0]


async def test_search_correct_headers(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike")
    call_args = ready_client.session.get.call_args
    headers = call_args[1]["headers"]
    assert headers["User-Agent"] == ready_client.selected_user_agent
    assert SESSION_COOKIE_NAME in headers["Cookie"]
    assert headers["Origin"] == ready_client.base_url
    assert headers["Referer"] == ready_client.base_url


async def test_search_correct_params(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike", page=2, per_page=50)
    call_args = ready_client.session.get.call_args
    params = call_args[1]["params"]
    assert params["page"] == 2
    assert params["per_page"] == 50
    assert params["search_text"] == "nike"
    assert params["order"] == "newest_first"


async def test_search_excludes_none_price_params(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike")
    params = ready_client.session.get.call_args[1]["params"]
    assert "price_from" not in params
    assert "price_to" not in params


async def test_search_includes_price_params_when_set(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike", price_from=10.0, price_to=50.0)
    params = ready_client.session.get.call_args[1]["params"]
    assert params["price_from"] == 10.0
    assert params["price_to"] == 50.0


async def test_search_marks_proxy_success_and_rotates(ready_client_with_proxy):
    client = ready_client_with_proxy
    pm = client.proxy_manager
    initial_proxy = client.selected_proxy
    client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await client.search_items("nike")
    assert initial_proxy not in pm.failed_proxies
    assert client.selected_proxy is not None


async def test_search_no_proxy_ops_without_manager(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike")
    assert ready_client.proxy_manager is None
    assert ready_client.selected_proxy is None


async def test_search_passes_proxy_string_to_session_get(ready_client_with_proxy):
    client = ready_client_with_proxy
    expected_proxy = client.selected_proxy.to_str_proxy()
    client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await client.search_items("nike")
    call_args = client.session.get.call_args
    assert call_args[1]["proxy"] == expected_proxy


async def test_search_proxy_none_when_no_proxy(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike")
    call_args = ready_client.session.get.call_args
    assert call_args[1]["proxy"] is None


async def test_search_empty_items_returns_empty_list(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    result = await ready_client.search_items("nike")
    assert result == []


# ============================================================================
# search_items - malformed response
# ============================================================================


async def test_search_missing_items_key_raises(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data={"no_items_key": []}
    )
    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert isinstance(exc_info.value.underlying_error, KeyError)


async def test_search_none_items_raises(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data={"items": None}
    )
    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert isinstance(exc_info.value.underlying_error, TypeError)


# ============================================================================
# search_items - retry logic 401/429
# ============================================================================


@pytest.mark.parametrize("status", [401, 429])
@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_search_retries_on_retry_status(mock_sleep, status, ready_client):
    ready_client.session.get.side_effect = [
        make_response_ctx(status),
        make_response_ctx(200, json_data=make_search_response([])),
    ]
    ready_client._update_request_settings = AsyncMock()

    result = await ready_client.search_items("nike")
    assert result == []
    assert ready_client.session.get.call_count == 2


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_search_exponential_backoff(mock_sleep, ready_client):
    ready_client.session.get.side_effect = [
        make_response_ctx(401),
        make_response_ctx(401),
        make_response_ctx(200, json_data=make_search_response([])),
    ]
    ready_client._update_request_settings = AsyncMock()

    await ready_client.search_items("nike")
    assert mock_sleep.call_args_list[0][0][0] == 1  # 2^0
    assert mock_sleep.call_args_list[1][0][0] == 2  # 2^1


@pytest.mark.parametrize("status", [401, 429])
@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_search_marks_proxy_failure_and_rotates(
    mock_sleep, status, ready_client_with_proxy
):
    client = ready_client_with_proxy
    initial_proxy = client.selected_proxy
    client.session.get.side_effect = [
        make_response_ctx(status),
        make_response_ctx(200, json_data=make_search_response([])),
    ]
    client._update_request_settings = AsyncMock()

    await client.search_items("nike")
    assert initial_proxy in client.proxy_manager.failed_proxies


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_search_calls_update_request_settings_on_retry(mock_sleep, ready_client):
    ready_client.session.get.side_effect = [
        make_response_ctx(401),
        make_response_ctx(200, json_data=make_search_response([])),
    ]
    ready_client._update_request_settings = AsyncMock()

    await ready_client.search_items("nike")
    ready_client._update_request_settings.assert_awaited_once()


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_search_raises_after_max_retries(mock_sleep, ready_client):
    ready_client.session.get.return_value = make_response_ctx(401)
    ready_client._update_request_settings = AsyncMock()

    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert "401" in exc_info.value.message


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_search_error_message_contains_endpoint_and_status(
    mock_sleep, ready_client
):
    ready_client.session.get.return_value = make_response_ctx(429)
    ready_client._update_request_settings = AsyncMock()

    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert "429" in exc_info.value.message
    assert (
        "endpoint" in exc_info.value.message.lower()
        or "SEARCH" in exc_info.value.message
    )


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_search_no_proxy_ops_on_retry_without_manager(mock_sleep, ready_client):
    ready_client.session.get.side_effect = [
        make_response_ctx(401),
        make_response_ctx(200, json_data=make_search_response([])),
    ]
    ready_client._update_request_settings = AsyncMock()
    await ready_client.search_items("nike")
    assert ready_client.proxy_manager is None
    assert ready_client.selected_proxy is None


# ============================================================================
# search_items - non-retryable status
# ============================================================================


@pytest.mark.parametrize("status", [403, 500])
async def test_search_raises_immediately_on_non_retryable(status, ready_client):
    ready_client.session.get.return_value = make_response_ctx(status)

    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert str(status) in exc_info.value.message


@pytest.mark.parametrize("status", [403, 500])
async def test_search_no_retry_on_non_retryable(status, ready_client):
    ready_client.session.get.return_value = make_response_ctx(status)

    with pytest.raises(VintedSearchRequestError):
        await ready_client.search_items("nike")
    assert ready_client.session.get.call_count == 1


# ============================================================================
# search_items - generic exception
# ============================================================================


async def test_search_network_error_wrapped(ready_client):
    ready_client.session.get.side_effect = aiohttp.ClientError("connection failed")

    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert isinstance(exc_info.value.underlying_error, aiohttp.ClientError)


async def test_search_underlying_error_preserved(ready_client):
    original = aiohttp.ClientError("timeout")
    ready_client.session.get.side_effect = original

    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert exc_info.value.underlying_error is original


async def test_search_error_not_double_wrapped(ready_client):
    original = VintedSearchRequestError(message="already wrapped")
    ready_client.session.get.side_effect = original

    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert exc_info.value is original


# ============================================================================
# _get_random_user_agent
# ============================================================================


def test_get_random_user_agent_returns_ua_string(ready_client):
    result = ready_client._get_random_user_agent()
    assert isinstance(result, str)
    assert "Mozilla" in result


def test_get_random_user_agent_raises_on_empty_list():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=[])
    with pytest.raises(VintedValidationError):
        client._get_random_user_agent()


def test_get_random_user_agent_raises_on_missing_ua_key():
    client = VintedNetworkClient(
        domain=VintedDomain.PL, user_agents=[{"not_ua": "value"}]
    )
    with pytest.raises(VintedValidationError):
        client._get_random_user_agent()


def test_get_random_user_agent_raises_on_non_dict_items():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=["not a dict"])  # type: ignore[misc]
    with pytest.raises(VintedValidationError):
        client._get_random_user_agent()


# ============================================================================
# _fetch_session_cookie
# ============================================================================


async def test_fetch_cookie_raises_when_session_none():
    client = VintedNetworkClient(domain=VintedDomain.PL, user_agents=[])
    with pytest.raises(VintedValidationError):
        await client._fetch_session_cookie()


async def test_fetch_cookie_returns_cookie_on_200(ready_client):
    ready_client.session.get.return_value = _cookie_ctx("test_cookie_123")

    result = await ready_client._fetch_session_cookie()
    assert result == "test_cookie_123"


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_fetch_cookie_retries_on_non_200_raises_after_all_retries(
    mock_sleep, ready_client
):
    ready_client.session.get.return_value = make_response_ctx(500)

    with pytest.raises(VintedCookieRequestError) as exc_info:
        await ready_client._fetch_session_cookie()
    assert "last_status" in exc_info.value.context


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_fetch_cookie_error_context_contains_last_status(
    mock_sleep, ready_client
):
    ready_client.session.get.return_value = make_response_ctx(503)

    with pytest.raises(VintedCookieRequestError) as exc_info:
        await ready_client._fetch_session_cookie()
    assert exc_info.value.context["last_status"] == 503


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_fetch_cookie_marks_proxy_failure_on_retry_status(
    mock_sleep, ready_client_with_proxy
):
    client = ready_client_with_proxy
    initial_proxy = client.selected_proxy
    client.session.get.return_value = make_response_ctx(429)

    with pytest.raises(VintedCookieRequestError):
        await client._fetch_session_cookie()
    assert initial_proxy in client.proxy_manager.failed_proxies


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_fetch_cookie_rotates_proxy_on_non_200(
    mock_sleep, ready_client_with_proxy
):
    client = ready_client_with_proxy
    client.session.get.side_effect = [
        make_response_ctx(500),
        _cookie_ctx("new_cookie"),
        _cookie_ctx("new_cookie"),
    ]

    result = await client._fetch_session_cookie()
    assert result == "new_cookie"


async def test_fetch_cookie_marks_proxy_success_on_200(ready_client_with_proxy):
    client = ready_client_with_proxy
    initial_proxy = client.selected_proxy
    client.session.get.return_value = _cookie_ctx("cookie")

    await client._fetch_session_cookie()
    assert initial_proxy not in client.proxy_manager.failed_proxies


async def test_fetch_cookie_continues_retry_when_cookie_missing(ready_client):
    ready_client.session.get.return_value = make_response_ctx(200, cookies={})

    with pytest.raises(VintedCookieRequestError):
        await ready_client._fetch_session_cookie()
    assert ready_client.session.get.call_count == 3  # REQUEST_RETRIES = 3


async def test_fetch_cookie_continues_retry_when_cookie_empty(ready_client):
    cookie_mock = MagicMock()
    cookie_mock.value = ""
    ready_client.session.get.return_value = make_response_ctx(
        200, cookies={SESSION_COOKIE_NAME: cookie_mock}
    )

    with pytest.raises(VintedCookieRequestError):
        await ready_client._fetch_session_cookie()


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_fetch_cookie_exponential_backoff_on_non_200(mock_sleep, ready_client):
    ready_client.session.get.return_value = make_response_ctx(500)

    with pytest.raises(VintedCookieRequestError):
        await ready_client._fetch_session_cookie()
    assert mock_sleep.call_args_list[0][0][0] == 1  # 2^0
    assert mock_sleep.call_args_list[1][0][0] == 2  # 2^1
    assert mock_sleep.call_args_list[2][0][0] == 4  # 2^2


async def test_fetch_cookie_uses_proxy_in_request(ready_client_with_proxy):
    client = ready_client_with_proxy
    expected_proxy = client.selected_proxy.to_str_proxy()
    client.session.get.return_value = _cookie_ctx("cookie")

    await client._fetch_session_cookie()
    call_args = client.session.get.call_args
    assert call_args[1]["proxy"] == expected_proxy


async def test_fetch_cookie_uses_home_endpoint(ready_client):
    ready_client.session.get.return_value = _cookie_ctx("cookie")

    await ready_client._fetch_session_cookie()
    url = ready_client.session.get.call_args[0][0]
    assert url.endswith("/")


async def test_fetch_cookie_sends_correct_headers(ready_client):
    ready_client.session.get.return_value = _cookie_ctx("cookie")

    await ready_client._fetch_session_cookie()
    headers = ready_client.session.get.call_args[1]["headers"]
    assert headers["User-Agent"] == ready_client.selected_user_agent
    assert headers["Origin"] == ready_client.base_url
    assert headers["Referer"] == ready_client.base_url


async def test_fetch_cookie_proxy_none_when_no_proxy(ready_client):
    ready_client.session.get.return_value = _cookie_ctx("cookie")

    await ready_client._fetch_session_cookie()
    call_args = ready_client.session.get.call_args
    assert call_args[1]["proxy"] is None


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_fetch_cookie_does_not_mark_failure_on_non_retry_status(
    mock_sleep, ready_client_with_proxy
):
    client = ready_client_with_proxy
    pm = client.proxy_manager
    initial_failed = len(pm.failed_proxies)

    client.session.get.side_effect = [
        make_response_ctx(500),
        _cookie_ctx("cookie"),
        _cookie_ctx("cookie"),
    ]

    await client._fetch_session_cookie()
    assert len(pm.failed_proxies) == initial_failed


# ============================================================================
# search_items - time parameter
# ============================================================================


async def test_search_includes_time_parameter(ready_client):
    ready_client.session.get.return_value = make_response_ctx(
        200, json_data=make_search_response([])
    )
    await ready_client.search_items("nike")
    params = ready_client.session.get.call_args[1]["params"]
    assert "time" in params
    assert isinstance(params["time"], float)


# ============================================================================
# _update_request_settings - direct tests
# ============================================================================


async def test_update_request_settings_updates_ua_and_cookie(ready_client):
    ready_client.selected_user_agent = None
    ready_client.session.get.return_value = _cookie_ctx("new_cookie")

    await ready_client._update_request_settings()
    assert ready_client.selected_user_agent in [
        ua["ua"] for ua in ready_client.user_agents
    ]
    assert ready_client.session_cookie == "new_cookie"


# ============================================================================
# _fetch_session_cookie - no sleep on 200 with missing cookie
# ============================================================================


@patch(
    "src.vinted_network_client.vinted_network_client.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_fetch_cookie_no_sleep_on_200_with_missing_cookie(
    mock_sleep, ready_client
):
    ready_client.session.get.return_value = make_response_ctx(200, cookies={})

    with pytest.raises(VintedCookieRequestError):
        await ready_client._fetch_session_cookie()
    mock_sleep.assert_not_called()


# ============================================================================
# _fetch_session_cookie - network exception during fetch
# ============================================================================


async def test_fetch_cookie_network_exception_propagates(ready_client):
    ready_client.session.get.side_effect = aiohttp.ClientError("connection reset")

    with pytest.raises(aiohttp.ClientError):
        await ready_client._fetch_session_cookie()


# ============================================================================
# search_items - json() raising exception
# ============================================================================


async def test_search_json_parse_error_wrapped(ready_client):
    ctx = make_response_ctx(200, json_data=make_search_response([]))
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(
        side_effect=aiohttp.ContentTypeError(
            MagicMock(), MagicMock(), message="invalid content type"
        )
    )
    response.cookies = {}
    ctx.__aenter__ = AsyncMock(return_value=response)
    ready_client.session.get.return_value = ctx

    with pytest.raises(VintedSearchRequestError) as exc_info:
        await ready_client.search_items("nike")
    assert isinstance(exc_info.value.underlying_error, aiohttp.ContentTypeError)
