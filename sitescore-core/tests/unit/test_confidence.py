import pytest

from sitescore.config.sectors import Sector
from sitescore.engines.confidence import calculate_confidence, data_vintage_score


def test_reference_confidence_example():
    result = calculate_confidence(
        Sector.COFFEE,
        geographic_level="tract",
        data_age_years=2,
        coverage={
            "demand": "full",
            "competition": "degraded",
            "accessibility": "full",
            "economics": "full",
        },
        input_qualities={
            "rent": "user",
            "price": "user",
            "capacity": "default",
            "schedule": "default",
        },
    )
    assert result.data_coverage == pytest.approx(88.0)
    assert result.input_completeness == pytest.approx(80.0)
    assert result.overall_score == pytest.approx(82.5)
    assert result.label == "moderate"


def test_vintage_unknown_and_old():
    assert data_vintage_score(None) == 0
    assert data_vintage_score(8) == 30
