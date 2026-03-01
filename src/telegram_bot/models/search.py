from dataclasses import dataclass


@dataclass
class Search:
    id: int
    chat_id: int | str
    query: str
    price_min: float
    price_max: float
