from sitescore.config.sectors import Sector
from sitescore.engines.location import calculate_location_score
from tests.validation.archetypes import ARCHETYPES


def _dominates(a, b):
    av = a.as_dict().values()
    bv = b.as_dict().values()
    pairs = list(zip(av, bv))
    return all(x >= y for x, y in pairs) and any(x > y for x, y in pairs)


def test_pareto_dominance_after_penalty():
    items = list(ARCHETYPES.items())
    for sector in Sector:
        for name_a, a in items:
            for name_b, b in items:
                if _dominates(a, b):
                    sa = calculate_location_score(sector, a).final_score
                    sb = calculate_location_score(sector, b).final_score
                    assert sa >= sb - 1e-9, (sector, name_a, name_b, sa, sb)
