import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.leadmap.persistence.models import (
    BusinessLocationRecord,
    BusinessNoteRecord,
    BusinessRecord,
    ObservationRecord,
    SearchRunRecord,
    TerritoryRecord,
)


def seed_business_detail(session: Session) -> BusinessRecord:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    territory = TerritoryRecord(
        id="territory-kildare",
        name="Kildare County",
        country_code="IE",
        administrative_area="County Kildare",
        locality=None,
        created_at=now,
    )
    business = BusinessRecord(
        id="business-1",
        canonical_name="Kildare Accountancy",
        normalized_name="kildare accountancy",
        qualification_status="needs_review",
        created_at=now - timedelta(days=2),
        updated_at=now,
    )
    location = BusinessLocationRecord(
        id="location-1",
        business=business,
        locality="Kildare County",
        administrative_area="County Kildare",
        country_code="IE",
        postal_area=None,
        phone="+353 45 000 000",
        website="https://kildare-accountancy.example",
        latitude="53.16",
        longitude="-6.91",
        created_at=now - timedelta(days=2),
        updated_at=now,
    )
    first_run = SearchRunRecord(
        id="run-1",
        territory=territory,
        provider="google_maps",
        query_text="accountant in Kildare County, IE",
        status="completed",
        started_at=now - timedelta(days=2),
        completed_at=now - timedelta(days=2),
    )
    second_run = SearchRunRecord(
        id="run-2",
        territory=territory,
        provider="google_maps",
        query_text="tax advisor in Kildare County, IE",
        status="completed",
        started_at=now,
        completed_at=now,
    )
    first = ObservationRecord(
        id="observation-1",
        search_run=first_run,
        location=location,
        provider="google_maps",
        provider_key="place-1",
        displayed_name="Kildare Accountancy",
        category="Accountant",
        source_url="https://maps.example/place-1",
        observed_at=now - timedelta(days=2),
        raw_payload_json=json.dumps(
            {
                "candidate_id": "q1-place-1",
                "query_sequence": 1,
                "result_rank": 2,
                "first_seen_scroll_step": 0,
                "raw_evidence": "Kildare Accountancy · Accountant",
                "address_text": "Kildare County",
            }
        ),
    )
    second = ObservationRecord(
        id="observation-2",
        search_run=second_run,
        location=location,
        provider="google_maps",
        provider_key="place-1",
        displayed_name="Kildare Accountancy",
        category="Tax consultant",
        source_url="https://maps.example/place-1",
        observed_at=now,
        raw_payload_json="not-json",
    )
    session.add_all([territory, business, location, first_run, second_run, first, second])
    session.commit()
    return business


def observation_evidence(
    observations: list[ObservationRecord],
) -> list[tuple[str, str | None, datetime]]:
    return [(item.id, item.raw_payload_json, item.observed_at) for item in observations]


def test_business_detail_returns_locations_and_ordered_observations(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    response = client.get(f"/api/v1/businesses/{business.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_name"] == "Kildare Accountancy"
    assert payload["qualification_status"] == "needs_review"
    assert payload["freshness"] == "fresh"
    assert payload["locations"] == [
        {
            "id": "location-1",
            "locality": "Kildare County",
            "administrative_area": "County Kildare",
            "country_code": "IE",
            "postal_area": None,
            "phone": "+353 45 000 000",
            "website": "https://kildare-accountancy.example",
            "latitude": "53.16",
            "longitude": "-6.91",
            "created_at": "2026-07-23T12:00:00Z",
            "updated_at": "2026-07-25T12:00:00Z",
        }
    ]
    assert [item["id"] for item in payload["observations"]] == [
        "observation-2",
        "observation-1",
    ]
    assert payload["observations"][0]["query_sequence"] is None
    assert payload["observations"][1] == {
        "id": "observation-1",
        "location_id": "location-1",
        "provider": "google_maps",
        "provider_key": "place-1",
        "displayed_name": "Kildare Accountancy",
        "category": "Accountant",
        "source_url": "https://maps.example/place-1",
        "observed_at": "2026-07-23T12:00:00Z",
        "query_text": "accountant in Kildare County, IE",
        "search_run_status": "completed",
        "query_sequence": 1,
        "result_rank": 2,
        "first_seen_scroll_step": 0,
        "candidate_id": "q1-place-1",
        "raw_evidence": "Kildare Accountancy · Accountant",
        "address_text": "Kildare County",
    }


def test_business_qualification_update_preserves_observations(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)
    before_observations = list(
        db_session.scalars(select(ObservationRecord).order_by(ObservationRecord.id))
    )
    before_payloads = observation_evidence(before_observations)

    response = client.patch(
        f"/api/v1/businesses/{business.id}/qualification",
        json={"qualification_status": "qualified"},
    )

    assert response.status_code == 200
    assert response.json()["qualification_status"] == "qualified"
    db_session.refresh(business)
    assert business.qualification_status == "qualified"
    after_observations = list(
        db_session.scalars(select(ObservationRecord).order_by(ObservationRecord.id))
    )
    assert observation_evidence(after_observations) == before_payloads


def test_business_qualification_rejects_unknown_status(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    response = client.patch(
        f"/api/v1/businesses/{business.id}/qualification",
        json={"qualification_status": "contacted"},
    )

    assert response.status_code == 422
    db_session.refresh(business)
    assert business.qualification_status == "needs_review"


def test_business_qualification_returns_404_for_unknown_business(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/businesses/missing/qualification",
        json={"qualification_status": "qualified"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Business not found."}


def test_business_notes_are_created_trimmed_and_listed_newest_first(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)
    older = BusinessNoteRecord(
        id="note-older",
        business_id=business.id,
        content="Older context",
        created_at=datetime(2026, 7, 24, 9, 0, tzinfo=UTC),
    )
    db_session.add(older)
    db_session.commit()

    create_response = client.post(
        f"/api/v1/businesses/{business.id}/notes",
        json={"content": "  Follow up after qualification review.  "},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["business_id"] == business.id
    assert created["content"] == "Follow up after qualification review."

    list_response = client.get(f"/api/v1/businesses/{business.id}/notes")
    assert list_response.status_code == 200
    notes = list_response.json()
    assert [note["content"] for note in notes] == [
        "Follow up after qualification review.",
        "Older context",
    ]


def test_business_note_creation_preserves_observations(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)
    before = observation_evidence(
        list(db_session.scalars(select(ObservationRecord).order_by(ObservationRecord.id)))
    )

    response = client.post(
        f"/api/v1/businesses/{business.id}/notes",
        json={"content": "Evidence reviewed manually."},
    )

    assert response.status_code == 201
    after = observation_evidence(
        list(db_session.scalars(select(ObservationRecord).order_by(ObservationRecord.id)))
    )
    assert after == before


def test_business_note_rejects_blank_and_oversized_content(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    blank = client.post(
        f"/api/v1/businesses/{business.id}/notes",
        json={"content": "   \n\t  "},
    )
    oversized = client.post(
        f"/api/v1/businesses/{business.id}/notes",
        json={"content": "x" * 4001},
    )

    assert blank.status_code == 422
    assert oversized.status_code == 422
    assert list(db_session.scalars(select(BusinessNoteRecord))) == []


def test_business_notes_return_404_for_unknown_business(client: TestClient) -> None:
    list_response = client.get("/api/v1/businesses/missing/notes")
    create_response = client.post(
        "/api/v1/businesses/missing/notes",
        json={"content": "Not persisted"},
    )

    assert list_response.status_code == 404
    assert create_response.status_code == 404
    assert list_response.json() == {"detail": "Business not found."}
    assert create_response.json() == {"detail": "Business not found."}


def test_business_detail_returns_404_for_unknown_business(client: TestClient) -> None:
    response = client.get("/api/v1/businesses/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Business not found."}
