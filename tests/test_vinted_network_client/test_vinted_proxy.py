import pytest

from src.vinted_network_client.models.vinted_proxy import VintedProxy


# ============================================================================
# scheme
# ============================================================================


def test_scheme_https():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username="u", password="p", is_https=True
    )
    assert proxy.scheme == "https"


def test_scheme_http():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=False
    )
    assert proxy.scheme == "http"


# ============================================================================
# to_str_proxy()
# ============================================================================


@pytest.mark.parametrize("is_https,expected_scheme", [(True, "https"), (False, "http")])
def test_to_str_proxy_with_credentials(is_https, expected_scheme):
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username="user", password="pass", is_https=is_https
    )
    assert proxy.to_str_proxy() == f"{expected_scheme}://user:pass@1.2.3.4:8080"


@pytest.mark.parametrize("is_https,expected_scheme", [(True, "https"), (False, "http")])
def test_to_str_proxy_without_credentials(is_https, expected_scheme):
    proxy = VintedProxy(
        ip="5.6.7.8", port="3128", username=None, password=None, is_https=is_https
    )
    assert proxy.to_str_proxy() == f"{expected_scheme}://5.6.7.8:3128"


# ============================================================================
# __str__ / __repr__
# ============================================================================


def test_str_with_credentials():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username="user", password="pass", is_https=True
    )
    result = str(proxy)
    assert "user:pass" in result
    assert "1.2.3.4:8080" in result
    assert "HTTPS: True" in result


def test_str_without_credentials():
    proxy = VintedProxy(
        ip="5.6.7.8", port="3128", username=None, password=None, is_https=False
    )
    result = str(proxy)
    assert "5.6.7.8:3128" in result
    assert "HTTPS: False" in result


def test_repr():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username="user", password="pass", is_https=True
    )
    result = repr(proxy)
    assert "VintedProxy" in result
    assert "1.2.3.4" in result


# ============================================================================
# Frozen behavior
# ============================================================================


def test_raises_on_attribute_set():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
    )
    with pytest.raises(AttributeError):
        proxy.ip = "9.9.9.9"  # type: ignore[misc]


def test_equality_by_values():
    a = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
    )
    b = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
    )
    assert a == b


def test_hashable():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
    )
    assert hash(proxy) is not None
    assert {proxy}  # can be used in sets


def test_inequality_by_different_values():
    a = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
    )
    b = VintedProxy(
        ip="5.6.7.8", port="3128", username=None, password=None, is_https=False
    )
    assert a != b


def test_hash_consistency_between_equal_objects():
    a = VintedProxy(
        ip="1.2.3.4", port="8080", username="u", password="p", is_https=True
    )
    b = VintedProxy(
        ip="1.2.3.4", port="8080", username="u", password="p", is_https=True
    )
    assert a == b
    assert hash(a) == hash(b)


# ============================================================================
# Partial credentials
# ============================================================================


def test_to_str_proxy_username_only_no_credentials_format():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username="user", password=None, is_https=True
    )
    assert proxy.to_str_proxy() == "https://1.2.3.4:8080"


def test_to_str_proxy_password_only_no_credentials_format():
    proxy = VintedProxy(
        ip="1.2.3.4", port="8080", username=None, password="pass", is_https=True
    )
    assert proxy.to_str_proxy() == "https://1.2.3.4:8080"
