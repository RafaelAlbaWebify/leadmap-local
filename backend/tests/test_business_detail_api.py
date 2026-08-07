from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.leadmap.domain.enums import QualificationStatus
from backend.leadmap.persistence.models import ObservationRecord
from backend.tests.fixtures import observation_evidence, seed_business_detail


def test_get_business_detail_returns_persisted_locations_and_observations(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    response = client.get(f"/api/v1/businesses/{business.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_name"] == "Coffee Box Galway"
    assert payload["qualification_status"] == QualificationStatus.NEEDS_REVIEW
    assert payload["freshness"] == "fresh"
    assert len(payload["locations"]) == 1
    assert payload["locations"][0]["website"] == "https://coffeebox.example"
    assert len(payload["observations"]) == 2
    assert payload["observations"][0]["query_text"] == "cafes galway"
    assert payload["observations"][0]["query_sequence"] == 2
    assert payload["observations"][0]["result_rank"] == 3
    assert payload["observations"][0]["first_seen_scroll_step"] == 1
    assert payload["observations"][0]["candidate_id"] == "candidate-1"
    assert payload["observations"][0]["raw_evidence"] == "Rendered card evidence"
    assert payload["observations"][0]["address_text"] == "1 Shop Street"


def test_get_business_detail_returns_404_for_unknown_business(client: TestClient) -> None:
    response = client.get("/api/v1/businesses/missing")

    assert response.status_code == 404


def test_business_qualification_updates_status_without_changing_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)
    before_payloads = observation_evidence(
        db_session.scalars(select(ObservationRecord).order_by(ObservationRecord.id))
    )

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


def test_business_qualification_accepts_commercial_status(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    response = client.patch(
        f"/api/v1/businesses/{business.id}/qualification",
        json={"qualification_status": "sent_to_veridra"},
    )

    assert response.status_code == 200
    assert response.json()["qualification_status"] == "sent_to_veridra"
    db_session.refresh(business)
    assert business.qualification_status == "sent_to_veridra"


def test_business_qualification_rejects_unknown_status(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    response = client.patch(
        f"/api/v1/businesses/{business.id}/qualification",
        json={"qualification_status": "not_a_real_status"},
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


def test_business_notes_can_be_added_and_listed(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    created = client.post(
        f"/api/v1/businesses/{business.id}/notes",
        json={"content": "Strong local maintenance prospect."},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["business_id"] == business.id
    assert payload["content"] == "Strong local maintenance prospect."

    listed = client.get(f"/api/v1/businesses/{business.id}/notes")
    assert listed.status_code == 200
    assert [item["content"] for item in listed.json()] == ["Strong local maintenance prospect."]


def test_business_notes_reject_blank_or_long_content(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)

    blank = client.post(f"/api/v1/businesses/{business.id}/notes", json={"content": "   "})
    too_long = client.post(
        f"/api/v1/businesses/{business.id}/notes",
        json={"content": "x" * 4001},
    )

    assert blank.status_code == 422
    assert too_long.status_code == 422


def test_business_notes_returns_404_for_unknown_business(client: TestClient) -> None:
    response = client.post(
        "/api/v1/businesses/missing/notes",
        json={"content": "Follow up."},
    )

    assert response.status_code == 404


def test_business_notes_are_returned_newest_first(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)
    client.post(f"/api/v1/businesses/{business.id}/notes", json={"content": "First"})
    second = client.post(f"/api/v1/businesses/{business.id}/notes", json={"content": "Second"})
    assert second.status_code == 201

    notes = client.get(f"/api/v1/businesses/{business.id}/notes")

    assert notes.status_code == 200
    assert [item["content"] for item in notes.json()] == ["Second", "First"]


def test_business_detail_freshness_uses_latest_observation(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business_detail(db_session)
    for observation in db_session.scalars(select(ObservationRecord)):
        observation.observed_at = datetime(2020, 1, 1, tzinfo=UTC)
    db_session.commit()

    response = client.get(f"/api/v1/businesses/{business.id}")

    assert response.status_code == 200
    assert response.json()["freshness"] == "stale"
