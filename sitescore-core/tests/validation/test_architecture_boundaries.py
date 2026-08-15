from pathlib import Path


SRC = Path("src/sitescore")


def read_source(relative_path: str) -> str:
    return (
        SRC / relative_path
    ).read_text(encoding="utf-8")


def test_location_engine_does_not_import_financial_engine():
    source = read_source(
        "engines/location.py"
    )

    forbidden = (
        "engines.financial",
        "FinancialResult",
        "bec_base",
        "rent_burden",
        "operating_margin",
    )

    for token in forbidden:
        assert token not in source


def test_financial_engine_does_not_import_location_engine():
    source = read_source(
        "engines/financial.py"
    )

    forbidden = (
        "engines.location",
        "LocationResult",
        "location_score",
        "final_score",
        "category_scores",
    )

    for token in forbidden:
        assert token not in source


def test_revenue_engine_does_not_use_location_score():
    source = read_source(
        "engines/revenue.py"
    )

    forbidden = (
        "location_score",
        "LocationResult",
        "final_score",
        "competition_score",
    )

    for token in forbidden:
        assert token not in source