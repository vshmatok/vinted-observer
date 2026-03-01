from dataclasses import dataclass
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(init=False)
class VintedUser:
    id: Optional[int] = None
    login: Optional[str] = None
    profile_url: Optional[str] = None

    def __init__(self, json_data: Optional[Any] = None):
        if json_data is not None:
            if not isinstance(json_data, dict):
                logger.warning(f"Expected dict for VintedUser, got {type(json_data).__name__}")
                return

            # Safely extract and validate id field
            if "id" in json_data and json_data["id"] is not None:
                try:
                    self.id = int(json_data["id"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedUser.id: {e}, value: {json_data['id']}")

            # Extract string fields
            self.login = json_data.get("login")
            self.profile_url = json_data.get("profile_url")

    def __str__(self) -> str:
        if self.login:
            return f"@{self.login}"
        elif self.id is not None:
            return f"User#{self.id}"
        return "VintedUser(N/A)"

    def __repr__(self) -> str:
        return f"VintedUser(id={self.id}, login={self.login!r}, profile_url={self.profile_url!r})"
