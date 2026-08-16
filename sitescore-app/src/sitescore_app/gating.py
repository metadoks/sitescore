from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from weakref import WeakValueDictionary

from sitescore_data.enums import PipelineStatus
from sitescore_data.schemas.common import SourceMetadata
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.demographics import DemographicSnapshot
from sitescore_data.schemas.features import DerivedLocationMetrics, NormalizedLocationFeatures
from sitescore_data.schemas.geography import ResolvedLocation
from sitescore_data.schemas.parking import ParkingSnapshot
from sitescore_data.schemas.pedestrian import IsochroneSnapshot, PedestrianCatchmentArtifact
from sitescore_data.schemas.pipeline import RealDataPipelineResult
from sitescore_data.schemas.readiness import ScoringReadinessReason, ScoringReadinessResult
from sitescore_data.schemas.road import RoadAccessSnapshot
from sitescore_data.schemas.transit import TransitSnapshot
from sitescore_data.validation import SectorKey
from sitescore_pipeline import ReadinessEvaluation


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
class ApplicationPipelineResult:
    """Factory-owned proof that the app invoked the frozen canonical terminal factory."""

    pipeline_result: RealDataPipelineResult

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApplicationPipelineResult is factory-owned; use "
            "build_application_pipeline_result"
        )


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ApplicationScoringInput:
    """Factory-owned permission to begin later application scoring.

    The capability retains both the app-owned canonical pipeline execution proof
    and the exact frozen terminal result. It is not a category-score DTO and does
    not mean scoring has occurred.
    """

    application_pipeline_result: ApplicationPipelineResult

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApplicationScoringInput is factory-owned; use "
            "build_application_scoring_input"
        )

    @property
    def pipeline_result(self) -> RealDataPipelineResult:
        return self.application_pipeline_result.pipeline_result

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
    """Describe terminal state only; this function does not grant authority."""
    if not isinstance(pipeline_result, RealDataPipelineResult):
        raise TypeError("pipeline_result must be a RealDataPipelineResult")

    readiness = pipeline_result.scoring_readiness
    upstream_reasons = (
        readiness.reason_codes if isinstance(readiness, ScoringReadinessResult) else ()
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


def _install_application_factories():
    # Import inside the installer so the exact frozen factory is captured only in
    # closure state. No module-global alias/token becomes an authorization surface.
    from sitescore_pipeline import build_real_data_pipeline_result as canonical_terminal_factory

    pipeline_registry: WeakValueDictionary[int, ApplicationPipelineResult] = WeakValueDictionary()
    scoring_registry: WeakValueDictionary[int, ApplicationScoringInput] = WeakValueDictionary()

    def require_pipeline_result(value: ApplicationPipelineResult) -> ApplicationPipelineResult:
        if not isinstance(value, ApplicationPipelineResult):
            raise TypeError("value must be an ApplicationPipelineResult")
        if pipeline_registry.get(id(value)) is not value:
            raise ValueError("application pipeline result is not canonical/factory-owned")
        return value

    def build_pipeline_result(
        *,
        readiness: ReadinessEvaluation,
        sector_key: SectorKey,
        resolved_location: ResolvedLocation | None,
        derived_metrics: DerivedLocationMetrics,
        source_metadata: tuple[SourceMetadata, ...],
        generated_at: datetime,
        demographics: DemographicSnapshot | None = None,
        pedestrian_catchment: PedestrianCatchmentArtifact | None = None,
        isochrone: IsochroneSnapshot | None = None,
        competition: CompetitionSnapshot | None = None,
        transit: TransitSnapshot | None = None,
        road: RoadAccessSnapshot | None = None,
        parking: ParkingSnapshot | None = None,
    ) -> ApplicationPipelineResult:
        terminal = canonical_terminal_factory(
            readiness=readiness,
            sector_key=sector_key,
            resolved_location=resolved_location,
            derived_metrics=derived_metrics,
            source_metadata=source_metadata,
            generated_at=generated_at,
            demographics=demographics,
            pedestrian_catchment=pedestrian_catchment,
            isochrone=isochrone,
            competition=competition,
            transit=transit,
            road=road,
            parking=parking,
        )
        value = object.__new__(ApplicationPipelineResult)
        object.__setattr__(value, "pipeline_result", terminal)
        pipeline_registry[id(value)] = value
        return value

    def build_scoring_input(
        application_pipeline_result: ApplicationPipelineResult,
    ) -> ApplicationScoringInput:
        canonical_app_result = require_pipeline_result(application_pipeline_result)
        eligibility = evaluate_application_scoring_gate(canonical_app_result.pipeline_result)
        if not eligibility.is_eligible:
            raise ApplicationScoringBlocked(eligibility)

        value = object.__new__(ApplicationScoringInput)
        object.__setattr__(value, "application_pipeline_result", canonical_app_result)
        scoring_registry[id(value)] = value
        return value

    def require_scoring_input(value: ApplicationScoringInput) -> ApplicationScoringInput:
        if not isinstance(value, ApplicationScoringInput):
            raise TypeError("value must be an ApplicationScoringInput")
        if scoring_registry.get(id(value)) is not value:
            raise ValueError("application scoring input is not canonical/factory-owned")
        require_pipeline_result(value.application_pipeline_result)
        return value

    return build_pipeline_result, require_pipeline_result, build_scoring_input, require_scoring_input


(
    build_application_pipeline_result,
    require_canonical_application_pipeline_result,
    build_application_scoring_input,
    require_canonical_application_scoring_input,
) = _install_application_factories()
del _install_application_factories
