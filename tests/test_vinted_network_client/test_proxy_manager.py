import asyncio
import pytest

from src.vinted_network_client.models.vinted_proxy import VintedProxy
from src.vinted_network_client.utils.proxy_manager import ProxyManager


@pytest.fixture
def proxy_a():
    return VintedProxy(
        ip="1.1.1.1", port="8080", username=None, password=None, is_https=True
    )


@pytest.fixture
def proxy_b():
    return VintedProxy(
        ip="2.2.2.2", port="8080", username=None, password=None, is_https=True
    )


@pytest.fixture
def manager(proxy_a, proxy_b):
    return ProxyManager([proxy_a, proxy_b])


# ============================================================================
# Properties
# ============================================================================


async def test_proxies_returns_all(manager, proxy_a, proxy_b):
    await manager.mark_failure(proxy_a)
    assert set(manager.proxies) == {proxy_a, proxy_b}


def test_failed_proxies_initially_empty(manager):
    assert manager.failed_proxies == []


async def test_failed_proxies_includes_banned(manager, proxy_a):
    await manager.mark_failure(proxy_a)
    assert proxy_a in manager.failed_proxies


async def test_healthy_excludes_banned(manager, proxy_a, proxy_b):
    await manager.mark_failure(proxy_a)
    assert manager.healthy_proxies == [proxy_b]


# ============================================================================
# get_proxy()
# ============================================================================


async def test_returns_lru_never_used_first(manager, proxy_a):
    proxy = await manager.get_proxy()
    assert proxy == proxy_a


async def test_rotates_after_mark_success(manager, proxy_b):
    first = await manager.get_proxy()
    await manager.mark_success(first)
    second = await manager.get_proxy()
    assert second == proxy_b


async def test_skips_banned(manager, proxy_a, proxy_b):
    await manager.mark_failure(proxy_a)
    proxy = await manager.get_proxy()
    assert proxy == proxy_b


async def test_resets_all_bans_when_all_banned(manager, proxy_a, proxy_b):
    await manager.mark_failure(proxy_a)
    await manager.mark_failure(proxy_b)
    proxy = await manager.get_proxy()
    assert proxy in (proxy_a, proxy_b)
    assert manager.failed_proxies == []


async def test_works_with_single_proxy(proxy_a):
    mgr = ProxyManager([proxy_a])
    proxy = await mgr.get_proxy()
    assert proxy == proxy_a


# ============================================================================
# mark_success()
# ============================================================================


async def test_mark_success_updates_matching_proxy(manager, proxy_a):
    await manager.mark_success(proxy_a)
    # proxy_a should now have last_used set, so LRU picks proxy_b next
    proxy = await manager.get_proxy()
    assert proxy != proxy_a


async def test_mark_success_unknown_proxy_is_noop(manager):
    unknown = VintedProxy(
        ip="9.9.9.9", port="1234", username=None, password=None, is_https=True
    )
    await manager.mark_success(unknown)
    assert len(manager.proxies) == 2


# ============================================================================
# mark_failure()
# ============================================================================


async def test_mark_failure_updates_matching_proxy(manager, proxy_a):
    await manager.mark_failure(proxy_a)
    assert proxy_a in manager.failed_proxies


async def test_mark_failure_unknown_proxy_is_noop(manager):
    unknown = VintedProxy(
        ip="9.9.9.9", port="1234", username=None, password=None, is_https=True
    )
    await manager.mark_failure(unknown)
    assert manager.failed_proxies == []


# ============================================================================
# Concurrency
# ============================================================================


async def test_concurrent_get_proxy_no_error(manager):
    results = await asyncio.gather(*[manager.get_proxy() for _ in range(10)])
    assert len(results) == 10
    assert all(r is not None for r in results)


# ============================================================================
# Empty proxy list
# ============================================================================


async def test_empty_proxy_list_get_proxy_raises():
    mgr = ProxyManager([])
    with pytest.raises(IndexError):
        await mgr.get_proxy()


# ============================================================================
# Single proxy banned then get_proxy
# ============================================================================


async def test_single_proxy_banned_resets_and_returns(proxy_a):
    mgr = ProxyManager([proxy_a])
    await mgr.mark_failure(proxy_a)
    proxy = await mgr.get_proxy()
    assert proxy == proxy_a
    assert mgr.failed_proxies == []


# ============================================================================
# LRU ordering after ban reset
# ============================================================================


async def test_lru_ordering_preserved_after_ban_reset(manager, proxy_a, proxy_b):
    await manager.mark_success(proxy_a)
    await manager.mark_failure(proxy_a)
    await manager.mark_failure(proxy_b)
    # All banned, reset triggered on next get_proxy
    proxy = await manager.get_proxy()
    # proxy_b should come first (never used or used earlier)
    assert proxy == proxy_b
