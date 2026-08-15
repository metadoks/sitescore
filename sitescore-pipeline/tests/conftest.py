from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from shapely.geometry import Polygon

from sitescore_benchmarks import (
    CellResolutionPolicy,
    CellShape,
    CommercialEvidencePolicy,
    EqualAreaProjectionPolicy,
    LatticeCellArtifact,
    LatticePolicy,
    ResolutionState,
)
from sitescore_spatial import (
    GeographyIdentity,
    GeometryCanonicalizationPolicy,
    build_boundary_geometry_artifact,
    build_crs_identity,
    build_geometry_engine_identity,
    build_geometry_source_identity,
    canonicalize_geometry,
)


BENCHMARK_TESTS = Path(__file__).resolve().parents[2] / "sitescore-benchmarks" / "tests"
if str(BENCHMARK_TESTS) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_TESTS))


@pytest.fixture(scope="session")
def engine():
    return build_geometry_engine_identity()


@pytest.fixture(scope="session")
def crs3857():
    return build_crs_identity("EPSG:3857")


@pytest.fixture(scope="session")
def canon_policy():
    return GeometryCanonicalizationPolicy()


@pytest.fixture(scope="session")
def geography():
    return GeographyIdentity("BENCHMARK_AREA", "area-1", "boundary-def-2026")


def _boundary(geo, crs, engine, canon_policy):
    geometry = canonicalize_geometry(
        Polygon([(-100, -100), (300, -100), (300, 300), (-100, 300), (-100, -100)]),
        crs_identity=crs,
        policy=canon_policy,
        engine=engine,
    )
    source = build_geometry_source_identity(
        provider="fixture",
        dataset="boundary",
        release="2026-08-01",
        vintage="2026",
        schema_version="1",
        source_crs_identity=crs,
        raw_content=b"pipeline-boundary",
    )
    return build_boundary_geometry_artifact(
        geography_identity=geo,
        geometry_role="BENCHMARK_BOUNDARY",
        source_identity=source,
        canonical_geometry=geometry,
        parser_id="fixture",
        parser_version="1",
        canonicalization_policy=canon_policy,
        engine=engine,
        source_refs=("src:pipeline-boundary",),
        generated_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        raw_artifact_ref="/tmp/pipeline-boundary",
    )


@pytest.fixture(scope="session")
def boundary_artifact(geography, crs3857, engine, canon_policy):
    return _boundary(geography, crs3857, engine, canon_policy)


@pytest.fixture
def evidence_policy():
    return CommercialEvidencePolicy(
        "commercial-evidence",
        "1.0",
        ("qualifying_place",),
        ("authoritative_noncommercial",),
    )


def unsafe_resolved_projection(crs):
    value = object.__new__(EqualAreaProjectionPolicy)
    object.__setattr__(value, "policy_id", "test-only-equal-area")
    object.__setattr__(value, "policy_version", "UNATTESTED_TEST_ONLY")
    object.__setattr__(value, "selection_algorithm", "TEST_ONLY_BYPASS")
    object.__setattr__(value, "state", ResolutionState.RESOLVED)
    object.__setattr__(value, "selected_crs", crs)
    return value


def unsafe_resolved_lattice(
    crs, canon_policy, engine, *, size=100.0, anchor=(0.0, 0.0), version="test"
):
    projection = unsafe_resolved_projection(crs)
    resolution = CellResolutionPolicy(
        "test-resolution", version, ResolutionState.RESOLVED, size, "m"
    )
    return LatticePolicy(
        "test-lattice",
        version,
        projection,
        resolution,
        CellShape.SQUARE,
        anchor[0],
        anchor[1],
        "AXIS_ALIGNED",
        "INTEGER_IJ",
        "1.0",
        canon_policy,
        engine,
    )


def make_area_result(geom, canon_policy, engine):
    from sitescore_spatial import (
        AreaPolicy,
        GeometryOperation,
        GeometryOperationPolicy,
        area_of_projected_geometry,
    )

    return area_of_projected_geometry(
        geom,
        area_policy=AreaPolicy(),
        operation_policy=GeometryOperationPolicy(
            "cell-area",
            "1.0",
            GeometryOperation.AREA,
            canon_policy.precision_policy,
        ),
        engine=engine,
    )


def make_test_lattice_cell(lattice, geom, i, j, canon_policy, engine):
    return LatticeCellArtifact(
        lattice,
        i,
        j,
        geom,
        make_area_result(geom, canon_policy, engine),
    )
