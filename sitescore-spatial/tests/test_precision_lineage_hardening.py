from __future__ import annotations

from dataclasses import replace

import pytest
from shapely.geometry import Polygon

from sitescore_spatial import (
    AreaPolicy,
    CRSTransformPolicy,
    GeometryCanonicalizationPolicy,
    GeometryOperation,
    GeometryOperationPolicy,
    GeometryOperationResult,
    GeometryPrecisionPolicy,
    OperationState,
    area_of_projected_geometry,
    canonicalize_geometry,
    intersect_geometries,
    project_geometry,
)


def op_policy(operation, precision_policy, *, allow_empty=False, version="1.0"):
    return GeometryOperationPolicy(
        policy_id=f"{operation.value.lower()}-policy",
        policy_version=version,
        operation=operation,
        precision_policy=precision_policy,
        allow_empty_result=allow_empty,
    )


def alt_precision():
    return GeometryPrecisionPolicy(policy_version="2.0")


def test_detached_precision_policy_id_constructor_api_removed():
    precision = GeometryPrecisionPolicy()
    with pytest.raises(TypeError, match="precision_policy_id"):
        GeometryOperationPolicy(
            policy_id="intersect-policy",
            policy_version="1.0",
            operation=GeometryOperation.INTERSECT,
            precision_policy_id=precision.identity_id,
        )


def test_precision_policy_change_changes_operation_policy_identity():
    p1 = GeometryPrecisionPolicy(policy_version="1.0")
    p2 = GeometryPrecisionPolicy(policy_version="2.0")
    o1 = op_policy(GeometryOperation.INTERSECT, p1)
    o2 = op_policy(GeometryOperation.INTERSECT, p2)
    assert o1.precision_policy is p1
    assert o2.precision_policy is p2
    assert o1.precision_policy_id != o2.precision_policy_id
    assert o1.identity_id != o2.identity_id


def test_intersection_rejects_operation_vs_canonicalization_precision_mismatch(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    wrong = op_policy(GeometryOperation.INTERSECT, alt_precision())
    with pytest.raises(ValueError, match="INTERSECT operation precision must match canonicalization precision"):
        intersect_geometries(a, b, policy=wrong, canonicalization_policy=canon_policy, engine=engine)


def test_intersection_same_precision_succeeds(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    result = intersect_geometries(a, b, policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.output_geometry is not None
    assert result.operation_policy.precision_policy.identity_id == result.output_geometry.canonicalization_policy.precision_policy.identity_id


def test_empty_intersection_keeps_precision_identity(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(2,2),(3,2),(3,3),(2,3),(2,2)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty=True)
    result = intersect_geometries(a, b, policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.output_geometry is not None and result.output_geometry.is_empty
    assert result.output_geometry.canonicalization_policy.empty_geometry_behavior.value == "ALLOW_OPERATION_OUTPUT"
    assert result.output_geometry.canonicalization_policy.precision_policy.identity_id == canon_policy.precision_policy.identity_id
    assert result.operation_policy.precision_policy.identity_id == canon_policy.precision_policy.identity_id


def test_project_rejects_operation_vs_canonicalization_precision_mismatch(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    wrong = op_policy(GeometryOperation.PROJECT, alt_precision())
    with pytest.raises(ValueError, match="PROJECT operation precision must match canonicalization precision"):
        project_geometry(
            source,
            target_crs="EPSG:3857",
            transform_policy=CRSTransformPolicy(),
            operation_policy=wrong,
            canonicalization_policy=canon_policy,
            engine=engine,
        )


def test_official_project_result_precision_matches_output(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(
        source,
        target_crs="EPSG:3857",
        transform_policy=CRSTransformPolicy(),
        operation_policy=op,
        canonicalization_policy=canon_policy,
        engine=engine,
    )
    assert result.state is OperationState.SUCCESS
    assert result.output_geometry is not None
    assert result.operation_policy.precision_policy.identity_id == result.output_geometry.canonicalization_policy.precision_policy.identity_id


def test_public_success_geometry_result_rejects_precision_mismatch(canonical, canon_policy, engine):
    wrong = op_policy(GeometryOperation.INTERSECT, alt_precision())
    with pytest.raises(ValueError, match="operation precision must match actual input geometry precision"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical),
            operation_policy=wrong,
            engine_identity=engine,
            output_geometry=canonical,
        )


def test_area_rejects_operation_precision_inconsistent_with_measured_geometry(crs3857, canon_policy, engine):
    geometry = canonicalize_geometry(Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    wrong = op_policy(GeometryOperation.AREA, alt_precision())
    with pytest.raises(ValueError, match="AREA operation precision must match measured input geometry precision"):
        area_of_projected_geometry(geometry, area_policy=AreaPolicy(), operation_policy=wrong, engine=engine)


def test_public_area_result_rejects_precision_evidence_mismatch(crs3857, canon_policy, engine):
    geometry = canonicalize_geometry(Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(TypeError, match="input_geometry_precision_policy"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.AREA,
            state=OperationState.SUCCESS,
            input_geometries=(geometry,),
            operation_policy=op,
            engine_identity=engine,
            input_geometry_precision_policy=alt_precision(),
            area_policy=AreaPolicy(),
            numeric_value=100.0,
            unit="m2",
        )


def test_official_area_carries_exact_input_precision(crs3857, canon_policy, engine):
    geometry = canonicalize_geometry(Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    result = area_of_projected_geometry(geometry, area_policy=AreaPolicy(), operation_policy=op, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.input_geometry_precision_policy is geometry.canonicalization_policy.precision_policy
    assert result.operation_policy.precision_policy.identity_id == result.input_geometry_precision_policy.identity_id


def test_geometry_precision_policy_change_changes_area_result_identity(crs3857, canon_policy, engine):
    geometry1 = canonicalize_geometry(Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    alt_canon = replace(canon_policy, precision_policy=alt_precision())
    geometry2 = canonicalize_geometry(Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=crs3857, policy=alt_canon, engine=engine)
    r1 = area_of_projected_geometry(geometry1, area_policy=AreaPolicy(), operation_policy=op_policy(GeometryOperation.AREA, canon_policy.precision_policy), engine=engine)
    r2 = area_of_projected_geometry(geometry2, area_policy=AreaPolicy(), operation_policy=op_policy(GeometryOperation.AREA, alt_canon.precision_policy), engine=engine)
    assert r1.numeric_value == r2.numeric_value
    assert r1.operation_policy.precision_policy_id != r2.operation_policy.precision_policy_id
    assert r1.operation_id != r2.operation_id
