from src.vinted_network_client.models.vinted_high_resolution import VintedHighResolution


# ============================================================================
# __init__
# ============================================================================


def test_full_json():
    hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
    assert hr.id == "hr_1"
    assert hr.timestamp == 1700000000


def test_none_input():
    hr = VintedHighResolution(None)
    assert hr.id is None
    assert hr.timestamp is None


def test_no_args():
    hr = VintedHighResolution()
    assert hr.id is None
    assert hr.timestamp is None


def test_non_dict_input():
    hr = VintedHighResolution("not a dict")
    assert hr.id is None
    assert hr.timestamp is None


def test_timestamp_as_int():
    hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
    assert isinstance(hr.timestamp, int)


def test_timestamp_from_string():
    hr = VintedHighResolution({"id": "hr_1", "timestamp": "1700000000"})
    assert hr.timestamp == 1700000000


def test_invalid_timestamp():
    hr = VintedHighResolution({"id": "hr_1", "timestamp": "not_a_number"})
    assert hr.timestamp is None


# ============================================================================
# __str__
# ============================================================================


def test_str_with_id_and_timestamp():
    hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
    assert "hr_1" in str(hr)
    assert "1700000000" in str(hr)


def test_str_id_only():
    hr = VintedHighResolution({"id": "hr_1"})
    assert "hr_1" in str(hr)


def test_str_empty():
    hr = VintedHighResolution()
    assert str(hr) == "VintedHighResolution(N/A)"


# ============================================================================
# __repr__
# ============================================================================


def test_repr_format():
    hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
    result = repr(hr)
    assert "VintedHighResolution" in result
    assert "hr_1" in result
    assert "1700000000" in result


# ============================================================================
# Edge cases
# ============================================================================


def test_timestamp_zero():
    hr = VintedHighResolution({"id": "hr_1", "timestamp": 0})
    assert hr.timestamp == 0


def test_id_as_integer():
    hr = VintedHighResolution({"id": 42, "timestamp": 1700000000})
    assert hr.id == 42
    assert isinstance(hr.id, int)
