from dataclasses import replace

import pytest
import shapely
from shapely.geometry import MultiPolygon, Polygon

from sitescore_spatial import (
    BoundaryGeometryArtifact,
    CRSTransformPolicy,
    CanonicalGeometry,
    EmptyGeometryBehavior,
    GeometryCanonicalizationPolicy,
    GeometryOperation,
    GeometryOperationResult,
    GeometryType,
    OperationState,
    TransformPlan,
    build_boundary_geometry_artifact,
    build_crs_identity,
    build_transform_plan,
    canonicalize_geometry,
    content_hash,
    intersect_geometries,
    operation_output_canonicalization_policy,
    project_geometry,
    semantic_hash,
)
from conftest import op_policy


def _semantic_geometry_id(wkb, gtype, crs, policy, engine):
    return semantic_hash({
        "canonical_geometry_hash": content_hash(wkb),
        "geometry_type": gtype.value,
        "crs_identity_id": crs.crs_identity_id,
        "canonicalization_policy_id": policy.identity_id,
        "engine_identity_id": engine.engine_identity_id,
    })


def _raw_wkb(geometry):
    return shapely.to_wkb(geometry, hex=False, output_dimension=2, byte_order=1, include_srid=False, flavor="iso")


def test_non_normalized_polygon_wkb_self_consistent_identity_rejected(crs4326, canon_policy, engine):
    # Deliberately non-normalized start point/orientation.
    raw = _raw_wkb(Polygon([(2,0),(2,2),(0,2),(0,0),(2,0)]))
    assert raw != canonicalize_geometry(shapely.from_wkb(raw), crs_identity=crs4326, policy=canon_policy, engine=engine).canonical_wkb
    with pytest.raises(ValueError, match="not canonical"):
        CanonicalGeometry(
            semantic_geometry_id=_semantic_geometry_id(raw, GeometryType.POLYGON, crs4326, canon_policy, engine),
            canonical_wkb=raw,
            canonical_geometry_hash=content_hash(raw),
            geometry_type=GeometryType.POLYGON,
            crs_identity=crs4326,
            canonicalization_policy=canon_policy,
            engine_identity=engine,
            is_empty=False,
        )


def test_non_normalized_multipolygon_member_order_rejected(crs4326, canon_policy, engine):
    p1 = Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)])
    p2 = Polygon([(3,0),(4,0),(4,1),(3,1),(3,0)])
    raw = _raw_wkb(MultiPolygon([p1, p2]))
    canonical = canonicalize_geometry(MultiPolygon([p1, p2]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    if raw == canonical.canonical_wkb:
        raw = _raw_wkb(MultiPolygon([p2, p1]))
    assert raw != canonical.canonical_wkb
    with pytest.raises(ValueError, match="not canonical"):
        CanonicalGeometry(
            semantic_geometry_id=_semantic_geometry_id(raw, GeometryType.MULTIPOLYGON, crs4326, canon_policy, engine),
            canonical_wkb=raw,
            canonical_geometry_hash=content_hash(raw),
            geometry_type=GeometryType.MULTIPOLYGON,
            crs_identity=crs4326,
            canonicalization_policy=canon_policy,
            engine_identity=engine,
            is_empty=False,
        )


def test_exact_canonical_wkb_direct_constructor_accepts(canonical):
    rebuilt = CanonicalGeometry(
        semantic_geometry_id=canonical.semantic_geometry_id,
        canonical_wkb=canonical.canonical_wkb,
        canonical_geometry_hash=canonical.canonical_geometry_hash,
        geometry_type=canonical.geometry_type,
        crs_identity=canonical.crs_identity,
        canonicalization_policy=canonical.canonicalization_policy,
        engine_identity=canonical.engine_identity,
        is_empty=canonical.is_empty,
    )
    assert rebuilt == canonical


def test_builder_result_satisfies_direct_canonical_invariant(canonical):
    assert CanonicalGeometry(
        semantic_geometry_id=canonical.semantic_geometry_id,
        canonical_wkb=canonical.canonical_wkb,
        canonical_geometry_hash=canonical.canonical_geometry_hash,
        geometry_type=canonical.geometry_type,
        crs_identity=canonical.crs_identity,
        canonicalization_policy=canonical.canonicalization_policy,
        engine_identity=canonical.engine_identity,
        is_empty=canonical.is_empty,
    ).semantic_geometry_id == canonical.semantic_geometry_id


def test_empty_bytes_cannot_claim_boundary_reject_policy(crs4326, canon_policy, engine):
    empty = Polygon()
    output_policy = operation_output_canonicalization_policy(canon_policy)
    allowed = canonicalize_geometry(empty, crs_identity=crs4326, policy=output_policy, engine=engine)
    with pytest.raises(ValueError, match="claimed canonicalization policy"):
        CanonicalGeometry(
            semantic_geometry_id=_semantic_geometry_id(allowed.canonical_wkb, GeometryType.POLYGON, crs4326, canon_policy, engine),
            canonical_wkb=allowed.canonical_wkb,
            canonical_geometry_hash=allowed.canonical_geometry_hash,
            geometry_type=GeometryType.POLYGON,
            crs_identity=crs4326,
            canonicalization_policy=canon_policy,
            engine_identity=engine,
            is_empty=True,
        )


def test_empty_intersection_commits_explicit_empty_allowed_policy(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(2,2),(3,2),(3,3),(2,3),(2,2)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty=True)
    result = intersect_geometries(a, b, policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.output_geometry.is_empty
    assert result.output_geometry.canonicalization_policy.empty_geometry_behavior is EmptyGeometryBehavior.ALLOW_OPERATION_OUTPUT
    assert result.output_geometry.canonicalization_policy_id != canon_policy.identity_id


def test_empty_boundary_artifact_direct_construction_impossible(geography, source, canon_policy, engine, now):
    output_policy = operation_output_canonicalization_policy(canon_policy)
    empty = canonicalize_geometry(Polygon(), crs_identity=source.source_crs_identity, policy=output_policy, engine=engine)
    with pytest.raises(ValueError, match="boundary artifact cannot contain empty"):
        BoundaryGeometryArtifact(
            geometry_artifact_id="0" * 64,
            geography_identity=geography,
            geometry_role="ADMIN_BOUNDARY",
            source_identity=source,
            raw_artifact_ref=None,
            canonical_geometry=empty,
            canonical_geometry_hash=empty.canonical_geometry_hash,
            canonical_geometry_encoding=output_policy.encoding,
            canonical_geometry_type=empty.geometry_type,
            canonical_crs_identity=empty.crs_identity,
            parser_id="parser",
            parser_version="1",
            canonicalization_policy_id=empty.canonicalization_policy_id,
            source_refs=("src:1",),
            generated_at=now,
        )


def _project_result_id(*, source, op_policy_id, engine, plan, output, state=OperationState.SUCCESS, reasons=()):
    return semantic_hash({
        "operation": GeometryOperation.PROJECT.value,
        "inputs": [source.semantic_geometry_id],
        "operation_policy_id": op_policy_id,
        "area_policy_id": None,
        "engine_id": engine.engine_identity_id,
        "input_crs_identity_id": source.crs_identity.crs_identity_id,
        "transform_plan_id": plan.plan_id if plan else None,
        "output_semantic_geometry_id": output.semantic_geometry_id if output else None,
        "numeric_value": None,
        "unit": None,
        "state": state.value,
        "reason_codes": sorted(reasons),
    })


def test_success_project_without_plan_rejected(canonical, canon_policy, engine):
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="requires exact transform_plan"):
        GeometryOperationResult(
            operation_id=_project_result_id(source=canonical, op_policy_id=op.identity_id, engine=engine, plan=None, output=canonical),
            operation=GeometryOperation.PROJECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical,),
            operation_policy=op,
            engine_identity=engine,
            output_geometry=canonical,
        )


def test_success_project_foreign_plan_source_rejected(canonical, canon_policy, engine, crs3857):
    target = build_crs_identity("EPSG:32618")
    foreign, reasons = build_transform_plan(crs3857, target, CRSTransformPolicy(), engine)
    assert foreign and not reasons
    output = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=target, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="source CRS mismatch"):
        GeometryOperationResult(
            operation_id="0"*64, operation=GeometryOperation.PROJECT, state=OperationState.SUCCESS,
            input_geometries=(canonical,), operation_policy=op,
            engine_identity=engine,
            transform_plan=foreign, output_geometry=output,
        )


def test_success_project_plan_engine_mismatch_rejected(canonical, canon_policy, engine, crs3857):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    from sitescore_spatial.contracts import GeometryEngineIdentity
    engine_record = engine.semantic_record()
    engine_record["engine_identity_version"] = "9.9"
    fake_engine = GeometryEngineIdentity(engine_identity_id=semantic_hash(engine_record), **engine_record)
    record = {
        "source_crs_identity_id": plan.source_crs_identity_id,
        "target_crs_identity_id": plan.target_crs_identity_id,
        "policy_identity_id": plan.policy_identity_id,
        "engine_identity_id": fake_engine.engine_identity_id,
        "selected_pipeline_hash": plan.selected_pipeline_hash,
        "grid_identities": list(plan.grid_identities),
    }
    fake_plan = TransformPlan(
        plan_id=semantic_hash(record),
        source_crs_identity=plan.source_crs_identity,
        target_crs_identity=plan.target_crs_identity,
        transform_policy=plan.transform_policy,
        engine_identity=fake_engine,
        selected_pipeline_hash=plan.selected_pipeline_hash,
        selected_pipeline_definition=plan.selected_pipeline_definition,
        grid_identities=plan.grid_identities,
    )
    output = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="engine mismatch"):
        GeometryOperationResult(
            operation_id="0"*64, operation=GeometryOperation.PROJECT, state=OperationState.SUCCESS,
            input_geometries=(canonical,), operation_policy=op,
            engine_identity=engine,
            transform_plan=fake_plan, output_geometry=output,
        )


def test_success_project_output_crs_mismatch_rejected(canonical, canon_policy, engine, crs3857):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="output CRS"):
        GeometryOperationResult(
            operation_id="0"*64, operation=GeometryOperation.PROJECT, state=OperationState.SUCCESS,
            input_geometries=(canonical,), operation_policy=op,
            engine_identity=engine,
            transform_plan=plan, output_geometry=canonical,
        )


def test_success_intersect_transform_plan_rejected(canonical, canon_policy, engine, crs3857):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    op = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="INTERSECT must not carry transform_plan"):
        GeometryOperationResult(
            operation_id="0"*64, operation=GeometryOperation.INTERSECT, state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical), operation_policy=op,
            engine_identity=engine, transform_plan=plan, output_geometry=canonical,
        )


def test_success_area_transform_plan_rejected(canonical, canon_policy, engine, crs3857):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="AREA must not carry transform_plan"):
        GeometryOperationResult(
            operation_id="0"*64, operation=GeometryOperation.AREA, state=OperationState.SUCCESS,
            input_geometries=(canonical,), operation_policy=op,
            engine_identity=engine, transform_plan=plan, numeric_value=1.0, unit="m2",
        )


def test_official_project_result_attaches_exact_verified_plan(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.transform_plan is not None
    assert result.transform_plan.source_crs_identity_id == source.crs_identity.crs_identity_id
    assert result.transform_plan.target_crs_identity_id == result.output_geometry.crs_identity.crs_identity_id
    assert result.transform_plan.engine_identity_id == result.engine_identity_id


def test_same_actual_project_semantics_deterministic_operation_identity(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    a = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=op, canonicalization_policy=canon_policy, engine=engine)
    b = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert a.transform_plan.plan_id == b.transform_plan.plan_id
    assert a.operation_id == b.operation_id
