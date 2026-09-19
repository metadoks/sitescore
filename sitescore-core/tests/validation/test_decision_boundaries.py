from sitescore.config.sectors import Sector
from sitescore.engines.decision import calculate_decision
from sitescore.engines.financial import calculate_financial_metrics
from sitescore.engines.location import calculate_location_score
from sitescore.engines.revenue import scenarios
from sitescore.schemas.location import CategoryScores


def _loc(x):
    return calculate_location_score(Sector.COFFEE, CategoryScores(x, x, x, x))


def _fin(bec):
    # BE revenue is exactly 1000.
    return calculate_financial_metrics(
        Sector.COFFEE,
        scenarios(max(0, bec * 800), bec * 1000, bec * 1200),
        rent=0,
        fixed_labor=700,
        fixed_overhead=0,
    )


def test_location_boundary_75():
    assert calculate_decision(_loc(75), _fin(1.5)).decision_class == "prime_opportunity"
    assert calculate_decision(_loc(74.999), _fin(1.5)).decision_class == "hidden_gem"


def test_location_boundary_50():
    assert calculate_decision(_loc(50), _fin(1.5)).decision_class == "hidden_gem"
    assert calculate_decision(_loc(49.999), _fin(1.5)).decision_class == "structural_risk"


def test_bec_boundaries():
    loc = _loc(80)
    assert calculate_decision(loc, _fin(1.5)).decision_class == "prime_opportunity"
    assert calculate_decision(loc, _fin(1.499)).decision_class == "strong_site_thin_economics"
    assert calculate_decision(loc, _fin(1.0)).decision_class == "strong_site_thin_economics"
    assert calculate_decision(loc, _fin(0.999)).decision_class == "tourist_trap"
