from backend.leadmap.services.normalization import normalize_business_name


def test_business_name_normalization() -> None:
    assert normalize_business_name("  O\u2019Malley & Co.  ") == "o malley co"
