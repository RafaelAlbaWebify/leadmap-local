from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.leadmap.domain.models import ObservedBusiness
from backend.leadmap.persistence.repositories import LeadRepository


def test_same_provider_identity_reuses_business_across_runs(db_session: Session) -> None:
    repository = LeadRepository(db_session)
    territory = repository.create_territory(
        name="Galway City",
        country_code="IE",
        administrative_area="County Galway",
        locality="Galway",
    )
    first_run = repository.start_search_run(
        territory_id=territory.id,
        provider="fixture",
        query_text="accountant Galway",
    )
    observed = ObservedBusiness(
        provider="fixture",
        provider_key="fixture-001",
        name="West Coast Accountancy",
        category="Accountant",
        locality="Galway",
        postal_area="H91",
        observed_at=datetime(2026, 7, 19, tzinfo=UTC),
    )
    first = repository.persist_observation(
        run=first_run,
        observed=observed,
        country_code="IE",
        administrative_area="County Galway",
    )
    second_run = repository.start_search_run(
        territory_id=territory.id,
        provider="fixture",
        query_text="tax advisor Galway",
    )
    second = repository.persist_observation(
        run=second_run,
        observed=observed,
        country_code="IE",
        administrative_area="County Galway",
    )

    assert first.location.business.id == second.location.business.id
    assert len(repository.list_businesses()) == 1


def test_duplicate_observation_in_same_run_is_idempotent(db_session: Session) -> None:
    repository = LeadRepository(db_session)
    territory = repository.create_territory(
        name="Galway City",
        country_code="IE",
        administrative_area="County Galway",
        locality="Galway",
    )
    run = repository.start_search_run(
        territory_id=territory.id,
        provider="fixture",
        query_text="accountant Galway",
    )
    observed = ObservedBusiness(
        provider="fixture",
        provider_key="fixture-001",
        name="West Coast Accountancy",
        category="Accountant",
        locality="Galway",
    )
    first = repository.persist_observation(
        run=run,
        observed=observed,
        country_code="IE",
        administrative_area="County Galway",
    )
    second = repository.persist_observation(
        run=run,
        observed=observed,
        country_code="IE",
        administrative_area="County Galway",
    )
    assert first.id == second.id
