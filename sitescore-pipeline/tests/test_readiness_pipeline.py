from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone, timedelta
import inspect

import pytest

import sitescore_pipeline.integration as integration
from sitescore_data import (
    AvailabilityState,
    BenchmarkPopulationType,
    CalibrationState,
    DataQualityState,
    PipelineStatus,
    ScoreEligibility,
    SectorKey,
    DATA_FEATURE_CONTRACT_VERSION,
)
from sitescore_data.enums import GeographyType
from sitescore_data.schemas.benchmarks import BenchmarkReference
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.features import DerivedLocationMetrics, NormalizedLocationFeatures
from sitescore_data.schemas.geography import GeographyRef, ResolvedLocation
from sitescore_data.schemas.pipeline import PipelineReason
from sitescore_data.schemas.readiness import (
    ApprovedFallbackPolicyRef,
    FeatureReadinessPolicy,
    ReadinessCompatibilityInput,
    ScoringReadinessReason,
)


T0 = datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc)
SOURCE = "test.source"
GEO_SOURCE = "test.geo"


def _available(value=60.0, *, calibration=CalibrationState.CALIBRATED, proxy=False, reasons=()):
    return MetricValue(
        value=value,
        unit="score_0_100",
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=proxy,
        source_refs=(SOURCE,),
        method_version="test/1.0",
        reason_codes=reasons,
    )


def _missing(*, calibration=CalibrationState.CALIBRATED):
    return MetricValue(
        value=None,
        unit="score_0_100",
        availability=AvailabilityState.MISSING,
        data_quality=DataQualityState.MISSING,
        score_eligibility=ScoreEligibility.INELIGIBLE,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=False,
        source_refs=(),
        method_version="test/1.0",
        reason_codes=("test_missing",),
    )


def _unknown(*, calibration=CalibrationState.UNCALIBRATED):
    return MetricValue(
        value=None,
        unit="score_0_100",
        availability=AvailabilityState.UNKNOWN,
        data_quality=DataQualityState.DEGRADED,
        score_eligibility=ScoreEligibility.INELIGIBLE,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=False,
        source_refs=(),
        method_version=None,
        reason_codes=("test_unavailable",),
    )


def _benchmark_ref(name: str):
    geography = GeographyRef(
        geography_type=GeographyType.CUSTOM,
        geography_id="test-geography",
        name="Test Geography",
        country_code="US",
        source_ref=GEO_SOURCE,
        source_version="1.0",
    )
    return BenchmarkReference(
        benchmark_id=f"{name}-benchmark",
        artifact_ref=f"artifact:{name}",
        frame_id="test-frame",
        frame_version="1.0",
        population_type=BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES,
        benchmark_geography_ref=geography,
        source_refs=(GEO_SOURCE,),
    )


def _features(**overrides):
    values = {
        "walkable_population_score": _available(61),
        "target_population_density_score": _available(62),
        "age_target_concentration_score": _available(
            50,
            calibration=CalibrationState.UNCALIBRATED,
            proxy=True,
            reasons=("age_affinity_not_calibrated",),
        ),
        "competition_opportunity_score": _available(63),
        "walkable_reach_area_score": _available(64),
        "transit_access_score": _available(65),
        "road_parking_access_score": _available(66),
        "household_income_score": _available(67),
        "competition_benchmark_ref": _benchmark_ref("competition"),
        "competition_measurement_definition_id": "competition-definition-v1",
        "competition_normalization_policy_version": "1.0",
        "transit_benchmark_ref": _benchmark_ref("transit"),
        "transit_source_bundle_fingerprint": "transit-bundle-v1",
        "transit_normalization_policy_version": "1.0",
        "road_parking_composite_policy_version": "1.0",
        "source_refs": (GEO_SOURCE, SOURCE),
        "feature_contract_version": DATA_FEATURE_CONTRACT_VERSION,
        "generated_at": T0,
    }
    values.update(overrides)
    return NormalizedLocationFeatures(**values)


def _policies(*, missing_policy=None, mismatch_policy=None):
    policies = []
    for name in integration.NORMALIZED_FEATURE_NAMES:
        required = "1.0"
        resolved = "1.0"
        fallback_id = None
        fallback_version = None
        if name == "age_target_concentration_score":
            fallback_id = "age_neutral_fallback"
            fallback_version = "1.0"
        if name == missing_policy:
            resolved = None
        if name == mismatch_policy:
            resolved = "2.0"
        policies.append(FeatureReadinessPolicy(
            feature_name=name,
            required=True,
            required_policy_version=required,
            resolved_policy_version=resolved,
            fallback_policy_id=fallback_id,
            fallback_policy_version=fallback_version,
        ))
    return tuple(policies)


def _assembly(
    features=None,
    *,
    policies=None,
    competition_definition="competition-definition-v1",
    transit_bundle="transit-bundle-v1",
    approved_age=True,
):
    features = features or _features()
    policies = policies or _policies()
    compatibility = ReadinessCompatibilityInput(
        competition_benchmark_measurement_definition_id=competition_definition,
        transit_benchmark_source_bundle_fingerprint=transit_bundle,
    )
    fallbacks = (
        ApprovedFallbackPolicyRef(
            feature_name="age_target_concentration_score",
            policy_id="age_neutral_fallback",
            policy_version="1.0",
        ),
    ) if approved_age else ()
    artifact_ids = (("test", "artifact-v1"),)
    assembly_id = integration._assembly_identity(
        features, policies, compatibility, fallbacks, artifact_ids
    )
    return integration.NormalizedFeatureAssembly(
        features=features,
        feature_policies=policies,
        compatibility=compatibility,
        approved_fallback_policies=fallbacks,
        artifact_identities=artifact_ids,
        assembly_id=assembly_id,
        _factory_token=integration._ASSEMBLY_TOKEN,
    )


def _derived(feature_contract_version=DATA_FEATURE_CONTRACT_VERSION):
    metric = MetricValue(
        value=None,
        unit="unitless",
        availability=AvailabilityState.UNKNOWN,
        data_quality=DataQualityState.DEGRADED,
        score_eligibility=ScoreEligibility.INELIGIBLE,
        calibration_state=CalibrationState.UNCALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(),
        method_version=None,
        reason_codes=("not_needed_for_controlled_test",),
    )
    return DerivedLocationMetrics(
        walkable_population=metric,
        target_population_density=metric,
        household_income=metric,
        household_income_ratio=metric,
        competition_pressure=metric,
        walkable_reach_area_km2=metric,
        transit_service_departure_equivalents_per_hour=metric,
        road_reachable_area_km2=metric,
        parking_public_offstreet_capacity=metric,
        parking_legal_curb_length_m=metric,
        demographic_snapshot_ref=None,
        competition_snapshot_ref=None,
        road_snapshot_ref=None,
        parking_snapshot_ref=None,
        source_refs=(),
        feature_contract_version=feature_contract_version,
        generated_at=T0,
    )


def _location():
    return ResolvedLocation(
        latitude=40.0,
        longitude=-73.0,
        formatted_address="1 Test Street",
        country_code="US",
        geography_refs=(),
        source_refs=(SOURCE,),
        resolution_method_version="test/1.0",
        generated_at=T0,
    )


def _readiness(assembly=None, when=T0):
    return integration.derive_scoring_readiness(assembly or _assembly(), evaluated_at=when)


def test_ready_001_all_eight_slots_required():
    features = replace(_features(), walkable_population_score=_missing())
    result = _readiness(_assembly(features)).result
    assert result.is_score_ready is False
    assert "walkable_population_score" in result.missing_required_features
    assert ScoringReadinessReason.MISSING_REQUIRED_FEATURE in result.reason_codes


def test_ready_002_missing_direct_feature_is_never_neutralized():
    missing = _missing()
    features = replace(_features(), household_income_score=missing)
    assert features.household_income_score.value is None
    result = _readiness(_assembly(features)).result
    assert result.is_score_ready is False
    assert features.household_income_score.value not in (0, 50)


def test_ready_003_uncalibrated_ordinary_numeric_feature_blocks():
    metric = _available(70, calibration=CalibrationState.UNCALIBRATED)
    result = _readiness(_assembly(replace(_features(), household_income_score=metric))).result
    state = next(s for s in result.feature_states if s.feature_name == "household_income_score")
    assert ScoringReadinessReason.FEATURE_UNCALIBRATED in state.reason_codes
    assert result.is_score_ready is False


def test_ready_004_exact_age_fallback_with_actual_approval_passes_its_slot():
    result = _readiness().result
    age = next(s for s in result.feature_states if s.feature_name == "age_target_concentration_score")
    assert age.reason_codes == ()
    assert result.is_score_ready is True


def test_ready_005_age_exception_cannot_leak_to_transit():
    transit = _available(
        50,
        calibration=CalibrationState.UNCALIBRATED,
        proxy=True,
        reasons=("age_affinity_not_calibrated",),
    )
    result = _readiness(_assembly(replace(_features(), transit_access_score=transit))).result
    state = next(s for s in result.feature_states if s.feature_name == "transit_access_score")
    assert ScoringReadinessReason.FEATURE_UNCALIBRATED in state.reason_codes
    assert result.is_score_ready is False


def test_ready_004_age_fallback_without_trusted_approval_is_rejected():
    result = _readiness(_assembly(approved_age=False)).result
    age = next(s for s in result.feature_states if s.feature_name == "age_target_concentration_score")
    assert ScoringReadinessReason.AGE_FALLBACK_POLICY_INVALID in age.reason_codes
    assert result.is_score_ready is False


def test_ready_006_competition_measurement_mismatch_blocks():
    result = _readiness(_assembly(competition_definition="different-definition")).result
    assert ScoringReadinessReason.COMPETITION_MEASUREMENT_MISMATCH in result.reason_codes
    assert "competition_opportunity_score" in result.incompatible_features


def test_ready_007_transit_bundle_mismatch_blocks():
    result = _readiness(_assembly(transit_bundle="different-bundle")).result
    assert ScoringReadinessReason.TRANSIT_SOURCE_BUNDLE_MISMATCH in result.reason_codes
    assert "transit_access_score" in result.incompatible_features


def test_ready_008_comb005_unavailable_blocks_with_frozen_reason():
    features = replace(
        _features(),
        road_parking_access_score=_unknown(),
        road_parking_composite_policy_version=None,
    )
    policies = list(_policies())
    idx = integration.NORMALIZED_FEATURE_NAMES.index("road_parking_access_score")
    policies[idx] = FeatureReadinessPolicy("road_parking_access_score", True, None, None)
    result = _readiness(_assembly(features, policies=tuple(policies))).result
    road = next(s for s in result.feature_states if s.feature_name == "road_parking_access_score")
    assert ScoringReadinessReason.ROAD_PARKING_COMPOSITE_UNAVAILABLE in road.reason_codes
    assert result.is_score_ready is False


def test_ready_009_missing_required_policy_blocks():
    result = _readiness(_assembly(policies=_policies(missing_policy="walkable_population_score"))).result
    assert ScoringReadinessReason.POLICY_NOT_CONFIGURED in result.reason_codes


def test_ready_010_policy_version_mismatch_blocks():
    result = _readiness(_assembly(policies=_policies(mismatch_policy="household_income_score"))).result
    assert ScoringReadinessReason.POLICY_VERSION_MISMATCH in result.reason_codes


def test_ready_011_insufficient_quality_state_blocks_without_substitution():
    result = _readiness(_assembly(replace(_features(), walkable_reach_area_score=_missing()))).result
    assert ScoringReadinessReason.INSUFFICIENT_DATA_QUALITY in result.reason_codes
    assert result.is_score_ready is False


def test_ready_012_canonical_readiness_has_no_detached_assertion_parameters():
    params = inspect.signature(integration.derive_scoring_readiness).parameters
    assert tuple(params) == ("assembly", "evaluated_at")
    for forbidden in ("is_score_ready", "readiness_fingerprint", "reason_codes", "feature_states"):
        assert forbidden not in params


def test_readiness_fingerprint_is_semantic_and_excludes_evaluated_at():
    assembly = _assembly()
    a = _readiness(assembly, T0).result
    b = _readiness(assembly, T0 + timedelta(days=1)).result
    assert a.evaluated_at != b.evaluated_at
    assert a.readiness_fingerprint == b.readiness_fingerprint


def test_assembly_identity_ignores_generated_at_but_changes_with_feature_semantics():
    a = _assembly(_features(generated_at=T0))
    b = _assembly(_features(generated_at=T0 + timedelta(hours=2)))
    c = _assembly(_features(household_income_score=_available(99)))
    assert a.assembly_id == b.assembly_id
    assert a.assembly_id != c.assembly_id


def test_pipeline_001_readiness_false_derives_not_score_ready():
    readiness = _readiness(_assembly(replace(_features(), household_income_score=_missing())))
    result = integration.build_real_data_pipeline_result(
        readiness=readiness,
        sector_key=SectorKey("coffee"),
        resolved_location=_location(),
        derived_metrics=_derived(),
        source_metadata=(),
        generated_at=T0,
    )
    assert result.status is PipelineStatus.NOT_SCORE_READY
    assert result.reason_codes == (PipelineReason.SCORING_NOT_READY,)
    assert result.scoring_readiness is readiness.result
    assert result.normalized_features is readiness.assembly.features


def test_pipeline_002_controlled_ready_fixture_derives_score_ready():
    readiness = _readiness()
    result = integration.build_real_data_pipeline_result(
        readiness=readiness,
        sector_key=SectorKey("coffee"),
        resolved_location=_location(),
        derived_metrics=_derived(),
        source_metadata=(),
        generated_at=T0,
    )
    assert result.status is PipelineStatus.SCORE_READY
    assert result.reason_codes == ()
    assert result.scoring_readiness.is_score_ready is True


def test_pipeline_003_score_ready_is_not_scored_category_output():
    result = integration.build_real_data_pipeline_result(
        readiness=_readiness(),
        sector_key=SectorKey("coffee"),
        resolved_location=_location(),
        derived_metrics=_derived(),
        source_metadata=(),
        generated_at=T0,
    )
    assert result.status is PipelineStatus.SCORE_READY
    for forbidden in ("category_scores", "location_score", "decision"):
        assert not hasattr(result, forbidden)


def test_pipeline_004_ordinary_unready_evidence_is_not_pipeline_error():
    readiness = _readiness(_assembly(replace(_features(), transit_access_score=_missing())))
    result = integration.build_real_data_pipeline_result(
        readiness=readiness,
        sector_key=SectorKey("coffee"),
        resolved_location=_location(),
        derived_metrics=_derived(),
        source_metadata=(),
        generated_at=T0,
    )
    assert result.status is PipelineStatus.NOT_SCORE_READY


def test_pipeline_005_explicit_stage_failure_derives_pipeline_error_without_readiness():
    result = integration.build_pipeline_error_result(
        failure=integration.PipelineStageFailure("provider_stage", "provider_failure"),
        sector_key=SectorKey("coffee"),
        source_metadata=(),
        generated_at=T0,
        resolved_location=_location(),
    )
    assert result.status is PipelineStatus.PIPELINE_ERROR
    assert result.scoring_readiness is None
    assert result.reason_codes == (PipelineReason.PIPELINE_STAGE_ERROR,)


def test_pipeline_006_terminal_factory_has_no_caller_status_authority():
    params = inspect.signature(integration.build_real_data_pipeline_result).parameters
    for forbidden in ("status", "reason_codes", "is_score_ready"):
        assert forbidden not in params


def test_pipeline_007_feature_contract_mismatch_is_rejected_by_frozen_terminal_dto():
    with pytest.raises(ValueError, match="feature_contract_version"):
        integration.build_real_data_pipeline_result(
            readiness=_readiness(),
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=_derived("different-contract"),
            source_metadata=(),
            generated_at=T0,
        )


def test_canonical_assembly_rejects_detached_metric_surface_and_requires_actual_artifact_types():
    params = inspect.signature(integration.assemble_normalized_location_features).parameters
    assert "features" not in params
    assert "metric_values" not in params
    assert "is_score_ready" not in params
    with pytest.raises(TypeError, match="FeatureNormalizationResult"):
        integration.assemble_normalized_location_features(
            direct_results=(object(),),
            age_fallback=object(),
            road_parking_result=object(),
            generated_at=T0,
        )
