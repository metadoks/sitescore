"""SiteScore real-data typed contracts and validation foundation."""

from .enums import (
    AvailabilityState,
    BenchmarkPopulationType,
    CalibrationState,
    DataQualityState,
    EligibilityState,
    GeographyType,
    PersistenceClass,
    PipelineStatus,
    ScoreEligibility,
    SpatialRepresentation,
    ValidityState,
)
from .validation import SectorKey
from .version import (
    BENCHMARK_SCHEMA_VERSION,
    DATA_FEATURE_CONTRACT_VERSION,
    DATA_SCHEMA_VERSION,
    DATA_SERIALIZATION_VERSION,
    PACKAGE_VERSION,
    READINESS_CONTRACT_VERSION,
)

__all__ = [
    "AvailabilityState",
    "BenchmarkPopulationType",
    "CalibrationState",
    "DataQualityState",
    "EligibilityState",
    "GeographyType",
    "PersistenceClass",
    "PipelineStatus",
    "ScoreEligibility",
    "SpatialRepresentation",
    "SectorKey",
    "ValidityState",
    "PACKAGE_VERSION",
    "DATA_SCHEMA_VERSION",
    "BENCHMARK_SCHEMA_VERSION",
    "DATA_FEATURE_CONTRACT_VERSION",
    "READINESS_CONTRACT_VERSION",
    "DATA_SERIALIZATION_VERSION",
]
