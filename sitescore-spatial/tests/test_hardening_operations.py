from dataclasses import replace

import pytest
from shapely.geometry import Polygon

from sitescore_spatial import (
    CRSTransformPolicy,
    GeometryCanonicalizationPolicy,
    GeometryOperation,
    OperationState,
    canonicalize_geometry,
    intersect_geometries,
    project_geometry,
)
from conftest import op_policy


def test_output_semantic_policy_change_changes_intersection_operation_id(crs4326, engine):
    p = Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)])
    q = Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)])
    in_policy = GeometryCanonicalizationPolicy(policy_version="1.0")
    a = canonicalize_geometry(p, crs_identity=crs4326, policy=in_policy, engine=engine)
    b = canonicalize_geometry(q, crs_identity=crs4326, policy=in_policy, engine=engine)
    op = op_policy(GeometryOperation.INTERSECT, in_policy.precision_policy)
    out1 = intersect_geometries(a, b, policy=op, canonicalization_policy=GeometryCanonicalizationPolicy(policy_version="1.0"), engine=engine)
    out2 = intersect_geometries(a, b, policy=op, canonicalization_policy=GeometryCanonicalizationPolicy(policy_version="2.0"), engine=engine)
    assert out1.output_geometry.canonical_wkb == out2.output_geometry.canonical_wkb
    assert out1.output_geometry.semantic_geometry_id != out2.output_geometry.semantic_geometry_id
    assert out1.operation_id != out2.operation_id


def test_intersection_input_order_still_invariant_after_output_binding(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    assert intersect_geometries(a,b,policy=op,canonicalization_policy=canon_policy,engine=engine).operation_id == intersect_geometries(b,a,policy=op,canonicalization_policy=canon_policy,engine=engine).operation_id


def test_projection_executes_exact_transformer_returned_by_single_resolver(monkeypatch, polygon, crs4326, canon_policy, engine):
    import sitescore_spatial.operations as operations
    from sitescore_spatial import build_crs_identity, build_transform_plan

    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    target = build_crs_identity("EPSG:3857")
    plan, reasons = build_transform_plan(crs4326, target, CRSTransformPolicy(), engine)
    assert plan is not None and not reasons

    calls = {"resolver": 0, "transform": 0}
    class ExactTransformer:
        def transform(self, x, y, errcheck=True):
            calls["transform"] += 1
            # Explicit deterministic fake selected execution semantics.
            return x + 1000.0, y + 2000.0

    def one_shot_resolver(*args, **kwargs):
        calls["resolver"] += 1
        return plan, ExactTransformer(), ()

    monkeypatch.setattr(operations, "resolve_transform_plan", one_shot_resolver)
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = operations.project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(), operation_policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.transform_plan_id == plan.plan_id
    assert calls["resolver"] == 1
    assert calls["transform"] > 0
    # If project_geometry independently reselected a generic TransformerGroup,
    # this deliberately fake transform would not be the executed output.
    out = operations.geometry_from_canonical(result.output_geometry)
    assert min(x for x, y in out.exterior.coords) > 1000


def test_transform_policy_change_changes_plan_and_result_identity(polygon, crs4326, canon_policy, engine):
    source = canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)
    op = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    a = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(policy_version="1.0"), operation_policy=op, canonicalization_policy=canon_policy, engine=engine)
    b = project_geometry(source, target_crs="EPSG:3857", transform_policy=CRSTransformPolicy(policy_version="2.0"), operation_policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert a.transform_plan_id != b.transform_plan_id
    assert a.operation_id != b.operation_id


def test_exact_plan_replay_unavailable_returns_none_not_generic_fallback(monkeypatch, crs4326, crs3857, engine):
    import sitescore_spatial.crs as crsmod
    from sitescore_spatial import CRSTransformPolicy, build_transform_plan
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan is not None and not reasons
    monkeypatch.setattr(crsmod.pyproj.Transformer, "from_pipeline", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no replay")))
    assert crsmod.transformer_from_plan(plan) is None
