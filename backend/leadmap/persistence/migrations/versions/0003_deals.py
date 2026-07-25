"""Add persisted deals.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("value_eur_cents", sa.Integer(), nullable=True),
        sa.Column("next_action", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deal_stage_updated", "deals", ["stage", "updated_at"])
    op.create_index("ix_deal_business_created", "deals", ["business_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_deal_business_created", table_name="deals")
    op.drop_index("ix_deal_stage_updated", table_name="deals")
    op.drop_table("deals")
