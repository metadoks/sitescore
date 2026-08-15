from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecisionResult:
    decision_class: str
    structural_band: str
    financial_band: str
    headline: str
    risk_flags: tuple[str, ...]
