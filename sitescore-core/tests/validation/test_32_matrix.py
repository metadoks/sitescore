from sitescore.config.sectors import Sector
from sitescore.engines.location import calculate_location_score
from tests.validation.archetypes import ARCHETYPES


def test_all_32_archetype_sector_combinations_are_valid():
    results = []
    for sector in Sector:
        for name, scores in ARCHETYPES.items():
            result = calculate_location_score(sector, scores)
            assert 0 <= result.base_score <= 100
            assert 0 <= result.penalty_multiplier <= 1
            assert 0 <= result.final_score <= 100
            results.append((sector, name, result.final_score))
    assert len(results) == 32
