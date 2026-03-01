import logging
import logging.handlers
from pathlib import Path


def setup_logging(
    log_level: str,
    log_format: str,
    log_date_format: str,
    log_file: str,
) -> logging.Logger:
    """
    Configure logging for the entire application.

    Sets up both console and optional file logging based on configuration.
    Should be called once at application startup.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=log_date_format)

    # Console handler - always enabled
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler - optional, only if log_file is configured
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Use RotatingFileHandler to prevent log files from growing too large
            # Max 10MB per file, keep 5 backup files
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(
                getattr(logging, log_level.upper(), logging.INFO)
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            root_logger.info(f"File logging enabled: {log_file}")
        except Exception as e:
            # If file logging fails, log to console but don't crash
            root_logger.error(f"Failed to setup file logging: {e}")

    return root_logger
