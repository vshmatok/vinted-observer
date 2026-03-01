from dataclasses import dataclass
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(init=False)
class VintedHighResolution:
    id: Optional[str] = None
    timestamp: Optional[int] = None

    def __init__(self, json_data: Optional[Any] = None):
        if json_data is not None:
            if not isinstance(json_data, dict):
                logger.warning(f"Expected dict for VintedHighResolution, got {type(json_data).__name__}")
                return

            # Extract id field
            self.id = json_data.get("id")

            # Safely extract and validate timestamp field
            if "timestamp" in json_data and json_data["timestamp"] is not None:
                try:
                    self.timestamp = int(json_data["timestamp"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedHighResolution.timestamp: {e}, value: {json_data['timestamp']}")

    def __str__(self) -> str:
        if self.id and self.timestamp:
            return f"VintedHighResolution(id={self.id}, timestamp={self.timestamp})"
        elif self.id:
            return f"VintedHighResolution(id={self.id})"
        return "VintedHighResolution(N/A)"

    def __repr__(self) -> str:
        return f"VintedHighResolution(id={self.id!r}, timestamp={self.timestamp})"
