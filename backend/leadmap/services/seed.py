from typing import TypedDict

from sqlalchemy.orm import Session

from backend.leadmap.persistence.repositories import LeadRepository


class TerritorySeed(TypedDict):
    name: str
    country_code: str
    administrative_area: str | None
    locality: str | None


class QueryTemplateSeed(TypedDict):
    name: str
    sector: str
    countries: list[str]
    phrases: list[str]


IRELAND_TERRITORIES: list[TerritorySeed] = [
    {
        "name": "Carlow County",
        "country_code": "IE",
        "administrative_area": "County Carlow",
        "locality": None,
    },
    {
        "name": "Cavan County",
        "country_code": "IE",
        "administrative_area": "County Cavan",
        "locality": None,
    },
    {
        "name": "Clare County",
        "country_code": "IE",
        "administrative_area": "County Clare",
        "locality": None,
    },
    {
        "name": "Cork City",
        "country_code": "IE",
        "administrative_area": "County Cork",
        "locality": "Cork",
    },
    {
        "name": "Cork County",
        "country_code": "IE",
        "administrative_area": "County Cork",
        "locality": None,
    },
    {
        "name": "Donegal County",
        "country_code": "IE",
        "administrative_area": "County Donegal",
        "locality": None,
    },
    {
        "name": "Dublin City",
        "country_code": "IE",
        "administrative_area": "County Dublin",
        "locality": "Dublin",
    },
    {
        "name": "Dún Laoghaire–Rathdown",
        "country_code": "IE",
        "administrative_area": "County Dublin",
        "locality": None,
    },
    {
        "name": "Fingal",
        "country_code": "IE",
        "administrative_area": "County Dublin",
        "locality": None,
    },
    {
        "name": "Galway City",
        "country_code": "IE",
        "administrative_area": "County Galway",
        "locality": "Galway",
    },
    {
        "name": "Galway County",
        "country_code": "IE",
        "administrative_area": "County Galway",
        "locality": None,
    },
    {
        "name": "Kerry County",
        "country_code": "IE",
        "administrative_area": "County Kerry",
        "locality": None,
    },
    {
        "name": "Kildare County",
        "country_code": "IE",
        "administrative_area": "County Kildare",
        "locality": None,
    },
    {
        "name": "Kilkenny County",
        "country_code": "IE",
        "administrative_area": "County Kilkenny",
        "locality": None,
    },
    {
        "name": "Laois County",
        "country_code": "IE",
        "administrative_area": "County Laois",
        "locality": None,
    },
    {
        "name": "Leitrim County",
        "country_code": "IE",
        "administrative_area": "County Leitrim",
        "locality": None,
    },
    {
        "name": "Limerick City and County",
        "country_code": "IE",
        "administrative_area": "County Limerick",
        "locality": None,
    },
    {
        "name": "Longford County",
        "country_code": "IE",
        "administrative_area": "County Longford",
        "locality": None,
    },
    {
        "name": "Louth County",
        "country_code": "IE",
        "administrative_area": "County Louth",
        "locality": None,
    },
    {
        "name": "Mayo County",
        "country_code": "IE",
        "administrative_area": "County Mayo",
        "locality": None,
    },
    {
        "name": "Meath County",
        "country_code": "IE",
        "administrative_area": "County Meath",
        "locality": None,
    },
    {
        "name": "Monaghan County",
        "country_code": "IE",
        "administrative_area": "County Monaghan",
        "locality": None,
    },
    {
        "name": "Offaly County",
        "country_code": "IE",
        "administrative_area": "County Offaly",
        "locality": None,
    },
    {
        "name": "Roscommon County",
        "country_code": "IE",
        "administrative_area": "County Roscommon",
        "locality": None,
    },
    {
        "name": "Sligo County",
        "country_code": "IE",
        "administrative_area": "County Sligo",
        "locality": None,
    },
    {
        "name": "South Dublin",
        "country_code": "IE",
        "administrative_area": "County Dublin",
        "locality": None,
    },
    {
        "name": "Tipperary County",
        "country_code": "IE",
        "administrative_area": "County Tipperary",
        "locality": None,
    },
    {
        "name": "Waterford City and County",
        "country_code": "IE",
        "administrative_area": "County Waterford",
        "locality": None,
    },
    {
        "name": "Westmeath County",
        "country_code": "IE",
        "administrative_area": "County Westmeath",
        "locality": None,
    },
    {
        "name": "Wexford County",
        "country_code": "IE",
        "administrative_area": "County Wexford",
        "locality": None,
    },
    {
        "name": "Wicklow County",
        "country_code": "IE",
        "administrative_area": "County Wicklow",
        "locality": None,
    },
]

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

    existing_territories = {
        (item.name.casefold(), item.country_code.upper()) for item in repository.list_territories()
    }
    for territory in IRELAND_TERRITORIES:
        key = (territory["name"].casefold(), territory["country_code"])
        if key not in existing_territories:
            repository.create_territory(**territory)
            existing_territories.add(key)
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
