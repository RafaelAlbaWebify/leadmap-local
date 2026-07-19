from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def new_id() -> str:
    return str(uuid4())


class TerritoryRecord(Base):
    __tablename__ = "territories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    administrative_area: Mapped[str | None] = mapped_column(String(200))
    locality: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    search_runs: Mapped[list["SearchRunRecord"]] = relationship(back_populates="territory")

    __table_args__ = (
        UniqueConstraint(
            "country_code",
            "name",
            "administrative_area",
            "locality",
            name="uq_territory_identity",
        ),
    )


class QueryTemplateRecord(Base):
    __tablename__ = "query_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str] = mapped_column(String(200), nullable=False)
    countries_csv: Mapped[str] = mapped_column(Text, nullable=False)
    phrases_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("name", "sector", name="uq_query_template_name_sector"),)


class BusinessRecord(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    canonical_name: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    qualification_status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    locations: Mapped[list["BusinessLocationRecord"]] = relationship(back_populates="business")


class BusinessLocationRecord(Base):
    __tablename__ = "business_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    locality: Mapped[str] = mapped_column(String(200), nullable=False)
    administrative_area: Mapped[str | None] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    postal_area: Mapped[str | None] = mapped_column(String(30))
    phone: Mapped[str | None] = mapped_column(String(80))
    website: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[str | None] = mapped_column(String(40))
    longitude: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    business: Mapped[BusinessRecord] = relationship(back_populates="locations")
    observations: Mapped[list["ObservationRecord"]] = relationship(back_populates="location")

    __table_args__ = (Index("ix_location_geo", "country_code", "administrative_area", "locality"),)


class SearchRunRecord(Base):
    __tablename__ = "search_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    territory_id: Mapped[str] = mapped_column(ForeignKey("territories.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    query_text: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    territory: Mapped[TerritoryRecord] = relationship(back_populates="search_runs")
    observations: Mapped[list["ObservationRecord"]] = relationship(back_populates="search_run")


class ObservationRecord(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    search_run_id: Mapped[str] = mapped_column(ForeignKey("search_runs.id"), nullable=False)
    location_id: Mapped[str] = mapped_column(ForeignKey("business_locations.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(500), nullable=False)
    displayed_name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload_json: Mapped[str | None] = mapped_column(Text)

    search_run: Mapped[SearchRunRecord] = relationship(back_populates="observations")
    location: Mapped[BusinessLocationRecord] = relationship(back_populates="observations")

    __table_args__ = (
        UniqueConstraint(
            "search_run_id", "provider", "provider_key", name="uq_observation_per_run"
        ),
        Index("ix_observation_provider_identity", "provider", "provider_key"),
        Index("ix_observation_observed_at", "observed_at"),
    )
