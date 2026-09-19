from __future__ import annotations

from datetime import datetime

from .contracts import (
    BoundaryGeometryArtifact,
    CanonicalGeometry,
    GeographyIdentity,
    GeometryCanonicalizationPolicy,
    GeometryEngineIdentity,
    GeometrySourceIdentity,
)
from .hashing import semantic_hash
from .validation import canonical_string, canonical_string_tuple


def build_boundary_geometry_artifact(
    *,
    geography_identity: GeographyIdentity,
    geometry_role: str,
    source_identity: GeometrySourceIdentity,
    canonical_geometry: CanonicalGeometry,
    parser_id: str,
    parser_version: str,
    canonicalization_policy: GeometryCanonicalizationPolicy,
    engine: GeometryEngineIdentity,
    source_refs: tuple[str, ...],
    generated_at: datetime,
    raw_artifact_ref: str | None = None,
) -> BoundaryGeometryArtifact:
    geometry_role = canonical_string(geometry_role, "geometry_role")
    parser_id = canonical_string(parser_id, "parser_id")
    parser_version = canonical_string(parser_version, "parser_version")
    refs = canonical_string_tuple(source_refs, "source_refs")
    if canonical_geometry.is_empty:
        raise ValueError("boundary artifact cannot contain empty geometry")
    if canonical_geometry.crs_identity.crs_identity_id != source_identity.source_crs_identity.crs_identity_id:
        raise ValueError("canonical geometry CRS does not match source CRS identity")
    if canonical_geometry.canonicalization_policy_id != canonicalization_policy.identity_id:
        raise ValueError("canonicalization policy mismatch")
    if canonical_geometry.engine_identity_id != engine.engine_identity_id:
        raise ValueError("engine identity mismatch")
    record = {
        "geography_identity_id": geography_identity.identity_id,
        "geometry_role": geometry_role,
        "source_identity_id": source_identity.source_identity_id,
        "canonical_geometry_semantic_id": canonical_geometry.semantic_geometry_id,
        "canonical_geometry_hash": canonical_geometry.canonical_geometry_hash,
        "canonical_geometry_encoding": canonicalization_policy.encoding,
        "canonical_geometry_type": canonical_geometry.geometry_type.value,
        "canonical_crs_identity_id": canonical_geometry.crs_identity.crs_identity_id,
        "parser_id": parser_id,
        "parser_version": parser_version,
        "canonicalization_policy_id": canonicalization_policy.identity_id,
        "engine_identity_id": engine.engine_identity_id,
        "source_refs": refs,
    }
    return BoundaryGeometryArtifact(
        geometry_artifact_id=semantic_hash(record),
        geography_identity=geography_identity,
        geometry_role=geometry_role,
        source_identity=source_identity,
        raw_artifact_ref=raw_artifact_ref,
        canonical_geometry=canonical_geometry,
        canonical_geometry_hash=canonical_geometry.canonical_geometry_hash,
        canonical_geometry_encoding=canonicalization_policy.encoding,
        canonical_geometry_type=canonical_geometry.geometry_type,
        canonical_crs_identity=canonical_geometry.crs_identity,
        parser_id=parser_id,
        parser_version=parser_version,
        canonicalization_policy_id=canonicalization_policy.identity_id,
        source_refs=refs,
        generated_at=generated_at,
    )
