import pytest

from backend.leadmap.services.query_plans import build_prepared_queries


def test_builds_deterministic_prepared_query_sequence() -> None:
    queries = build_prepared_queries(
        phrases=["accountant", "tax advisor", "bookkeeper"],
        territory_name="Kildare County",
        country_code="ie",
    )

    assert [query.sequence for query in queries] == [1, 2, 3]
    assert [query.phrase for query in queries] == [
        "accountant",
        "tax advisor",
        "bookkeeper",
    ]
    assert [query.query_text for query in queries] == [
        "accountant in Kildare County, IE",
        "tax advisor in Kildare County, IE",
        "bookkeeper in Kildare County, IE",
    ]


def test_skips_blank_and_case_insensitive_duplicate_phrases() -> None:
    queries = build_prepared_queries(
        phrases=[" accountant ", "", "Accountant", "tax advisor"],
        territory_name=" Galway City ",
        country_code="IE",
    )

    assert [query.phrase for query in queries] == ["accountant", "tax advisor"]
    assert queries[0].query_text == "accountant in Galway City, IE"


@pytest.mark.parametrize(
    ("phrases", "territory_name", "country_code", "message"),
    [
        (["accountant"], " ", "IE", "territory_name cannot be blank"),
        (["accountant"], "Galway City", "IRE", "country_code must contain exactly two"),
        (["", "   "], "Galway City", "IE", "At least one non-empty query phrase"),
    ],
)
def test_rejects_invalid_prepared_query_inputs(
    phrases: list[str],
    territory_name: str,
    country_code: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_prepared_queries(
            phrases=phrases,
            territory_name=territory_name,
            country_code=country_code,
        )
