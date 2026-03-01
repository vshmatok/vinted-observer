import logging

import pytest


@pytest.fixture(autouse=True)
def clean_root_logger():
    """Save and restore root logger state around each test."""
    root = logging.getLogger()
    original_level = root.level
    original_handlers = root.handlers[:]

    yield

    for h in root.handlers:
        if h not in original_handlers:
            h.close()
    root.handlers = original_handlers
    root.setLevel(original_level)
