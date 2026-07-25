from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.leadmap.persistence.models import (
    BusinessLocationRecord,
    BusinessRecord,
    ObservationRecord,
    SearchRunRecord,
    TerritoryRecord,
)


class AggregateIdentityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AggregateObservationInput:
    query_text: str
    query_sequence: int
    result_rank: int
    first_seen_scroll_step: int
    captured_at: datetime
    source_url: str | None
    raw_evidence: str | None
    candidate_id: str


@dataclass(frozen=True, slots=True)
class AggregateBusinessInput:
    displayed_name: str
    normalized_name: str
    category: str | None
    address_text: str | None
    phone: str | None
    website: str | None
    latitude: str | None
    longitude: str | None
    provider_key: str
    included: bool
    observations: tuple[AggregateObservationInput, ...]


@dataclass(frozen=True, slots=True)
class AggregateSaveResult:
    businesses_created: int
    businesses_matched: int
    observations_created: int
    observations_skipped: int
    businesses_skipped: int


def persist_aggregate_batch(
    session: Session,
    *,
    batch_id: str,
    territory: TerritoryRecord,
    businesses: tuple[AggregateBusinessInput, ...],
    provider: str = "google_maps",
) -> AggregateSaveResult:
    created = 0
    matched = 0
    observations_created = 0
    observations_skipped = 0
    businesses_skipped = 0

    runs: dict[int, SearchRunRecord] = {}
    for business_input in businesses:
        if not business_input.included:
            businesses_skipped += 1
            continue

        provider_key = _provider_identity_key(business_input)
        previous = _latest_observation(session, provider=provider, provider_key=provider_key)
        if previous is None:
            business, location = _new_business_location(territory, business_input)
            session.add_all([business, location])
            created += 1
        else:
            location = previous.location
            business = location.business
            _refresh_business_location(business, location, business_input)
            matched += 1

        for observation_input in business_input.observations:
            run = runs.get(observation_input.query_sequence)
            if run is None:
                run = _get_or_create_run(
                    session,
                    batch_id=batch_id,
                    territory=territory,
                    provider=provider,
                    observation=observation_input,
                )
                runs[observation_input.query_sequence] = run

            existing = session.scalar(
                select(ObservationRecord).where(
                    ObservationRecord.search_run_id == run.id,
                    ObservationRecord.provider == provider,
                    ObservationRecord.provider_key == provider_key,
                )
            )
            if existing is not None:
                observations_skipped += 1
                continue

            session.add(
                ObservationRecord(
                    search_run=run,
                    location=location,
                    provider=provider,
                    provider_key=provider_key,
                    displayed_name=business_input.displayed_name,
                    category=business_input.category or "Uncategorised",
                    source_url=observation_input.source_url,
                    observed_at=_as_utc(observation_input.captured_at),
                    raw_payload_json=json.dumps(
                        {
                            "candidate_id": observation_input.candidate_id,
                            "query_sequence": observation_input.query_sequence,
                            "result_rank": observation_input.result_rank,
                            "first_seen_scroll_step": observation_input.first_seen_scroll_step,
                            "raw_evidence": observation_input.raw_evidence,
                            "address_text": business_input.address_text,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                )
            )
            observations_created += 1

    session.commit()
    return AggregateSaveResult(
        businesses_created=created,
        businesses_matched=matched,
        observations_created=observations_created,
        observations_skipped=observations_skipped,
        businesses_skipped=businesses_skipped,
    )


def _provider_identity_key(item: AggregateBusinessInput) -> str:
    provider_key = item.provider_key.strip()
    if provider_key:
        return provider_key

    normalized_name = item.normalized_name.strip()
    discriminator = (
        (item.phone or "").strip()
        or (item.website or "").strip().casefold()
        or (item.address_text or "").strip().casefold()
    )
    if not normalized_name or not discriminator:
        raise AggregateIdentityError(
            "A business without a provider key requires a normalized name and "
            "stable phone, website, or address."
        )
    identity = f"{normalized_name}|{discriminator}".encode("utf-8")
    digest = hashlib.sha256(identity, usedforsecurity=False).hexdigest()
    return f"fallback:{digest}"


def _latest_observation(
    session: Session,
    *,
    provider: str,
    provider_key: str,
) -> ObservationRecord | None:
    return session.scalar(
        select(ObservationRecord)
        .options(
            selectinload(ObservationRecord.location).selectinload(
                BusinessLocationRecord.business
            )
        )
        .where(
            ObservationRecord.provider == provider,
            ObservationRecord.provider_key == provider_key,
        )
        .order_by(ObservationRecord.observed_at.desc())
    )


def _new_business_location(
    territory: TerritoryRecord,
    item: AggregateBusinessInput,
) -> tuple[BusinessRecord, BusinessLocationRecord]:
    observed_at = min(_as_utc(value.captured_at) for value in item.observations)
    business = BusinessRecord(
        canonical_name=item.displayed_name,
        normalized_name=item.normalized_name,
        qualification_status="needs_review",
        created_at=observed_at,
        updated_at=observed_at,
    )
    location = BusinessLocationRecord(
        business=business,
        locality=territory.locality or territory.name,
        administrative_area=territory.administrative_area,
        country_code=territory.country_code,
        postal_area=None,
        phone=item.phone,
        website=item.website,
        latitude=item.latitude,
        longitude=item.longitude,
        created_at=observed_at,
        updated_at=observed_at,
    )
    return business, location


def _refresh_business_location(
    business: BusinessRecord,
    location: BusinessLocationRecord,
    item: AggregateBusinessInput,
) -> None:
    latest = max(_as_utc(value.captured_at) for value in item.observations)
    if latest >= business.updated_at:
        business.canonical_name = item.displayed_name
        business.normalized_name = item.normalized_name
        business.updated_at = latest
        location.phone = item.phone
        location.website = item.website
        location.latitude = item.latitude
        location.longitude = item.longitude
        location.updated_at = latest


def _get_or_create_run(
    session: Session,
    *,
    batch_id: str,
    territory: TerritoryRecord,
    provider: str,
    observation: AggregateObservationInput,
) -> SearchRunRecord:
    run_key = f"leadmap:{batch_id}:query:{observation.query_sequence}"
    run_id = str(uuid5(NAMESPACE_URL, run_key))
    existing = session.get(SearchRunRecord, run_id)
    if existing is not None:
        conflicts = (
            existing.territory_id != territory.id
            or existing.query_text != observation.query_text
        )
        if conflicts:
            raise ValueError(
                "Batch query sequence conflicts with an existing persisted search run."
            )
        return existing

    captured_at = _as_utc(observation.captured_at)
    run = SearchRunRecord(
        id=run_id,
        territory_id=territory.id,
        provider=provider,
        query_text=observation.query_text,
        status="completed",
        started_at=captured_at,
        completed_at=captured_at,
    )
    session.add(run)
    return run


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
