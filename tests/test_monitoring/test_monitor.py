import pytest
from datetime import datetime
from unittest.mock import MagicMock
from src.monitoring.monitor import Monitor
from src.message_bus.queries.get_recent_found_items_query import (
    GetRecentFoundItemsQuery,
)
from src.message_bus.queries.get_status_report_query import GetStatusReportQuery


# ============================================================================
# _get_uptime_report tests
# ============================================================================


@pytest.mark.parametrize(
    "startup_time, now, expected",
    [
        (
            datetime(2026, 2, 20, 7, 30, 0),
            datetime(2026, 2, 21, 10, 0, 0),
            "⏰ Uptime: 1d 2h 30m",
        ),
        (
            datetime(2026, 2, 21, 6, 45, 0),
            datetime(2026, 2, 21, 10, 0, 0),
            "⏰ Uptime: 3h 15m",
        ),
        (
            datetime(2026, 2, 21, 9, 55, 0),
            datetime(2026, 2, 21, 10, 0, 0),
            "⏰ Uptime: 5m",
        ),
        (
            datetime(2026, 2, 21, 10, 0, 0),
            datetime(2026, 2, 21, 10, 0, 0),
            "⏰ Uptime: 0m",
        ),
        (
            datetime(2026, 2, 19, 9, 50, 0),
            datetime(2026, 2, 21, 10, 0, 0),
            "⏰ Uptime: 2d 0h 10m",
        ),
    ],
)
def test_uptime_formatting(
    mocker, mock_message_bus, mock_error_parser, startup_time, now, expected
):
    mock_dt = mocker.patch("src.monitoring.monitor.datetime", wraps=datetime)
    mock_dt.now.return_value = now

    mon = Monitor(
        message_bus=mock_message_bus,
        proxy_manager=None,
        startup_time=startup_time,
        error_parser=mock_error_parser,
        status_items_timeframe_hours=1,
    )
    assert mon._get_uptime_report() == expected


def test_uptime_startup_in_future(mocker, monitor):
    mock_dt = mocker.patch("src.monitoring.monitor.datetime", wraps=datetime)
    mock_dt.now.return_value = datetime(2026, 2, 21, 9, 0, 0)

    result = monitor._get_uptime_report()
    assert result == "⏰ Uptime: Error calculating"


def test_uptime_datetime_now_raises(mocker, monitor):
    mock_dt = mocker.patch("src.monitoring.monitor.datetime", wraps=datetime)
    mock_dt.now.side_effect = Exception("clock error")

    result = monitor._get_uptime_report()
    assert result == "⏰ Uptime: Error calculating"


# ============================================================================
# _get_recent_items_report tests
# ============================================================================


async def test_recent_items_uses_configured_hours(monitor, mock_message_bus):
    mock_message_bus.query.return_value = []

    await monitor._get_recent_items_report()
    mock_message_bus.query.assert_called_once()
    query_arg = mock_message_bus.query.call_args[0][0]
    assert isinstance(query_arg, GetRecentFoundItemsQuery)
    assert query_arg.hours == 1


async def test_recent_items_different_timeframe(
    mock_message_bus,
    mock_error_parser,
):
    mon = Monitor(
        message_bus=mock_message_bus,
        proxy_manager=None,
        startup_time=datetime(2026, 2, 21, 10, 0, 0),
        error_parser=mock_error_parser,
        status_items_timeframe_hours=24,
    )
    mock_message_bus.query.return_value = []

    result = await mon._get_recent_items_report()
    assert "(last 24h): 0 items" in result

    mock_message_bus.query.assert_called_once()
    query_arg = mock_message_bus.query.call_args[0][0]
    assert query_arg.hours == 24


async def test_recent_items_with_results(monitor, mock_message_bus):
    mock_message_bus.query.return_value = [
        {"search_id": 1, "query": "nike shoes", "item_count": 5},
        {"search_id": 2, "query": "adidas jacket", "item_count": 3},
    ]

    result = await monitor._get_recent_items_report()
    assert "📦 Items found (last 1h):" in result
    assert 'Search #1 "nike shoes": 5 items' in result
    assert 'Search #2 "adidas jacket": 3 items' in result
    assert "Total: 8 items" in result

    nike_pos = result.index("nike shoes")
    adidas_pos = result.index("adidas jacket")
    total_pos = result.index("Total:")
    assert nike_pos < adidas_pos < total_pos


async def test_recent_items_empty(monitor, mock_message_bus):
    mock_message_bus.query.return_value = []

    result = await monitor._get_recent_items_report()
    assert "(last 1h): 0 items" in result


async def test_recent_items_none(monitor, mock_message_bus):
    mock_message_bus.query.return_value = None

    result = await monitor._get_recent_items_report()
    assert "(last 1h): 0 items" in result


async def test_recent_items_single_result(monitor, mock_message_bus):
    mock_message_bus.query.return_value = [
        {"search_id": 1, "query": "nike shoes", "item_count": 5},
    ]

    result = await monitor._get_recent_items_report()
    assert "📦 Items found (last 1h):" in result
    assert 'Search #1 "nike shoes": 5 items' in result
    assert "Total: 5 items" in result


async def test_recent_items_zero_count(monitor, mock_message_bus):
    mock_message_bus.query.return_value = [
        {"search_id": 1, "query": "nike shoes", "item_count": 0},
        {"search_id": 2, "query": "adidas jacket", "item_count": 3},
    ]

    result = await monitor._get_recent_items_report()
    assert 'Search #1 "nike shoes": 0 items' in result
    assert "Total: 3 items" in result


async def test_recent_items_query_with_html_characters_is_escaped(
    monitor, mock_message_bus
):
    mock_message_bus.query.return_value = [
        {"search_id": 1, "query": '<script>alert("xss")</script>', "item_count": 3},
    ]

    result = await monitor._get_recent_items_report()
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "3 items" in result


async def test_recent_items_query_exception(monitor, mock_message_bus):
    mock_message_bus.query.side_effect = Exception("db error")

    result = await monitor._get_recent_items_report()
    assert "Error retrieving data" in result


# ============================================================================
# _get_proxy_report tests
# ============================================================================


def test_proxy_not_configured(monitor):
    result = monitor._get_proxy_report()
    assert result == "🔒 Proxies: Not configured"


def test_proxy_all_healthy(monitor_with_proxy, mock_proxy_manager):
    mock_proxy_manager.proxies = [MagicMock(), MagicMock(), MagicMock()]
    mock_proxy_manager.healthy_proxies = [MagicMock(), MagicMock(), MagicMock()]
    mock_proxy_manager.failed_proxies = []

    result = monitor_with_proxy._get_proxy_report()
    assert "3 configured" in result
    assert "3 healthy" in result
    assert "0 currently banned" in result


def test_proxy_some_banned(monitor_with_proxy, mock_proxy_manager):
    mock_proxy_manager.proxies = [MagicMock(), MagicMock(), MagicMock()]
    mock_proxy_manager.healthy_proxies = [MagicMock()]
    mock_proxy_manager.failed_proxies = [MagicMock(), MagicMock()]

    result = monitor_with_proxy._get_proxy_report()
    assert "3 configured" in result
    assert "1 healthy" in result
    assert "2 currently banned" in result


def test_proxy_all_banned(monitor_with_proxy, mock_proxy_manager):
    mock_proxy_manager.proxies = [MagicMock(), MagicMock()]
    mock_proxy_manager.healthy_proxies = []
    mock_proxy_manager.failed_proxies = [MagicMock(), MagicMock()]

    result = monitor_with_proxy._get_proxy_report()
    assert "2 configured" in result
    assert "0 healthy" in result
    assert "2 currently banned" in result


# ============================================================================
# _get_recent_errors_report tests
# ============================================================================


async def test_errors_with_results(monitor, mock_error_parser):
    mock_error_parser.get_recent_errors.return_value = [
        "2026-02-21 09:00:00 - app - ERROR - connection failed",
        "2026-02-21 09:30:00 - app - CRITICAL - out of memory",
    ]

    result = await monitor._get_recent_errors_report()
    assert "⚠️ Recent Errors (last 2):" in result
    assert "connection failed" in result
    assert "out of memory" in result


async def test_errors_empty(monitor, mock_error_parser):
    mock_error_parser.get_recent_errors.return_value = []

    result = await monitor._get_recent_errors_report()
    assert result == "⚠️ Recent Errors: None"


async def test_errors_exception(monitor, mock_error_parser):
    mock_error_parser.get_recent_errors.side_effect = Exception("parse failure")

    result = await monitor._get_recent_errors_report()
    assert "Error parsing logs" in result


# ============================================================================
# generate_status_report tests
# ============================================================================


async def test_full_report_structure(
    mocker, monitor, mock_message_bus, mock_error_parser
):
    mock_dt = mocker.patch("src.monitoring.monitor.datetime", wraps=datetime)
    mock_dt.now.return_value = datetime(2026, 2, 21, 12, 0, 0)

    mock_message_bus.query.return_value = [
        {"search_id": 1, "query": "shoes", "item_count": 10},
    ]
    mock_error_parser.get_recent_errors.return_value = [
        "2026-02-21 11:00:00 - app - ERROR - timeout",
    ]

    report = await monitor.generate_status_report(GetStatusReportQuery())

    assert "🤖 Bot Status: ✅ Running" in report
    assert "⏰ Uptime:" in report
    assert "📦 Items found" in report
    assert "🔒 Proxies:" in report
    assert "⚠️ Recent Errors" in report

    assert (
        report.index("🤖")
        < report.index("⏰")
        < report.index("📦")
        < report.index("🔒")
        < report.index("⚠️")
    )


async def test_full_report_with_all_errors(
    mocker, monitor, mock_message_bus, mock_error_parser
):
    mock_dt = mocker.patch("src.monitoring.monitor.datetime", wraps=datetime)
    mock_dt.now.side_effect = Exception("clock broken")

    mock_message_bus.query.side_effect = Exception("db down")
    mock_error_parser.get_recent_errors.side_effect = Exception("parse broken")

    report = await monitor.generate_status_report(GetStatusReportQuery())

    assert "🤖 Bot Status: ✅ Running" in report
    assert "⏰ Uptime: Error calculating" in report
    assert "Error retrieving data" in report
    assert "Error parsing logs" in report
