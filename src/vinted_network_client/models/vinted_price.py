from dataclasses import dataclass
from typing import Optional


@dataclass
class VintedPrice:
    amount: Optional[float] = None
    currency_code: Optional[str] = None

    def __str__(self) -> str:
        if self.amount is not None and self.currency_code:
            return f"{self.amount} {self.currency_code}"
        elif self.amount is not None:
            return f"{self.amount}"
        return "VintedPrice(N/A)"

    def __repr__(self) -> str:
        return (
            f"VintedPrice(amount={self.amount}, currency_code={self.currency_code!r})"
        )
