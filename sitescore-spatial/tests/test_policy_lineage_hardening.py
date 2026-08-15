from __future__ import annotations

from dataclasses import replace

import pytest
from shapely.geometry import Polygon

from sitescore_spatial import (
    AreaPolicy,
    CRSTransformPolicy,
    GeometryOperation,
    GeometryOperationPolicy,
    GeometryOperationResult,
    OperationState,
    TransformPlan,
    area_of_projected_geometry,
    build_crs_identity,
    build_transform_plan,
    canonicalize_geometry,
    intersect_geometries,
    project_geometry,
    semantic_hash,
)


def op_policy(operation, precision_policy, *, allow_empty=False, version="1.0"):
    return GeometryOperationPolicy(
        policy_id=f"{operation.value.lower()}-policy",
        policy_version=version,
        operation=operation,
        precision_policy=precision_policy,
        allow_empty_result=allow_empty,
    )


def result_id(*, operation, inputs, operation_policy, engine_id, input_crs=None,
              transform_plan=None, area_policy=None, output=None, numeric=None,
              unit=None, state=OperationState.SUCCESS, reasons=()):
    return semantic_hash({
        "operation": operation.value,
        "inputs": sorted(inputs),
        "operation_policy_id": operation_policy.identity_id,
        "area_policy_id": area_policy.identity_id if area_policy is not None else None,
        "engine_id": engine_id,
        "input_crs_identity_id": input_crs.crs_identity_id if input_crs is not None else None,
        "transform_plan_id": transform_plan.plan_id if transform_plan is not None else None,
        "output_semantic_geometry_id": output.semantic_geometry_id if output is not None else None,
        "numeric_value": numeric,
        "unit": unit,
        "state": state.value,
        "reason_codes": sorted(reasons),
    })


def test_detached_operation_policy_id_constructor_api_removed(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(TypeError, match="operation_policy_id"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical),
            operation_policy_id=policy.identity_id,
            engine_identity=engine,
            output_geometry=canonical,
        )


@pytest.mark.parametrize(
    ("operation", "wrong_operation"),
    [
        (GeometryOperation.INTERSECT, GeometryOperation.PROJECT),
        (GeometryOperation.PROJECT, GeometryOperation.INTERSECT),
        (GeometryOperation.AREA, GeometryOperation.INTERSECT),
    ],
)
def test_result_operation_policy_must_match_operation(operation, wrong_operation, canonical, canon_policy, engine):
    wrong = op_policy(wrong_operation, canon_policy.precision_policy)
    kwargs = dict(
        operation_id="0" * 64,
        operation=operation,
        state=OperationState.UNRESOLVED,
        input_geometries=(canonical,),
        operation_policy=wrong,
        engine_identity=engine,
        reason_codes=("x",),
    )
    if operation is GeometryOperation.AREA:
        kwargs["area_policy"] = AreaPolicy()
    with pytest.raises(ValueError, match="operation_policy.operation"):
        GeometryOperationResult(**kwargs)


def test_empty_success_intersection_requires_allow_empty(canonical, canon_policy, engine):
    empty_policy = replace(canon_policy, empty_geometry_behavior=__import__("sitescore_spatial").EmptyGeometryBehavior.ALLOW_OPERATION_OUTPUT)
    empty = canonicalize_geometry(Polygon(), crs_identity=canonical.crs_identity, policy=empty_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty=False)
    oid = result_id(
        operation=GeometryOperation.INTERSECT,
        inputs=(canonical.semantic_geometry_id, canonical.semantic_geometry_id),
        operation_policy=policy,
        engine_id=engine.engine_identity_id,
        output=empty,
    )
    with pytest.raises(ValueError, match="allow_empty_result=True"):
        GeometryOperationResult(
            operation_id=oid,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical),
            operation_policy=policy,
            engine_identity=engine,
            output_geometry=empty,
        )


def test_empty_success_intersection_with_allow_empty_attaches_policy(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(2,2),(3,2),(3,3),(2,3),(2,2)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty=True)
    result = intersect_geometries(a, b, policy=policy, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.output_geometry is not None and result.output_geometry.is_empty
    assert result.operation_policy is policy
    assert result.operation_policy_id == policy.identity_id


def test_success_area_requires_area_policy(crs3857, canon_policy, engine):
    g = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="requires actual AreaPolicy"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.AREA,
            state=OperationState.SUCCESS,
            input_geometries=(g,),
            operation_policy=op,
            engine_identity=engine,
            numeric_value=1.0,
            unit="m2",
        )


def test_success_area_requires_measured_input_geometry(crs3857, canon_policy, engine):
    g = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="exact measured CanonicalGeometry"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.AREA,
            state=OperationState.SUCCESS,
            input_geometries=(),
            operation_policy=op,
            engine_identity=engine,
            area_policy=AreaPolicy(),
            numeric_value=1.0,
            unit="m2",
        )


def test_success_area_unit_must_match_area_policy(crs3857, canon_policy, engine):
    g = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="must match AreaPolicy.output_unit"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.AREA,
            state=OperationState.SUCCESS,
            input_geometries=(g,),
            operation_policy=op,
            engine_identity=engine,
            area_policy=AreaPolicy(),
            numeric_value=1.0,
            unit="km2",
        )


def test_success_area_geographic_crs_rejected(canonical, canon_policy, engine):
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="projected input CRS"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.AREA,
            state=OperationState.SUCCESS,
            input_geometries=(canonical,),
            operation_policy=op,
            engine_identity=engine,
            area_policy=AreaPolicy(),
            numeric_value=1.0,
            unit="m2",
        )


def test_official_area_carries_exact_policy_and_crs(crs3857, canon_policy, engine):
    g = canonicalize_geometry(Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    area_policy = AreaPolicy()
    result = area_of_projected_geometry(g, area_policy=area_policy, operation_policy=op, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.operation_policy is op
    assert result.area_policy is area_policy
    assert result.input_crs_identity is crs3857
    assert result.unit == area_policy.output_unit


def test_detached_transform_policy_id_constructor_api_removed(crs4326, crs3857, engine):
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    with pytest.raises(TypeError, match="policy_identity_id"):
        TransformPlan(
            plan_id=plan.plan_id,
            source_crs_identity=plan.source_crs_identity,
            target_crs_identity=plan.target_crs_identity,
            policy_identity_id=plan.policy_identity_id,
            engine_identity_id=plan.engine_identity_id,
            selected_pipeline_hash=plan.selected_pipeline_hash,
            selected_pipeline_definition=plan.selected_pipeline_definition,
            grid_identities=plan.grid_identities,
        )


def test_transform_policy_change_changes_plan_id_same_pipeline(crs4326, crs3857, engine):
    p1 = CRSTransformPolicy(policy_version="1.0")
    p2 = CRSTransformPolicy(policy_version="2.0")
    plan1, reasons1 = build_transform_plan(crs4326, crs3857, p1, engine)
    plan2, reasons2 = build_transform_plan(crs4326, crs3857, p2, engine)
    assert plan1 and plan2 and not reasons1 and not reasons2
    assert plan1.selected_pipeline_hash == plan2.selected_pipeline_hash
    assert plan1.transform_policy is p1
    assert plan2.transform_policy is p2
    assert plan1.policy_identity_id != plan2.policy_identity_id
    assert plan1.plan_id != plan2.plan_id


def test_official_project_result_retains_exact_transform_and_operation_policies(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    transform_policy = CRSTransformPolicy()
    operation_policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(
        source,
        target_crs="EPSG:3857",
        transform_policy=transform_policy,
        operation_policy=operation_policy,
        canonicalization_policy=canon_policy,
        engine=engine,
    )
    assert result.state is OperationState.SUCCESS
    assert result.operation_policy is operation_policy
    assert result.transform_plan is not None
    assert result.transform_plan.transform_policy is transform_policy
    assert result.transform_plan.policy_identity_id == transform_policy.identity_id


def test_operation_policy_version_changes_result_identity(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    p1 = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, version="1.0")
    p2 = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, version="2.0")
    r1 = intersect_geometries(a, b, policy=p1, canonicalization_policy=canon_policy, engine=engine)
    r2 = intersect_geometries(a, b, policy=p2, canonicalization_policy=canon_policy, engine=engine)
    assert r1.output_geometry.semantic_geometry_id == r2.output_geometry.semantic_geometry_id
    assert r1.operation_policy_id != r2.operation_policy_id
    assert r1.operation_id != r2.operation_id
