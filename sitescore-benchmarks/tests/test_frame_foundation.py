from datetime import datetime, timezone
import inspect
import pytest
from sitescore_benchmarks import *
from sitescore_benchmarks.hashing import semantic_hash
from conftest import make_bundle, make_intersection_operation


def src(n):
    return EvidenceSourceIdentity("generic-provider", "commercial-evidence", f"2026-08-{n:02d}", "2026", "1", semantic_hash({"source": n}))


def raw(n=1, evidence_type="place", attrs=()):
    return CommercialEvidenceRecord(evidence_type, src(n), attrs)


def unresolved_item(cell, classification_policy, applicability_policy, n=1, evidence_type="place"):
    rec = raw(n, evidence_type)
    cls = classify_commercial_evidence(rec, classification_policy)
    app = evaluate_evidence_cell_applicability(cls, cell, applicability_policy)
    return CommercialEvidenceItem(cls, app)


def _unsafe_resolved_classification(rec, evidence_class, disposition, *, version="test"):
    p = object.__new__(CommercialEvidenceClassificationPolicy)
    object.__setattr__(p, "policy_id", "test-only-classification")
    object.__setattr__(p, "policy_version", version)
    object.__setattr__(p, "state", ResolutionState.RESOLVED)
    object.__setattr__(p, "method", "TEST_ONLY_BYPASS")
    c = object.__new__(CommercialEvidenceClassification)
    object.__setattr__(c, "evidence_record", rec)
    object.__setattr__(c, "classification_policy", p)
    object.__setattr__(c, "evidence_class", evidence_class)
    object.__setattr__(c, "disposition", disposition)
    object.__setattr__(c, "reason_codes", ("test_only_resolved_classification",))
    return c


def _unsafe_applicable(cls, cell, *, version="test"):
    p = object.__new__(EvidenceCellApplicabilityPolicy)
    object.__setattr__(p, "policy_id", "test-only-applicability")
    object.__setattr__(p, "policy_version", version)
    object.__setattr__(p, "state", ResolutionState.RESOLVED)
    object.__setattr__(p, "method", "TEST_ONLY_BYPASS")
    a = object.__new__(EvidenceCellApplicability)
    object.__setattr__(a, "classification", cls)
    object.__setattr__(a, "lattice_cell", cell)
    object.__setattr__(a, "applicability_policy", p)
    object.__setattr__(a, "state", ApplicabilityState.APPLICABLE)
    object.__setattr__(a, "reason_codes", ("test_only_applicable",))
    return a


def resolved_test_item(cell, evidence_class, disposition, n=1, *, cver="test", aver="test"):
    cls = _unsafe_resolved_classification(raw(n), evidence_class, disposition, version=cver)
    return CommercialEvidenceItem(cls, _unsafe_applicable(cls, cell, version=aver))


# Commercial evidence / eligibility invariants after FRAME-H004/H005

def test_no_evidence_is_unknown(evidence_policy, eligibility_policy, evidence_cell):
    b = make_bundle(evidence_policy, evidence_cell)
    r = evaluate_commercial_eligibility(b, eligibility_policy)
    assert r.state is EligibilityState.UNKNOWN
    assert r.reason_codes == ("insufficient_commercial_evidence",)


def test_source_record_without_classification_or_applicability_is_unknown(evidence_policy, eligibility_policy, evidence_cell, classification_unresolved, applicability_unresolved):
    item = unresolved_item(evidence_cell, classification_unresolved, applicability_unresolved)
    b = make_bundle(evidence_policy, evidence_cell, (item,))
    assert evaluate_commercial_eligibility(b, eligibility_policy).state is EligibilityState.UNKNOWN


def test_resolved_positive_and_applicable_is_eligible_whitebox(evidence_policy, eligibility_policy, evidence_cell):
    item = resolved_test_item(evidence_cell, "qualifying_place", EvidenceDisposition.POSITIVE)
    b = make_bundle(evidence_policy, evidence_cell, (item,))
    assert evaluate_commercial_eligibility(b, eligibility_policy).state is EligibilityState.ELIGIBLE


def test_resolved_exclusion_and_applicable_is_ineligible_whitebox(evidence_policy, eligibility_policy, evidence_cell):
    item = resolved_test_item(evidence_cell, "authoritative_noncommercial", EvidenceDisposition.EXPLICIT_EXCLUSION, 2)
    b = make_bundle(evidence_policy, evidence_cell, (item,))
    assert evaluate_commercial_eligibility(b, eligibility_policy).state is EligibilityState.INELIGIBLE


def test_conflict_is_unknown_whitebox(evidence_policy, eligibility_policy, evidence_cell):
    a = resolved_test_item(evidence_cell, "qualifying_place", EvidenceDisposition.POSITIVE, 1)
    b = resolved_test_item(evidence_cell, "authoritative_noncommercial", EvidenceDisposition.EXPLICIT_EXCLUSION, 2)
    bundle = make_bundle(evidence_policy, evidence_cell, (a, b))
    assert evaluate_commercial_eligibility(bundle, eligibility_policy).state is EligibilityState.UNKNOWN


def test_eligibility_self_assertion_rejected(evidence_policy, eligibility_policy, evidence_cell):
    b = make_bundle(evidence_policy, evidence_cell)
    with pytest.raises(ValueError):
        CommercialEligibilityResult(b, eligibility_policy, EligibilityState.ELIGIBLE, ())


def test_ineligible_from_absence_self_assertion_rejected(evidence_policy, eligibility_policy, evidence_cell):
    b = make_bundle(evidence_policy, evidence_cell)
    with pytest.raises(ValueError):
        CommercialEligibilityResult(b, eligibility_policy, EligibilityState.INELIGIBLE, ("authoritative_exclusion_evidence",))


def test_evidence_bundle_identity_order_independent(evidence_policy, evidence_cell):
    a = resolved_test_item(evidence_cell, "qualifying_place", EvidenceDisposition.POSITIVE, 1)
    b = resolved_test_item(evidence_cell, "qualifying_place", EvidenceDisposition.POSITIVE, 4)
    x = make_bundle(evidence_policy, evidence_cell, (a, b))
    y = make_bundle(evidence_policy, evidence_cell, (b, a))
    assert x.bundle_id == y.bundle_id


def test_evidence_source_locator_is_nonsemantic(evidence_cell, classification_unresolved, applicability_unresolved):
    s = src(5)
    r1 = CommercialEvidenceRecord("place", s, (("class", "retail"),), "/tmp/a")
    r2 = CommercialEvidenceRecord("place", s, (("class", "retail"),), "/different/path")
    c1 = classify_commercial_evidence(r1, classification_unresolved)
    c2 = classify_commercial_evidence(r2, classification_unresolved)
    assert c1.identity_id == c2.identity_id


def test_mutable_evidence_release_rejected():
    with pytest.raises(ValueError):
        EvidenceSourceIdentity("p", "d", "latest", "2026", "1", semantic_hash({"x": 1}))

# FRAME-H001: no false equal-area resolution

@pytest.mark.parametrize("fixture_name", ["crs3857", "crs3395"])
def test_non_equal_area_mercator_crs_cannot_resolve_equal_area_policy(request, fixture_name):
    crs = request.getfixturevalue(fixture_name)
    with pytest.raises(ValueError, match="equal-area projection attestation"):
        EqualAreaProjectionPolicy("p", "1", "EXPLICIT", ResolutionState.RESOLVED, crs)


def test_arbitrary_projected_metre_crs_not_equal_area_by_assertion(crs3857):
    with pytest.raises(ValueError):
        EqualAreaProjectionPolicy("p", "1", "CALLER_ASSERTS_EQUAL_AREA", ResolutionState.RESOLVED, crs3857)


def test_unresolved_equal_area_policy_valid(projection_unresolved):
    assert projection_unresolved.state is ResolutionState.UNRESOLVED
    assert projection_unresolved.selected_crs is None


def test_resolved_equal_area_state_not_constructible_even_without_crs():
    with pytest.raises(ValueError):
        EqualAreaProjectionPolicy("p", "1", "future", ResolutionState.RESOLVED, None)


# FRAME-H002: unresolved lattice cannot claim canonical lattice cells

def test_unresolved_lattice_has_no_anchor(lattice_unresolved):
    assert not lattice_unresolved.is_resolved
    assert lattice_unresolved.anchor_x is None and lattice_unresolved.anchor_y is None


def test_unresolved_lattice_arbitrary_geometry_cannot_be_lattice_cell(lattice_unresolved, full_cell):
    # Constructor cannot even be completed without a successful AREA result; unresolved lattice
    # is independently rejected by the derivation boundary.
    with pytest.raises(ValueError, match="unresolved"):
        derive_lattice_cell(lattice_policy=lattice_unresolved, index_i=0, index_j=0)


def test_commercial_frame_cell_requires_lattice_artifact():
    sig = inspect.signature(CommercialFrameCell)
    assert "lattice_cell" in sig.parameters
    assert "full_cell_geometry" not in sig.parameters
    assert "full_cell_area" not in sig.parameters
    assert "area_unit" not in sig.parameters


def test_cell_resolution_identity_changes_without_claiming_resolved_lattice(projection_unresolved, canon_policy, engine):
    r1 = CellResolutionPolicy("r", "1", ResolutionState.RESOLVED, 100.0, "m")
    r2 = CellResolutionPolicy("r", "2", ResolutionState.RESOLVED, 200.0, "m")
    a = LatticePolicy("l", "1", projection_unresolved, r1, CellShape.SQUARE, None, None, "AXIS_ALIGNED", "INTEGER_IJ", "1", canon_policy, engine)
    b = LatticePolicy("l", "1", projection_unresolved, r2, CellShape.SQUARE, None, None, "AXIS_ALIGNED", "INTEGER_IJ", "1", canon_policy, engine)
    assert not a.is_resolved and not b.is_resolved
    assert a.identity_id != b.identity_id


def test_resolution_unit_must_be_metre():
    with pytest.raises(ValueError):
        CellResolutionPolicy("r", "1", ResolutionState.RESOLVED, 100.0, "km")


# Membership remains separate/unresolved

def test_unresolved_membership_policy_forces_unresolved(full_cell, boundary_artifact, membership_unresolved):
    m = evaluate_boundary_membership(full_cell, boundary_artifact, membership_unresolved)
    assert m.state is BoundaryMembershipState.UNRESOLVED


def test_membership_self_assertion_rejected(full_cell, boundary_artifact, membership_unresolved):
    with pytest.raises(ValueError):
        FrameBoundaryMembership(full_cell, boundary_artifact, membership_unresolved, None, BoundaryMembershipState.MEMBER, ())


def test_resolved_membership_policy_without_implementation_stays_unresolved(full_cell, boundary_artifact):
    p = FrameBoundaryMembershipPolicy("membership", "future-1", ResolutionState.RESOLVED, "FUTURE_APPROVED_METHOD")
    r = evaluate_boundary_membership(full_cell, boundary_artifact, p)
    assert r.state is BoundaryMembershipState.UNRESOLVED
    assert r.reason_codes == ("boundary_membership_method_not_implemented",)


# FRAME-H003-C numeric/operation coherence

@pytest.mark.parametrize("area,full,expected", [(10000.0,10000.0,1.0),(5000.0,10000.0,0.5),(1e-5,10000.0,1e-9),(0.0,10000.0,0.0)])
def test_diagnostic_fraction_is_derived(full_cell, boundary_artifact, area, full, expected):
    d = BoundaryIntersectionEvidence(full_cell, boundary_artifact, DiagnosticState.AVAILABLE, None, area, full)
    assert d.intersection_fraction == expected
    assert d.full_cell_geometry.semantic_geometry_id == full_cell.semantic_geometry_id


def test_diagnostic_constructor_has_no_fraction_input():
    assert "intersection_fraction" not in inspect.signature(BoundaryIntersectionEvidence).parameters


def test_invalid_intersection_area_greater_than_full_rejected(full_cell, boundary_artifact):
    with pytest.raises(ValueError):
        BoundaryIntersectionEvidence(full_cell, boundary_artifact, DiagnosticState.AVAILABLE, None, 11000.0, 10000.0)


def test_unresolved_diagnostic_does_not_fake_zero(full_cell, boundary_artifact):
    d = BoundaryIntersectionEvidence(full_cell, boundary_artifact, DiagnosticState.UNRESOLVED)
    assert d.intersection_area is None and d.intersection_fraction is None


def test_correct_intersection_operation_evidence_accepted(full_cell, boundary_artifact, canon_policy, engine):
    op = make_intersection_operation(full_cell, boundary_artifact, canon_policy, engine)
    d = BoundaryIntersectionEvidence(full_cell, boundary_artifact, DiagnosticState.AVAILABLE, op, 10000.0, 10000.0)
    assert d.intersection_operation is op


def test_foreign_intersection_inputs_rejected(full_cell, full_cell2, boundary_artifact, canon_policy, engine):
    op = make_intersection_operation(full_cell2, boundary_artifact, canon_policy, engine)
    with pytest.raises(ValueError, match="inputs"):
        BoundaryIntersectionEvidence(full_cell, boundary_artifact, DiagnosticState.AVAILABLE, op, 10000.0, 10000.0)


def test_non_intersect_operation_rejected(full_cell, boundary_artifact, canon_policy, engine):
    from sitescore_spatial import area_of_projected_geometry, AreaPolicy, GeometryOperationPolicy, GeometryOperation
    ap = AreaPolicy()
    opol = GeometryOperationPolicy("area", "1", GeometryOperation.AREA, canon_policy.precision_policy)
    area_op = area_of_projected_geometry(full_cell, area_policy=ap, operation_policy=opol, engine=engine)
    with pytest.raises(ValueError, match="INTERSECT"):
        BoundaryIntersectionEvidence(full_cell, boundary_artifact, DiagnosticState.AVAILABLE, area_op, 10000.0, 10000.0)


def test_membership_rejects_foreign_diagnostic_cell(full_cell, full_cell2, boundary_artifact, membership_unresolved):
    d = BoundaryIntersectionEvidence(full_cell2, boundary_artifact, DiagnosticState.AVAILABLE, None, 10000.0, 10000.0)
    with pytest.raises(ValueError, match="full-cell"):
        FrameBoundaryMembership(full_cell, boundary_artifact, membership_unresolved, d, BoundaryMembershipState.UNRESOLVED, ("boundary_membership_policy_unresolved",))


def test_membership_rejects_foreign_diagnostic_boundary(full_cell, boundary_artifact, boundary_artifact2, membership_unresolved):
    d = BoundaryIntersectionEvidence(full_cell, boundary_artifact2, DiagnosticState.AVAILABLE, None, 10000.0, 10000.0)
    with pytest.raises(ValueError, match="boundary"):
        FrameBoundaryMembership(full_cell, boundary_artifact, membership_unresolved, d, BoundaryMembershipState.UNRESOLVED, ("boundary_membership_policy_unresolved",))


# FRAME-H003-A frame geography/boundary coherence and unresolved zero-cell structural frame

def test_frame_geography_boundary_mismatch_rejected(geography, boundary_artifact2, lattice_unresolved, membership_unresolved, eligibility_policy):
    with pytest.raises(ValueError, match="geography/boundary"):
        CommercialFrame(
            geography, boundary_artifact2, lattice_unresolved, membership_unresolved,
            eligibility_policy, (), FrameState.UNRESOLVED,
            ("boundary_membership_policy_unresolved", "lattice_policy_unresolved"), None,
        )


def test_unresolved_frame_with_zero_canonical_cells_is_valid(geography, boundary_artifact, lattice_unresolved, membership_unresolved, eligibility_policy):
    f = build_frame(
        benchmark_geography=geography,
        boundary_artifact=boundary_artifact,
        lattice_policy=lattice_unresolved,
        membership_policy=membership_unresolved,
        eligibility_policy=eligibility_policy,
        cells=(),
    )
    assert f.state is FrameState.UNRESOLVED
    assert f.cells == ()
    assert f.eligible_cell_ids == ()


def test_generated_at_nonsemantic_for_unresolved_frame(geography, boundary_artifact, lattice_unresolved, membership_unresolved, eligibility_policy):
    a = build_frame(benchmark_geography=geography, boundary_artifact=boundary_artifact, lattice_policy=lattice_unresolved, membership_policy=membership_unresolved, eligibility_policy=eligibility_policy, cells=(), generated_at=datetime(2026,8,14,tzinfo=timezone.utc))
    b = build_frame(benchmark_geography=geography, boundary_artifact=boundary_artifact, lattice_policy=lattice_unresolved, membership_policy=membership_unresolved, eligibility_policy=eligibility_policy, cells=(), generated_at=datetime(2026,8,15,tzinfo=timezone.utc))
    assert a.frame_id == b.frame_id


def test_membership_policy_change_changes_frame_identity(geography, boundary_artifact, lattice_unresolved, eligibility_policy):
    m1 = FrameBoundaryMembershipPolicy("m", "1", ResolutionState.UNRESOLVED)
    m2 = FrameBoundaryMembershipPolicy("m", "2", ResolutionState.UNRESOLVED)
    f1 = build_frame(benchmark_geography=geography, boundary_artifact=boundary_artifact, lattice_policy=lattice_unresolved, membership_policy=m1, eligibility_policy=eligibility_policy, cells=())
    f2 = build_frame(benchmark_geography=geography, boundary_artifact=boundary_artifact, lattice_policy=lattice_unresolved, membership_policy=m2, eligibility_policy=eligibility_policy, cells=())
    assert f1.frame_id != f2.frame_id

# White-box downstream contract tests for FRAME-H002/H003-B. The projection fixture
# intentionally bypasses FRAME-H001 only inside tests; public RESOLVED construction remains impossible.

def test_lattice_cell_rejects_foreign_crs(crs3395, crs3857, canon_policy, engine):
    from shapely.geometry import Polygon
    from sitescore_spatial import canonicalize_geometry
    from conftest import unsafe_resolved_lattice, make_area_result
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine)
    g = canonicalize_geometry(Polygon([(0,0),(100,0),(100,100),(0,100),(0,0)]), crs_identity=crs3395, policy=canon_policy, engine=engine)
    with pytest.raises(ValueError, match="CRS"):
        LatticeCellArtifact(lattice, 0, 0, g, make_area_result(g, canon_policy, engine))


def test_lattice_cell_rejects_wrong_size(crs3857, canon_policy, engine):
    from shapely.geometry import Polygon
    from sitescore_spatial import canonicalize_geometry
    from conftest import unsafe_resolved_lattice, make_area_result
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine, size=100.0)
    g = canonicalize_geometry(Polygon([(0,0),(90,0),(90,90),(0,90),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    with pytest.raises(ValueError, match="anchor/resolution/index|area"):
        LatticeCellArtifact(lattice, 0, 0, g, make_area_result(g, canon_policy, engine))


def test_lattice_cell_rejects_wrong_index_location(full_cell, crs3857, canon_policy, engine):
    from conftest import unsafe_resolved_lattice, make_area_result
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine)
    with pytest.raises(ValueError, match="anchor/resolution/index"):
        LatticeCellArtifact(lattice, 1, 0, full_cell, make_area_result(full_cell, canon_policy, engine))


def test_lattice_cell_area_is_derived_not_constructor_float(full_cell, crs3857, canon_policy, engine):
    from conftest import unsafe_resolved_lattice, make_test_lattice_cell
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine)
    cell = make_test_lattice_cell(lattice, full_cell, 0, 0, canon_policy, engine)
    assert cell.full_cell_area == 10000.0
    assert cell.area_unit == "m2"
    assert "full_cell_area" not in inspect.signature(LatticeCellArtifact).parameters
    assert "area_unit" not in inspect.signature(LatticeCellArtifact).parameters


def test_lattice_anchor_change_changes_derived_cell_id(crs3857, canon_policy, engine):
    from shapely.geometry import Polygon
    from sitescore_spatial import canonicalize_geometry
    from conftest import unsafe_resolved_lattice, make_test_lattice_cell
    l1 = unsafe_resolved_lattice(crs3857, canon_policy, engine, anchor=(0.0,0.0), version="a")
    l2 = unsafe_resolved_lattice(crs3857, canon_policy, engine, anchor=(10.0,0.0), version="b")
    g1 = canonicalize_geometry(Polygon([(0,0),(100,0),(100,100),(0,100),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    g2 = canonicalize_geometry(Polygon([(10,0),(110,0),(110,100),(10,100),(10,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    c1 = make_test_lattice_cell(l1,g1,0,0,canon_policy,engine)
    c2 = make_test_lattice_cell(l2,g2,0,0,canon_policy,engine)
    assert c1.lattice_cell_id != c2.lattice_cell_id


def test_lattice_index_change_changes_derived_cell_id(crs3857, canon_policy, engine):
    from shapely.geometry import Polygon
    from sitescore_spatial import canonicalize_geometry
    from conftest import unsafe_resolved_lattice, make_test_lattice_cell
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine)
    g0 = canonicalize_geometry(Polygon([(0,0),(100,0),(100,100),(0,100),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    g1 = canonicalize_geometry(Polygon([(100,0),(200,0),(200,100),(100,100),(100,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    c0 = make_test_lattice_cell(lattice,g0,0,0,canon_policy,engine)
    c1 = make_test_lattice_cell(lattice,g1,1,0,canon_policy,engine)
    assert c0.lattice_cell_id != c1.lattice_cell_id


def _make_commercial_cell(lattice_cell, boundary, membership_policy, evidence_policy, eligibility_policy):
    m = evaluate_boundary_membership(lattice_cell.full_cell_geometry, boundary, membership_policy)
    b = CommercialFrameEvidenceBundle(lattice_cell, evidence_policy)
    e = evaluate_commercial_eligibility(b, eligibility_policy)
    return CommercialFrameCell(lattice_cell, m, b, e)


def test_frame_rejects_cell_membership_foreign_boundary(full_cell, crs3857, canon_policy, engine, boundary_artifact, boundary_artifact2, geography, membership_unresolved, evidence_policy, eligibility_policy):
    from conftest import unsafe_resolved_lattice, make_test_lattice_cell
    lattice = unsafe_resolved_lattice(crs3857, canon_policy, engine)
    lc = make_test_lattice_cell(lattice, full_cell, 0, 0, canon_policy, engine)
    cell = _make_commercial_cell(lc, boundary_artifact2, membership_unresolved, evidence_policy, eligibility_policy)
    with pytest.raises(ValueError, match="boundary artifact mismatch"):
        # Direct construction is used so the frame-level invariant is exercised.
        CommercialFrame(geography, boundary_artifact, lattice, membership_unresolved, eligibility_policy, (cell,), FrameState.UNRESOLVED, ("boundary_membership_policy_unresolved","cell_membership_unresolved"))


def test_correct_commutative_intersection_operation_inputs_accepted(full_cell, boundary_artifact, canon_policy, engine):
    from sitescore_spatial import GeometryOperationPolicy, GeometryOperation, intersect_geometries
    p = GeometryOperationPolicy("diag", "1", GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty_result=True)
    op = intersect_geometries(boundary_artifact.canonical_geometry, full_cell, policy=p, canonicalization_policy=canon_policy, engine=engine)
    d = BoundaryIntersectionEvidence(full_cell, boundary_artifact, DiagnosticState.AVAILABLE, op, 10000.0, 10000.0)
    assert d.intersection_fraction == 1.0

# FRAME-H004/H005 evidence-lineage hardening

def test_bundle_detached_cell_string_constructor_api_impossible():
    sig = inspect.signature(CommercialFrameEvidenceBundle)
    assert "lattice_cell" in sig.parameters
    assert "cell_lattice_id" not in sig.parameters


def test_same_evidence_different_actual_cell_changes_bundle_identity(evidence_policy, evidence_cell, evidence_cell2, classification_unresolved, applicability_unresolved):
    i1 = unresolved_item(evidence_cell, classification_unresolved, applicability_unresolved, 9)
    i2 = unresolved_item(evidence_cell2, classification_unresolved, applicability_unresolved, 9)
    b1 = make_bundle(evidence_policy, evidence_cell, (i1,))
    b2 = make_bundle(evidence_policy, evidence_cell2, (i2,))
    assert b1.bundle_id != b2.bundle_id


def test_bundle_rejects_evidence_applicable_to_foreign_cell(evidence_policy, evidence_cell, evidence_cell2):
    item = resolved_test_item(evidence_cell, "qualifying_place", EvidenceDisposition.POSITIVE, 10)
    with pytest.raises(ValueError, match="foreign lattice cell"):
        make_bundle(evidence_policy, evidence_cell2, (item,))


def test_commercial_frame_cell_rejects_bundle_for_foreign_lattice_cell(evidence_policy, eligibility_policy, evidence_cell, evidence_cell2, boundary_artifact, membership_unresolved):
    membership = evaluate_boundary_membership(evidence_cell.full_cell_geometry, boundary_artifact, membership_unresolved)
    foreign_bundle = make_bundle(evidence_policy, evidence_cell2)
    foreign_eligibility = evaluate_commercial_eligibility(foreign_bundle, eligibility_policy)
    with pytest.raises(ValueError, match="evidence bundle cell mismatch"):
        CommercialFrameCell(evidence_cell, membership, foreign_bundle, foreign_eligibility)


def test_public_classification_policy_cannot_resolve_arbitrary_disposition():
    with pytest.raises(ValueError, match="classification"):
        CommercialEvidenceClassificationPolicy("classify", "1", ResolutionState.RESOLVED, "CALLER_MAPS_ANYTHING")


def test_public_raw_evidence_cannot_self_assert_positive(evidence_cell, classification_unresolved):
    rec = raw(11)
    with pytest.raises(ValueError, match="classification state"):
        CommercialEvidenceClassification(rec, classification_unresolved, "qualifying_place", EvidenceDisposition.POSITIVE, ())


def test_public_raw_evidence_cannot_self_assert_exclusion(evidence_cell, classification_unresolved):
    rec = raw(12)
    with pytest.raises(ValueError, match="classification state"):
        CommercialEvidenceClassification(rec, classification_unresolved, "authoritative_noncommercial", EvidenceDisposition.EXPLICIT_EXCLUSION, ())


def test_classification_resolved_but_applicability_unresolved_yields_unknown(evidence_policy, eligibility_policy, evidence_cell, applicability_unresolved):
    cls = _unsafe_resolved_classification(raw(13), "qualifying_place", EvidenceDisposition.POSITIVE)
    app = evaluate_evidence_cell_applicability(cls, evidence_cell, applicability_unresolved)
    item = CommercialEvidenceItem(cls, app)
    bundle = make_bundle(evidence_policy, evidence_cell, (item,))
    assert evaluate_commercial_eligibility(bundle, eligibility_policy).state is EligibilityState.UNKNOWN


def test_mere_source_record_without_cell_applicability_yields_unknown(evidence_policy, eligibility_policy, evidence_cell, classification_unresolved, applicability_unresolved):
    item = unresolved_item(evidence_cell, classification_unresolved, applicability_unresolved, 14)
    bundle = make_bundle(evidence_policy, evidence_cell, (item,))
    result = evaluate_commercial_eligibility(bundle, eligibility_policy)
    assert result.state is EligibilityState.UNKNOWN
    assert result.reason_codes == ("insufficient_commercial_evidence",)


def test_classification_policy_version_changes_evidence_and_result_identity(evidence_policy, eligibility_policy, evidence_cell, applicability_unresolved):
    p1 = CommercialEvidenceClassificationPolicy("classification", "1", ResolutionState.UNRESOLVED)
    p2 = CommercialEvidenceClassificationPolicy("classification", "2", ResolutionState.UNRESOLVED)
    rec = raw(15)
    c1 = classify_commercial_evidence(rec, p1)
    c2 = classify_commercial_evidence(rec, p2)
    a1 = evaluate_evidence_cell_applicability(c1, evidence_cell, applicability_unresolved)
    a2 = evaluate_evidence_cell_applicability(c2, evidence_cell, applicability_unresolved)
    i1, i2 = CommercialEvidenceItem(c1,a1), CommercialEvidenceItem(c2,a2)
    b1, b2 = make_bundle(evidence_policy,evidence_cell,(i1,)), make_bundle(evidence_policy,evidence_cell,(i2,))
    r1, r2 = evaluate_commercial_eligibility(b1,eligibility_policy), evaluate_commercial_eligibility(b2,eligibility_policy)
    assert i1.identity_id != i2.identity_id
    assert b1.bundle_id != b2.bundle_id
    assert r1.identity_id != r2.identity_id


def test_applicability_policy_version_changes_evidence_bundle_result_identity(evidence_policy, eligibility_policy, evidence_cell, classification_unresolved):
    p1 = EvidenceCellApplicabilityPolicy("apply", "1", ResolutionState.UNRESOLVED)
    p2 = EvidenceCellApplicabilityPolicy("apply", "2", ResolutionState.UNRESOLVED)
    cls = classify_commercial_evidence(raw(16), classification_unresolved)
    a1 = evaluate_evidence_cell_applicability(cls,evidence_cell,p1)
    a2 = evaluate_evidence_cell_applicability(cls,evidence_cell,p2)
    i1, i2 = CommercialEvidenceItem(cls,a1), CommercialEvidenceItem(cls,a2)
    b1, b2 = make_bundle(evidence_policy,evidence_cell,(i1,)), make_bundle(evidence_policy,evidence_cell,(i2,))
    r1, r2 = evaluate_commercial_eligibility(b1,eligibility_policy), evaluate_commercial_eligibility(b2,eligibility_policy)
    assert a1.identity_id != a2.identity_id
    assert b1.bundle_id != b2.bundle_id
    assert r1.identity_id != r2.identity_id
