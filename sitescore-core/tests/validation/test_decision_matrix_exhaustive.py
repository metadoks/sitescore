import pytest

from sitescore.config.sectors import Sector
from sitescore.engines.decision import (
    calculate_decision,
)
from sitescore.schemas.financial import (
    FinancialResult,
    RevenueScenarios,
)
from sitescore.schemas.location import (
    LocationResult,
)


def make_location(score: float) -> LocationResult:
    if score >= 75:
        band = "strong"
    elif score >= 50:
        band = "conditional"
    else:
        band = "weak"

    return LocationResult(
        base_score=score,
        penalty_multiplier=1.0,
        final_score=score,
        structural_band=band,
        dominant_risk_category=None,
    )


def make_financial(bec: float) -> FinancialResult:
    break_even = 10000
    base_revenue = bec * break_even

    return FinancialResult(
        revenue=RevenueScenarios(
            conservative=base_revenue * 0.8,
            base=base_revenue,
            optimistic=base_revenue * 1.2,
        ),
        variable_cost_base=0,
        contribution_margin_base=base_revenue,
        fixed_costs=10000,
        operating_profit_base=base_revenue - 10000,
        break_even_revenue=break_even,
        bec_base=bec,
        bec_conservative=bec * 0.8,
        rent_burden_pct=10,
        rent_burden_severity="normal",
        operating_margin_pct=0,
        break_even_volume=1000,
        stress_test_failed=(bec * 0.8 < 1),
    )


@pytest.mark.parametrize(
    "location_score,bec,expected",
    [
        (75, 1.50, "prime_opportunity"),
        (75, 1.00, "strong_site_thin_economics"),
        (75, 0.99, "tourist_trap"),

        (50, 1.50, "hidden_gem"),
        (50, 1.00, "conditional_site"),
        (50, 0.99, "weak_site_weak_economics"),

        (49.99, 1.50, "structural_risk"),
        (49.99, 1.00, "structural_risk"),
        (49.99, 0.99, "dead_end"),
    ],
)
def test_decision_matrix_boundaries(
    location_score,
    bec,
    expected,
):
    result = calculate_decision(
        location=make_location(location_score),
        financial=make_financial(bec),
    )

    assert result.decision_class == expected