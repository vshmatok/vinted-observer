import pytest

from src.vinted_network_client.models.vinted_image import VintedImage
from src.vinted_network_client.models.vinted_high_resolution import VintedHighResolution
from src.vinted_network_client.models.vinted_media import VintedMedia


class TestInit:
    def test_full_json(self):
        json_data = {
            "id": 1,
            "image_no": 2,
            "is_main": True,
            "is_suspicious": False,
            "is_hidden": False,
            "full_size_url": "https://images.vinted.net/full/12345.jpg",
            "high_resolution": {"id": "hr_1", "timestamp": 1700000000},
            "thumbnails": [
                {"type": "thumb", "url": "https://images.vinted.net/thumb.jpg"},
            ],
        }
        img = VintedImage(json_data)
        assert img.id == 1
        assert img.image_no == 2
        assert img.is_main is True
        assert img.is_suspicious is False
        assert img.is_hidden is False
        assert img.full_size_url == "https://images.vinted.net/full/12345.jpg"
        assert isinstance(img.high_resolution, VintedHighResolution)
        assert img.high_resolution.id == "hr_1"
        assert isinstance(img.thumbnails, list)
        assert len(img.thumbnails) == 1
        assert isinstance(img.thumbnails[0], VintedMedia)

    def test_none_input(self):
        img = VintedImage(None)
        assert img.id is None
        assert img.image_no is None
        assert img.high_resolution is None
        assert img.thumbnails is None

    def test_no_args(self):
        img = VintedImage()
        assert img.id is None
        assert img.thumbnails is None

    def test_non_dict_input(self):
        img = VintedImage("not a dict")
        assert img.id is None

    def test_id_as_int(self):
        img = VintedImage({"id": "42"})
        assert img.id == 42
        assert isinstance(img.id, int)

    def test_image_no_as_int(self):
        img = VintedImage({"image_no": "3"})
        assert img.image_no == 3
        assert isinstance(img.image_no, int)

    def test_invalid_high_resolution_non_dict(self):
        img = VintedImage({"high_resolution": "not a dict"})
        assert isinstance(img.high_resolution, VintedHighResolution)
        assert img.high_resolution.id is None

    def test_thumbnails_as_list(self):
        img = VintedImage({"thumbnails": [{"type": "a", "url": "http://a.com"}]})
        assert img.thumbnails is not None
        assert len(img.thumbnails) == 1

    def test_thumbnails_non_list(self):
        img = VintedImage({"thumbnails": "not a list"})
        assert img.thumbnails is None

    def test_thumbnails_invalid_items(self):
        img = VintedImage({"thumbnails": [None, 42]})
        assert isinstance(img.thumbnails, list)
        assert len(img.thumbnails) == 2

    def test_boolean_fields(self):
        img = VintedImage({"is_main": True, "is_suspicious": True, "is_hidden": True})
        assert img.is_main is True
        assert img.is_suspicious is True
        assert img.is_hidden is True

    def test_empty_thumbnails_list_stays_none(self):
        img = VintedImage({"thumbnails": []})
        assert img.thumbnails is None


class TestStr:
    def test_with_all_fields(self):
        img = VintedImage(
            {
                "id": 1,
                "image_no": 2,
                "is_main": True,
                "full_size_url": "https://images.vinted.net/full/12345.jpg",
            }
        )
        result = str(img)
        assert "id=1" in result
        assert "no=2" in result
        assert "main" in result

    def test_empty(self):
        img = VintedImage()
        assert str(img) == "VintedImage(N/A)"

    def test_with_id_zero(self):
        img = VintedImage({"id": 0})
        result = str(img)
        assert "id=0" in result


class TestRepr:
    def test_format(self):
        img = VintedImage({"id": 1, "image_no": 2})
        result = repr(img)
        assert "VintedImage" in result
        assert "1" in result
        assert "2" in result


class TestEquality:
    def test_unhashable(self):
        img = VintedImage({"id": 1})
        with pytest.raises(TypeError):
            hash(img)
