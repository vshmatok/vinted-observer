from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """
    Base class for all events.

    Events are fire-and-forget notifications.
    Handler errors are logged but not propagated to publisher.
    """

    pass
