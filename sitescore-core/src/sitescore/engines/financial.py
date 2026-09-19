from sitescore.config.financial_priors import FINANCIAL_PRIORS
from sitescore.config.sectors import Sector
from sitescore.schemas.financial import FinancialResult, RevenueScenarios

from .costs import calculate_break_even_revenue, calculate_fixed_costs, calculate_variable_cost


def _rent_severity(rbi: float, threshold: float) -> str:
    if rbi <= threshold:
        return "normal"
    if rbi <= threshold * 1.25:
        return "elevated"
    return "severe"


def calculate_financial_metrics(
    sector: Sector,
    revenue: RevenueScenarios,
    rent: float,
    fixed_labor: float,
    fixed_overhead: float,
    unit_price: float | None = None,
) -> FinancialResult:
    prior = FINANCIAL_PRIORS[sector]
    vcr = prior.variable_cost_ratio
    cmr = 1.0 - vcr

    fixed_costs = calculate_fixed_costs(rent, fixed_labor, fixed_overhead)
    variable_cost_base = calculate_variable_cost(revenue.base, vcr)
    contribution_margin_base = revenue.base - variable_cost_base
    operating_profit_base = contribution_margin_base - fixed_costs
    break_even_revenue = calculate_break_even_revenue(fixed_costs, cmr)

    bec_base = float("inf") if break_even_revenue == 0 else revenue.base / break_even_revenue
    bec_conservative = float("inf") if break_even_revenue == 0 else revenue.conservative / break_even_revenue
    rent_burden_pct = 0.0 if revenue.base == 0 and rent == 0 else (float("inf") if revenue.base == 0 else rent / revenue.base * 100)
    operating_margin_pct = 0.0 if revenue.base == 0 else operating_profit_base / revenue.base * 100

    break_even_volume = None
    if unit_price is not None:
        if unit_price <= 0:
            raise ValueError("unit_price must be > 0")
        break_even_volume = break_even_revenue / unit_price

    return FinancialResult(
        revenue=revenue,
        variable_cost_base=round(variable_cost_base, 6),
        contribution_margin_base=round(contribution_margin_base, 6),
        fixed_costs=round(fixed_costs, 6),
        operating_profit_base=round(operating_profit_base, 6),
        break_even_revenue=round(break_even_revenue, 6),
        bec_base=bec_base if bec_base == float("inf") else round(bec_base, 6),
        bec_conservative=bec_conservative if bec_conservative == float("inf") else round(bec_conservative, 6),
        rent_burden_pct=rent_burden_pct if rent_burden_pct == float("inf") else round(rent_burden_pct, 6),
        rent_burden_severity=_rent_severity(rent_burden_pct, prior.rent_burden_warning_pct),
        operating_margin_pct=round(operating_margin_pct, 6),
        break_even_volume=None if break_even_volume is None else round(break_even_volume, 6),
        stress_test_failed=bec_conservative < 1.0,
    )
