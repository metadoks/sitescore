"""Immutable parking source, policy, reachability, and evidence contracts (Checkpoint 3.3-8)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from sitescore_data.schemas.parking import ParkingMode

from .._validation import (
    require_aware_datetime,
    require_canonical_id,
    require_finite_number,
    require_nonempty_text,
    require_optional_nonempty_text,
)
from ..artifacts import ParsedArtifact, RawAcquisitionArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from ..identity import ProviderIdentity

PARKING_SOURCE_MANIFEST_GRAMMAR = "v1"
PARKING_SOURCE_BUNDLE_GRAMMAR = "v1"
PARKING_MAPPING_POLICY_GRAMMAR = "v1"
PARKING_COVERAGE_GRAMMAR = "v1"
PARKING_FACILITY_EVIDENCE_GRAMMAR = "v1"
PARKING_DYNAMIC_EVIDENCE_GRAMMAR = "v1"
PARKING_ELIGIBILITY_POLICY_GRAMMAR = "v1"
PARKING_MOTOR_REACHABILITY_GRAMMAR = "v1"
PARKING_PEDESTRIAN_REACHABILITY_GRAMMAR = "v1"
PARKING_ACCESSIBILITY_COMPATIBILITY_GRAMMAR = "v1"
PARKING_DYNAMIC_LINK_POLICY_GRAMMAR = "v1"
PARKING_DERIVATION_GRAMMAR = "v1"

PARKING_OSM_MAPPING_PROFILE_ID = "osm_parking_tags"
PARKING_OSM_MAPPING_PROFILE_VERSION = "v1"
PARKING_DYNAMIC_MAPPING_PROFILE_ID = "parking_dynamic_values"
PARKING_DYNAMIC_MAPPING_PROFILE_VERSION = "v1"
PARKING_NORMALIZED_MAPPING_PROFILE_ID = "normalized_parking_inventory"
PARKING_NORMALIZED_MAPPING_PROFILE_VERSION = "v1"
PARKING_STATIC_PARSER_ID = "parking_static_records"
PARKING_DYNAMIC_PARSER_ID = "parking_dynamic_records"


class ParkingSourceRole(StrEnum):
    STATIC_INVENTORY = "static_inventory"
    DYNAMIC_AVAILABILITY = "dynamic_availability"


class ParkingSourceAuthority(StrEnum):
    AUTHORITATIVE = "authoritative"
    COMMUNITY_MAPPED = "community_mapped"
    OTHER = "other"
    UNKNOWN = "unknown"


class ParkingSourceCompleteness(StrEnum):
    EXHAUSTIVE = "exhaustive"
    NON_EXHAUSTIVE = "non_exhaustive"
    UNKNOWN = "unknown"


class ParkingCoverageState(StrEnum):
    SUFFICIENT = "sufficient"
    UNKNOWN = "unknown"
    INSUFFICIENT = "insufficient"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class ParkingValueState(StrEnum):
    VALUE = "value"
    MISSING = "missing"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ParkingProviderAccessState(StrEnum):
    PUBLIC = "public"
    PERMISSIVE = "permissive"
    PRIVATE = "private"
    CUSTOMERS = "customers"
    PERMIT = "permit"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class ParkingEligibilityState(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"


class CurbLegalityState(StrEnum):
    LEGAL = "legal"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ParkingReachabilityState(StrEnum):
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class ParkingGeometryType(StrEnum):
    NODE = "node"
    WAY = "way"
    RELATION = "relation"
    OTHER = "other"


class ParkingDynamicLinkageMode(StrEnum):
    SHARED_CANONICAL_PARKING_ID = "shared_canonical_parking_id"


def _reject_mutable_identity(value: str, *, field_name: str) -> str:
    require_nonempty_text(value, field_name=field_name)
    lowered = value.lower()
    mutable_tokens = {"latest", "current", "live", "today", "now"}
    if lowered in mutable_tokens or "latest" in lowered or "current" in lowered:
        raise ValueError(f"{field_name} must be immutable/pinned, not mutable latest/current/live identity")
    return value


def _require_tuple(value: tuple[Any, ...], *, field_name: str) -> tuple[Any, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    return value


def _require_unique_refs(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    _require_tuple(values, field_name=field_name)
    for item in values:
        require_canonical_id(item, field_name=f"{field_name} item")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


def _validate_optional_coordinates(latitude: float | None, longitude: float | None) -> None:
    if (latitude is None) != (longitude is None):
        raise ValueError("parking latitude/longitude must both be supplied or both be None")
    if latitude is None:
        return
    require_finite_number(latitude, field_name="latitude")
    require_finite_number(longitude, field_name="longitude")
    if not -90.0 <= float(latitude) <= 90.0:
        raise ValueError("latitude must be in [-90, 90]")
    if not -180.0 <= float(longitude) <= 180.0:
        raise ValueError("longitude must be in [-180, 180]")


def _validate_numeric_state(*, state: ParkingValueState, value: int | float | None, field_name: str,
                            integer: bool = False, minimum: float | None = None,
                            maximum: float | None = None) -> None:
    if not isinstance(state, ParkingValueState):
        raise TypeError(f"{field_name}_state must be a ParkingValueState")
    if state is ParkingValueState.VALUE:
        if value is None:
            raise ValueError(f"{field_name} VALUE state requires a numeric value")
        require_finite_number(value, field_name=field_name)
        if integer and (isinstance(value, bool) or not isinstance(value, int)):
            raise TypeError(f"{field_name} must be an int when state=VALUE")
        number = float(value)
        if minimum is not None and number < minimum:
            raise ValueError(f"{field_name} must be >= {minimum}")
        if maximum is not None and number > maximum:
            raise ValueError(f"{field_name} must be <= {maximum}")
    elif value is not None:
        raise ValueError(f"{field_name} must be None when state != VALUE")


@dataclass(frozen=True, slots=True)
class ParkingSourceManifest:
    manifest_version: str
    source_role: ParkingSourceRole
    source_provider: str
    dataset: str
    dataset_release: str
    vintage: str | None
    schema_id: str
    schema_version: str
    media_type: str
    content_hash: ContentHash
    parser_id: str
    parser_version: str
    acquisition_id: str
    acquisition_version: str
    authority: ParkingSourceAuthority
    completeness: ParkingSourceCompleteness

    def __post_init__(self) -> None:
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        if not isinstance(self.source_role, ParkingSourceRole):
            raise TypeError("source_role must be a ParkingSourceRole")
        require_canonical_id(self.source_provider, field_name="source_provider")
        require_nonempty_text(self.dataset, field_name="dataset")
        _reject_mutable_identity(self.dataset_release, field_name="dataset_release")
        if self.vintage is not None:
            _reject_mutable_identity(self.vintage, field_name="vintage")
        require_canonical_id(self.schema_id, field_name="schema_id")
        require_nonempty_text(self.schema_version, field_name="schema_version")
        require_nonempty_text(self.media_type, field_name="media_type")
        if self.media_type != self.media_type.strip():
            raise ValueError("media_type must be trimmed")
        if not isinstance(self.content_hash, ContentHash):
            raise TypeError("content_hash must be a ContentHash")
        require_canonical_id(self.parser_id, field_name="parser_id")
        require_nonempty_text(self.parser_version, field_name="parser_version")
        require_canonical_id(self.acquisition_id, field_name="acquisition_id")
        require_nonempty_text(self.acquisition_version, field_name="acquisition_version")
        if not isinstance(self.authority, ParkingSourceAuthority):
            raise TypeError("authority must be a ParkingSourceAuthority")
        if not isinstance(self.completeness, ParkingSourceCompleteness):
            raise TypeError("completeness must be a ParkingSourceCompleteness")
        if self.source_provider == "openstreetmap":
            if self.authority is not ParkingSourceAuthority.COMMUNITY_MAPPED:
                raise ValueError("OpenStreetMap parking sources must remain COMMUNITY_MAPPED evidence")
            if self.completeness is ParkingSourceCompleteness.EXHAUSTIVE:
                raise ValueError("OpenStreetMap parking sources cannot claim authoritative exhaustive inventory semantics")
        if self.source_role is ParkingSourceRole.STATIC_INVENTORY and self.parser_id != PARKING_STATIC_PARSER_ID:
            raise ValueError(f"V1 static parking source requires parser_id={PARKING_STATIC_PARSER_ID}")
        if self.source_role is ParkingSourceRole.DYNAMIC_AVAILABILITY and self.parser_id != PARKING_DYNAMIC_PARSER_ID:
            raise ValueError(f"V1 dynamic parking source requires parser_id={PARKING_DYNAMIC_PARSER_ID}")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_SOURCE_MANIFEST_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "manifest_version": self.manifest_version,
            "source_role": self.source_role.value,
            "source_provider": self.source_provider,
            "dataset": self.dataset,
            "dataset_release": self.dataset_release,
            "vintage": self.vintage,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "media_type": self.media_type,
            "content_hash": str(self.content_hash),
            "parser_id": self.parser_id,
            "parser_version": self.parser_version,
            "acquisition_id": self.acquisition_id,
            "acquisition_version": self.acquisition_version,
            "authority": self.authority.value,
            "completeness": self.completeness.value,
        })

    @property
    def provider_identity(self) -> ProviderIdentity:
        domain = "parking_inventory" if self.source_role is ParkingSourceRole.STATIC_INVENTORY else "parking_dynamic"
        return ProviderIdentity(
            provider_key=self.source_provider,
            domain=domain,
            dataset=self.dataset,
            dataset_release=self.dataset_release,
            vintage=self.vintage,
            schema_version=self.schema_version,
            parser_version=self.parser_version,
            method_version=f"{self.acquisition_id}.{self.acquisition_version}",
        )


@dataclass(frozen=True, slots=True)
class ParkingDynamicLinkPolicy:
    policy_id: str
    policy_version: str
    inventory_manifest_identity: ContentHash
    dynamic_manifest_identity: ContentHash
    linkage_mode: ParkingDynamicLinkageMode = ParkingDynamicLinkageMode.SHARED_CANONICAL_PARKING_ID
    mapping_profile_id: str = PARKING_DYNAMIC_MAPPING_PROFILE_ID
    mapping_profile_version: str = PARKING_DYNAMIC_MAPPING_PROFILE_VERSION

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if not isinstance(self.inventory_manifest_identity, ContentHash):
            raise TypeError("inventory_manifest_identity must be a ContentHash")
        if not isinstance(self.dynamic_manifest_identity, ContentHash):
            raise TypeError("dynamic_manifest_identity must be a ContentHash")
        if not isinstance(self.linkage_mode, ParkingDynamicLinkageMode):
            raise TypeError("linkage_mode must be a ParkingDynamicLinkageMode")
        if self.linkage_mode is not ParkingDynamicLinkageMode.SHARED_CANONICAL_PARKING_ID:
            raise ValueError("V1 supports only SHARED_CANONICAL_PARKING_ID dynamic linkage")
        if self.mapping_profile_id != PARKING_DYNAMIC_MAPPING_PROFILE_ID:
            raise ValueError("V1 dynamic linkage must use the canonical parking dynamic mapping profile")
        if self.mapping_profile_version != PARKING_DYNAMIC_MAPPING_PROFILE_VERSION:
            raise ValueError("unsupported parking dynamic mapping profile version")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_DYNAMIC_LINK_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "inventory_manifest_identity": str(self.inventory_manifest_identity),
            "dynamic_manifest_identity": str(self.dynamic_manifest_identity),
            "linkage_mode": self.linkage_mode.value,
            "mapping_profile_id": self.mapping_profile_id,
            "mapping_profile_version": self.mapping_profile_version,
        })


@dataclass(frozen=True, slots=True)
class ParkingSourceBundle:
    bundle_id: str
    bundle_version: str
    inventory_manifest: ParkingSourceManifest
    dynamic_manifest: ParkingSourceManifest | None = None
    dynamic_link_policy: ParkingDynamicLinkPolicy | None = None

    def __post_init__(self) -> None:
        require_canonical_id(self.bundle_id, field_name="bundle_id")
        require_nonempty_text(self.bundle_version, field_name="bundle_version")
        if not isinstance(self.inventory_manifest, ParkingSourceManifest):
            raise TypeError("inventory_manifest must be a ParkingSourceManifest")
        if self.inventory_manifest.source_role is not ParkingSourceRole.STATIC_INVENTORY:
            raise ValueError("inventory_manifest must have STATIC_INVENTORY role")
        if self.dynamic_manifest is None:
            if self.dynamic_link_policy is not None:
                raise ValueError("dynamic_link_policy cannot be supplied without dynamic_manifest")
        else:
            if not isinstance(self.dynamic_manifest, ParkingSourceManifest):
                raise TypeError("dynamic_manifest must be a ParkingSourceManifest or None")
            if self.dynamic_manifest.source_role is not ParkingSourceRole.DYNAMIC_AVAILABILITY:
                raise ValueError("dynamic_manifest must have DYNAMIC_AVAILABILITY role")
            if not isinstance(self.dynamic_link_policy, ParkingDynamicLinkPolicy):
                raise ValueError("dynamic_manifest requires explicit ParkingDynamicLinkPolicy")
            if self.dynamic_link_policy.inventory_manifest_identity != self.inventory_manifest.identity:
                raise ValueError("dynamic link policy is bound to a foreign inventory manifest")
            if self.dynamic_link_policy.dynamic_manifest_identity != self.dynamic_manifest.identity:
                raise ValueError("dynamic link policy is bound to a foreign dynamic manifest")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_SOURCE_BUNDLE_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "bundle_id": self.bundle_id,
            "bundle_version": self.bundle_version,
            "inventory_manifest_identity": str(self.inventory_manifest.identity),
            "dynamic_manifest_identity": str(self.dynamic_manifest.identity) if self.dynamic_manifest else None,
            "dynamic_link_policy_identity": str(self.dynamic_link_policy.identity) if self.dynamic_link_policy else None,
        })


@dataclass(frozen=True, slots=True)
class ParkingMappingPolicy:
    policy_id: str
    policy_version: str
    mapping_profile_id: str
    mapping_profile_version: str
    access_precedence: tuple[str, ...] = ("motor_vehicle", "vehicle", "access")
    street_parking_scheme: str = "parking_side"
    capacity_semantics: str = "explicit_numeric_only"
    curb_semantics: str = "explicit_legal_segment_length_only"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        require_canonical_id(self.mapping_profile_id, field_name="mapping_profile_id")
        require_nonempty_text(self.mapping_profile_version, field_name="mapping_profile_version")
        _require_tuple(self.access_precedence, field_name="access_precedence")
        if self.mapping_profile_id == PARKING_OSM_MAPPING_PROFILE_ID:
            if self.mapping_profile_version != PARKING_OSM_MAPPING_PROFILE_VERSION:
                raise ValueError("unsupported OSM parking mapping profile version")
            if self.access_precedence != ("motor_vehicle", "vehicle", "access"):
                raise ValueError("OSM V1 parking access precedence is motor_vehicle > vehicle > access")
            if self.street_parking_scheme != "parking_side":
                raise ValueError("OSM V1 requires current parking:<side> street-parking semantics")
            if self.capacity_semantics != "explicit_numeric_only":
                raise ValueError("OSM V1 capacity must be explicit numeric source evidence only")
            if self.curb_semantics != "explicit_legal_segment_length_only":
                raise ValueError("OSM V1 curb supply requires explicitly evidenced legal segment length")
        elif self.mapping_profile_id == PARKING_NORMALIZED_MAPPING_PROFILE_ID:
            if self.mapping_profile_version != PARKING_NORMALIZED_MAPPING_PROFILE_VERSION:
                raise ValueError("unsupported normalized parking mapping profile version")
            if self.capacity_semantics != "explicit_numeric_only" or self.curb_semantics != "explicit_legal_segment_length_only":
                raise ValueError("normalized V1 parking mapping keeps explicit capacity/curb evidence only")
        else:
            raise ValueError("unsupported parking mapping profile")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_MAPPING_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "mapping_profile_id": self.mapping_profile_id,
            "mapping_profile_version": self.mapping_profile_version,
            "access_precedence": self.access_precedence,
            "street_parking_scheme": self.street_parking_scheme,
            "capacity_semantics": self.capacity_semantics,
            "curb_semantics": self.curb_semantics,
        })


@dataclass(frozen=True, slots=True)
class ParkingCoverageEvidence:
    source_manifest_identity: ContentHash
    query_scope_id: str
    state: ParkingCoverageState
    observed_record_count: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.source_manifest_identity, ContentHash):
            raise TypeError("source_manifest_identity must be a ContentHash")
        require_canonical_id(self.query_scope_id, field_name="query_scope_id")
        if not isinstance(self.state, ParkingCoverageState):
            raise TypeError("state must be a ParkingCoverageState")
        if self.state in {ParkingCoverageState.FAILED, ParkingCoverageState.UNSUPPORTED}:
            if self.observed_record_count is not None:
                raise ValueError("FAILED/UNSUPPORTED coverage cannot claim observed record count")
        else:
            if isinstance(self.observed_record_count, bool) or not isinstance(self.observed_record_count, int):
                raise TypeError("successful/partial coverage requires integer observed_record_count")
            if self.observed_record_count < 0:
                raise ValueError("observed_record_count must be nonnegative")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_COVERAGE_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "source_manifest_identity": str(self.source_manifest_identity),
            "query_scope_id": self.query_scope_id,
            "state": self.state.value,
            "observed_record_count": self.observed_record_count,
        })


@dataclass(frozen=True, slots=True)
class ParkingFacilityEvidence:
    parking_id: str
    source_entity_id: str
    geometry_identity: str
    geometry_type: ParkingGeometryType
    latitude: float | None
    longitude: float | None
    parking_mode: ParkingMode
    parking_type: str | None
    access_state: ParkingProviderAccessState
    capacity_state: ParkingValueState
    capacity: int | None
    capacity_method_id: str
    capacity_method_version: str
    curb_legality_state: CurbLegalityState
    curb_length_state: ParkingValueState
    curb_length_m: float | None
    curb_measurement_method_id: str | None
    curb_measurement_method_version: str | None
    fee: str | None
    supervised: str | None
    surface: str | None
    mapping_policy_identity: ContentHash
    source_manifest_identity: ContentHash
    raw_content_hash: ContentHash
    parsed_artifact_identity: ContentHash
    source_ref: str
    source_tags: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        require_canonical_id(self.parking_id, field_name="parking_id")
        require_nonempty_text(self.source_entity_id, field_name="source_entity_id")
        require_canonical_id(self.geometry_identity, field_name="geometry_identity")
        if not isinstance(self.geometry_type, ParkingGeometryType):
            raise TypeError("geometry_type must be a ParkingGeometryType")
        _validate_optional_coordinates(self.latitude, self.longitude)
        if not isinstance(self.parking_mode, ParkingMode):
            raise TypeError("parking_mode must be a ParkingMode")
        require_optional_nonempty_text(self.parking_type, field_name="parking_type")
        if not isinstance(self.access_state, ParkingProviderAccessState):
            raise TypeError("access_state must be a ParkingProviderAccessState")
        _validate_numeric_state(state=self.capacity_state, value=self.capacity, field_name="capacity", integer=True, minimum=0)
        require_canonical_id(self.capacity_method_id, field_name="capacity_method_id")
        require_nonempty_text(self.capacity_method_version, field_name="capacity_method_version")
        if not isinstance(self.curb_legality_state, CurbLegalityState):
            raise TypeError("curb_legality_state must be a CurbLegalityState")
        _validate_numeric_state(state=self.curb_length_state, value=self.curb_length_m, field_name="curb_length_m", minimum=0)
        if self.parking_mode is ParkingMode.OFF_STREET:
            if self.curb_legality_state is not CurbLegalityState.NOT_APPLICABLE:
                raise ValueError("OFF_STREET parking requires NOT_APPLICABLE curb legality")
            if self.curb_length_state is not ParkingValueState.NOT_APPLICABLE:
                raise ValueError("OFF_STREET parking requires NOT_APPLICABLE curb length")
        else:
            if self.curb_legality_state is CurbLegalityState.NOT_APPLICABLE:
                raise ValueError("ON_STREET parking requires explicit curb legality state")
        if self.curb_length_state is ParkingValueState.VALUE:
            if self.curb_measurement_method_id is None or self.curb_measurement_method_version is None:
                raise ValueError("explicit curb length requires measurement method identity/version")
            require_canonical_id(self.curb_measurement_method_id, field_name="curb_measurement_method_id")
            require_nonempty_text(self.curb_measurement_method_version, field_name="curb_measurement_method_version")
        elif self.curb_measurement_method_id is not None or self.curb_measurement_method_version is not None:
            raise ValueError("curb measurement method is only valid with explicit curb length VALUE")
        require_optional_nonempty_text(self.fee, field_name="fee")
        require_optional_nonempty_text(self.supervised, field_name="supervised")
        require_optional_nonempty_text(self.surface, field_name="surface")
        for name, value in (
            ("mapping_policy_identity", self.mapping_policy_identity),
            ("source_manifest_identity", self.source_manifest_identity),
            ("raw_content_hash", self.raw_content_hash),
            ("parsed_artifact_identity", self.parsed_artifact_identity),
        ):
            if not isinstance(value, ContentHash):
                raise TypeError(f"{name} must be a ContentHash")
        require_canonical_id(self.source_ref, field_name="source_ref")
        _require_tuple(self.source_tags, field_name="source_tags")
        keys = []
        for item in self.source_tags:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("source_tags must contain (key, value) tuples")
            key, value = item
            require_nonempty_text(key, field_name="source tag key")
            require_nonempty_text(value, field_name="source tag value")
            keys.append(key)
        if len(keys) != len(set(keys)):
            raise ValueError("source_tags must not duplicate keys")
        if self.source_tags != tuple(sorted(self.source_tags)):
            raise ValueError("source_tags must be canonically sorted")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_FACILITY_EVIDENCE_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "parking_id": self.parking_id,
            "source_entity_id": self.source_entity_id,
            "geometry_identity": self.geometry_identity,
            "geometry_type": self.geometry_type.value,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "parking_mode": self.parking_mode.value,
            "parking_type": self.parking_type,
            "access_state": self.access_state.value,
            "capacity_state": self.capacity_state.value,
            "capacity": self.capacity,
            "capacity_method_id": self.capacity_method_id,
            "capacity_method_version": self.capacity_method_version,
            "curb_legality_state": self.curb_legality_state.value,
            "curb_length_state": self.curb_length_state.value,
            "curb_length_m": self.curb_length_m,
            "curb_measurement_method_id": self.curb_measurement_method_id,
            "curb_measurement_method_version": self.curb_measurement_method_version,
            "fee": self.fee,
            "supervised": self.supervised,
            "surface": self.surface,
            "mapping_policy_identity": str(self.mapping_policy_identity),
            "source_manifest_identity": str(self.source_manifest_identity),
            "raw_content_hash": str(self.raw_content_hash),
            "parsed_artifact_identity": str(self.parsed_artifact_identity),
            "source_ref": self.source_ref,
            "source_tags": self.source_tags,
        })


@dataclass(frozen=True, slots=True)
class ParkingDynamicEvidence:
    parking_id: str
    source_entity_id: str
    available_spaces_state: ParkingValueState
    available_spaces: int | None
    occupancy_state: ParkingValueState
    occupancy: float | None
    availability_timestamp: datetime | None
    source_manifest_identity: ContentHash
    raw_content_hash: ContentHash
    parsed_artifact_identity: ContentHash
    source_ref: str

    def __post_init__(self) -> None:
        require_canonical_id(self.parking_id, field_name="parking_id")
        require_nonempty_text(self.source_entity_id, field_name="source_entity_id")
        _validate_numeric_state(state=self.available_spaces_state, value=self.available_spaces,
                                field_name="available_spaces", integer=True, minimum=0)
        _validate_numeric_state(state=self.occupancy_state, value=self.occupancy,
                                field_name="occupancy", minimum=0, maximum=1)
        dynamic_available = self.available_spaces_state is ParkingValueState.VALUE or self.occupancy_state is ParkingValueState.VALUE
        if dynamic_available:
            if self.availability_timestamp is None:
                raise ValueError("dynamic VALUE evidence requires availability_timestamp")
            require_aware_datetime(self.availability_timestamp, field_name="availability_timestamp")
        elif self.availability_timestamp is not None:
            require_aware_datetime(self.availability_timestamp, field_name="availability_timestamp")
        for name, value in (
            ("source_manifest_identity", self.source_manifest_identity),
            ("raw_content_hash", self.raw_content_hash),
            ("parsed_artifact_identity", self.parsed_artifact_identity),
        ):
            if not isinstance(value, ContentHash):
                raise TypeError(f"{name} must be a ContentHash")
        require_canonical_id(self.source_ref, field_name="source_ref")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_DYNAMIC_EVIDENCE_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "parking_id": self.parking_id,
            "source_entity_id": self.source_entity_id,
            "available_spaces_state": self.available_spaces_state.value,
            "available_spaces": self.available_spaces,
            "occupancy_state": self.occupancy_state.value,
            "occupancy": self.occupancy,
            "availability_timestamp": self.availability_timestamp,
            "source_manifest_identity": str(self.source_manifest_identity),
            "raw_content_hash": str(self.raw_content_hash),
            "parsed_artifact_identity": str(self.parsed_artifact_identity),
            "source_ref": self.source_ref,
        })


@dataclass(frozen=True, slots=True)
class ParkingInventoryEvidence:
    source_manifest_identity: ContentHash
    mapping_policy_identity: ContentHash
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact
    source_ref: str
    facilities: tuple[ParkingFacilityEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_manifest_identity, ContentHash):
            raise TypeError("source_manifest_identity must be a ContentHash")
        if not isinstance(self.mapping_policy_identity, ContentHash):
            raise TypeError("mapping_policy_identity must be a ContentHash")
        if not isinstance(self.raw_artifact, RawAcquisitionArtifact):
            raise TypeError("raw_artifact must be RawAcquisitionArtifact")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be ParsedArtifact")
        if self.parsed_artifact.raw_content_hash != self.raw_artifact.content_hash:
            raise ValueError("parsed parking artifact must derive from supplied raw artifact")
        require_canonical_id(self.source_ref, field_name="source_ref")
        _require_tuple(self.facilities, field_name="facilities")
        for facility in self.facilities:
            if not isinstance(facility, ParkingFacilityEvidence):
                raise TypeError("facilities must contain ParkingFacilityEvidence")
            if facility.source_manifest_identity != self.source_manifest_identity:
                raise ValueError("facility source manifest identity mismatch")
            if facility.mapping_policy_identity != self.mapping_policy_identity:
                raise ValueError("facility mapping policy identity mismatch")
            if facility.raw_content_hash != self.raw_artifact.content_hash:
                raise ValueError("facility raw-content lineage mismatch")
            if facility.parsed_artifact_identity != self.parsed_artifact.identity:
                raise ValueError("facility parsed-artifact lineage mismatch")
            if facility.source_ref != self.source_ref:
                raise ValueError("facility source_ref mismatch")
        ids = tuple(f.parking_id for f in self.facilities)
        if ids != tuple(sorted(ids)):
            raise ValueError("parking facilities must be deterministically ordered by parking_id")
        if len(ids) != len(set(ids)):
            raise ValueError("parking facility IDs must be unique")


@dataclass(frozen=True, slots=True)
class ParkingDynamicBundleEvidence:
    source_manifest_identity: ContentHash
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact
    source_ref: str
    records: tuple[ParkingDynamicEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_manifest_identity, ContentHash):
            raise TypeError("source_manifest_identity must be a ContentHash")
        if not isinstance(self.raw_artifact, RawAcquisitionArtifact):
            raise TypeError("raw_artifact must be RawAcquisitionArtifact")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be ParsedArtifact")
        if self.parsed_artifact.raw_content_hash != self.raw_artifact.content_hash:
            raise ValueError("parsed dynamic artifact must derive from supplied raw artifact")
        require_canonical_id(self.source_ref, field_name="source_ref")
        _require_tuple(self.records, field_name="records")
        for record in self.records:
            if not isinstance(record, ParkingDynamicEvidence):
                raise TypeError("records must contain ParkingDynamicEvidence")
            if record.source_manifest_identity != self.source_manifest_identity:
                raise ValueError("dynamic record source manifest mismatch")
            if record.raw_content_hash != self.raw_artifact.content_hash:
                raise ValueError("dynamic record raw-content lineage mismatch")
            if record.parsed_artifact_identity != self.parsed_artifact.identity:
                raise ValueError("dynamic record parsed-artifact lineage mismatch")
            if record.source_ref != self.source_ref:
                raise ValueError("dynamic record source_ref mismatch")
        ids = tuple(r.parking_id for r in self.records)
        if ids != tuple(sorted(ids)):
            raise ValueError("dynamic records must be deterministically ordered by parking_id")
        if len(ids) != len(set(ids)):
            raise ValueError("dynamic parking IDs must be unique")


@dataclass(frozen=True, slots=True)
class ParkingEligibilityPolicy:
    policy_id: str
    policy_version: str
    eligible_access_states: tuple[ParkingProviderAccessState, ...] = (
        ParkingProviderAccessState.PUBLIC,
        ParkingProviderAccessState.PERMISSIVE,
    )
    subject_property_private_qualification: bool = False

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        _require_tuple(self.eligible_access_states, field_name="eligible_access_states")
        if self.eligible_access_states != (ParkingProviderAccessState.PUBLIC, ParkingProviderAccessState.PERMISSIVE):
            raise ValueError("V1 generic parking eligibility is limited to PUBLIC and PERMISSIVE access")
        if not isinstance(self.subject_property_private_qualification, bool):
            raise TypeError("subject_property_private_qualification must be a bool")
        if self.subject_property_private_qualification:
            raise ValueError("V1 does not auto-qualify subject-property private/customer parking")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_ELIGIBILITY_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "eligible_access_states": tuple(x.value for x in self.eligible_access_states),
            "subject_property_private_qualification": self.subject_property_private_qualification,
        })


@dataclass(frozen=True, slots=True)
class ParkingMotorReachabilityRecord:
    parking_id: str
    state: ParkingReachabilityState

    def __post_init__(self) -> None:
        require_canonical_id(self.parking_id, field_name="parking_id")
        if not isinstance(self.state, ParkingReachabilityState):
            raise TypeError("state must be a ParkingReachabilityState")


@dataclass(frozen=True, slots=True)
class ParkingMotorReachabilityEvidence:
    source_manifest_identity: ContentHash
    road_derivation_identity: ContentHash
    graph_compatibility_identity: ContentHash
    drive_budget_policy_identity: ContentHash
    method_id: str
    method_version: str
    source_refs: tuple[str, ...]
    records: tuple[ParkingMotorReachabilityRecord, ...]

    def __post_init__(self) -> None:
        for name in ("source_manifest_identity", "road_derivation_identity", "graph_compatibility_identity", "drive_budget_policy_identity"):
            if not isinstance(getattr(self, name), ContentHash):
                raise TypeError(f"{name} must be a ContentHash")
        require_canonical_id(self.method_id, field_name="method_id")
        require_nonempty_text(self.method_version, field_name="method_version")
        _require_unique_refs(self.source_refs, field_name="source_refs")
        _require_tuple(self.records, field_name="records")
        for record in self.records:
            if not isinstance(record, ParkingMotorReachabilityRecord):
                raise TypeError("records must contain ParkingMotorReachabilityRecord")
        ids = tuple(r.parking_id for r in self.records)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("motor reachability records must be uniquely sorted by parking_id")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_MOTOR_REACHABILITY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "source_manifest_identity": str(self.source_manifest_identity),
            "road_derivation_identity": str(self.road_derivation_identity),
            "graph_compatibility_identity": str(self.graph_compatibility_identity),
            "drive_budget_policy_identity": str(self.drive_budget_policy_identity),
            "method_id": self.method_id,
            "method_version": self.method_version,
            "source_refs": self.source_refs,
            "records": tuple((r.parking_id, r.state.value) for r in self.records),
        })


@dataclass(frozen=True, slots=True)
class ParkingPedestrianReachabilityRecord:
    parking_id: str
    state: ParkingReachabilityState
    walk_time_to_site_seconds: float | None

    def __post_init__(self) -> None:
        require_canonical_id(self.parking_id, field_name="parking_id")
        if not isinstance(self.state, ParkingReachabilityState):
            raise TypeError("state must be a ParkingReachabilityState")
        if self.state is ParkingReachabilityState.REACHABLE:
            if self.walk_time_to_site_seconds is None:
                raise ValueError("REACHABLE pedestrian evidence requires walk_time_to_site_seconds")
            require_finite_number(self.walk_time_to_site_seconds, field_name="walk_time_to_site_seconds")
            if self.walk_time_to_site_seconds < 0:
                raise ValueError("walk_time_to_site_seconds must be nonnegative")
        elif self.walk_time_to_site_seconds is not None:
            raise ValueError("non-REACHABLE pedestrian evidence cannot carry walk time")


@dataclass(frozen=True, slots=True)
class ParkingPedestrianReachabilityEvidence:
    source_manifest_identity: ContentHash
    pedestrian_derivation_identity: ContentHash
    walking_budget_policy_identity: ContentHash
    method_id: str
    method_version: str
    source_refs: tuple[str, ...]
    records: tuple[ParkingPedestrianReachabilityRecord, ...]

    def __post_init__(self) -> None:
        for name in ("source_manifest_identity", "pedestrian_derivation_identity", "walking_budget_policy_identity"):
            if not isinstance(getattr(self, name), ContentHash):
                raise TypeError(f"{name} must be a ContentHash")
        require_canonical_id(self.method_id, field_name="method_id")
        require_nonempty_text(self.method_version, field_name="method_version")
        _require_unique_refs(self.source_refs, field_name="source_refs")
        _require_tuple(self.records, field_name="records")
        for record in self.records:
            if not isinstance(record, ParkingPedestrianReachabilityRecord):
                raise TypeError("records must contain ParkingPedestrianReachabilityRecord")
        ids = tuple(r.parking_id for r in self.records)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("pedestrian reachability records must be uniquely sorted by parking_id")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_PEDESTRIAN_REACHABILITY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "source_manifest_identity": str(self.source_manifest_identity),
            "pedestrian_derivation_identity": str(self.pedestrian_derivation_identity),
            "walking_budget_policy_identity": str(self.walking_budget_policy_identity),
            "method_id": self.method_id,
            "method_version": self.method_version,
            "source_refs": self.source_refs,
            "records": tuple((r.parking_id, r.state.value, r.walk_time_to_site_seconds) for r in self.records),
        })




@dataclass(frozen=True, slots=True)
class ParkingAccessibilityCompatibility:
    compatibility_id: str
    compatibility_version: str
    expected_road_derivation_identity: ContentHash
    expected_graph_compatibility_identity: ContentHash
    expected_drive_budget_policy_identity: ContentHash
    expected_pedestrian_derivation_identity: ContentHash
    expected_walking_budget_policy_identity: ContentHash

    def __post_init__(self) -> None:
        require_canonical_id(self.compatibility_id, field_name="compatibility_id")
        require_nonempty_text(self.compatibility_version, field_name="compatibility_version")
        for name in (
            "expected_road_derivation_identity",
            "expected_graph_compatibility_identity",
            "expected_drive_budget_policy_identity",
            "expected_pedestrian_derivation_identity",
            "expected_walking_budget_policy_identity",
        ):
            if not isinstance(getattr(self, name), ContentHash):
                raise TypeError(f"{name} must be a ContentHash")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_ACCESSIBILITY_COMPATIBILITY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "compatibility_id": self.compatibility_id,
            "compatibility_version": self.compatibility_version,
            "expected_road_derivation_identity": str(self.expected_road_derivation_identity),
            "expected_graph_compatibility_identity": str(self.expected_graph_compatibility_identity),
            "expected_drive_budget_policy_identity": str(self.expected_drive_budget_policy_identity),
            "expected_pedestrian_derivation_identity": str(self.expected_pedestrian_derivation_identity),
            "expected_walking_budget_policy_identity": str(self.expected_walking_budget_policy_identity),
        })


@dataclass(frozen=True, slots=True)
class ParkingFacilityDecisionEvidence:
    parking_id: str
    eligibility: ParkingEligibilityState
    motor_reachability: ParkingReachabilityState
    pedestrian_reachability: ParkingReachabilityState
    usable: bool | None

    def __post_init__(self) -> None:
        require_canonical_id(self.parking_id, field_name="parking_id")
        if not isinstance(self.eligibility, ParkingEligibilityState):
            raise TypeError("eligibility must be ParkingEligibilityState")
        if not isinstance(self.motor_reachability, ParkingReachabilityState):
            raise TypeError("motor_reachability must be ParkingReachabilityState")
        if not isinstance(self.pedestrian_reachability, ParkingReachabilityState):
            raise TypeError("pedestrian_reachability must be ParkingReachabilityState")
        if self.usable is not None and not isinstance(self.usable, bool):
            raise TypeError("usable must be bool or None")


@dataclass(frozen=True, slots=True)
class ParkingDerivationEvidence:
    source_bundle_identity: ContentHash
    coverage_identity: ContentHash
    mapping_policy_identity: ContentHash
    eligibility_policy_identity: ContentHash
    accessibility_compatibility_identity: ContentHash
    motor_reachability_identity: ContentHash
    pedestrian_reachability_identity: ContentHash
    dynamic_link_policy_identity: ContentHash | None
    dynamic_bundle_identity: ContentHash | None
    facility_evidence_ids: tuple[str, ...]
    dynamic_evidence_ids: tuple[str, ...]
    decisions: tuple[ParkingFacilityDecisionEvidence, ...]
    measurement_identity: ContentHash
    snapshot_id: str

    def __post_init__(self) -> None:
        for name in (
            "source_bundle_identity", "coverage_identity", "mapping_policy_identity",
            "eligibility_policy_identity", "accessibility_compatibility_identity",
            "motor_reachability_identity", "pedestrian_reachability_identity", "measurement_identity",
        ):
            if not isinstance(getattr(self, name), ContentHash):
                raise TypeError(f"{name} must be a ContentHash")
        if self.dynamic_link_policy_identity is not None and not isinstance(self.dynamic_link_policy_identity, ContentHash):
            raise TypeError("dynamic_link_policy_identity must be ContentHash or None")
        if self.dynamic_bundle_identity is not None and not isinstance(self.dynamic_bundle_identity, ContentHash):
            raise TypeError("dynamic_bundle_identity must be ContentHash or None")
        _require_unique_refs(self.facility_evidence_ids, field_name="facility_evidence_ids")
        _require_unique_refs(self.dynamic_evidence_ids, field_name="dynamic_evidence_ids")
        _require_tuple(self.decisions, field_name="decisions")
        ids = tuple(d.parking_id for d in self.decisions)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("decisions must be uniquely ordered by parking_id")
        require_canonical_id(self.snapshot_id, field_name="snapshot_id")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PARKING_DERIVATION_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "source_bundle_identity": str(self.source_bundle_identity),
            "coverage_identity": str(self.coverage_identity),
            "mapping_policy_identity": str(self.mapping_policy_identity),
            "eligibility_policy_identity": str(self.eligibility_policy_identity),
            "accessibility_compatibility_identity": str(self.accessibility_compatibility_identity),
            "motor_reachability_identity": str(self.motor_reachability_identity),
            "pedestrian_reachability_identity": str(self.pedestrian_reachability_identity),
            "dynamic_link_policy_identity": str(self.dynamic_link_policy_identity) if self.dynamic_link_policy_identity else None,
            "dynamic_bundle_identity": str(self.dynamic_bundle_identity) if self.dynamic_bundle_identity else None,
            "facility_evidence_ids": self.facility_evidence_ids,
            "dynamic_evidence_ids": self.dynamic_evidence_ids,
            "decisions": tuple({
                "parking_id": d.parking_id,
                "eligibility": d.eligibility.value,
                "motor_reachability": d.motor_reachability.value,
                "pedestrian_reachability": d.pedestrian_reachability.value,
                "usable": d.usable,
            } for d in self.decisions),
            "measurement_identity": str(self.measurement_identity),
            "snapshot_id": self.snapshot_id,
        })
