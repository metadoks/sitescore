from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import json

from sitescore_benchmarks.composite import (
    RoadParkingCompositeResult,
    RoadParkingCompositeState,
)
from sitescore_benchmarks.normalization import (
    AGE_TARGET_CONCENTRATION_FALLBACK_V1,
    FEATURE_NORMALIZATION_POLICIES_V1,
    AgeTargetConcentrationFallback,
    FeatureNormalizationResult,
    FeatureNormalizationState,
)
from sitescore_data import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    PipelineStatus,
    ScoreEligibility,
    SectorKey,
    DATA_FEATURE_CONTRACT_VERSION,
)
from sitescore_data.feature_surface import NORMALIZED_FEATURE_NAMES
from sitescore_data.schemas.benchmarks import BenchmarkReference
from sitescore_data.schemas.common import DataContractVersions, MetricValue, SourceMetadata
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.demographics import DemographicSnapshot
from sitescore_data.schemas.features import DerivedLocationMetrics, NormalizedLocationFeatures
from sitescore_data.schemas.geography import ResolvedLocation
from sitescore_data.schemas.parking import ParkingSnapshot
from sitescore_data.schemas.pedestrian import IsochroneSnapshot, PedestrianCatchmentArtifact
from sitescore_data.schemas.pipeline import PipelineReason, RealDataPipelineResult
from sitescore_data.schemas.readiness import (
    ApprovedFallbackPolicyRef,
    FeatureReadinessPolicy,
    ReadinessCompatibilityInput,
    ScoringReadinessResult,
)
from sitescore_data.schemas.road import RoadAccessSnapshot
from sitescore_data.schemas.transit import TransitSnapshot
from sitescore_data.validation import require_aware_datetime, require_canonical_identifier
from sitescore_data.validators.readiness import ScoringReadinessValidator


PIPELINE_VERSION = "0.1.0"
READINESS_VALIDATOR_VERSION = "sitescore-pipeline-readiness/1.0"
_DIRECT_FEATURE_KEYS = tuple(
    policy.normalized_feature_key
    for policy in FEATURE_NORMALIZATION_POLICIES_V1.values()
)
_EXPECTED_DIRECT_FEATURE_KEYS = {
    "walkable_population_score",
    "target_population_density_score",
    "competition_opportunity_score",
    "walkable_reach_area_score",
    "transit_access_score",
    "household_income_score",
}


def _semantic_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _canonical_union(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({item for group in groups for item in group}))


def _metric_record(metric: MetricValue) -> dict[str, object]:
    return {
        "value": metric.value,
        "unit": metric.unit,
        "availability": metric.availability.value,
        "data_quality": metric.data_quality.value,
        "score_eligibility": metric.score_eligibility.value,
        "calibration_state": metric.calibration_state.value,
        "is_estimate": metric.is_estimate,
        "is_proxy": metric.is_proxy,
        "source_refs": tuple(sorted(metric.source_refs)),
        "method_version": metric.method_version,
        "reason_codes": metric.reason_codes,
    }


def _feature_surface_record(features: NormalizedLocationFeatures) -> dict[str, object]:
    return {
        "metrics": {
            name: _metric_record(getattr(features, name))
            for name in NORMALIZED_FEATURE_NAMES
        },
        "competition_benchmark_id": (
            features.competition_benchmark_ref.benchmark_id
            if features.competition_benchmark_ref else None
        ),
        "competition_measurement_definition_id": features.competition_measurement_definition_id,
        "competition_normalization_policy_version": features.competition_normalization_policy_version,
        "transit_benchmark_id": (
            features.transit_benchmark_ref.benchmark_id
            if features.transit_benchmark_ref else None
        ),
        "transit_source_bundle_fingerprint": features.transit_source_bundle_fingerprint,
        "transit_normalization_policy_version": features.transit_normalization_policy_version,
        "road_parking_composite_policy_version": features.road_parking_composite_policy_version,
        "source_refs": tuple(sorted(features.source_refs)),
        "feature_contract_version": features.feature_contract_version,
    }


@dataclass(frozen=True, slots=True)
class BenchmarkReferenceBinding:
    """Bind a persisted data-layer benchmark reference to an actual 3.4-6 result."""

    normalization_result: FeatureNormalizationResult
    reference: BenchmarkReference

    def __post_init__(self) -> None:
        if not isinstance(self.normalization_result, FeatureNormalizationResult):
            raise TypeError("normalization_result must be FeatureNormalizationResult")
        if not isinstance(self.reference, BenchmarkReference):
            raise TypeError("reference must be BenchmarkReference")
        distribution = self.normalization_result.benchmark_distribution
        if self.reference.benchmark_id != distribution.distribution_id:
            raise ValueError("BenchmarkReference.benchmark_id must bind the actual distribution_id")
        if self.reference.frame_id != distribution.measurement_set.frame.frame_id:
            raise ValueError("BenchmarkReference.frame_id must bind the actual benchmark frame")

    @property
    def normalized_feature_key(self) -> str:
        return self.normalization_result.normalized_feature_key

    @property
    def identity_id(self) -> str:
        return _semantic_hash({
            "normalization_result_id": self.normalization_result.identity_id,
            "benchmark_id": self.reference.benchmark_id,
            "artifact_ref": self.reference.artifact_ref,
            "frame_id": self.reference.frame_id,
            "frame_version": self.reference.frame_version,
            "source_refs": tuple(sorted(self.reference.source_refs)),
        })


_ASSEMBLY_TOKEN = object()
_READINESS_TOKEN = object()


@dataclass(frozen=True, slots=True)
class NormalizedFeatureAssembly:
    features: NormalizedLocationFeatures
    feature_policies: tuple[FeatureReadinessPolicy, ...]
    compatibility: ReadinessCompatibilityInput
    approved_fallback_policies: tuple[ApprovedFallbackPolicyRef, ...]
    artifact_identities: tuple[tuple[str, str], ...]
    assembly_id: str
    _factory_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._factory_token is not _ASSEMBLY_TOKEN:
            raise ValueError("NormalizedFeatureAssembly must be produced by canonical pipeline assembly")
        if not isinstance(self.features, NormalizedLocationFeatures):
            raise TypeError("features must be NormalizedLocationFeatures")
        if tuple(name for name, _ in self.artifact_identities) != tuple(sorted(name for name, _ in self.artifact_identities)):
            raise ValueError("artifact_identities must be canonical-sorted")
        if self.assembly_id != _assembly_identity(
            self.features,
            self.feature_policies,
            self.compatibility,
            self.approved_fallback_policies,
            self.artifact_identities,
        ):
            raise ValueError("assembly_id must derive from actual assembly semantics")


@dataclass(frozen=True, slots=True)
class ReadinessEvaluation:
    assembly: NormalizedFeatureAssembly
    result: ScoringReadinessResult
    _factory_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._factory_token is not _READINESS_TOKEN:
            raise ValueError("ReadinessEvaluation must be produced by canonical pipeline validation")
        if not isinstance(self.assembly, NormalizedFeatureAssembly):
            raise TypeError("assembly must be NormalizedFeatureAssembly")
        if not isinstance(self.result, ScoringReadinessResult):
            raise TypeError("result must be ScoringReadinessResult")


@dataclass(frozen=True, slots=True)
class PipelineStageFailure:
    stage_id: str
    reason_code: str

    def __post_init__(self) -> None:
        require_canonical_identifier(self.stage_id, field_name="stage_id")
        require_canonical_identifier(self.reason_code, field_name="reason_code")


def _binding_map(bindings: tuple[BenchmarkReferenceBinding, ...]) -> dict[str, BenchmarkReferenceBinding]:
    if not isinstance(bindings, tuple):
        raise TypeError("benchmark_bindings must be a tuple")
    if any(not isinstance(item, BenchmarkReferenceBinding) for item in bindings):
        raise TypeError("benchmark_bindings must contain BenchmarkReferenceBinding values")
    by_feature = {item.normalized_feature_key: item for item in bindings}
    if len(by_feature) != len(bindings):
        raise ValueError("benchmark_bindings must be unique by normalized feature")
    return by_feature


def _direct_metric(
    result: FeatureNormalizationResult,
    binding: BenchmarkReferenceBinding | None,
) -> MetricValue:
    source_metric = result.site_measurement.metric_value
    source_refs = _canonical_union(
        source_metric.source_refs,
        binding.reference.source_refs if binding else (),
    )
    method_version = f"{result.policy.policy_id}/{result.policy.policy_version}"

    if result.state is FeatureNormalizationState.AVAILABLE:
        if result.score is None:
            raise RuntimeError("AVAILABLE normalization result must carry derived score")
        return MetricValue(
            value=result.score,
            unit="score_0_100",
            availability=AvailabilityState.AVAILABLE,
            data_quality=source_metric.data_quality,
            score_eligibility=ScoreEligibility.ELIGIBLE,
            calibration_state=CalibrationState.CALIBRATED,
            is_estimate=source_metric.is_estimate,
            is_proxy=source_metric.is_proxy,
            source_refs=source_refs,
            method_version=method_version,
            reason_codes=(),
        )

    if result.state is FeatureNormalizationState.SITE_METRIC_NOT_AVAILABLE:
        availability = source_metric.availability
        if availability is AvailabilityState.AVAILABLE:
            availability = AvailabilityState.UNKNOWN
        quality = source_metric.data_quality
        if availability is AvailabilityState.UNKNOWN and quality is DataQualityState.FULL:
            quality = DataQualityState.DEGRADED
        eligibility = source_metric.score_eligibility
        if eligibility is ScoreEligibility.ELIGIBLE:
            eligibility = ScoreEligibility.INELIGIBLE
        calibration = source_metric.calibration_state
    elif result.state is FeatureNormalizationState.SITE_METRIC_NOT_ELIGIBLE:
        availability = AvailabilityState.UNKNOWN
        quality = DataQualityState.DEGRADED
        eligibility = source_metric.score_eligibility
        calibration = source_metric.calibration_state
    elif result.state is FeatureNormalizationState.SITE_METRIC_NOT_CALIBRATED:
        availability = AvailabilityState.UNKNOWN
        quality = DataQualityState.DEGRADED
        eligibility = ScoreEligibility.INELIGIBLE
        calibration = CalibrationState.UNCALIBRATED
    else:
        availability = AvailabilityState.UNKNOWN
        quality = DataQualityState.DEGRADED
        eligibility = ScoreEligibility.INELIGIBLE
        calibration = CalibrationState.CALIBRATED

    return MetricValue(
        value=None,
        unit="score_0_100",
        availability=availability,
        data_quality=quality,
        score_eligibility=eligibility,
        calibration_state=calibration,
        is_estimate=source_metric.is_estimate,
        is_proxy=source_metric.is_proxy,
        source_refs=source_refs,
        method_version=method_version,
        reason_codes=tuple(dict.fromkeys(result.reason_codes)),
    )


def _age_metric(age_fallback: AgeTargetConcentrationFallback) -> MetricValue:
    if age_fallback.policy.identity_id != AGE_TARGET_CONCENTRATION_FALLBACK_V1.identity_id:
        raise ValueError("age fallback must bind exact locked V1 authority")
    source_ref = f"age-fallback.{age_fallback.policy.identity_id}"
    return MetricValue(
        value=age_fallback.score,
        unit=age_fallback.unit,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=CalibrationState.UNCALIBRATED,
        is_estimate=False,
        is_proxy=True,
        source_refs=(source_ref,),
        method_version=age_fallback.method_version,
        reason_codes=age_fallback.reason_codes,
    )


def _road_parking_metric(result: RoadParkingCompositeResult) -> MetricValue:
    if not isinstance(result, RoadParkingCompositeResult):
        raise TypeError("road_parking_result must be RoadParkingCompositeResult")
    if result.state is RoadParkingCompositeState.AVAILABLE:
        if result.score is None:
            raise RuntimeError("AVAILABLE road/parking result must have derived score")
        return MetricValue(
            value=result.score,
            unit="score_0_100",
            availability=AvailabilityState.AVAILABLE,
            data_quality=DataQualityState.FULL,
            score_eligibility=ScoreEligibility.ELIGIBLE,
            calibration_state=CalibrationState.CALIBRATED,
            is_estimate=False,
            is_proxy=False,
            source_refs=(f"comb005.{result.identity_id}",),
            method_version=f"{result.policy.policy_id}/{result.policy.policy_version}",
            reason_codes=(),
        )
    return MetricValue(
        value=None,
        unit="score_0_100",
        availability=AvailabilityState.UNKNOWN,
        data_quality=DataQualityState.DEGRADED,
        score_eligibility=ScoreEligibility.INELIGIBLE,
        calibration_state=CalibrationState.UNCALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(),
        method_version=None,
        reason_codes=tuple(dict.fromkeys(result.reason_codes)),
    )


def _source_bundle(result: FeatureNormalizationResult, *, benchmark: bool) -> dict[str, str]:
    compatibility = (
        result.compatibility.benchmark_compatibility
        if benchmark
        else result.compatibility.site_compatibility
    )
    if compatibility is None:
        return {}
    return dict(compatibility.source_bundle_compatibility)


def _assembly_identity(
    features: NormalizedLocationFeatures,
    feature_policies: tuple[FeatureReadinessPolicy, ...],
    compatibility: ReadinessCompatibilityInput,
    approved_fallback_policies: tuple[ApprovedFallbackPolicyRef, ...],
    artifact_identities: tuple[tuple[str, str], ...],
) -> str:
    return _semantic_hash({
        "features": _feature_surface_record(features),
        "feature_policies": tuple(
            (
                p.feature_name,
                p.required,
                p.required_policy_version,
                p.resolved_policy_version,
                p.fallback_policy_id,
                p.fallback_policy_version,
            )
            for p in feature_policies
        ),
        "compatibility": (
            compatibility.competition_benchmark_measurement_definition_id,
            compatibility.transit_benchmark_source_bundle_fingerprint,
        ),
        "approved_fallback_policies": tuple(
            (p.feature_name, p.policy_id, p.policy_version)
            for p in approved_fallback_policies
        ),
        "artifact_identities": artifact_identities,
    })


def assemble_normalized_location_features(
    *,
    direct_results: tuple[FeatureNormalizationResult, ...],
    age_fallback: AgeTargetConcentrationFallback,
    road_parking_result: RoadParkingCompositeResult,
    benchmark_bindings: tuple[BenchmarkReferenceBinding, ...] = (),
    generated_at: datetime,
) -> NormalizedFeatureAssembly:
    """Canonical 3.4-8 assembly from actual 3.4-6/3.4-7 artifacts."""
    require_aware_datetime(generated_at, field_name="generated_at")
    if not isinstance(direct_results, tuple):
        raise TypeError("direct_results must be a tuple")
    if any(not isinstance(item, FeatureNormalizationResult) for item in direct_results):
        raise TypeError("direct_results must contain FeatureNormalizationResult values")
    by_feature = {item.normalized_feature_key: item for item in direct_results}
    if len(by_feature) != len(direct_results):
        raise ValueError("direct_results must be unique by normalized feature")
    if set(by_feature) != _EXPECTED_DIRECT_FEATURE_KEYS:
        raise ValueError("direct_results must cover exactly the six locked direct V1 mappings")
    if not isinstance(age_fallback, AgeTargetConcentrationFallback):
        raise TypeError("age_fallback must be AgeTargetConcentrationFallback")
    if age_fallback.policy.identity_id != AGE_TARGET_CONCENTRATION_FALLBACK_V1.identity_id:
        raise ValueError("age_fallback must use exact locked V1 authority")
    if not isinstance(road_parking_result, RoadParkingCompositeResult):
        raise TypeError("road_parking_result must be RoadParkingCompositeResult")

    bindings = _binding_map(benchmark_bindings)
    for key, binding in bindings.items():
        if key not in by_feature:
            raise ValueError("benchmark binding must belong to one of the six direct results")
        if binding.normalization_result.identity_id != by_feature[key].identity_id:
            raise ValueError("benchmark binding normalization result must be the actual assembled result")

    metrics = {
        key: _direct_metric(result, bindings.get(key))
        for key, result in by_feature.items()
    }
    metrics["age_target_concentration_score"] = _age_metric(age_fallback)
    metrics["road_parking_access_score"] = _road_parking_metric(road_parking_result)

    competition_result = by_feature["competition_opportunity_score"]
    transit_result = by_feature["transit_access_score"]
    competition_site_bundle = _source_bundle(competition_result, benchmark=False)
    competition_benchmark_bundle = _source_bundle(competition_result, benchmark=True)
    transit_site_bundle = _source_bundle(transit_result, benchmark=False)
    transit_benchmark_bundle = _source_bundle(transit_result, benchmark=True)

    competition_binding = bindings.get("competition_opportunity_score")
    transit_binding = bindings.get("transit_access_score")
    source_refs = _canonical_union(
        *(metric.source_refs for metric in metrics.values()),
        competition_binding.reference.source_refs if competition_binding else (),
        transit_binding.reference.source_refs if transit_binding else (),
    )

    road_policy_version = (
        road_parking_result.policy.policy_version
        if road_parking_result.state is RoadParkingCompositeState.AVAILABLE
        else None
    )

    features = NormalizedLocationFeatures(
        walkable_population_score=metrics["walkable_population_score"],
        target_population_density_score=metrics["target_population_density_score"],
        age_target_concentration_score=metrics["age_target_concentration_score"],
        competition_opportunity_score=metrics["competition_opportunity_score"],
        walkable_reach_area_score=metrics["walkable_reach_area_score"],
        transit_access_score=metrics["transit_access_score"],
        road_parking_access_score=metrics["road_parking_access_score"],
        household_income_score=metrics["household_income_score"],
        competition_benchmark_ref=competition_binding.reference if competition_binding else None,
        competition_measurement_definition_id=competition_site_bundle.get("competition_measurement_definition_id"),
        competition_normalization_policy_version=competition_result.policy.policy_version,
        transit_benchmark_ref=transit_binding.reference if transit_binding else None,
        transit_source_bundle_fingerprint=transit_site_bundle.get("transit_source_bundle_fingerprint"),
        transit_normalization_policy_version=transit_result.policy.policy_version,
        road_parking_composite_policy_version=road_policy_version,
        source_refs=source_refs,
        feature_contract_version=DATA_FEATURE_CONTRACT_VERSION,
        generated_at=generated_at,
    )

    feature_policies: list[FeatureReadinessPolicy] = []
    for feature_name in NORMALIZED_FEATURE_NAMES:
        if feature_name in by_feature:
            version = by_feature[feature_name].policy.policy_version
            feature_policies.append(FeatureReadinessPolicy(feature_name, True, version, version))
        elif feature_name == "age_target_concentration_score":
            feature_policies.append(FeatureReadinessPolicy(
                feature_name,
                True,
                age_fallback.policy.policy_version,
                age_fallback.policy.policy_version,
                age_fallback.policy.policy_id,
                age_fallback.policy.policy_version,
            ))
        else:
            feature_policies.append(FeatureReadinessPolicy(feature_name, True, None, road_policy_version))

    approved_fallbacks = (
        ApprovedFallbackPolicyRef(
            feature_name=age_fallback.normalized_feature_key,
            policy_id=age_fallback.policy.policy_id,
            policy_version=age_fallback.policy.policy_version,
        ),
    )
    compatibility = ReadinessCompatibilityInput(
        competition_benchmark_measurement_definition_id=competition_benchmark_bundle.get(
            "competition_measurement_definition_id"
        ),
        transit_benchmark_source_bundle_fingerprint=transit_benchmark_bundle.get(
            "transit_source_bundle_fingerprint"
        ),
    )
    artifact_identities = tuple(sorted(
        [
            *((name, result.identity_id) for name, result in by_feature.items()),
            ("age_target_concentration_score", age_fallback.policy.identity_id),
            ("road_parking_access_score", road_parking_result.identity_id),
            *((f"benchmark_binding.{item.normalized_feature_key}", item.identity_id) for item in benchmark_bindings),
        ],
        key=lambda item: item[0],
    ))
    policy_tuple = tuple(feature_policies)
    assembly_id = _assembly_identity(
        features, policy_tuple, compatibility, approved_fallbacks, artifact_identities
    )
    return NormalizedFeatureAssembly(
        features=features,
        feature_policies=policy_tuple,
        compatibility=compatibility,
        approved_fallback_policies=approved_fallbacks,
        artifact_identities=artifact_identities,
        assembly_id=assembly_id,
        _factory_token=_ASSEMBLY_TOKEN,
    )


def _readiness_fingerprint(assembly: NormalizedFeatureAssembly) -> str:
    return _semantic_hash({
        "assembly_id": assembly.assembly_id,
        "validator_version": READINESS_VALIDATOR_VERSION,
        "features": _feature_surface_record(assembly.features),
        "feature_policies": tuple(
            (
                p.feature_name,
                p.required_policy_version,
                p.resolved_policy_version,
                p.fallback_policy_id,
                p.fallback_policy_version,
            )
            for p in assembly.feature_policies
        ),
        "compatibility": (
            assembly.compatibility.competition_benchmark_measurement_definition_id,
            assembly.compatibility.transit_benchmark_source_bundle_fingerprint,
        ),
        "approved_fallback_policies": tuple(
            (p.feature_name, p.policy_id, p.policy_version)
            for p in assembly.approved_fallback_policies
        ),
        "artifact_identities": assembly.artifact_identities,
    })


def derive_scoring_readiness(
    assembly: NormalizedFeatureAssembly,
    *,
    evaluated_at: datetime,
) -> ReadinessEvaluation:
    """Derive frozen readiness; caller cannot assert readiness/fingerprint summaries."""
    if not isinstance(assembly, NormalizedFeatureAssembly) or assembly._factory_token is not _ASSEMBLY_TOKEN:
        raise TypeError("assembly must come from canonical pipeline assembly")
    require_aware_datetime(evaluated_at, field_name="evaluated_at")
    fingerprint = _readiness_fingerprint(assembly)
    result = ScoringReadinessValidator(
        validator_version=READINESS_VALIDATOR_VERSION
    ).validate(
        features=assembly.features,
        feature_policies=assembly.feature_policies,
        compatibility=assembly.compatibility,
        approved_fallback_policies=assembly.approved_fallback_policies,
        evaluated_at=evaluated_at,
        readiness_fingerprint=fingerprint,
    )
    return ReadinessEvaluation(assembly, result, _READINESS_TOKEN)


def build_real_data_pipeline_result(
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
) -> RealDataPipelineResult:
    """Canonical successful-stage terminal factory. Status is derived from readiness."""
    if not isinstance(readiness, ReadinessEvaluation) or readiness._factory_token is not _READINESS_TOKEN:
        raise TypeError("readiness must come from canonical pipeline validation")
    if not isinstance(derived_metrics, DerivedLocationMetrics):
        raise TypeError("derived_metrics must be DerivedLocationMetrics")
    require_aware_datetime(generated_at, field_name="generated_at")
    status = (
        PipelineStatus.SCORE_READY
        if readiness.result.is_score_ready
        else PipelineStatus.NOT_SCORE_READY
    )
    if status is PipelineStatus.SCORE_READY and resolved_location is None:
        raise ValueError("score-ready terminal result requires actual resolved_location")
    reasons = () if status is PipelineStatus.SCORE_READY else (PipelineReason.SCORING_NOT_READY,)
    return RealDataPipelineResult(
        status=status,
        sector_key=sector_key,
        resolved_location=resolved_location,
        demographics=demographics,
        pedestrian_catchment=pedestrian_catchment,
        isochrone=isochrone,
        competition=competition,
        transit=transit,
        road=road,
        parking=parking,
        derived_metrics=derived_metrics,
        normalized_features=readiness.assembly.features,
        scoring_readiness=readiness.result,
        source_metadata=tuple(sorted(source_metadata, key=lambda item: item.source_id)),
        pipeline_version=PIPELINE_VERSION,
        data_contract_versions=DataContractVersions.current(),
        generated_at=generated_at,
        reason_codes=reasons,
    )


def build_pipeline_error_result(
    *,
    failure: PipelineStageFailure,
    sector_key: SectorKey,
    source_metadata: tuple[SourceMetadata, ...],
    generated_at: datetime,
    resolved_location: ResolvedLocation | None = None,
    demographics: DemographicSnapshot | None = None,
    pedestrian_catchment: PedestrianCatchmentArtifact | None = None,
    isochrone: IsochroneSnapshot | None = None,
    competition: CompetitionSnapshot | None = None,
    transit: TransitSnapshot | None = None,
    road: RoadAccessSnapshot | None = None,
    parking: ParkingSnapshot | None = None,
    derived_metrics: DerivedLocationMetrics | None = None,
) -> RealDataPipelineResult:
    """Terminal factory for an actual execution-stage failure, never ordinary unready evidence."""
    if not isinstance(failure, PipelineStageFailure):
        raise TypeError("failure must be PipelineStageFailure")
    require_aware_datetime(generated_at, field_name="generated_at")
    return RealDataPipelineResult(
        status=PipelineStatus.PIPELINE_ERROR,
        sector_key=sector_key,
        resolved_location=resolved_location,
        demographics=demographics,
        pedestrian_catchment=pedestrian_catchment,
        isochrone=isochrone,
        competition=competition,
        transit=transit,
        road=road,
        parking=parking,
        derived_metrics=derived_metrics,
        normalized_features=None,
        scoring_readiness=None,
        source_metadata=tuple(sorted(source_metadata, key=lambda item: item.source_id)),
        pipeline_version=PIPELINE_VERSION,
        data_contract_versions=DataContractVersions.current(),
        generated_at=generated_at,
        reason_codes=(PipelineReason.PIPELINE_STAGE_ERROR,),
    )
