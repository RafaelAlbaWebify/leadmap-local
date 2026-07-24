from sqlalchemy.orm import Session

from backend.leadmap.persistence.repositories import LeadRepository
from backend.leadmap.services.seed import IRELAND_TERRITORIES, seed_ireland


def test_fresh_seed_creates_all_irish_local_authorities(db_session: Session) -> None:
    result = seed_ireland(db_session)
    territories = LeadRepository(db_session).list_territories()

    assert result["territories_created"] == 31
    assert result["total_territories"] == 31
    assert len(IRELAND_TERRITORIES) == 31
    assert {territory.name for territory in territories} >= {
        "Cork City",
        "Cork County",
        "Dublin City",
        "Dún Laoghaire–Rathdown",
        "Galway City",
        "Galway County",
        "Limerick City and County",
        "South Dublin",
        "Waterford City and County",
    }


def test_seed_adds_missing_authorities_without_replacing_existing_galway(
    db_session: Session,
) -> None:
    repository = LeadRepository(db_session)
    galway = repository.create_territory(
        name="Galway City",
        country_code="IE",
        administrative_area="County Galway",
        locality="Galway",
    )

    result = seed_ireland(db_session)
    territories = repository.list_territories()
    seeded_galway = next(
        item for item in territories if item.name == "Galway City"
    )

    assert result["territories_created"] == 30
    assert result["total_territories"] == 31
    assert seeded_galway.id == galway.id


def test_seed_is_idempotent(db_session: Session) -> None:
    first = seed_ireland(db_session)
    second = seed_ireland(db_session)

    assert first["territories_created"] == 31
    assert second["territories_created"] == 0
    assert second["query_templates_created"] == 0
    assert second["total_territories"] == 31
    assert second["total_query_templates"] == 5
