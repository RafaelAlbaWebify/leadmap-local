from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

_COORDINATES_RE = re.compile(r"/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


class VisiblePageUnsupported(RuntimeError):
    pass


class VisiblePageSelectorDrift(RuntimeError):
    pass


def _coordinates_from_url(url: str | None) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    match = _COORDINATES_RE.search(unquote(url))
    if match is None:
        return None, None
    return match.group(1), match.group(2)


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
        text = card.inner_text(timeout=2_000).strip()
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
