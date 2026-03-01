"""Input validation utilities for Telegram bot."""

import math

from src.telegram_bot.utility.validation_result import ValidationResult


def validate_price(value: str, field_name: str = "price") -> ValidationResult:
    """
    Validate price input.

    Args:
        value: String input from user
        field_name: Name of field for error messages (e.g., "minimum price", "maximum price")

    Returns:
        ValidationResult with is_valid and optional error_message
    """
    try:
        price = float(value.strip())
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message=f"Please enter a valid {field_name} like '50'.",
        )

    if math.isnan(price) or math.isinf(price):
        return ValidationResult(
            is_valid=False,
            error_message=f"Please enter a valid {field_name} like '50'.",
        )

    if price < 0:
        return ValidationResult(
            is_valid=False,
            error_message=f"{field_name.capitalize()} cannot be negative. Please enter a valid {field_name} like '50'.",
        )

    return ValidationResult(is_valid=True)


def validate_price_range(min_price: float, max_price: float) -> ValidationResult:
    """
    Validate that max price is greater than min price.

    Args:
        min_price: Minimum price
        max_price: Maximum price

    Returns:
        ValidationResult with is_valid and optional error_message
    """
    if max_price <= 0:
        return ValidationResult(
            is_valid=False,
            error_message="Maximum price must be greater than zero. Please enter a valid maximum price like '200'.",
        )

    if max_price <= min_price:
        return ValidationResult(
            is_valid=False,
            error_message=(
                "Maximum price must be greater than minimum price. "
                "Please enter a valid maximum price like '200'."
            ),
        )

    return ValidationResult(is_valid=True)


def validate_search_query(query: str) -> ValidationResult:
    """
    Validate search query input.

    Args:
        query: Search query string

    Returns:
        ValidationResult with is_valid and optional error_message
    """
    query = query.strip()

    if not query:
        return ValidationResult(
            is_valid=False,
            error_message="Please enter a valid search term like 'vintage jacket'.",
        )

    if len(query) < 2:
        return ValidationResult(
            is_valid=False,
            error_message="Search term must be at least 2 characters long.",
        )

    if len(query) > 100:
        return ValidationResult(
            is_valid=False,
            error_message="Search term must be at most 100 characters.",
        )

    return ValidationResult(is_valid=True)


def validate_edit_price_min(
    new_min_price: float, current_max_price: float
) -> ValidationResult:
    """
    Validate minimum price during edit operation.

    Args:
        new_min_price: New minimum price value
        current_max_price: Current maximum price (to validate range)

    Returns:
        ValidationResult with is_valid and optional error_message
    """
    if new_min_price < 0:
        return ValidationResult(
            is_valid=False,
            error_message="Minimum price must be non-negative and less than the maximum price.",
        )

    if new_min_price >= current_max_price:
        return ValidationResult(
            is_valid=False,
            error_message="Minimum price must be non-negative and less than the maximum price.",
        )

    return ValidationResult(is_valid=True)


def validate_edit_price_max(
    new_max_price: float, current_min_price: float
) -> ValidationResult:
    """
    Validate maximum price during edit operation.

    Args:
        new_max_price: New maximum price value
        current_min_price: Current minimum price (to validate range)

    Returns:
        ValidationResult with is_valid and optional error_message
    """
    if new_max_price <= 0:
        return ValidationResult(
            is_valid=False,
            error_message="Maximum price must be greater than zero and greater than the minimum price.",
        )

    if new_max_price <= current_min_price:
        return ValidationResult(
            is_valid=False,
            error_message="Maximum price must be greater than zero and greater than the minimum price.",
        )

    return ValidationResult(is_valid=True)
