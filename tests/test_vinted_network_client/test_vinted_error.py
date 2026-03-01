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


class TestInit:
    def test_message_stored(self):
        err = VintedError("test message")
        assert err.message == "test message"

    def test_default_context_is_empty_dict(self):
        err = VintedError("msg")
        assert err.context == {}

    def test_provided_context_stored(self):
        ctx = {"operation": "search"}
        err = VintedError("msg", context=ctx)
        assert err.message == "msg"
        assert err.context == ctx

    def test_timestamp_is_utc(self):
        err = VintedError("msg")
        assert err.timestamp.tzinfo == timezone.utc
        assert (datetime.now(timezone.utc) - err.timestamp).total_seconds() < 2

    def test_underlying_error_stored_and_sets_cause(self):
        cause = ValueError("root cause")
        err = VintedError("msg", underlying_error=cause)
        assert err.underlying_error is cause
        assert err.__cause__ is cause

    def test_is_exception_subclass(self):
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
    def test_subclass_catchable_as_vinted_error(self, cls):
        err = cls(message="test")
        assert isinstance(err, VintedError)


class TestToDict:
    def test_contains_required_keys(self):
        err = VintedError("msg")
        d = err.to_dict()
        assert "error_type" in d
        assert "message" in d
        assert "context" in d
        assert "timestamp" in d
        assert "component" in d

    def test_error_type_matches_class_name_for_subclass(self):
        err = VintedSearchRequestError(message="search failed")
        assert err.to_dict()["error_type"] == "VintedSearchRequestError"

    def test_component_is_vinted_network_client(self):
        err = VintedError("msg")
        assert err.to_dict()["component"] == "vinted_network_client"

    def test_underlying_error_included_when_present(self):
        cause = ValueError("root")
        err = VintedError("msg", underlying_error=cause)
        d = err.to_dict()
        assert "underlying_error" in d
        assert d["underlying_error"]["type"] == "ValueError"

    def test_underlying_error_absent_when_none(self):
        err = VintedError("msg")
        assert "underlying_error" not in err.to_dict()

    def test_timestamp_is_iso_format(self):
        err = VintedError("msg")
        ts = err.to_dict()["timestamp"]
        datetime.fromisoformat(ts)

    def test_underlying_error_includes_module(self):
        cause = ValueError("root")
        err = VintedError("msg", underlying_error=cause)
        d = err.to_dict()
        assert d["underlying_error"]["module"] == "builtins"


class TestGetErrorChain:
    def test_single_error_returns_self(self):
        err = VintedError("msg")
        chain = err.get_error_chain()
        assert chain == [err]

    def test_two_level_chain(self):
        cause = ValueError("root")
        err = VintedError("msg", underlying_error=cause)
        chain = err.get_error_chain()
        assert len(chain) == 2
        assert chain[0] is err
        assert chain[1] is cause

    def test_three_level_nested_chain(self):
        root = TypeError("deep root")
        mid = VintedError("mid", underlying_error=root)
        top = VintedError("top", underlying_error=mid)
        chain = top.get_error_chain()
        assert len(chain) == 3
        assert chain[0] is top
        assert chain[1] is mid
        assert chain[2] is root

    def test_follows_context_when_no_cause(self):
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


class TestGetRootCause:
    def test_returns_self_when_no_underlying(self):
        err = VintedError("msg")
        assert err.get_root_cause() is err

    def test_returns_deepest_in_chain(self):
        root = TypeError("deep root")
        mid = VintedError("mid", underlying_error=root)
        top = VintedError("top", underlying_error=mid)
        assert top.get_root_cause() is root


class TestStr:
    def test_contains_class_name_and_message(self):
        err = VintedError("something broke")
        result = str(err)
        assert "VintedError" in result
        assert "something broke" in result

    def test_contains_context(self):
        err = VintedError("msg", context={"op": "search"})
        assert "search" in str(err)

    def test_includes_caused_by_when_underlying(self):
        cause = ValueError("root")
        err = VintedError("msg", underlying_error=cause)
        assert "Caused by:" in str(err)
        assert "ValueError" in str(err)

    def test_omits_caused_by_when_no_underlying(self):
        err = VintedError("msg")
        assert "Caused by:" not in str(err)
