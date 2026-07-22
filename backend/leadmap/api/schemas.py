from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.leadmap.domain.enums import FreshnessStatus


class LeadResponse(BaseModel):
    id: str
    name: str
    category: str
    locality: str
    postal_area: str | None
    website: str | None
    phone: str | None
    first_observed_at: datetime
    last_observed_at: datetime
    freshness: str
    qualification_status: str


class DashboardResponse(BaseModel):
    total_businesses: int
    qualified_leads: int
    needs_review: int
    stale_records: int
    territories: int
    recent_leads: list[LeadResponse]


class TerritoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    country_code: str = Field(min_length=2, max_length=2)
    administrative_area: str | None = Field(default=None, max_length=200)
    locality: str | None = Field(default=None, max_length=200)

    @field_validator("name", "administrative_area", "locality", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.strip().upper()


class TerritoryResponse(TerritoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class QueryTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sector: str = Field(min_length=1, max_length=200)
    countries: list[str] = Field(min_length=1)
    phrases: list[str] = Field(min_length=1)

    @field_validator("name", "sector")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().upper() for value in values if value.strip()})
        if not normalized:
            raise ValueError("At least one non-empty country code is required.")
        if any(len(value) != 2 for value in normalized):
            raise ValueError("Country codes must contain exactly two characters.")
        return normalized

    @field_validator("phrases")
    @classmethod
    def normalize_phrases(cls, values: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if not normalized:
            raise ValueError("At least one non-empty phrase is required.")
        return normalized


class QueryTemplateResponse(QueryTemplateCreate):
    id: str
    created_at: datetime


class SeedResponse(BaseModel):
    territories_created: int
    query_templates_created: int
    total_territories: int
    total_query_templates: int


class DiscoveryPlanCreate(BaseModel):
    territory_id: str
    query_template_id: str
    max_results_per_query: int = Field(default=20, ge=1, le=100)


class DiscoveryPlanResponse(BaseModel):
    territory_id: str
    territory_name: str
    country_code: str
    query_template_id: str
    query_template_name: str
    sector: str
    phrases: list[str]
    max_results_per_query: int
    total_planned_queries: int
    mode: str = "assisted"


AssistedSessionStateValue = Literal[
    "idle",
    "launching",
    "awaiting_operator",
    "ready",
    "stopped",
    "failed",
]


class AssistedSessionLaunch(DiscoveryPlanCreate):
    pass


class AssistedSessionResponse(BaseModel):
    session_id: str | None
    state: AssistedSessionStateValue
    territory_id: str | None
    query_template_id: str | None
    start_url: str | None
    error: str | None


class GeographySourceResponse(BaseModel):
    dataset_title: str
    publisher: str
    licence: str
    edition_year: int
    source_url: str
    retrieved_at: datetime


class GeographyBoundingBoxResponse(BaseModel):
    west: float
    south: float
    east: float
    north: float


class GeographyBoundaryResponse(BaseModel):
    external_id: str
    name: str
    geometry_type: Literal["Polygon", "MultiPolygon"]
    coordinates: Any
    bounding_box: GeographyBoundingBoxResponse


class GeographyArtifactResponse(BaseModel):
    schema_version: str
    idempotency_key: str
    checksum_sha256: str
    source: GeographySourceResponse
    feature_count: int
    boundaries: list[GeographyBoundaryResponse]


class GeographyArtifactSummaryResponse(BaseModel):
    schema_version: str
    idempotency_key: str
    checksum_sha256: str
    source: GeographySourceResponse
    feature_count: int


class TerritoryBoundaryLinkCreate(BaseModel):
    checksum_sha256: str = Field(min_length=64, max_length=64)
    boundary_external_id: str = Field(min_length=1, max_length=300)


class TerritoryBoundaryLinkResponse(BaseModel):
    territory_id: str
    checksum_sha256: str
    boundary_external_id: str
    boundary_name: str


class TerritoryCoverageResponse(BaseModel):
    territory_id: str
    territory_name: str
    checksum_sha256: str
    boundary_external_id: str
    boundary_name: str
    lead_count: int
    latest_observed_at: datetime | None
    freshness: FreshnessStatus
