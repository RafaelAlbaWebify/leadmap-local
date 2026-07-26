"""Add persisted follow-up tasks.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=True),
        sa.Column("deal_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(business_id IS NOT NULL AND deal_id IS NULL) OR "
            "(business_id IS NULL AND deal_id IS NOT NULL)",
            name="ck_task_exactly_one_parent",
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_status_due", "tasks", ["status", "due_date"])
    op.create_index("ix_task_business_created", "tasks", ["business_id", "created_at"])
    op.create_index("ix_task_deal_created", "tasks", ["deal_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_task_deal_created", table_name="tasks")
    op.drop_index("ix_task_business_created", table_name="tasks")
    op.drop_index("ix_task_status_due", table_name="tasks")
    op.drop_table("tasks")
