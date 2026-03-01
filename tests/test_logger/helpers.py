import logging
import logging.handlers


def get_rotating_handler():
    """Extract the single RotatingFileHandler from the root logger."""
    handlers = [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(handlers) == 1, f"Expected 1 RotatingFileHandler, got {len(handlers)}"
    return handlers[0]
