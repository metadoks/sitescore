from datetime import timedelta

from sitescore_spatial import (
    CompatibilityState,
    GeographyIdentity,
    TrustedGeographyGeometryCompatibilityPolicy,
    build_boundary_geometry_artifact,
    evaluate_geography_geometry_compatibility,
)


def build_artifact(geography, source, canonical, canon_policy, engine, now, ref="/tmp/a.geojson"):
    return build_boundary_geometry_artifact(
        geography_identity=geography, geometry_role="ADMIN_BOUNDARY", source_identity=source,
        canonical_geometry=canonical, parser_id="geojson-parser", parser_version="1.0",
        canonicalization_policy=canon_policy, engine=engine, source_refs=("src:1",),
        generated_at=now, raw_artifact_ref=ref,
    )


def test_path_change_does_not_change_artifact_identity(geography, source, canonical, canon_policy, engine, now):
    a = build_artifact(geography, source, canonical, canon_policy, engine, now, "/a")
    b = build_artifact(geography, source, canonical, canon_policy, engine, now, "/b")
    assert a.geometry_artifact_id == b.geometry_artifact_id


def test_generated_at_change_does_not_change_artifact_identity(geography, source, canonical, canon_policy, engine, now):
    a = build_artifact(geography, source, canonical, canon_policy, engine, now)
    b = build_artifact(geography, source, canonical, canon_policy, engine, now + timedelta(days=1))
    assert a.geometry_artifact_id == b.geometry_artifact_id


def test_compatible_actual_inputs(geography, source, canonical, canon_policy, engine, now):
    geometry_geo = GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2024-bg-definition")
    artifact = build_artifact(geometry_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy("acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition")
    result = evaluate_geography_geometry_compatibility(actual_geography=geography, actual_demographic_definition_identity="acs-2024-bg-definition", actual_geometry_artifact=artifact, trusted_policy=policy)
    assert result.state is CompatibilityState.COMPATIBLE


def test_same_id_incompatible_vintage_rejected(geography, source, canonical, canon_policy, engine, now):
    geometry_geo = GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2023-bg-definition")
    artifact = build_artifact(geometry_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy("acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition")
    result = evaluate_geography_geometry_compatibility(actual_geography=geography, actual_demographic_definition_identity="acs-2024-bg-definition", actual_geometry_artifact=artifact, trusted_policy=policy)
    assert result.state is CompatibilityState.INCOMPATIBLE
    assert "unexpected_geometry_definition_identity" in result.reason_codes


def test_foreign_geometry_artifact_rejected(geography, source, canonical, canon_policy, engine, now):
    foreign_geo = GeographyIdentity("BLOCK_GROUP", "999999999999", "tiger-2024-bg-definition")
    artifact = build_artifact(foreign_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy("acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition")
    result = evaluate_geography_geometry_compatibility(actual_geography=geography, actual_demographic_definition_identity="acs-2024-bg-definition", actual_geometry_artifact=artifact, trusted_policy=policy)
    assert result.state is CompatibilityState.INCOMPATIBLE
    assert "canonical_geography_identifier_mismatch" in result.reason_codes


def test_self_asserted_wrong_demographic_identity_cannot_pass(geography, source, canonical, canon_policy, engine, now):
    geometry_geo = GeographyIdentity("BLOCK_GROUP", "360610001001", "tiger-2024-bg-definition")
    artifact = build_artifact(geometry_geo, source, canonical, canon_policy, engine, now)
    policy = TrustedGeographyGeometryCompatibilityPolicy("acs-tiger-compat", "1", "BLOCK_GROUP", "acs-2024-bg-definition", "tiger-2024-bg-definition")
    result = evaluate_geography_geometry_compatibility(actual_geography=geography, actual_demographic_definition_identity="acs-2023-bg-definition", actual_geometry_artifact=artifact, trusted_policy=policy)
    assert result.state is CompatibilityState.INCOMPATIBLE
    assert "unexpected_demographic_definition_identity" in result.reason_codes
