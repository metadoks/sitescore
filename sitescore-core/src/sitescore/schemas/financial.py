from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RevenueScenarios:
    conservative: float
    base: float
    optimistic: float

    def __post_init__(self):
        if min(self.conservative, self.base, self.optimistic) < 0:
            raise ValueError("Revenue scenarios cannot be negative")
        if not (self.conservative <= self.base <= self.optimistic):
            raise ValueError("Revenue scenarios must satisfy conservative <= base <= optimistic")


@dataclass(frozen=True, slots=True)
class FinancialResult:
    revenue: RevenueScenarios
    variable_cost_base: float
    contribution_margin_base: float
    fixed_costs: float
    operating_profit_base: float
    break_even_revenue: float
    bec_base: float
    bec_conservative: float
    rent_burden_pct: float
    rent_burden_severity: str
    operating_margin_pct: float
    break_even_volume: float | None
    stress_test_failed: bool
