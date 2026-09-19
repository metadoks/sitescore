from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    overall_score: float
    label: str
    geographic_precision: float
    data_vintage: float
    data_coverage: float
    input_completeness: float
