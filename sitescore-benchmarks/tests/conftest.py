from datetime import datetime, timezone
import pytest
from shapely.geometry import Polygon
from sitescore_spatial import (
    GeographyIdentity,
    GeometryCanonicalizationPolicy,
    GeometryOperationPolicy,
    GeometryOperation,
    build_crs_identity,
    build_geometry_engine_identity,
    build_geometry_source_identity,
    canonicalize_geometry,
    build_boundary_geometry_artifact,
    intersect_geometries,
)
from sitescore_benchmarks import *
from sitescore_benchmarks.hashing import semantic_hash


@pytest.fixture(scope="session")
def engine():
    return build_geometry_engine_identity()


@pytest.fixture(scope="session")
def crs3857():
    return build_crs_identity("EPSG:3857")


@pytest.fixture(scope="session")
def crs3395():
    return build_crs_identity("EPSG:3395")


@pytest.fixture(scope="session")
def canon_policy():
    return GeometryCanonicalizationPolicy()


@pytest.fixture(scope="session")
def precision(canon_policy):
    return canon_policy.precision_policy


@pytest.fixture(scope="session")
def geography():
    return GeographyIdentity("BENCHMARK_AREA", "area-1", "boundary-def-2026")


@pytest.fixture(scope="session")
def geography2():
    return GeographyIdentity("BENCHMARK_AREA", "area-2", "boundary-def-2026")


def _boundary(geo, crs, engine, canon_policy, token, coords):
    cg = canonicalize_geometry(Polygon(coords), crs_identity=crs, policy=canon_policy, engine=engine)
    src = build_geometry_source_identity(
        provider="fixture",
        dataset="boundary",
        release="2026-08-01",
        vintage="2026",
        schema_version="1",
        source_crs_identity=crs,
        raw_content=token.encode(),
    )
    return build_boundary_geometry_artifact(
        geography_identity=geo,
        geometry_role="BENCHMARK_BOUNDARY",
        source_identity=src,
        canonical_geometry=cg,
        parser_id="fixture",
        parser_version="1",
        canonicalization_policy=canon_policy,
        engine=engine,
        source_refs=(f"src:{token}",),
        generated_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        raw_artifact_ref=f"/tmp/{token}",
    )


@pytest.fixture(scope="session")
def boundary_artifact(geography, crs3857, engine, canon_policy):
    return _boundary(geography, crs3857, engine, canon_policy, "boundary-a", [(-100,-100),(300,-100),(300,300),(-100,300),(-100,-100)])


@pytest.fixture(scope="session")
def boundary_artifact2(geography2, crs3857, engine, canon_policy):
    return _boundary(geography2, crs3857, engine, canon_policy, "boundary-b", [(500,500),(900,500),(900,900),(500,900),(500,500)])


@pytest.fixture
def full_cell(crs3857, engine, canon_policy):
    return canonicalize_geometry(Polygon([(0,0),(100,0),(100,100),(0,100),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)


@pytest.fixture
def full_cell2(crs3857, engine, canon_policy):
    return canonicalize_geometry(Polygon([(100,0),(200,0),(200,100),(100,100),(100,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)


@pytest.fixture
def projection_unresolved():
    return EqualAreaProjectionPolicy("equal-area-selection", "1.0", "UNRESOLVED_BY_CALIBRATION", ResolutionState.UNRESOLVED)


@pytest.fixture
def resolution_unresolved():
    return CellResolutionPolicy("cell-resolution", "1.0", ResolutionState.UNRESOLVED)


@pytest.fixture
def lattice_unresolved(projection_unresolved, resolution_unresolved, canon_policy, engine):
    return LatticePolicy(
        "square-lattice", "1.0", projection_unresolved, resolution_unresolved,
        CellShape.SQUARE, None, None, "AXIS_ALIGNED", "INTEGER_IJ", "1.0",
        canon_policy, engine,
    )


@pytest.fixture
def membership_unresolved():
    return FrameBoundaryMembershipPolicy("boundary-membership", "1.0", ResolutionState.UNRESOLVED)


@pytest.fixture
def evidence_policy():
    return CommercialEvidencePolicy("commercial-evidence", "1.0", ("qualifying_place",), ("authoritative_noncommercial",))


@pytest.fixture
def eligibility_policy(evidence_policy):
    return CommercialEligibilityPolicy("commercial-eligibility", "1.0", evidence_policy)


def candidate_cell_id(index="0:0"):
    return semantic_hash({"candidate_cell": index})


def make_bundle(ep, lattice_cell, items=()):
    ordered = tuple(sorted(items, key=lambda x: x.identity_id))
    return CommercialFrameEvidenceBundle(lattice_cell, ep, ordered)


def make_intersection_operation(a, boundary_artifact, canon_policy, engine):
    policy = GeometryOperationPolicy("diag-intersect", "1.0", GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty_result=True)
    return intersect_geometries(a, boundary_artifact.canonical_geometry, policy=policy, canonicalization_policy=canon_policy, engine=engine)


def unsafe_resolved_projection(crs):
    """White-box test fixture only: bypass FRAME-H001 constructor to exercise downstream contracts.
    This does NOT make the CRS an accepted equal-area production choice.
    """
    p = object.__new__(EqualAreaProjectionPolicy)
    object.__setattr__(p, "policy_id", "test-only-equal-area")
    object.__setattr__(p, "policy_version", "UNATTESTED_TEST_ONLY")
    object.__setattr__(p, "selection_algorithm", "TEST_ONLY_BYPASS")
    object.__setattr__(p, "state", ResolutionState.RESOLVED)
    object.__setattr__(p, "selected_crs", crs)
    return p


def unsafe_resolved_lattice(crs, canon_policy, engine, *, size=100.0, anchor=(0.0,0.0), version="test"):
    p = unsafe_resolved_projection(crs)
    r = CellResolutionPolicy("test-resolution", version, ResolutionState.RESOLVED, size, "m")
    return LatticePolicy("test-lattice", version, p, r, CellShape.SQUARE, anchor[0], anchor[1], "AXIS_ALIGNED", "INTEGER_IJ", "1.0", canon_policy, engine)


def make_area_result(geom, canon_policy, engine):
    from sitescore_spatial import area_of_projected_geometry, AreaPolicy, GeometryOperationPolicy, GeometryOperation
    ap = AreaPolicy()
    op = GeometryOperationPolicy("cell-area", "1.0", GeometryOperation.AREA, canon_policy.precision_policy)
    return area_of_projected_geometry(geom, area_policy=ap, operation_policy=op, engine=engine)


def make_test_lattice_cell(lattice, geom, i, j, canon_policy, engine):
    return LatticeCellArtifact(lattice, i, j, geom, make_area_result(geom, canon_policy, engine))

@pytest.fixture
def evidence_cell(full_cell, crs3857, canon_policy, engine):
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine)
    return make_test_lattice_cell(lattice, full_cell, 0, 0, canon_policy, engine)

@pytest.fixture
def classification_unresolved():
    return CommercialEvidenceClassificationPolicy("commercial-classification", "1.0", ResolutionState.UNRESOLVED)

@pytest.fixture
def applicability_unresolved():
    return EvidenceCellApplicabilityPolicy("cell-applicability", "1.0", ResolutionState.UNRESOLVED)

@pytest.fixture
def evidence_cell2(full_cell2, crs3857, canon_policy, engine):
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine)
    return make_test_lattice_cell(lattice, full_cell2, 1, 0, canon_policy, engine)
