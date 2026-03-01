import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.message_bus.message_bus import MessageBus
from src.monitoring.error_parser import ErrorParser
from src.vinted_network_client.utils.proxy_manager import ProxyManager
from src.monitoring.monitor import Monitor


@pytest.fixture
def mock_message_bus():
    bus = AsyncMock(spec=MessageBus)
    bus.query.return_value = []
    return bus


@pytest.fixture
def mock_error_parser():
    parser = AsyncMock(spec=ErrorParser)
    parser.get_recent_errors.return_value = []
    return parser


@pytest.fixture
def mock_proxy_manager():
    pm = MagicMock(spec=ProxyManager)
    pm.proxies = []
    pm.healthy_proxies = []
    pm.failed_proxies = []
    return pm


@pytest.fixture
def monitor(mock_message_bus, mock_error_parser):
    return Monitor(
        message_bus=mock_message_bus,
        proxy_manager=None,
        startup_time=datetime(2026, 2, 21, 10, 0, 0),
        error_parser=mock_error_parser,
        status_items_timeframe_hours=1,
    )


@pytest.fixture
def monitor_with_proxy(mock_message_bus, mock_error_parser, mock_proxy_manager):
    return Monitor(
        message_bus=mock_message_bus,
        proxy_manager=mock_proxy_manager,
        startup_time=datetime(2026, 2, 21, 10, 0, 0),
        error_parser=mock_error_parser,
        status_items_timeframe_hours=1,
    )


@pytest.fixture
def valid_log_file(tmp_path):
    """Well-formed log lines matching the default format."""
    content = (
        "2026-02-19 10:00:01 - myapp - INFO - App started\n"
        "2026-02-19 10:00:02 - myapp - ERROR - Something broke\n"
        "2026-02-19 10:00:03 - myapp - CRITICAL - Fatal\n"
    )
    file = tmp_path / "valid.log"
    file.write_text(content)
    return file


@pytest.fixture
def malformed_log_file(tmp_path):
    """Lines that won't match the expected format."""
    content = (
        "not a log line at all\n"
        "ERROR without timestamp\n"
        "2026-02-19 - missing fields\n"
        "2026-02-19 10:00:01 - myapp - ERROR - Valid line among garbage\n"
    )
    file = tmp_path / "malformed.log"
    file.write_text(content)
    return file


@pytest.fixture
def empty_log_file(tmp_path):
    """An empty log file."""
    file = tmp_path / "empty.log"
    file.write_text("")
    return file


@pytest.fixture
def permission_denied_log_file(tmp_path):
    """A log file that exists but cannot be read due to permissions."""
    file = tmp_path / "noperm.log"
    file.write_text("2026-02-19 10:00:00 - app - ERROR - fail\n")
    os.chmod(file, 0o000)
    yield file
    os.chmod(file, 0o644)  # restore for cleanup


@pytest.fixture
def large_log_file(tmp_path):
    """A log file larger than 65KB to test tail reading."""
    file = tmp_path / "large.log"

    # Create a line that will be cut off at the 65KB boundary
    padding_line = "2026-02-19 09:00:00 - myapp - INFO - " + "x" * 200 + "\n"
    error_line = "2026-02-19 10:00:00 - myapp - ERROR - should be found\n"

    # Fill file beyond 65536 bytes: padding + one error at the end
    lines_needed = (65536 // len(padding_line)) + 10
    content = padding_line * lines_needed + error_line
    file.write_text(content)

    return file


@pytest.fixture
def special_chars_log_file(tmp_path):
    """Log file with special characters to ensure encoding is handled."""
    content = (
        "2026-02-19 10:00:00 - app - ERROR - failed - retry in 5s\n"
        "2026-02-19 10:00:01 - app - ERROR - regex [a-z]+ and (group) failed\n"
        "2026-02-19 10:00:02 - app - ERROR - connection to München failed\n"
    )
    file = tmp_path / "special.log"
    file.write_text(content)
    return file


@pytest.fixture
def all_errors_log_file(tmp_path):
    """Log file where all lines are errors"""
    content = (
        "2026-02-19 10:00:00 - app - ERROR - first\n"
        "2026-02-19 10:00:01 - app - CRITICAL - second\n"
        "2026-02-19 10:00:02 - app - ERROR - third\n"
    )
    file = tmp_path / "all_errors.log"
    file.write_text(content)
    return file
