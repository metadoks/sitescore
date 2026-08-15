from sitescore.config.category_weights import SECTOR_CATEGORY_WEIGHTS
from sitescore.config.confidence_rules import (
    CONFIDENCE_WEIGHTS,
    DATA_COVERAGE_LEVELS,
    DATA_VINTAGE_SCORES,
    GEOGRAPHIC_PRECISION_SCORES,
    INPUT_QUALITY_SCORES,
    INPUT_WEIGHTS,
)
from sitescore.config.sectors import Category, Sector
from sitescore.schemas.confidence import ConfidenceResult


def geographic_precision_score(level: str) -> float:
    return GEOGRAPHIC_PRECISION_SCORES.get(level, 0.0)


def data_vintage_score(age_years: int | None) -> float:
    if age_years is None or age_years < 0:
        return 0.0
    if age_years >= 5:
        return 30.0
    return DATA_VINTAGE_SCORES[age_years]


def data_coverage_score(sector: Sector, coverage: dict[str, str]) -> float:
    weights = SECTOR_CATEGORY_WEIGHTS[sector]
    total = 0.0
    for category in Category:
        level = coverage.get(category.value, "missing")
        if level not in DATA_COVERAGE_LEVELS:
            raise ValueError(f"Unknown coverage level: {level}")
        total += weights[category] * DATA_COVERAGE_LEVELS[level]
    return total


def input_completeness_score(qualities: dict[str, str]) -> float:
    total = 0.0
    for name, weight in INPUT_WEIGHTS.items():
        quality = qualities.get(name, "missing")
        if quality not in INPUT_QUALITY_SCORES:
            raise ValueError(f"Unknown input quality: {quality}")
        total += weight * INPUT_QUALITY_SCORES[quality]
    return total


def _label(score: float) -> str:
    if score >= 85:
        return "high"
    if score >= 70:
        return "moderate"
    if score >= 50:
        return "limited"
    return "low"


def calculate_confidence(
    sector: Sector,
    geographic_level: str,
    data_age_years: int | None,
    coverage: dict[str, str],
    input_qualities: dict[str, str],
) -> ConfidenceResult:
    g = geographic_precision_score(geographic_level)
    v = data_vintage_score(data_age_years)
    c = data_coverage_score(sector, coverage)
    i = input_completeness_score(input_qualities)
    overall = (
        CONFIDENCE_WEIGHTS["geographic_precision"] * g
        + CONFIDENCE_WEIGHTS["data_vintage"] * v
        + CONFIDENCE_WEIGHTS["data_coverage"] * c
        + CONFIDENCE_WEIGHTS["input_completeness"] * i
    )
    return ConfidenceResult(
        overall_score=round(overall, 6),
        label=_label(overall),
        geographic_precision=g,
        data_vintage=v,
        data_coverage=round(c, 6),
        input_completeness=round(i, 6),
    )
