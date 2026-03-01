from dataclasses import dataclass
import time
from typing import Optional

from src.vinted_network_client.models.vinted_proxy import VintedProxy


@dataclass
class ProxyStats:
    proxy: VintedProxy
    last_used: Optional[float] = None
    last_failed: Optional[float] = None
    is_banned: bool = False

    def mark_success(self):
        """Mark proxy as successful."""
        self.last_used = time.time()
        self.is_banned = False

    def mark_failure(self):
        """Mark proxy as failed."""
        self.last_failed = time.time()
        self.is_banned = True
