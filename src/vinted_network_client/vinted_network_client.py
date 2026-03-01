import asyncio
import aiohttp
import random
import time
import logging
from typing import List, Optional, Self

from src.vinted_network_client.models.vinted_item import VintedItem
from src.vinted_network_client.models.vinted_domain import VintedDomain
from src.vinted_network_client.models.vinted_endpoint import VintedEndpoint
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
    BASE_DOMAIN,
    REQUEST_RETRIES,
    RETRY_STATUS_CODES,
)
from src.vinted_network_client.utils.middlewares import logging_middleware
from src.vinted_network_client.utils.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)


class VintedNetworkClient:
    """Client for interacting with Vinted's network API."""

    def __init__(
        self,
        domain: VintedDomain,
        user_agents: List[dict],
        proxy_manager: Optional[ProxyManager] = None,
    ):
        """Initialize client. Use VintedNetworkClient.create() to also set up the session."""
        self.session = None
        self.base_url = f"{BASE_DOMAIN}.{domain.value}"
        self.user_agents = user_agents
        self.selected_user_agent = None
        self.session_cookie = None
        self.proxy_manager = proxy_manager
        self.selected_proxy = None

    @classmethod
    async def create(
        cls,
        domain: VintedDomain,
        user_agents: List[dict],
        proxy_manager: Optional[ProxyManager] = None,
    ) -> Self:
        client = cls(domain, user_agents, proxy_manager)
        await client._setup()
        return client

    async def close(self):
        if self.session:
            await self.session.close()

    async def search_items(
        self,
        query: str,
        page: int = 1,
        per_page: int = 96,
        price_from: Optional[float] = None,
        price_to: Optional[float] = None,
        _retry_count: int = 0,
    ) -> List[VintedItem]:
        if not self.session:
            raise VintedValidationError(
                message="HTTP session not initialized. Call setup() first.",
                context={"operation": "search_items"},
            )
        if not self.user_agents or not self.session_cookie:
            raise VintedValidationError(
                message="User agents not loaded. Call setup() first.",
                context={"operation": "search_items"},
            )

        endpoint = VintedEndpoint.SEARCH
        headers = {
            "User-Agent": self.selected_user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, zstd",  # br is causing issues with aiohttp
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",  # Do Not Track
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Origin": self.base_url,
            "Referer": self.base_url,
            "Cookie": f"{SESSION_COOKIE_NAME}={self.session_cookie}",
        }
        params = {
            "page": page,
            "per_page": per_page,
            "time": time.time(),
            "search_text": query,
            "price_from": price_from,
            "price_to": price_to,
            "order": "newest_first",
        }
        params = {k: v for k, v in params.items() if v is not None}

        try:
            async with self.session.get(
                f"{self.base_url}/{endpoint.value}",
                headers=headers,
                params=params,
                proxy=(
                    self.selected_proxy.to_str_proxy() if self.selected_proxy else None
                ),
            ) as response:
                if response.status == 200:
                    if self.proxy_manager and self.selected_proxy:
                        await self.proxy_manager.mark_success(self.selected_proxy)
                        self.selected_proxy = await self.proxy_manager.get_proxy()

                    try:
                        response_data = await response.json()
                        items = [VintedItem(item) for item in response_data["items"]]

                        logger.info(f"Successfully retrieved {len(items)} items")

                        return items
                    except (KeyError, TypeError) as e:
                        raise VintedSearchRequestError(
                            message="Invalid response format from Vinted API",
                            underlying_error=e,
                        ) from e
                elif response.status in RETRY_STATUS_CODES:
                    if _retry_count >= REQUEST_RETRIES:
                        raise VintedSearchRequestError(
                            message=f"Cannot perform API call to endpoint {endpoint}, "
                            f"error code: {response.status}"
                        )

                    sleep_time = 2**_retry_count
                    logger.info(f"Sleeping for {sleep_time} seconds before retrying...")
                    await asyncio.sleep(sleep_time)

                    logger.info(
                        "Refreshing session cookie, user agent, and proxy and retrying..."
                    )
                    if self.proxy_manager and self.selected_proxy:
                        await self.proxy_manager.mark_failure(self.selected_proxy)
                        self.selected_proxy = await self.proxy_manager.get_proxy()

                    await self._update_request_settings()

                    return await self.search_items(
                        query,
                        page,
                        per_page,
                        price_from,
                        price_to,
                        _retry_count=_retry_count + 1,
                    )
                else:
                    raise VintedSearchRequestError(
                        message=f"Cannot perform API call to endpoint {endpoint}, "
                        f"error code: {response.status}"
                    )
        except VintedSearchRequestError:
            raise
        except Exception as e:
            raise VintedSearchRequestError(
                message="Network error during search_items API call.",
                underlying_error=e,
            ) from e

    async def _setup(self):
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
                middlewares=[logging_middleware],
            )
            if self.proxy_manager:
                self.selected_proxy = await self.proxy_manager.get_proxy()

            await self._update_request_settings()
        except Exception as e:
            await self.close()
            raise VintedSetupError(
                message="Error during VintedNetworkClient setup.",
                underlying_error=e,
            ) from e

    async def _update_request_settings(self):
        """Update user agent, and session cookie for new request."""
        self.selected_user_agent = self._get_random_user_agent()
        self.session_cookie = await self._fetch_session_cookie()

    def _get_random_user_agent(self) -> str:
        """Get random user agent from loaded list. Raises VintedValidationError if not available."""
        if not self.user_agents:
            raise VintedValidationError(
                message="User agents not loaded. Call setup() first.",
                context={"operation": "get_random_user_agent"},
            )

        try:
            return random.choice(self.user_agents)["ua"]
        except (KeyError, IndexError, TypeError) as e:
            raise VintedValidationError(
                message="Invalid user agent data format.",
                context={"operation": "get_random_user_agent", "error": str(e)},
            ) from e

    async def _fetch_session_cookie(self) -> str:
        if not self.session:
            raise VintedValidationError(
                message="HTTP session not initialized. Call setup() first.",
                context={"operation": "fetch_session_cookie"},
            )

        endpoint = VintedEndpoint.HOME
        headers = {
            "User-Agent": self.selected_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, zstd",  # br is causing issues with aiohttp
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",  # Do Not Track
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Origin": self.base_url,
            "Referer": self.base_url,
        }

        last_response = None

        for i in range(REQUEST_RETRIES):
            logger.info(f"Attempt {i + 1} to fetch session cookie...")

            async with self.session.get(
                f"{self.base_url}/{endpoint.value}",
                headers=headers,
                proxy=(
                    self.selected_proxy.to_str_proxy() if self.selected_proxy else None
                ),
            ) as response:
                last_response = response

                if response.status == 200:
                    if self.proxy_manager and self.selected_proxy:
                        await self.proxy_manager.mark_success(self.selected_proxy)
                    try:
                        cookie = response.cookies.get(SESSION_COOKIE_NAME)
                        if cookie and cookie.value:
                            return cookie.value

                        logger.warning("Cannot find session cookie in response")
                    except (AttributeError, KeyError) as e:
                        logger.warning(f"Error accessing cookie from response: {e}")
                else:
                    sleep_time = 2**i
                    logger.info(f"Sleeping for {sleep_time} seconds before retrying...")
                    await asyncio.sleep(sleep_time)

                    if self.proxy_manager:
                        if (
                            self.selected_proxy
                            and response.status in RETRY_STATUS_CODES
                        ):
                            await self.proxy_manager.mark_failure(self.selected_proxy)
                        self.selected_proxy = await self.proxy_manager.get_proxy()

        raise VintedCookieRequestError(
            message=f"Failed to fetch session cookie after multiple attempts from {self.base_url}.",
            context={"last_status": last_response.status if last_response else None},
        )
