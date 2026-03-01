import pytest

from src.vinted_network_client.models.vinted_user import VintedUser


# ============================================================================
# __init__
# ============================================================================


def test_full_json():
    user = VintedUser(
        {"id": 99, "login": "seller123", "profile_url": "https://vinted.pl/member/99"}
    )
    assert user.id == 99
    assert user.login == "seller123"
    assert user.profile_url == "https://vinted.pl/member/99"


def test_none_input():
    user = VintedUser(None)
    assert user.id is None
    assert user.login is None
    assert user.profile_url is None


def test_no_args():
    user = VintedUser()
    assert user.id is None
    assert user.login is None


def test_non_dict_input():
    user = VintedUser("not a dict")
    assert user.id is None
    assert user.login is None


def test_id_as_int():
    user = VintedUser({"id": "42"})
    assert user.id == 42
    assert isinstance(user.id, int)


def test_invalid_id():
    user = VintedUser({"id": "not_a_number"})
    assert user.id is None


def test_missing_fields_default_none():
    user = VintedUser({})
    assert user.id is None
    assert user.login is None
    assert user.profile_url is None


# ============================================================================
# __str__
# ============================================================================


def test_str_with_login():
    user = VintedUser({"id": 99, "login": "seller123"})
    assert str(user) == "@seller123"


def test_str_with_id_only():
    user = VintedUser({"id": 42})
    assert str(user) == "User#42"


def test_str_empty():
    user = VintedUser()
    assert str(user) == "VintedUser(N/A)"


# ============================================================================
# __repr__
# ============================================================================


def test_repr_format():
    user = VintedUser(
        {"id": 99, "login": "seller123", "profile_url": "https://vinted.pl/member/99"}
    )
    result = repr(user)
    assert "VintedUser" in result
    assert "99" in result
    assert "seller123" in result


# ============================================================================
# __str__ edge case - id=0
# ============================================================================


def test_str_with_id_zero():
    user = VintedUser({"id": 0})
    assert str(user) == "User#0"


# ============================================================================
# Equality and hash
# ============================================================================


def test_equal_users():
    a = VintedUser({"id": 1, "login": "u1"})
    b = VintedUser({"id": 1, "login": "u1"})
    assert a == b


def test_different_users_not_equal():
    a = VintedUser({"id": 1, "login": "u1"})
    b = VintedUser({"id": 2, "login": "u2"})
    assert a != b


def test_unhashable():
    user = VintedUser({"id": 1})
    with pytest.raises(TypeError):
        hash(user)
