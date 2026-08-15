from __future__ import annotations

from dataclasses import dataclass, field
import json
from datetime import datetime
from typing import Optional

from .enums import (
    AxisOrderPolicy,
    CompatibilityState,
    EmptyGeometryBehavior,
    GeometryOperation,
    GeometryPrecisionMode,
    GeometryType,
    InvalidGeometryBehavior,
    OperationState,
)
from .hashing import content_hash, semantic_hash
from .validation import canonical_string, canonical_string_tuple, finite_number, immutable_release, sha256_hex


@dataclass(frozen=True, slots=True)
class AxisSemantic:
    name: str
    direction: str
    unit_name: str
    unit_conversion_factor: float

    def __post_init__(self) -> None:
        canonical_string(self.name, "axis.name")
        canonical_string(self.direction, "axis.direction")
        canonical_string(self.unit_name, "axis.unit_name")
        finite_number(self.unit_conversion_factor, "axis.unit_conversion_factor")

    def semantic_record(self) -> dict:
        return {"name": self.name, "direction": self.direction, "unit_name": self.unit_name, "unit_conversion_factor": self.unit_conversion_factor}


@dataclass(frozen=True, slots=True)
class CRSIdentity:
    crs_identity_id: str
    authority: Optional[str]
    authority_code: Optional[str]
    canonical_definition: str
    axis_semantics: tuple[AxisSemantic, ...]
    is_geographic: bool
    is_projected: bool
    definition_policy_id: str = "projjson"
    definition_policy_version: str = "1.0"

    @property
    def canonical_definition_hash(self) -> str:
        return semantic_hash(json.loads(self.canonical_definition))

    def __post_init__(self) -> None:
        # The public CRS identity carries the executable canonical definition, not a detached hash.
        # Parse and re-emit through the pinned pyproj runtime so key/format noise is non-semantic.
        try:
            from pyproj import CRS
            supplied = json.loads(self.canonical_definition)
            if not isinstance(supplied, dict):
                raise ValueError("canonical_definition must encode a PROJJSON object")
            parsed = CRS.from_json_dict(supplied)
            canonical_definition = json.dumps(
                parsed.to_json_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except Exception as exc:
            raise ValueError("canonical_definition must be a valid executable PROJJSON CRS definition") from exc
        object.__setattr__(self, "canonical_definition", canonical_definition)

        sha256_hex(self.crs_identity_id, "crs_identity_id")
        if (self.authority is None) != (self.authority_code is None):
            raise ValueError("authority and authority_code must be both present or both absent")
        if self.authority is not None:
            canonical_string(self.authority, "authority")
            canonical_string(self.authority_code or "", "authority_code")
        if not self.axis_semantics:
            raise ValueError("axis_semantics must not be empty")
        if not isinstance(self.axis_semantics, tuple) or any(not isinstance(a, AxisSemantic) for a in self.axis_semantics):
            raise TypeError("axis_semantics must contain AxisSemantic values")
        canonical_string(self.definition_policy_id, "definition_policy_id")
        canonical_string(self.definition_policy_version, "definition_policy_version")

        actual_axis = tuple(
            AxisSemantic(
                name=a.name,
                direction=a.direction,
                unit_name=a.unit_name,
                unit_conversion_factor=float(a.unit_conversion_factor),
            )
            for a in parsed.axis_info
        )
        if tuple(self.axis_semantics) != actual_axis:
            raise ValueError("axis_semantics do not match canonical CRS definition")
        if self.is_geographic != bool(parsed.is_geographic):
            raise ValueError("is_geographic does not match canonical CRS definition")
        if self.is_projected != bool(parsed.is_projected):
            raise ValueError("is_projected does not match canonical CRS definition")

        if self.authority is not None and self.authority_code is not None:
            try:
                authority_crs = CRS.from_user_input(f"{self.authority}:{self.authority_code}")
                authority_definition = json.dumps(
                    authority_crs.to_json_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
                )
            except Exception as exc:
                raise ValueError("authority/code cannot be resolved by the pinned CRS runtime") from exc
            if authority_definition != self.canonical_definition:
                raise ValueError("authority/code does not match canonical CRS definition")

        expected = semantic_hash(self.semantic_record())
        if self.crs_identity_id != expected:
            raise ValueError("crs_identity_id does not match CRS semantic content")

    def semantic_record(self) -> dict:
        return {
            "authority": self.authority,
            "authority_code": self.authority_code,
            "canonical_definition_hash": self.canonical_definition_hash,
            "axis_semantics": [a.semantic_record() for a in self.axis_semantics],
            "is_geographic": self.is_geographic,
            "is_projected": self.is_projected,
            "definition_policy_id": self.definition_policy_id,
            "definition_policy_version": self.definition_policy_version,
        }


@dataclass(frozen=True, slots=True)
class GeographyIdentity:
    geography_type: str
    canonical_identifier: str
    definition_identity: str
    identity_version: str = "1.0"

    def __post_init__(self) -> None:
        canonical_string(self.geography_type, "geography_type")
        canonical_string(self.canonical_identifier, "canonical_identifier")
        canonical_string(self.definition_identity, "definition_identity")
        canonical_string(self.identity_version, "identity_version")

    @property
    def identity_id(self) -> str:
        return semantic_hash(self.semantic_record())

    def semantic_record(self) -> dict:
        return {
            "geography_type": self.geography_type,
            "canonical_identifier": self.canonical_identifier,
            "definition_identity": self.definition_identity,
            "identity_version": self.identity_version,
        }


@dataclass(frozen=True, slots=True)
class GeometrySourceIdentity:
    source_identity_id: str
    provider: str
    dataset: str
    release: str
    vintage: str
    schema_version: str
    source_crs_identity: CRSIdentity
    raw_content_hash: str

    def __post_init__(self) -> None:
        sha256_hex(self.source_identity_id, "source_identity_id")
        canonical_string(self.provider, "provider")
        canonical_string(self.dataset, "dataset")
        immutable_release(self.release)
        immutable_release(self.vintage, "vintage")
        canonical_string(self.schema_version, "schema_version")
        if not isinstance(self.source_crs_identity, CRSIdentity):
            raise TypeError("source_crs_identity must be CRSIdentity")
        sha256_hex(self.raw_content_hash, "raw_content_hash")
        expected = semantic_hash(self.semantic_record())
        if self.source_identity_id != expected:
            raise ValueError("source_identity_id does not match source semantic content")

    def semantic_record(self) -> dict:
        return {
            "provider": self.provider,
            "dataset": self.dataset,
            "release": self.release,
            "vintage": self.vintage,
            "schema_version": self.schema_version,
            "source_crs_identity_id": self.source_crs_identity.crs_identity_id,
            "raw_content_hash": self.raw_content_hash,
        }


@dataclass(frozen=True, slots=True)
class GeometryEngineIdentity:
    engine_identity_id: str
    python_version: str
    geometry_library: str
    geometry_library_version: str
    geos_version: str
    projection_library: str
    projection_library_version: str
    proj_version: str
    proj_database_hash: Optional[str]
    engine_identity_version: str = "1.0"

    def __post_init__(self) -> None:
        sha256_hex(self.engine_identity_id, "engine_identity_id")
        for n in ("python_version", "geometry_library", "geometry_library_version", "geos_version", "projection_library", "projection_library_version", "proj_version", "engine_identity_version"):
            canonical_string(getattr(self, n), n)
        if self.proj_database_hash is not None:
            sha256_hex(self.proj_database_hash, "proj_database_hash")
        expected = semantic_hash(self.semantic_record())
        if self.engine_identity_id != expected:
            raise ValueError("engine_identity_id does not match engine semantic content")

    def semantic_record(self) -> dict:
        return {
            "python_version": self.python_version,
            "geometry_library": self.geometry_library,
            "geometry_library_version": self.geometry_library_version,
            "geos_version": self.geos_version,
            "projection_library": self.projection_library,
            "projection_library_version": self.projection_library_version,
            "proj_version": self.proj_version,
            "proj_database_hash": self.proj_database_hash,
            "engine_identity_version": self.engine_identity_version,
        }


@dataclass(frozen=True, slots=True)
class GeometryPrecisionPolicy:
    policy_id: str = "full_double_geometry_precision"
    policy_version: str = "1.0"
    mode: GeometryPrecisionMode = GeometryPrecisionMode.FULL_DOUBLE
    grid_size: None = None

    def __post_init__(self) -> None:
        canonical_string(self.policy_id, "policy_id")
        canonical_string(self.policy_version, "policy_version")
        if not isinstance(self.mode, GeometryPrecisionMode):
            raise TypeError("mode must be GeometryPrecisionMode")
        if self.mode is not GeometryPrecisionMode.FULL_DOUBLE or self.grid_size is not None:
            raise ValueError("Checkpoint 3.4-1 freezes no coordinate quantization; only FULL_DOUBLE is supported")

    @property
    def identity_id(self) -> str:
        return semantic_hash({"policy_id": self.policy_id, "policy_version": self.policy_version, "mode": self.mode.value, "grid_size": None})


@dataclass(frozen=True, slots=True)
class GeometryCanonicalizationPolicy:
    policy_id: str = "boundary_geometry_canonicalization"
    policy_version: str = "1.0"
    accepted_geometry_types: tuple[GeometryType, ...] = (GeometryType.POLYGON, GeometryType.MULTIPOLYGON)
    coordinate_dimensions: int = 2
    normalize_rings_and_parts: bool = True
    invalid_geometry_behavior: InvalidGeometryBehavior = InvalidGeometryBehavior.REJECT
    empty_geometry_behavior: EmptyGeometryBehavior = EmptyGeometryBehavior.REJECT
    encoding: str = "OGC_WKB_LE_2D_NO_SRID"
    precision_policy: GeometryPrecisionPolicy = field(default_factory=GeometryPrecisionPolicy)

    def __post_init__(self) -> None:
        canonical_string(self.policy_id, "policy_id")
        canonical_string(self.policy_version, "policy_version")
        if not isinstance(self.accepted_geometry_types, tuple) or any(not isinstance(x, GeometryType) for x in self.accepted_geometry_types):
            raise TypeError("accepted_geometry_types must contain GeometryType values")
        if not isinstance(self.invalid_geometry_behavior, InvalidGeometryBehavior):
            raise TypeError("invalid_geometry_behavior must be InvalidGeometryBehavior")
        if not isinstance(self.empty_geometry_behavior, EmptyGeometryBehavior):
            raise TypeError("empty_geometry_behavior must be EmptyGeometryBehavior")
        if not isinstance(self.precision_policy, GeometryPrecisionPolicy):
            raise TypeError("precision_policy must be GeometryPrecisionPolicy")
        if tuple(self.accepted_geometry_types) != (GeometryType.POLYGON, GeometryType.MULTIPOLYGON):
            raise ValueError("V1 boundary policy accepts exactly Polygon and MultiPolygon")
        if self.coordinate_dimensions != 2:
            raise ValueError("V1 boundary policy is strictly 2D")
        if not self.normalize_rings_and_parts:
            raise ValueError("V1 canonicalization requires strict ring/part normalization")
        if self.invalid_geometry_behavior is not InvalidGeometryBehavior.REJECT:
            raise ValueError("V1 must not repair invalid geometry")
        if self.empty_geometry_behavior not in {EmptyGeometryBehavior.REJECT, EmptyGeometryBehavior.ALLOW_OPERATION_OUTPUT}:
            raise ValueError("unsupported V1 empty geometry behavior")
        if self.encoding != "OGC_WKB_LE_2D_NO_SRID":
            raise ValueError("unsupported canonical encoding")

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "accepted_geometry_types": [x.value for x in self.accepted_geometry_types],
            "coordinate_dimensions": self.coordinate_dimensions,
            "normalize_rings_and_parts": self.normalize_rings_and_parts,
            "invalid_geometry_behavior": self.invalid_geometry_behavior.value,
            "empty_geometry_behavior": self.empty_geometry_behavior.value,
            "encoding": self.encoding,
            "precision_policy_id": self.precision_policy.identity_id,
        })


@dataclass(frozen=True, slots=True)
class CanonicalGeometry:
    semantic_geometry_id: str
    canonical_wkb: bytes = field(repr=False)
    canonical_geometry_hash: str = ""
    geometry_type: GeometryType = GeometryType.POLYGON
    crs_identity: CRSIdentity | None = None
    canonicalization_policy: GeometryCanonicalizationPolicy | None = None
    engine_identity: GeometryEngineIdentity | None = None
    is_empty: bool = False

    @property
    def engine_identity_id(self) -> str:
        if self.engine_identity is None:
            raise ValueError("engine_identity required")
        return self.engine_identity.engine_identity_id

    @property
    def canonicalization_policy_id(self) -> str:
        if self.canonicalization_policy is None:
            raise ValueError("canonicalization_policy required")
        return self.canonicalization_policy.identity_id

    def __post_init__(self) -> None:
        sha256_hex(self.semantic_geometry_id, "semantic_geometry_id")
        if not isinstance(self.canonical_wkb, bytes):
            raise TypeError("canonical_wkb must be bytes")
        sha256_hex(self.canonical_geometry_hash, "canonical_geometry_hash")
        if not isinstance(self.geometry_type, GeometryType):
            raise TypeError("geometry_type must be GeometryType")
        if not isinstance(self.crs_identity, CRSIdentity):
            raise TypeError("crs_identity must be CRSIdentity")
        if not isinstance(self.canonicalization_policy, GeometryCanonicalizationPolicy):
            raise TypeError("canonicalization_policy must be GeometryCanonicalizationPolicy")
        if not isinstance(self.engine_identity, GeometryEngineIdentity):
            raise TypeError("engine_identity must be GeometryEngineIdentity")
        if content_hash(self.canonical_wkb) != self.canonical_geometry_hash:
            raise ValueError("canonical_geometry_hash does not match canonical_wkb")
        try:
            import shapely
            from .geometry_codec import canonical_wkb_v1
            decoded = shapely.from_wkb(self.canonical_wkb)
        except Exception as exc:
            raise ValueError("canonical_wkb cannot be decoded") from exc
        expected_type = GeometryType.POLYGON if decoded.geom_type == "Polygon" else GeometryType.MULTIPOLYGON if decoded.geom_type == "MultiPolygon" else None
        if expected_type is None or expected_type is not self.geometry_type:
            raise ValueError("geometry_type does not match canonical_wkb")
        if bool(decoded.is_empty) != self.is_empty:
            raise ValueError("is_empty does not match canonical_wkb")
        allow_empty = self.canonicalization_policy.empty_geometry_behavior is EmptyGeometryBehavior.ALLOW_OPERATION_OUTPUT
        try:
            _normalized, expected_wkb = canonical_wkb_v1(decoded, allow_empty=allow_empty)
        except ValueError as exc:
            raise ValueError(f"canonical_wkb violates claimed canonicalization policy: {exc}") from exc
        if expected_wkb != self.canonical_wkb:
            raise ValueError("canonical_wkb is not canonical under claimed canonicalization policy")
        expected = semantic_hash({
            "canonical_geometry_hash": self.canonical_geometry_hash,
            "geometry_type": self.geometry_type.value,
            "crs_identity_id": self.crs_identity.crs_identity_id,
            "canonicalization_policy_id": self.canonicalization_policy.identity_id,
            "engine_identity_id": self.engine_identity_id,
        })
        if self.semantic_geometry_id != expected:
            raise ValueError("semantic_geometry_id does not match canonical geometry semantics")


@dataclass(frozen=True, slots=True)
class BoundaryGeometryArtifact:
    geometry_artifact_id: str
    geography_identity: GeographyIdentity
    geometry_role: str
    source_identity: GeometrySourceIdentity
    raw_artifact_ref: Optional[str]
    canonical_geometry: CanonicalGeometry
    canonical_geometry_hash: str
    canonical_geometry_encoding: str
    canonical_geometry_type: GeometryType
    canonical_crs_identity: CRSIdentity
    parser_id: str
    parser_version: str
    canonicalization_policy_id: str
    source_refs: tuple[str, ...]
    generated_at: datetime

    @property
    def engine_identity(self) -> GeometryEngineIdentity:
        return self.canonical_geometry.engine_identity

    @property
    def engine_identity_id(self) -> str:
        return self.canonical_geometry.engine_identity_id

    def __post_init__(self) -> None:
        sha256_hex(self.geometry_artifact_id, "geometry_artifact_id")
        if not isinstance(self.geography_identity, GeographyIdentity):
            raise TypeError("geography_identity must be GeographyIdentity")
        if not isinstance(self.source_identity, GeometrySourceIdentity):
            raise TypeError("source_identity must be GeometrySourceIdentity")
        if not isinstance(self.canonical_geometry, CanonicalGeometry):
            raise TypeError("canonical_geometry must be CanonicalGeometry")
        if not isinstance(self.canonical_geometry_type, GeometryType):
            raise TypeError("canonical_geometry_type must be GeometryType")
        if not isinstance(self.canonical_crs_identity, CRSIdentity):
            raise TypeError("canonical_crs_identity must be CRSIdentity")
        canonical_string(self.geometry_role, "geometry_role")
        if self.raw_artifact_ref is not None:
            canonical_string(self.raw_artifact_ref, "raw_artifact_ref")
        if self.canonical_geometry.is_empty:
            raise ValueError("boundary artifact cannot contain empty geometry")
        sha256_hex(self.canonical_geometry_hash, "canonical_geometry_hash")
        canonical_string(self.canonical_geometry_encoding, "canonical_geometry_encoding")
        if self.canonical_geometry_hash != self.canonical_geometry.canonical_geometry_hash:
            raise ValueError("boundary canonical geometry hash mismatch")
        if self.canonical_geometry_type is not self.canonical_geometry.geometry_type:
            raise ValueError("boundary canonical geometry type mismatch")
        if self.canonical_crs_identity.crs_identity_id != self.canonical_geometry.crs_identity.crs_identity_id:
            raise ValueError("boundary canonical CRS mismatch")
        if self.canonicalization_policy_id != self.canonical_geometry.canonicalization_policy_id:
            raise ValueError("boundary canonicalization policy mismatch")
        canonical_string(self.parser_id, "parser_id")
        canonical_string(self.parser_version, "parser_version")
        sha256_hex(self.canonicalization_policy_id, "canonicalization_policy_id")
        object.__setattr__(self, "source_refs", canonical_string_tuple(self.source_refs, "source_refs"))
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        expected = semantic_hash({
            "geography_identity_id": self.geography_identity.identity_id,
            "geometry_role": self.geometry_role,
            "source_identity_id": self.source_identity.source_identity_id,
            "canonical_geometry_semantic_id": self.canonical_geometry.semantic_geometry_id,
            "canonical_geometry_hash": self.canonical_geometry_hash,
            "canonical_geometry_encoding": self.canonical_geometry_encoding,
            "canonical_geometry_type": self.canonical_geometry_type.value,
            "canonical_crs_identity_id": self.canonical_crs_identity.crs_identity_id,
            "parser_id": self.parser_id,
            "parser_version": self.parser_version,
            "canonicalization_policy_id": self.canonicalization_policy_id,
            "engine_identity_id": self.engine_identity_id,
            "source_refs": self.source_refs,
        })
        if self.geometry_artifact_id != expected:
            raise ValueError("geometry_artifact_id does not match artifact semantic content")


@dataclass(frozen=True, slots=True)
class TrustedGeographyGeometryCompatibilityPolicy:
    policy_id: str
    policy_version: str
    expected_geography_type: str
    expected_demographic_definition_identity: str
    expected_geometry_definition_identity: str

    def __post_init__(self) -> None:
        for n in ("policy_id", "policy_version", "expected_geography_type", "expected_demographic_definition_identity", "expected_geometry_definition_identity"):
            canonical_string(getattr(self, n), n)

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "expected_geography_type": self.expected_geography_type,
            "expected_demographic_definition_identity": self.expected_demographic_definition_identity,
            "expected_geometry_definition_identity": self.expected_geometry_definition_identity,
        })


def _geography_geometry_compatibility_reasons(
    geography_identity: GeographyIdentity,
    demographic_definition_identity: str,
    geometry_artifact: BoundaryGeometryArtifact,
    trusted_policy: TrustedGeographyGeometryCompatibilityPolicy,
) -> tuple[str, ...]:
    canonical_string(demographic_definition_identity, "demographic_definition_identity")
    reasons: list[str] = []
    artifact_geo = geometry_artifact.geography_identity
    if geography_identity.geography_type != artifact_geo.geography_type:
        reasons.append("geography_type_mismatch")
    if geography_identity.canonical_identifier != artifact_geo.canonical_identifier:
        reasons.append("canonical_geography_identifier_mismatch")
    if geography_identity.geography_type != trusted_policy.expected_geography_type:
        reasons.append("unexpected_geography_type")
    if demographic_definition_identity != trusted_policy.expected_demographic_definition_identity:
        reasons.append("unexpected_demographic_definition_identity")
    if artifact_geo.definition_identity != trusted_policy.expected_geometry_definition_identity:
        reasons.append("unexpected_geometry_definition_identity")
    if geography_identity.definition_identity != demographic_definition_identity:
        reasons.append("actual_geography_definition_does_not_match_demographic_definition")
    return tuple(sorted(reasons))


@dataclass(frozen=True, slots=True)
class GeographyGeometryCompatibility:
    compatibility_id: str
    geography_identity: GeographyIdentity
    geometry_artifact: BoundaryGeometryArtifact
    trusted_policy: TrustedGeographyGeometryCompatibilityPolicy
    demographic_definition_identity: str
    state: CompatibilityState
    reason_codes: tuple[str, ...]

    @property
    def geography_identity_id(self) -> str:
        return self.geography_identity.identity_id

    @property
    def geometry_artifact_id(self) -> str:
        return self.geometry_artifact.geometry_artifact_id

    @property
    def policy_identity_id(self) -> str:
        return self.trusted_policy.identity_id

    def __post_init__(self) -> None:
        sha256_hex(self.compatibility_id, "compatibility_id")
        if not isinstance(self.geography_identity, GeographyIdentity):
            raise TypeError("geography_identity must be GeographyIdentity")
        if not isinstance(self.geometry_artifact, BoundaryGeometryArtifact):
            raise TypeError("geometry_artifact must be BoundaryGeometryArtifact")
        if not isinstance(self.trusted_policy, TrustedGeographyGeometryCompatibilityPolicy):
            raise TypeError("trusted_policy must be TrustedGeographyGeometryCompatibilityPolicy")
        canonical_string(self.demographic_definition_identity, "demographic_definition_identity")
        if not isinstance(self.state, CompatibilityState):
            raise TypeError("state must be CompatibilityState")
        actual_reasons = _geography_geometry_compatibility_reasons(
            self.geography_identity,
            self.demographic_definition_identity,
            self.geometry_artifact,
            self.trusted_policy,
        )
        expected_state = CompatibilityState.COMPATIBLE if not actual_reasons else CompatibilityState.INCOMPATIBLE
        supplied_reasons = canonical_string_tuple(self.reason_codes, "reason_codes", allow_empty=True)
        supplied_reasons = tuple(sorted(supplied_reasons))
        object.__setattr__(self, "reason_codes", supplied_reasons)
        if self.state is not expected_state:
            raise ValueError("compatibility state does not match attached evidence")
        if supplied_reasons != actual_reasons:
            raise ValueError("compatibility reason_codes do not match attached evidence")
        expected = semantic_hash({
            "geography_identity_id": self.geography_identity_id,
            "geometry_artifact_id": self.geometry_artifact_id,
            "policy_identity_id": self.policy_identity_id,
            "demographic_definition_identity": self.demographic_definition_identity,
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
        })
        if self.compatibility_id != expected:
            raise ValueError("compatibility_id does not match compatibility semantic content")


@dataclass(frozen=True, slots=True)
class CRSTransformPolicy:
    policy_id: str = "explicit_proj_transform"
    policy_version: str = "1.0"
    axis_order_policy: AxisOrderPolicy = AxisOrderPolicy.ALWAYS_XY
    allow_ballpark: bool = False
    require_best_available: bool = True
    network_enabled: bool = False

    def __post_init__(self) -> None:
        canonical_string(self.policy_id, "policy_id")
        canonical_string(self.policy_version, "policy_version")
        if not isinstance(self.axis_order_policy, AxisOrderPolicy):
            raise TypeError("axis_order_policy must be AxisOrderPolicy")
        if self.axis_order_policy is not AxisOrderPolicy.ALWAYS_XY:
            raise ValueError("V1 supports explicit ALWAYS_XY only")
        if self.allow_ballpark:
            raise ValueError("V1 canonical transforms forbid ballpark operations")
        if self.network_enabled:
            raise ValueError("V1 canonical transforms require PROJ network disabled")

    @property
    def identity_id(self) -> str:
        return semantic_hash({"policy_id": self.policy_id, "policy_version": self.policy_version, "axis_order_policy": self.axis_order_policy.value, "allow_ballpark": self.allow_ballpark, "require_best_available": self.require_best_available, "network_enabled": self.network_enabled})


@dataclass(frozen=True, slots=True)
class TransformPlan:
    plan_id: str
    source_crs_identity: CRSIdentity
    target_crs_identity: CRSIdentity
    transform_policy: CRSTransformPolicy
    engine_identity: GeometryEngineIdentity
    selected_pipeline_hash: str
    selected_pipeline_definition: str
    grid_identities: tuple[str, ...]

    @property
    def source_crs_identity_id(self) -> str:
        return self.source_crs_identity.crs_identity_id

    @property
    def target_crs_identity_id(self) -> str:
        return self.target_crs_identity.crs_identity_id

    @property
    def policy_identity_id(self) -> str:
        return self.transform_policy.identity_id

    @property
    def engine_identity_id(self) -> str:
        return self.engine_identity.engine_identity_id

    def __post_init__(self) -> None:
        for n in ("plan_id", "selected_pipeline_hash"):
            sha256_hex(getattr(self, n), n)
        if not isinstance(self.source_crs_identity, CRSIdentity):
            raise TypeError("source_crs_identity must be CRSIdentity")
        if not isinstance(self.target_crs_identity, CRSIdentity):
            raise TypeError("target_crs_identity must be CRSIdentity")
        if not isinstance(self.transform_policy, CRSTransformPolicy):
            raise TypeError("transform_policy must be CRSTransformPolicy")
        if not isinstance(self.engine_identity, GeometryEngineIdentity):
            raise TypeError("engine_identity must be GeometryEngineIdentity")
        canonical_string(self.selected_pipeline_definition, "selected_pipeline_definition")
        object.__setattr__(self, "grid_identities", canonical_string_tuple(self.grid_identities, "grid_identities", allow_empty=True))
        expected_pipeline_hash = semantic_hash({"definition": self.selected_pipeline_definition, "grid_identities": list(self.grid_identities)})
        if self.selected_pipeline_hash != expected_pipeline_hash:
            raise ValueError("selected_pipeline_hash does not match selected transform semantics")
        expected_plan_id = semantic_hash({
            "source_crs_identity_id": self.source_crs_identity_id,
            "target_crs_identity_id": self.target_crs_identity_id,
            "policy_identity_id": self.transform_policy.identity_id,
            "engine_identity_id": self.engine_identity_id,
            "selected_pipeline_hash": self.selected_pipeline_hash,
            "grid_identities": list(self.grid_identities),
        })
        if self.plan_id != expected_plan_id:
            raise ValueError("plan_id does not match transform plan semantic content")


@dataclass(frozen=True, slots=True)
class GeometryOperationPolicy:
    policy_id: str
    policy_version: str
    operation: GeometryOperation
    precision_policy: GeometryPrecisionPolicy
    allow_empty_result: bool = False

    def __post_init__(self) -> None:
        canonical_string(self.policy_id, "policy_id")
        canonical_string(self.policy_version, "policy_version")
        if not isinstance(self.operation, GeometryOperation):
            raise TypeError("operation must be GeometryOperation")
        if not isinstance(self.precision_policy, GeometryPrecisionPolicy):
            raise TypeError("precision_policy must be GeometryPrecisionPolicy")

    @property
    def precision_policy_id(self) -> str:
        return self.precision_policy.identity_id

    @property
    def identity_id(self) -> str:
        return semantic_hash({"policy_id": self.policy_id, "policy_version": self.policy_version, "operation": self.operation.value, "precision_policy_id": self.precision_policy.identity_id, "allow_empty_result": self.allow_empty_result})


@dataclass(frozen=True, slots=True)
class GeometryOperationResult:
    operation_id: str
    operation: GeometryOperation
    state: OperationState
    input_geometries: tuple[CanonicalGeometry, ...]
    operation_policy: GeometryOperationPolicy
    engine_identity: GeometryEngineIdentity
    transform_plan: Optional[TransformPlan] = None
    area_policy: Optional["AreaPolicy"] = None
    output_geometry: Optional[CanonicalGeometry] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    reason_codes: tuple[str, ...] = ()

    @property
    def input_geometry_ids(self) -> tuple[str, ...]:
        return tuple(sorted(g.semantic_geometry_id for g in self.input_geometries))

    @property
    def engine_identity_id(self) -> str:
        return self.engine_identity.engine_identity_id

    @property
    def operation_policy_id(self) -> str:
        return self.operation_policy.identity_id

    @property
    def area_policy_id(self) -> Optional[str]:
        return self.area_policy.identity_id if self.area_policy is not None else None

    @property
    def input_crs_identity(self) -> Optional[CRSIdentity]:
        if len(self.input_geometries) == 1:
            return self.input_geometries[0].crs_identity
        return None

    @property
    def input_crs_identity_id(self) -> Optional[str]:
        value = self.input_crs_identity
        return value.crs_identity_id if value is not None else None

    @property
    def input_geometry_precision_policy(self) -> Optional[GeometryPrecisionPolicy]:
        if len(self.input_geometries) == 1:
            return self.input_geometries[0].canonicalization_policy.precision_policy
        return None

    @property
    def transform_plan_id(self) -> Optional[str]:
        return self.transform_plan.plan_id if self.transform_plan is not None else None

    def __post_init__(self) -> None:
        sha256_hex(self.operation_id, "operation_id")
        if not isinstance(self.operation, GeometryOperation):
            raise TypeError("operation must be GeometryOperation")
        if not isinstance(self.state, OperationState):
            raise TypeError("state must be OperationState")
        if not isinstance(self.input_geometries, tuple):
            raise TypeError("input_geometries must be a tuple")
        if any(not isinstance(g, CanonicalGeometry) for g in self.input_geometries):
            raise TypeError("input_geometries must contain CanonicalGeometry objects")
        if not isinstance(self.operation_policy, GeometryOperationPolicy):
            raise TypeError("operation_policy must be GeometryOperationPolicy")
        if self.operation_policy.operation is not self.operation:
            raise ValueError("operation_policy.operation must match result.operation")
        if not isinstance(self.engine_identity, GeometryEngineIdentity):
            raise TypeError("engine_identity must be GeometryEngineIdentity")
        if self.transform_plan is not None and not isinstance(self.transform_plan, TransformPlan):
            raise TypeError("transform_plan must be TransformPlan")
        if self.area_policy is not None and not isinstance(self.area_policy, AreaPolicy):
            raise TypeError("area_policy must be AreaPolicy")
        if self.output_geometry is not None and not isinstance(self.output_geometry, CanonicalGeometry):
            raise TypeError("output_geometry must be CanonicalGeometry")
        object.__setattr__(self, "reason_codes", canonical_string_tuple(self.reason_codes, "reason_codes", allow_empty=True))
        if self.state is OperationState.SUCCESS and self.reason_codes:
            raise ValueError("SUCCESS cannot contain reason_codes")
        if self.numeric_value is not None:
            finite_number(self.numeric_value, "numeric_value")
        if (self.numeric_value is None) != (self.unit is None):
            raise ValueError("numeric_value and unit must be present together")
        if self.unit is not None:
            canonical_string(self.unit, "unit")

        geometry_ops = {GeometryOperation.CANONICALIZE, GeometryOperation.PROJECT, GeometryOperation.INTERSECT}
        if self.state is OperationState.SUCCESS:
            if self.operation in geometry_ops:
                if self.output_geometry is None or self.numeric_value is not None or self.unit is not None:
                    raise ValueError("successful geometry operation requires output_geometry only")
            elif self.operation is GeometryOperation.AREA:
                if self.output_geometry is not None or self.numeric_value is None or self.unit is None:
                    raise ValueError("successful AREA requires numeric_value and unit only")
        else:
            if self.output_geometry is not None or self.numeric_value is not None or self.unit is not None:
                raise ValueError("non-SUCCESS result must not carry successful output payload")

        if self.operation is GeometryOperation.INTERSECT:
            if self.transform_plan is not None:
                raise ValueError("INTERSECT must not carry transform_plan")
            if self.area_policy is not None:
                raise ValueError("INTERSECT must not carry area_policy")
            if self.state is OperationState.SUCCESS:
                if len(self.input_geometries) != 2:
                    raise ValueError("successful INTERSECT requires exactly two actual input geometries")
                a, b = self.input_geometries
                if a.crs_identity.crs_identity_id != b.crs_identity.crs_identity_id:
                    raise ValueError("successful INTERSECT requires matching input CRS semantics")
                for g in self.input_geometries:
                    if self.operation_policy.precision_policy.identity_id != g.canonicalization_policy.precision_policy.identity_id:
                        raise ValueError("INTERSECT operation precision must match actual input geometry precision")

        elif self.operation is GeometryOperation.PROJECT:
            if self.area_policy is not None:
                raise ValueError("PROJECT must not carry area_policy")
            if self.state is OperationState.SUCCESS and len(self.input_geometries) != 1:
                raise ValueError("successful PROJECT requires exactly one actual input geometry")
            if len(self.input_geometries) > 1:
                raise ValueError("PROJECT cannot carry more than one input geometry")
            input_geometry = self.input_geometries[0] if self.input_geometries else None
            if input_geometry is not None and self.operation_policy.precision_policy.identity_id != input_geometry.canonicalization_policy.precision_policy.identity_id:
                raise ValueError("PROJECT operation precision must match actual input geometry precision")
            if self.state is OperationState.SUCCESS and self.transform_plan is None:
                raise ValueError("successful PROJECT requires exact transform_plan")
            if self.transform_plan is not None:
                if self.transform_plan.engine_identity_id != self.engine_identity_id:
                    raise ValueError("PROJECT transform plan engine mismatch")
                if input_geometry is None:
                    raise ValueError("PROJECT transform plan requires actual input geometry evidence")
                if self.transform_plan.source_crs_identity.crs_identity_id != input_geometry.crs_identity.crs_identity_id:
                    raise ValueError("PROJECT transform plan source CRS mismatch")
                if self.output_geometry is not None and self.output_geometry.crs_identity.crs_identity_id != self.transform_plan.target_crs_identity.crs_identity_id:
                    raise ValueError("PROJECT output CRS must match transform plan target CRS")

        elif self.operation is GeometryOperation.AREA:
            if self.transform_plan is not None:
                raise ValueError("AREA must not carry transform_plan")
            if not isinstance(self.area_policy, AreaPolicy):
                raise ValueError("AREA result requires actual AreaPolicy")
            if self.state is OperationState.SUCCESS and len(self.input_geometries) != 1:
                raise ValueError("successful AREA requires exact measured CanonicalGeometry")
            if len(self.input_geometries) > 1:
                raise ValueError("AREA cannot carry more than one input geometry")
            input_geometry = self.input_geometries[0] if self.input_geometries else None
            if input_geometry is not None:
                if self.operation_policy.precision_policy.identity_id != input_geometry.canonicalization_policy.precision_policy.identity_id:
                    raise ValueError("AREA operation precision must match measured input geometry precision")
                if self.state is OperationState.SUCCESS:
                    crs = input_geometry.crs_identity
                    if not crs.is_projected or crs.is_geographic:
                        raise ValueError("successful AREA requires projected input CRS")
                    if len(crs.axis_semantics) < 2 or any(
                        abs(a.unit_conversion_factor - 1.0) > 1e-12 or a.unit_name.lower() not in {"metre", "meter"}
                        for a in crs.axis_semantics[:2]
                    ):
                        raise ValueError("successful AREA requires metre-based projected CRS")
                    if self.area_policy.output_unit != self.unit:
                        raise ValueError("AREA result unit must match AreaPolicy.output_unit")

        elif self.operation is GeometryOperation.CANONICALIZE:
            if self.transform_plan is not None or self.area_policy is not None:
                raise ValueError("CANONICALIZE must not carry transform/area policy")
        else:
            raise ValueError("unsupported geometry operation")

        if self.state is OperationState.SUCCESS and self.operation in geometry_ops and self.output_geometry is not None:
            if self.operation_policy.precision_policy.identity_id != self.output_geometry.canonicalization_policy.precision_policy.identity_id:
                raise ValueError("operation precision must match output canonical geometry precision")
            if self.engine_identity_id != self.output_geometry.engine_identity_id:
                raise ValueError("successful geometry result engine must match output geometry engine")

        if (
            self.state is OperationState.SUCCESS
            and self.operation is GeometryOperation.INTERSECT
            and self.output_geometry is not None
            and self.output_geometry.is_empty
            and not self.operation_policy.allow_empty_result
        ):
            raise ValueError("empty successful INTERSECT requires allow_empty_result=True")

        expected = semantic_hash({
            "operation": self.operation.value,
            "inputs": list(self.input_geometry_ids),
            "operation_policy_id": self.operation_policy.identity_id,
            "area_policy_id": self.area_policy.identity_id if self.area_policy is not None else None,
            "engine_id": self.engine_identity_id,
            "input_crs_identity_id": self.input_crs_identity_id,
            "input_geometry_precision_policy_id": self.input_geometry_precision_policy.identity_id if self.input_geometry_precision_policy is not None else None,
            "transform_plan_id": self.transform_plan.plan_id if self.transform_plan is not None else None,
            "output_semantic_geometry_id": self.output_geometry.semantic_geometry_id if self.output_geometry is not None else None,
            "numeric_value": self.numeric_value,
            "unit": self.unit,
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
        })
        if self.operation_id != expected:
            raise ValueError("operation_id does not match operation result semantic content")


@dataclass(frozen=True, slots=True)
class AreaPolicy:
    policy_id: str = "projected_planar_area"
    policy_version: str = "1.0"
    method_version: str = "geos-planar-area-v1"
    output_unit: str = "m2"

    def __post_init__(self) -> None:
        for n in ("policy_id", "policy_version", "method_version", "output_unit"):
            canonical_string(getattr(self, n), n)
        if self.output_unit != "m2":
            raise ValueError("V1 area output is square metres only")

    @property
    def identity_id(self) -> str:
        return semantic_hash({"policy_id": self.policy_id, "policy_version": self.policy_version, "method_version": self.method_version, "output_unit": self.output_unit})
