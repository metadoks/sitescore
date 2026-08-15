from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import inspect
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    GeographyType,
    ScoreEligibility,
    ValidityState,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.demographics import AgeCohortPopulation, DemographicSnapshot
from sitescore_data.schemas.geography import GeographyRef
from sitescore_data.schemas.parking import ParkingSnapshot
from sitescore_data.schemas.pedestrian import IsochroneSnapshot
from sitescore_data.schemas.road import RoadAccessSnapshot, RoadOriginQuality
from sitescore_data.schemas.transit import TransitObservation, TransitServiceWindow, TransitSnapshot
from sitescore_metrics import (
    DEFINITIONS,
    POLICIES,
    FULL_BINARY64,
    DerivedMetricMeasurement,
    DerivationStrategy,
    MeasurementPrecisionPolicy,
    MeasurementSubject,
    MetricDefinition,
    MetricDerivationPolicy,
    MetricEvidence,
    MetricImplementationStatus,
    SubjectKind,
    measure_household_income,
    measure_parking_legal_curb_length,
    measure_parking_public_offstreet_capacity,
    measure_transit_service,
    measure_walkable_reach_area,
    unresolved_competition_pressure,
    unresolved_road_reachable_area,
)
from sitescore_spatial import canonicalize_geometry
from sitescore_benchmarks import *
from sitescore_benchmarks.hashing import semantic_hash
from conftest import make_test_lattice_cell, unsafe_resolved_lattice


NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def mv(
    value,
    unit,
    ref="src",
    method="m-v1",
    *,
    availability=AvailabilityState.AVAILABLE,
    quality=DataQualityState.FULL,
    calibration=CalibrationState.CALIBRATED,
):
    if availability is AvailabilityState.AVAILABLE:
        refs = (ref,)
        eligibility = ScoreEligibility.ELIGIBLE
    else:
        refs = ()
        eligibility = ScoreEligibility.INELIGIBLE
    return MetricValue(
        value, unit, availability, quality, eligibility, calibration,
        False, False, refs, method, (),
    )


def demo(n=1, *, generated_at=NOW):
    geography = GeographyRef(
        GeographyType.BLOCK_GROUP, f"36061000100{n}", f"BG{n}", "US", f"geo_src_{n}", "2025"
    )
    return DemographicSnapshot(
        geography,
        mv(400 + n, "people", f"acs-pop-{n}"),
        (AgeCohortPopulation("age_18_24", 18, 25, 100, 0.25),),
        mv(80000 + n, "usd_per_household", f"acs-income-{n}", "acs-income-v1"),
        (f"acs-{n}",), AvailabilityState.AVAILABLE, DataQualityState.FULL, generated_at,
    )


def iso(n=1, *, missing=False, generated_at=NOW):
    area = (
        MetricValue(
            None, "km2", AvailabilityState.MISSING, DataQualityState.MISSING,
            ScoreEligibility.INELIGIBLE, CalibrationState.UNCALIBRATED,
            False, False, (), "iso-area-v1", ("missing",),
        )
        if missing else mv(1.0 + n / 10.0, "km2", f"routing-{n}", "iso-area-v1")
    )
    return IsochroneSnapshot(
        f"iso_{n}", f"walk_{n}", area, (() if missing else (f"routing-{n}",)),
        (AvailabilityState.MISSING if missing else AvailabilityState.AVAILABLE),
        (DataQualityState.MISSING if missing else DataQualityState.FULL),
        "iso-v1", generated_at,
    )


def transit(n=1, *, bundle="bundle:abc"):
    window = TransitServiceWindow(
        "America/New_York", ValidityState.VALID, date(2026, 1, 1), date(2026, 12, 31),
        tuple(date(2026, 8, d) for d in range(3, 10)), "typical-week-v1", "gtfs-calendar-v1",
    )
    observations = tuple(TransitObservation(h, 2, 0.5, 2.5 + n / 100.0) for h in range(168))
    return TransitSnapshot(
        f"transit_{n}", (), window, observations,
        mv(2.5 + n / 100.0, "departure_equivalents_per_hour", f"gtfs-{n}", "transit-v1"),
        None, bundle, (f"gtfs-{n}",), AvailabilityState.AVAILABLE, DataQualityState.FULL, NOW,
    )


def parking(n=1):
    return ParkingSnapshot(
        f"parking_{n}", (), mv(1, "count", f"park-{n}"),
        mv(40 + n, "spaces", f"park-{n}", "parking-v1"),
        mv(0, "count", f"park-{n}"), mv(100.0 + n, "m", f"park-{n}", "curb-v1"),
        mv(0, "spaces", f"park-{n}"), False, (f"park-{n}",),
        AvailabilityState.AVAILABLE, DataQualityState.FULL, ScoreEligibility.ELIGIBLE, NOW,
    )


def competition(n=1, *, definition_id="measurement_def_1"):
    return CompetitionSnapshot(
        f"comp_{n}", definition_id, None, None, (),
        AvailabilityState.UNKNOWN, DataQualityState.MISSING, NOW,
    )


def road(n=1, *, profile="drive", version="1.0"):
    return RoadAccessSnapshot(
        f"road_{n}", f"origin_{n}", RoadOriginQuality.UNRESOLVED,
        profile, version, (), None, (), AvailabilityState.UNKNOWN, DataQualityState.MISSING, NOW,
    )


def _unsafe_member(cell, boundary_artifact, membership_policy):
    membership = object.__new__(FrameBoundaryMembership)
    object.__setattr__(membership, "full_cell_geometry", cell.full_cell_geometry)
    object.__setattr__(membership, "boundary_artifact", boundary_artifact)
    object.__setattr__(membership, "membership_policy", membership_policy)
    object.__setattr__(membership, "diagnostic_evidence", None)
    object.__setattr__(membership, "state", BoundaryMembershipState.MEMBER)
    object.__setattr__(membership, "reason_codes", ("test_only_member",))
    return membership


def _unsafe_resolved_item(cell, n=1):
    source = EvidenceSourceIdentity(
        "fixture", "commercial-evidence", f"2026-08-{n:02d}", "2026", "1",
        semantic_hash({"source": n, "cell": cell.lattice_cell_id}),
    )
    record = CommercialEvidenceRecord("place", source)
    classification_policy = object.__new__(CommercialEvidenceClassificationPolicy)
    object.__setattr__(classification_policy, "policy_id", "test-only-classification")
    object.__setattr__(classification_policy, "policy_version", "test")
    object.__setattr__(classification_policy, "state", ResolutionState.RESOLVED)
    object.__setattr__(classification_policy, "method", "TEST_ONLY_BYPASS")
    classification = object.__new__(CommercialEvidenceClassification)
    object.__setattr__(classification, "evidence_record", record)
    object.__setattr__(classification, "classification_policy", classification_policy)
    object.__setattr__(classification, "evidence_class", "qualifying_place")
    object.__setattr__(classification, "disposition", EvidenceDisposition.POSITIVE)
    object.__setattr__(classification, "reason_codes", ("test_only_resolved_classification",))
    applicability_policy = object.__new__(EvidenceCellApplicabilityPolicy)
    object.__setattr__(applicability_policy, "policy_id", "test-only-applicability")
    object.__setattr__(applicability_policy, "policy_version", "test")
    object.__setattr__(applicability_policy, "state", ResolutionState.RESOLVED)
    object.__setattr__(applicability_policy, "method", "TEST_ONLY_BYPASS")
    applicability = object.__new__(EvidenceCellApplicability)
    object.__setattr__(applicability, "classification", classification)
    object.__setattr__(applicability, "lattice_cell", cell)
    object.__setattr__(applicability, "applicability_policy", applicability_policy)
    object.__setattr__(applicability, "state", ApplicabilityState.APPLICABLE)
    object.__setattr__(applicability, "reason_codes", ("test_only_applicable",))
    return CommercialEvidenceItem(classification, applicability)


def make_frame(
    *, cell_count, crs3857, canon_policy, engine, boundary_artifact, geography,
    evidence_policy, eligibility_version="1.0", generated_at=NOW,
):
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine, version="cp344-test")
    membership_policy = FrameBoundaryMembershipPolicy(
        "test-membership", "1.0", ResolutionState.RESOLVED, "TEST_ONLY_MEMBER"
    )
    eligibility_policy = CommercialEligibilityPolicy(
        "commercial-eligibility", eligibility_version, evidence_policy
    )
    cells = []
    for i in range(cell_count):
        geom = canonicalize_geometry(
            Polygon([
                (100 * i, 0), (100 * (i + 1), 0), (100 * (i + 1), 100),
                (100 * i, 100), (100 * i, 0),
            ]),
            crs_identity=crs3857, policy=canon_policy, engine=engine,
        )
        lattice_cell = make_test_lattice_cell(lattice, geom, i, 0, canon_policy, engine)
        bundle = CommercialFrameEvidenceBundle(
            lattice_cell, evidence_policy, (_unsafe_resolved_item(lattice_cell, i + 1),)
        )
        eligibility = evaluate_commercial_eligibility(bundle, eligibility_policy)
        assert eligibility.state is EligibilityState.ELIGIBLE
        cells.append(CommercialFrameCell(
            lattice_cell, _unsafe_member(lattice_cell, boundary_artifact, membership_policy),
            bundle, eligibility,
        ))
    return CommercialFrame(
        geography, boundary_artifact, lattice, membership_policy, eligibility_policy,
        tuple(sorted(cells, key=lambda cell: cell.cell_id)), FrameState.STRUCTURAL_ONLY,
        ("production_membership_semantics_not_approved",), generated_at,
    )


@pytest.fixture
def frame3(crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy):
    return make_frame(
        cell_count=3, crs3857=crs3857, canon_policy=canon_policy, engine=engine,
        boundary_artifact=boundary_artifact, geography=geography, evidence_policy=evidence_policy,
    )


def income_attempt(frame, cell, n, *, precision=FULL_BINARY64, snapshot=None):
    snapshot = snapshot or demo(n)
    inputs = (MetricEvidence(snapshot, "demographic_snapshot"),)
    subject = adapt_benchmark_cell_subject(frame, cell, inputs=inputs)
    return build_benchmark_cell_measurement(
        frame, cell, measure_household_income(subject, snapshot, precision_policy=precision)
    )


def area_attempt(frame, cell, n, *, missing=False, precision=FULL_BINARY64, snapshot=None):
    snapshot = snapshot or iso(n, missing=missing)
    inputs = (MetricEvidence(snapshot, "isochrone_snapshot"),)
    subject = adapt_benchmark_cell_subject(frame, cell, inputs=inputs)
    return build_benchmark_cell_measurement(
        frame, cell, measure_walkable_reach_area(subject, snapshot, precision_policy=precision)
    )


def transit_attempt(frame, cell, n, *, bundle="bundle:abc"):
    snapshot = transit(n, bundle=bundle)
    subject = adapt_benchmark_cell_subject(
        frame, cell, inputs=(MetricEvidence(snapshot, "transit_snapshot"),)
    )
    measurement = measure_transit_service(
        subject, snapshot, expected_source_bundle_fingerprint=bundle
    )
    return build_benchmark_cell_measurement(frame, cell, measurement)


def parking_attempt(frame, cell, n, *, curb=False):
    snapshot = parking(n)
    subject = adapt_benchmark_cell_subject(
        frame, cell, inputs=(MetricEvidence(snapshot, "parking_snapshot"),)
    )
    measurement = (
        measure_parking_legal_curb_length(subject, snapshot)
        if curb else measure_parking_public_offstreet_capacity(subject, snapshot)
    )
    return build_benchmark_cell_measurement(frame, cell, measurement)


def competition_attempt(frame, cell, n, *, definition_id="measurement_def_1"):
    snapshot = competition(n, definition_id=definition_id)
    subject = adapt_benchmark_cell_subject(
        frame, cell, inputs=(MetricEvidence(snapshot, "competition_snapshot"),)
    )
    measurement = unresolved_competition_pressure(
        subject, snapshot, expected_measurement_definition_id=definition_id
    )
    return build_benchmark_cell_measurement(frame, cell, measurement)


def road_attempt(frame, cell, n, *, profile="drive", version="1.0"):
    snapshot = road(n, profile=profile, version=version)
    subject = adapt_benchmark_cell_subject(
        frame, cell, inputs=(MetricEvidence(snapshot, "road_snapshot"),)
    )
    return build_benchmark_cell_measurement(
        frame, cell, unresolved_road_reachable_area(subject, snapshot)
    )


def complete_attempts(frame, builder):
    return tuple(builder(frame, cell, i + 1) for i, cell in enumerate(frame.cells))
