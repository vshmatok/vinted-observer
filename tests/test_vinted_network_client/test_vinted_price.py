import pytest

from src.vinted_network_client.models.vinted_price import VintedPrice


class TestDefaults:
    def test_amount_is_none(self):
        price = VintedPrice()
        assert price.amount is None

    def test_currency_code_is_none(self):
        price = VintedPrice()
        assert price.currency_code is None


class TestStr:
    def test_with_amount_and_currency(self):
        price = VintedPrice(amount=25.50, currency_code="PLN")
        assert str(price) == "25.5 PLN"

    def test_with_amount_only(self):
        price = VintedPrice(amount=10.0)
        assert str(price) == "10.0"

    def test_no_amount(self):
        price = VintedPrice()
        assert str(price) == "VintedPrice(N/A)"

    def test_with_zero_amount(self):
        price = VintedPrice(amount=0, currency_code="EUR")
        assert str(price) == "0 EUR"


class TestRepr:
    def test_format(self):
        price = VintedPrice(amount=25.50, currency_code="PLN")
        result = repr(price)
        assert "VintedPrice" in result
        assert "25.5" in result
        assert "PLN" in result


class TestEquality:
    def test_same_values_are_equal(self):
        p1 = VintedPrice(amount=10.0, currency_code="EUR")
        p2 = VintedPrice(amount=10.0, currency_code="EUR")
        assert p1 == p2

    def test_different_values_are_not_equal(self):
        p1 = VintedPrice(amount=10.0, currency_code="EUR")
        p2 = VintedPrice(amount=20.0, currency_code="EUR")
        assert p1 != p2

    def test_unhashable(self):
        price = VintedPrice(amount=10.0, currency_code="EUR")
        with pytest.raises(TypeError):
            hash(price)
