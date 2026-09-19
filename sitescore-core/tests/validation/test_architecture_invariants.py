from pathlib import Path

from sitescore.config.sectors import Sector
from sitescore.engines.confidence import calculate_confidence
from sitescore.engines.location import calculate_location_score
from sitescore.schemas.location import CategoryScores

ROOT = Path(__file__).resolve().parents[2] / "src" / "sitescore" / "engines"


def test_location_and_financial_engines_do_not_import_each_other():
    location_source = (ROOT / "location.py").read_text()
    financial_source = (ROOT / "financial.py").read_text()
    assert "engines.financial" not in location_source
    assert "from .financial" not in location_source
    assert "engines.location" not in financial_source
    assert "from .location" not in financial_source


def test_same_input_same_output():
    scores = CategoryScores(90, 60, 95, 20)
    assert calculate_location_score(Sector.COFFEE, scores) == calculate_location_score(Sector.COFFEE, scores)


def test_confidence_monotonicity_for_geography():
    common = dict(
        sector=Sector.COFFEE,
        data_age_years=2,
        coverage={"demand": "full", "competition": "full", "accessibility": "full", "economics": "full"},
        input_qualities={"rent": "user", "price": "user", "capacity": "user", "schedule": "user"},
    )
    county = calculate_confidence(geographic_level="county", **common).overall_score
    tract = calculate_confidence(geographic_level="tract", **common).overall_score
    block = calculate_confidence(geographic_level="block_group", **common).overall_score
    assert county <= tract <= block
