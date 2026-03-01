from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
import logging
from .vinted_image import VintedImage
from .vinted_price import VintedPrice
from .vinted_user import VintedUser

logger = logging.getLogger(__name__)


@dataclass(init=False)
class VintedItem:
    id: Optional[int] = None
    title: Optional[str] = None
    photo: Optional[VintedImage] = None
    price: Optional[VintedPrice] = None
    view_count: Optional[int] = None
    user: Optional[VintedUser] = None
    path: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    total_item_price: Optional[VintedPrice] = None
    brand_title: Optional[str] = None
    size_title: Optional[str] = None
    buy_url: Optional[str] = None
    created_at_ts: Optional[datetime] = None
    raw_timestamp: Optional[int] = None

    def __init__(self, json_data: Optional[Any] = None):
        if json_data is not None:
            if not isinstance(json_data, dict):
                logger.warning(f"Expected dict for VintedItem, got {type(json_data).__name__}")
                return

            # Safely extract and validate id field
            if "id" in json_data and json_data["id"] is not None:
                try:
                    self.id = int(json_data["id"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedItem.id: {e}, value: {json_data['id']}")

            # Safely extract and validate view_count field
            if "view_count" in json_data and json_data["view_count"] is not None:
                try:
                    self.view_count = int(json_data["view_count"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedItem.view_count: {e}, value: {json_data['view_count']}")

            # Extract string fields
            self.title = json_data.get("title")
            self.path = json_data.get("path")
            self.url = json_data.get("url")
            self.status = json_data.get("status")
            self.brand_title = json_data.get("brand_title")
            self.size_title = json_data.get("size_title")

            # Parse user object
            if "user" in json_data and json_data["user"]:
                try:
                    self.user = VintedUser(json_data["user"])
                except Exception as e:
                    logger.warning(f"Failed to parse VintedItem.user: {e}")
                    self.user = None

            # Parse photo object
            if "photo" in json_data and json_data["photo"]:
                try:
                    self.photo = VintedImage(json_data["photo"])
                except Exception as e:
                    logger.warning(f"Failed to parse VintedItem.photo: {e}")
                    self.photo = None

            # Parse price from different formats
            if isinstance(json_data.get("price"), dict):
                try:
                    self.price = VintedPrice(
                        float(json_data["price"]["amount"]),
                        currency_code=json_data["price"]["currency_code"],
                    )
                    # Also set total_item_price if not explicitly provided
                    self.total_item_price = self.price
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedItem.price from dict: {e}")
                    self.price = None
            elif isinstance(json_data.get("price"), str):
                try:
                    self.price = VintedPrice(float(json_data["price"]))
                    # Also set total_item_price if not explicitly provided
                    self.total_item_price = self.price
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedItem.price from string: {e}")
                    self.price = None

            # Parse total_item_price (overwrites price if present)
            if isinstance(json_data.get("total_item_price"), dict):
                try:
                    self.total_item_price = VintedPrice(
                        float(json_data["total_item_price"]["amount"]),
                        currency_code=json_data["total_item_price"]["currency_code"],
                    )
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedItem.total_item_price from dict: {e}")
            elif isinstance(json_data.get("total_item_price"), str):
                try:
                    self.total_item_price = VintedPrice(
                        float(json_data["total_item_price"])
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedItem.total_item_price from string: {e}")

            # Build buy URL
            if self.url is not None and self.id is not None:
                try:
                    if "items" in self.url:
                        self.buy_url = (
                            self.url.split("items")[0]
                            + "transaction/buy/new?source_screen=item&transaction%5Bitem_id%5D="
                            + str(self.id)
                        )
                    else:
                        logger.warning(f"VintedItem.url does not contain 'items': {self.url}")
                        self.buy_url = None
                except Exception as e:
                    logger.warning(f"Failed to build VintedItem.buy_url: {e}")
                    self.buy_url = None

            # Parse timestamp from photo
            if (
                self.photo is not None
                and self.photo.high_resolution is not None
                and self.photo.high_resolution.timestamp is not None
            ):
                try:
                    self.created_at_ts = datetime.fromtimestamp(
                        float(self.photo.high_resolution.timestamp), tz=timezone.utc
                    )
                    self.raw_timestamp = self.photo.high_resolution.timestamp
                except (ValueError, OSError, TypeError) as e:
                    logger.warning(f"Failed to parse VintedItem.created_at_ts from timestamp: {e}")
                    self.created_at_ts = None
                    self.raw_timestamp = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VintedItem):
            return False

        return self.id == other.id

    def __hash__(self) -> int:
        return hash(("id", self.id))

    def __str__(self) -> str:
        parts = []
        if self.title:
            parts.append(self.title)
        if self.total_item_price:
            parts.append(str(self.total_item_price))
        if self.brand_title:
            parts.append(f"({self.brand_title})")
        if self.size_title:
            parts.append(f"Size: {self.size_title}")
        if self.url:
            parts.append(f"URL: {self.url}")

        if parts:
            return " - ".join(parts)
        return f"VintedItem#{self.id}" if self.id else "VintedItem(N/A)"

    def __repr__(self) -> str:
        return (
            f"VintedItem(id={self.id}, title={self.title!r}, "
            f"price={self.total_item_price!r}, brand={self.brand_title!r}, "
            f"size={self.size_title!r}, status={self.status!r}, "
            f"user={self.user!r}, url={self.url!r})"
        )
