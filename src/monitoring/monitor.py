import logging
from html import escape
from typing import Optional
from datetime import datetime
from src.message_bus.queries.get_status_report_query import GetStatusReportQuery
from src.monitoring.error_parser import ErrorParser
from src.message_bus.message_bus import MessageBus
from src.message_bus.queries.get_recent_found_items_query import (
    GetRecentFoundItemsQuery,
)
from src.config import Config
from src.vinted_network_client.utils.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)


class Monitor:
    def __init__(
        self,
        message_bus: MessageBus,
        proxy_manager: Optional[ProxyManager],
        startup_time: datetime,
        error_parser: ErrorParser,
        status_items_timeframe_hours: int = Config.STATUS_ITEMS_TIMEFRAME_HOURS,
    ):
        self.message_bus = message_bus
        self.startup_time = startup_time
        self.status_items_timeframe_hours = status_items_timeframe_hours
        self.proxy_manager = proxy_manager
        self.error_parser = error_parser

    async def generate_status_report(self, query: GetStatusReportQuery) -> str:
        status_parts = []

        status_parts.append("🤖 Bot Status: ✅ Running")

        status_parts.append(self._get_uptime_report())
        status_parts.append("")

        recent_items_report = await self._get_recent_items_report()
        status_parts.append(recent_items_report)
        status_parts.append("")

        proxy_report = self._get_proxy_report()
        status_parts.append(proxy_report)
        status_parts.append("")

        recent_errors_report = await self._get_recent_errors_report()
        status_parts.append(recent_errors_report)

        return "\n".join(status_parts)

    def _get_uptime_report(self) -> str:
        try:
            now = datetime.now()
            if self.startup_time > now:
                logger.warning(f"startup_time {self.startup_time} is in the future")
                return "⏰ Uptime: Error calculating"

            uptime = now - self.startup_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            uptime_str = ""
            if days > 0:
                uptime_str += f"{days}d "
            if hours > 0 or days > 0:
                uptime_str += f"{hours}h "
            uptime_str += f"{minutes}m"

            return f"⏰ Uptime: {uptime_str.strip()}"
        except Exception as e:
            logger.error(f"Failed to calculate uptime: {e}", exc_info=True)
            return "⏰ Uptime: Error calculating"

    async def _get_recent_items_report(self) -> str:
        status_parts = []

        try:
            hours = self.status_items_timeframe_hours
            recent_items = await self.message_bus.query(
                GetRecentFoundItemsQuery(hours=hours)
            )

            if recent_items:
                total_items = sum(item["item_count"] for item in recent_items)
                status_parts.append(f"📦 Items found (last {hours}h):")
                for item in recent_items:
                    search_id = item["search_id"]
                    query = item["query"]
                    count = item["item_count"]
                    status_parts.append(
                        f'  • Search #{search_id} "{escape(query)}": {count} items'
                    )
                status_parts.append(f"  • Total: {total_items} items")
            else:
                status_parts.append(f"📦 Items found (last {hours}h): 0 items")
        except Exception as e:
            logger.error(f"Failed to get recent found items: {e}", exc_info=True)
            status_parts.append("📦 Items found: Error retrieving data")

        return "\n".join(status_parts)

    def _get_proxy_report(self) -> str:
        if self.proxy_manager is None:
            return "🔒 Proxies: Not configured"

        proxy_count = len(self.proxy_manager.proxies)
        failed_proxy_count = len(self.proxy_manager.failed_proxies)
        return (
            f"🔒 Proxies: {proxy_count} configured,"
            f" {len(self.proxy_manager.healthy_proxies)} healthy,"
            f" {failed_proxy_count} currently banned."
        )

    async def _get_recent_errors_report(self) -> str:
        status_parts = []

        try:
            recent_errors = await self.error_parser.get_recent_errors()
            if recent_errors:
                status_parts.append(f"⚠️ Recent Errors (last {len(recent_errors)}):")
                for error in recent_errors:
                    status_parts.append(f"  {error}")
            else:
                status_parts.append("⚠️ Recent Errors: None")
        except Exception as e:
            logger.error(f"Failed to parse recent errors: {e}", exc_info=True)
            status_parts.append("⚠️ Recent Errors: Error parsing logs")

        return "\n".join(status_parts)
