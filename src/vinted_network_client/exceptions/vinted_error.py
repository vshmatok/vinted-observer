from datetime import datetime, timezone
from typing import Optional, Dict, Any


class VintedError(Exception):
    """
    Base exception for all Vinted API errors.

    Attributes:
        message: Human-readable error description
        context: Dictionary with error context (operation, proxy, endpoint, etc.)
        timestamp: When the error occurred
        underlying_error: The original exception that caused this error (if any)
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        underlying_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)
        self.underlying_error = underlying_error

        # If underlying_error provided, preserve it in the exception chain
        if underlying_error:
            self.__cause__ = underlying_error

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        error_dict = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "component": "vinted_network_client",
        }

        # Include underlying error info
        if self.underlying_error:
            error_dict["underlying_error"] = {
                "type": type(self.underlying_error).__name__,
                "message": str(self.underlying_error),
                "module": type(self.underlying_error).__module__,
            }

        return error_dict

    def get_error_chain(self) -> list[Exception]:
        """Get full chain of errors from root cause to this error"""
        chain: list[Exception] = [self]
        current: Optional[Exception] = self.underlying_error
        while current is not None:
            chain.append(current)
            current = getattr(current, "__cause__", None) or getattr(
                current, "__context__", None
            )
        return chain

    def get_root_cause(self) -> Exception:
        """Get the root cause (first error in the chain)"""
        chain = self.get_error_chain()
        return chain[-1]

    def __str__(self) -> str:
        base_str = (
            f"[{self.__class__.__name__}] {self.message} " f"(context: {self.context})"
        )

        if self.underlying_error:
            base_str += f"\n  Caused by: {type(self.underlying_error).__name__}: {str(self.underlying_error)}"

        return base_str
