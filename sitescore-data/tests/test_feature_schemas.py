from dataclasses import FrozenInstanceError, fields
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
from sitescore_data.schemas.features import (
    DerivedLocationMetrics,
    NormalizedLocationFeatures,
    ReadyCategoryScorePayload,
)
from sitescore_data.schemas.geography import GeographyRef
from sitescore_data.validation import SectorKey


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)


def metric(
    value: int | float | None,
    unit: str,
    *,
    availability: AvailabilityState = AvailabilityState.AVAILABLE,
    quality: DataQualityState = DataQualityState.FULL,
    eligibility: ScoreEligibility = ScoreEligibility.ELIGIBLE,
    calibration: CalibrationState = CalibrationState.CALIBRATED,
    is_proxy: bool = False,
    source_ref: str = "source_one",
    reason_codes: tuple[str, ...] = (),
) -> MetricValue:
    refs = () if availability is AvailabilityState.NOT_APPLICABLE else (source_ref,)
    return MetricValue(
        value=value,
        unit=unit,
        availability=availability,
        data_quality=quality,
        score_eligibility=eligibility,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=is_proxy,
        source_refs=refs,
        method_version="method-v1",
        reason_codes=reason_codes,
    )


def unavailable_score(
    availability: AvailabilityState = AvailabilityState.UNAVAILABLE,
) -> MetricValue:
    quality = (
        DataQualityState.NOT_APPLICABLE
        if availability is AvailabilityState.NOT_APPLICABLE
        else DataQualityState.MISSING
    )
    eligibility = (
        ScoreEligibility.NOT_APPLICABLE
        if availability is AvailabilityState.NOT_APPLICABLE
        else ScoreEligibility.INELIGIBLE
    )
    calibration = (
        CalibrationState.NOT_APPLICABLE
        if availability is AvailabilityState.NOT_APPLICABLE
        else CalibrationState.UNCALIBRATED
    )
    return metric(
        None,
        "score_0_100",
        availability=availability,
        quality=quality,
        eligibility=eligibility,
        calibration=calibration,
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


def derived(**overrides: object) -> DerivedLocationMetrics:
    values: dict[str, object] = {
        "walkable_population": metric(12000, "people"),
        "target_population_density": metric(3000, "people_per_km2"),
        "household_income": metric(85000, "usd_per_household"),
        "household_income_ratio": metric(1.1, "ratio"),
        "competition_pressure": metric(
            None,
            "density_reduction",
            availability=AvailabilityState.UNKNOWN,
            quality=DataQualityState.DEGRADED,
            eligibility=ScoreEligibility.DIAGNOSTIC_ONLY,
            calibration=CalibrationState.UNCALIBRATED,
        ),
        "walkable_reach_area_km2": metric(1.8, "km2"),
        "transit_service_departure_equivalents_per_hour": metric(
            12.5, "departure_equivalents_per_hour"
        ),
        "road_reachable_area_km2": metric(42.0, "km2"),
        "parking_public_offstreet_capacity": metric(250, "spaces"),
        "parking_legal_curb_length_m": metric(800.0, "m"),
        "demographic_snapshot_ref": "demographic_snapshot_001",
        "competition_snapshot_ref": "competition_snapshot_001",
        "road_snapshot_ref": "road_snapshot_001",
        "parking_snapshot_ref": "parking_snapshot_001",
        "source_refs": ("source_one",),
        "feature_contract_version": "1.0",
        "generated_at": NOW,
    }
    values.update(overrides)
    return DerivedLocationMetrics(**values)  # type: ignore[arg-type]


def score(value: float, *, source_ref: str = "source_one") -> MetricValue:
    return metric(value, "score_0_100", source_ref=source_ref)


def normalized(**overrides: object) -> NormalizedLocationFeatures:
    values: dict[str, object] = {
        "walkable_population_score": score(60),
        "target_population_density_score": score(55),
        "age_target_concentration_score": metric(
            50,
            "score_0_100",
            calibration=CalibrationState.UNCALIBRATED,
            is_proxy=True,
            reason_codes=("age_affinity_not_calibrated",),
        ),
        "competition_opportunity_score": unavailable_score(),
        "walkable_reach_area_score": score(65),
        "transit_access_score": score(70),
        "road_parking_access_score": unavailable_score(),
        "household_income_score": score(75),
        "competition_benchmark_ref": None,
        "competition_measurement_definition_id": None,
        "competition_normalization_policy_version": None,
        "transit_benchmark_ref": None,
        "transit_source_bundle_fingerprint": "sha256:transit-bundle",
        "transit_normalization_policy_version": "transit-norm-v1",
        "road_parking_composite_policy_version": None,
        "source_refs": ("source_one",),
        "feature_contract_version": "1.0",
        "generated_at": NOW,
    }
    values.update(overrides)
    return NormalizedLocationFeatures(**values)  # type: ignore[arg-type]


def payload(**overrides: object) -> ReadyCategoryScorePayload:
    values: dict[str, object] = {
        "sector_key": SectorKey("coffee"),
        "demand": 70.0,
        "competition": 60.0,
        "accessibility": 80.0,
        "economics": 55.0,
        "readiness_fingerprint": "readiness:abc123",
        "feature_contract_version": "1.0",
        "normalization_policy_version": "normalization-v1",
    }
    values.update(overrides)
    return ReadyCategoryScorePayload(**values)  # type: ignore[arg-type]


def test_derived_metrics_preserve_real_units_and_are_not_scores() -> None:
    value = derived()
    assert value.walkable_population.unit == "people"
    assert value.transit_service_departure_equivalents_per_hour.unit == (
        "departure_equivalents_per_hour"
    )
    assert value.walkable_reach_area_km2.unit == "km2"
    assert value.walkable_population.unit != "score_0_100"


def test_derived_metric_state_aware_missing_and_uncalibrated_supported() -> None:
    value = derived()
    assert value.competition_pressure.value is None
    assert value.competition_pressure.availability is AvailabilityState.UNKNOWN
    assert (
        value.competition_pressure.calibration_state
        is CalibrationState.UNCALIBRATED
    )


def test_multi_scale_scalar_reductions_must_be_calibrated_when_numeric() -> None:
    with pytest.raises(ValueError):
        derived(
            competition_pressure=metric(
                3.0,
                "density_reduction",
                calibration=CalibrationState.UNCALIBRATED,
            )
        )

    with pytest.raises(ValueError):
        derived(
            road_reachable_area_km2=metric(
                42.0,
                "km2",
                calibration=CalibrationState.UNCALIBRATED,
            )
        )


def test_derived_metric_source_lineage_is_explicit() -> None:
    with pytest.raises(ValueError):
        derived(source_refs=())


@pytest.mark.parametrize("bad", [-0.01, 100.01, math.nan, math.inf, -math.inf])
def test_normalized_available_scores_must_be_finite_0_to_100(bad: float) -> None:
    with pytest.raises(ValueError):
        normalized(walkable_population_score=score(bad))


def test_unavailable_normalized_feature_is_nonnumeric() -> None:
    value = normalized()
    assert value.road_parking_access_score.value is None
    assert (
        value.road_parking_access_score.availability
        is AvailabilityState.UNAVAILABLE
    )


def test_age_neutral_50_can_be_explicit_proxy_and_uncalibrated() -> None:
    age = normalized().age_target_concentration_score
    assert age.value == 50
    assert age.is_proxy is True
    assert age.calibration_state is CalibrationState.UNCALIBRATED
    assert "age_affinity_not_calibrated" in age.reason_codes


def test_uncalibrated_age_numeric_is_only_frozen_neutral_fallback() -> None:
    with pytest.raises(ValueError):
        normalized(
            age_target_concentration_score=metric(
                60,
                "score_0_100",
                calibration=CalibrationState.UNCALIBRATED,
                is_proxy=True,
                reason_codes=("age_affinity_not_calibrated",),
            )
        )

    with pytest.raises(ValueError):
        normalized(
            age_target_concentration_score=metric(
                50,
                "score_0_100",
                calibration=CalibrationState.UNCALIBRATED,
                is_proxy=False,
                reason_codes=("age_affinity_not_calibrated",),
            )
        )


def test_derived_age_evidence_is_snapshot_reference_not_ambiguous_scalar() -> None:
    value = derived()
    assert value.demographic_snapshot_ref == "demographic_snapshot_001"
    assert not hasattr(value, "age_profile_population_share")


def test_true_zero_transit_score_is_available_zero() -> None:
    value = normalized(transit_access_score=score(0))
    assert value.transit_access_score.value == 0
    assert value.transit_access_score.availability is AvailabilityState.AVAILABLE


def test_missing_transit_does_not_become_available_zero() -> None:
    value = normalized(
        transit_access_score=unavailable_score(AvailabilityState.MISSING)
    )
    assert value.transit_access_score.value is None
    assert value.transit_access_score.availability is AvailabilityState.MISSING


def test_competition_reproducibility_metadata_can_be_carried_without_validation_engine() -> None:
    ref = benchmark("competition_benchmark_v1")
    value = normalized(
        competition_benchmark_ref=ref,
        competition_measurement_definition_id="competition_measurement_v1",
        competition_normalization_policy_version="competition-norm-v1",
        source_refs=("source_one", "benchmark_source", "benchmark_geo"),
    )
    assert value.competition_benchmark_ref == ref
    assert value.competition_measurement_definition_id == "competition_measurement_v1"


def test_ready_payload_requires_sector_key() -> None:
    with pytest.raises(TypeError):
        payload(sector_key="coffee")


@pytest.mark.parametrize("field_name", ["demand", "competition", "accessibility", "economics"])
@pytest.mark.parametrize("bad", [-0.01, 100.01, math.nan, math.inf, -math.inf])
def test_ready_payload_scores_are_finite_and_bounded(
    field_name: str,
    bad: float,
) -> None:
    with pytest.raises((ValueError, TypeError)):
        payload(**{field_name: bad})


def test_ready_payload_is_deterministic_and_immutable() -> None:
    left = payload()
    right = payload()
    assert left == right
    assert hash(left) == hash(right)
    with pytest.raises(FrozenInstanceError):
        left.demand = 50  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_feature_schemas_have_no_mutable_annotations() -> None:
    for schema in (
        DerivedLocationMetrics,
        NormalizedLocationFeatures,
        ReadyCategoryScorePayload,
    ):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def test_feature_schemas_require_explicit_aware_generated_at() -> None:
    with pytest.raises(ValueError):
        derived(generated_at=datetime(2026, 8, 12, 12, 0))
    with pytest.raises(ValueError):
        normalized(generated_at=datetime(2026, 8, 12, 12, 0))


def test_feature_contracts_are_exported_from_schemas_package() -> None:
    from sitescore_data.schemas import (
        DerivedLocationMetrics as ExportedDerivedLocationMetrics,
        NormalizedLocationFeatures as ExportedNormalizedLocationFeatures,
        ReadyCategoryScorePayload as ExportedReadyCategoryScorePayload,
    )

    assert ExportedDerivedLocationMetrics is DerivedLocationMetrics
    assert ExportedNormalizedLocationFeatures is NormalizedLocationFeatures
    assert ExportedReadyCategoryScorePayload is ReadyCategoryScorePayload
