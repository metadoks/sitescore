from __future__ import annotations

import json
from dataclasses import replace

import pytest
from pyproj import CRS
from shapely.geometry import Polygon

from sitescore_spatial import (
    AreaPolicy,
    AxisSemantic,
    CRSIdentity,
    CRSTransformPolicy,
    GeometryEngineIdentity,
    GeometryOperation,
    GeometryOperationPolicy,
    GeometryOperationResult,
    OperationState,
    area_of_projected_geometry,
    build_crs_identity,
    build_geometry_engine_identity,
    build_transform_plan,
    canonicalize_geometry,
    intersect_geometries,
    project_geometry,
)
from sitescore_spatial.hashing import semantic_hash


def _crs_record(*, authority, authority_code, canonical_definition, axis_semantics, is_geographic, is_projected):
    definition_hash = semantic_hash(json.loads(canonical_definition))
    return {
        "authority": authority,
        "authority_code": authority_code,
        "canonical_definition_hash": definition_hash,
        "axis_semantics": [a.semantic_record() for a in axis_semantics],
        "is_geographic": is_geographic,
        "is_projected": is_projected,
        "definition_policy_id": "projjson",
        "definition_policy_version": "1.0",
    }


def _fake_engine(actual: GeometryEngineIdentity, *, suffix="-attestation-test") -> GeometryEngineIdentity:
    record = actual.semantic_record()
    record["geometry_library_version"] = record["geometry_library_version"] + suffix
    return GeometryEngineIdentity(engine_identity_id=semantic_hash(record), **record)


def _op_policy(operation, precision):
    return GeometryOperationPolicy(
        policy_id=f"{operation.value.lower()}_v1",
        policy_version="1.0",
        operation=operation,
        precision_policy=precision,
        allow_empty_result=False,
    )


def _result_id(*, operation, input_geometries, operation_policy, engine, output=None, plan=None, state=OperationState.SUCCESS, reasons=()):
    input_ids = tuple(sorted(g.semantic_geometry_id for g in input_geometries))
    input_crs = input_geometries[0].crs_identity if len(input_geometries) == 1 else None
    input_precision = input_geometries[0].canonicalization_policy.precision_policy if len(input_geometries) == 1 else None
    return semantic_hash({
        "operation": operation.value,
        "inputs": list(input_ids),
        "operation_policy_id": operation_policy.identity_id,
        "area_policy_id": None,
        "engine_id": engine.engine_identity_id,
        "input_crs_identity_id": input_crs.crs_identity_id if input_crs else None,
        "input_geometry_precision_policy_id": input_precision.identity_id if input_precision else None,
        "transform_plan_id": plan.plan_id if plan else None,
        "output_semantic_geometry_id": output.semantic_geometry_id if output else None,
        "numeric_value": None,
        "unit": None,
        "state": state.value,
        "reason_codes": sorted(reasons),
    })


def test_fictional_projected_metre_crs_claim_rejected(crs4326):
    metres = (
        AxisSemantic("Easting", "east", "metre", 1.0),
        AxisSemantic("Northing", "north", "metre", 1.0),
    )
    record = _crs_record(
        authority=None,
        authority_code=None,
        canonical_definition=crs4326.canonical_definition,
        axis_semantics=metres,
        is_geographic=False,
        is_projected=True,
    )
    with pytest.raises(ValueError, match="axis_semantics|is_projected|is_geographic"):
        CRSIdentity(
            crs_identity_id=semantic_hash(record),
            authority=None,
            authority_code=None,
            canonical_definition=crs4326.canonical_definition,
            axis_semantics=metres,
            is_geographic=False,
            is_projected=True,
        )


def test_epsg4326_definition_claimed_projected_rejected(crs4326):
    record = _crs_record(
        authority=crs4326.authority,
        authority_code=crs4326.authority_code,
        canonical_definition=crs4326.canonical_definition,
        axis_semantics=crs4326.axis_semantics,
        is_geographic=False,
        is_projected=True,
    )
    with pytest.raises(ValueError, match="is_geographic|is_projected"):
        CRSIdentity(
            crs_identity_id=semantic_hash(record),
            authority=crs4326.authority,
            authority_code=crs4326.authority_code,
            canonical_definition=crs4326.canonical_definition,
            axis_semantics=crs4326.axis_semantics,
            is_geographic=False,
            is_projected=True,
        )


def test_epsg4326_definition_claimed_metre_axes_rejected(crs4326):
    metres = tuple(replace(a, unit_name="metre", unit_conversion_factor=1.0) for a in crs4326.axis_semantics)
    record = _crs_record(
        authority=crs4326.authority,
        authority_code=crs4326.authority_code,
        canonical_definition=crs4326.canonical_definition,
        axis_semantics=metres,
        is_geographic=True,
        is_projected=False,
    )
    with pytest.raises(ValueError, match="axis_semantics"):
        CRSIdentity(
            crs_identity_id=semantic_hash(record),
            authority=crs4326.authority,
            authority_code=crs4326.authority_code,
            canonical_definition=crs4326.canonical_definition,
            axis_semantics=metres,
            is_geographic=True,
            is_projected=False,
        )


def test_authority_code_definition_mismatch_rejected(crs4326):
    record = _crs_record(
        authority="EPSG",
        authority_code="3857",
        canonical_definition=crs4326.canonical_definition,
        axis_semantics=crs4326.axis_semantics,
        is_geographic=True,
        is_projected=False,
    )
    with pytest.raises(ValueError, match="authority/code does not match"):
        CRSIdentity(
            crs_identity_id=semantic_hash(record),
            authority="EPSG",
            authority_code="3857",
            canonical_definition=crs4326.canonical_definition,
            axis_semantics=crs4326.axis_semantics,
            is_geographic=True,
            is_projected=False,
        )


def test_crs_definition_key_order_noise_is_nonsemantic(crs4326):
    obj = json.loads(crs4326.canonical_definition)
    noisy = json.dumps(dict(reversed(list(obj.items()))), indent=2)
    rebuilt = CRSIdentity(
        crs_identity_id=crs4326.crs_identity_id,
        authority=crs4326.authority,
        authority_code=crs4326.authority_code,
        canonical_definition=noisy,
        axis_semantics=crs4326.axis_semantics,
        is_geographic=crs4326.is_geographic,
        is_projected=crs4326.is_projected,
    )
    assert rebuilt.crs_identity_id == crs4326.crs_identity_id
    assert rebuilt.canonical_definition == crs4326.canonical_definition


def test_crs_definition_change_changes_identity(crs4326, crs3857):
    assert crs4326.canonical_definition_hash != crs3857.canonical_definition_hash
    assert crs4326.crs_identity_id != crs3857.crs_identity_id


def test_actual_epsg4326_area_cannot_be_m2(canonical, canon_policy, engine):
    result = area_of_projected_geometry(
        canonical,
        area_policy=AreaPolicy(),
        operation_policy=_op_policy(GeometryOperation.AREA, canon_policy.precision_policy),
        engine=engine,
    )
    assert result.state is OperationState.INCOMPATIBLE
    assert result.numeric_value is None
    assert result.reason_codes == ("projected_crs_required",)


def test_actual_metre_projected_area_remains_valid(crs3857, canon_policy, engine):
    geometry = canonicalize_geometry(
        Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]),
        crs_identity=crs3857,
        policy=canon_policy,
        engine=engine,
    )
    result = area_of_projected_geometry(
        geometry,
        area_policy=AreaPolicy(),
        operation_policy=_op_policy(GeometryOperation.AREA, canon_policy.precision_policy),
        engine=engine,
    )
    assert result.state is OperationState.SUCCESS
    assert result.numeric_value == pytest.approx(100.0)
    assert result.unit == "m2"
    assert result.engine_identity == engine


def test_success_intersect_result_engine_must_match_output(canonical, canon_policy, engine):
    fake = _fake_engine(engine)
    op = _op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="engine must match output geometry engine"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical),
            operation_policy=op,
            engine_identity=fake,
            output_geometry=canonical,
        )


def test_success_project_result_engine_must_match_plan(canonical, crs3857, canon_policy, engine):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan is not None and not reasons
    output = canonicalize_geometry(
        Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]),
        crs_identity=crs3857,
        policy=canon_policy,
        engine=engine,
    )
    fake = _fake_engine(engine)
    op = _op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="transform plan engine mismatch"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.PROJECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical,),
            operation_policy=op,
            engine_identity=fake,
            transform_plan=plan,
            output_geometry=output,
        )


def test_success_project_result_engine_must_match_output_even_if_plan_matches_fake(canonical, crs3857, canon_policy, engine):
    actual_plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert actual_plan is not None and not reasons
    fake = _fake_engine(engine)
    plan_record = {
        "source_crs_identity_id": actual_plan.source_crs_identity_id,
        "target_crs_identity_id": actual_plan.target_crs_identity_id,
        "policy_identity_id": actual_plan.transform_policy.identity_id,
        "engine_identity_id": fake.engine_identity_id,
        "selected_pipeline_hash": actual_plan.selected_pipeline_hash,
        "grid_identities": list(actual_plan.grid_identities),
    }
    fake_plan = replace(actual_plan, plan_id=semantic_hash(plan_record), engine_identity=fake)
    output = canonicalize_geometry(
        Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), crs_identity=crs3857, policy=canon_policy, engine=engine
    )
    op = _op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    with pytest.raises(ValueError, match="engine must match output geometry engine"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.PROJECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical,),
            operation_policy=op,
            engine_identity=fake,
            transform_plan=fake_plan,
            output_geometry=output,
        )


def test_official_intersection_result_engine_coherence(canonical, canon_policy, engine):
    op = _op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    result = intersect_geometries(canonical, canonical, policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert result.state is OperationState.SUCCESS
    assert result.engine_identity == engine
    assert result.engine_identity_id == result.output_geometry.engine_identity_id


def test_official_project_result_engine_plan_output_coherence(canonical, crs3857, canon_policy, engine):
    op = _op_policy(GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(
        canonical,
        target_crs="EPSG:3857",
        transform_policy=CRSTransformPolicy(),
        operation_policy=op,
        canonicalization_policy=canon_policy,
        engine=engine,
    )
    assert result.state is OperationState.SUCCESS
    assert result.engine_identity == engine
    assert result.engine_identity_id == result.transform_plan.engine_identity_id
    assert result.engine_identity_id == result.output_geometry.engine_identity_id


def test_detached_result_engine_identity_constructor_removed(canonical, canon_policy, engine):
    op = _op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    with pytest.raises(TypeError, match="engine_identity_id"):
        GeometryOperationResult(
            operation_id="0" * 64,
            operation=GeometryOperation.INTERSECT,
            state=OperationState.SUCCESS,
            input_geometries=(canonical, canonical),
            operation_policy=op,
            engine_identity_id=engine.engine_identity_id,
            output_geometry=canonical,
        )

def test_non_authority_custom_projected_crs_remains_verifiable(canon_policy, engine):
    custom = build_crs_identity("+proj=aeqd +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs +type=crs")
    assert custom.authority is None and custom.authority_code is None
    assert custom.is_projected and not custom.is_geographic
    geometry = canonicalize_geometry(
        Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]), crs_identity=custom, policy=canon_policy, engine=engine
    )
    result = area_of_projected_geometry(
        geometry,
        area_policy=AreaPolicy(),
        operation_policy=_op_policy(GeometryOperation.AREA, canon_policy.precision_policy),
        engine=engine,
    )
    assert result.state is OperationState.SUCCESS
    assert result.numeric_value == pytest.approx(100.0)

def test_detached_canonical_definition_hash_constructor_removed(crs4326):
    with pytest.raises(TypeError, match="canonical_definition_hash"):
        CRSIdentity(
            crs_identity_id=crs4326.crs_identity_id,
            authority=crs4326.authority,
            authority_code=crs4326.authority_code,
            canonical_definition_hash=crs4326.canonical_definition_hash,
            axis_semantics=crs4326.axis_semantics,
            is_geographic=crs4326.is_geographic,
            is_projected=crs4326.is_projected,
        )


def test_operation_engine_semantics_change_result_identity(canonical, canon_policy, engine):
    fake = _fake_engine(engine, suffix="-v2")
    op = _op_policy(GeometryOperation.INTERSECT, canon_policy.precision_policy)
    reasons = ("synthetic_engine_failure",)
    id_actual = _result_id(
        operation=GeometryOperation.INTERSECT,
        input_geometries=(canonical,),
        operation_policy=op,
        engine=engine,
        state=OperationState.ENGINE_ERROR,
        reasons=reasons,
    )
    id_fake = _result_id(
        operation=GeometryOperation.INTERSECT,
        input_geometries=(canonical,),
        operation_policy=op,
        engine=fake,
        state=OperationState.ENGINE_ERROR,
        reasons=reasons,
    )
    actual_result = GeometryOperationResult(
        operation_id=id_actual,
        operation=GeometryOperation.INTERSECT,
        state=OperationState.ENGINE_ERROR,
        input_geometries=(canonical,),
        operation_policy=op,
        engine_identity=engine,
        reason_codes=reasons,
    )
    fake_result = GeometryOperationResult(
        operation_id=id_fake,
        operation=GeometryOperation.INTERSECT,
        state=OperationState.ENGINE_ERROR,
        input_geometries=(canonical,),
        operation_policy=op,
        engine_identity=fake,
        reason_codes=reasons,
    )
    assert actual_result.operation_id != fake_result.operation_id
