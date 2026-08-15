from __future__ import annotations

from dataclasses import replace
import inspect
from pathlib import Path

import pytest

from sitescore_benchmarks import (
    AGE_TARGET_CONCENTRATION_FALLBACK_V1,
    FEATURE_NORMALIZATION_POLICIES_V1,
    FeatureNormalizationDirection,
    FeatureNormalizationPolicy,
    FeatureNormalizationResult,
    FeatureNormalizationState,
    SiteBenchmarkCompatibilityState,
    build_age_target_concentration_fallback,
    build_benchmark_distribution,
    build_benchmark_measurement_set,
    feature_normalization_policy,
    normalize_feature,
)
from sitescore_data.enums import CalibrationState
from sitescore_data.schemas.common import MetricValue
from sitescore_metrics import (
    FULL_BINARY64,
    MeasurementPrecisionPolicy,
    MeasurementSubject,
    SubjectKind,
    measure_household_income,
    measure_parking_legal_curb_length,
    measure_parking_public_offstreet_capacity,
    measure_transit_service,
    measure_walkable_reach_area,
)

from cp344_helpers import (
    area_attempt,
    complete_attempts,
    demo,
    income_attempt,
    iso,
    make_frame,
    parking,
    parking_attempt,
    transit,
    transit_attempt,
)


@pytest.fixture
def frame2(crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy):
    return make_frame(
        cell_count=2,
        crs3857=crs3857,
        canon_policy=canon_policy,
        engine=engine,
        boundary_artifact=boundary_artifact,
        geography=geography,
        evidence_policy=evidence_policy,
    )


@pytest.fixture
def frame3(crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy):
    return make_frame(
        cell_count=3,
        crs3857=crs3857,
        canon_policy=canon_policy,
        engine=engine,
        boundary_artifact=boundary_artifact,
        geography=geography,
        evidence_policy=evidence_policy,
    )


def _site_subject(*scope_refs, site_id="site_1"):
    return MeasurementSubject(
        SubjectKind.SITE,
        "sitescore_metrics.site",
        "1.0",
        (("site_id", site_id),),
        tuple(sorted({f"site:{site_id}", *scope_refs})),
    )


def _site_income(n, *, precision=FULL_BINARY64, snapshot=None):
    snapshot = snapshot or demo(n)
    subject = _site_subject(f"geography:{snapshot.geography_ref.geography_id}")
    return measure_household_income(subject, snapshot, precision_policy=precision)


def _site_area(n, *, missing=False):
    snapshot = iso(n, missing=missing)
    subject = _site_subject(f"catchment:{snapshot.catchment_ref}")
    return measure_walkable_reach_area(subject, snapshot)


def _site_transit(n, *, bundle="bundle:abc"):
    snapshot = transit(n, bundle=bundle)
    subject = _site_subject(f"transit:{snapshot.snapshot_id}")
    return measure_transit_service(
        subject,
        snapshot,
        expected_source_bundle_fingerprint=bundle,
    )


def _site_parking(n, *, curb=False):
    snapshot = parking(n)
    subject = _site_subject(f"parking:{snapshot.snapshot_id}")
    return (
        measure_parking_legal_curb_length(subject, snapshot)
        if curb
        else measure_parking_public_offstreet_capacity(subject, snapshot)
    )


def _income_distribution(frame):
    return build_benchmark_distribution(build_benchmark_measurement_set(
        frame,
        complete_attempts(frame, income_attempt),
        metric_key="household_income",
    ))


def _area_distribution(frame, *, all_missing=False):
    attempts = tuple(
        area_attempt(frame, cell, i + 1, missing=all_missing)
        for i, cell in enumerate(frame.cells)
    )
    return build_benchmark_distribution(build_benchmark_measurement_set(
        frame,
        attempts,
        metric_key="walkable_reach_area_km2",
    ))


def _transit_distribution(frame, *, bundle="bundle:abc"):
    attempts = tuple(
        transit_attempt(frame, cell, i + 1, bundle=bundle)
        for i, cell in enumerate(frame.cells)
    )
    return build_benchmark_distribution(build_benchmark_measurement_set(
        frame,
        attempts,
        metric_key="transit_service_departure_equivalents_per_hour",
    ))


def _parking_distribution(frame, *, curb=False):
    attempts = tuple(
        parking_attempt(frame, cell, i + 1, curb=curb)
        for i, cell in enumerate(frame.cells)
    )
    metric_key = "parking_legal_curb_length_m" if curb else "parking_public_offstreet_capacity"
    return build_benchmark_distribution(build_benchmark_measurement_set(
        frame,
        attempts,
        metric_key=metric_key,
    ))


def _replace_income_metric(snapshot, *, method=None, calibration=None):
    original = snapshot.household_income
    revised = MetricValue(
        original.value,
        original.unit,
        original.availability,
        original.data_quality,
        original.score_eligibility,
        calibration if calibration is not None else original.calibration_state,
        original.is_estimate,
        original.is_proxy,
        original.source_refs,
        method if method is not None else original.method_version,
        original.reason_codes,
    )
    return replace(snapshot, household_income=revised)


def test_norm_001_higher_is_better_real_domain_path_is_75(frame2):
    result = normalize_feature(_site_income(2), _income_distribution(frame2))
    assert result.state is FeatureNormalizationState.AVAILABLE
    assert result.percentile == 0.75
    assert result.score == 75.0
    assert result.normalized_feature_key == "household_income_score"


def test_norm_002_competition_inversion_is_structurally_frozen_without_faking_metric():
    policy = feature_normalization_policy("competition_pressure")
    assert policy.direction is FeatureNormalizationDirection.LOWER_PERCENTILE_IS_BETTER
    assert policy.transform_percentile(0.75) == 25.0
    assert policy.normalized_feature_key == "competition_opportunity_score"


def test_norm_003_endpoint_transforms_have_no_special_override():
    ordinary = feature_normalization_policy("household_income")
    competition = feature_normalization_policy("competition_pressure")
    assert ordinary.transform_percentile(0.0) == 0.0
    assert ordinary.transform_percentile(1.0) == 100.0
    assert competition.transform_percentile(0.0) == 100.0
    assert competition.transform_percentile(1.0) == 0.0


def test_comp_001_exact_compatible_site_benchmark_success(frame2):
    result = normalize_feature(_site_income(2), _income_distribution(frame2))
    assert result.compatibility.state is SiteBenchmarkCompatibilityState.COMPATIBLE
    assert result.compatibility.reason_codes == ()
    assert result.score == 75.0


def test_comp_002_wrong_metric_never_normalizes(frame2):
    result = normalize_feature(_site_income(2), _area_distribution(frame2))
    assert result.state is FeatureNormalizationState.INCOMPATIBLE
    assert "metric_definition_mismatch" in result.reason_codes
    assert result.percentile is None
    assert result.score is None


def test_comp_003_method_mismatch_never_normalizes(frame2):
    snapshot = _replace_income_metric(demo(2), method="acs-income-v2")
    result = normalize_feature(_site_income(2, snapshot=snapshot), _income_distribution(frame2))
    assert result.state is FeatureNormalizationState.INCOMPATIBLE
    assert "method_version_mismatch" in result.reason_codes
    assert result.score is None


def test_comp_004_measurement_precision_mismatch_never_normalizes(frame2):
    precision_v2 = MeasurementPrecisionPolicy("real_unit_full_binary64", "2.0")
    result = normalize_feature(
        _site_income(2, precision=precision_v2),
        _income_distribution(frame2),
    )
    assert result.state is FeatureNormalizationState.INCOMPATIBLE
    assert "measurement_precision_mismatch" in result.reason_codes
    assert result.score is None


def test_comp_005_transit_bundle_mismatch_never_normalizes(frame2):
    result = normalize_feature(
        _site_transit(2, bundle="bundle:site"),
        _transit_distribution(frame2, bundle="bundle:benchmark"),
    )
    assert result.state is FeatureNormalizationState.INCOMPATIBLE
    assert "transit_source_bundle_mismatch" in result.reason_codes
    assert result.score is None


def test_comp_006_transit_same_bundle_normalizes(frame2):
    result = normalize_feature(
        _site_transit(2, bundle="bundle:abc"),
        _transit_distribution(frame2, bundle="bundle:abc"),
    )
    assert result.state is FeatureNormalizationState.AVAILABLE
    assert result.compatibility.state is SiteBenchmarkCompatibilityState.COMPATIBLE
    assert result.score is not None
    assert 0.0 <= result.score <= 100.0
    assert result.normalized_feature_key == "transit_access_score"


def test_comp_007_unavailable_benchmark_never_normalizes(frame2):
    result = normalize_feature(_site_area(2), _area_distribution(frame2, all_missing=True))
    assert result.state is FeatureNormalizationState.BENCHMARK_NOT_AVAILABLE
    assert "benchmark_not_available" in result.reason_codes
    assert result.percentile is None
    assert result.score is None


def test_comp_008_site_unavailable_never_substitutes_zero(frame2):
    result = normalize_feature(_site_area(2, missing=True), _area_distribution(frame2))
    assert result.state is FeatureNormalizationState.SITE_METRIC_NOT_AVAILABLE
    assert result.score is None
    assert result.percentile is None


def test_comp_009_uncalibrated_numeric_site_never_gets_neutral_score(frame2):
    snapshot = _replace_income_metric(demo(2), calibration=CalibrationState.UNCALIBRATED)
    result = normalize_feature(_site_income(2, snapshot=snapshot), _income_distribution(frame2))
    assert result.state is FeatureNormalizationState.SITE_METRIC_NOT_CALIBRATED
    assert result.score is None
    assert result.percentile is None


def test_comp_010_domain_result_has_no_caller_asserted_compatibility_percentile_score_or_invert():
    params = tuple(inspect.signature(FeatureNormalizationResult).parameters)
    assert params == ("site_measurement", "benchmark_distribution", "policy")
    normalize_params = tuple(inspect.signature(normalize_feature).parameters)
    assert normalize_params == ("site_measurement", "benchmark_distribution")
    for forbidden in ("compatible", "compatibility_id", "percentile", "score", "invert"):
        assert forbidden not in params
        assert forbidden not in normalize_params


def test_canonical_direction_cannot_be_caller_reversed():
    canonical = feature_normalization_policy("household_income")
    with pytest.raises(ValueError, match="direction is frozen"):
        FeatureNormalizationPolicy(
            canonical.policy_id,
            canonical.policy_version,
            canonical.metric_key,
            canonical.normalized_feature_key,
            FeatureNormalizationDirection.LOWER_PERCENTILE_IS_BETTER,
        )


def test_only_six_direct_feature_mappings_exist_and_no_parking_or_road_slot_is_invented():
    assert set(FEATURE_NORMALIZATION_POLICIES_V1) == {
        "walkable_population",
        "target_population_density",
        "competition_pressure",
        "walkable_reach_area_km2",
        "transit_service_departure_equivalents_per_hour",
        "household_income",
    }
    with pytest.raises(ValueError, match="no direct V1 feature normalization"):
        feature_normalization_policy("road_reachable_area_km2")
    with pytest.raises(ValueError, match="no direct V1 feature normalization"):
        feature_normalization_policy("parking_public_offstreet_capacity")
    with pytest.raises(ValueError, match="no direct V1 feature normalization"):
        feature_normalization_policy("parking_legal_curb_length_m")


def test_parking_only_cannot_become_final_road_parking_feature(frame2):
    with pytest.raises(ValueError, match="no direct V1 feature normalization"):
        normalize_feature(_site_parking(2), _parking_distribution(frame2))
    with pytest.raises(ValueError, match="no direct V1 feature normalization"):
        normalize_feature(_site_parking(2, curb=True), _parking_distribution(frame2, curb=True))


def test_age_fallback_exact_frozen_unique_semantics():
    fallback = build_age_target_concentration_fallback()
    assert fallback.normalized_feature_key == "age_target_concentration_score"
    assert fallback.score == 50.0
    assert fallback.unit == "score_0_100"
    assert fallback.availability == "available"
    assert fallback.score_eligibility == "eligible"
    assert fallback.calibration_state == "uncalibrated"
    assert fallback.is_proxy is True
    assert fallback.reason_codes == ("age_affinity_not_calibrated",)
    assert fallback.method_version == "age_neutral_fallback/1.0"
    assert fallback.policy.identity_id == AGE_TARGET_CONCENTRATION_FALLBACK_V1.identity_id


def test_age_fallback_policy_is_not_generic_or_reusable_for_other_features():
    params = tuple(inspect.signature(build_age_target_concentration_fallback).parameters)
    assert params == ()
    with pytest.raises(ValueError, match="frozen for V1"):
        type(AGE_TARGET_CONCENTRATION_FALLBACK_V1)(normalized_feature_key="transit_access_score")


def test_missing_non_age_feature_never_receives_age_fallback(frame2):
    result = normalize_feature(_site_area(2, missing=True), _area_distribution(frame2))
    assert result.score is None
    assert result.reason_codes != ("age_affinity_not_calibrated",)


def test_result_identity_is_deterministic_for_same_actual_inputs(frame2):
    site = _site_income(2)
    benchmark = _income_distribution(frame2)
    a = normalize_feature(site, benchmark)
    b = normalize_feature(site, benchmark)
    assert a.identity_id == b.identity_id
    assert a.compatibility.identity_id == b.compatibility.identity_id


def test_site_measurement_semantic_change_changes_result_identity(frame2):
    benchmark = _income_distribution(frame2)
    a = normalize_feature(_site_income(1), benchmark)
    b = normalize_feature(_site_income(2), benchmark)
    assert a.site_measurement.measurement_id != b.site_measurement.measurement_id
    assert a.identity_id != b.identity_id


def test_benchmark_distribution_change_changes_result_identity(
    crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy
):
    frame_a = make_frame(
        cell_count=2, crs3857=crs3857, canon_policy=canon_policy, engine=engine,
        boundary_artifact=boundary_artifact, geography=geography, evidence_policy=evidence_policy,
        eligibility_version="1.0",
    )
    frame_b = make_frame(
        cell_count=2, crs3857=crs3857, canon_policy=canon_policy, engine=engine,
        boundary_artifact=boundary_artifact, geography=geography, evidence_policy=evidence_policy,
        eligibility_version="1.1",
    )
    site = _site_income(2)
    a = normalize_feature(site, _income_distribution(frame_a))
    b = normalize_feature(site, _income_distribution(frame_b))
    assert a.benchmark_distribution.distribution_id != b.benchmark_distribution.distribution_id
    assert a.identity_id != b.identity_id


def test_normalization_policy_identity_binds_ecdf_and_metric_semantics():
    policy = feature_normalization_policy("household_income")
    assert policy.metric_definition is not None
    assert policy.metric_derivation_policy is not None
    assert policy.ecdf_policy.identity_id
    assert policy.ecdf_policy.comparison_policy.identity_id
    assert policy.identity_id


def test_no_whole_normalized_features_readiness_or_core_surface_is_constructed():
    import sitescore_benchmarks.normalization as module
    source = Path(module.__file__).read_text().lower()
    for forbidden in (
        "normalizedlocationfeatures",
        "categoryscores",
        "scoringreadiness",
        "realdatapipelineresult",
        "core.analyze",
    ):
        assert forbidden not in source
    assert "road_parking_access_score" not in source
    assert "road_weight" not in source
    assert "parking_weight" not in source
    assert "0.5 *" not in source
