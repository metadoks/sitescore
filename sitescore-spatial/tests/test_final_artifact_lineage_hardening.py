from __future__ import annotations

import pytest

from sitescore_spatial import (
    CompatibilityState,
    CRSTransformPolicy,
    GeographyGeometryCompatibility,
    GeographyIdentity,
    TransformPlan,
    TrustedGeographyGeometryCompatibilityPolicy,
    build_boundary_geometry_artifact,
    build_crs_identity,
    build_transform_plan,
    evaluate_geography_geometry_compatibility,
)
from sitescore_spatial.hashing import semantic_hash


def _artifact(geography, source, canonical, canon_policy, engine, now):
    return build_boundary_geometry_artifact(
        geography_identity=geography,
        geometry_role="ADMIN_BOUNDARY",
        source_identity=source,
        canonical_geometry=canonical,
        parser_id="geojson-parser",
        parser_version="1.0",
        canonicalization_policy=canon_policy,
        engine=engine,
        source_refs=("src:1",),
        generated_at=now,
    )


def _plan_record(plan, *, source=None, target=None, policy=None, engine=None):
    source = source or plan.source_crs_identity
    target = target or plan.target_crs_identity
    policy = policy or plan.transform_policy
    engine = engine or plan.engine_identity
    return {
        "source_crs_identity_id": source.crs_identity_id,
        "target_crs_identity_id": target.crs_identity_id,
        "policy_identity_id": policy.identity_id,
        "engine_identity_id": engine.engine_identity_id,
        "selected_pipeline_hash": plan.selected_pipeline_hash,
        "grid_identities": list(plan.grid_identities),
    }


def test_transform_plan_detached_source_crs_id_constructor_impossible(crs4326, crs3857, engine):
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    with pytest.raises(TypeError, match="source_crs_identity_id"):
        TransformPlan(
            plan_id=plan.plan_id,
            source_crs_identity_id=plan.source_crs_identity_id,
            target_crs_identity=plan.target_crs_identity,
            transform_policy=plan.transform_policy,
            engine_identity=plan.engine_identity,
            selected_pipeline_hash=plan.selected_pipeline_hash,
            selected_pipeline_definition=plan.selected_pipeline_definition,
            grid_identities=plan.grid_identities,
        )


def test_transform_plan_detached_target_crs_id_constructor_impossible(crs4326, crs3857, engine):
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    with pytest.raises(TypeError, match="target_crs_identity_id"):
        TransformPlan(
            plan_id=plan.plan_id,
            source_crs_identity=plan.source_crs_identity,
            target_crs_identity_id=plan.target_crs_identity_id,
            transform_policy=plan.transform_policy,
            engine_identity=plan.engine_identity,
            selected_pipeline_hash=plan.selected_pipeline_hash,
            selected_pipeline_definition=plan.selected_pipeline_definition,
            grid_identities=plan.grid_identities,
        )


def test_transform_plan_source_crs_semantics_change_plan_id(crs4326, crs3857, engine):
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    alternate_source = build_crs_identity("EPSG:4269")
    record = _plan_record(plan, source=alternate_source)
    alternate = TransformPlan(
        plan_id=semantic_hash(record),
        source_crs_identity=alternate_source,
        target_crs_identity=plan.target_crs_identity,
        transform_policy=plan.transform_policy,
        engine_identity=plan.engine_identity,
        selected_pipeline_hash=plan.selected_pipeline_hash,
        selected_pipeline_definition=plan.selected_pipeline_definition,
        grid_identities=plan.grid_identities,
    )
    assert alternate.plan_id != plan.plan_id
    assert alternate.source_crs_identity is alternate_source


def test_transform_plan_target_crs_semantics_change_plan_id(crs4326, crs3857, engine):
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    alternate_target = build_crs_identity("EPSG:3395")
    record = _plan_record(plan, target=alternate_target)
    alternate = TransformPlan(
        plan_id=semantic_hash(record),
        source_crs_identity=plan.source_crs_identity,
        target_crs_identity=alternate_target,
        transform_policy=plan.transform_policy,
        engine_identity=plan.engine_identity,
        selected_pipeline_hash=plan.selected_pipeline_hash,
        selected_pipeline_definition=plan.selected_pipeline_definition,
        grid_identities=plan.grid_identities,
    )
    assert alternate.plan_id != plan.plan_id
    assert alternate.target_crs_identity is alternate_target


def test_official_transform_plan_retains_exact_source_target_objects(crs4326, crs3857, engine):
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    assert plan.source_crs_identity is crs4326
    assert plan.target_crs_identity is crs3857
    assert plan.source_crs_identity_id == crs4326.crs_identity_id
    assert plan.target_crs_identity_id == crs3857.crs_identity_id


def test_historical_plan_can_carry_internally_valid_crs_objects(crs4326, crs3857, engine):
    plan, reasons = build_transform_plan(crs4326, crs3857, CRSTransformPolicy(), engine)
    assert plan and not reasons
    # The persistent constructor validates the attached executable CRS objects and plan content,
    # but does not claim the historical plan was freshly selected by today's authority database.
    replayed = TransformPlan(
        plan_id=plan.plan_id,
        source_crs_identity=plan.source_crs_identity,
        target_crs_identity=plan.target_crs_identity,
        transform_policy=plan.transform_policy,
        engine_identity=plan.engine_identity,
        selected_pipeline_hash=plan.selected_pipeline_hash,
        selected_pipeline_definition=plan.selected_pipeline_definition,
        grid_identities=plan.grid_identities,
    )
    assert replayed == plan


def test_compatibility_detached_ids_constructor_impossible(geography, source, canonical, canon_policy, engine, now):
    geometry_geo = GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2024-bg-definition")
    artifact = _artifact(geometry_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy(
        "acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition"
    )
    with pytest.raises(TypeError, match="geography_identity_id"):
        GeographyGeometryCompatibility(
            compatibility_id="0" * 64,
            geography_identity_id=geography.identity_id,
            geometry_artifact=artifact,
            trusted_policy=policy,
            demographic_definition_identity="acs-2024-bg-definition",
            state=CompatibilityState.COMPATIBLE,
            reason_codes=(),
        )
    with pytest.raises(TypeError, match="geometry_artifact_id"):
        GeographyGeometryCompatibility(
            compatibility_id="0" * 64,
            geography_identity=geography,
            geometry_artifact_id=artifact.geometry_artifact_id,
            trusted_policy=policy,
            demographic_definition_identity="acs-2024-bg-definition",
            state=CompatibilityState.COMPATIBLE,
            reason_codes=(),
        )
    with pytest.raises(TypeError, match="policy_identity_id"):
        GeographyGeometryCompatibility(
            compatibility_id="0" * 64,
            geography_identity=geography,
            geometry_artifact=artifact,
            policy_identity_id=policy.identity_id,
            demographic_definition_identity="acs-2024-bg-definition",
            state=CompatibilityState.COMPATIBLE,
            reason_codes=(),
        )


def _compat_id(geography, artifact, policy, demographic_definition, state, reasons):
    return semantic_hash({
        "geography_identity_id": geography.identity_id,
        "geometry_artifact_id": artifact.geometry_artifact_id,
        "policy_identity_id": policy.identity_id,
        "demographic_definition_identity": demographic_definition,
        "state": state.value,
        "reason_codes": list(sorted(reasons)),
    })


def test_direct_compatible_claim_with_incompatible_definition_rejected(geography, source, canonical, canon_policy, engine, now):
    bad_geo = GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2023-bg-definition")
    artifact = _artifact(bad_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy(
        "acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition"
    )
    cid = _compat_id(geography, artifact, policy, "acs-2024-bg-definition", CompatibilityState.COMPATIBLE, ())
    with pytest.raises(ValueError, match="state does not match attached evidence"):
        GeographyGeometryCompatibility(
            compatibility_id=cid,
            geography_identity=geography,
            geometry_artifact=artifact,
            trusted_policy=policy,
            demographic_definition_identity="acs-2024-bg-definition",
            state=CompatibilityState.COMPATIBLE,
            reason_codes=(),
        )


def test_direct_compatible_claim_with_foreign_artifact_rejected(geography, source, canonical, canon_policy, engine, now):
    foreign_geo = GeographyIdentity("BLOCK_GROUP", "999999999999", "tiger-2024-bg-definition")
    artifact = _artifact(foreign_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy(
        "acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition"
    )
    cid = _compat_id(geography, artifact, policy, "acs-2024-bg-definition", CompatibilityState.COMPATIBLE, ())
    with pytest.raises(ValueError, match="state does not match attached evidence"):
        GeographyGeometryCompatibility(
            compatibility_id=cid,
            geography_identity=geography,
            geometry_artifact=artifact,
            trusted_policy=policy,
            demographic_definition_identity="acs-2024-bg-definition",
            state=CompatibilityState.COMPATIBLE,
            reason_codes=(),
        )


def test_direct_compatible_claim_with_trusted_policy_mismatch_rejected(geography, source, canonical, canon_policy, engine, now):
    geometry_geo = GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2024-bg-definition")
    artifact = _artifact(geometry_geo, source, canonical, canon_policy, engine, now)
    wrong_policy = TrustedGeographyGeometryCompatibilityPolicy(
        "acs-tiger-compat", "2", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2025-bg-definition"
    )
    cid = _compat_id(geography, artifact, wrong_policy, "acs-2024-bg-definition", CompatibilityState.COMPATIBLE, ())
    with pytest.raises(ValueError, match="state does not match attached evidence"):
        GeographyGeometryCompatibility(
            compatibility_id=cid,
            geography_identity=geography,
            geometry_artifact=artifact,
            trusted_policy=wrong_policy,
            demographic_definition_identity="acs-2024-bg-definition",
            state=CompatibilityState.COMPATIBLE,
            reason_codes=(),
        )


def test_official_evaluator_carries_actual_evidence_and_states(geography, source, canonical, canon_policy, engine, now):
    geometry_geo = GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2024-bg-definition")
    artifact = _artifact(geometry_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy(
        "acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition"
    )
    result = evaluate_geography_geometry_compatibility(
        actual_geography=geography,
        actual_demographic_definition_identity="acs-2024-bg-definition",
        actual_geometry_artifact=artifact,
        trusted_policy=policy,
    )
    assert result.state is CompatibilityState.COMPATIBLE
    assert result.geography_identity is geography
    assert result.geometry_artifact is artifact
    assert result.trusted_policy is policy
    assert result.reason_codes == ()

    bad_artifact = _artifact(
        GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2023-bg-definition"),
        source, canonical, canon_policy, engine, now,
    )
    incompatible = evaluate_geography_geometry_compatibility(
        actual_geography=geography,
        actual_demographic_definition_identity="acs-2024-bg-definition",
        actual_geometry_artifact=bad_artifact,
        trusted_policy=policy,
    )
    assert incompatible.state is CompatibilityState.INCOMPATIBLE
    assert "unexpected_geometry_definition_identity" in incompatible.reason_codes


def test_compatibility_identity_changes_with_actual_evidence_semantics(geography, source, canonical, canon_policy, engine, now):
    artifact = _artifact(
        GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2024-bg-definition"),
        source, canonical, canon_policy, engine, now,
    )
    policy1 = TrustedGeographyGeometryCompatibilityPolicy(
        "acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition"
    )
    result1 = evaluate_geography_geometry_compatibility(
        actual_geography=geography,
        actual_demographic_definition_identity="acs-2024-bg-definition",
        actual_geometry_artifact=artifact,
        trusted_policy=policy1,
    )
    policy2 = TrustedGeographyGeometryCompatibilityPolicy(
        "acs-tiger-compat", "2", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition"
    )
    result2 = evaluate_geography_geometry_compatibility(
        actual_geography=geography,
        actual_demographic_definition_identity="acs-2024-bg-definition",
        actual_geometry_artifact=artifact,
        trusted_policy=policy2,
    )
    assert result1.compatibility_id != result2.compatibility_id

    altered_geography = GeographyIdentity("BLOCK_GROUP", "360610001001", "acs-2025-bg-definition")
    result3 = evaluate_geography_geometry_compatibility(
        actual_geography=altered_geography,
        actual_demographic_definition_identity="acs-2025-bg-definition",
        actual_geometry_artifact=artifact,
        trusted_policy=policy1,
    )
    assert result1.compatibility_id != result3.compatibility_id
