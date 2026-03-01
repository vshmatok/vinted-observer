import pytest
from datetime import datetime, timezone

from src.vinted_network_client.exceptions.vinted_error import VintedError
from src.vinted_network_client.exceptions.vinted_cookie_request_error import (
    VintedCookieRequestError,
)
from src.vinted_network_client.exceptions.vinted_search_request_error import (
    VintedSearchRequestError,
)
from src.vinted_network_client.exceptions.vinted_setup_error import VintedSetupError
from src.vinted_network_client.exceptions.vinted_validation_error import (
    VintedValidationError,
)


# ============================================================================
# __init__
# ============================================================================


def test_message_stored():
    err = VintedError("test message")
    assert err.message == "test message"


def test_default_context_is_empty_dict():
    err = VintedError("msg")
    assert err.context == {}


def test_provided_context_stored():
    ctx = {"operation": "search"}
    err = VintedError("msg", context=ctx)
    assert err.message == "msg"
    assert err.context == ctx


def test_timestamp_is_utc():
    err = VintedError("msg")
    assert err.timestamp.tzinfo == timezone.utc
    assert (datetime.now(timezone.utc) - err.timestamp).total_seconds() < 2


def test_underlying_error_stored_and_sets_cause():
    cause = ValueError("root cause")
    err = VintedError("msg", underlying_error=cause)
    assert err.underlying_error is cause
    assert err.__cause__ is cause


def test_is_exception_subclass():
    err = VintedError("msg")
    assert isinstance(err, Exception)


@pytest.mark.parametrize(
    "cls",
    [
        VintedCookieRequestError,
        VintedSearchRequestError,
        VintedSetupError,
        VintedValidationError,
    ],
)
def test_subclass_catchable_as_vinted_error(cls):
    err = cls(message="test")
    assert isinstance(err, VintedError)


# ============================================================================
# to_dict()
# ============================================================================


def test_to_dict_contains_required_keys():
    err = VintedError("msg")
    d = err.to_dict()
    assert "error_type" in d
    assert "message" in d
    assert "context" in d
    assert "timestamp" in d
    assert "component" in d


def test_to_dict_error_type_matches_class_name_for_subclass():
    err = VintedSearchRequestError(message="search failed")
    assert err.to_dict()["error_type"] == "VintedSearchRequestError"


def test_to_dict_component_is_vinted_network_client():
    err = VintedError("msg")
    assert err.to_dict()["component"] == "vinted_network_client"


def test_to_dict_underlying_error_included_when_present():
    cause = ValueError("root")
    err = VintedError("msg", underlying_error=cause)
    d = err.to_dict()
    assert "underlying_error" in d
    assert d["underlying_error"]["type"] == "ValueError"


def test_to_dict_underlying_error_absent_when_none():
    err = VintedError("msg")
    assert "underlying_error" not in err.to_dict()


def test_to_dict_timestamp_is_iso_format():
    err = VintedError("msg")
    ts = err.to_dict()["timestamp"]
    datetime.fromisoformat(ts)


# ============================================================================
# get_error_chain()
# ============================================================================


def test_single_error_returns_self():
    err = VintedError("msg")
    chain = err.get_error_chain()
    assert chain == [err]


def test_two_level_chain():
    cause = ValueError("root")
    err = VintedError("msg", underlying_error=cause)
    chain = err.get_error_chain()
    assert len(chain) == 2
    assert chain[0] is err
    assert chain[1] is cause


def test_three_level_nested_chain():
    root = TypeError("deep root")
    mid = VintedError("mid", underlying_error=root)
    top = VintedError("top", underlying_error=mid)
    chain = top.get_error_chain()
    assert len(chain) == 3
    assert chain[0] is top
    assert chain[1] is mid
    assert chain[2] is root


# ============================================================================
# get_root_cause()
# ============================================================================


def test_returns_self_when_no_underlying():
    err = VintedError("msg")
    assert err.get_root_cause() is err


def test_returns_deepest_in_chain():
    root = TypeError("deep root")
    mid = VintedError("mid", underlying_error=root)
    top = VintedError("top", underlying_error=mid)
    assert top.get_root_cause() is root


# ============================================================================
# __str__
# ============================================================================


def test_str_contains_class_name_and_message():
    err = VintedError("something broke")
    result = str(err)
    assert "VintedError" in result
    assert "something broke" in result


def test_str_contains_context():
    err = VintedError("msg", context={"op": "search"})
    assert "search" in str(err)


def test_str_includes_caused_by_when_underlying():
    cause = ValueError("root")
    err = VintedError("msg", underlying_error=cause)
    assert "Caused by:" in str(err)
    assert "ValueError" in str(err)


def test_str_omits_caused_by_when_no_underlying():
    err = VintedError("msg")
    assert "Caused by:" not in str(err)


# ============================================================================
# get_error_chain() - __context__ fallback
# ============================================================================


def test_error_chain_follows_context_when_no_cause():
    root = ValueError("root cause")
    try:
        try:
            raise root
        except ValueError:
            raise RuntimeError("mid level")
    except RuntimeError as mid:
        err = VintedError("top", underlying_error=mid)
        chain = err.get_error_chain()
        assert len(chain) == 3
        assert chain[0] is err
        assert chain[1] is mid
        assert chain[2] is root


# ============================================================================
# to_dict() - underlying_error module field
# ============================================================================


def test_to_dict_underlying_error_includes_module():
    cause = ValueError("root")
    err = VintedError("msg", underlying_error=cause)
    d = err.to_dict()
    assert d["underlying_error"]["module"] == "builtins"
