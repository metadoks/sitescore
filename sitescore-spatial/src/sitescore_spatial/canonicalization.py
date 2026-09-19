from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from .contracts import CRSIdentity, CanonicalGeometry, GeometryCanonicalizationPolicy, GeometryEngineIdentity
from .enums import EmptyGeometryBehavior, GeometryType
from .geometry_codec import canonical_wkb_v1
from .hashing import content_hash, semantic_hash
from .identity import attest_actual_geometry_engine


def _as_geometry(value) -> BaseGeometry:
    if isinstance(value, BaseGeometry):
        return value
    if isinstance(value, Mapping):
        return shape(value)
    raise TypeError("geometry input must be a Shapely geometry or GeoJSON-like mapping")


def operation_output_canonicalization_policy(policy: GeometryCanonicalizationPolicy) -> GeometryCanonicalizationPolicy:
    """Explicit policy variant for legitimate empty operation outputs."""
    return replace(
        policy,
        policy_id=f"{policy.policy_id}_operation_output",
        empty_geometry_behavior=EmptyGeometryBehavior.ALLOW_OPERATION_OUTPUT,
    )


def canonicalize_geometry(
    value,
    *,
    crs_identity: CRSIdentity,
    policy: GeometryCanonicalizationPolicy,
    engine: GeometryEngineIdentity,
) -> CanonicalGeometry:
    attest_actual_geometry_engine(engine)
    geometry = _as_geometry(value)
    allow_empty = policy.empty_geometry_behavior is EmptyGeometryBehavior.ALLOW_OPERATION_OUTPUT
    normalized, wkb = canonical_wkb_v1(geometry, allow_empty=allow_empty)
    geometry_hash = content_hash(wkb)
    gtype = GeometryType.POLYGON if normalized.geom_type == "Polygon" else GeometryType.MULTIPOLYGON
    semantic_record = {
        "canonical_geometry_hash": geometry_hash,
        "geometry_type": gtype.value,
        "crs_identity_id": crs_identity.crs_identity_id,
        "canonicalization_policy_id": policy.identity_id,
        "engine_identity_id": engine.engine_identity_id,
    }
    return CanonicalGeometry(
        semantic_geometry_id=semantic_hash(semantic_record),
        canonical_wkb=wkb,
        canonical_geometry_hash=geometry_hash,
        geometry_type=gtype,
        crs_identity=crs_identity,
        canonicalization_policy=policy,
        engine_identity=engine,
        is_empty=bool(normalized.is_empty),
    )


def geometry_from_canonical(value: CanonicalGeometry) -> BaseGeometry:
    import shapely
    return shapely.from_wkb(value.canonical_wkb)
