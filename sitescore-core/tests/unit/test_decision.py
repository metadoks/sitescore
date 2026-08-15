from sitescore.config.sectors import Sector
from sitescore.engines.decision import calculate_decision
from sitescore.engines.financial import calculate_financial_metrics
from sitescore.engines.location import calculate_location_score
from sitescore.engines.revenue import scenarios
from sitescore.schemas.location import CategoryScores


def _financial_for_bec(target_bec: float):
    # Coffee CMR=0.70. FC=700 => break-even=1000, so base revenue = target_bec*1000.
    return calculate_financial_metrics(
        Sector.COFFEE,
        scenarios(target_bec * 800, target_bec * 1000, target_bec * 1200),
        rent=0,
        fixed_labor=700,
        fixed_overhead=0,
    )


def _location(score: float):
    # Equal category scores above dealbreaker thresholds => final score == requested score.
    return calculate_location_score(Sector.COFFEE, CategoryScores(score, score, score, score))


def test_all_decision_cells():
    cases = [
        (80, 1.6, "prime_opportunity"),
        (80, 1.2, "strong_site_thin_economics"),
        (80, 0.9, "tourist_trap"),
        (60, 1.6, "hidden_gem"),
        (60, 1.2, "conditional_site"),
        (60, 0.9, "weak_site_weak_economics"),
        (40, 1.6, "structural_risk"),
        (40, 0.9, "dead_end"),
    ]
    for loc, bec, expected in cases:
        decision = calculate_decision(_location(loc), _financial_for_bec(bec))
        assert decision.decision_class == expected


def test_stress_flag_is_modifier_not_class_override():
    loc = _location(80)
    fin = calculate_financial_metrics(
        Sector.COFFEE,
        scenarios(900, 1600, 2200),
        rent=0,
        fixed_labor=700,
        fixed_overhead=0,
    )
    result = calculate_decision(loc, fin)
    assert result.decision_class == "prime_opportunity"
    assert "STRESS_TEST_FAILED" in result.risk_flags
