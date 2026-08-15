from dataclasses import dataclass
from types import MappingProxyType

from .sectors import Sector


@dataclass(frozen=True, slots=True)
class FinancialPrior:
    variable_cost_ratio: float
    rent_burden_warning_pct: float


FINANCIAL_PRIORS = MappingProxyType({
    Sector.COFFEE: FinancialPrior(0.30, 15.0),
    Sector.RESTAURANT: FinancialPrior(0.35, 12.0),
    Sector.GYM: FinancialPrior(0.05, 25.0),
    Sector.BEAUTY: FinancialPrior(0.55, 15.0),
})
