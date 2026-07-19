"""Initial persistent lead model."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "territories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("administrative_area", sa.String(length=200), nullable=True),
        sa.Column("locality", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "country_code", "name", "administrative_area", "locality", name="uq_territory_identity"
        ),
    )
    op.create_table(
        "query_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sector", sa.String(length=200), nullable=False),
        sa.Column("countries_csv", sa.Text(), nullable=False),
        sa.Column("phrases_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "sector", name="uq_query_template_name_sector"),
    )
    op.create_table(
        "businesses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("canonical_name", sa.String(length=300), nullable=False),
        sa.Column("normalized_name", sa.String(length=300), nullable=False),
        sa.Column("qualification_status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_businesses_normalized_name", "businesses", ["normalized_name"])
    op.create_table(
        "business_locations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("locality", sa.String(length=200), nullable=False),
        sa.Column("administrative_area", sa.String(length=200), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("postal_area", sa.String(length=30), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("latitude", sa.String(length=40), nullable=True),
        sa.Column("longitude", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_location_geo",
        "business_locations",
        ["country_code", "administrative_area", "locality"],
    )
    op.create_table(
        "search_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("territory_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("query_text", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["territory_id"], ["territories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "observations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("search_run_id", sa.String(length=36), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_key", sa.String(length=500), nullable=False),
        sa.Column("displayed_name", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["location_id"], ["business_locations.id"]),
        sa.ForeignKeyConstraint(["search_run_id"], ["search_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "search_run_id", "provider", "provider_key", name="uq_observation_per_run"
        ),
    )
    op.create_index(
        "ix_observation_provider_identity", "observations", ["provider", "provider_key"]
    )
    op.create_index("ix_observation_observed_at", "observations", ["observed_at"])


def downgrade() -> None:
    op.drop_index("ix_observation_observed_at", table_name="observations")
    op.drop_index("ix_observation_provider_identity", table_name="observations")
    op.drop_table("observations")
    op.drop_table("search_runs")
    op.drop_index("ix_location_geo", table_name="business_locations")
    op.drop_table("business_locations")
    op.drop_index("ix_businesses_normalized_name", table_name="businesses")
    op.drop_table("businesses")
    op.drop_table("query_templates")
    op.drop_table("territories")
