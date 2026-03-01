"""Tests for telegram_bot.utility.validators — pure functions, no mocks."""

import pytest

from src.telegram_bot.utility.validators import (
    validate_price,
    validate_price_range,
    validate_search_query,
    validate_edit_price_min,
    validate_edit_price_max,
)


# --- validate_price ---


def test_validate_price_valid_integer():
    result = validate_price("50")
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_price_valid_float():
    result = validate_price("49.99")
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_price_zero_is_valid():
    result = validate_price("0")
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_price_leading_trailing_whitespace():
    result = validate_price("  42  ")
    assert result.is_valid is True
    assert result.error_message is None


@pytest.mark.parametrize(
    "value",
    ["abc", "", "   ", "1.2.3", "49,99"],
    ids=["non_numeric", "empty", "whitespace_only", "multiple_dots", "comma_decimal"],
)
def test_validate_price_non_numeric(value):
    result = validate_price(value)
    assert result.is_valid is False
    assert result.error_message is not None
    assert "valid price" in result.error_message


def test_validate_price_negative():
    result = validate_price("-5")
    assert result.is_valid is False
    assert result.error_message is not None
    assert "negative" in result.error_message.lower()


@pytest.mark.parametrize(
    "value",
    ["nan", "inf", "-inf"],
    ids=["nan", "inf", "negative_inf"],
)
def test_validate_price_nan_inf(value):
    result = validate_price(value)
    assert result.is_valid is False
    assert result.error_message is not None
    assert "valid price" in result.error_message


def test_validate_price_scientific_notation():
    result = validate_price("1e5")
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_price_custom_field_name_in_error():
    result = validate_price("abc", field_name="maximum price")
    assert result.is_valid is False
    assert result.error_message is not None
    assert "maximum price" in result.error_message


# --- validate_price_range ---


def test_validate_price_range_valid_range():
    result = validate_price_range(10.0, 100.0)
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_price_range_small_difference():
    result = validate_price_range(99.99, 100.0)
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_price_range_max_is_zero():
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
def test_validate_price_range_invalid(min_price, max_price):
    result = validate_price_range(min_price, max_price)
    assert result.is_valid is False
    assert result.error_message is not None


def test_validate_price_range_negative_min_positive_max():
    result = validate_price_range(-5.0, 10.0)
    assert result.is_valid is True
    assert result.error_message is None


# --- validate_search_query ---


def test_validate_search_query_valid_query():
    result = validate_search_query("nike shoes")
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_search_query_exactly_two_chars():
    result = validate_search_query("ab")
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_search_query_exactly_100_chars():
    result = validate_search_query("a" * 100)
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_search_query_strips_whitespace():
    result = validate_search_query("  ab  ")
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_search_query_unicode():
    result = validate_search_query("vintage куртка")
    assert result.is_valid is True
    assert result.error_message is None


@pytest.mark.parametrize(
    "query",
    ["", "   "],
    ids=["empty", "whitespace_only"],
)
def test_validate_search_query_blank(query):
    result = validate_search_query(query)
    assert result.is_valid is False
    assert result.error_message is not None
    assert "valid search term" in result.error_message


def test_validate_search_query_too_short():
    result = validate_search_query("a")
    assert result.is_valid is False
    assert result.error_message is not None
    assert "at least 2" in result.error_message


def test_validate_search_query_too_long():
    result = validate_search_query("a" * 101)
    assert result.is_valid is False
    assert result.error_message is not None
    assert "at most 100" in result.error_message


# --- validate_edit_price_min ---


def test_validate_edit_price_min_valid():
    result = validate_edit_price_min(10.0, 100.0)
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_edit_price_min_zero_is_valid():
    result = validate_edit_price_min(0.0, 100.0)
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_edit_price_min_small_difference():
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
def test_validate_edit_price_min_invalid(new_min, current_max):
    result = validate_edit_price_min(new_min, current_max)
    assert result.is_valid is False
    assert result.error_message is not None


# --- validate_edit_price_max ---


def test_validate_edit_price_max_valid():
    result = validate_edit_price_max(100.0, 10.0)
    assert result.is_valid is True
    assert result.error_message is None


def test_validate_edit_price_max_min_is_zero():
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
def test_validate_edit_price_max_invalid(new_max, current_min):
    result = validate_edit_price_max(new_max, current_min)
    assert result.is_valid is False
    assert result.error_message is not None
