from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    """
    Base class for all queries.

    Queries are read operations that return data without modifying state.
    Handler errors propagate to caller.
    """

    pass
