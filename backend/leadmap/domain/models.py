from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .enums import QualificationStatus


@dataclass(frozen=True, slots=True)
class Territory:
    name: str
    country_code: str
    administrative_area: str | None = None
    locality: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class QueryTemplate:
    name: str
    sector: str
    phrases: tuple[str, ...]
    countries: tuple[str, ...]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ObservedBusiness:
    provider: str
    provider_key: str
    name: str
    category: str
    locality: str
    source_url: str | None = None
    postal_area: str | None = None
    website: str | None = None
    phone: str | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    qualification_status: QualificationStatus = QualificationStatus.NEEDS_REVIEW
