from sitescore.config.category_weights import SECTOR_CATEGORY_WEIGHTS
from sitescore.config.dealbreakers import get_rule
from sitescore.config.decision_rules import LOCATION_CONDITIONAL_MIN, LOCATION_STRONG_MIN
from sitescore.config.sectors import Category, Sector
from sitescore.schemas.location import CategoryScores, LocationResult

from .penalty import calculate_penalty


def structural_band(score: float) -> str:
    if score >= LOCATION_STRONG_MIN:
        return "strong"
    if score >= LOCATION_CONDITIONAL_MIN:
        return "conditional"
    return "weak"


def calculate_location_score(sector: Sector, scores: CategoryScores) -> LocationResult:
    weights = SECTOR_CATEGORY_WEIGHTS[sector]
    values = {
        Category.DEMAND: scores.demand,
        Category.COMPETITION: scores.competition,
        Category.ACCESSIBILITY: scores.accessibility,
        Category.ECONOMICS: scores.economics,
    }
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError(f"Category weights for {sector} must sum to 1.0")

    base_score = sum(weights[c] * values[c] for c in Category)

    penalties: dict[Category, float] = {}
    for category in Category:
        rule = get_rule(sector, category)
        penalties[category] = calculate_penalty(
            values[category], rule.threshold, rule.max_penalty
        )

    dominant = min(penalties, key=penalties.get)
    final_multiplier = penalties[dominant]
    final_score = base_score * final_multiplier

    return LocationResult(
        base_score=round(base_score, 6),
        penalty_multiplier=round(final_multiplier, 6),
        final_score=round(final_score, 6),
        structural_band=structural_band(final_score),
        dominant_risk_category=None if final_multiplier == 1.0 else dominant.value,
    )
