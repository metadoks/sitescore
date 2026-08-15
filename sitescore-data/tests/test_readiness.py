from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
import math
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    BenchmarkPopulationType,
    CalibrationState,
    DataQualityState,
    GeographyType,
    ScoreEligibility,
)
from sitescore_data.schemas.benchmarks import BenchmarkReference
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.features import NormalizedLocationFeatures
from sitescore_data.schemas.geography import GeographyRef
from sitescore_data.schemas.readiness import (
    ApprovedFallbackPolicyRef,
    FeatureReadinessPolicy,
    PolicyVersionRef,
    ReadinessCompatibilityInput,
    ScoringFeatureReadiness,
    ScoringReadinessReason,
    ScoringReadinessResult,
)
from sitescore_data.validation import SectorKey
from sitescore_data.validators.readiness import (
    NORMALIZED_FEATURE_NAMES,
    ScoringReadinessValidator,
    create_ready_category_score_payload,
)


NOW = datetime(2026, 8, 12, 13, 0, tzinfo=timezone.utc)


def metric(
    value: int | float | None,
    *,
    availability: AvailabilityState = AvailabilityState.AVAILABLE,
    quality: DataQualityState = DataQualityState.FULL,
    eligibility: ScoreEligibility = ScoreEligibility.ELIGIBLE,
    calibration: CalibrationState = CalibrationState.CALIBRATED,
    is_proxy: bool = False,
    reason_codes: tuple[str, ...] = (),
    source_ref: str = "source_one",
) -> MetricValue:
    refs = () if availability is AvailabilityState.NOT_APPLICABLE else (source_ref,)
    return MetricValue(
        value=value,
        unit="score_0_100",
        availability=availability,
        data_quality=quality,
        score_eligibility=eligibility,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=is_proxy,
        source_refs=refs,
        method_version="feature-v1",
        reason_codes=reason_codes,
    )


def geography() -> GeographyRef:
    return GeographyRef(
        geography_type=GeographyType.CBSA,
        geography_id="35620",
        name="New York-Newark-Jersey City",
        country_code="US",
        source_ref="benchmark_geo",
        source_version="2025",
    )


def benchmark(benchmark_id: str) -> BenchmarkReference:
    return BenchmarkReference(
        benchmark_id=benchmark_id,
        artifact_ref=f"artifact://{benchmark_id}",
        frame_id="commercial_frame_v1",
        frame_version="1.0",
        population_type=(
            BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES
        ),
        benchmark_geography_ref=geography(),
        source_refs=("benchmark_source", "benchmark_geo"),
    )


def ready_features(**overrides: object) -> NormalizedLocationFeatures:
    values: dict[str, object] = {
        "walkable_population_score": metric(60),
        "target_population_density_score": metric(55),
        "age_target_concentration_score": metric(
            50,
            calibration=CalibrationState.UNCALIBRATED,
            is_proxy=True,
            reason_codes=("age_affinity_not_calibrated",),
        ),
        "competition_opportunity_score": metric(68),
        "walkable_reach_area_score": metric(65),
        "transit_access_score": metric(70),
        "road_parking_access_score": metric(72),
        "household_income_score": metric(75),
        "competition_benchmark_ref": benchmark("competition_benchmark_v1"),
        "competition_measurement_definition_id": "competition_measurement_v1",
        "competition_normalization_policy_version": "competition-norm-v1",
        "transit_benchmark_ref": benchmark("transit_benchmark_v1"),
        "transit_source_bundle_fingerprint": "sha256:transit-bundle-v1",
        "transit_normalization_policy_version": "transit-norm-v1",
        "road_parking_composite_policy_version": "road-parking-v1",
        "source_refs": (
            "source_one",
            "benchmark_source",
            "benchmark_geo",
        ),
        "feature_contract_version": "1.0",
        "generated_at": NOW,
    }
    values.update(overrides)
    return NormalizedLocationFeatures(**values)  # type: ignore[arg-type]


def policies(**overrides: FeatureReadinessPolicy) -> tuple[FeatureReadinessPolicy, ...]:
    values = {
        name: FeatureReadinessPolicy(
            feature_name=name,
            required=True,
        )
        for name in NORMALIZED_FEATURE_NAMES
    }
    values["age_target_concentration_score"] = FeatureReadinessPolicy(
        feature_name="age_target_concentration_score",
        required=True,
        fallback_policy_id="age_neutral_fallback",
        fallback_policy_version="1.0",
    )
    values["competition_opportunity_score"] = FeatureReadinessPolicy(
        feature_name="competition_opportunity_score",
        required=True,
        required_policy_version="competition-norm-v1",
        resolved_policy_version="competition-norm-v1",
    )
    values["transit_access_score"] = FeatureReadinessPolicy(
        feature_name="transit_access_score",
        required=True,
        required_policy_version="transit-norm-v1",
        resolved_policy_version="transit-norm-v1",
    )
    values["road_parking_access_score"] = FeatureReadinessPolicy(
        feature_name="road_parking_access_score",
        required=True,
        required_policy_version="road-parking-v1",
        resolved_policy_version="road-parking-v1",
    )
    values.update(overrides)
    return tuple(values[name] for name in NORMALIZED_FEATURE_NAMES)


def compatibility(**overrides: object) -> ReadinessCompatibilityInput:
    values: dict[str, object] = {
        "competition_benchmark_measurement_definition_id": (
            "competition_measurement_v1"
        ),
        "transit_benchmark_source_bundle_fingerprint": (
            "sha256:transit-bundle-v1"
        ),
    }
    values.update(overrides)
    return ReadinessCompatibilityInput(**values)  # type: ignore[arg-type]


def approved_age_fallbacks(
    *,
    policy_id: str = "age_neutral_fallback",
    policy_version: str = "1.0",
    feature_name: str = "age_target_concentration_score",
) -> tuple[ApprovedFallbackPolicyRef, ...]:
    return (
        ApprovedFallbackPolicyRef(
            feature_name=feature_name,
            policy_id=policy_id,
            policy_version=policy_version,
        ),
    )


def validate(
    features: NormalizedLocationFeatures | None = None,
    *,
    feature_policies: tuple[FeatureReadinessPolicy, ...] | None = None,
    compat: ReadinessCompatibilityInput | None = None,
    fingerprint: str = "readiness:abc123",
    approved_fallback_policies: tuple[ApprovedFallbackPolicyRef, ...] | None = None,
) -> ScoringReadinessResult:
    return ScoringReadinessValidator(validator_version="readiness-v1").validate(
        features=features or ready_features(),
        feature_policies=feature_policies or policies(),
        compatibility=compat or compatibility(),
        approved_fallback_policies=(
            approved_age_fallbacks()
            if approved_fallback_policies is None
            else approved_fallback_policies
        ),
        evaluated_at=NOW,
        readiness_fingerprint=fingerprint,
    )


def unavailable_metric(
    availability: AvailabilityState,
    *,
    eligibility: ScoreEligibility = ScoreEligibility.INELIGIBLE,
) -> MetricValue:
    return metric(
        None,
        availability=availability,
        quality=(
            DataQualityState.MISSING
            if availability is not AvailabilityState.NOT_APPLICABLE
            else DataQualityState.NOT_APPLICABLE
        ),
        eligibility=(
            ScoreEligibility.NOT_APPLICABLE
            if availability is AvailabilityState.NOT_APPLICABLE
            else eligibility
        ),
        calibration=(
            CalibrationState.NOT_APPLICABLE
            if availability is AvailabilityState.NOT_APPLICABLE
            else CalibrationState.CALIBRATED
        ),
    )


def test_all_required_ready_features_pass() -> None:
    result = validate()
    assert result.is_score_ready is True
    assert result.missing_required_features == ()
    assert result.uncalibrated_features == ()
    assert result.insufficient_quality_features == ()
    assert result.incompatible_features == ()
    assert result.reason_codes == ()


@pytest.mark.parametrize(
    "availability",
    [AvailabilityState.MISSING, AvailabilityState.UNAVAILABLE],
)
def test_missing_or_unavailable_required_feature_blocks(
    availability: AvailabilityState,
) -> None:
    result = validate(
        ready_features(
            walkable_population_score=unavailable_metric(availability)
        )
    )
    assert result.is_score_ready is False
    assert "walkable_population_score" in result.missing_required_features
    assert ScoringReadinessReason.MISSING_REQUIRED_FEATURE in result.reason_codes


def test_diagnostic_only_required_feature_blocks() -> None:
    result = validate(
        ready_features(
            walkable_population_score=metric(
                60,
                eligibility=ScoreEligibility.DIAGNOSTIC_ONLY,
            )
        )
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.FEATURE_DIAGNOSTIC_ONLY in result.reason_codes


def test_ineligible_required_feature_blocks() -> None:
    result = validate(
        ready_features(
            walkable_population_score=metric(
                60,
                eligibility=ScoreEligibility.INELIGIBLE,
            )
        )
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.FEATURE_INELIGIBLE in result.reason_codes


def test_uncalibrated_required_feature_blocks() -> None:
    result = validate(
        ready_features(
            walkable_population_score=metric(
                60,
                calibration=CalibrationState.UNCALIBRATED,
            )
        )
    )
    assert result.is_score_ready is False
    assert "walkable_population_score" in result.uncalibrated_features
    assert ScoringReadinessReason.FEATURE_UNCALIBRATED in result.reason_codes


def test_valid_explicit_age_fallback_is_allowed() -> None:
    result = validate()
    age_state = next(
        state
        for state in result.feature_states
        if state.feature_name == "age_target_concentration_score"
    )
    assert result.is_score_ready is True
    assert age_state.calibration_state is CalibrationState.UNCALIBRATED
    assert age_state.fallback_policy_id == "age_neutral_fallback"
    assert age_state.fallback_policy_version == "1.0"
    assert age_state.reason_codes == ()


def test_age_fallback_without_explicit_approved_policy_is_blocked() -> None:
    result = validate(
        feature_policies=policies(
            age_target_concentration_score=FeatureReadinessPolicy(
                feature_name="age_target_concentration_score",
                required=True,
            )
        )
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.FEATURE_UNCALIBRATED in result.reason_codes


def test_generic_uncalibrated_fallback_policy_does_not_bypass_block() -> None:
    result = validate(
        ready_features(
            walkable_population_score=metric(
                50,
                calibration=CalibrationState.UNCALIBRATED,
                is_proxy=True,
                reason_codes=("age_affinity_not_calibrated",),
            )
        ),
        feature_policies=policies(
            walkable_population_score=FeatureReadinessPolicy(
                feature_name="walkable_population_score",
                required=True,
                fallback_policy_id="generic_neutral",
                fallback_policy_version="1.0",
            )
        ),
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.FEATURE_UNCALIBRATED in result.reason_codes


def test_competition_measurement_mismatch_blocks() -> None:
    result = validate(
        compat=compatibility(
            competition_benchmark_measurement_definition_id=(
                "different_measurement_v2"
            )
        )
    )
    assert result.is_score_ready is False
    assert "competition_opportunity_score" in result.incompatible_features
    assert (
        ScoringReadinessReason.COMPETITION_MEASUREMENT_MISMATCH
        in result.reason_codes
    )


def test_transit_source_bundle_mismatch_blocks() -> None:
    result = validate(
        compat=compatibility(
            transit_benchmark_source_bundle_fingerprint="sha256:different"
        )
    )
    assert result.is_score_ready is False
    assert "transit_access_score" in result.incompatible_features
    assert ScoringReadinessReason.TRANSIT_SOURCE_BUNDLE_MISMATCH in result.reason_codes


def test_road_parking_policy_absent_blocks() -> None:
    result = validate(
        ready_features(road_parking_composite_policy_version=None)
    )
    assert result.is_score_ready is False
    assert "road_parking_access_score" in result.incompatible_features
    assert (
        ScoringReadinessReason.ROAD_PARKING_COMPOSITE_UNAVAILABLE
        in result.reason_codes
    )


def test_road_parking_calibrated_eligible_policy_resolved_passes() -> None:
    result = validate()
    road_state = next(
        state
        for state in result.feature_states
        if state.feature_name == "road_parking_access_score"
    )
    assert result.is_score_ready is True
    assert road_state.score_eligibility is ScoreEligibility.ELIGIBLE
    assert road_state.calibration_state is CalibrationState.CALIBRATED
    assert road_state.resolved_policy_version == "road-parking-v1"


def test_policy_version_mismatch_blocks() -> None:
    result = validate(
        feature_policies=policies(
            transit_access_score=FeatureReadinessPolicy(
                feature_name="transit_access_score",
                required=True,
                required_policy_version="transit-norm-v2",
                resolved_policy_version="transit-norm-v1",
            )
        )
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.POLICY_VERSION_MISMATCH in result.reason_codes


def test_false_readiness_has_blocking_reason() -> None:
    result = validate(
        ready_features(
            walkable_population_score=unavailable_metric(
                AvailabilityState.MISSING
            )
        )
    )
    assert result.is_score_ready is False
    assert result.reason_codes


def test_result_is_immutable_and_deterministic() -> None:
    left = validate()
    right = validate()
    assert left == right
    assert hash(left) == hash(right)
    with pytest.raises(FrozenInstanceError):
        left.is_score_ready = False  # type: ignore[misc]


def test_readiness_requires_aware_evaluated_at() -> None:
    with pytest.raises(ValueError):
        ScoringReadinessValidator(validator_version="readiness-v1").validate(
            features=ready_features(),
            feature_policies=policies(),
            compatibility=compatibility(),
            approved_fallback_policies=approved_age_fallbacks(),
            evaluated_at=datetime(2026, 8, 12, 13, 0),
            readiness_fingerprint="readiness:abc123",
        )


def test_factory_rejects_nonready_result() -> None:
    readiness = validate(
        ready_features(
            walkable_population_score=unavailable_metric(
                AvailabilityState.MISSING
            )
        )
    )
    with pytest.raises(ValueError):
        create_ready_category_score_payload(
            readiness=readiness,
            sector_key=SectorKey("coffee"),
            demand=70,
            competition=60,
            accessibility=80,
            economics=55,
            feature_contract_version="1.0",
            normalization_policy_version="normalization-v1",
        )


def test_factory_accepts_precomputed_scores_and_preserves_fingerprint() -> None:
    readiness = validate(fingerprint="readiness:factory-test")
    payload = create_ready_category_score_payload(
        readiness=readiness,
        sector_key=SectorKey("coffee"),
        demand=70,
        competition=60,
        accessibility=80,
        economics=55,
        feature_contract_version="1.0",
        normalization_policy_version="normalization-v1",
    )
    assert payload.demand == 70
    assert payload.competition == 60
    assert payload.accessibility == 80
    assert payload.economics == 55
    assert payload.readiness_fingerprint == "readiness:factory-test"


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, -0.1, 100.1])
def test_factory_payload_numeric_invariants_still_apply(bad: float) -> None:
    readiness = validate()
    with pytest.raises(ValueError):
        create_ready_category_score_payload(
            readiness=readiness,
            sector_key=SectorKey("coffee"),
            demand=bad,
            competition=60,
            accessibility=80,
            economics=55,
            feature_contract_version="1.0",
            normalization_policy_version="normalization-v1",
        )


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_readiness_schemas_have_no_mutable_annotations() -> None:
    for schema in (
        PolicyVersionRef,
        ApprovedFallbackPolicyRef,
    FeatureReadinessPolicy,
        ReadinessCompatibilityInput,
        ScoringFeatureReadiness,
        ScoringReadinessResult,
    ):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def test_special_feature_policy_resolution_uses_actual_feature_metadata() -> None:
    result = validate(
        ready_features(transit_normalization_policy_version="transit-norm-v2"),
        feature_policies=policies(
            transit_access_score=FeatureReadinessPolicy(
                feature_name="transit_access_score",
                required=True,
                required_policy_version="transit-norm-v1",
                resolved_policy_version="transit-norm-v1",
            )
        ),
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.POLICY_VERSION_MISMATCH in result.reason_codes
    resolved = {
        entry.policy_id: entry.version
        for entry in result.resolved_policy_versions
    }
    assert resolved["transit_access_score"] == "transit-norm-v2"


def test_road_parking_missing_actual_policy_is_not_reported_as_resolved() -> None:
    result = validate(
        ready_features(road_parking_composite_policy_version=None)
    )
    resolved_ids = {
        entry.policy_id
        for entry in result.resolved_policy_versions
    }
    assert "road_parking_access_score" not in resolved_ids
    assert ScoringReadinessReason.POLICY_NOT_CONFIGURED in result.reason_codes


def test_arbitrary_age_fallback_id_is_blocked_without_matching_approval() -> None:
    result = validate(
        feature_policies=policies(
            age_target_concentration_score=FeatureReadinessPolicy(
                feature_name="age_target_concentration_score",
                required=True,
                fallback_policy_id="invented_fallback",
                fallback_policy_version="1.0",
            )
        )
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.AGE_FALLBACK_POLICY_INVALID in result.reason_codes


def test_wrong_age_fallback_version_is_blocked() -> None:
    result = validate(
        feature_policies=policies(
            age_target_concentration_score=FeatureReadinessPolicy(
                feature_name="age_target_concentration_score",
                required=True,
                fallback_policy_id="age_neutral_fallback",
                fallback_policy_version="2.0",
            )
        )
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.AGE_FALLBACK_POLICY_INVALID in result.reason_codes


def test_no_approved_age_fallback_is_blocked() -> None:
    result = validate(approved_fallback_policies=())
    assert result.is_score_ready is False
    assert ScoringReadinessReason.AGE_FALLBACK_POLICY_INVALID in result.reason_codes


def test_age_approval_cannot_target_another_feature() -> None:
    with pytest.raises(ValueError):
        validate(
            approved_fallback_policies=approved_age_fallbacks(
                feature_name="walkable_population_score"
            )
        )


def test_required_false_cannot_bypass_frozen_v1_readiness() -> None:
    with pytest.raises(ValueError):
        validate(
            feature_policies=policies(
                road_parking_access_score=FeatureReadinessPolicy(
                    feature_name="road_parking_access_score",
                    required=False,
                )
            )
        )


def test_readiness_fingerprint_is_preserved_external_reference_not_generated() -> None:
    left = validate(fingerprint="external-readiness-ref-a")
    right = validate(fingerprint="external-readiness-ref-b")
    assert left.readiness_fingerprint == "external-readiness-ref-a"
    assert right.readiness_fingerprint == "external-readiness-ref-b"
    assert left.feature_states == right.feature_states


def test_matching_but_arbitrary_requested_and_approved_age_fallback_is_blocked() -> None:
    result = validate(
        feature_policies=policies(
            age_target_concentration_score=FeatureReadinessPolicy(
                feature_name="age_target_concentration_score",
                required=True,
                fallback_policy_id="invented_fallback",
                fallback_policy_version="9.9",
            )
        ),
        approved_fallback_policies=approved_age_fallbacks(
            policy_id="invented_fallback",
            policy_version="9.9",
        ),
    )
    assert result.is_score_ready is False
    assert ScoringReadinessReason.AGE_FALLBACK_POLICY_INVALID in result.reason_codes


def test_readiness_result_rejects_fabricated_or_incomplete_v1_surface() -> None:
    canonical = validate()

    with pytest.raises(ValueError):
        replace(canonical, feature_states=())

    with pytest.raises(ValueError):
        replace(canonical, feature_states=canonical.feature_states[:-1])

    wrong_required = replace(canonical.feature_states[0], required=False)
    with pytest.raises(ValueError):
        replace(
            canonical,
            feature_states=(wrong_required,) + canonical.feature_states[1:],
        )

    with pytest.raises(ValueError):
        replace(
            canonical,
            feature_states=(canonical.feature_states[1], canonical.feature_states[0])
            + canonical.feature_states[2:],
        )


def test_ready_result_rejects_feature_level_blocking_reason() -> None:
    canonical = validate()
    blocked = replace(
        canonical.feature_states[0],
        reason_codes=(ScoringReadinessReason.FEATURE_INELIGIBLE,),
    )
    with pytest.raises(ValueError):
        replace(
            canonical,
            feature_states=(blocked,) + canonical.feature_states[1:],
        )


def test_readiness_summary_collections_must_match_feature_reasons() -> None:
    nonready = validate(
        ready_features(
            walkable_population_score=unavailable_metric(AvailabilityState.MISSING)
        )
    )
    assert nonready.missing_required_features == ("walkable_population_score",)

    with pytest.raises(ValueError):
        replace(nonready, missing_required_features=())

    with pytest.raises(ValueError):
        replace(
            nonready,
            missing_required_features=(
                "walkable_population_score",
                "household_income_score",
            ),
        )


def test_global_reason_codes_must_match_feature_state_reasons() -> None:
    canonical = validate()
    with pytest.raises(ValueError):
        replace(
            canonical,
            is_score_ready=False,
            reason_codes=(ScoringReadinessReason.POLICY_VERSION_MISMATCH,),
        )
