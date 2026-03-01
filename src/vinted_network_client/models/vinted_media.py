from dataclasses import dataclass
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(init=False)
class VintedMedia:
    type: Optional[str] = None
    url: Optional[str] = None

    def __init__(self, json_data: Optional[Any] = None):
        if json_data is not None:
            if not isinstance(json_data, dict):
                logger.warning(f"Expected dict for VintedMedia, got {type(json_data).__name__}")
                return

            # Extract string fields
            self.type = json_data.get("type")
            self.url = json_data.get("url")

    def __str__(self) -> str:
        if self.type and self.url:
            return f"{self.type}: {self.url}"
        elif self.url:
            return self.url
        return "VintedMedia(N/A)"

    def __repr__(self) -> str:
        return f"VintedMedia(type={self.type!r}, url={self.url!r})"
