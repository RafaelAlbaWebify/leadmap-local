from __future__ import annotations

import json
from io import StringIO
from typing import Any

import pytest

from backend.leadmap.browser.google_maps import (
    VisiblePageSelectorDrift,
    capture_visible_google_maps_cards,
)
from backend.leadmap.browser.protocol import (
    MAX_MESSAGE_BYTES,
    BrowserProtocolError,
    ProtocolRequest,
    ProtocolResponse,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
    write_message,
)


class FakeLink:
    def __init__(self, href: str | None) -> None:
        self._href = href

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self._href


class FakeLinks:
    def __init__(self, links: list[FakeLink]) -> None:
        self._links = links

    def count(self) -> int:
        return len(self._links)

    def nth(self, index: int) -> FakeLink:
        return self._links[index]


class FakeCard:
    def __init__(self, text: str, links: list[FakeLink]) -> None:
        self._text = text
        self._links = FakeLinks(links)

    def inner_text(self, *, timeout: int) -> str:
        assert timeout == 2_000
        return self._text

    def locator(self, selector: str) -> FakeLinks:
        assert selector == "a[href]"
        return self._links


class FakeCards:
    def __init__(self, cards: list[FakeCard]) -> None:
        self._cards = cards

    def count(self) -> int:
        return len(self._cards)

    def nth(self, index: int) -> FakeCard:
        return self._cards[index]


class FakePage:
    url = "https://www.google.com/maps/search/consultants"

    def __init__(self, cards: list[FakeCard]) -> None:
        self._cards = FakeCards(cards)

    def locator(self, selector: str) -> FakeCards:
        assert selector == '[role="feed"] [role="article"]'
        return self._cards


def test_captures_visible_google_maps_card_evidence() -> None:
    maps_url = "https://www.google.com/maps/place/Alpha/@53.2707,-9.0568,17z"
    page = FakePage(
        [
            FakeCard(
                "Alpha Consulting\nBusiness consultant\nOpen",
                [
                    FakeLink(None),
                    FakeLink(maps_url),
                    FakeLink("https://alpha.example/"),
                ],
            )
        ]
    )

    candidates = capture_visible_google_maps_cards(page, max_results=10)

    assert candidates == [
        {
            "candidate_id": "",
            "provider_key": maps_url,
            "displayed_name": "Alpha Consulting",
            "normalized_name": "",
            "category": "Business consultant",
            "address_text": None,
            "phone": None,
            "website": "https://alpha.example/",
            "source_url": maps_url,
            "latitude": "53.2707",
            "longitude": "-9.0568",
            "raw_evidence": ("Alpha Consulting\nBusiness consultant\nOpen"),
            "included": True,
        }
    ]


def test_capture_respects_limit_and_skips_blank_cards() -> None:
    page = FakePage(
        [
            FakeCard(" \n ", []),
            FakeCard("Second Business", []),
            FakeCard("Third Business", []),
        ]
    )

    candidates = capture_visible_google_maps_cards(page, max_results=2)

    assert len(candidates) == 1
    assert candidates[0]["displayed_name"] == "Second Business"
    assert candidates[0]["provider_key"] == "visible-card-1"


def test_capture_reports_selector_drift() -> None:
    with pytest.raises(
        VisiblePageSelectorDrift,
        match="No visible Google Maps result cards",
    ):
        capture_visible_google_maps_cards(FakePage([]), max_results=10)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (json.dumps([]), "JSON object"),
        (
            json.dumps(
                {
                    "protocol_version": 1,
                    "command": "capture_visible",
                    "payload": {},
                }
            ),
            "request_id",
        ),
        (
            json.dumps(
                {
                    "protocol_version": 1,
                    "request_id": "request-1",
                    "payload": {},
                }
            ),
            "command",
        ),
        (
            json.dumps(
                {
                    "protocol_version": 1,
                    "request_id": "request-1",
                    "command": "capture_visible",
                    "payload": [],
                }
            ),
            "payload",
        ),
    ],
)
def test_decode_request_rejects_invalid_envelopes(
    message: str,
    expected: str,
) -> None:
    with pytest.raises(BrowserProtocolError, match=expected):
        decode_request(message)


def test_protocol_rejects_oversized_input() -> None:
    oversized = "x" * (MAX_MESSAGE_BYTES + 1)

    with pytest.raises(BrowserProtocolError, match="size limit"):
        decode_request(oversized)


def test_decode_response_rejects_invalid_success_result() -> None:
    message = json.dumps(
        {
            "protocol_version": 1,
            "request_id": "request-1",
            "ok": True,
            "result": [],
        }
    )

    with pytest.raises(BrowserProtocolError, match="result"):
        decode_response(message, expected_request_id="request-1")


@pytest.mark.parametrize(
    "error_value",
    [
        None,
        [],
        {"code": 3, "message": "Failure"},
        {"code": "failure", "message": 3},
    ],
)
def test_decode_response_rejects_invalid_error_envelope(
    error_value: Any,
) -> None:
    value: dict[str, Any] = {
        "protocol_version": 1,
        "request_id": "request-1",
        "ok": False,
    }

    if error_value is not None:
        value["error"] = error_value

    with pytest.raises(BrowserProtocolError, match="error envelope"):
        decode_response(
            json.dumps(value),
            expected_request_id="request-1",
        )


def test_decode_response_requires_boolean_ok() -> None:
    message = json.dumps(
        {
            "protocol_version": 1,
            "request_id": "request-1",
            "ok": "yes",
        }
    )

    with pytest.raises(BrowserProtocolError, match="ok state"):
        decode_response(message, expected_request_id="request-1")


def test_protocol_defaults_success_and_error_payloads() -> None:
    success = ProtocolResponse(request_id="request-1", ok=True)
    error = ProtocolResponse(request_id="request-2", ok=False)

    decoded_success = decode_response(
        encode_response(success),
        expected_request_id="request-1",
    )
    decoded_error = decode_response(
        encode_response(error),
        expected_request_id="request-2",
    )

    assert decoded_success.result == {}
    assert decoded_error.error_code == "browser_error"
    assert decoded_error.error_message == "The browser command failed."


def test_write_message_flushes_text_stream() -> None:
    class RecordingStream(StringIO):
        flushed = False

        def flush(self) -> None:
            self.flushed = True
            super().flush()

    stream = RecordingStream()
    request = ProtocolRequest(
        request_id="request-1",
        command="capture_visible",
        payload={"max_results": 5},
    )

    write_message(stream, encode_request(request))

    assert stream.flushed is True
    assert '"request_id":"request-1"' in stream.getvalue()


def test_write_message_rejects_oversized_output() -> None:
    stream = StringIO()
    message = "x" * (MAX_MESSAGE_BYTES + 1)

    with pytest.raises(BrowserProtocolError, match="size limit"):
        write_message(stream, message)
