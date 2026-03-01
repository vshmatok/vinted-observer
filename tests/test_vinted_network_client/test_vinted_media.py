from src.vinted_network_client.models.vinted_media import VintedMedia


class TestInit:
    def test_full_json(self):
        media = VintedMedia(
            {"type": "thumb", "url": "https://img.vinted.net/thumb.jpg"}
        )
        assert media.type == "thumb"
        assert media.url == "https://img.vinted.net/thumb.jpg"

    def test_none_input(self):
        media = VintedMedia(None)
        assert media.type is None
        assert media.url is None

    def test_no_args(self):
        media = VintedMedia()
        assert media.type is None
        assert media.url is None

    def test_non_dict_input(self):
        media = VintedMedia("not a dict")
        assert media.type is None
        assert media.url is None


class TestStr:
    def test_with_type_and_url(self):
        media = VintedMedia(
            {"type": "thumb", "url": "https://img.vinted.net/thumb.jpg"}
        )
        assert str(media) == "thumb: https://img.vinted.net/thumb.jpg"

    def test_url_only(self):
        media = VintedMedia({"url": "https://img.vinted.net/thumb.jpg"})
        assert str(media) == "https://img.vinted.net/thumb.jpg"

    def test_empty(self):
        media = VintedMedia()
        assert str(media) == "VintedMedia(N/A)"

    def test_type_only_no_url(self):
        media = VintedMedia({"type": "thumb"})
        assert str(media) == "VintedMedia(N/A)"

    def test_missing_keys_in_dict(self):
        media = VintedMedia({"unrelated_key": "value"})
        assert media.type is None
        assert media.url is None
        assert str(media) == "VintedMedia(N/A)"


class TestRepr:
    def test_format(self):
        media = VintedMedia(
            {"type": "thumb", "url": "https://img.vinted.net/thumb.jpg"}
        )
        result = repr(media)
        assert "VintedMedia" in result
        assert "thumb" in result
        assert "https://img.vinted.net/thumb.jpg" in result
