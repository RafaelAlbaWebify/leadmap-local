from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.models import BusinessRecord, DealRecord, TaskRecord

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
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
    def validate_task(self) -> "TaskCreate":
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Task title cannot be blank.")
        if (self.business_id is None) == (self.deal_id is None):
            raise ValueError("A task must belong to exactly one business or deal.")
        return self


class TaskResponse(BaseModel):
    id: str
    business_id: str | None
    deal_id: str | None
    parent_name: str
    title: str
    due_date: date | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


def _response(record: TaskRecord) -> TaskResponse:
    if record.business is not None:
        parent_name = record.business.canonical_name
    elif record.deal is not None:
        parent_name = record.deal.title
    else:
        raise RuntimeError("Persisted task has no parent.")
    return TaskResponse(
        id=record.id,
        business_id=record.business_id,
        deal_id=record.deal_id,
        parent_name=parent_name,
        title=record.title,
        due_date=record.due_date,
        status=TaskStatus(record.status),
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


@router.get("", response_model=list[TaskResponse])
def list_tasks(session: SessionDependency) -> list[TaskResponse]:
    records = session.scalars(
        select(TaskRecord)
        .options(joinedload(TaskRecord.business), joinedload(TaskRecord.deal))
        .order_by(TaskRecord.status, TaskRecord.due_date, TaskRecord.created_at.desc())
    ).all()
    return [_response(record) for record in records]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, session: SessionDependency) -> TaskResponse:
    business = session.get(BusinessRecord, payload.business_id) if payload.business_id else None
    deal = session.get(DealRecord, payload.deal_id) if payload.deal_id else None
    if payload.business_id and business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
    if payload.deal_id and deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found.")

    now = datetime.now(UTC)
    record = TaskRecord(
        business=business,
        deal=deal,
        title=payload.title,
        due_date=payload.due_date,
        status=TaskStatus.OPEN.value,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _response(record)


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: str, session: SessionDependency) -> TaskResponse:
    record = session.scalar(
        select(TaskRecord)
        .options(joinedload(TaskRecord.business), joinedload(TaskRecord.deal))
        .where(TaskRecord.id == task_id)
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if record.status == TaskStatus.COMPLETED.value:
        return _response(record)

    now = datetime.now(UTC)
    record.status = TaskStatus.COMPLETED.value
    record.updated_at = now
    record.completed_at = now
    session.commit()
    session.refresh(record)
    return _response(record)
