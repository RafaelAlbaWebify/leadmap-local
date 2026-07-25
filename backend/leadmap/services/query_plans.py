from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PreparedQuery:
    sequence: int
    phrase: str
    query_text: str


def build_prepared_queries(
    *,
    phrases: list[str],
    territory_name: str,
    country_code: str,
) -> tuple[PreparedQuery, ...]:
    clean_territory = territory_name.strip()
    clean_country = country_code.strip().upper()
    if not clean_territory:
        raise ValueError("territory_name cannot be blank.")
    if len(clean_country) != 2:
        raise ValueError("country_code must contain exactly two characters.")

    prepared: list[PreparedQuery] = []
    seen_phrases: set[str] = set()
    for raw_phrase in phrases:
        phrase = raw_phrase.strip()
        if not phrase or phrase.casefold() in seen_phrases:
            continue
        seen_phrases.add(phrase.casefold())
        prepared.append(
            PreparedQuery(
                sequence=len(prepared) + 1,
                phrase=phrase,
                query_text=f"{phrase} in {clean_territory}, {clean_country}",
            )
        )

    if not prepared:
        raise ValueError("At least one non-empty query phrase is required.")
    return tuple(prepared)
