import pytest

from src.vinted_network_client.models.vinted_proxy import VintedProxy


class TestScheme:
    def test_https(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username="u", password="p", is_https=True
        )
        assert proxy.scheme == "https"

    def test_http(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username=None, password=None, is_https=False
        )
        assert proxy.scheme == "http"


class TestToStrProxy:
    @pytest.mark.parametrize(
        "is_https,expected_scheme", [(True, "https"), (False, "http")]
    )
    def test_with_credentials(self, is_https, expected_scheme):
        proxy = VintedProxy(
            ip="1.2.3.4",
            port="8080",
            username="user",
            password="pass",
            is_https=is_https,
        )
        assert proxy.to_str_proxy() == f"{expected_scheme}://user:pass@1.2.3.4:8080"

    @pytest.mark.parametrize(
        "is_https,expected_scheme", [(True, "https"), (False, "http")]
    )
    def test_without_credentials(self, is_https, expected_scheme):
        proxy = VintedProxy(
            ip="5.6.7.8", port="3128", username=None, password=None, is_https=is_https
        )
        assert proxy.to_str_proxy() == f"{expected_scheme}://5.6.7.8:3128"


class TestStrRepr:
    def test_str_with_credentials(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username="user", password="pass", is_https=True
        )
        result = str(proxy)
        assert "user:pass" in result
        assert "1.2.3.4:8080" in result
        assert "HTTPS: True" in result

    def test_str_without_credentials(self):
        proxy = VintedProxy(
            ip="5.6.7.8", port="3128", username=None, password=None, is_https=False
        )
        result = str(proxy)
        assert "5.6.7.8:3128" in result
        assert "HTTPS: False" in result

    def test_repr(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username="user", password="pass", is_https=True
        )
        result = repr(proxy)
        assert "VintedProxy" in result
        assert "1.2.3.4" in result


class TestFrozenBehavior:
    def test_raises_on_attribute_set(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
        )
        with pytest.raises(AttributeError):
            proxy.ip = "9.9.9.9"  # type: ignore[misc]

    def test_equality_by_values(self):
        a = VintedProxy(
            ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
        )
        b = VintedProxy(
            ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
        )
        assert a == b

    def test_hashable(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
        )
        assert hash(proxy) is not None
        assert {proxy}  # can be used in sets

    def test_inequality_by_different_values(self):
        a = VintedProxy(
            ip="1.2.3.4", port="8080", username=None, password=None, is_https=True
        )
        b = VintedProxy(
            ip="5.6.7.8", port="3128", username=None, password=None, is_https=False
        )
        assert a != b

    def test_hash_consistency_between_equal_objects(self):
        a = VintedProxy(
            ip="1.2.3.4", port="8080", username="u", password="p", is_https=True
        )
        b = VintedProxy(
            ip="1.2.3.4", port="8080", username="u", password="p", is_https=True
        )
        assert a == b
        assert hash(a) == hash(b)


class TestPartialCredentials:
    def test_username_only_no_credentials_format(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username="user", password=None, is_https=True
        )
        assert proxy.to_str_proxy() == "https://1.2.3.4:8080"

    def test_password_only_no_credentials_format(self):
        proxy = VintedProxy(
            ip="1.2.3.4", port="8080", username=None, password="pass", is_https=True
        )
        assert proxy.to_str_proxy() == "https://1.2.3.4:8080"
