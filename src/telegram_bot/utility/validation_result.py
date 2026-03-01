"""Result type for input validation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Result of input validation.

    Attributes:
        is_valid: Whether the validation passed
        error_message: Optional error message if validation failed
    """

    is_valid: bool
    error_message: Optional[str] = None
