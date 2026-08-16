"""SiteScore FAZ 3.4-8 readiness and terminal pipeline integration."""

from .integration import (
    PIPELINE_VERSION,
    READINESS_VALIDATOR_VERSION,
    BenchmarkReferenceBinding,
    NormalizedFeatureAssembly,
    PipelineStageFailure,
    ReadinessEvaluation,
    assemble_normalized_location_features,
    build_pipeline_error_result,
    build_real_data_pipeline_result,
    derive_scoring_readiness,
)

__all__ = [
    "PIPELINE_VERSION",
    "READINESS_VALIDATOR_VERSION",
    "BenchmarkReferenceBinding",
    "NormalizedFeatureAssembly",
    "PipelineStageFailure",
    "ReadinessEvaluation",
    "assemble_normalized_location_features",
    "derive_scoring_readiness",
    "build_real_data_pipeline_result",
    "build_pipeline_error_result",
]
