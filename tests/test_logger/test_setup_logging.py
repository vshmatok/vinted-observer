import logging
import logging.handlers

import pytest

from src.logger import setup_logging

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_rotating_handler():
    """Extract the single RotatingFileHandler from the root logger."""
    handlers = [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(handlers) == 1, f"Expected 1 RotatingFileHandler, got {len(handlers)}"
    return handlers[0]


# --- Console-only mode ---


def test_returns_root_logger():
    result = setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    assert result is logging.getLogger()


def test_sets_root_logger_level():
    setup_logging(
        log_level="DEBUG",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    assert logging.getLogger().level == logging.DEBUG


def test_clears_existing_handlers():
    root = logging.getLogger()
    dummy = logging.StreamHandler()
    root.addHandler(dummy)
    assert dummy in root.handlers

    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    assert dummy not in logging.getLogger().handlers


def test_adds_console_handler():
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    handlers = logging.getLogger().handlers
    stream_handlers = [h for h in handlers if type(h) is logging.StreamHandler]
    assert len(stream_handlers) == 1


def test_console_handler_uses_configured_level():
    setup_logging(
        log_level="WARNING",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    handler = logging.getLogger().handlers[0]
    assert handler.level == logging.WARNING


# NOTE: formatter._fmt is a private attribute; no public API exists
def test_console_handler_uses_configured_format():
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    handler = logging.getLogger().handlers[0]
    assert handler.formatter is not None
    assert handler.formatter._fmt == LOG_FORMAT
    assert handler.formatter.datefmt == LOG_DATE_FORMAT


def test_no_file_handler_when_log_file_is_none():
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=None,  # type: ignore[arg-type]
    )
    handlers = logging.getLogger().handlers
    assert len(handlers) == 1
    assert type(handlers[0]) is logging.StreamHandler


def test_idempotent_on_double_call():
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    handlers = logging.getLogger().handlers
    stream_handlers = [h for h in handlers if type(h) is logging.StreamHandler]
    assert len(stream_handlers) == 1


# --- Parametrized log levels ---


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_log_level_parametrized(level):
    setup_logging(
        log_level=level,
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    expected = getattr(logging, level)
    root = logging.getLogger()
    assert root.level == expected
    assert root.handlers[0].level == expected


def test_log_level_case_insensitive():
    setup_logging(
        log_level="debug",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    assert logging.getLogger().level == logging.DEBUG


def test_invalid_log_level_falls_back_to_info():
    setup_logging(
        log_level="FOOBAR",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file="",
    )
    assert logging.getLogger().level == logging.INFO
    assert logging.getLogger().handlers[0].level == logging.INFO


# --- File handler mode ---


def test_file_handler_added_when_log_file_set(tmp_path):
    log_file = str(tmp_path / "app.log")
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=log_file,
    )
    handlers = logging.getLogger().handlers
    assert len(handlers) == 2
    _get_rotating_handler()


def test_file_handler_creates_parent_directories(tmp_path):
    log_file = str(tmp_path / "a" / "b" / "c" / "app.log")
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=log_file,
    )
    assert (tmp_path / "a" / "b" / "c").is_dir()


def test_file_handler_rotation_config(tmp_path):
    log_file = str(tmp_path / "app.log")
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=log_file,
    )
    handler = _get_rotating_handler()
    assert handler.maxBytes == 10 * 1024 * 1024
    assert handler.backupCount == 5
    assert handler.encoding == "utf-8"


# NOTE: formatter._fmt is a private attribute; no public API exists
def test_file_handler_uses_configured_level_and_format(tmp_path):
    log_file = str(tmp_path / "app.log")
    setup_logging(
        log_level="ERROR",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=log_file,
    )
    handler = _get_rotating_handler()
    assert handler.level == logging.ERROR
    assert handler.formatter is not None
    assert handler.formatter._fmt == LOG_FORMAT
    assert handler.formatter.datefmt == LOG_DATE_FORMAT


def test_file_handler_logs_success_message(tmp_path, capfd):
    log_file = str(tmp_path / "app.log")
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=log_file,
    )
    captured = capfd.readouterr()
    assert f"File logging enabled: {log_file}" in captured.err


# --- Error handling ---


def test_file_handler_failure_falls_back_to_console(mocker, tmp_path):
    mocker.patch(
        "src.logger.logging.handlers.RotatingFileHandler",
        side_effect=PermissionError("no access"),
    )
    log_file = str(tmp_path / "app.log")
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=log_file,
    )

    handlers = logging.getLogger().handlers
    assert len(handlers) == 1
    assert type(handlers[0]) is logging.StreamHandler


def test_file_handler_failure_logs_error(mocker, tmp_path, capfd):
    mocker.patch(
        "src.logger.logging.handlers.RotatingFileHandler",
        side_effect=PermissionError("no access"),
    )
    log_file = str(tmp_path / "app.log")
    setup_logging(
        log_level="INFO",
        log_format=LOG_FORMAT,
        log_date_format=LOG_DATE_FORMAT,
        log_file=log_file,
    )

    captured = capfd.readouterr()
    assert "Failed to setup file logging" in captured.err
