from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.leadmap.persistence.models import BusinessRecord, DealRecord


def seed_business(session: Session, *, qualified: bool = True) -> BusinessRecord:
    now = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    business = BusinessRecord(
        id="business-qualified" if qualified else "business-review",
        canonical_name="Kildare Accountancy",
        normalized_name="kildare accountancy",
        qualification_status="qualified" if qualified else "needs_review",
        created_at=now,
        updated_at=now,
    )
    session.add(business)
    session.commit()
    return business


def test_create_and_list_deal_for_qualified_business(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business(db_session)

    response = client.post(
        f"/api/v1/businesses/{business.id}/deals",
        json={
            "title": "  Website redesign opportunity  ",
            "stage": "discovery",
            "value_eur_cents": 350000,
            "next_action": "  Book discovery call  ",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["business_id"] == business.id
    assert created["business_name"] == "Kildare Accountancy"
    assert created["title"] == "Website redesign opportunity"
    assert created["stage"] == "discovery"
    assert created["value_eur_cents"] == 350000
    assert created["next_action"] == "Book discovery call"

    listed = client.get("/api/v1/deals")
    assert listed.status_code == 200
    assert listed.json() == [created]


def test_deal_creation_rejects_non_qualified_business(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business(db_session, qualified=False)

    response = client.post(
        f"/api/v1/businesses/{business.id}/deals",
        json={"title": "Potential project", "stage": "lead"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Only qualified businesses can create deals."}
    assert db_session.query(DealRecord).count() == 0


def test_deal_creation_returns_404_for_unknown_business(client: TestClient) -> None:
    response = client.post(
        "/api/v1/businesses/missing/deals",
        json={"title": "Potential project", "stage": "lead"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Business not found."}


def test_deal_creation_validates_payload(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business(db_session)

    blank_title = client.post(
        f"/api/v1/businesses/{business.id}/deals",
        json={"title": "   ", "stage": "lead"},
    )
    unsupported_stage = client.post(
        f"/api/v1/businesses/{business.id}/deals",
        json={"title": "Potential project", "stage": "negotiation"},
    )
    negative_value = client.post(
        f"/api/v1/businesses/{business.id}/deals",
        json={"title": "Potential project", "stage": "lead", "value_eur_cents": -1},
    )

    assert blank_title.status_code == 422
    assert unsupported_stage.status_code == 422
    assert negative_value.status_code == 422
    assert db_session.query(DealRecord).count() == 0
