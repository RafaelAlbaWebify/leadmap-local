import csv
import io
import json
from datetime import UTC, datetime

from backend.leadmap.persistence.models import BusinessRecord

EXPORT_SCHEMA_VERSION = "1.1"
EXPORT_FIELDS = [
    "business_id",
    "location_id",
    "business_name",
    "qualification_status",
    "country_code",
    "administrative_area",
    "locality",
    "postal_area",
    "phone",
    "website",
    "first_observed_at",
    "last_observed_at",
]


def businesses_to_rows(businesses: list[BusinessRecord]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for business in businesses:
        for location in business.locations:
            observed_at_values = [item.observed_at for item in location.observations]
            first_observed = min(observed_at_values, default=location.created_at)
            last_observed = max(observed_at_values, default=location.updated_at)
            rows.append(
                {
                    "business_id": business.id,
                    "location_id": location.id,
                    "business_name": business.canonical_name,
                    "qualification_status": business.qualification_status,
                    "country_code": location.country_code,
                    "administrative_area": location.administrative_area or "",
                    "locality": location.locality,
                    "postal_area": location.postal_area or "",
                    "phone": location.phone or "",
                    "website": location.website or "",
                    "first_observed_at": first_observed.isoformat(),
                    "last_observed_at": last_observed.isoformat(),
                }
            )
    return rows


def export_csv(businesses: list[BusinessRecord]) -> str:
    rows = businesses_to_rows(businesses)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_json(businesses: list[BusinessRecord]) -> str:
    payload = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "records": businesses_to_rows(businesses),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
