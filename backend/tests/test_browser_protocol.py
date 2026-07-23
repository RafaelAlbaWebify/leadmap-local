import json

import pytest

from backend.leadmap.browser.protocol import (
    BrowserProtocolError,
    ProtocolRequest,
    ProtocolResponse,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)


def test_request_round_trip() -> None:
    request = ProtocolRequest(
        request_id="request-1",
        command="capture_visible",
        payload={"max_results": 10},
    )

    assert decode_request(encode_request(request)) == request


def test_response_round_trip() -> None:
    response = ProtocolResponse(
        request_id="request-1",
        ok=True,
        result={"candidates": []},
    )

    assert decode_response(
        encode_response(response), expected_request_id="request-1"
    ) == response


def test_rejects_mismatched_request_id() -> None:
    response = ProtocolResponse(request_id="other", ok=True, result={})

    with pytest.raises(BrowserProtocolError, match="request_id mismatch"):
        decode_response(encode_response(response), expected_request_id="request-1")


def test_rejects_malformed_and_wrong_version_messages() -> None:
    with pytest.raises(BrowserProtocolError, match="malformed JSON"):
        decode_request("not-json\n")

    message = json.dumps(
        {
            "protocol_version": 999,
            "request_id": "request-1",
            "command": "capture_visible",
            "payload": {},
        }
    )
    with pytest.raises(BrowserProtocolError, match="version mismatch"):
        decode_request(message)


def test_decodes_explicit_error_envelope() -> None:
    response = ProtocolResponse(
        request_id="request-1",
        ok=False,
        error_code="unsupported_page",
        error_message="Open Google Maps.",
    )

    decoded = decode_response(
        encode_response(response), expected_request_id="request-1"
    )

    assert decoded.ok is False
    assert decoded.error_code == "unsupported_page"
    assert decoded.error_message == "Open Google Maps."
