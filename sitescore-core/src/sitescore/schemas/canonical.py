from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from sitescore.schemas.confidence import ConfidenceResult
from sitescore.schemas.decision import DecisionResult
from sitescore.schemas.financial import FinancialResult
from sitescore.schemas.location import LocationResult
from sitescore.schemas.metadata import ModelVersions


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, tuple):
        return [
            _serialize(item)
            for item in value
        ]

    if isinstance(value, list):
        return [
            _serialize(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: _serialize(item)
            for key, item in value.items()
        }

    return value


@dataclass(frozen=True, slots=True)
class CanonicalAnalysisResult:
    analysis_fingerprint: str
    model_versions: ModelVersions

    location: LocationResult
    financial: FinancialResult
    decision: DecisionResult
    confidence: ConfidenceResult

    def to_dict(self) -> dict:
        return _serialize(asdict(self))