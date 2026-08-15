from dataclasses import replace

import pytest
import shapely
from shapely.geometry import Polygon

from sitescore_spatial import (
    BoundaryGeometryArtifact,
    CRSIdentity,
    CanonicalGeometry,
    GeometryEngineIdentity,
    GeometryOperation,
    GeometryOperationResult,
    GeometrySourceIdentity,
    OperationState,
    TransformPlan,
    build_boundary_geometry_artifact,
    build_crs_identity,
    build_geometry_engine_identity,
    canonicalize_geometry,
    content_hash,
    semantic_hash,
)
from conftest import op_policy


def test_forged_crs_identity_id_rejected(crs4326):
    with pytest.raises(ValueError, match="crs_identity_id"):
        replace(crs4326, crs_identity_id="0" * 64)


def test_forged_source_identity_id_rejected(source):
    with pytest.raises(ValueError, match="source_identity_id"):
        replace(source, source_identity_id="0" * 64)


def test_forged_engine_identity_id_rejected(engine):
    with pytest.raises(ValueError, match="engine_identity_id"):
        replace(engine, engine_identity_id="0" * 64)


def test_fictional_but_self_consistent_engine_rejected_at_execution(polygon, crs4326, canon_policy, engine):
    record = engine.semantic_record() | {"geometry_library": "FakeGIS", "geometry_library_version": "99.0"}
    fake = GeometryEngineIdentity(engine_identity_id=semantic_hash(record), **record)
    with pytest.raises(ValueError, match="active spatial runtime"):
        canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=fake)


def test_canonical_geometry_wkb_hash_mismatch_rejected(canonical):
    other_wkb = shapely.to_wkb(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), hex=False, output_dimension=2, byte_order=1, include_srid=False, flavor="iso")
    with pytest.raises(ValueError, match="canonical_geometry_hash"):
        CanonicalGeometry(
            semantic_geometry_id=canonical.semantic_geometry_id,
            canonical_wkb=other_wkb,
            canonical_geometry_hash=canonical.canonical_geometry_hash,
            geometry_type=canonical.geometry_type,
            crs_identity=canonical.crs_identity,
            canonicalization_policy=canonical.canonicalization_policy,
            engine_identity=canonical.engine_identity,
            is_empty=False,
        )


def test_canonical_geometry_semantic_id_mismatch_rejected(canonical):
    with pytest.raises(ValueError, match="semantic_geometry_id"):
        replace(canonical, semantic_geometry_id="0" * 64)


def test_canonical_geometry_type_wkb_mismatch_rejected(canonical):
    from sitescore_spatial import GeometryType
    with pytest.raises(ValueError, match="geometry_type"):
        replace(canonical, geometry_type=GeometryType.MULTIPOLYGON)


def test_boundary_artifact_id_mismatch_rejected(geography, source, canonical, canon_policy, engine, now):
    artifact = build_boundary_geometry_artifact(
        geography_identity=geography, geometry_role="ADMIN_BOUNDARY", source_identity=source,
        canonical_geometry=canonical, parser_id="parser", parser_version="1",
        canonicalization_policy=canon_policy, engine=engine, source_refs=("src:1",), generated_at=now,
    )
    with pytest.raises(ValueError, match="geometry_artifact_id"):
        replace(artifact, geometry_artifact_id="0" * 64)


def test_transform_plan_pipeline_hash_mismatch_rejected(crs4326, crs3857, engine):
    from sitescore_spatial import CRSTransformPolicy, build_transform_plan
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan is not None and not reasons
    with pytest.raises(ValueError, match="selected_pipeline_hash"):
        replace(plan, selected_pipeline_hash="0" * 64)


def test_transform_plan_id_mismatch_rejected(crs4326, crs3857, engine):
    from sitescore_spatial import CRSTransformPolicy, build_transform_plan
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan is not None and not reasons
    with pytest.raises(ValueError, match="plan_id"):
        replace(plan, plan_id="0" * 64)


def _operation_id(*, operation, inputs, policy_id, engine_id, state, transform_plan_id=None, output=None, numeric=None, unit=None, reasons=()):
    return semantic_hash({
        "operation": operation.value,
        "inputs": sorted(inputs),
        "operation_policy_id": policy_id,
        "area_policy_id": None,
        "engine_id": engine_id,
        "input_crs_identity_id": None,
        "transform_plan_id": transform_plan_id,
        "output_semantic_geometry_id": output.semantic_geometry_id if output else None,
        "numeric_value": numeric,
        "unit": unit,
        "state": state.value,
        "reason_codes": sorted(reasons),
    })


def test_operation_result_id_mismatch_rejected(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="operation_id"):
        GeometryOperationResult(
            operation_id="0" * 64, operation=GeometryOperation.INTERSECT, state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical), operation_policy=policy,
            engine_identity=engine, output_geometry=canonical,
        )


def test_fabricated_success_without_payload_rejected(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    oid = _operation_id(operation=GeometryOperation.INTERSECT, inputs=(canonical.semantic_geometry_id,), policy_id=policy.identity_id, engine_id=engine.engine_identity_id, state=OperationState.SUCCESS)
    with pytest.raises(ValueError, match="requires output_geometry"):
        GeometryOperationResult(
            operation_id=oid, operation=GeometryOperation.INTERSECT, state=OperationState.SUCCESS,
            input_geometries=(canonical,), operation_policy=policy,
            engine_identity=engine,
        )


def test_non_success_carrying_success_payload_rejected(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    oid = _operation_id(operation=GeometryOperation.INTERSECT, inputs=(canonical.semantic_geometry_id,), policy_id=policy.identity_id, engine_id=engine.engine_identity_id, state=OperationState.UNRESOLVED, output=canonical, reasons=("x",))
    with pytest.raises(ValueError, match="must not carry"):
        GeometryOperationResult(
            operation_id=oid, operation=GeometryOperation.INTERSECT, state=OperationState.UNRESOLVED,
            input_geometries=(canonical,), operation_policy=policy,
            engine_identity=engine, output_geometry=canonical, reason_codes=("x",),
        )
