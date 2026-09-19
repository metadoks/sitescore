def calculate_variable_cost(revenue: float, variable_cost_ratio: float) -> float:
    if revenue < 0:
        raise ValueError("revenue cannot be negative")
    if not 0 <= variable_cost_ratio < 1:
        raise ValueError("variable_cost_ratio must be in [0, 1)")
    return revenue * variable_cost_ratio


def calculate_fixed_costs(rent: float, fixed_labor: float, fixed_overhead: float) -> float:
    if min(rent, fixed_labor, fixed_overhead) < 0:
        raise ValueError("fixed costs cannot be negative")
    return rent + fixed_labor + fixed_overhead


def calculate_break_even_revenue(fixed_costs: float, contribution_margin_ratio: float) -> float:
    if fixed_costs < 0:
        raise ValueError("fixed_costs cannot be negative")
    if not 0 < contribution_margin_ratio <= 1:
        raise ValueError("contribution_margin_ratio must be in (0, 1]")
    return fixed_costs / contribution_margin_ratio
