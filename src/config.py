import os
import json
import aiofiles
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from src.vinted_network_client.models.vinted_proxy import VintedProxy
from src.vinted_network_client.models.vinted_domain import VintedDomain

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Central configuration loader for the application."""

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Vinted
    domain_str = os.getenv("VINTED_DOMAIN", "PL")
    try:
        VINTED_DOMAIN: VintedDomain = VintedDomain[domain_str]
    except KeyError as e:
        valid_domains = ", ".join([d.name for d in VintedDomain])
        raise ValueError(
            f"Invalid VINTED_DOMAIN '{domain_str}'. " f"Valid options: {valid_domains}"
        )

    # Paths
    PROXY_CONFIG_PATH: str = os.getenv(
        "PROXY_CONFIG_PATH", "src/resources/proxies.json"
    )
    USER_AGENTS_PATH: str = os.getenv("USER_AGENTS_PATH", "src/resources/agents.json")

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "database.db")

    try:
        DB_CLEANUP_INTERVAL_HOURS: int = int(
            os.getenv("DB_CLEANUP_INTERVAL_HOURS", "24")
        )
        if DB_CLEANUP_INTERVAL_HOURS <= 0:
            raise ValueError("DB_CLEANUP_INTERVAL_HOURS must be positive")
    except ValueError as e:
        raise ValueError(f"Invalid DB_CLEANUP_INTERVAL_HOURS value: {e}")

    try:
        DB_LISTING_RETENTION_DAYS: int = int(
            os.getenv("DB_LISTING_RETENTION_DAYS", "1")
        )
        if DB_LISTING_RETENTION_DAYS <= 0:
            raise ValueError("DB_LISTING_RETENTION_DAYS must be positive")
    except ValueError as e:
        raise ValueError(f"Invalid DB_LISTING_RETENTION_DAYS value: {e}")

    try:
        DB_BUSY_TIMEOUT: int = int(os.getenv("DB_BUSY_TIMEOUT", "5000"))
        if DB_BUSY_TIMEOUT <= 0:
            raise ValueError("DB_BUSY_TIMEOUT must be positive")
    except ValueError as e:
        raise ValueError(f"Invalid DB_BUSY_TIMEOUT value: {e}")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    _VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if LOG_LEVEL.upper() not in _VALID_LOG_LEVELS:
        raise ValueError(
            f"Invalid LOG_LEVEL '{LOG_LEVEL}'. "
            f"Valid options: {', '.join(sorted(_VALID_LOG_LEVELS))}"
        )
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    LOG_DATE_FORMAT: str = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    LOG_FILE: str = os.getenv("LOG_FILE", "")  # Optional file logging

    # Status Command
    try:
        STATUS_ITEMS_TIMEFRAME_HOURS: int = int(
            os.getenv("STATUS_ITEMS_TIMEFRAME_HOURS", "1")
        )
        if STATUS_ITEMS_TIMEFRAME_HOURS < 0:
            raise ValueError("STATUS_ITEMS_TIMEFRAME_HOURS must be non-negative")
    except ValueError as e:
        raise ValueError(f"Invalid STATUS_ITEMS_TIMEFRAME_HOURS value: {e}")

    try:
        ERROR_FETCH_AMOUNT: int = int(os.getenv("ERROR_FETCH_AMOUNT", "10"))
        if ERROR_FETCH_AMOUNT <= 0:
            raise ValueError("ERROR_FETCH_AMOUNT must be positive")
    except ValueError as e:
        raise ValueError(f"Invalid ERROR_FETCH_AMOUNT value: {e}")

    # Search
    try:
        SEARCH_SLEEP_TIME: int = int(os.getenv("SEARCH_SLEEP_TIME", "1"))
        if SEARCH_SLEEP_TIME < 0:
            raise ValueError("SEARCH_SLEEP_TIME must be non-negative")
    except ValueError as e:
        raise ValueError(f"Invalid SEARCH_SLEEP_TIME value: {e}")

    @staticmethod
    def load_error_log_levels() -> List[str]:
        # Log levels to treat as errors (comma-separated)
        try:
            error_levels_str = os.getenv("ERROR_LOG_LEVELS", "ERROR,CRITICAL")
            ERROR_LOG_LEVELS: List[str] = [
                level.strip().upper()
                for level in error_levels_str.split(",")
                if level.strip()  # Filter out empty strings
            ]
        except ValueError as e:
            raise ValueError(f"Invalid ERROR_LOG_LEVELS value: {e}")

        if not ERROR_LOG_LEVELS:
            raise ValueError("ERROR_LOG_LEVELS cannot be empty")

        # Validate that all levels are valid Python logging levels
        VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        invalid_levels = [
            level for level in ERROR_LOG_LEVELS if level not in VALID_LOG_LEVELS
        ]
        if invalid_levels:
            raise ValueError(
                f"Invalid log levels in ERROR_LOG_LEVELS: {', '.join(invalid_levels)}. "
                f"Valid levels: {', '.join(sorted(VALID_LOG_LEVELS))}"
            )

        return ERROR_LOG_LEVELS

    @staticmethod
    async def load_proxies() -> Optional[List[VintedProxy]]:
        """Load proxy configuration from JSON file."""
        proxy_path = Path(Config.PROXY_CONFIG_PATH)
        if not proxy_path.exists():
            logger.info(
                f"Proxy configuration file not found: {Config.PROXY_CONFIG_PATH}"
            )
            return None

        try:
            async with aiofiles.open(proxy_path, "r", encoding="utf-8") as f:
                content = await f.read()
        except PermissionError as e:
            raise PermissionError(
                f"Permission denied reading proxy config file: {Config.PROXY_CONFIG_PATH}"
            ) from e
        except Exception as e:
            raise IOError(
                f"Error reading proxy config file: {Config.PROXY_CONFIG_PATH}"
            ) from e

        try:
            proxies = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in proxy config file: {Config.PROXY_CONFIG_PATH}. "
                f"Error: {e}"
            ) from e

        if not isinstance(proxies, list):
            raise ValueError("Proxy configuration must be a JSON array")

        proxy_list = []
        for i, proxy in enumerate(proxies):
            try:
                if not isinstance(proxy, dict):
                    raise ValueError(f"Proxy at index {i} must be an object")

                required_keys = ["ip", "port", "username", "password"]
                missing_keys = [key for key in required_keys if key not in proxy]
                if missing_keys:
                    raise ValueError(
                        f"Proxy at index {i} missing required keys: {', '.join(missing_keys)}"
                    )

                ip = proxy["ip"]
                port = proxy["port"]
                username = proxy["username"]
                password = proxy["password"]
                is_https = proxy.get("is_https", False)

                if not isinstance(ip, str) or not ip.strip():
                    raise ValueError(
                        f"Proxy at index {i}: 'ip' must be a non-empty string"
                    )

                if not isinstance(port, (str, int)):
                    raise ValueError(
                        f"Proxy at index {i}: 'port' must be a string or integer"
                    )
                port_str = str(port)
                if not port_str.isdigit() or not (1 <= int(port_str) <= 65535):
                    raise ValueError(
                        f"Proxy at index {i}: 'port' must be between 1 and 65535"
                    )

                if not isinstance(is_https, bool):
                    raise ValueError(
                        f"Proxy at index {i}: 'is_https' must be a boolean"
                    )

                proxy_list.append(
                    VintedProxy(
                        ip=ip.strip(),
                        port=port_str,
                        username=username,
                        password=password,
                        is_https=is_https,
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                logger.error(f"Error parsing proxy at index {i}: {e}")
                raise ValueError(
                    f"Invalid proxy configuration at index {i}: {e}"
                ) from e

        return len(proxy_list) > 0 and proxy_list or None

    @staticmethod
    async def load_user_agents() -> List[Dict[str, Any]]:
        """Load user agents from JSON file."""
        agents_path = Path(Config.USER_AGENTS_PATH)
        if not agents_path.exists():
            raise FileNotFoundError(
                f"User agents file not found: {Config.USER_AGENTS_PATH}"
            )

        try:
            async with aiofiles.open(agents_path, "r", encoding="utf-8") as f:
                content = await f.read()
        except PermissionError as e:
            raise PermissionError(
                f"Permission denied reading user agents file: {Config.USER_AGENTS_PATH}"
            ) from e
        except Exception as e:
            raise IOError(
                f"Error reading user agents file: {Config.USER_AGENTS_PATH}"
            ) from e

        try:
            agents = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in user agents file: {Config.USER_AGENTS_PATH}. "
                f"Error: {e}"
            ) from e

        if not isinstance(agents, list):
            raise ValueError("User agents must be a JSON array")

        if not agents:
            raise ValueError("User agents list cannot be empty")

        for i, agent in enumerate(agents):
            if not isinstance(agent, dict):
                raise ValueError(
                    f"User agent at index {i} must be an object, got {type(agent).__name__}"
                )

        return agents

    @staticmethod
    def validate():
        """Validate that all required configuration values are set."""
        errors = []

        if not Config.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is not set")

        if not Path(Config.USER_AGENTS_PATH).exists():
            errors.append(f"User agents file not found: {Config.USER_AGENTS_PATH}")

        if errors:
            raise ValueError(
                "Configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
