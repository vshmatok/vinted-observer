from dataclasses import dataclass
from typing import Any, List, Optional
import logging
from .vinted_media import VintedMedia
from .vinted_high_resolution import VintedHighResolution

logger = logging.getLogger(__name__)


@dataclass(init=False)
class VintedImage:
    id: Optional[int] = None
    image_no: Optional[int] = None
    thumbnails: Optional[List[VintedMedia]] = None
    is_main: Optional[bool] = None
    is_suspicious: Optional[bool] = None
    high_resolution: Optional[VintedHighResolution] = None
    full_size_url: Optional[str] = None
    is_hidden: Optional[bool] = None

    def __init__(self, json_data: Optional[Any] = None):
        if json_data is not None:
            if not isinstance(json_data, dict):
                logger.warning(f"Expected dict for VintedImage, got {type(json_data).__name__}")
                return

            # Safely extract and validate id field
            if "id" in json_data and json_data["id"] is not None:
                try:
                    self.id = int(json_data["id"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedImage.id: {e}, value: {json_data['id']}")

            # Safely extract and validate image_no field
            if "image_no" in json_data and json_data["image_no"] is not None:
                try:
                    self.image_no = int(json_data["image_no"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedImage.image_no: {e}, value: {json_data['image_no']}")

            # Extract boolean fields
            self.is_main = json_data.get("is_main")
            self.is_suspicious = json_data.get("is_suspicious")
            self.is_hidden = json_data.get("is_hidden")

            # Extract string fields
            self.full_size_url = json_data.get("full_size_url")

            # Parse high_resolution object
            if "high_resolution" in json_data and json_data["high_resolution"]:
                try:
                    self.high_resolution = VintedHighResolution(json_data["high_resolution"])
                except Exception as e:
                    logger.warning(f"Failed to parse VintedImage.high_resolution: {e}")
                    self.high_resolution = None

            # Parse thumbnails list
            if "thumbnails" in json_data and json_data["thumbnails"]:
                if isinstance(json_data["thumbnails"], list):
                    try:
                        self.thumbnails = [VintedMedia(media) for media in json_data["thumbnails"]]
                    except Exception as e:
                        logger.warning(f"Failed to parse VintedImage.thumbnails: {e}")
                        self.thumbnails = None
                else:
                    logger.warning(f"Expected list for VintedImage.thumbnails, got {type(json_data['thumbnails']).__name__}")

    def __str__(self) -> str:
        parts = []
        if self.id is not None:
            parts.append(f"id={self.id}")
        if self.image_no is not None:
            parts.append(f"no={self.image_no}")
        if self.is_main:
            parts.append("main")
        if self.full_size_url:
            parts.append(f"url={self.full_size_url[:50]}...")

        if parts:
            return f"VintedImage({', '.join(parts)})"
        return "VintedImage(N/A)"

    def __repr__(self) -> str:
        return (
            f"VintedImage(id={self.id}, image_no={self.image_no}, "
            f"is_main={self.is_main}, is_suspicious={self.is_suspicious}, "
            f"full_size_url={self.full_size_url!r}, is_hidden={self.is_hidden})"
        )
