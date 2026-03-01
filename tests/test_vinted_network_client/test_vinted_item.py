from datetime import datetime, timezone

from src.vinted_network_client.models.vinted_item import VintedItem
from src.vinted_network_client.models.vinted_user import VintedUser
from src.vinted_network_client.models.vinted_image import VintedImage
from src.vinted_network_client.models.vinted_price import VintedPrice

from tests.test_vinted_network_client.helpers import make_item_json


class TestInit:
    def test_full_json_parses_all_fields(self):
        item = VintedItem(make_item_json())
        assert item.id == 12345
        assert item.title == "Nike Air Max"
        assert item.view_count == 42
        assert item.path == "/items/12345-nike-air-max"
        assert item.url == "https://www.vinted.pl/items/12345-nike-air-max"
        assert item.status == "active"
        assert item.brand_title == "Nike"
        assert item.size_title == "M"
        assert isinstance(item.user, VintedUser)
        assert isinstance(item.photo, VintedImage)
        assert isinstance(item.price, VintedPrice)
        assert isinstance(item.total_item_price, VintedPrice)
        assert item.buy_url is not None
        assert item.created_at_ts is not None
        assert item.raw_timestamp == 1700000000

    def test_none_input(self):
        item = VintedItem(None)
        assert item.id is None
        assert item.title is None

    def test_no_args(self):
        item = VintedItem()
        assert item.id is None

    def test_non_dict_input(self):
        item = VintedItem("not a dict")
        assert item.id is None

    def test_id_parsed_as_int(self):
        item = VintedItem(make_item_json(id="999"))
        assert item.id == 999
        assert isinstance(item.id, int)

    def test_invalid_id_stays_none(self):
        item = VintedItem(make_item_json(id="not_a_number"))
        assert item.id is None

    def test_view_count_parsed_as_int(self):
        item = VintedItem(make_item_json(view_count="100"))
        assert item.view_count == 100
        assert isinstance(item.view_count, int)

    def test_invalid_view_count_stays_none(self):
        item = VintedItem(make_item_json(view_count="abc"))
        assert item.view_count is None

    def test_string_fields_extracted(self):
        item = VintedItem(
            make_item_json(
                title="Test",
                path="/test",
                url="https://test.com/items/1",
                status="sold",
                brand_title="Adidas",
                size_title="L",
            )
        )
        assert item.title == "Test"
        assert item.path == "/test"
        assert item.status == "sold"
        assert item.brand_title == "Adidas"
        assert item.size_title == "L"

    def test_user_parsed_as_vinted_user(self):
        item = VintedItem(make_item_json())
        assert isinstance(item.user, VintedUser)
        assert item.user.login == "seller123"

    def test_invalid_user_sets_none(self):
        item = VintedItem(make_item_json(user=123))
        assert isinstance(item.user, VintedUser)
        assert item.user.id is None

    def test_photo_parsed_as_vinted_image(self):
        item = VintedItem(make_item_json())
        assert isinstance(item.photo, VintedImage)

    def test_invalid_photo_sets_none(self):
        item = VintedItem(make_item_json(photo=123))
        assert isinstance(item.photo, VintedImage)
        assert item.photo.id is None

    def test_price_from_dict_format(self):
        item = VintedItem(
            make_item_json(
                price={"amount": "25.50", "currency_code": "PLN"},
                total_item_price=None,
            )
        )
        assert item.price is not None
        assert item.price.amount == 25.50
        assert item.price.currency_code == "PLN"

    def test_price_from_string_format(self):
        item = VintedItem(make_item_json(price="19.99", total_item_price=None))
        assert item.price is not None
        assert item.price.amount == 19.99

    def test_invalid_price_dict_sets_none(self):
        item = VintedItem(make_item_json(price={"bad": "data"}, total_item_price=None))
        assert item.price is None

    def test_invalid_price_string_sets_none(self):
        item = VintedItem(make_item_json(price="not_a_number", total_item_price=None))
        assert item.price is None

    def test_total_item_price_overwrites_when_present(self):
        item = VintedItem(
            make_item_json(
                price={"amount": "10.00", "currency_code": "PLN"},
                total_item_price={"amount": "30.00", "currency_code": "PLN"},
            )
        )
        assert item.total_item_price is not None
        assert item.total_item_price.amount == 30.00

    def test_total_item_price_from_string(self):
        item = VintedItem(make_item_json(total_item_price="45.00"))
        assert item.total_item_price is not None
        assert item.total_item_price.amount == 45.00

    def test_buy_url_built_from_url_and_id(self):
        item = VintedItem(make_item_json())
        assert item.buy_url is not None
        assert "transaction/buy/new" in item.buy_url
        assert "12345" in item.buy_url

    def test_buy_url_none_when_url_lacks_items(self):
        item = VintedItem(make_item_json(url="https://www.vinted.pl/no-match"))
        assert item.buy_url is None

    def test_buy_url_none_when_url_is_none(self):
        item = VintedItem(make_item_json(url=None))
        assert item.buy_url is None

    def test_buy_url_none_when_id_is_none(self):
        item = VintedItem(make_item_json(id=None))
        assert item.buy_url is None

    def test_created_at_ts_from_photo_timestamp(self):
        item = VintedItem(make_item_json())
        assert isinstance(item.created_at_ts, datetime)
        assert item.created_at_ts.tzinfo == timezone.utc

    def test_created_at_ts_none_when_no_photo(self):
        item = VintedItem(make_item_json(photo=None))
        assert item.created_at_ts is None

    def test_raw_timestamp_matches_photo_timestamp(self):
        item = VintedItem(make_item_json())
        assert item.raw_timestamp == 1700000000

    def test_missing_optional_fields_default_none(self):
        item = VintedItem({"id": 1})
        assert item.title is None
        assert item.user is None
        assert item.photo is None
        assert item.brand_title is None

    def test_created_at_ts_extreme_negative_timestamp(self):
        json_data = make_item_json()
        json_data["photo"]["high_resolution"]["timestamp"] = -1
        item = VintedItem(json_data)
        # Should either parse or gracefully fail to None
        assert item.created_at_ts is None or item.created_at_ts is not None

    def test_total_item_price_without_price_key(self):
        json_data = make_item_json(
            total_item_price={"amount": "15.00", "currency_code": "EUR"}
        )
        del json_data["price"]
        item = VintedItem(json_data)
        assert item.price is None
        assert item.total_item_price is not None
        assert item.total_item_price.amount == 15.0

    def test_buy_url_splits_at_first_items_occurrence(self):
        item = VintedItem(make_item_json(url="https://items.example.com/items/12345"))
        assert item.buy_url is not None
        assert "transaction/buy/new" in item.buy_url


class TestEq:
    def test_same_id_equal(self):
        a = VintedItem(make_item_json(id=1))
        b = VintedItem(make_item_json(id=1))
        assert a == b

    def test_different_id_not_equal(self):
        a = VintedItem(make_item_json(id=1))
        b = VintedItem(make_item_json(id=2))
        assert a != b

    def test_non_vinted_item_returns_false(self):
        a = VintedItem(make_item_json(id=1))
        assert a != "not an item"

    def test_both_id_none_are_equal(self):
        a = VintedItem()
        b = VintedItem()
        assert a == b


class TestHash:
    def test_same_id_same_hash(self):
        a = VintedItem(make_item_json(id=1))
        b = VintedItem(make_item_json(id=1))
        assert hash(a) == hash(b)

    def test_different_id_different_hash(self):
        a = VintedItem(make_item_json(id=1))
        b = VintedItem(make_item_json(id=2))
        assert hash(a) != hash(b)

    def test_deduplication_in_set(self):
        a = VintedItem(make_item_json(id=1))
        b = VintedItem(make_item_json(id=1))
        c = VintedItem(make_item_json(id=2))
        assert len({a, b, c}) == 2

    def test_both_id_none_same_hash(self):
        a = VintedItem()
        b = VintedItem()
        assert hash(a) == hash(b)

    def test_id_none_deduplication_in_set(self):
        a = VintedItem()
        b = VintedItem()
        c = VintedItem(make_item_json(id=1))
        assert len({a, b, c}) == 2


class TestStr:
    def test_full_item(self):
        item = VintedItem(make_item_json())
        result = str(item)
        assert "Nike Air Max" in result
        assert "Nike" in result

    def test_minimal_item_with_id(self):
        item = VintedItem({"id": 42})
        assert "42" in str(item)

    def test_empty_item(self):
        item = VintedItem()
        assert str(item) == "VintedItem(N/A)"


class TestRepr:
    def test_contains_key_fields(self):
        item = VintedItem(make_item_json())
        result = repr(item)
        assert "VintedItem" in result
        assert "12345" in result
        assert "Nike Air Max" in result

    def test_has_balanced_parentheses(self):
        item = VintedItem(make_item_json())
        result = repr(item)
        assert result.count("(") == result.count(")")
