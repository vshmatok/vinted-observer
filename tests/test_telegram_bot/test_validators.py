"""Tests for telegram_bot.utility.validators — pure functions, no mocks."""

import pytest

from src.telegram_bot.utility.validators import (
    validate_price,
    validate_price_range,
    validate_search_query,
    validate_edit_price_min,
    validate_edit_price_max,
)


class TestValidatePrice:
    def test_valid_integer(self):
        result = validate_price("50")
        assert result.is_valid is True
        assert result.error_message is None

    def test_valid_float(self):
        result = validate_price("49.99")
        assert result.is_valid is True
        assert result.error_message is None

    def test_zero_is_valid(self):
        result = validate_price("0")
        assert result.is_valid is True
        assert result.error_message is None

    def test_leading_trailing_whitespace(self):
        result = validate_price("  42  ")
        assert result.is_valid is True
        assert result.error_message is None

    @pytest.mark.parametrize(
        "value",
        ["abc", "", "   ", "1.2.3", "49,99"],
        ids=[
            "non_numeric",
            "empty",
            "whitespace_only",
            "multiple_dots",
            "comma_decimal",
        ],
    )
    def test_non_numeric(self, value):
        result = validate_price(value)
        assert result.is_valid is False
        assert result.error_message is not None
        assert "valid price" in result.error_message

    def test_negative(self):
        result = validate_price("-5")
        assert result.is_valid is False
        assert result.error_message is not None
        assert "negative" in result.error_message.lower()

    @pytest.mark.parametrize(
        "value",
        ["nan", "inf", "-inf"],
        ids=["nan", "inf", "negative_inf"],
    )
    def test_nan_inf(self, value):
        result = validate_price(value)
        assert result.is_valid is False
        assert result.error_message is not None
        assert "valid price" in result.error_message

    def test_scientific_notation(self):
        result = validate_price("1e5")
        assert result.is_valid is True
        assert result.error_message is None

    def test_custom_field_name_in_error(self):
        result = validate_price("abc", field_name="maximum price")
        assert result.is_valid is False
        assert result.error_message is not None
        assert "maximum price" in result.error_message


class TestValidatePriceRange:
    def test_valid_range(self):
        result = validate_price_range(10.0, 100.0)
        assert result.is_valid is True
        assert result.error_message is None

    def test_small_difference(self):
        result = validate_price_range(99.99, 100.0)
        assert result.is_valid is True
        assert result.error_message is None

    def test_max_is_zero(self):
        result = validate_price_range(0.0, 0.0)
        assert result.is_valid is False
        assert result.error_message is not None
        assert "greater than zero" in result.error_message.lower()

    @pytest.mark.parametrize(
        ("min_price", "max_price"),
        [
            (100.0, 50.0),
            (50.0, 50.0),
            (0.0, -10.0),
            (-5.0, -3.0),
        ],
        ids=["max_less_than_min", "max_equals_min", "max_negative", "both_negative"],
    )
    def test_invalid(self, min_price, max_price):
        result = validate_price_range(min_price, max_price)
        assert result.is_valid is False
        assert result.error_message is not None

    def test_negative_min_positive_max(self):
        result = validate_price_range(-5.0, 10.0)
        assert result.is_valid is True
        assert result.error_message is None


class TestValidateSearchQuery:
    def test_valid_query(self):
        result = validate_search_query("nike shoes")
        assert result.is_valid is True
        assert result.error_message is None

    def test_exactly_two_chars(self):
        result = validate_search_query("ab")
        assert result.is_valid is True
        assert result.error_message is None

    def test_exactly_100_chars(self):
        result = validate_search_query("a" * 100)
        assert result.is_valid is True
        assert result.error_message is None

    def test_strips_whitespace(self):
        result = validate_search_query("  ab  ")
        assert result.is_valid is True
        assert result.error_message is None

    def test_unicode(self):
        result = validate_search_query("vintage куртка")
        assert result.is_valid is True
        assert result.error_message is None

    @pytest.mark.parametrize(
        "query",
        ["", "   "],
        ids=["empty", "whitespace_only"],
    )
    def test_blank(self, query):
        result = validate_search_query(query)
        assert result.is_valid is False
        assert result.error_message is not None
        assert "valid search term" in result.error_message

    def test_too_short(self):
        result = validate_search_query("a")
        assert result.is_valid is False
        assert result.error_message is not None
        assert "at least 2" in result.error_message

    def test_too_long(self):
        result = validate_search_query("a" * 101)
        assert result.is_valid is False
        assert result.error_message is not None
        assert "at most 100" in result.error_message


class TestValidateEditPriceMin:
    def test_valid(self):
        result = validate_edit_price_min(10.0, 100.0)
        assert result.is_valid is True
        assert result.error_message is None

    def test_zero_is_valid(self):
        result = validate_edit_price_min(0.0, 100.0)
        assert result.is_valid is True
        assert result.error_message is None

    def test_small_difference(self):
        result = validate_edit_price_min(99.99, 100.0)
        assert result.is_valid is True
        assert result.error_message is None

    @pytest.mark.parametrize(
        ("new_min", "current_max"),
        [
            (-5.0, 100.0),
            (100.0, 100.0),
            (150.0, 100.0),
            (0.0, 0.0),
        ],
        ids=["negative", "equals_max", "greater_than_max", "both_zero"],
    )
    def test_invalid(self, new_min, current_max):
        result = validate_edit_price_min(new_min, current_max)
        assert result.is_valid is False
        assert result.error_message is not None


class TestValidateEditPriceMax:
    def test_valid(self):
        result = validate_edit_price_max(100.0, 10.0)
        assert result.is_valid is True
        assert result.error_message is None

    def test_min_is_zero(self):
        result = validate_edit_price_max(5.0, 0.0)
        assert result.is_valid is True
        assert result.error_message is None

    @pytest.mark.parametrize(
        ("new_max", "current_min"),
        [
            (0.0, 10.0),
            (-5.0, 10.0),
            (10.0, 10.0),
            (5.0, 10.0),
        ],
        ids=["zero", "negative", "equals_min", "less_than_min"],
    )
    def test_invalid(self, new_max, current_min):
        result = validate_edit_price_max(new_max, current_min)
        assert result.is_valid is False
        assert result.error_message is not None
