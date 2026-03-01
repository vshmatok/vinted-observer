import asyncio
import logging
from typing import List
from src.vinted_network_client.models.vinted_proxy import VintedProxy
from src.vinted_network_client.models.vinted_proxy_stats import ProxyStats

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy settings for network requests."""

    def __init__(self, vinted_proxies: List[VintedProxy]):
        self._lock = asyncio.Lock()
        self._proxies_stats = [ProxyStats(proxy) for proxy in vinted_proxies]

    @property
    def proxies(self) -> List[VintedProxy]:
        """Returns the list of proxies being managed."""
        return [stat.proxy for stat in self._proxies_stats]
    
    @property
    def failed_proxies(self) -> List[VintedProxy]:
        """Returns the list of failed proxies being managed."""
        return [stat.proxy for stat in self._proxies_stats if stat.is_banned]
    
    @property
    def healthy_proxies(self) -> List[VintedProxy]:
        """Returns the list of healthy proxies being managed."""
        return [stat.proxy for stat in self._proxies_stats if not stat.is_banned]

    async def get_proxy(self) -> VintedProxy:
        async with self._lock:
            # Filter healthy proxies
            working_proxies = [s for s in self._proxies_stats if  not s.is_banned]
            ordered_working_proxies = sorted(
                working_proxies,
                key=lambda s: (s.last_used is not None, s.last_used)
            )

            if not ordered_working_proxies:
                logger.info("All proxies are currently banned. Resetting ban status.")
                
                for stat in self._proxies_stats:
                    stat.is_banned = False
                ordered_working_proxies = sorted(
                    self._proxies_stats,
                    key=lambda s: (s.last_used is not None, s.last_used)
                )

            return ordered_working_proxies[0].proxy

    async def mark_success(self, proxy: VintedProxy):
        """Mark proxy request as successful."""
        async with self._lock:
            logger.info(f"Marking proxy {proxy} as successful.")
            for stat in self._proxies_stats:
                if stat.proxy == proxy:
                    stat.mark_success()
                    break

    async def mark_failure(self, proxy: VintedProxy):
        """Mark proxy request as failed."""
        async with self._lock:
            logger.info(f"Marking proxy {proxy} as failed.")
            for stat in self._proxies_stats:
                if stat.proxy == proxy:
                    stat.mark_failure()
                    break
