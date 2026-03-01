"""Test helpers for telegram_bot tests."""

from src.vinted_network_client.models.vinted_item import VintedItem
from src.vinted_network_client.models.vinted_price import VintedPrice


def make_vinted_item(**kwargs) -> VintedItem:
    """Build a VintedItem with sensible defaults, bypassing JSON parsing."""
    defaults = {
        "id": 42,
        "title": "Vintage Jacket",
        "photo": None,
        "price": VintedPrice(amount=25.50, currency_code="EUR"),
        "view_count": 10,
        "user": None,
        "path": "/items/42",
        "url": "https://www.vinted.pl/items/42",
        "status": "active",
        "total_item_price": VintedPrice(amount=29.99, currency_code="EUR"),
        "brand_title": "Nike",
        "size_title": "M",
        "buy_url": "https://www.vinted.pl/items/42/buy",
        "created_at_ts": None,
        "raw_timestamp": None,
    }
    defaults.update(kwargs)

    item = VintedItem.__new__(VintedItem)
    for key, value in defaults.items():
        setattr(item, key, value)
    return item
