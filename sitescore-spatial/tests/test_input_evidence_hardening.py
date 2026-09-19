from __future__ import annotations

from dataclasses import replace

import pytest
from shapely.geometry import Polygon

from sitescore_spatial import (
    AreaPolicy,
    BoundaryGeometryArtifact,
    CRSTransformPolicy,
    CanonicalGeometry,
    GeographyIdentity,
    GeometryCanonicalizationPolicy,
    GeometryOperation,
    GeometryOperationPolicy,
    GeometryOperationResult,
    GeometryPrecisionPolicy,
    OperationState,
    area_of_projected_geometry,
    build_boundary_geometry_artifact,
    build_crs_identity,
    build_geometry_source_identity,
    build_transform_plan,
    canonicalize_geometry,
    intersect_geometries,
    project_geometry,
)
from sitescore_spatial.operations import _result_id


class FakeCRS:
    crs_identity_id = "1" * 64


class FakeCanonicalizationPolicy:
    identity_id = "2" * 64
    precision_policy = GeometryPrecisionPolicy()
    empty_geometry_behavior = __import__("sitescore_spatial").EmptyGeometryBehavior.REJECT


class FakePrecisionPolicy:
    identity_id = "3" * 64


class FakeGeography:
    identity_id = "4" * 64


class FakeSource:
    source_identity_id = "5" * 64
    source_crs_identity = FakeCRS()


class FakeCanonicalGeometry:
    semantic_geometry_id = "6" * 64
    is_empty = False


class FakeOperation:
    value = "INTERSECT"


class FakeOutputGeometry:
    semantic_geometry_id = "7" * 64


def op_policy(operation, precision, *, allow_empty=False):
    return GeometryOperationPolicy(
        policy_id=f"{operation.value.lower()}-input-evidence-v1",
        policy_version="1.0",
        operation=operation,
        precision_policy=precision,
        allow_empty_result=allow_empty,
    )


def make_artifact(*, geography, source, canonical, canon_policy, engine, now):
    return build_boundary_geometry_artifact(
        geography_identity=geography,
        geometry_role="ADMIN_BOUNDARY",
        source_identity=source,
        canonical_geometry=canonical,
        parser_id="test-parser",
        parser_version="1.0",
        canonicalization_policy=canon_policy,
        engine=engine,
        source_refs=("source-ref",),
        generated_at=now,
    )


# SPATIAL-H013 -- concrete nested contract types

def test_canonical_geometry_rejects_duck_typed_crs(canonical):
    with pytest.raises(TypeError, match="crs_identity must be CRSIdentity"):
        replace(canonical, crs_identity=FakeCRS())


def test_canonical_geometry_rejects_duck_typed_canonicalization_policy(canonical):
    with pytest.raises(TypeError, match="canonicalization_policy must be GeometryCanonicalizationPolicy"):
        replace(canonical, canonicalization_policy=FakeCanonicalizationPolicy())


def test_geometry_source_identity_rejects_fake_source_crs(crs4326):
    source = build_geometry_source_identity(
        provider="provider", dataset="dataset", release="2026-01-01", vintage="2025",
        schema_version="1", source_crs_identity=crs4326, raw_content=b"x",
    )
    with pytest.raises(TypeError, match="source_crs_identity must be CRSIdentity"):
        replace(source, source_crs_identity=FakeCRS())


@pytest.mark.parametrize(
    ("field_name", "fake_value", "message"),
    [
        ("geography_identity", FakeGeography(), "geography_identity must be GeographyIdentity"),
        ("source_identity", FakeSource(), "source_identity must be GeometrySourceIdentity"),
        ("canonical_geometry", FakeCanonicalGeometry(), "canonical_geometry must be CanonicalGeometry"),
        ("canonical_crs_identity", FakeCRS(), "canonical_crs_identity must be CRSIdentity"),
    ],
)
def test_boundary_artifact_rejects_duck_typed_nested_contracts(
    field_name, fake_value, message, geography, source, canonical, canon_policy, engine, now
):
    artifact = make_artifact(
        geography=geography, source=source, canonical=canonical, canon_policy=canon_policy, engine=engine, now=now
    )
    with pytest.raises(TypeError, match=message):
        replace(artifact, **{field_name: fake_value})


def test_canonicalization_policy_rejects_fake_precision_policy():
    with pytest.raises(TypeError, match="precision_policy must be GeometryPrecisionPolicy"):
        GeometryCanonicalizationPolicy(precision_policy=FakePrecisionPolicy())


def test_operation_policy_rejects_fake_operation(canon_policy):
    with pytest.raises(TypeError, match="operation must be GeometryOperation"):
        GeometryOperationPolicy(
            policy_id="fake-operation",
            policy_version="1.0",
            operation=FakeOperation(),
            precision_policy=canon_policy.precision_policy,
        )


def test_operation_result_rejects_fake_output_geometry(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(TypeError, match="output_geometry must be CanonicalGeometry"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical),
            operation_policy=policy,
            engine_identity=engine,
            output_geometry=FakeOutputGeometry(),
        )


# SPATIAL-H014 -- actual operation input evidence

def test_detached_input_geometry_ids_constructor_api_removed(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(TypeError, match="input_geometry_ids"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.UNRESOLVED,
            input_geometries=(canonical,),
            input_geometry_ids=(canonical.semantic_geometry_id,),
            operation_policy=policy,
            engine_identity=engine,
            reason_codes=("x",),
        )


def test_success_intersect_requires_actual_two_inputs(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="exactly two actual input geometries"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(),
            operation_policy=policy,
            engine_identity=engine,
            output_geometry=canonical,
        )
    with pytest.raises(ValueError, match="exactly two actual input geometries"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical,),
            operation_policy=policy,
            engine_identity=engine,
            output_geometry=canonical,
        )


def test_official_intersect_retains_actual_inputs_and_commutative_identity(crs4326, canon_policy, engine):
    a = canonicalize_geometry(Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    b = canonicalize_geometry(Polygon([(1,1),(3,1),(3,3),(1,3),(1,1)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    ab = intersect_geometries(a, b, policy=policy, canonicalization_policy=canon_policy, engine=engine)
    ba = intersect_geometries(b, a, policy=policy, canonicalization_policy=canon_policy, engine=engine)
    assert ab.state is OperationState.SUCCESS and ba.state is OperationState.SUCCESS
    assert ab.input_geometries == (a, b)
    assert ba.input_geometries == (b, a)
    assert ab.input_geometry_ids == ba.input_geometry_ids
    assert ab.operation_id == ba.operation_id


def test_intersect_foreign_crs_pair_never_yields_success(canonical, crs3857, canon_policy, engine):
    other = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    result = intersect_geometries(canonical, other, policy=policy, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.INCOMPATIBLE
    assert result.input_geometries == (canonical, other)


def test_success_project_requires_actual_input_geometry(canonical, crs3857, canon_policy, engine):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan is not None and not reasons
    output = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="exactly one actual input geometry"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.PROJECT,
            state=OperationState.SUCCESS,
            input_geometries=(),
            operation_policy=policy,
            engine_identity=engine,
            transform_plan=plan,
            output_geometry=output,
        )


def test_project_plan_source_must_match_actual_input_geometry(canonical, crs3857, canon_policy, engine):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan is not None and not reasons
    foreign_input = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    output = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="source CRS mismatch"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.PROJECT,
            state=OperationState.SUCCESS,
            input_geometries=(foreign_input,),
            operation_policy=policy,
            engine_identity=engine,
            transform_plan=plan,
            output_geometry=output,
        )


def test_official_project_retains_exact_source_geometry(canonical, canon_policy, engine):
    policy = op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(
        canonical,
        target_crs="EPSG:3857",
        transform_policy=CRSTransformPolicy(),
        operation_policy=policy,
        canonicalization_policy=canon_policy,
        engine=engine,
    )
    assert result.state is OperationState.SUCCESS
    assert result.input_geometries == (canonical,)
    assert result.input_geometries[0] is canonical
    assert result.input_crs_identity is canonical.crs_identity


def test_success_area_requires_measured_canonical_geometry(crs3857, canon_policy, engine):
    policy = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="exact measured CanonicalGeometry"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.AREA,
            state=OperationState.SUCCESS,
            input_geometries=(),
            operation_policy=policy,
            engine_identity=engine,
            area_policy=AreaPolicy(),
            numeric_value=1.0,
            unit="m2",
        )


def test_detached_area_input_crs_lineage_constructor_removed(crs3857, canon_policy, engine):
    geometry = canonicalize_geometry(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    with pytest.raises(TypeError, match="input_crs_identity"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.AREA,
            state=OperationState.SUCCESS,
            input_geometries=(geometry,),
            input_crs_identity=crs3857,
            operation_policy=policy,
            engine_identity=engine,
            area_policy=AreaPolicy(),
            numeric_value=1.0,
            unit="m2",
        )


def test_official_area_retains_exact_measured_geometry(crs3857, canon_policy, engine):
    geometry = canonicalize_geometry(Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.AREA, canon_policy.precision_policy)
    result = area_of_projected_geometry(geometry, area_policy=AreaPolicy(), operation_policy=policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.input_geometries == (geometry,)
    assert result.input_geometries[0] is geometry
    assert result.input_crs_identity is geometry.crs_identity
    assert result.input_geometry_precision_policy is geometry.canonicalization_policy.precision_policy


def test_input_geometry_semantics_change_operation_identity(canonical, crs4326, canon_policy, engine):
    other = canonicalize_geometry(Polygon([(10,10),(11,10),(11,11),(10,11),(10,10)]), crs_identity=crs4326, policy=canon_policy, engine=engine)
    policy = op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    reasons = ("synthetic_failure",)
    id_a = _result_id(
        operation=GeometryOperation.INTERSECT,
        input_geometries=(canonical,),
        operation_policy=policy,
        engine=engine,
        state=OperationState.ENGINE_ERROR,
        reasons=reasons,
    )
    id_b = _result_id(
        operation=GeometryOperation.INTERSECT,
        input_geometries=(other,),
        operation_policy=policy,
        engine=engine,
        state=OperationState.ENGINE_ERROR,
        reasons=reasons,
    )
    assert id_a != id_b
