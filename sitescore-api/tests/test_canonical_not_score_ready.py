from __future__ import annotations

from datetime import date, datetime, timezone
import os
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from shapely.geometry import Polygon
from sqlalchemy import select, text

import sitescore_api.execution as execution_module
from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
from sitescore_app import ApplicationScoringGateState, evaluate_application_scoring_gate
from sitescore_benchmarks import (
    CellResolutionPolicy,
    CellShape,
    CommercialEligibilityPolicy,
    CommercialEvidencePolicy,
    CommercialFrame,
    EqualAreaProjectionPolicy,
    FrameBoundaryMembershipPolicy,
    FrameState,
    LatticePolicy,
    ResolutionState,
    RoadParkingCompositeState,
    build_benchmark_distribution,
    build_benchmark_measurement_set,
    evaluate_road_parking_composite,
)
from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    GeographyType,
    PipelineStatus,
    ScoreEligibility,
    ScoringReadinessReason,
    ValidityState,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.demographics import AgeCohortPopulation, DemographicSnapshot
from sitescore_data.schemas.geography import GeographyRef, ResolvedLocation
from sitescore_data.schemas.pedestrian import IsochroneSnapshot
from sitescore_data.schemas.transit import TransitObservation, TransitServiceWindow, TransitSnapshot
from sitescore_spatial import (
    GeographyIdentity,
    GeometryCanonicalizationPolicy,
    build_boundary_geometry_artifact,
    build_crs_identity,
    build_geometry_engine_identity,
    build_geometry_source_identity,
    canonicalize_geometry,
)

from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel
from sitescore_api.execution import CanonicalAnalysisExecutor, ExecutionEvidence
from sitescore_api.ingress import build_analysis_ingress_command
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.models import AnalysisRequest
from sitescore_api.worker import AnalysisWorkerService

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
ADAPTER = TypeAdapter(AnalysisRequest)
DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")


def _available(value: float, unit: str, source_ref: str, method: str) -> MetricValue:
    return MetricValue(
        value=value,
        unit=unit,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=CalibrationState.CALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(source_ref,),
        method_version=method,
        reason_codes=(),
    )


def _empty_public_benchmark_frame() -> CommercialFrame:
    engine = build_geometry_engine_identity()
    crs = build_crs_identity("EPSG:3857")
    canon = GeometryCanonicalizationPolicy()
    geography = GeographyIdentity("BENCHMARK_AREA", "api-test-area", "boundary-def-2026")
    geometry = canonicalize_geometry(
        Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
        crs_identity=crs,
        policy=canon,
        engine=engine,
    )
    source = build_geometry_source_identity(
        provider="test-provider",
        dataset="benchmark-boundary",
        release="2026-08-17",
        vintage="2026",
        schema_version="1",
        source_crs_identity=crs,
        raw_content=b"api-canonical-empty-benchmark-frame",
    )
    boundary = build_boundary_geometry_artifact(
        geography_identity=geography,
        geometry_role="BENCHMARK_BOUNDARY",
        source_identity=source,
        canonical_geometry=geometry,
        parser_id="api-test-boundary-parser",
        parser_version="1",
        canonicalization_policy=canon,
        engine=engine,
        source_refs=("source:api-test-boundary",),
        generated_at=NOW,
        raw_artifact_ref="artifact:api-test-boundary",
    )
    projection = EqualAreaProjectionPolicy(
        "api-test-equal-area",
        "1.0",
        "UNRESOLVED",
        ResolutionState.UNRESOLVED,
    )
    resolution = CellResolutionPolicy(
        "api-test-cell-resolution",
        "1.0",
        ResolutionState.UNRESOLVED,
    )
    lattice = LatticePolicy(
        "api-test-lattice",
        "1.0",
        projection,
        resolution,
        CellShape.SQUARE,
        None,
        None,
        "AXIS_ALIGNED",
        "INTEGER_IJ",
        "1.0",
        canon,
        engine,
    )
    membership = FrameBoundaryMembershipPolicy(
        "api-test-membership",
        "1.0",
        ResolutionState.UNRESOLVED,
    )
    evidence_policy = CommercialEvidencePolicy(
        "api-test-commercial-evidence",
        "1.0",
        ("qualifying_place",),
        ("authoritative_noncommercial",),
    )
    eligibility = CommercialEligibilityPolicy(
        "api-test-commercial-eligibility",
        "1.0",
        evidence_policy,
    )
    return CommercialFrame(
        geography,
        boundary,
        lattice,
        membership,
        eligibility,
        (),
        FrameState.UNRESOLVED,
        ("boundary_membership_policy_unresolved", "lattice_policy_unresolved"),
        NOW,
    )


def _benchmark_distributions():
    frame = _empty_public_benchmark_frame()
    keys = (
        "walkable_population",
        "target_population_density",
        "competition_pressure",
        "walkable_reach_area_km2",
        "transit_service_departure_equivalents_per_hour",
        "household_income",
    )
    return {
        key: build_benchmark_distribution(
            build_benchmark_measurement_set(frame, (), metric_key=key)
        )
        for key in keys
    }


def _evidence() -> ExecutionEvidence:
    geography = GeographyRef(
        GeographyType.BLOCK_GROUP,
        "480010001001",
        "API Test BG",
        "US",
        "source:api-geography",
        "2025",
    )
    population = 1000
    demographics = DemographicSnapshot(
        geography,
        _available(population, "people", "source:api-pop", "api-pop/1"),
        (AgeCohortPopulation("age_18_24", 18, 25, 200, 0.2),),
        _available(80000, "usd_per_household", "source:api-income", "api-income/1"),
        ("source:api-income", "source:api-pop"),
        AvailabilityState.AVAILABLE,
        DataQualityState.FULL,
        NOW,
    )
    isochrone = IsochroneSnapshot(
        "api_isochrone",
        "api_walk_catchment",
        _available(1.5, "km2", "source:api-routing", "api-iso/1"),
        ("source:api-routing",),
        AvailabilityState.AVAILABLE,
        DataQualityState.FULL,
        "api-iso/1",
        NOW,
    )
    competition = CompetitionSnapshot(
        "api_competition",
        "api_competition_definition_v1",
        None,
        None,
        (),
        AvailabilityState.UNKNOWN,
        DataQualityState.MISSING,
        NOW,
    )
    window = TransitServiceWindow(
        "America/Chicago",
        ValidityState.VALID,
        date(2026, 1, 1),
        date(2026, 12, 31),
        (date(2026, 8, 17),),
        "typical-week-v1",
        "gtfs-calendar-v1",
    )
    observations = tuple(TransitObservation(hour, 2, 0.5, 2.5) for hour in range(168))
    transit = TransitSnapshot(
        "api_transit",
        (),
        window,
        observations,
        _available(2.5, "departure_equivalents_per_hour", "source:api-gtfs", "api-transit/1"),
        None,
        "api-transit-bundle-v1",
        ("source:api-gtfs",),
        AvailabilityState.AVAILABLE,
        DataQualityState.FULL,
        NOW,
    )
    location = ResolvedLocation(
        latitude=30.2672,
        longitude=-97.7431,
        formatted_address="123 Main St, Austin, TX",
        country_code="US",
        geography_refs=(geography,),
        source_refs=("source:api-geocoder",),
        resolution_method_version="api-geocoder/1",
        generated_at=NOW,
    )
    return ExecutionEvidence(
        resolved_location=location,
        demographics=demographics,
        isochrone=isochrone,
        competition=competition,
        transit=transit,
        benchmark_distributions=_benchmark_distributions(),
        source_metadata=(),
        geographic_level=GeographicLevel.BLOCK_GROUP,
        data_age_years=1,
        data_coverage={
            "demand": CoverageLevel.FULL,
            "competition": CoverageLevel.FULL,
            "accessibility": CoverageLevel.FULL,
            "economics": CoverageLevel.FULL,
        },
        input_qualities={
            "rent": InputQuality.USER,
            "price": InputQuality.USER,
            "capacity": InputQuality.USER,
            "schedule": InputQuality.USER,
        },
    )


class StaticEvidenceSource:
    def __init__(self, evidence: ExecutionEvidence) -> None:
        self.evidence = evidence

    def acquire(self, command, *, now):
        return self.evidence


class NoopDispatcher:
    def dispatch_analysis(self, analysis_id):
        return None


def test_real_frozen_public_chain_propagates_comb005_to_not_score_ready(monkeypatch, valid_payloads):
    road_parking = evaluate_road_parking_composite()
    assert road_parking.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert road_parking.score is None

    analyze_calls = 0

    def forbidden_core_analyze(_value):
        nonlocal analyze_calls
        analyze_calls += 1
        raise AssertionError("core analyze must not run for canonical NOT_SCORE_READY")

    monkeypatch.setattr(execution_module, "analyze_application_core_input", forbidden_core_analyze)
    model = ADAPTER.validate_python(valid_payloads["coffee"])
    command = build_analysis_ingress_command(model, request_id=uuid4(), analysis_id=uuid4())
    result = CanonicalAnalysisExecutor(StaticEvidenceSource(_evidence())).execute(command, now=NOW)

    assert result.completed is None
    assert result.not_score_ready is not None
    pipeline = result.not_score_ready.application_pipeline_result.pipeline_result
    assert pipeline.status is PipelineStatus.NOT_SCORE_READY
    assert pipeline.normalized_features is not None
    assert pipeline.normalized_features.road_parking_access_score.value is None
    assert pipeline.normalized_features.road_parking_composite_policy_version is None
    assert pipeline.scoring_readiness is not None
    assert pipeline.scoring_readiness.is_score_ready is False
    assert ScoringReadinessReason.ROAD_PARKING_COMPOSITE_UNAVAILABLE in pipeline.scoring_readiness.reason_codes
    assert evaluate_application_scoring_gate(pipeline).state is ApplicationScoringGateState.NOT_SCORE_READY
    assert analyze_calls == 0
    assert result.not_score_ready.readiness_projection["is_score_ready"] is False


@pytest.mark.skipif(not DATABASE_URL, reason="durable canonical terminal test requires real PostgreSQL")
def test_worker_persists_real_canonical_not_score_ready_without_scored_result(monkeypatch, valid_payloads):
    assert DATABASE_URL is not None
    database = Database(DATABASE_URL)
    with database.engine.begin() as conn:
        conn.execute(text("TRUNCATE dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))

    analyze_calls = 0

    def forbidden_core_analyze(_value):
        nonlocal analyze_calls
        analyze_calls += 1
        raise AssertionError("core analyze must not run for canonical NOT_SCORE_READY")

    monkeypatch.setattr(execution_module, "analyze_application_core_input", forbidden_core_analyze)
    executor = CanonicalAnalysisExecutor(StaticEvidenceSource(_evidence()))
    worker = AnalysisWorkerService(database, executor)
    backend = PostgresAnalysisLifecycleBackend(database, NoopDispatcher(), deadline_seconds=900)
    consumer_id = uuid4()
    with database.session() as session:
        with session.begin():
            session.add(
                ConsumerModel(
                    consumer_id=consumer_id,
                    name="canonical-worker-test",
                    active=True,
                    created_at=datetime.now(timezone.utc),
                )
            )

    model = ADAPTER.validate_python(valid_payloads["coffee"])
    command = build_analysis_ingress_command(model, request_id=uuid4(), analysis_id=uuid4())
    accepted = backend.submit(command, model, consumer_id=consumer_id, idempotency_key="canonical-not-ready")
    assert accepted.state == "queued"
    assert worker.execute_analysis(accepted.analysis_id) == "not_score_ready"

    with database.session() as session:
        row = session.get(AnalysisModel, accepted.analysis_id)
        assert row is not None
        assert row.state == "not_score_ready"
        assert row.result_body is None
        assert row.readiness_body is not None
        assert row.readiness_body["is_score_ready"] is False
        assert "road_parking_composite_unavailable" in row.readiness_body["readiness_reason_codes"]
    assert analyze_calls == 0
