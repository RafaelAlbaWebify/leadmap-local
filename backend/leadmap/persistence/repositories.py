import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.leadmap.domain.freshness import calculate_freshness
from backend.leadmap.domain.models import ObservedBusiness
from backend.leadmap.services.normalization import normalize_business_name

from .models import (
    BusinessLocationRecord,
    BusinessRecord,
    ObservationRecord,
    QueryTemplateRecord,
    SearchRunRecord,
    TerritoryRecord,
)


class LeadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_territory(
        self,
        *,
        name: str,
        country_code: str,
        administrative_area: str | None,
        locality: str | None,
    ) -> TerritoryRecord:
        territory = TerritoryRecord(
            name=name,
            country_code=country_code.upper(),
            administrative_area=administrative_area,
            locality=locality,
            created_at=datetime.now(UTC),
        )
        self.session.add(territory)
        self.session.commit()
        self.session.refresh(territory)
        return territory

    def list_territories(self) -> list[TerritoryRecord]:
        return list(self.session.scalars(select(TerritoryRecord).order_by(TerritoryRecord.name)))

    def get_territory(self, territory_id: str) -> TerritoryRecord | None:
        return self.session.get(TerritoryRecord, territory_id)

    def create_query_template(
        self,
        *,
        name: str,
        sector: str,
        countries: list[str],
        phrases: list[str],
    ) -> QueryTemplateRecord:
        template = QueryTemplateRecord(
            name=name,
            sector=sector,
            countries_csv=",".join(sorted({country.upper() for country in countries})),
            phrases_json=json.dumps(phrases, ensure_ascii=False),
            created_at=datetime.now(UTC),
        )
        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)
        return template

    def get_query_template(self, query_template_id: str) -> QueryTemplateRecord | None:
        return self.session.get(QueryTemplateRecord, query_template_id)

    def list_query_templates(self, country_code: str | None = None) -> list[QueryTemplateRecord]:
        templates = list(
            self.session.scalars(select(QueryTemplateRecord).order_by(QueryTemplateRecord.sector))
        )
        if country_code is None:
            return templates
        target = country_code.upper()
        return [item for item in templates if target in item.countries_csv.split(",")]

    def start_search_run(
        self,
        *,
        territory_id: str,
        provider: str,
        query_text: str,
    ) -> SearchRunRecord:
        run = SearchRunRecord(
            territory_id=territory_id,
            provider=provider,
            query_text=query_text,
            status="active",
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def complete_search_run(self, run: SearchRunRecord) -> SearchRunRecord:
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(run)
        return run

    def persist_observation(
        self,
        *,
        run: SearchRunRecord,
        observed: ObservedBusiness,
        country_code: str,
        administrative_area: str | None,
    ) -> ObservationRecord:
        existing = self.session.scalar(
            select(ObservationRecord).where(
                ObservationRecord.search_run_id == run.id,
                ObservationRecord.provider == observed.provider,
                ObservationRecord.provider_key == observed.provider_key,
            )
        )
        if existing is not None:
            return existing

        previous = self.session.scalar(
            select(ObservationRecord)
            .options(
                selectinload(ObservationRecord.location).selectinload(
                    BusinessLocationRecord.business
                )
            )
            .where(
                ObservationRecord.provider == observed.provider,
                ObservationRecord.provider_key == observed.provider_key,
            )
            .order_by(ObservationRecord.observed_at.desc())
        )

        if previous is not None:
            location = previous.location
            business = location.business
            business.canonical_name = observed.name
            business.normalized_name = normalize_business_name(observed.name)
            business.updated_at = observed.observed_at
            location.phone = observed.phone
            location.website = observed.website
            location.postal_area = observed.postal_area
            location.updated_at = observed.observed_at
        else:
            business = BusinessRecord(
                canonical_name=observed.name,
                normalized_name=normalize_business_name(observed.name),
                qualification_status=observed.qualification_status.value,
                created_at=observed.observed_at,
                updated_at=observed.observed_at,
            )
            location = BusinessLocationRecord(
                business=business,
                locality=observed.locality,
                administrative_area=administrative_area,
                country_code=country_code.upper(),
                postal_area=observed.postal_area,
                phone=observed.phone,
                website=observed.website,
                created_at=observed.observed_at,
                updated_at=observed.observed_at,
            )
            self.session.add_all([business, location])

        observation = ObservationRecord(
            search_run=run,
            location=location,
            provider=observed.provider,
            provider_key=observed.provider_key,
            displayed_name=observed.name,
            category=observed.category,
            source_url=observed.source_url,
            observed_at=observed.observed_at,
        )
        self.session.add(observation)
        self.session.commit()
        self.session.refresh(observation)
        return observation

    def list_businesses(self) -> list[BusinessRecord]:
        statement = (
            select(BusinessRecord)
            .options(
                selectinload(BusinessRecord.locations).selectinload(
                    BusinessLocationRecord.observations
                )
            )
            .order_by(BusinessRecord.canonical_name)
        )
        return list(self.session.scalars(statement))

    def recent_leads(self, limit: int) -> list[dict[str, object]]:
        statement = (
            select(ObservationRecord)
            .options(
                selectinload(ObservationRecord.location).selectinload(
                    BusinessLocationRecord.business
                )
            )
            .order_by(ObservationRecord.observed_at.desc())
            .limit(limit)
        )
        observations = list(self.session.scalars(statement))
        return [
            {
                "id": observation.location.business.id,
                "name": observation.location.business.canonical_name,
                "category": observation.category,
                "locality": observation.location.locality,
                "postal_area": observation.location.postal_area,
                "website": observation.location.website,
                "phone": observation.location.phone,
                "first_observed_at": observation.location.business.created_at,
                "last_observed_at": observation.observed_at,
                "freshness": calculate_freshness(observation.observed_at).value,
                "qualification_status": observation.location.business.qualification_status,
            }
            for observation in observations
        ]
