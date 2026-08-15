"""Public typed schemas available in the SiteScore data-contract package."""

from .benchmarks import BenchmarkReference, CommercialBenchmarkFrameMetadata
from .common import DataContractVersions, MetricValue, SourceMetadata
from .competition import CompetitionCurve, CompetitionObservation, CompetitionSnapshot
from .demographics import AgeCohortPopulation, DemographicSnapshot
from .features import (
    DerivedLocationMetrics,
    NormalizedLocationFeatures,
    ReadyCategoryScorePayload,
)
from .geography import GeographyRef, ResolvedLocation
from .parking import ParkingAccessClass, ParkingMode, ParkingObservation, ParkingSnapshot
from .pedestrian import IsochroneSnapshot, PedestrianCatchmentArtifact
from .pipeline import PipelineReason, RealDataPipelineResult
from .road import RoadAccessSnapshot, RoadObservation, RoadOriginQuality
from .readiness import (
    ApprovedFallbackPolicyRef,
    FeatureReadinessPolicy,
    PolicyVersionRef,
    ReadinessCompatibilityInput,
    ScoringFeatureReadiness,
    ScoringReadinessReason,
    ScoringReadinessResult,
)
from .transit import (
    TransitObservation,
    TransitServiceWindow,
    TransitSnapshot,
    TransitStopRef,
)

__all__ = [
    "AgeCohortPopulation",
    "ApprovedFallbackPolicyRef",
    "BenchmarkReference",
    "CommercialBenchmarkFrameMetadata",
    "CompetitionCurve",
    "CompetitionObservation",
    "CompetitionSnapshot",
    "DataContractVersions",
    "DerivedLocationMetrics",
    "DemographicSnapshot",
    "GeographyRef",
    "IsochroneSnapshot",
    "MetricValue",
    "NormalizedLocationFeatures",
    "ParkingAccessClass",
    "ParkingMode",
    "ParkingObservation",
    "ParkingSnapshot",
    "PedestrianCatchmentArtifact",
    "PipelineReason",
    "ReadyCategoryScorePayload",
    "RealDataPipelineResult",
    "FeatureReadinessPolicy",
    "PolicyVersionRef",
    "ReadinessCompatibilityInput",
    "ScoringFeatureReadiness",
    "ScoringReadinessReason",
    "ScoringReadinessResult",
    "ResolvedLocation",
    "RoadAccessSnapshot",
    "RoadObservation",
    "RoadOriginQuality",
    "SourceMetadata",
    "TransitObservation",
    "TransitServiceWindow",
    "TransitSnapshot",
    "TransitStopRef",
]
