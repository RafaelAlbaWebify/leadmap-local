from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
