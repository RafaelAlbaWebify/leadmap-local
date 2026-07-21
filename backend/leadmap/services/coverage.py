from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.leadmap.domain.enums import FreshnessStatus
from backend.leadmap.domain.freshness import calculate_freshness
from backend.leadmap.persistence.models import (
    BusinessLocationRecord,
    ObservationRecord,
    TerritoryRecord,
)


@dataclass(frozen=True, slots=True)
class TerritoryCoverage:
    lead_count: int
    latest_observed_at: datetime | None
    freshness: FreshnessStatus


def calculate_territory_coverage(
    session: Session,
    territory: TerritoryRecord,
) -> TerritoryCoverage:
    conditions = [BusinessLocationRecord.country_code == territory.country_code]
    if territory.administrative_area is not None:
        conditions.append(
            BusinessLocationRecord.administrative_area == territory.administrative_area
        )
    if territory.locality is not None:
        conditions.append(BusinessLocationRecord.locality == territory.locality)

    row = session.execute(
        select(
            func.count(func.distinct(BusinessLocationRecord.business_id)),
            func.max(ObservationRecord.observed_at),
        )
        .select_from(BusinessLocationRecord)
        .outerjoin(
            ObservationRecord,
            ObservationRecord.location_id == BusinessLocationRecord.id,
        )
        .where(*conditions)
    ).one()
    lead_count = int(row[0] or 0)
    latest_observed_at = cast(datetime | None, row[1])
    if latest_observed_at is not None and latest_observed_at.tzinfo is None:
        latest_observed_at = latest_observed_at.replace(tzinfo=UTC)
    return TerritoryCoverage(
        lead_count=lead_count,
        latest_observed_at=latest_observed_at,
        freshness=calculate_freshness(latest_observed_at),
    )
