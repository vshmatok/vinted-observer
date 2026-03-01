from src.vinted_network_client.models.vinted_media import VintedMedia


# ============================================================================
# __init__
# ============================================================================


def test_full_json():
    media = VintedMedia({"type": "thumb", "url": "https://img.vinted.net/thumb.jpg"})
    assert media.type == "thumb"
    assert media.url == "https://img.vinted.net/thumb.jpg"


def test_none_input():
    media = VintedMedia(None)
    assert media.type is None
    assert media.url is None


def test_no_args():
    media = VintedMedia()
    assert media.type is None
    assert media.url is None


def test_non_dict_input():
    media = VintedMedia("not a dict")
    assert media.type is None
    assert media.url is None


# ============================================================================
# __str__
# ============================================================================


def test_str_with_type_and_url():
    media = VintedMedia({"type": "thumb", "url": "https://img.vinted.net/thumb.jpg"})
    assert str(media) == "thumb: https://img.vinted.net/thumb.jpg"


def test_str_url_only():
    media = VintedMedia({"url": "https://img.vinted.net/thumb.jpg"})
    assert str(media) == "https://img.vinted.net/thumb.jpg"


def test_str_empty():
    media = VintedMedia()
    assert str(media) == "VintedMedia(N/A)"


# ============================================================================
# __repr__
# ============================================================================


def test_repr_format():
    media = VintedMedia({"type": "thumb", "url": "https://img.vinted.net/thumb.jpg"})
    result = repr(media)
    assert "VintedMedia" in result
    assert "thumb" in result
    assert "https://img.vinted.net/thumb.jpg" in result


# ============================================================================
# __str__ edge cases
# ============================================================================


def test_str_type_only_no_url():
    media = VintedMedia({"type": "thumb"})
    assert str(media) == "VintedMedia(N/A)"


def test_missing_keys_in_dict():
    media = VintedMedia({"unrelated_key": "value"})
    assert media.type is None
    assert media.url is None
    assert str(media) == "VintedMedia(N/A)"
