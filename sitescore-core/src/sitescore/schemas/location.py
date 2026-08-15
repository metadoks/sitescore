from dataclasses import dataclass


def _bounded(name: str, value: float, low: float = 0.0, high: float = 100.0) -> float:
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}; got {value}")
    return value


@dataclass(frozen=True, slots=True)
class CategoryScores:
    demand: float
    competition: float
    accessibility: float
    economics: float

    def __post_init__(self):
        for field in ("demand", "competition", "accessibility", "economics"):
            object.__setattr__(self, field, _bounded(field, getattr(self, field)))

    def as_dict(self) -> dict[str, float]:
        return {
            "demand": self.demand,
            "competition": self.competition,
            "accessibility": self.accessibility,
            "economics": self.economics,
        }


@dataclass(frozen=True, slots=True)
class LocationResult:
    base_score: float
    penalty_multiplier: float
    final_score: float
    structural_band: str
    dominant_risk_category: str | None
