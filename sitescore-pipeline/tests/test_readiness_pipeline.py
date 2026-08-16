from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
import inspect
import sys

import pytest

import sitescore_pipeline.integration as integration
from sitescore_benchmarks import (
    build_benchmark_cell_measurement,
    build_benchmark_distribution,
    build_benchmark_measurement_set,
    adapt_benchmark_cell_subject,
)
from sitescore_benchmarks.composite import evaluate_road_parking_composite
from sitescore_benchmarks.normalization import (
    build_age_target_concentration_fallback,
    normalize_feature,
)
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
from sitescore_data.validators.readiness import ScoringReadinessValidator
from sitescore_metrics import (
    MeasurementSubject,
    MetricEvidence,
    SubjectKind,
    measure_household_income,
    measure_transit_service,
    measure_walkable_reach_area,
    unresolved_competition_pressure,
    unresolved_target_population_density,
    unresolved_walkable_population,
)


BENCHMARK_TESTS = Path(__file__).resolve().parents[2] / "sitescore-benchmarks" / "tests"
if str(BENCHMARK_TESTS) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_TESTS))

from cp344_helpers import (  # noqa: E402
    area_attempt,
    competition,
    competition_attempt,
    complete_attempts,
    demo,
    income_attempt,
    iso,
    make_frame,
    transit,
    transit_attempt,
)


T0 = datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc)
SOURCE = "test.source"
GEO_SOURCE = "test.geo"


def _site_subject(*scope_refs: str) -> MeasurementSubject:
    return MeasurementSubject(
        SubjectKind.SITE,
        "sitescore_metrics.site",
        "1.0",
        (("site_id", "site_1"),),
        tuple(sorted({"site:site_1", *scope_refs})),
    )


def _walkable_attempt(frame, cell, n):
    demographic = demo(n)
    catchment = iso(n)
    inputs = (
        MetricEvidence(demographic, "demographic_snapshot"),
        MetricEvidence(catchment, "isochrone_snapshot"),
    )
    subject = adapt_benchmark_cell_subject(frame, cell, inputs=inputs)
    return build_benchmark_cell_measurement(
        frame,
        cell,
        unresolved_walkable_population(subject, demographic, catchment),
    )


def _target_density_attempt(frame, cell, n):
    demographic = demo(n)
    inputs = (MetricEvidence(demographic, "demographic_snapshot"),)
    subject = adapt_benchmark_cell_subject(frame, cell, inputs=inputs)
    return build_benchmark_cell_measurement(
        frame,
        cell,
        unresolved_target_population_density(subject, demographic),
    )


def _distribution(frame, metric_key, attempt_builder):
    attempts = tuple(
        attempt_builder(frame, cell, i + 1)
        for i, cell in enumerate(frame.cells)
    )
    return build_benchmark_distribution(
        build_benchmark_measurement_set(
            frame,
            attempts,
            metric_key=metric_key,
        )
    )


def _actual_direct_results(frame):
    demographic = demo(2)
    catchment = iso(2)
    transit_snapshot = transit(2, bundle="bundle:abc")
    competition_snapshot = competition(2, definition_id="measurement_def_1")

    walkable_site = unresolved_walkable_population(
        _site_subject(
            f"geography:{demographic.geography_ref.geography_id}",
            f"catchment:{catchment.catchment_ref}",
        ),
        demographic,
        catchment,
    )
    density_site = unresolved_target_population_density(
        _site_subject(f"geography:{demographic.geography_ref.geography_id}"),
        demographic,
    )
    income_site = measure_household_income(
        _site_subject(f"geography:{demographic.geography_ref.geography_id}"),
        demographic,
    )
    reach_site = measure_walkable_reach_area(
        _site_subject(f"catchment:{catchment.catchment_ref}"),
        catchment,
    )
    transit_site = measure_transit_service(
        _site_subject(f"transit:{transit_snapshot.snapshot_id}"),
        transit_snapshot,
        expected_source_bundle_fingerprint="bundle:abc",
    )
    competition_site = unresolved_competition_pressure(
        _site_subject(f"competition:{competition_snapshot.snapshot_id}"),
        competition_snapshot,
        expected_measurement_definition_id="measurement_def_1",
    )

    distributions = {
        "walkable_population": _distribution(
            frame, "walkable_population", _walkable_attempt
        ),
        "target_population_density": _distribution(
            frame, "target_population_density", _target_density_attempt
        ),
        "household_income": build_benchmark_distribution(
            build_benchmark_measurement_set(
                frame,
                complete_attempts(frame, income_attempt),
                metric_key="household_income",
            )
        ),
        "walkable_reach_area_km2": build_benchmark_distribution(
            build_benchmark_measurement_set(
                frame,
                complete_attempts(frame, area_attempt),
                metric_key="walkable_reach_area_km2",
            )
        ),
        "transit_service_departure_equivalents_per_hour": build_benchmark_distribution(
            build_benchmark_measurement_set(
                frame,
                complete_attempts(frame, transit_attempt),
                metric_key="transit_service_departure_equivalents_per_hour",
            )
        ),
        "competition_pressure": build_benchmark_distribution(
            build_benchmark_measurement_set(
                frame,
                complete_attempts(frame, competition_attempt),
                metric_key="competition_pressure",
            )
        ),
    }
    measurements = {
        "walkable_population": walkable_site,
        "target_population_density": density_site,
        "household_income": income_site,
        "walkable_reach_area_km2": reach_site,
        "transit_service_departure_equivalents_per_hour": transit_site,
        "competition_pressure": competition_site,
    }
    return tuple(
        normalize_feature(measurements[key], distributions[key])
        for key in (
            "walkable_population",
            "target_population_density",
            "competition_pressure",
            "walkable_reach_area_km2",
            "transit_service_departure_equivalents_per_hour",
            "household_income",
        )
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
def canonical_assembly(frame2):
    return integration.assemble_normalized_location_features(
        direct_results=_actual_direct_results(frame2),
        age_fallback=build_age_target_concentration_fallback(),
        road_parking_result=evaluate_road_parking_composite(),
        generated_at=T0,
    )


@pytest.fixture
def canonical_readiness(canonical_assembly):
    return integration.derive_scoring_readiness(
        canonical_assembly,
        evaluated_at=T0,
    )


def _unknown_real(unit: str, reason: str = "unresolved") -> MetricValue:
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


def _coherent_derived(assembly) -> DerivedLocationMetrics:
    by_key = {
        result.site_measurement.definition.metric_key:
            result.site_measurement.metric_value
        for result in assembly.direct_results
    }
    values = {
        "walkable_population": by_key["walkable_population"],
        "target_population_density": by_key["target_population_density"],
        "household_income": by_key["household_income"],
        "household_income_ratio": _unknown_real("ratio", "ratio_unresolved"),
        "competition_pressure": by_key["competition_pressure"],
        "walkable_reach_area_km2": by_key["walkable_reach_area_km2"],
        "transit_service_departure_equivalents_per_hour": by_key[
            "transit_service_departure_equivalents_per_hour"
        ],
        "road_reachable_area_km2": _unknown_real("km2", "road_unresolved"),
        "parking_public_offstreet_capacity": _unknown_real(
            "spaces", "parking_unresolved"
        ),
        "parking_legal_curb_length_m": _unknown_real(
            "m", "curb_unresolved"
        ),
    }
    source_refs = tuple(sorted({
        ref
        for metric in values.values()
        for ref in metric.source_refs
    }))
    return DerivedLocationMetrics(
        **values,
        demographic_snapshot_ref=None,
        competition_snapshot_ref=None,
        road_snapshot_ref=None,
        parking_snapshot_ref=None,
        source_refs=source_refs,
        feature_contract_version=DATA_FEATURE_CONTRACT_VERSION,
        generated_at=T0,
    )


def _all_unknown_derived() -> DerivedLocationMetrics:
    return DerivedLocationMetrics(
        walkable_population=_unknown_real("people"),
        target_population_density=_unknown_real("people_per_km2"),
        household_income=_unknown_real("usd_per_household"),
        household_income_ratio=_unknown_real("ratio"),
        competition_pressure=_unknown_real("competition_pressure"),
        walkable_reach_area_km2=_unknown_real("km2"),
        transit_service_departure_equivalents_per_hour=_unknown_real(
            "departure_equivalents_per_hour"
        ),
        road_reachable_area_km2=_unknown_real("km2"),
        parking_public_offstreet_capacity=_unknown_real("spaces"),
        parking_legal_curb_length_m=_unknown_real("m"),
        demographic_snapshot_ref=None,
        competition_snapshot_ref=None,
        road_snapshot_ref=None,
        parking_snapshot_ref=None,
        source_refs=(),
        feature_contract_version=DATA_FEATURE_CONTRACT_VERSION,
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


def _available_score(value: float, *, age=False) -> MetricValue:
    return MetricValue(
        value=value,
        unit="score_0_100",
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=(
            CalibrationState.UNCALIBRATED if age else CalibrationState.CALIBRATED
        ),
        is_estimate=False,
        is_proxy=age,
        source_refs=(SOURCE,),
        method_version="test/1.0",
        reason_codes=(("age_affinity_not_calibrated",) if age else ()),
    )


def _controlled_ready_features() -> NormalizedLocationFeatures:
    geography = GeographyRef(
        GeographyType.CUSTOM,
        "test-geography",
        "Test Geography",
        "US",
        GEO_SOURCE,
        "1.0",
    )
    competition_ref = BenchmarkReference(
        "competition-benchmark",
        "artifact:competition",
        "test-frame",
        "1.0",
        BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES,
        geography,
        (GEO_SOURCE,),
    )
    transit_ref = BenchmarkReference(
        "transit-benchmark",
        "artifact:transit",
        "test-frame",
        "1.0",
        BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES,
        geography,
        (GEO_SOURCE,),
    )
    return NormalizedLocationFeatures(
        walkable_population_score=_available_score(61),
        target_population_density_score=_available_score(62),
        age_target_concentration_score=_available_score(50, age=True),
        competition_opportunity_score=_available_score(63),
        walkable_reach_area_score=_available_score(64),
        transit_access_score=_available_score(65),
        road_parking_access_score=_available_score(66),
        household_income_score=_available_score(67),
        competition_benchmark_ref=competition_ref,
        competition_measurement_definition_id="competition-definition-v1",
        competition_normalization_policy_version="1.0",
        transit_benchmark_ref=transit_ref,
        transit_source_bundle_fingerprint="transit-bundle-v1",
        transit_normalization_policy_version="1.0",
        road_parking_composite_policy_version="1.0",
        source_refs=(GEO_SOURCE, SOURCE),
        feature_contract_version=DATA_FEATURE_CONTRACT_VERSION,
        generated_at=T0,
    )


def _controlled_policies():
    values = []
    for name in integration.NORMALIZED_FEATURE_NAMES:
        fallback_id = "age_neutral_fallback" if name == "age_target_concentration_score" else None
        fallback_version = "1.0" if fallback_id else None
        values.append(FeatureReadinessPolicy(
            name,
            True,
            "1.0",
            "1.0",
            fallback_id,
            fallback_version,
        ))
    return tuple(values)


def test_current_canonical_assembly_is_not_score_ready(canonical_readiness):
    assert canonical_readiness.result.is_score_ready is False
    assert ScoringReadinessReason.ROAD_PARKING_COMPOSITE_UNAVAILABLE in (
        canonical_readiness.result.reason_codes
    )


def test_age_exception_remains_exact_in_canonical_assembly(canonical_assembly):
    metric = canonical_assembly.features.age_target_concentration_score
    assert metric.value == 50
    assert metric.calibration_state is CalibrationState.UNCALIBRATED
    assert metric.is_proxy is True
    assert metric.reason_codes == ("age_affinity_not_calibrated",)


def test_no_missing_direct_feature_is_neutralized(canonical_assembly):
    assert canonical_assembly.features.walkable_population_score.value is None
    assert canonical_assembly.features.target_population_density_score.value is None
    assert canonical_assembly.features.competition_opportunity_score.value is None


def test_readiness_fingerprint_excludes_evaluated_timestamp(canonical_assembly):
    a = integration.derive_scoring_readiness(canonical_assembly, evaluated_at=T0)
    b = integration.derive_scoring_readiness(
        canonical_assembly, evaluated_at=T0 + timedelta(days=1)
    )
    assert a.result.evaluated_at != b.result.evaluated_at
    assert a.result.readiness_fingerprint == b.result.readiness_fingerprint


def test_h001_direct_assembly_constructor_is_forbidden():
    with pytest.raises(TypeError, match="factory-owned"):
        integration.NormalizedFeatureAssembly()


def test_h001_importable_hash_cannot_register_forged_assembly(canonical_assembly):
    forged = object.__new__(integration.NormalizedFeatureAssembly)
    for name in (
        "features",
        "direct_results",
        "feature_policies",
        "compatibility",
        "approved_fallback_policies",
        "artifact_identities",
        "assembly_id",
    ):
        object.__setattr__(forged, name, getattr(canonical_assembly, name))
    reproduced = integration._compute_assembly_id(
        forged.features,
        forged.direct_results,
        forged.feature_policies,
        forged.compatibility,
        forged.approved_fallback_policies,
        forged.artifact_identities,
    )
    assert reproduced == forged.assembly_id
    with pytest.raises(TypeError, match="exact object returned"):
        integration.derive_scoring_readiness(forged, evaluated_at=T0)


def test_h001_old_module_level_token_authority_no_longer_exists():
    assert not hasattr(integration, "_ASSEMBLY_TOKEN")
    assert not hasattr(integration, "_READINESS_TOKEN")
    assert not hasattr(integration, "_assembly_identity")
    assert not hasattr(integration, "_install_canonical_factories")


def test_h001_direct_readiness_constructor_is_forbidden():
    with pytest.raises(TypeError, match="factory-owned"):
        integration.ReadinessEvaluation()


def test_h001_detached_readiness_result_cannot_reach_terminal(canonical_readiness):
    forged = object.__new__(integration.ReadinessEvaluation)
    object.__setattr__(forged, "assembly", canonical_readiness.assembly)
    object.__setattr__(forged, "result", canonical_readiness.result)
    with pytest.raises(TypeError, match="exact object returned"):
        integration.build_real_data_pipeline_result(
            readiness=forged,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=_coherent_derived(canonical_readiness.assembly),
            source_metadata=(),
            generated_at=T0,
        )


def test_h001_production_api_has_no_detached_readiness_authority_parameters():
    params = inspect.signature(integration.derive_scoring_readiness).parameters
    assert tuple(params) == ("assembly", "evaluated_at")
    for forbidden in (
        "is_score_ready",
        "readiness_fingerprint",
        "reason_codes",
        "feature_states",
    ):
        assert forbidden not in params


def test_controlled_test_local_validator_can_model_score_ready_without_pipeline_authority():
    result = ScoringReadinessValidator(validator_version="test-validator/1.0").validate(
        features=_controlled_ready_features(),
        feature_policies=_controlled_policies(),
        compatibility=ReadinessCompatibilityInput(
            "competition-definition-v1",
            "transit-bundle-v1",
        ),
        approved_fallback_policies=(ApprovedFallbackPolicyRef(
            "age_target_concentration_score",
            "age_neutral_fallback",
            "1.0",
        ),),
        evaluated_at=T0,
        readiness_fingerprint="test-local-ready-fingerprint",
    )
    assert result.is_score_ready is True
    assert not isinstance(result, integration.ReadinessEvaluation)


def test_h002_semantically_coherent_overlapping_real_metrics_are_accepted(
    canonical_readiness,
):
    result = integration.build_real_data_pipeline_result(
        readiness=canonical_readiness,
        sector_key=SectorKey("coffee"),
        resolved_location=_location(),
        derived_metrics=_coherent_derived(canonical_readiness.assembly),
        source_metadata=(),
        generated_at=T0,
    )
    assert result.status is PipelineStatus.NOT_SCORE_READY
    assert result.reason_codes == (PipelineReason.SCORING_NOT_READY,)


def test_h002_household_income_value_mismatch_is_rejected(canonical_readiness):
    derived = _coherent_derived(canonical_readiness.assembly)
    wrong = replace(
        derived.household_income,
        value=float(derived.household_income.value) + 1.0,
    )
    derived = replace(derived, household_income=wrong)
    with pytest.raises(ValueError, match="household_income"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=derived,
            source_metadata=(),
            generated_at=T0,
        )


def test_h002_household_income_method_mismatch_is_rejected(canonical_readiness):
    derived = _coherent_derived(canonical_readiness.assembly)
    wrong = replace(derived.household_income, method_version="different-method")
    derived = replace(derived, household_income=wrong)
    with pytest.raises(ValueError, match="household_income"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=derived,
            source_metadata=(),
            generated_at=T0,
        )


def test_h002_transit_source_lineage_mismatch_is_rejected(canonical_readiness):
    derived = _coherent_derived(canonical_readiness.assembly)
    wrong = replace(
        derived.transit_service_departure_equivalents_per_hour,
        source_refs=("different-transit-source",),
    )
    derived = replace(
        derived,
        transit_service_departure_equivalents_per_hour=wrong,
        source_refs=tuple(sorted({
            ref
            for name in (
                "walkable_population",
                "target_population_density",
                "household_income",
                "household_income_ratio",
                "competition_pressure",
                "walkable_reach_area_km2",
                "transit_service_departure_equivalents_per_hour",
                "road_reachable_area_km2",
                "parking_public_offstreet_capacity",
                "parking_legal_curb_length_m",
            )
            for ref in getattr(derived, name).source_refs
        } | {"different-transit-source"})),
    )
    with pytest.raises(ValueError, match="transit_service_departure"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=derived,
            source_metadata=(),
            generated_at=T0,
        )


def test_h002_walkable_reach_method_mismatch_is_rejected(canonical_readiness):
    derived = _coherent_derived(canonical_readiness.assembly)
    wrong = replace(
        derived.walkable_reach_area_km2,
        method_version="different-reach-method",
    )
    derived = replace(derived, walkable_reach_area_km2=wrong)
    with pytest.raises(ValueError, match="walkable_reach_area_km2"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=derived,
            source_metadata=(),
            generated_at=T0,
        )


def test_h002_all_unknown_overlapping_placeholder_surface_is_rejected(
    canonical_readiness,
):
    with pytest.raises(ValueError, match="real-unit lineage mismatch"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=_all_unknown_derived(),
            source_metadata=(),
            generated_at=T0,
        )


def test_pipeline_error_remains_distinct_from_ordinary_unready():
    result = integration.build_pipeline_error_result(
        failure=integration.PipelineStageFailure(
            "provider_stage", "provider_failure"
        ),
        sector_key=SectorKey("coffee"),
        source_metadata=(),
        generated_at=T0,
        resolved_location=_location(),
    )
    assert result.status is PipelineStatus.PIPELINE_ERROR
    assert result.scoring_readiness is None
    assert result.reason_codes == (PipelineReason.PIPELINE_STAGE_ERROR,)


def test_terminal_factory_has_no_caller_status_authority():
    params = inspect.signature(
        integration.build_real_data_pipeline_result
    ).parameters
    for forbidden in ("status", "reason_codes", "is_score_ready"):
        assert forbidden not in params


def test_canonical_assembly_rejects_detached_metric_surface():
    params = inspect.signature(
        integration.assemble_normalized_location_features
    ).parameters
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



def _copy_factory_owned_assembly(source):
    copied = object.__new__(integration.NormalizedFeatureAssembly)
    for name in (
        "features",
        "direct_results",
        "feature_policies",
        "compatibility",
        "approved_fallback_policies",
        "artifact_identities",
        "assembly_id",
    ):
        object.__setattr__(copied, name, getattr(source, name))
    return copied


@pytest.mark.parametrize(
    "field_name",
    (
        "features",
        "direct_results",
        "feature_policies",
        "compatibility",
        "approved_fallback_policies",
        "artifact_identities",
        "assembly_id",
    ),
)
def test_pipe_auth_h001_registered_assembly_field_replacement_is_rejected(
    canonical_assembly,
    field_name,
):
    replacements = {
        "features": replace(canonical_assembly.features),
        "direct_results": tuple(list(canonical_assembly.direct_results)),
        "feature_policies": tuple(list(canonical_assembly.feature_policies)),
        "compatibility": replace(canonical_assembly.compatibility),
        "approved_fallback_policies": tuple(
            list(canonical_assembly.approved_fallback_policies)
        ),
        "artifact_identities": tuple(list(canonical_assembly.artifact_identities)),
        "assembly_id": canonical_assembly.assembly_id + "0",
    }
    object.__setattr__(canonical_assembly, field_name, replacements[field_name])
    with pytest.raises(ValueError, match="assembly integrity violation"):
        integration.derive_scoring_readiness(canonical_assembly, evaluated_at=T0)


def test_pipe_auth_h001_readiness_assembly_replacement_is_rejected(
    canonical_readiness,
):
    forged = _copy_factory_owned_assembly(canonical_readiness.assembly)
    object.__setattr__(canonical_readiness, "assembly", forged)
    with pytest.raises(ValueError, match="readiness evaluation integrity violation"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=_coherent_derived(forged),
            source_metadata=(),
            generated_at=T0,
        )


def test_pipe_auth_h001_readiness_result_replacement_is_rejected(
    canonical_readiness,
):
    object.__setattr__(
        canonical_readiness,
        "result",
        replace(canonical_readiness.result),
    )
    with pytest.raises(ValueError, match="readiness evaluation integrity violation"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=_coherent_derived(canonical_readiness.assembly),
            source_metadata=(),
            generated_at=T0,
        )


def test_pipe_auth_h001_nested_readiness_score_ready_mutation_is_rejected(
    canonical_readiness,
):
    assert canonical_readiness.result.is_score_ready is False
    object.__setattr__(canonical_readiness.result, "is_score_ready", True)
    with pytest.raises(ValueError, match="readiness evaluation integrity violation"):
        integration.build_real_data_pipeline_result(
            readiness=canonical_readiness,
            sector_key=SectorKey("coffee"),
            resolved_location=_location(),
            derived_metrics=_coherent_derived(canonical_readiness.assembly),
            source_metadata=(),
            generated_at=T0,
        )


def test_pipe_auth_h001_nested_forged_road_parking_score_is_rejected(
    canonical_assembly,
):
    original = canonical_assembly.features.road_parking_access_score
    assert original.value is None
    forged_metric = replace(
        original,
        value=66.0,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=CalibrationState.CALIBRATED,
        source_refs=(SOURCE,),
        method_version="forged-comb005/1.0",
        reason_codes=(),
    )
    object.__setattr__(
        canonical_assembly.features,
        "road_parking_access_score",
        forged_metric,
    )
    with pytest.raises(ValueError, match="assembly integrity violation"):
        integration.derive_scoring_readiness(canonical_assembly, evaluated_at=T0)


def test_pipe_auth_h001_unmodified_canonical_path_preserves_not_score_ready(
    canonical_readiness,
):
    terminal = integration.build_real_data_pipeline_result(
        readiness=canonical_readiness,
        sector_key=SectorKey("coffee"),
        resolved_location=_location(),
        derived_metrics=_coherent_derived(canonical_readiness.assembly),
        source_metadata=(),
        generated_at=T0,
    )
    assert terminal.status is PipelineStatus.NOT_SCORE_READY
    assert terminal.normalized_features is canonical_readiness.assembly.features
    assert terminal.scoring_readiness is canonical_readiness.result
    assert terminal.normalized_features.road_parking_access_score.value is None
