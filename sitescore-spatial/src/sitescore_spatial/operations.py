from __future__ import annotations

import math

import shapely
from shapely.ops import transform as shapely_transform

from .canonicalization import canonicalize_geometry, geometry_from_canonical, operation_output_canonicalization_policy
from .contracts import (
    AreaPolicy,
    CRSTransformPolicy,
    CanonicalGeometry,
    GeometryCanonicalizationPolicy,
    GeometryEngineIdentity,
    GeometryOperationPolicy,
    GeometryOperationResult,
    TransformPlan,
)
from .crs import _crs_from_identity, build_crs_identity, resolve_transform_plan
from .enums import GeometryOperation, OperationState
from .hashing import semantic_hash
from .identity import attest_actual_geometry_engine


def _result_id(*, operation, input_geometries, operation_policy, engine, transform_plan=None, area_policy=None, output_geometry=None, numeric_value=None, unit=None, state, reasons=()):
    input_ids = tuple(sorted(g.semantic_geometry_id for g in input_geometries))
    input_crs_identity = input_geometries[0].crs_identity if len(input_geometries) == 1 else None
    input_precision = input_geometries[0].canonicalization_policy.precision_policy if len(input_geometries) == 1 else None
    return semantic_hash({
        "operation": operation.value,
        "inputs": list(input_ids),
        "operation_policy_id": operation_policy.identity_id,
        "area_policy_id": area_policy.identity_id if area_policy is not None else None,
        "engine_id": engine.engine_identity_id,
        "input_crs_identity_id": input_crs_identity.crs_identity_id if input_crs_identity is not None else None,
        "input_geometry_precision_policy_id": input_precision.identity_id if input_precision is not None else None,
        "transform_plan_id": transform_plan.plan_id if transform_plan is not None else None,
        "output_semantic_geometry_id": output_geometry.semantic_geometry_id if output_geometry is not None else None,
        "numeric_value": numeric_value,
        "unit": unit,
        "state": state.value,
        "reason_codes": sorted(reasons),
    })


def _result(*, operation, state, input_geometries, operation_policy, engine, transform_plan=None, area_policy=None, output_geometry=None, numeric_value=None, unit=None, reasons=()):
    inputs = tuple(input_geometries)
    return GeometryOperationResult(
        operation_id=_result_id(
            operation=operation,
            input_geometries=inputs,
            operation_policy=operation_policy,
            engine=engine,
            transform_plan=transform_plan,
            area_policy=area_policy,
            output_geometry=output_geometry,
            numeric_value=numeric_value,
            unit=unit,
            state=state,
            reasons=reasons,
        ),
        operation=operation,
        state=state,
        input_geometries=inputs,
        operation_policy=operation_policy,
        engine_identity=engine,
        transform_plan=transform_plan,
        area_policy=area_policy,
        output_geometry=output_geometry,
        numeric_value=numeric_value,
        unit=unit,
        reason_codes=tuple(reasons),
    )

def intersect_geometries(a: CanonicalGeometry, b: CanonicalGeometry, *, policy: GeometryOperationPolicy, canonicalization_policy: GeometryCanonicalizationPolicy, engine: GeometryEngineIdentity) -> GeometryOperationResult:
    attest_actual_geometry_engine(engine)
    input_geometries = (a, b)
    if policy.operation is not GeometryOperation.INTERSECT:
        raise ValueError("operation policy must be INTERSECT")
    if policy.precision_policy.identity_id != canonicalization_policy.precision_policy.identity_id:
        raise ValueError("INTERSECT operation precision must match canonicalization precision")
    if any(policy.precision_policy.identity_id != g.canonicalization_policy.precision_policy.identity_id for g in input_geometries):
        raise ValueError("INTERSECT operation precision must match actual input geometry precision")
    if a.crs_identity.crs_identity_id != b.crs_identity.crs_identity_id:
        return _result(operation=policy.operation, state=OperationState.INCOMPATIBLE, input_geometries=input_geometries, operation_policy=policy, engine=engine, reasons=("crs_mismatch",))
    try:
        out = shapely.intersection(geometry_from_canonical(a), geometry_from_canonical(b), grid_size=None)
        if out.is_empty and not policy.allow_empty_result:
            return _result(operation=policy.operation, state=OperationState.UNRESOLVED, input_geometries=input_geometries, operation_policy=policy, engine=engine, reasons=("empty_intersection_not_allowed",))
        output_policy = operation_output_canonicalization_policy(canonicalization_policy) if out.is_empty else canonicalization_policy
        canonical = canonicalize_geometry(out, crs_identity=a.crs_identity, policy=output_policy, engine=engine)
        return _result(operation=policy.operation, state=OperationState.SUCCESS, input_geometries=input_geometries, operation_policy=policy, engine=engine, output_geometry=canonical)
    except ValueError:
        state = OperationState.INVALID_INPUT
        reasons = ("intersection_output_invalid_for_boundary_geometry_family",)
    except Exception:
        state = OperationState.ENGINE_ERROR
        reasons = ("intersection_engine_error",)
    return _result(operation=policy.operation, state=state, input_geometries=input_geometries, operation_policy=policy, engine=engine, reasons=reasons)


def project_geometry(geometry: CanonicalGeometry, *, target_crs, transform_policy: CRSTransformPolicy, operation_policy: GeometryOperationPolicy, canonicalization_policy: GeometryCanonicalizationPolicy, engine: GeometryEngineIdentity) -> GeometryOperationResult:
    attest_actual_geometry_engine(engine)
    if operation_policy.operation is not GeometryOperation.PROJECT:
        raise ValueError("operation policy must be PROJECT")
    if operation_policy.precision_policy.identity_id != canonicalization_policy.precision_policy.identity_id:
        raise ValueError("PROJECT operation precision must match canonicalization precision")
    input_geometries = (geometry,)
    if operation_policy.precision_policy.identity_id != geometry.canonicalization_policy.precision_policy.identity_id:
        raise ValueError("PROJECT operation precision must match actual input geometry precision")
    target_identity = build_crs_identity(target_crs)
    plan: TransformPlan | None = None
    try:
        plan, transformer, plan_reasons = resolve_transform_plan(geometry.crs_identity, target_identity, transform_policy, engine)
        if plan is None or transformer is None:
            return _result(operation=operation_policy.operation, state=OperationState.UNRESOLVED, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, reasons=plan_reasons or ("transform_plan_unresolved",))

        def fn(x, y, z=None):
            return transformer.transform(x, y, errcheck=True)

        out = shapely_transform(fn, geometry_from_canonical(geometry))
        canonical = canonicalize_geometry(out, crs_identity=target_identity, policy=canonicalization_policy, engine=engine)
        return _result(operation=operation_policy.operation, state=OperationState.SUCCESS, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, transform_plan=plan, output_geometry=canonical)
    except ValueError:
        state = OperationState.INVALID_INPUT
        reasons = ("projection_invalid_input",)
    except Exception:
        state = OperationState.ENGINE_ERROR
        reasons = ("projection_engine_error",)
    return _result(operation=operation_policy.operation, state=state, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, transform_plan=plan, reasons=reasons)


def area_of_projected_geometry(geometry: CanonicalGeometry, *, area_policy: AreaPolicy, operation_policy: GeometryOperationPolicy, engine: GeometryEngineIdentity) -> GeometryOperationResult:
    attest_actual_geometry_engine(engine)
    if operation_policy.operation is not GeometryOperation.AREA:
        raise ValueError("operation policy must be AREA")
    if operation_policy.precision_policy.identity_id != geometry.canonicalization_policy.precision_policy.identity_id:
        raise ValueError("AREA operation precision must match measured input geometry precision")
    input_geometries = (geometry,)
    crs = geometry.crs_identity
    try:
        executable_crs = _crs_from_identity(crs)
    except (TypeError, ValueError):
        return _result(operation=operation_policy.operation, state=OperationState.INCOMPATIBLE, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, area_policy=area_policy, reasons=("crs_execution_attestation_failed",))
    if not executable_crs.is_projected or executable_crs.is_geographic:
        return _result(operation=operation_policy.operation, state=OperationState.INCOMPATIBLE, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, area_policy=area_policy, reasons=("projected_crs_required",))
    axes = tuple(executable_crs.axis_info)
    if len(axes) < 2 or any(abs(float(a.unit_conversion_factor) - 1.0) > 1e-12 or a.unit_name.lower() not in {"metre", "meter"} for a in axes[:2]):
        return _result(operation=operation_policy.operation, state=OperationState.INCOMPATIBLE, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, area_policy=area_policy, reasons=("metre_projected_crs_required",))
    try:
        value = float(geometry_from_canonical(geometry).area)
        if not math.isfinite(value) or value < 0:
            raise RuntimeError("invalid area")
        return _result(operation=operation_policy.operation, state=OperationState.SUCCESS, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, area_policy=area_policy, numeric_value=value, unit=area_policy.output_unit)
    except Exception:
        return _result(operation=operation_policy.operation, state=OperationState.ENGINE_ERROR, input_geometries=input_geometries, operation_policy=operation_policy, engine=engine, area_policy=area_policy, reasons=("area_engine_error",))
