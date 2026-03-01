from src.vinted_network_client.models.vinted_high_resolution import VintedHighResolution


class TestInit:
    def test_full_json(self):
        hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
        assert hr.id == "hr_1"
        assert hr.timestamp == 1700000000

    def test_none_input(self):
        hr = VintedHighResolution(None)
        assert hr.id is None
        assert hr.timestamp is None

    def test_no_args(self):
        hr = VintedHighResolution()
        assert hr.id is None
        assert hr.timestamp is None

    def test_non_dict_input(self):
        hr = VintedHighResolution("not a dict")
        assert hr.id is None
        assert hr.timestamp is None

    def test_timestamp_as_int(self):
        hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
        assert isinstance(hr.timestamp, int)

    def test_timestamp_from_string(self):
        hr = VintedHighResolution({"id": "hr_1", "timestamp": "1700000000"})
        assert hr.timestamp == 1700000000

    def test_invalid_timestamp(self):
        hr = VintedHighResolution({"id": "hr_1", "timestamp": "not_a_number"})
        assert hr.timestamp is None


class TestStr:
    def test_with_id_and_timestamp(self):
        hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
        assert "hr_1" in str(hr)
        assert "1700000000" in str(hr)

    def test_id_only(self):
        hr = VintedHighResolution({"id": "hr_1"})
        assert "hr_1" in str(hr)

    def test_empty(self):
        hr = VintedHighResolution()
        assert str(hr) == "VintedHighResolution(N/A)"


class TestRepr:
    def test_format(self):
        hr = VintedHighResolution({"id": "hr_1", "timestamp": 1700000000})
        result = repr(hr)
        assert "VintedHighResolution" in result
        assert "hr_1" in result
        assert "1700000000" in result

    def test_timestamp_zero(self):
        hr = VintedHighResolution({"id": "hr_1", "timestamp": 0})
        assert hr.timestamp == 0

    def test_id_as_integer(self):
        hr = VintedHighResolution({"id": 42, "timestamp": 1700000000})
        assert hr.id == 42
        assert isinstance(hr.id, int)
