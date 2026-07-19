from typing import TypedDict

from sqlalchemy.orm import Session

from backend.leadmap.persistence.repositories import LeadRepository


class QueryTemplateSeed(TypedDict):
    name: str
    sector: str
    countries: list[str]
    phrases: list[str]


IRELAND_QUERY_TEMPLATES: list[QueryTemplateSeed] = [
    {
        "name": "Accountancy",
        "sector": "Professional Services",
        "countries": ["IE"],
        "phrases": ["accountant", "accounting firm", "tax advisor", "bookkeeper"],
    },
    {
        "name": "Legal Services",
        "sector": "Professional Services",
        "countries": ["IE"],
        "phrases": ["solicitor", "law firm", "conveyancing solicitor"],
    },
    {
        "name": "Dental Clinics",
        "sector": "Healthcare",
        "countries": ["IE"],
        "phrases": ["dentist", "dental clinic", "orthodontist"],
    },
    {
        "name": "Recruitment Agencies",
        "sector": "Professional Services",
        "countries": ["IE"],
        "phrases": ["recruitment agency", "staffing agency", "employment agency"],
    },
    {
        "name": "Property Services",
        "sector": "Property",
        "countries": ["IE"],
        "phrases": ["estate agent", "property management", "chartered surveyor"],
    },
]


def seed_ireland(session: Session) -> dict[str, int]:
    repository = LeadRepository(session)
    territories_created = 0
    templates_created = 0

    if not repository.list_territories():
        repository.create_territory(
            name="Galway City",
            country_code="IE",
            administrative_area="County Galway",
            locality="Galway",
        )
        territories_created += 1

    existing = {(item.name, item.sector) for item in repository.list_query_templates()}
    for template in IRELAND_QUERY_TEMPLATES:
        if (template["name"], template["sector"]) not in existing:
            repository.create_query_template(**template)
            templates_created += 1

    return {
        "territories_created": territories_created,
        "query_templates_created": templates_created,
        "total_territories": len(repository.list_territories()),
        "total_query_templates": len(repository.list_query_templates()),
    }
