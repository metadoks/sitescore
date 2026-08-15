from sitescore.config.decision_rules import (
    BEC_STRONG_MIN,
    BEC_THIN_MIN,
    LOCATION_CONDITIONAL_MIN,
    LOCATION_STRONG_MIN,
)
from sitescore.schemas.decision import DecisionResult
from sitescore.schemas.financial import FinancialResult
from sitescore.schemas.location import LocationResult


def _financial_band(bec: float) -> str:
    if bec >= BEC_STRONG_MIN:
        return "strong"
    if bec >= BEC_THIN_MIN:
        return "thin"
    return "non_viable"


def calculate_decision(location: LocationResult, financial: FinancialResult) -> DecisionResult:
    score = location.final_score
    bec = financial.bec_base

    if score >= LOCATION_STRONG_MIN:
        if bec >= BEC_STRONG_MIN:
            decision_class = "prime_opportunity"
            headline = "Strong Location / Strong Economics"
        elif bec >= BEC_THIN_MIN:
            decision_class = "strong_site_thin_economics"
            headline = "Strong Location / Thin Economics"
        else:
            decision_class = "tourist_trap"
            headline = "Strong Location / Toxic Economics"
    elif score >= LOCATION_CONDITIONAL_MIN:
        if bec >= BEC_STRONG_MIN:
            decision_class = "hidden_gem"
            headline = "Conditional Location / Strong Economics"
        elif bec >= BEC_THIN_MIN:
            decision_class = "conditional_site"
            headline = "Conditional Location / Thin Economics"
        else:
            decision_class = "weak_site_weak_economics"
            headline = "Conditional Location / Weak Economics"
    else:
        if bec >= BEC_THIN_MIN:
            decision_class = "structural_risk"
            headline = "Weak Location / Financially Viable"
        else:
            decision_class = "dead_end"
            headline = "Weak Location / Weak Economics"

    flags: list[str] = []
    if financial.rent_burden_severity == "elevated":
        flags.append("HIGH_RENT_BURDEN")
    elif financial.rent_burden_severity == "severe":
        flags.append("SEVERE_RENT_BURDEN")
    if financial.stress_test_failed:
        flags.append("STRESS_TEST_FAILED")
    if financial.operating_margin_pct < 0:
        flags.append("NEGATIVE_BASE_OPERATING_MARGIN")

    return DecisionResult(
        decision_class=decision_class,
        structural_band=location.structural_band,
        financial_band=_financial_band(bec),
        headline=headline,
        risk_flags=tuple(flags),
    )
