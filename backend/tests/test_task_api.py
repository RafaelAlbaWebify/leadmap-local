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
    now = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
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
    seed_business(db_session)
    created = client.post(
        "/api/v1/tasks",
        json={
            "title": "  Call decision maker  ",
            "due_date": "2026-07-30",
            "business_id": "business-1",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "Call decision maker"
    assert payload["status"] == "open"
    assert payload["parent_type"] == "business"
    assert payload["parent_name"] == "Kildare Accountancy"

    listed = client.get("/api/v1/tasks")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [payload["id"]]

    completed = client.patch(f"/api/v1/tasks/{payload['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert client.patch(f"/api/v1/tasks/{payload['id']}/complete").status_code == 200


def test_create_deal_task_returns_parent_identity(
    client: TestClient,
    db_session: Session,
) -> None:
    business = seed_business(db_session)
    seed_deal(db_session, business)
    response = client.post(
        "/api/v1/tasks",
        json={"title": "Review proposal", "deal_id": "deal-1"},
    )
    assert response.status_code == 201
    assert response.json()["parent_type"] == "deal"
    assert response.json()["parent_name"] == "Website redesign"


def test_task_creation_rejects_invalid_contracts(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_business(db_session)
    cases = [
        {"title": " ", "business_id": "business-1"},
        {"title": "x" * 301, "business_id": "business-1"},
        {"title": "No parent"},
        {
            "title": "Two parents",
            "business_id": "business-1",
            "deal_id": "deal-1",
        },
        {
            "title": "Bad date",
            "due_date": "tomorrow",
            "business_id": "business-1",
        },
    ]
    for payload in cases:
        assert client.post("/api/v1/tasks", json=payload).status_code == 422

    unknown = client.post(
        "/api/v1/tasks",
        json={"title": "Unknown", "business_id": "missing"},
    )
    assert unknown.status_code == 404
    assert db_session.query(TaskRecord).count() == 0


def test_complete_unknown_task_returns_404(client: TestClient) -> None:
    response = client.patch("/api/v1/tasks/missing/complete")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found."}
