from __future__ import annotations

from dataclasses import replace

import pytest
from shapely.geometry import Polygon

from sitescore_spatial import (
    BoundaryGeometryArtifact,
    CRSTransformPolicy,
    CanonicalGeometry,
    GeometryEngineIdentity,
    GeometryOperation,
    GeometryOperationPolicy,
    TransformPlan,
    area_of_projected_geometry,
    build_boundary_geometry_artifact,
    build_transform_plan,
    canonicalize_geometry,
    intersect_geometries,
    project_geometry,
)
from sitescore_spatial.hashing import semantic_hash
from sitescore_spatial.canonicalization import operation_output_canonicalization_policy
from sitescore_spatial.contracts import AreaPolicy


def _historical_engine(engine, version="historical-9.9"):
    record = engine.semantic_record()
    record["engine_identity_version"] = version
    return GeometryEngineIdentity(engine_identity_id=semantic_hash(record), **record)


def _canonical_with_engine(template: CanonicalGeometry, engine: GeometryEngineIdentity) -> CanonicalGeometry:
    record = {
        "canonical_geometry_hash": template.canonical_geometry_hash,
        "geometry_type": template.geometry_type.value,
        "crs_identity_id": template.crs_identity.crs_identity_id,
        "canonicalization_policy_id": template.canonicalization_policy.identity_id,
        "engine_identity_id": engine.engine_identity_id,
    }
    return CanonicalGeometry(
        semantic_geometry_id=semantic_hash(record),
        canonical_wkb=template.canonical_wkb,
        canonical_geometry_hash=template.canonical_geometry_hash,
        geometry_type=template.geometry_type,
        crs_identity=template.crs_identity,
        canonicalization_policy=template.canonicalization_policy,
        engine_identity=engine,
        is_empty=template.is_empty,
    )


def test_canonical_geometry_detached_engine_id_constructor_impossible(canonical):
    with pytest.raises(TypeError, match="engine_identity_id"):
        CanonicalGeometry(
            semantic_geometry_id=canonical.semantic_geometry_id,
            canonical_wkb=canonical.canonical_wkb,
            canonical_geometry_hash=canonical.canonical_geometry_hash,
            geometry_type=canonical.geometry_type,
            crs_identity=canonical.crs_identity,
            canonicalization_policy=canonical.canonicalization_policy,
            engine_identity_id=canonical.engine_identity_id,
            is_empty=canonical.is_empty,
        )


def test_historical_self_consistent_engine_allowed_for_artifact_but_not_current_execution(canonical, canon_policy, engine):
    historical = _historical_engine(engine)
    replayed = _canonical_with_engine(canonical, historical)
    assert replayed.engine_identity == historical
    assert replayed.engine_identity_id == historical.engine_identity_id
    with pytest.raises(ValueError, match="active spatial runtime"):
        canonicalize_geometry(
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
            crs_identity=canonical.crs_identity,
            policy=canon_policy,
            engine=historical,
        )


def test_geometry_engine_semantics_change_semantic_geometry_id(canonical, engine):
    historical = _historical_engine(engine)
    replayed = _canonical_with_engine(canonical, historical)
    assert replayed.canonical_wkb == canonical.canonical_wkb
    assert replayed.semantic_geometry_id != canonical.semantic_geometry_id


def test_official_canonicalize_attaches_exact_runtime_engine(canonical, engine):
    assert canonical.engine_identity is engine
    assert canonical.engine_identity_id == engine.engine_identity_id


def test_transform_plan_detached_engine_id_constructor_impossible(canonical, crs3857, engine):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    with pytest.raises(TypeError, match="engine_identity_id"):
        TransformPlan(
            plan_id=plan.plan_id,
            source_crs_identity=plan.source_crs_identity,
            target_crs_identity=plan.target_crs_identity,
            transform_policy=plan.transform_policy,
            engine_identity_id=plan.engine_identity_id,
            selected_pipeline_hash=plan.selected_pipeline_hash,
            selected_pipeline_definition=plan.selected_pipeline_definition,
            grid_identities=plan.grid_identities,
        )


def test_transform_plan_engine_semantics_change_plan_id(canonical, crs3857, engine):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    historical = _historical_engine(engine)
    record = {
        "source_crs_identity_id": plan.source_crs_identity_id,
        "target_crs_identity_id": plan.target_crs_identity_id,
        "policy_identity_id": plan.policy_identity_id,
        "engine_identity_id": historical.engine_identity_id,
        "selected_pipeline_hash": plan.selected_pipeline_hash,
        "grid_identities": list(plan.grid_identities),
    }
    historical_plan = TransformPlan(
        plan_id=semantic_hash(record),
        source_crs_identity=plan.source_crs_identity,
        target_crs_identity=plan.target_crs_identity,
        transform_policy=plan.transform_policy,
        engine_identity=historical,
        selected_pipeline_hash=plan.selected_pipeline_hash,
        selected_pipeline_definition=plan.selected_pipeline_definition,
        grid_identities=plan.grid_identities,
    )
    assert historical_plan.plan_id != plan.plan_id
    assert historical_plan.engine_identity == historical


def test_official_transform_plan_attaches_exact_runtime_engine(canonical, crs3857, engine):
    plan, reasons = build_transform_plan(canonical.crs_identity, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    assert plan.engine_identity is engine


def test_boundary_artifact_engine_is_derived_from_canonical_geometry(geography, source, canonical, canon_policy, engine, now):
    artifact = build_boundary_geometry_artifact(
        geography_identity=geography,
        geometry_role="ADMIN_BOUNDARY",
        source_identity=source,
        canonical_geometry=canonical,
        parser_id="parser",
        parser_version="1",
        canonicalization_policy=canon_policy,
        engine=engine,
        source_refs=("src:1",),
        generated_at=now,
    )
    assert artifact.engine_identity is canonical.engine_identity
    assert artifact.engine_identity_id == canonical.engine_identity_id
    with pytest.raises(TypeError, match="engine_identity_id"):
        BoundaryGeometryArtifact(
            geometry_artifact_id=artifact.geometry_artifact_id,
            geography_identity=artifact.geography_identity,
            geometry_role=artifact.geometry_role,
            source_identity=artifact.source_identity,
            raw_artifact_ref=artifact.raw_artifact_ref,
            canonical_geometry=artifact.canonical_geometry,
            canonical_geometry_hash=artifact.canonical_geometry_hash,
            canonical_geometry_encoding=artifact.canonical_geometry_encoding,
            canonical_geometry_type=artifact.canonical_geometry_type,
            canonical_crs_identity=artifact.canonical_crs_identity,
            parser_id=artifact.parser_id,
            parser_version=artifact.parser_version,
            canonicalization_policy_id=artifact.canonicalization_policy_id,
            engine_identity_id=engine.engine_identity_id,
            source_refs=artifact.source_refs,
            generated_at=artifact.generated_at,
        )


def test_official_intersect_result_output_engine_coherent(canonical, canon_policy, engine):
    op = GeometryOperationPolicy("intersect", "1.0", GeometryOperation.INTERSECT, canon_policy.precision_policy)
    result = intersect_geometries(canonical, canonical, policy=op, canonicalization_policy=canon_policy, engine=engine)
    assert result.engine_identity == result.output_geometry.engine_identity == engine


def test_official_project_result_plan_output_engine_coherent(canonical, crs3857, canon_policy, engine):
    op = GeometryOperationPolicy("project", "1.0", GeometryOperation.PROJECT, canon_policy.precision_policy)
    result = project_geometry(
        canonical,
        target_crs=crs3857.canonical_definition,
        transform_policy=CRSTransformPolicy(),
        operation_policy=op,
        canonicalization_policy=canon_policy,
        engine=engine,
    )
    assert result.engine_identity == result.transform_plan.engine_identity == result.output_geometry.engine_identity == engine


def test_area_allows_historical_input_engine_different_from_current_execution(crs3857, canon_policy, engine):
    current = canonicalize_geometry(
        Polygon([(0,0),(10,0),(10,10),(0,10),(0,0)]),
        crs_identity=crs3857,
        policy=canon_policy,
        engine=engine,
    )
    historical = _historical_engine(engine)
    replayed = _canonical_with_engine(current, historical)
    op = GeometryOperationPolicy("area", "1.0", GeometryOperation.AREA, canon_policy.precision_policy)
    result = area_of_projected_geometry(replayed, area_policy=AreaPolicy(), operation_policy=op, engine=engine)
    assert result.numeric_value == pytest.approx(100.0)
    assert result.engine_identity == engine
    assert replayed.engine_identity == historical
    assert result.engine_identity_id != replayed.engine_identity_id
