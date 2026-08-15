import pytest

from sitescore.config.sectors import Sector
from sitescore.engines.financial import (
    calculate_financial_metrics,
)
from sitescore.schemas.financial import (
    RevenueScenarios,
)


def test_operating_profit_identity():
    revenue = RevenueScenarios(
        conservative=20000,
        base=30000,
        optimistic=40000,
    )

    result = calculate_financial_metrics(
        sector=Sector.COFFEE,
        revenue=revenue,
        rent=4000,
        fixed_labor=5000,
        fixed_overhead=1000,
        unit_price=10,
    )

    expected_profit = (
        result.revenue.base
        - result.variable_cost_base
        - result.fixed_costs
    )

    assert result.operating_profit_base == pytest.approx(
        expected_profit
    )


def test_fixed_cost_identity():
    revenue = RevenueScenarios(
        conservative=20000,
        base=30000,
        optimistic=40000,
    )

    result = calculate_financial_metrics(
        sector=Sector.COFFEE,
        revenue=revenue,
        rent=4000,
        fixed_labor=5000,
        fixed_overhead=1000,
        unit_price=10,
    )

    assert result.fixed_costs == pytest.approx(
        10000
    )


def test_contribution_margin_identity():
    revenue = RevenueScenarios(
        conservative=20000,
        base=30000,
        optimistic=40000,
    )

    result = calculate_financial_metrics(
        sector=Sector.COFFEE,
        revenue=revenue,
        rent=4000,
        fixed_labor=5000,
        fixed_overhead=1000,
        unit_price=10,
    )

    expected_cm = (
        result.revenue.base
        - result.variable_cost_base
    )

    assert (
        result.contribution_margin_base
        == pytest.approx(expected_cm)
    )


def test_break_even_identity():
    revenue = RevenueScenarios(
        conservative=20000,
        base=30000,
        optimistic=40000,
    )

    result = calculate_financial_metrics(
        sector=Sector.COFFEE,
        revenue=revenue,
        rent=4000,
        fixed_labor=5000,
        fixed_overhead=1000,
        unit_price=10,
    )

    # Coffee V1 CMR = 70%
    expected_break_even = (
        result.fixed_costs / 0.70
    )

    assert (
        result.break_even_revenue
        == pytest.approx(expected_break_even)
    )
    def test_revenue_scenario_ordering_preserved():
        revenue = RevenueScenarios(
            conservative=20000,
            base=30000,
            optimistic=40000,
    )

        result = calculate_financial_metrics(
            sector=Sector.COFFEE,
            revenue=revenue,
            rent=4000,
            fixed_labor=5000,
            fixed_overhead=1000,
            unit_price=10,
    )

    assert (
        result.revenue.conservative
        <= result.revenue.base
        <= result.revenue.optimistic
    )

    def test_bec_identity():
        revenue = RevenueScenarios(
        conservative=20000,
        base=30000,
        optimistic=40000,
    )

    result = calculate_financial_metrics(
        sector=Sector.COFFEE,
        revenue=revenue,
        rent=4000,
        fixed_labor=5000,
        fixed_overhead=1000,
        unit_price=10,
    )

    assert result.bec_base == pytest.approx(
        result.revenue.base
        / result.break_even_revenue
    )

    assert result.bec_conservative == pytest.approx(
        result.revenue.conservative
        / result.break_even_revenue
    )

    def test_rent_burden_identity():
        revenue = RevenueScenarios(
        conservative=20000,
        base=30000,
        optimistic=40000,
    )

    result = calculate_financial_metrics(
        sector=Sector.COFFEE,
        revenue=revenue,
        rent=4000,
        fixed_labor=5000,
        fixed_overhead=1000,
        unit_price=10,
    )

    expected = (
        4000 / 30000
    ) * 100

    assert result.rent_burden_pct == pytest.approx(
        expected
    )

    def test_operating_margin_identity():
        revenue = RevenueScenarios(
        conservative=20000,
        base=30000,
        optimistic=40000,
    )

    result = calculate_financial_metrics(
        sector=Sector.COFFEE,
        revenue=revenue,
        rent=4000,
        fixed_labor=5000,
        fixed_overhead=1000,
        unit_price=10,
    )

    expected = (
        result.operating_profit_base
        / result.revenue.base
    ) * 100

    assert result.operating_margin_pct == pytest.approx(
        expected
    )