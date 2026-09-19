from dataclasses import replace

from sitescore.config.sectors import Sector
from sitescore.engines.location import calculate_location_score
from sitescore.schemas.location import CategoryScores
from tests.validation.archetypes import ARCHETYPES


def test_location_score_monotonicity():
    for sector in Sector:
        for base in ARCHETYPES.values():
            for field in ("demand", "competition", "accessibility", "economics"):
                previous = None
                for score in range(0, 101):
                    candidate = replace(base, **{field: score})
                    current = calculate_location_score(sector, candidate).final_score
                    if previous is not None:
                        assert current >= previous - 1e-9, (sector, field, score, previous, current)
                    previous = current
