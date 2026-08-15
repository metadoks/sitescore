from dataclasses import asdict, dataclass

from .confidence import ConfidenceResult
from .decision import DecisionResult
from .financial import FinancialResult
from .location import LocationResult


@dataclass(frozen=True, slots=True)
class ReportResult:
    location: LocationResult
    financial: FinancialResult
    decision: DecisionResult
    confidence: ConfidenceResult

    def to_dict(self) -> dict:
        return asdict(self)
