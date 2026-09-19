import pytest

from sitescore.config.category_weights import SECTOR_CATEGORY_WEIGHTS
from sitescore.config.sectors import Sector
from sitescore.engines.location import calculate_location_score
from sitescore.schemas.location import CategoryScores


def test_all_category_weights_sum_to_one():
    for sector, weights in SECTOR_CATEGORY_WEIGHTS.items():
        assert sum(weights.values()) == pytest.approx(1.0), sector


def test_transit_hub_coffee_expected_base():
    result = calculate_location_score(Sector.COFFEE, CategoryScores(90, 60, 95, 20))
    assert result.base_score == pytest.approx(75.0)
    assert result.penalty_multiplier == pytest.approx(1.0)
    assert result.final_score == pytest.approx(75.0)
    assert result.structural_band == "strong"


def test_category_bounds():
    with pytest.raises(ValueError):
        CategoryScores(101, 50, 50, 50)
