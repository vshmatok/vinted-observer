import pytest
from src.monitoring.error_parser import ErrorParser

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LEVELS = ["ERROR", "CRITICAL"]


class TestParseLogLine:
    @pytest.mark.parametrize(
        "log_format, line, expected_fields",
        [
            (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "2026-02-19 10:00:00 - app - ERROR - msg",
                {
                    "asctime": "2026-02-19 10:00:00",
                    "name": "app",
                    "levelname": "ERROR",
                    "message": "msg",
                },
            ),
            (
                "%(levelname)s %(asctime)s %(message)s",
                "ERROR 2026-02-19 10:00:00 something failed",
                {
                    "levelname": "ERROR",
                    "asctime": "2026-02-19 10:00:00",
                    "message": "something failed",
                },
            ),
            (
                "%(asctime)s [%(process)d] %(levelname)s - %(message)s",
                "2026-02-19 10:00:00 [12345] ERROR - connection refused",
                {
                    "asctime": "2026-02-19 10:00:00",
                    "process": "12345",
                    "levelname": "ERROR",
                    "message": "connection refused",
                },
            ),
            (
                "%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s",
                "2026-02-19 10:00:00 handler.py:42 ERROR request failed",
                {
                    "asctime": "2026-02-19 10:00:00",
                    "filename": "handler.py",
                    "lineno": "42",
                    "levelname": "ERROR",
                    "message": "request failed",
                },
            ),
            (
                "%(asctime)s %(name)s %(module)s.%(funcName)s:%(lineno)d [%(levelname)s] %(message)s",
                "2026-02-19 10:00:00 myapp utils.process_data:99 [CRITICAL] unexpected null",
                {
                    "asctime": "2026-02-19 10:00:00",
                    "name": "myapp",
                    "module": "utils",
                    "funcName": "process_data",
                    "lineno": "99",
                    "levelname": "CRITICAL",
                    "message": "unexpected null",
                },
            ),
            (
                "[%(thread)d] %(pathname)s - %(levelname)s - %(message)s",
                "[98765] /src/monitoring/error_parser.py - WARNING - slow query",
                {
                    "thread": "98765",
                    "pathname": "/src/monitoring/error_parser.py",
                    "levelname": "WARNING",
                    "message": "slow query",
                },
            ),
        ],
    )
    def test_with_different_formats(self, log_format, line, expected_fields):
        parser = ErrorParser(
            max_count=10, path="", log_levels=DEFAULT_LEVELS, log_format=log_format
        )
        result = parser._parse_log_line(line)
        assert result is not None

        for field, value in expected_fields.items():
            assert result[field] == value

    async def test_malformed_line_returns_none(self):
        parser = ErrorParser(
            max_count=10, path="", log_levels=DEFAULT_LEVELS, log_format=DEFAULT_FORMAT
        )
        line = "this is not a valid log line"
        result = parser._parse_log_line(line)
        assert result is None


class TestGetRecentErrors:
    async def test_empty_path_returns_empty(self):
        parser = ErrorParser(
            max_count=10, path="", log_levels=DEFAULT_LEVELS, log_format=DEFAULT_FORMAT
        )
        assert await parser.get_recent_errors() == []

    async def test_nonexistent_file_returns_empty(self, tmp_path):
        non_existent_file = tmp_path / "no_such.log"
        parser = ErrorParser(
            max_count=10,
            path=str(non_existent_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        assert await parser.get_recent_errors() == []

    async def test_empty_log_file_returns_empty(self, empty_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(empty_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        assert await parser.get_recent_errors() == []

    async def test_filters_by_log_level(self, valid_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(valid_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert len(errors) == 2
        assert "ERROR" in errors[0]
        assert "CRITICAL" in errors[1]
        assert not any("INFO" in e for e in errors)

    async def test_returns_chronological_order(self, valid_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(valid_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert "10:00:02" in errors[0]
        assert "10:00:03" in errors[1]

    async def test_max_count_limits_results(self, valid_log_file):
        parser = ErrorParser(
            max_count=1,
            path=str(valid_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert len(errors) == 1
        assert "10:00:03" in errors[0]  # most recent error is kept

    async def test_malformed_lines_skipped(self, malformed_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(malformed_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert len(errors) == 1
        assert "Valid line among garbage" in errors[0]

    async def test_permission_error_returns_empty(self, permission_denied_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(permission_denied_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert errors == []

    async def test_tail_reading_discards_partial_first_line(self, large_log_file):
        """When file > 65KB, only the tail is read and the first (partial) line is discarded."""
        parser = ErrorParser(
            max_count=10,
            path=str(large_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert len(errors) == 1
        assert "should be found" in errors[0]

    async def test_critical_level(self, valid_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(valid_log_file),
            log_levels=["CRITICAL"],
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert len(errors) == 1
        assert "CRITICAL" in errors[0]

    async def test_generic_exception_returns_empty(self, mocker, valid_log_file):
        mocker.patch(
            "src.monitoring.error_parser.aiofiles.open",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
        )
        parser = ErrorParser(
            max_count=10,
            path=str(valid_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert errors == []

    async def test_special_chars_in_message(self, special_chars_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(special_chars_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert len(errors) == 3
        assert "failed - retry in 5s" in errors[0]
        assert "[a-z]+ and (group) failed" in errors[1]
        assert "München" in errors[2]

    @pytest.mark.parametrize("max_count", [0, -1, -100])
    async def test_non_positive_max_count_returns_empty(
        self, valid_log_file, max_count
    ):
        parser = ErrorParser(
            max_count=max_count,
            path=str(valid_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert errors == []  # max_count=0 should return no errors

    async def test_all_lines_are_errors(self, all_errors_log_file):
        parser = ErrorParser(
            max_count=10,
            path=str(all_errors_log_file),
            log_levels=DEFAULT_LEVELS,
            log_format=DEFAULT_FORMAT,
        )
        errors = await parser.get_recent_errors()
        assert len(errors) == 3
        assert "first" in errors[0]
        assert "third" in errors[2]
