from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from weakref import WeakValueDictionary

from sitescore_data.enums import PipelineStatus
from sitescore_data.schemas.features import NormalizedLocationFeatures
from sitescore_data.schemas.pipeline import RealDataPipelineResult
from sitescore_data.schemas.readiness import ScoringReadinessReason, ScoringReadinessResult


class ApplicationScoringGateState(StrEnum):
    ELIGIBLE = "eligible"
    NOT_SCORE_READY = "not_score_ready"
    PIPELINE_ERROR = "pipeline_error"
    INCONSISTENT_TERMINAL_STATE = "inconsistent_terminal_state"


class ApplicationScoringGateReason(StrEnum):
    PIPELINE_NOT_SCORE_READY = "pipeline_not_score_ready"
    PIPELINE_ERROR = "pipeline_error"
    READINESS_MISSING = "readiness_missing"
    READINESS_FALSE = "readiness_false"
    NORMALIZED_FEATURES_MISSING = "normalized_features_missing"


@dataclass(frozen=True, slots=True)
class ApplicationScoringEligibility:
    pipeline_result: RealDataPipelineResult
    state: ApplicationScoringGateState
    reason_codes: tuple[ApplicationScoringGateReason, ...]
    upstream_readiness_reasons: tuple[ScoringReadinessReason, ...]

    @property
    def is_eligible(self) -> bool:
        return self.state is ApplicationScoringGateState.ELIGIBLE


class ApplicationScoringBlocked(RuntimeError):
    def __init__(self, eligibility: ApplicationScoringEligibility) -> None:
        self.eligibility = eligibility
        super().__init__(f"application scoring blocked: {eligibility.state.value}")


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ApplicationScoringInput:
    """Factory-owned capability binding a trusted terminal pipeline result.

    This is not a category-score DTO and does not mean scoring has occurred.
    Future scoring adapters must validate this capability with
    ``require_canonical_application_scoring_input`` before use.
    """

    pipeline_result: RealDataPipelineResult

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApplicationScoringInput is factory-owned; use "
            "build_application_scoring_input"
        )

    @property
    def sector_key(self):
        return self.pipeline_result.sector_key

    @property
    def normalized_features(self) -> NormalizedLocationFeatures:
        value = self.pipeline_result.normalized_features
        if not isinstance(value, NormalizedLocationFeatures):
            raise RuntimeError("canonical application scoring input lost normalized features")
        return value

    @property
    def readiness_fingerprint(self) -> str:
        readiness = self.pipeline_result.scoring_readiness
        if not isinstance(readiness, ScoringReadinessResult):
            raise RuntimeError("canonical application scoring input lost readiness")
        return readiness.readiness_fingerprint


def evaluate_application_scoring_gate(
    pipeline_result: RealDataPipelineResult,
) -> ApplicationScoringEligibility:
    if not isinstance(pipeline_result, RealDataPipelineResult):
        raise TypeError("pipeline_result must be a RealDataPipelineResult")

    readiness = pipeline_result.scoring_readiness
    upstream_reasons = (
        readiness.reason_codes
        if isinstance(readiness, ScoringReadinessResult)
        else ()
    )

    if pipeline_result.status is PipelineStatus.PIPELINE_ERROR:
        return ApplicationScoringEligibility(
            pipeline_result=pipeline_result,
            state=ApplicationScoringGateState.PIPELINE_ERROR,
            reason_codes=(ApplicationScoringGateReason.PIPELINE_ERROR,),
            upstream_readiness_reasons=(),
        )

    if pipeline_result.status is PipelineStatus.NOT_SCORE_READY:
        return ApplicationScoringEligibility(
            pipeline_result=pipeline_result,
            state=ApplicationScoringGateState.NOT_SCORE_READY,
            reason_codes=(ApplicationScoringGateReason.PIPELINE_NOT_SCORE_READY,),
            upstream_readiness_reasons=upstream_reasons,
        )

    reasons: list[ApplicationScoringGateReason] = []
    if not isinstance(readiness, ScoringReadinessResult):
        reasons.append(ApplicationScoringGateReason.READINESS_MISSING)
    elif readiness.is_score_ready is not True:
        reasons.append(ApplicationScoringGateReason.READINESS_FALSE)

    if not isinstance(pipeline_result.normalized_features, NormalizedLocationFeatures):
        reasons.append(ApplicationScoringGateReason.NORMALIZED_FEATURES_MISSING)

    if reasons:
        return ApplicationScoringEligibility(
            pipeline_result=pipeline_result,
            state=ApplicationScoringGateState.INCONSISTENT_TERMINAL_STATE,
            reason_codes=tuple(reasons),
            upstream_readiness_reasons=upstream_reasons,
        )

    return ApplicationScoringEligibility(
        pipeline_result=pipeline_result,
        state=ApplicationScoringGateState.ELIGIBLE,
        reason_codes=(),
        upstream_readiness_reasons=(),
    )


def _install_application_scoring_input_factory():
    registry: WeakValueDictionary[int, ApplicationScoringInput] = WeakValueDictionary()

    def build(
        pipeline_result: RealDataPipelineResult,
    ) -> ApplicationScoringInput:
        eligibility = evaluate_application_scoring_gate(pipeline_result)
        if not eligibility.is_eligible:
            raise ApplicationScoringBlocked(eligibility)

        value = object.__new__(ApplicationScoringInput)
        object.__setattr__(value, "pipeline_result", pipeline_result)
        registry[id(value)] = value
        return value

    def require(value: ApplicationScoringInput) -> ApplicationScoringInput:
        if not isinstance(value, ApplicationScoringInput):
            raise TypeError("value must be an ApplicationScoringInput")
        if registry.get(id(value)) is not value:
            raise ValueError("application scoring input is not canonical/factory-owned")
        return value

    return build, require


(
    build_application_scoring_input,
    require_canonical_application_scoring_input,
) = _install_application_scoring_input_factory()
del _install_application_scoring_input_factory
