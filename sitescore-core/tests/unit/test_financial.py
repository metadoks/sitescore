import pytest

from sitescore.config.sectors import Sector
from sitescore.engines.financial import calculate_financial_metrics
from sitescore.engines.revenue import scenarios


def test_coffee_break_even_example():
    revenue = scenarios(12_000, 32_000, 45_000)
    result = calculate_financial_metrics(
        Sector.COFFEE,
        revenue,
        rent=4_000,
        fixed_labor=6_000,
        fixed_overhead=1_500,
        unit_price=8,
    )
    assert result.fixed_costs == pytest.approx(11_500)
    assert result.break_even_revenue == pytest.approx(16_428.571429, rel=1e-6)
    assert result.break_even_volume == pytest.approx(2_053.571429, rel=1e-6)
    assert result.bec_base == pytest.approx(1.947826, rel=1e-6)
    assert result.rent_burden_pct == pytest.approx(12.5)
    assert result.rent_burden_severity == "normal"
    assert result.stress_test_failed is True


def test_negative_fixed_cost_rejected():
    with pytest.raises(ValueError):
        calculate_financial_metrics(
            Sector.COFFEE, scenarios(1, 2, 3), rent=-1, fixed_labor=0, fixed_overhead=0
        )
