from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    GeographyType,
    PersistenceClass,
    PipelineStatus,
    ScoreEligibility,
)
from sitescore_data.schemas.common import DataContractVersions, MetricValue, SourceMetadata
from sitescore_data.schemas.features import (
    DerivedLocationMetrics,
    NormalizedLocationFeatures,
)
from sitescore_data.schemas.geography import GeographyRef, ResolvedLocation
from sitescore_data.schemas.pipeline import PipelineReason, RealDataPipelineResult
from sitescore_data.schemas.readiness import (
    ScoringFeatureReadiness,
    ScoringReadinessReason,
    ScoringReadinessResult,
)
from sitescore_data.feature_surface import NORMALIZED_FEATURE_NAMES
from sitescore_data.serialization import to_primitive
from sitescore_data.validation import SectorKey
from test_competition_schemas import snapshot as competition_snapshot
from test_transit_schemas import snapshot as transit_snapshot


NOW = datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc)
SECTOR = SectorKey("coffee")


def metric(value: float, *, unit: str, calibration: CalibrationState = CalibrationState.CALIBRATED) -> MetricValue:
    return MetricValue(
        value=value,
        unit=unit,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=False,
        source_refs=("source_one",),
        method_version="metric-v1",
    )


def derived() -> DerivedLocationMetrics:
    return DerivedLocationMetrics(
        walkable_population=metric(1000, unit="people"),
        target_population_density=metric(2500, unit="people_per_km2"),
        household_income=metric(80000, unit="usd_per_household"),
        household_income_ratio=metric(1.1, unit="ratio"),
        competition_pressure=metric(3.0, unit="competitors_per_km2"),
        walkable_reach_area_km2=metric(1.5, unit="km2"),
        transit_service_departure_equivalents_per_hour=metric(
            12.0,
            unit="departure_equivalents_per_hour",
        ),
        road_reachable_area_km2=metric(20.0, unit="km2"),
        parking_public_offstreet_capacity=metric(150, unit="spaces"),
        parking_legal_curb_length_m=metric(300, unit="m"),
        demographic_snapshot_ref="demographic_snapshot_1",
        competition_snapshot_ref="competition_snapshot_1",
        road_snapshot_ref="road_snapshot_1",
        parking_snapshot_ref="parking_snapshot_1",
        source_refs=("source_one",),
        feature_contract_version="1.0",
        generated_at=NOW,
    )


def score(value: float) -> MetricValue:
    return metric(value, unit="score_0_100")


def normalized(**overrides: object) -> NormalizedLocationFeatures:
    values: dict[str, object] = dict(
        walkable_population_score=score(60),
        target_population_density_score=score(55),
        age_target_concentration_score=score(50),
        competition_opportunity_score=score(68),
        walkable_reach_area_score=score(65),
        transit_access_score=score(70),
        road_parking_access_score=score(72),
        household_income_score=score(75),
        competition_benchmark_ref=None,
        competition_measurement_definition_id=None,
        competition_normalization_policy_version=None,
        transit_benchmark_ref=None,
        transit_source_bundle_fingerprint=None,
        transit_normalization_policy_version=None,
        road_parking_composite_policy_version=None,
        source_refs=("source_one",),
        feature_contract_version="1.0",
        generated_at=NOW,
    )
    values.update(overrides)
    return NormalizedLocationFeatures(**values)  # type: ignore[arg-type]


def readiness(ready: bool, *, fingerprint: str = "readiness:abc") -> ScoringReadinessResult:
    states = tuple(
        ScoringFeatureReadiness(
            feature_name=name,
            required=True,
            availability=(
                AvailabilityState.MISSING
                if (not ready and name == "transit_access_score")
                else AvailabilityState.AVAILABLE
            ),
            data_quality=(
                DataQualityState.MISSING
                if (not ready and name == "transit_access_score")
                else DataQualityState.FULL
            ),
            score_eligibility=(
                ScoreEligibility.INELIGIBLE
                if (not ready and name == "transit_access_score")
                else ScoreEligibility.ELIGIBLE
            ),
            calibration_state=CalibrationState.CALIBRATED,
            required_policy_version=None,
            resolved_policy_version=None,
            fallback_policy_id=None,
            fallback_policy_version=None,
            reason_codes=(
                (ScoringReadinessReason.MISSING_REQUIRED_FEATURE,)
                if (not ready and name == "transit_access_score")
                else ()
            ),
        )
        for name in NORMALIZED_FEATURE_NAMES
    )
    return ScoringReadinessResult(
        is_score_ready=ready,
        missing_required_features=("transit_access_score",) if not ready else (),
        uncalibrated_features=(),
        insufficient_quality_features=(),
        incompatible_features=(),
        reason_codes=(ScoringReadinessReason.MISSING_REQUIRED_FEATURE,) if not ready else (),
        required_policy_versions=(),
        resolved_policy_versions=(),
        feature_states=states,
        validator_version="readiness-v1",
        evaluated_at=NOW,
        readiness_fingerprint=fingerprint,
    )


def source(source_id: str) -> SourceMetadata:
    return SourceMetadata(
        source_id=source_id,
        provider="Provider",
        dataset="Dataset",
        dataset_release="2026-08",
        vintage="2026",
        schema_version="1",
        retrieved_at=NOW,
        content_hash=f"opaque:{source_id}",
        persistence_class=PersistenceClass.PERSIST,
        data_quality=DataQualityState.FULL,
    )


def resolved_location() -> ResolvedLocation:
    geo = GeographyRef(
        geography_type=GeographyType.CBSA,
        geography_id="35620",
        name="New York-Newark-Jersey City",
        country_code="US",
        source_ref="geo_source",
        source_version="2025",
    )
    return ResolvedLocation(
        latitude=40.7128,
        longitude=-74.006,
        formatted_address="New York, NY, USA",
        country_code="US",
        geography_refs=(geo,),
        source_refs=("geo_source",),
        resolution_method_version="resolve-v1",
        generated_at=NOW,
    )


def result(**overrides: object) -> RealDataPipelineResult:
    values: dict[str, object] = {
        "status": PipelineStatus.SCORE_READY,
        "sector_key": SECTOR,
        "resolved_location": resolved_location(),
        "demographics": None,
        "pedestrian_catchment": None,
        "isochrone": None,
        "competition": None,
        "transit": None,
        "road": None,
        "parking": None,
        "derived_metrics": derived(),
        "normalized_features": normalized(),
        "scoring_readiness": readiness(True),
        "source_metadata": (),
        "pipeline_version": "pipeline-v1",
        "data_contract_versions": DataContractVersions.current(),
        "generated_at": NOW,
        "reason_codes": (),
    }
    values.update(overrides)
    return RealDataPipelineResult(**values)  # type: ignore[arg-type]


def test_score_ready_valid_and_means_ready_not_scored() -> None:
    value = result()
    assert value.status is PipelineStatus.SCORE_READY
    assert value.scoring_readiness is not None
    assert value.scoring_readiness.is_score_ready is True
    assert not hasattr(value, "ready_category_score_payload")


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("resolved_location", None),
        ("scoring_readiness", None),
        ("normalized_features", None),
    ],
)
def test_score_ready_requires_data_layer_terminal_fields(
    field_name: str,
    field_value: object,
) -> None:
    overrides: dict[str, object] = {field_name: field_value}
    if field_name == "normalized_features":
        overrides["scoring_readiness"] = None
    with pytest.raises(ValueError):
        result(**overrides)


def test_score_ready_requires_true_readiness() -> None:
    with pytest.raises(ValueError):
        result(scoring_readiness=readiness(False))


def test_not_score_ready_requires_false_readiness_and_preserves_reasons() -> None:
    value = result(
        status=PipelineStatus.NOT_SCORE_READY,
        scoring_readiness=readiness(False),
        reason_codes=(PipelineReason.SCORING_NOT_READY,),
    )
    assert value.scoring_readiness is not None
    assert value.scoring_readiness.reason_codes == (
        ScoringReadinessReason.MISSING_REQUIRED_FEATURE,
    )

    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.NOT_SCORE_READY,
            scoring_readiness=readiness(True),
            reason_codes=(PipelineReason.SCORING_NOT_READY,),
        )


def test_not_score_ready_reason_taxonomy_is_exclusive() -> None:
    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.NOT_SCORE_READY,
            scoring_readiness=readiness(False),
            reason_codes=(),
        )

    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.NOT_SCORE_READY,
            scoring_readiness=readiness(False),
            reason_codes=(
                PipelineReason.SCORING_NOT_READY,
                PipelineReason.PIPELINE_STAGE_ERROR,
            ),
        )


def test_pipeline_error_requires_exclusive_error_reason() -> None:
    value = result(
        status=PipelineStatus.PIPELINE_ERROR,
        derived_metrics=None,
        normalized_features=None,
        scoring_readiness=None,
        reason_codes=(PipelineReason.PIPELINE_STAGE_ERROR,),
    )
    assert value.status is PipelineStatus.PIPELINE_ERROR

    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.PIPELINE_ERROR,
            derived_metrics=None,
            normalized_features=None,
            scoring_readiness=None,
            reason_codes=(),
        )

    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.PIPELINE_ERROR,
            derived_metrics=None,
            normalized_features=None,
            scoring_readiness=None,
            reason_codes=(
                PipelineReason.PIPELINE_STAGE_ERROR,
                PipelineReason.SCORING_NOT_READY,
            ),
        )


def test_pipeline_error_preserves_partial_upstream_evidence() -> None:
    location = resolved_location()
    value = result(
        status=PipelineStatus.PIPELINE_ERROR,
        resolved_location=location,
        derived_metrics=None,
        normalized_features=None,
        scoring_readiness=None,
        reason_codes=(PipelineReason.PIPELINE_STAGE_ERROR,),
    )
    assert value.resolved_location == location


def test_pipeline_error_cannot_contain_completed_readiness() -> None:
    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.PIPELINE_ERROR,
            reason_codes=(PipelineReason.PIPELINE_STAGE_ERROR,),
        )


def test_normalized_features_require_derived_metrics() -> None:
    with pytest.raises(ValueError):
        result(derived_metrics=None)


def test_readiness_requires_normalized_features() -> None:
    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.PIPELINE_ERROR,
            derived_metrics=derived(),
            normalized_features=None,
            scoring_readiness=readiness(True),
            reason_codes=(PipelineReason.PIPELINE_STAGE_ERROR,),
        )


def test_source_metadata_requires_unique_deterministic_order() -> None:
    a = source("a_source")
    b = source("b_source")
    assert result(source_metadata=(a, b)).source_metadata == (a, b)

    with pytest.raises(ValueError):
        result(source_metadata=(b, a))

    with pytest.raises(ValueError):
        result(source_metadata=(a, a))


def test_source_metadata_is_not_forced_to_resolve_all_opaque_nested_refs() -> None:
    # Nested refs use mixed source/artifact ontologies across Checkpoints 1-6.
    # An empty SourceMetadata registry is therefore structurally valid here.
    assert result(source_metadata=()).source_metadata == ()


def test_generated_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        result(generated_at=datetime(2026, 8, 12, 14, 0))


def test_pipeline_result_is_immutable() -> None:
    value = result()
    with pytest.raises(FrozenInstanceError):
        value.pipeline_version = "changed"  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_pipeline_schema_has_no_mutable_annotations() -> None:
    hints = get_type_hints(RealDataPipelineResult)
    for field in fields(RealDataPipelineResult):
        assert not _contains_mutable(hints[field.name])


def test_pipeline_serialization_is_deterministic() -> None:
    left = to_primitive(result(source_metadata=(source("a_source"),)))
    right = to_primitive(result(source_metadata=(source("a_source"),)))
    assert left == right
    assert left["status"] == "score_ready"
    assert left["reason_codes"] == []
    assert left["source_metadata"][0]["source_id"] == "a_source"


def test_pipeline_envelope_does_not_own_ready_category_score_payload() -> None:
    assert "ready_category_score_payload" not in {
        field.name for field in fields(RealDataPipelineResult)
    }


def test_score_ready_serialization_stops_before_category_payload() -> None:
    primitive = to_primitive(result())
    assert primitive["status"] == "score_ready"
    assert "ready_category_score_payload" not in primitive


def test_pipeline_error_rejects_false_readiness_too() -> None:
    with pytest.raises(ValueError):
        result(
            status=PipelineStatus.PIPELINE_ERROR,
            scoring_readiness=readiness(False),
            reason_codes=(PipelineReason.PIPELINE_STAGE_ERROR,),
        )


def test_not_score_ready_accepts_no_pipeline_error_reason() -> None:
    value = result(
        status=PipelineStatus.NOT_SCORE_READY,
        scoring_readiness=readiness(False),
        reason_codes=(PipelineReason.SCORING_NOT_READY,),
    )
    assert value.reason_codes == (PipelineReason.SCORING_NOT_READY,)


def test_transit_snapshot_to_normalized_identity_binding() -> None:
    transit = transit_snapshot(source_bundle_fingerprint="bundle_a")
    matching = normalized(transit_source_bundle_fingerprint="bundle_a")
    assert result(transit=transit, normalized_features=matching).transit == transit

    with pytest.raises(ValueError):
        result(
            transit=transit,
            normalized_features=normalized(
                transit_source_bundle_fingerprint="bundle_b"
            ),
        )


def test_competition_snapshot_to_normalized_identity_binding() -> None:
    competition = competition_snapshot(
        measurement_definition_id="competition_definition_a"
    )
    matching = normalized(
        competition_measurement_definition_id="competition_definition_a"
    )
    assert (
        result(competition=competition, normalized_features=matching).competition
        == competition
    )

    with pytest.raises(ValueError):
        result(
            competition=competition,
            normalized_features=normalized(
                competition_measurement_definition_id="competition_definition_b"
            ),
        )


def test_feature_contract_versions_must_be_coherent_within_pipeline_graph() -> None:
    with pytest.raises(ValueError):
        result(
            derived_metrics=replace(derived(), feature_contract_version="2.0")
        )

    with pytest.raises(ValueError):
        result(
            normalized_features=replace(
                normalized(),
                feature_contract_version="2.0",
            )
        )

    historical_versions = replace(
        DataContractVersions.current(),
        data_feature_contract_version="0.9",
    )
    historical_derived = replace(derived(), feature_contract_version="0.9")
    historical_normalized = replace(normalized(), feature_contract_version="0.9")
    value = result(
        derived_metrics=historical_derived,
        normalized_features=historical_normalized,
        data_contract_versions=historical_versions,
    )
    assert value.data_contract_versions.data_feature_contract_version == "0.9"
