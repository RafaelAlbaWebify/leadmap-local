from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

_AT_COORDINATES_RE = re.compile(r"/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_DATA_COORDINATES_RE = re.compile(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)")
_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "ð", "î")


class VisiblePageUnsupported(RuntimeError):
    pass


class VisiblePageSelectorDrift(RuntimeError):
    pass


def _coordinates_from_url(url: str | None) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    decoded_url = unquote(url)
    for pattern in (_AT_COORDINATES_RE, _DATA_COORDINATES_RE):
        match = pattern.search(decoded_url)
        if match is not None:
            return match.group(1), match.group(2)
    return None, None


def _utf8_sequence_length(first_byte: int) -> int | None:
    if 0xC2 <= first_byte <= 0xDF:
        return 2
    if 0xE0 <= first_byte <= 0xEF:
        return 3
    if 0xF0 <= first_byte <= 0xF4:
        return 4
    return None


def _repair_mojibake(text: str) -> str:
    if not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text

    repaired: list[str] = []
    index = 0
    while index < len(text):
        character = text[index]
        code_point = ord(character)
        sequence_length = _utf8_sequence_length(code_point) if code_point <= 255 else None
        if sequence_length is None or index + sequence_length > len(text):
            repaired.append(character)
            index += 1
            continue

        candidate = text[index : index + sequence_length]
        if any(ord(part) > 255 for part in candidate):
            repaired.append(character)
            index += 1
            continue

        candidate_bytes = bytes(ord(part) for part in candidate)
        if not all(0x80 <= byte <= 0xBF for byte in candidate_bytes[1:]):
            repaired.append(character)
            index += 1
            continue

        try:
            decoded = candidate_bytes.decode("utf-8")
        except UnicodeDecodeError:
            repaired.append(character)
            index += 1
            continue

        original_markers = sum(candidate.count(marker) for marker in _MOJIBAKE_MARKERS)
        decoded_markers = sum(decoded.count(marker) for marker in _MOJIBAKE_MARKERS)
        if decoded_markers < original_markers:
            repaired.append(decoded)
            index += sequence_length
        else:
            repaired.append(character)
            index += 1

    return "".join(repaired)


def capture_visible_google_maps_cards(
    page: Any,
    *,
    max_results: int,
) -> list[dict[str, Any]]:
    if max_results < 1:
        raise ValueError("max_results must be at least 1.")
    if "google." not in page.url or "/maps" not in page.url:
        raise VisiblePageUnsupported(
            "Open a supported Google Maps results page in the visible browser and retry."
        )

    cards = page.locator('[role="feed"] [role="article"]')
    count = min(cards.count(), max_results)
    if count == 0:
        raise VisiblePageSelectorDrift(
            "No visible Google Maps result cards were found. Confirm the results panel is open "
            "and retry; the page structure may have changed."
        )

    captured: list[dict[str, Any]] = []
    for index in range(count):
        card = cards.nth(index)
        text = _repair_mojibake(card.inner_text(timeout=2_000).strip())
        links = card.locator("a[href]")
        source_url: str | None = None
        website: str | None = None
        provider_key: str | None = None
        for link_index in range(links.count()):
            href = links.nth(link_index).get_attribute("href")
            if not href:
                continue
            if "/maps/place/" in href and source_url is None:
                source_url = href
                provider_key = href
            elif href.startswith("http") and "google." not in href and website is None:
                website = href

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        displayed_name = lines[0] if lines else ""
        if not displayed_name:
            continue
        latitude, longitude = _coordinates_from_url(source_url)
        captured.append(
            {
                "candidate_id": "",
                "provider_key": provider_key or f"visible-card-{index}",
                "displayed_name": displayed_name,
                "normalized_name": "",
                "category": lines[1] if len(lines) > 1 else None,
                "address_text": None,
                "phone": None,
                "website": website,
                "source_url": source_url,
                "latitude": latitude,
                "longitude": longitude,
                "raw_evidence": text,
                "included": True,
            }
        )
    return captured
