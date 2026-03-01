import time

from tests.test_vinted_network_client.helpers import make_proxy_stats


class TestDefaults:
    def test_last_used_none(self):
        stats = make_proxy_stats()
        assert stats.last_used is None

    def test_last_failed_none(self):
        stats = make_proxy_stats()
        assert stats.last_failed is None

    def test_is_banned_false(self):
        stats = make_proxy_stats()
        assert stats.is_banned is False


class TestMarkSuccess:
    def test_sets_last_used(self):
        stats = make_proxy_stats()
        before = time.time()
        stats.mark_success()
        assert stats.last_used is not None
        assert stats.last_used >= before

    def test_clears_is_banned(self):
        stats = make_proxy_stats()
        stats.is_banned = True
        stats.mark_success()
        assert stats.is_banned is False

    def test_does_not_change_last_failed(self):
        stats = make_proxy_stats()
        stats.last_failed = 999.0
        stats.mark_success()
        assert stats.last_failed == 999.0


class TestMarkFailure:
    def test_sets_last_failed(self):
        stats = make_proxy_stats()
        before = time.time()
        stats.mark_failure()
        assert stats.last_failed is not None
        assert stats.last_failed >= before

    def test_sets_is_banned(self):
        stats = make_proxy_stats()
        stats.mark_failure()
        assert stats.is_banned is True

    def test_does_not_change_last_used(self):
        stats = make_proxy_stats()
        stats.last_used = 999.0
        stats.mark_failure()
        assert stats.last_used == 999.0


class TestRecoverySequence:
    def test_clears_banned_and_updates_last_used(self):
        stats = make_proxy_stats()
        stats.mark_failure()
        assert stats.is_banned is True
        failed_time = stats.last_failed

        stats.mark_success()
        assert stats.is_banned is False
        assert stats.last_used is not None
        assert stats.last_failed == failed_time


class TestMultipleConsecutiveCalls:
    def test_multiple_success_updates_last_used(self):
        stats = make_proxy_stats()
        stats.mark_success()
        first_used = stats.last_used
        assert first_used is not None
        time.sleep(0.01)
        stats.mark_success()
        assert stats.last_used is not None
        assert stats.last_used >= first_used
