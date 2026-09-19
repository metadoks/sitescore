from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from datetime import datetime
from enum import Enum, StrEnum
from weakref import ref

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

    The capability retains the exact construction-time pipeline authority that
    earned permission. It is not a category-score DTO and does not mean scoring
    has occurred.
    """

    application_pipeline_result: ApplicationPipelineResult

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApplicationScoringInput is factory-owned; use "
            "build_application_scoring_input"
        )

    @property
    def pipeline_result(self) -> RealDataPipelineResult:
        raise RuntimeError("application scoring authority resolver not installed")

    @property
    def sector_key(self):
        raise RuntimeError("application scoring authority resolver not installed")

    @property
    def normalized_features(self) -> NormalizedLocationFeatures:
        raise RuntimeError("application scoring authority resolver not installed")

    @property
    def readiness_fingerprint(self) -> str:
        raise RuntimeError("application scoring authority resolver not installed")


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

    pipeline_bindings: dict[int, tuple[object, ...]] = {}
    scoring_bindings: dict[int, tuple[object, ...]] = {}

    def semantic_record(value: object) -> object:
        """Return a deterministic immutable semantic record for authority attestation."""
        if value is None:
            return ("none",)
        if isinstance(value, Enum):
            return ("enum", type(value).__module__, type(value).__qualname__, value.value)
        if isinstance(value, datetime):
            return ("datetime", value.isoformat())
        if isinstance(value, (str, int, float, bool)):
            return ("scalar", type(value).__name__, value)
        if isinstance(value, tuple):
            return ("tuple", tuple(semantic_record(item) for item in value))
        if isinstance(value, list):
            return ("list", tuple(semantic_record(item) for item in value))
        if isinstance(value, dict):
            items = tuple(
                sorted(
                    (
                        repr(semantic_record(key)),
                        semantic_record(key),
                        semantic_record(item),
                    )
                    for key, item in value.items()
                )
            )
            return ("dict", items)
        if isinstance(value, (set, frozenset)):
            items = tuple(sorted(repr(semantic_record(item)) for item in value))
            return ("set", items)
        if is_dataclass(value):
            field_records = []
            for field in dataclass_fields(value):
                try:
                    field_value = getattr(value, field.name)
                except AttributeError:
                    field_records.append((field.name, ("missing_field", field.name)))
                else:
                    field_records.append((field.name, semantic_record(field_value)))
            return (
                "dataclass",
                type(value).__module__,
                type(value).__qualname__,
                tuple(field_records),
            )
        raise TypeError(
            "unsupported authority semantic value type: "
            f"{type(value).__module__}.{type(value).__qualname__}"
        )

    def terminal_authority_record(
        terminal: RealDataPipelineResult,
    ) -> tuple[object, ...]:
        return (
            "application_terminal_authority_v2",
            semantic_record(terminal.status),
            semantic_record(terminal.sector_key),
            semantic_record(terminal.normalized_features),
            semantic_record(terminal.scoring_readiness),
        )

    def register_pipeline_binding(
        value: ApplicationPipelineResult,
        terminal: RealDataPipelineResult,
    ) -> None:
        object_id = id(value)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            pipeline_bindings.pop(object_id, None)

        readiness = terminal.scoring_readiness
        readiness_flag = (
            readiness.is_score_ready
            if isinstance(readiness, ScoringReadinessResult)
            else None
        )
        readiness_reasons = (
            readiness.reason_codes
            if isinstance(readiness, ScoringReadinessResult)
            else ()
        )
        readiness_fingerprint = (
            readiness.readiness_fingerprint
            if isinstance(readiness, ScoringReadinessResult)
            else None
        )
        pipeline_bindings[object_id] = (
            ref(value, cleanup),
            terminal,
            terminal_authority_record(terminal),
            terminal.status,
            terminal.sector_key,
            terminal.normalized_features,
            readiness_flag,
            readiness_reasons,
            readiness_fingerprint,
        )

    def resolve_pipeline_binding(
        value: ApplicationPipelineResult,
    ) -> tuple[object, ...]:
        if not isinstance(value, ApplicationPipelineResult):
            raise TypeError("value must be an ApplicationPipelineResult")
        binding = pipeline_bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("application pipeline result is not canonical/factory-owned")

        terminal = binding[1]
        if not isinstance(terminal, RealDataPipelineResult):
            raise RuntimeError("canonical application pipeline binding corrupted")
        if value.pipeline_result is not terminal:
            raise ValueError("application pipeline result integrity violation")

        try:
            current_record = terminal_authority_record(terminal)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                "application pipeline result semantic integrity violation"
            ) from exc
        if current_record != binding[2]:
            raise ValueError("application pipeline result semantic integrity violation")
        return binding

    def resolve_pipeline_result(
        value: ApplicationPipelineResult,
    ) -> RealDataPipelineResult:
        terminal = resolve_pipeline_binding(value)[1]
        if not isinstance(terminal, RealDataPipelineResult):
            raise RuntimeError("canonical application pipeline binding corrupted")
        return terminal

    def require_pipeline_result(
        value: ApplicationPipelineResult,
    ) -> ApplicationPipelineResult:
        resolve_pipeline_binding(value)
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
        register_pipeline_binding(value, terminal)
        return value

    def bound_gate(binding: tuple[object, ...]) -> ApplicationScoringEligibility:
        terminal = binding[1]
        status = binding[3]
        normalized_features = binding[5]
        readiness_flag = binding[6]
        readiness_reasons = binding[7]

        if not isinstance(terminal, RealDataPipelineResult):
            raise RuntimeError("canonical application pipeline binding corrupted")
        if status is PipelineStatus.PIPELINE_ERROR:
            return ApplicationScoringEligibility(
                pipeline_result=terminal,
                state=ApplicationScoringGateState.PIPELINE_ERROR,
                reason_codes=(ApplicationScoringGateReason.PIPELINE_ERROR,),
                upstream_readiness_reasons=(),
            )
        if status is PipelineStatus.NOT_SCORE_READY:
            return ApplicationScoringEligibility(
                pipeline_result=terminal,
                state=ApplicationScoringGateState.NOT_SCORE_READY,
                reason_codes=(ApplicationScoringGateReason.PIPELINE_NOT_SCORE_READY,),
                upstream_readiness_reasons=readiness_reasons,
            )

        reasons: list[ApplicationScoringGateReason] = []
        if readiness_flag is None:
            reasons.append(ApplicationScoringGateReason.READINESS_MISSING)
        elif readiness_flag is not True:
            reasons.append(ApplicationScoringGateReason.READINESS_FALSE)
        if not isinstance(normalized_features, NormalizedLocationFeatures):
            reasons.append(ApplicationScoringGateReason.NORMALIZED_FEATURES_MISSING)
        if reasons:
            return ApplicationScoringEligibility(
                pipeline_result=terminal,
                state=ApplicationScoringGateState.INCONSISTENT_TERMINAL_STATE,
                reason_codes=tuple(reasons),
                upstream_readiness_reasons=readiness_reasons,
            )
        return ApplicationScoringEligibility(
            pipeline_result=terminal,
            state=ApplicationScoringGateState.ELIGIBLE,
            reason_codes=(),
            upstream_readiness_reasons=(),
        )

    def register_scoring_binding(
        value: ApplicationScoringInput,
        application_pipeline_result: ApplicationPipelineResult,
        pipeline_binding: tuple[object, ...],
    ) -> None:
        object_id = id(value)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            scoring_bindings.pop(object_id, None)

        scoring_bindings[object_id] = (
            ref(value, cleanup),
            application_pipeline_result,
            pipeline_binding[1],
            pipeline_binding[2],
            pipeline_binding[4],
            pipeline_binding[5],
            pipeline_binding[8],
        )

    def build_scoring_input(
        application_pipeline_result: ApplicationPipelineResult,
    ) -> ApplicationScoringInput:
        pipeline_binding = resolve_pipeline_binding(application_pipeline_result)
        eligibility = bound_gate(pipeline_binding)
        if not eligibility.is_eligible:
            raise ApplicationScoringBlocked(eligibility)

        value = object.__new__(ApplicationScoringInput)
        object.__setattr__(
            value,
            "application_pipeline_result",
            application_pipeline_result,
        )
        register_scoring_binding(
            value,
            application_pipeline_result,
            pipeline_binding,
        )
        return value

    def resolve_scoring_authority(
        value: ApplicationScoringInput,
    ) -> tuple[RealDataPipelineResult, SectorKey, NormalizedLocationFeatures, str]:
        if not isinstance(value, ApplicationScoringInput):
            raise TypeError("value must be an ApplicationScoringInput")
        binding = scoring_bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("application scoring input is not canonical/factory-owned")

        application_pipeline_result = binding[1]
        if not isinstance(application_pipeline_result, ApplicationPipelineResult):
            raise RuntimeError("canonical application scoring binding corrupted")
        if value.application_pipeline_result is not application_pipeline_result:
            raise ValueError("application scoring input integrity violation")

        pipeline_binding = resolve_pipeline_binding(application_pipeline_result)
        if (
            pipeline_binding[1] is not binding[2]
            or pipeline_binding[2] != binding[3]
            or pipeline_binding[4] is not binding[4]
            or pipeline_binding[5] is not binding[5]
            or pipeline_binding[8] != binding[6]
        ):
            raise ValueError("application scoring input semantic integrity violation")

        terminal = binding[2]
        sector_key = binding[4]
        normalized_features = binding[5]
        readiness_fingerprint = binding[6]
        if not isinstance(terminal, RealDataPipelineResult):
            raise RuntimeError("canonical application scoring binding corrupted")
        if not isinstance(sector_key, SectorKey):
            raise RuntimeError("canonical application scoring sector binding corrupted")
        if not isinstance(normalized_features, NormalizedLocationFeatures):
            raise RuntimeError("canonical application scoring feature binding corrupted")
        if not isinstance(readiness_fingerprint, str):
            raise RuntimeError("canonical application scoring readiness binding corrupted")
        return terminal, sector_key, normalized_features, readiness_fingerprint

    def require_scoring_input(
        value: ApplicationScoringInput,
    ) -> ApplicationScoringInput:
        resolve_scoring_authority(value)
        return value

    def scoring_pipeline_result(value: ApplicationScoringInput) -> RealDataPipelineResult:
        return resolve_scoring_authority(value)[0]

    def scoring_sector_key(value: ApplicationScoringInput):
        return resolve_scoring_authority(value)[1]

    def scoring_normalized_features(
        value: ApplicationScoringInput,
    ) -> NormalizedLocationFeatures:
        return resolve_scoring_authority(value)[2]

    def scoring_readiness_fingerprint(value: ApplicationScoringInput) -> str:
        return resolve_scoring_authority(value)[3]

    ApplicationScoringInput.pipeline_result = property(scoring_pipeline_result)
    ApplicationScoringInput.sector_key = property(scoring_sector_key)
    ApplicationScoringInput.normalized_features = property(scoring_normalized_features)
    ApplicationScoringInput.readiness_fingerprint = property(
        scoring_readiness_fingerprint
    )

    return (
        build_pipeline_result,
        require_pipeline_result,
        build_scoring_input,
        require_scoring_input,
    )


(
    build_application_pipeline_result,
    require_canonical_application_pipeline_result,
    build_application_scoring_input,
    require_canonical_application_scoring_input,
) = _install_application_factories()
del _install_application_factories
