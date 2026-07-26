from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.models import BusinessRecord, DealRecord, TaskRecord

router = APIRouter(prefix="/api/v1", tags=["tasks"])
SessionDependency = Annotated[Session, Depends(get_session)]


class TaskStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    due_date: date | None = None
    business_id: str | None = None
    deal_id: str | None = None

    @model_validator(mode="after")
    def validate_parent_and_title(self) -> "TaskCreate":
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Task title cannot be blank.")
        if (self.business_id is None) == (self.deal_id is None):
            raise ValueError("A task must reference exactly one business or deal.")
        return self


class TaskResponse(BaseModel):
    id: str
    title: str
    due_date: date | None
    status: TaskStatus
    business_id: str | None
    deal_id: str | None
    parent_type: str
    parent_name: str
    created_at: datetime
    updated_at: datetime


def _response(record: TaskRecord) -> TaskResponse:
    if record.business is not None:
        parent_type = "business"
        parent_name = record.business.canonical_name
    else:
        parent_type = "deal"
        parent_name = record.deal.title
    return TaskResponse(
        id=record.id,
        title=record.title,
        due_date=record.due_date,
        status=TaskStatus(record.status),
        business_id=record.business_id,
        deal_id=record.deal_id,
        parent_type=parent_type,
        parent_name=parent_name,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(session: SessionDependency) -> list[TaskResponse]:
    records = session.scalars(
        select(TaskRecord)
        .options(joinedload(TaskRecord.business), joinedload(TaskRecord.deal))
        .order_by(TaskRecord.status, TaskRecord.due_date, TaskRecord.created_at.desc())
    ).all()
    return [_response(record) for record in records]


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, session: SessionDependency) -> TaskResponse:
    business = None
    deal = None
    if payload.business_id is not None:
        business = session.get(BusinessRecord, payload.business_id)
        if business is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
    if payload.deal_id is not None:
        deal = session.scalar(
            select(DealRecord).options(joinedload(DealRecord.business)).where(DealRecord.id == payload.deal_id)
        )
        if deal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found.")

    now = datetime.now(UTC)
    record = TaskRecord(
        title=payload.title,
        due_date=payload.due_date,
        status=TaskStatus.OPEN.value,
        business=business,
        deal=deal,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _response(record)


@router.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: str, session: SessionDependency) -> TaskResponse:
    record = session.scalar(
        select(TaskRecord)
        .options(joinedload(TaskRecord.business), joinedload(TaskRecord.deal))
        .where(TaskRecord.id == task_id)
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if record.status != TaskStatus.COMPLETED.value:
        record.status = TaskStatus.COMPLETED.value
        record.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(record)
    return _response(record)
