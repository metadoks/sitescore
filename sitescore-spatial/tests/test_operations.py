from shapely.geometry import Polygon

from sitescore_spatial import (
    AreaPolicy,
    CRSTransformPolicy,
    GeometryOperation,
    OperationState,
    area_of_projected_geometry,
    canonicalize_geometry,
    intersect_geometries,
    project_geometry,
)
from conftest import op_policy


def test_intersection_commutative_identity(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    ab = intersect_geometries(a,b,policy=policy,canonicalization_policy=canon_policy,engine=engine)
    ba = intersect_geometries(b,a,policy=policy,canonicalization_policy=canon_policy,engine=engine)
    assert ab.state is OperationState.SUCCESS
    assert ab.operation_id == ba.operation_id
    assert ab.output_geometry.canonical_wkb == ba.output_geometry.canonical_wkb


def test_intersection_policy_change_changes_identity(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    p1 = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, version="1.0")
    p2 = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, version="2.0")
    assert intersect_geometries(a,b,policy=p1,canonicalization_policy=canon_policy,engine=engine).operation_id != intersect_geometries(a,b,policy=p2,canonicalization_policy=canon_policy,engine=engine).operation_id


def test_empty_intersection_explicit_success_when_allowed(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(2,0),(3,0),(3,1),(2,1),(2,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty=True)
    result = intersect_geometries(a,b,policy=policy,canonicalization_policy=canon_policy,engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.output_geometry.is_empty


def test_empty_intersection_unresolved_when_not_allowed(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(2,0),(3,0),(3,1),(2,1),(2,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy, allow_empty=False)
    result = intersect_geometries(a,b,policy=policy,canonicalization_policy=canon_policy,engine=engine)
    assert result.state is OperationState.UNRESOLVED
    assert result.numeric_value is None


def test_intersection_crs_mismatch_explicit(crs4326, crs3857, canon_policy, engine):
    p = Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)])
    a = canonicalize_geometry(p, crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(p, crs_identity=crs3857, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    result = intersect_geometries(a,b,policy=policy,canonicalization_policy=canon_policy,engine=engine)
    assert result.state is OperationState.INCOMPATIBLE


def test_project_geometry_success(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=policy, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.output_geometry.crs_identity.is_projected
    assert result.transform_plan_id is not None


def test_target_crs_change_changes_project_identity(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    a = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=policy, canonicalization_policy=canon_policy, engine=engine)
    b = project_geometry(source, target_crs="EPSG:32635", transform_policy=CRSTransformPolicy(), operation_policy=policy, canonicalization_policy=canon_policy, engine=engine)
    assert a.operation_id != b.operation_id


def test_lat_lon_swap_out_of_range_is_not_silent(crs4326, canon_policy, engine):
    # Correct semantics would be lon=120, lat=40. Swapping gives lat=120, which PROJ rejects with errcheck=True.
    swapped = Polygon([(40,120),(41,120),(41,121),(40,121),(40,120)])
    source = canonicalize_geometry(swapped, crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=policy, canonicalization_policy=canon_policy, engine=engine)
    assert result.state in {OperationState.INVALID_INPUT, OperationState.ENGINE_ERROR}


def test_area_requires_projected_crs(polygon, crs4326, canon_policy, engine):
    geometry = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    result = area_of_projected_geometry(geometry, area_policy=AreaPolicy(), operation_policy=policy, engine=engine)
    assert result.state is OperationState.INCOMPATIBLE
    assert result.numeric_value is None


def test_projected_area_finite_nonnegative(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    project_policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    projected = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=project_policy, canonicalization_policy=canon_policy, engine=engine)
    area_policy = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    result = area_of_projected_geometry(projected.output_geometry, area_policy=AreaPolicy(), operation_policy=area_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.numeric_value > 0
    assert result.unit == "m2"


def test_area_policy_version_changes_operation_identity(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    projected = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy), canonicalization_policy=canon_policy, engine=engine).output_geometry
    op = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    a = area_of_projected_geometry(projected, area_policy=AreaPolicy(policy_version="1.0"), operation_policy=op, engine=engine)
    b = area_of_projected_geometry(projected, area_policy=AreaPolicy(policy_version="2.0"), operation_policy=op, engine=engine)
    assert a.operation_id != b.operation_id


def test_transform_policy_version_changes_project_identity(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    operation = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    a = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(policy_version="1.0"), operation_policy=operation, canonicalization_policy=canon_policy, engine=engine)
    b = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(policy_version="2.0"), operation_policy=operation, canonicalization_policy=canon_policy, engine=engine)
    assert a.operation_id != b.operation_id


def test_axis_order_alternative_is_rejected():
    import pytest
    with pytest.raises(TypeError, match="AxisOrderPolicy"):
        CRSTransformPolicy(axis_order_policy="AUTHORITY_ORDER")


def test_ballpark_transform_policy_rejected():
    import pytest
    with pytest.raises(ValueError, match="ballpark"):
        CRSTransformPolicy(allow_ballpark=True)


def test_canonical_transform_policy_requires_network_disabled():
    import pytest
    with pytest.raises(ValueError, match="network disabled"):
        CRSTransformPolicy(network_enabled=True)


def test_intersection_engine_failure_explicit(monkeypatch, crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    import sitescore_spatial.operations as operations
    def boom(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(operations.shapely, "intersection", boom)
    result = operations.intersect_geometries(a,b,policy=policy,canonicalization_policy=canon_policy,engine=engine)
    assert result.state is OperationState.ENGINE_ERROR
    assert result.numeric_value is None
