from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol

from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
from sitescore_app import (
    ApplicationScoringGateState,
    aggregate_application_category_scores,
    analyze_application_core_input,
    build_application_core_analysis_input,
    build_application_pipeline_result,
    build_application_scoring_input,
    evaluate_application_scoring_gate,
)
from sitescore_benchmarks.composite import evaluate_road_parking_composite
from sitescore_benchmarks.distribution import BenchmarkDistributionArtifact
from sitescore_benchmarks.normalization import (
    build_age_target_concentration_fallback,
    normalize_feature,
)
from sitescore_data.schemas.common import MetricValue, SourceMetadata
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.demographics import DemographicSnapshot
from sitescore_data.schemas.features import DerivedLocationMetrics
from sitescore_data.schemas.geography import ResolvedLocation
from sitescore_data.schemas.pedestrian import IsochroneSnapshot
from sitescore_data.schemas.transit import TransitSnapshot
from sitescore_data.validation import SectorKey
from sitescore_metrics import (
    MeasurementSubject,
    SubjectKind,
    measure_household_income,
    measure_transit_service,
    measure_walkable_reach_area,
    unresolved_competition_pressure,
    unresolved_target_population_density,
    unresolved_walkable_population,
)
from sitescore_pipeline import assemble_normalized_location_features, derive_scoring_readiness

from .errors import CanonicalExecutionFailed, ExecutionConfigurationError
from .ingress import AnalysisIngressCommand
from .outcomes import (
    CanonicalCompletedOutcome,
    CanonicalNotScoreReadyOutcome,
    build_canonical_completed_outcome,
    build_canonical_not_score_ready_outcome,
)


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    resolved_location: ResolvedLocation
    demographics: DemographicSnapshot
    isochrone: IsochroneSnapshot
    competition: CompetitionSnapshot
    transit: TransitSnapshot
    benchmark_distributions: Mapping[str, BenchmarkDistributionArtifact]
    source_metadata: tuple[SourceMetadata, ...]
    geographic_level: GeographicLevel
    data_age_years: int | None
    data_coverage: Mapping[str, CoverageLevel]
    input_qualities: Mapping[str, InputQuality]


class ExecutionEvidenceSource(Protocol):
    """Server/deployment-owned external evidence boundary.

    Implementations acquire provider evidence and load server-owned canonical
    benchmark artifacts. Caller JSON never supplies this authority.
    """

    def acquire(self, command: AnalysisIngressCommand, *, now: datetime) -> ExecutionEvidence: ...


class MissingExecutionEvidenceSource:
    def acquire(self, command: AnalysisIngressCommand, *, now: datetime) -> ExecutionEvidence:
        raise ExecutionConfigurationError("canonical execution evidence source is not configured")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    not_score_ready: CanonicalNotScoreReadyOutcome | None = None
    completed: CanonicalCompletedOutcome | None = None

    def __post_init__(self) -> None:
        if (self.not_score_ready is None) == (self.completed is None):
            raise ValueError("execution result must contain exactly one canonical terminal outcome")


def _site_subject(command: AnalysisIngressCommand, evidence: ExecutionEvidence) -> MeasurementSubject:
    refs = {
        f"geography:{evidence.demographics.geography_ref.geography_id}",
        f"catchment:{evidence.isochrone.catchment_ref}",
        f"competition:{evidence.competition.snapshot_id}",
        f"transit:{evidence.transit.snapshot_id}",
    }
    return MeasurementSubject(
        SubjectKind.SITE,
        "sitescore_api.analysis_site",
        "1.0",
        (("analysis_id", str(command.analysis_id)),),
        tuple(sorted(refs)),
    )


def _unknown_metric(unit: str, reason: str) -> MetricValue:
    from sitescore_data.enums import AvailabilityState, CalibrationState, DataQualityState, ScoreEligibility
    return MetricValue(
        value=None,
        unit=unit,
        availability=AvailabilityState.UNKNOWN,
        data_quality=DataQualityState.MISSING,
        score_eligibility=ScoreEligibility.INELIGIBLE,
        calibration_state=CalibrationState.UNCALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(),
        method_version=None,
        reason_codes=(reason,),
    )


class CanonicalAnalysisExecutor:
    def __init__(self, evidence_source: ExecutionEvidenceSource) -> None:
        self.evidence_source = evidence_source

    def execute(self, command: AnalysisIngressCommand, *, now: datetime) -> ExecutionResult:
        evidence = self.evidence_source.acquire(command, now=now)
        subject = _site_subject(command, evidence)

        measurements = {
            "walkable_population": unresolved_walkable_population(subject, evidence.demographics, evidence.isochrone),
            "target_population_density": unresolved_target_population_density(subject, evidence.demographics),
            "competition_pressure": unresolved_competition_pressure(
                subject,
                evidence.competition,
                expected_measurement_definition_id=evidence.competition.measurement_definition_id,
            ),
            "walkable_reach_area_km2": measure_walkable_reach_area(subject, evidence.isochrone),
            "transit_service_departure_equivalents_per_hour": measure_transit_service(
                subject,
                evidence.transit,
                expected_source_bundle_fingerprint=evidence.transit.source_bundle_fingerprint,
            ),
            "household_income": measure_household_income(subject, evidence.demographics),
        }
        direct_results = tuple(
            normalize_feature(measurements[key], evidence.benchmark_distributions[key])
            for key in (
                "walkable_population",
                "target_population_density",
                "competition_pressure",
                "walkable_reach_area_km2",
                "transit_service_departure_equivalents_per_hour",
                "household_income",
            )
        )
        road_parking = evaluate_road_parking_composite()
        assembly = assemble_normalized_location_features(
            direct_results=direct_results,
            age_fallback=build_age_target_concentration_fallback(),
            road_parking_result=road_parking,
            generated_at=now,
        )
        readiness = derive_scoring_readiness(assembly, evaluated_at=now)

        by_metric = {
            item.site_measurement.definition.metric_key: item.site_measurement.metric_value
            for item in direct_results
        }
        derived = DerivedLocationMetrics(
            walkable_population=by_metric["walkable_population"],
            target_population_density=by_metric["target_population_density"],
            household_income=by_metric["household_income"],
            household_income_ratio=_unknown_metric("ratio", "household_income_denominator_policy_unresolved"),
            competition_pressure=by_metric["competition_pressure"],
            walkable_reach_area_km2=by_metric["walkable_reach_area_km2"],
            transit_service_departure_equivalents_per_hour=by_metric[
                "transit_service_departure_equivalents_per_hour"
            ],
            road_reachable_area_km2=_unknown_metric("km2", "road_reduction_policy_unresolved"),
            parking_public_offstreet_capacity=_unknown_metric("spaces", "parking_component_unresolved"),
            parking_legal_curb_length_m=_unknown_metric("m", "parking_component_unresolved"),
            demographic_snapshot_ref=None,
            competition_snapshot_ref=None,
            road_snapshot_ref=None,
            parking_snapshot_ref=None,
            source_refs=tuple(
                sorted({ref for item in by_metric.values() for ref in item.source_refs})
            ),
            feature_contract_version=assembly.features.feature_contract_version,
            generated_at=now,
        )
        app_pipeline = build_application_pipeline_result(
            readiness=readiness,
            sector_key=SectorKey(command.sector.value),
            resolved_location=evidence.resolved_location,
            derived_metrics=derived,
            source_metadata=evidence.source_metadata,
            generated_at=now,
            demographics=evidence.demographics,
            isochrone=evidence.isochrone,
            competition=evidence.competition,
            transit=evidence.transit,
        )
        eligibility = evaluate_application_scoring_gate(app_pipeline.pipeline_result)
        if eligibility.state is ApplicationScoringGateState.NOT_SCORE_READY:
            return ExecutionResult(
                not_score_ready=build_canonical_not_score_ready_outcome(app_pipeline)
            )
        if eligibility.state is not ApplicationScoringGateState.ELIGIBLE:
            raise CanonicalExecutionFailed(
                f"canonical application gate blocked: {eligibility.state.value}"
            )

        scoring = build_application_scoring_input(app_pipeline)
        category = aggregate_application_category_scores(scoring)
        core_input = build_application_core_analysis_input(
            category,
            revenue_input=command.revenue_input,
            monthly_rent=command.monthly_rent,
            fixed_labor=command.fixed_labor,
            fixed_overhead=command.fixed_overhead,
            geographic_level=evidence.geographic_level,
            data_age_years=evidence.data_age_years,
            data_coverage=dict(evidence.data_coverage),
            input_qualities=dict(evidence.input_qualities),
        )
        app_result = analyze_application_core_input(core_input)
        return ExecutionResult(completed=build_canonical_completed_outcome(app_result))
