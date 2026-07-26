from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.leadmap.persistence.models import BusinessRecord, DealRecord, TaskRecord


def seed_business(session: Session) -> BusinessRecord:
    now = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    business = BusinessRecord(
        id="business-1",
        canonical_name="Kildare Accountancy",
        normalized_name="kildare accountancy",
        qualification_status="qualified",
        created_at=now,
        updated_at=now,
    )
    session.add(business)
    session.commit()
    return business


def seed_deal(session: Session, business: BusinessRecord) -> DealRecord:
    now = datetime(2026, 7, 26, 12, 30, tzinfo=UTC)
    deal = DealRecord(
        id="deal-1",
        business=business,
        title="Website redesign",
        stage="proposal",
        value_eur_cents=350000,
        next_action="Send proposal",
        created_at=now,
        updated_at=now,
    )
    session.add(deal)
    session.commit()
    return deal


def test_create_list_and_complete_business_task(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business(db_session)

    created_response = client.post(
        "/api/v1/tasks",
        json={
            "business_id": business.id,
            "title": "  Call the owner  ",
            "due_date": "2026-07-30",
        },
    )

    assert created_response.status_code == 201
    created = created_response.json()
    assert created["business_id"] == business.id
    assert created["deal_id"] is None
    assert created["parent_name"] == "Kildare Accountancy"
    assert created["title"] == "Call the owner"
    assert created["due_date"] == "2026-07-30"
    assert created["status"] == "open"
    assert created["completed_at"] is None

    listed = client.get("/api/v1/tasks")
    assert listed.status_code == 200
    assert listed.json() == [created]

    completed_response = client.patch(f"/api/v1/tasks/{created['id']}/complete")
    assert completed_response.status_code == 200
    completed = completed_response.json()
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None

    record = db_session.get(TaskRecord, created["id"])
    assert record is not None
    assert record.title == "Call the owner"
    assert record.business_id == business.id
    assert record.deal_id is None


def test_create_deal_task(client: TestClient, db_session: Session) -> None:
    business = seed_business(db_session)
    deal = seed_deal(db_session, business)

    response = client.post(
        "/api/v1/tasks",
        json={"deal_id": deal.id, "title": "Prepare proposal"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["business_id"] is None
    assert payload["deal_id"] == deal.id
    assert payload["parent_name"] == "Website redesign"
    assert payload["status"] == "open"


def test_task_creation_validates_parent_and_title(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business(db_session)

    no_parent = client.post("/api/v1/tasks", json={"title": "Call client"})
    two_parents = client.post(
        "/api/v1/tasks",
        json={"business_id": business.id, "deal_id": "deal-1", "title": "Call client"},
    )
    blank_title = client.post(
        "/api/v1/tasks",
        json={"business_id": business.id, "title": "   "},
    )
    missing_business = client.post(
        "/api/v1/tasks",
        json={"business_id": "missing", "title": "Call client"},
    )

    assert no_parent.status_code == 422
    assert two_parents.status_code == 422
    assert blank_title.status_code == 422
    assert missing_business.status_code == 404
    assert db_session.query(TaskRecord).count() == 0


def test_complete_unknown_task_returns_404(client: TestClient) -> None:
    response = client.patch("/api/v1/tasks/missing/complete")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found."}
