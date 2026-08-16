"""SiteScore FAZ 4 application-domain boundary foundation."""

from .aggregation import (
    ApplicationCategoryAggregationResult,
    aggregate_application_category_scores,
    require_canonical_application_category_aggregation_result,
)
from .gating import (
    ApplicationPipelineResult,
    ApplicationScoringBlocked,
    ApplicationScoringEligibility,
    ApplicationScoringGateReason,
    ApplicationScoringGateState,
    ApplicationScoringInput,
    build_application_pipeline_result,
    build_application_scoring_input,
    evaluate_application_scoring_gate,
    require_canonical_application_pipeline_result,
    require_canonical_application_scoring_input,
)

__all__ = [
    "ApplicationPipelineResult",
    "ApplicationScoringBlocked",
    "ApplicationScoringEligibility",
    "ApplicationScoringGateReason",
    "ApplicationScoringGateState",
    "ApplicationScoringInput",
    "ApplicationCategoryAggregationResult",
    "build_application_pipeline_result",
    "require_canonical_application_pipeline_result",
    "evaluate_application_scoring_gate",
    "build_application_scoring_input",
    "require_canonical_application_scoring_input",
    "aggregate_application_category_scores",
    "require_canonical_application_category_aggregation_result",
]
