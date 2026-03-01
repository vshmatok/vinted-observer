import logging
import aiofiles
import re
from pathlib import Path
from typing import List, Optional, Dict, Pattern

logger = logging.getLogger(__name__)


class ErrorParser:
    """Parse log files to extract recent error entries."""

    def __init__(
        self,
        max_count: int,
        path: str,
        log_levels: List[str],
        log_format: str,
    ):
        self.max_count = max_count
        self.path = path
        self.log_levels = log_levels
        self.log_format = log_format
        self._log_pattern = self._build_log_pattern()

    async def get_recent_errors(self) -> List[str]:
        """
        Get the most recent error entries from the log file.
        Returns:
            List of formatted error strings with timestamp and message
        """

        if not self.path:
            logger.debug("No log file configured, cannot retrieve errors")
            return []

        log_path = Path(self.path)
        if not log_path.exists():
            logger.warning(f"Log file does not exist: {self.path}")
            return []

        if self.max_count <= 0:
            logger.debug("Max count is non-positive, returning empty error list")
            return []

        try:
            errors = []
            async with aiofiles.open(log_path, "r", encoding="utf-8") as f:
                # Read only the tail of the file to avoid loading large logs into memory
                await f.seek(0, 2)
                file_size = await f.tell()
                read_size = min(file_size, 65536)
                await f.seek(file_size - read_size)
                chunk = await f.read()
                lines = chunk.splitlines()

                # Discard first partial line if we didn't read from the start
                if read_size < file_size:
                    lines = lines[1:]

                # Parse lines in reverse to get most recent errors first
                for line in reversed(lines):
                    parsed = self._parse_log_line(line)
                    if parsed and parsed.get("levelname") in self.log_levels:
                        errors.append(line.strip())

                        if len(errors) >= self.max_count:
                            break

            # Reverse to show chronologically (oldest to newest)
            return list(reversed(errors))

        except PermissionError:
            logger.error(f"Permission denied reading log file: {self.path}")
            return []
        except Exception as e:
            logger.error(f"Failed to read log file {self.path}: {e}", exc_info=True)
            return []

    def _parse_log_line(self, line: str) -> Optional[Dict[str, str]]:
        """
        Parse a log line using the configured LOG_FORMAT.

        Args:
            line: Raw log line

        Returns:
            Dictionary with extracted fields or None if parsing fails
        """
        try:
            match = self._log_pattern.match(line.strip())
            if match:
                return match.groupdict()
            return None
        except Exception as e:
            logger.debug(f"Failed to parse log line: {e}", exc_info=True)
            return None

    def _build_log_pattern(self) -> Pattern:
        """
        Build a regex pattern from the LOG_FORMAT configuration.

        Returns:
            Compiled regex pattern
        """

        # Map of format placeholders to regex patterns
        format_to_regex = {
            "%(asctime)s": r"(?P<asctime>\S+\s+\S+)",  # Date and time
            "%(name)s": r"(?P<name>\S+)",  # Logger name
            "%(levelname)s": r"(?P<levelname>\w+)",  # Log level
            "%(message)s": r"(?P<message>.*)",  # Message (captures rest)
            "%(pathname)s": r"(?P<pathname>\S+)",
            "%(filename)s": r"(?P<filename>\S+)",
            "%(module)s": r"(?P<module>\S+)",
            "%(funcName)s": r"(?P<funcName>\S+)",
            "%(lineno)d": r"(?P<lineno>\d+)",
            "%(process)d": r"(?P<process>\d+)",
            "%(thread)d": r"(?P<thread>\d+)",
        }

        # Escape special regex characters in the format string
        pattern = re.escape(self.log_format)

        # Replace escaped format placeholders with regex patterns
        for placeholder, regex in format_to_regex.items():
            escaped_placeholder = re.escape(placeholder)
            if escaped_placeholder in pattern:
                # Replace the escaped placeholder with the regex pattern
                pattern = pattern.replace(escaped_placeholder, regex)

        try:
            return re.compile(pattern)
        except re.error as e:
            raise ValueError(
                f"Failed to build log pattern from format '{self.log_format}': {e}"
            ) from e
