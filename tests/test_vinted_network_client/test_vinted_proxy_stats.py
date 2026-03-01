import time

from src.vinted_network_client.models.vinted_proxy import VintedProxy
from src.vinted_network_client.models.vinted_proxy_stats import ProxyStats


def _make_stats():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
    )
    return ProxyStats(proxy=proxy)


# ============================================================================
# Defaults
# ============================================================================


def test_last_used_none():
    stats = _make_stats()
    assert stats.last_used is None


def test_last_failed_none():
    stats = _make_stats()
    assert stats.last_failed is None


def test_is_banned_false():
    stats = _make_stats()
    assert stats.is_banned is False


# ============================================================================
# mark_success()
# ============================================================================


def test_mark_success_sets_last_used():
    stats = _make_stats()
    before = time.time()
    stats.mark_success()
    assert stats.last_used is not None
    assert stats.last_used >= before


def test_mark_success_clears_is_banned():
    stats = _make_stats()
    stats.is_banned = True
    stats.mark_success()
    assert stats.is_banned is False


def test_mark_success_does_not_change_last_failed():
    stats = _make_stats()
    stats.last_failed = 999.0
    stats.mark_success()
    assert stats.last_failed == 999.0


# ============================================================================
# mark_failure()
# ============================================================================


def test_mark_failure_sets_last_failed():
    stats = _make_stats()
    before = time.time()
    stats.mark_failure()
    assert stats.last_failed is not None
    assert stats.last_failed >= before


def test_mark_failure_sets_is_banned():
    stats = _make_stats()
    stats.mark_failure()
    assert stats.is_banned is True


def test_mark_failure_does_not_change_last_used():
    stats = _make_stats()
    stats.last_used = 999.0
    stats.mark_failure()
    assert stats.last_used == 999.0


# ============================================================================
# Recovery sequence: failure then success
# ============================================================================


def test_recovery_clears_banned_and_updates_last_used():
    stats = _make_stats()
    stats.mark_failure()
    assert stats.is_banned is True
    failed_time = stats.last_failed

    stats.mark_success()
    assert stats.is_banned is False
    assert stats.last_used is not None
    assert stats.last_failed == failed_time


# ============================================================================
# Multiple consecutive calls
# ============================================================================


def test_multiple_success_updates_last_used():
    stats = _make_stats()
    stats.mark_success()
    first_used = stats.last_used
    assert first_used is not None
    time.sleep(0.01)
    stats.mark_success()
    assert stats.last_used is not None
    assert stats.last_used >= first_used
