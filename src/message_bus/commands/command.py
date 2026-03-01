from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """
    Base class for all commands.

    Commands are write operations that modify state.
    Handler errors propagate to caller.
    """

    pass
