import pytest

from src.vinted_network_client.models.vinted_user import VintedUser


class TestInit:
    def test_full_json(self):
        user = VintedUser(
            {
                "id": 99,
                "login": "seller123",
                "profile_url": "https://vinted.pl/member/99",
            }
        )
        assert user.id == 99
        assert user.login == "seller123"
        assert user.profile_url == "https://vinted.pl/member/99"

    def test_none_input(self):
        user = VintedUser(None)
        assert user.id is None
        assert user.login is None
        assert user.profile_url is None

    def test_no_args(self):
        user = VintedUser()
        assert user.id is None
        assert user.login is None

    def test_non_dict_input(self):
        user = VintedUser("not a dict")
        assert user.id is None
        assert user.login is None

    def test_id_as_int(self):
        user = VintedUser({"id": "42"})
        assert user.id == 42
        assert isinstance(user.id, int)

    def test_invalid_id(self):
        user = VintedUser({"id": "not_a_number"})
        assert user.id is None

    def test_missing_fields_default_none(self):
        user = VintedUser({})
        assert user.id is None
        assert user.login is None
        assert user.profile_url is None


class TestStr:
    def test_with_login(self):
        user = VintedUser({"id": 99, "login": "seller123"})
        assert str(user) == "@seller123"

    def test_with_id_only(self):
        user = VintedUser({"id": 42})
        assert str(user) == "User#42"

    def test_empty(self):
        user = VintedUser()
        assert str(user) == "VintedUser(N/A)"

    def test_with_id_zero(self):
        user = VintedUser({"id": 0})
        assert str(user) == "User#0"


class TestRepr:
    def test_format(self):
        user = VintedUser(
            {
                "id": 99,
                "login": "seller123",
                "profile_url": "https://vinted.pl/member/99",
            }
        )
        result = repr(user)
        assert "VintedUser" in result
        assert "99" in result
        assert "seller123" in result


class TestEquality:
    def test_equal_users(self):
        a = VintedUser({"id": 1, "login": "u1"})
        b = VintedUser({"id": 1, "login": "u1"})
        assert a == b

    def test_different_users_not_equal(self):
        a = VintedUser({"id": 1, "login": "u1"})
        b = VintedUser({"id": 2, "login": "u2"})
        assert a != b

    def test_unhashable(self):
        user = VintedUser({"id": 1})
        with pytest.raises(TypeError):
            hash(user)
