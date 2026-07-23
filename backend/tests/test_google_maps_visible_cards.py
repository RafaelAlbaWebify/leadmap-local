import pytest

from backend.leadmap.browser.google_maps import (
    VisiblePageUnsupported,
    _coordinates_from_url,
    capture_visible_google_maps_cards,
)


class UnsupportedPage:
    url = "https://example.com/"


def test_extracts_coordinates_from_google_maps_url() -> None:
    assert _coordinates_from_url("https://www.google.com/maps/place/Test/@53.2707,-9.0568,17z") == (
        "53.2707",
        "-9.0568",
    )


def test_coordinates_are_optional() -> None:
    assert _coordinates_from_url(None) == (None, None)
    assert _coordinates_from_url("https://www.google.com/maps/place/Test") == (
        None,
        None,
    )


def test_rejects_unsupported_page_without_dom_access() -> None:
    with pytest.raises(VisiblePageUnsupported, match="supported Google Maps"):
        capture_visible_google_maps_cards(UnsupportedPage(), max_results=10)


def test_rejects_invalid_capture_limit() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        capture_visible_google_maps_cards(UnsupportedPage(), max_results=0)
