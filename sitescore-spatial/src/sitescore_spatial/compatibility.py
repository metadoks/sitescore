from __future__ import annotations

from .contracts import (
    BoundaryGeometryArtifact,
    GeographyGeometryCompatibility,
    GeographyIdentity,
    TrustedGeographyGeometryCompatibilityPolicy,
    _geography_geometry_compatibility_reasons,
)
from .enums import CompatibilityState
from .hashing import semantic_hash


def evaluate_geography_geometry_compatibility(
    *,
    actual_geography: GeographyIdentity,
    actual_demographic_definition_identity: str,
    actual_geometry_artifact: BoundaryGeometryArtifact,
    trusted_policy: TrustedGeographyGeometryCompatibilityPolicy,
) -> GeographyGeometryCompatibility:
    reasons = _geography_geometry_compatibility_reasons(
        actual_geography,
        actual_demographic_definition_identity,
        actual_geometry_artifact,
        trusted_policy,
    )
    state = CompatibilityState.COMPATIBLE if not reasons else CompatibilityState.INCOMPATIBLE
    record = {
        "geography_identity_id": actual_geography.identity_id,
        "geometry_artifact_id": actual_geometry_artifact.geometry_artifact_id,
        "policy_identity_id": trusted_policy.identity_id,
        "demographic_definition_identity": actual_demographic_definition_identity,
        "state": state.value,
        "reason_codes": list(reasons),
    }
    return GeographyGeometryCompatibility(
        compatibility_id=semantic_hash(record),
        geography_identity=actual_geography,
        geometry_artifact=actual_geometry_artifact,
        trusted_policy=trusted_policy,
        demographic_definition_identity=actual_demographic_definition_identity,
        state=state,
        reason_codes=reasons,
    )
