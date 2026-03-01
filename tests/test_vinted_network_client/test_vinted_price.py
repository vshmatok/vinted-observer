import pytest

from src.vinted_network_client.models.vinted_price import VintedPrice


# ============================================================================
# Defaults
# ============================================================================


def test_default_amount_is_none():
    price = VintedPrice()
    assert price.amount is None


def test_default_currency_code_is_none():
    price = VintedPrice()
    assert price.currency_code is None


# ============================================================================
# __str__
# ============================================================================


def test_str_with_amount_and_currency():
    price = VintedPrice(amount=25.50, currency_code="PLN")
    assert str(price) == "25.5 PLN"


def test_str_with_amount_only():
    price = VintedPrice(amount=10.0)
    assert str(price) == "10.0"


def test_str_no_amount():
    price = VintedPrice()
    assert str(price) == "VintedPrice(N/A)"


# ============================================================================
# __repr__
# ============================================================================


def test_repr_format():
    price = VintedPrice(amount=25.50, currency_code="PLN")
    result = repr(price)
    assert "VintedPrice" in result
    assert "25.5" in result
    assert "PLN" in result


# ============================================================================
# Equality
# ============================================================================


def test_same_values_are_equal():
    p1 = VintedPrice(amount=10.0, currency_code="EUR")
    p2 = VintedPrice(amount=10.0, currency_code="EUR")
    assert p1 == p2


def test_different_values_are_not_equal():
    p1 = VintedPrice(amount=10.0, currency_code="EUR")
    p2 = VintedPrice(amount=20.0, currency_code="EUR")
    assert p1 != p2


def test_str_with_zero_amount():
    price = VintedPrice(amount=0, currency_code="EUR")
    assert str(price) == "0 EUR"


def test_unhashable():
    price = VintedPrice(amount=10.0, currency_code="EUR")
    with pytest.raises(TypeError):
        hash(price)
