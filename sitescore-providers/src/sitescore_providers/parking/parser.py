"""Strict parking inventory/dynamic parsers for Checkpoint 3.3-8."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sitescore_data.schemas.parking import ParkingMode

from .._validation import require_finite_number
from ..artifacts import ArtifactRef, ArtifactStore
from ..errors import ProviderInvariantError, ProviderMalformedResponseError
from ..parsing import build_parsed_artifact
from .models import (
    CurbLegalityState,
    PARKING_DYNAMIC_MAPPING_PROFILE_ID,
    PARKING_DYNAMIC_MAPPING_PROFILE_VERSION,
    PARKING_OSM_MAPPING_PROFILE_ID,
    PARKING_OSM_MAPPING_PROFILE_VERSION,
    PARKING_NORMALIZED_MAPPING_PROFILE_ID,
    PARKING_NORMALIZED_MAPPING_PROFILE_VERSION,
    ParkingDynamicBundleEvidence,
    ParkingDynamicEvidence,
    ParkingFacilityEvidence,
    ParkingGeometryType,
    ParkingInventoryEvidence,
    ParkingMappingPolicy,
    ParkingProviderAccessState,
    ParkingSourceManifest,
    ParkingSourceRole,
    ParkingValueState,
)
from .reader import ParkingRecordReader

# NOTE: ParkingRawSourceEvidence is declared in builders.py to keep SourceMetadata
# construction next to the generic lineage builder. Import lazily in functions to
# avoid a parser/builders import cycle.

_STREET_PARKING_TYPES = frozenset({
    "lane", "street_side", "on_kerb", "half_on_kerb", "shoulder", "layby"
})
_RESTRICTIVE_ACCESS = frozenset({"private", "customers", "permit", "no"})
_RESTRICTIVE_CURB = frozenset({"no_parking", "no_stopping", "no_standing", "loading_only", "charging_only"})


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderMalformedResponseError(f"{field_name} must be a mapping")
    return value


def _text(value: Any, field_name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProviderMalformedResponseError(f"{field_name} must be a non-empty trimmed string")
    return value


def _tags(value: Any) -> dict[str, str]:
    raw = _mapping(value, "tags")
    out: dict[str, str] = {}
    for key, item in raw.items():
        if not isinstance(key, str) or not key or key != key.strip():
            raise ProviderMalformedResponseError("tag keys must be non-empty trimmed strings")
        if not isinstance(item, str) or not item or item != item.strip():
            raise ProviderMalformedResponseError("tag values must be non-empty trimmed strings")
        out[key] = item
    return out


def _geometry_type(value: Any) -> ParkingGeometryType:
    try:
        return ParkingGeometryType(value)
    except (ValueError, TypeError) as exc:
        raise ProviderMalformedResponseError("invalid parking geometry_type") from exc


def _parse_nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ProviderMalformedResponseError(f"{field_name} must not be bool")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.isdigit():
        parsed = int(value)
    else:
        raise ProviderMalformedResponseError(f"{field_name} must be an explicit nonnegative integer")
    if parsed < 0:
        raise ProviderMalformedResponseError(f"{field_name} must be nonnegative")
    return parsed


def _parse_nonnegative_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderMalformedResponseError(f"{field_name} must be finite numeric")
    try:
        require_finite_number(value, field_name=field_name)
    except (TypeError, ValueError) as exc:
        raise ProviderMalformedResponseError(str(exc)) from exc
    result = float(value)
    if result < 0:
        raise ProviderMalformedResponseError(f"{field_name} must be nonnegative")
    return result


def _parse_ratio(value: Any, field_name: str) -> float:
    result = _parse_nonnegative_float(value, field_name)
    if result > 1:
        raise ProviderMalformedResponseError(f"{field_name} must be <= 1")
    return result


def _optional_coordinates(row: Mapping[str, Any]) -> tuple[float | None, float | None]:
    lat = row.get("latitude")
    lon = row.get("longitude")
    if lat is None and lon is None:
        return None, None
    if lat is None or lon is None:
        raise ProviderMalformedResponseError("latitude and longitude must be supplied together")
    if isinstance(lat, bool) or isinstance(lon, bool) or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise ProviderMalformedResponseError("latitude/longitude must be finite numeric")
    try:
        require_finite_number(lat, field_name="latitude")
        require_finite_number(lon, field_name="longitude")
    except (TypeError, ValueError) as exc:
        raise ProviderMalformedResponseError(str(exc)) from exc
    if not -90.0 <= float(lat) <= 90.0 or not -180.0 <= float(lon) <= 180.0:
        raise ProviderMalformedResponseError("parking coordinates out of bounds")
    return float(lat), float(lon)


def _parse_timestamp(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ProviderMalformedResponseError(f"{field_name} must be ISO-8601 datetime") from exc
    else:
        raise ProviderMalformedResponseError(f"{field_name} must be datetime or ISO-8601 string")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProviderMalformedResponseError(f"{field_name} must be timezone-aware")
    return parsed


def _canonical_osm_id(entity_id: str, suffix: str | None = None) -> str:
    lowered = entity_id.lower().replace("/", ".").replace(":", ".").replace("-", "_")
    base = f"parking.osm.{lowered}"
    return f"{base}.{suffix}" if suffix else base


def _provider_access(tags: Mapping[str, str], policy: ParkingMappingPolicy) -> ParkingProviderAccessState:
    selected: str | None = None
    for key in policy.access_precedence:
        value = tags.get(key)
        if value is not None:
            selected = value.lower()
            break
    if selected in {"yes", "public"}:
        return ParkingProviderAccessState.PUBLIC
    if selected == "permissive":
        return ParkingProviderAccessState.PERMISSIVE
    if selected == "private":
        return ParkingProviderAccessState.PRIVATE
    if selected == "customers":
        return ParkingProviderAccessState.CUSTOMERS
    if selected == "permit":
        return ParkingProviderAccessState.PERMIT
    if selected in {"no", "destination", "delivery", "agricultural", "forestry"}:
        return ParkingProviderAccessState.RESTRICTED
    return ParkingProviderAccessState.UNKNOWN


def _curb_access(value: Any) -> ParkingProviderAccessState:
    if value is None:
        return ParkingProviderAccessState.UNKNOWN
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProviderMalformedResponseError("curb access must be string or null")
    selected = value.lower()
    if selected in {"yes", "public"}:
        return ParkingProviderAccessState.PUBLIC
    if selected == "permissive":
        return ParkingProviderAccessState.PERMISSIVE
    if selected == "private":
        return ParkingProviderAccessState.PRIVATE
    if selected == "customers":
        return ParkingProviderAccessState.CUSTOMERS
    if selected == "permit":
        return ParkingProviderAccessState.PERMIT
    if selected in {"no", "destination", "delivery"}:
        return ParkingProviderAccessState.RESTRICTED
    return ParkingProviderAccessState.UNKNOWN


def _capacity_from_value(value: Any) -> tuple[ParkingValueState, int | None]:
    if value is None:
        return ParkingValueState.MISSING, None
    return ParkingValueState.VALUE, _parse_nonnegative_int(value, "capacity")


def _facility_from_osm_record(*, row: Mapping[str, Any], manifest: ParkingSourceManifest,
                              mapping_policy: ParkingMappingPolicy, raw_hash, parsed_identity, source_ref: str) -> ParkingFacilityEvidence:
    kind = row.get("kind", "facility")
    if kind not in {"facility", "curb_segment"}:
        raise ProviderMalformedResponseError("parking row kind must be facility or curb_segment")
    entity_id = _text(row.get("entity_id"), "entity_id")
    assert entity_id is not None
    geometry_identity = _text(row.get("geometry_identity"), "geometry_identity")
    assert geometry_identity is not None
    geometry_type = _geometry_type(row.get("geometry_type"))
    latitude, longitude = _optional_coordinates(row)

    if kind == "curb_segment":
        source_tags = _tags(row.get("source_tags", {}))
        parking_position = _text(row.get("parking_position"), "parking_position")
        assert parking_position is not None
        if parking_position not in _STREET_PARKING_TYPES:
            raise ProviderInvariantError("curb_segment must represent an explicit physical parking position")
        if any(key.startswith("parking:lane") or key.startswith("parking:condition") for key in source_tags):
            raise ProviderInvariantError("deprecated parking:lane/parking:condition scheme is not canonical OSM V1 input")
        access = _curb_access(row.get("access"))
        restriction = row.get("restriction")
        if restriction is not None and (not isinstance(restriction, str) or not restriction or restriction != restriction.strip()):
            raise ProviderMalformedResponseError("curb restriction must be string or null")
        conditional = row.get("conditional_restrictions_present", False)
        if not isinstance(conditional, bool):
            raise ProviderMalformedResponseError("conditional_restrictions_present must be bool")
        if conditional:
            legality = CurbLegalityState.UNKNOWN
        elif restriction in _RESTRICTIVE_CURB:
            legality = CurbLegalityState.RESTRICTED
        elif restriction not in {None, "none"}:
            legality = CurbLegalityState.UNKNOWN
        elif access in {ParkingProviderAccessState.PRIVATE, ParkingProviderAccessState.CUSTOMERS,
                        ParkingProviderAccessState.PERMIT, ParkingProviderAccessState.RESTRICTED}:
            legality = CurbLegalityState.RESTRICTED
        elif access in {ParkingProviderAccessState.PUBLIC, ParkingProviderAccessState.PERMISSIVE}:
            legality = CurbLegalityState.LEGAL
        else:
            legality = CurbLegalityState.UNKNOWN
        capacity_state, capacity = _capacity_from_value(row.get("capacity"))
        length_value = row.get("curb_length_m")
        if length_value is None:
            curb_state, curb_length = ParkingValueState.MISSING, None
            method_id = method_version = None
        else:
            curb_state, curb_length = ParkingValueState.VALUE, _parse_nonnegative_float(length_value, "curb_length_m")
            method_id = _text(row.get("curb_measurement_method_id"), "curb_measurement_method_id")
            method_version = _text(row.get("curb_measurement_method_version"), "curb_measurement_method_version")
        suffix = _text(row.get("side"), "side", optional=True)
        if suffix not in {None, "left", "right"}:
            raise ProviderMalformedResponseError("curb side must be left/right/null")
        return ParkingFacilityEvidence(
            parking_id=_canonical_osm_id(entity_id, suffix), source_entity_id=entity_id,
            geometry_identity=geometry_identity, geometry_type=geometry_type,
            latitude=latitude, longitude=longitude, parking_mode=ParkingMode.ON_STREET, parking_type=parking_position,
            access_state=access, capacity_state=capacity_state, capacity=capacity,
            capacity_method_id="explicit_source_capacity", capacity_method_version=mapping_policy.mapping_profile_version,
            curb_legality_state=legality, curb_length_state=curb_state, curb_length_m=curb_length,
            curb_measurement_method_id=method_id, curb_measurement_method_version=method_version,
            fee=_text(row.get("fee"), "fee", optional=True),
            supervised=_text(row.get("supervised"), "supervised", optional=True),
            surface=_text(row.get("surface"), "surface", optional=True),
            mapping_policy_identity=mapping_policy.identity, source_manifest_identity=manifest.identity,
            raw_content_hash=raw_hash, parsed_artifact_identity=parsed_identity, source_ref=source_ref,
            source_tags=tuple(sorted(source_tags.items())),
        )

    tags = _tags(row.get("tags"))
    if tags.get("amenity") != "parking":
        raise ProviderInvariantError("OSM facility row must carry amenity=parking")
    parking_type = tags.get("parking")
    mode = ParkingMode.ON_STREET if parking_type in _STREET_PARKING_TYPES else ParkingMode.OFF_STREET
    access = _provider_access(tags, mapping_policy)
    capacity_state, capacity = _capacity_from_value(tags.get("capacity"))
    if mode is ParkingMode.OFF_STREET:
        curb_legality = CurbLegalityState.NOT_APPLICABLE
        curb_state = ParkingValueState.NOT_APPLICABLE
        curb_length = None
        method_id = method_version = None
    else:
        restriction = tags.get("restriction")
        has_conditional = any(key.startswith("restriction:conditional") or key.startswith("access:conditional") for key in tags)
        if has_conditional:
            curb_legality = CurbLegalityState.UNKNOWN
        elif restriction in _RESTRICTIVE_CURB:
            curb_legality = CurbLegalityState.RESTRICTED
        elif restriction not in {None, "none"}:
            curb_legality = CurbLegalityState.UNKNOWN
        elif access in {ParkingProviderAccessState.PUBLIC, ParkingProviderAccessState.PERMISSIVE}:
            curb_legality = CurbLegalityState.LEGAL
        elif access is ParkingProviderAccessState.UNKNOWN:
            curb_legality = CurbLegalityState.UNKNOWN
        else:
            curb_legality = CurbLegalityState.RESTRICTED
        if row.get("curb_length_m") is None:
            curb_state, curb_length = ParkingValueState.MISSING, None
            method_id = method_version = None
        else:
            curb_state, curb_length = ParkingValueState.VALUE, _parse_nonnegative_float(row.get("curb_length_m"), "curb_length_m")
            method_id = _text(row.get("curb_measurement_method_id"), "curb_measurement_method_id")
            method_version = _text(row.get("curb_measurement_method_version"), "curb_measurement_method_version")
    return ParkingFacilityEvidence(
        parking_id=_canonical_osm_id(entity_id), source_entity_id=entity_id,
        geometry_identity=geometry_identity, geometry_type=geometry_type,
        latitude=latitude, longitude=longitude, parking_mode=mode, parking_type=parking_type,
        access_state=access, capacity_state=capacity_state, capacity=capacity,
        capacity_method_id="explicit_source_capacity", capacity_method_version=mapping_policy.mapping_profile_version,
        curb_legality_state=curb_legality, curb_length_state=curb_state, curb_length_m=curb_length,
        curb_measurement_method_id=method_id, curb_measurement_method_version=method_version,
        fee=tags.get("fee"), supervised=tags.get("supervised"), surface=tags.get("surface"),
        mapping_policy_identity=mapping_policy.identity, source_manifest_identity=manifest.identity,
        raw_content_hash=raw_hash, parsed_artifact_identity=parsed_identity, source_ref=source_ref,
        source_tags=tuple(sorted(tags.items())),
    )



def _facility_from_normalized_record(*, row: Mapping[str, Any], manifest: ParkingSourceManifest,
                                     mapping_policy: ParkingMappingPolicy, raw_hash, parsed_identity, source_ref: str) -> ParkingFacilityEvidence:
    parking_id = _text(row.get("parking_id"), "parking_id")
    source_entity_id = _text(row.get("source_entity_id"), "source_entity_id")
    geometry_identity = _text(row.get("geometry_identity"), "geometry_identity")
    assert parking_id and source_entity_id and geometry_identity
    geometry_type = _geometry_type(row.get("geometry_type"))
    latitude, longitude = _optional_coordinates(row)
    try:
        mode = ParkingMode(row.get("parking_mode"))
    except (ValueError, TypeError) as exc:
        raise ProviderMalformedResponseError("invalid normalized parking_mode") from exc
    try:
        access = ParkingProviderAccessState(row.get("access_state"))
    except (ValueError, TypeError) as exc:
        raise ProviderMalformedResponseError("invalid normalized parking access_state") from exc
    capacity_state, capacity = _capacity_from_value(row.get("capacity"))
    if mode is ParkingMode.OFF_STREET:
        legality = CurbLegalityState.NOT_APPLICABLE
        curb_state, curb_length = ParkingValueState.NOT_APPLICABLE, None
        curb_method_id = curb_method_version = None
    else:
        try:
            legality = CurbLegalityState(row.get("curb_legality_state"))
        except (ValueError, TypeError) as exc:
            raise ProviderMalformedResponseError("normalized on-street record requires valid curb_legality_state") from exc
        if row.get("curb_length_m") is None:
            curb_state, curb_length = ParkingValueState.MISSING, None
            curb_method_id = curb_method_version = None
        else:
            curb_state, curb_length = ParkingValueState.VALUE, _parse_nonnegative_float(row.get("curb_length_m"), "curb_length_m")
            curb_method_id = _text(row.get("curb_measurement_method_id"), "curb_measurement_method_id")
            curb_method_version = _text(row.get("curb_measurement_method_version"), "curb_measurement_method_version")
    tags = _tags(row.get("source_tags", {}))
    return ParkingFacilityEvidence(
        parking_id=parking_id, source_entity_id=source_entity_id, geometry_identity=geometry_identity,
        geometry_type=geometry_type, latitude=latitude, longitude=longitude, parking_mode=mode, parking_type=_text(row.get("parking_type"), "parking_type", optional=True),
        access_state=access, capacity_state=capacity_state, capacity=capacity,
        capacity_method_id="explicit_source_capacity", capacity_method_version=mapping_policy.mapping_profile_version,
        curb_legality_state=legality, curb_length_state=curb_state, curb_length_m=curb_length,
        curb_measurement_method_id=curb_method_id, curb_measurement_method_version=curb_method_version,
        fee=_text(row.get("fee"), "fee", optional=True), supervised=_text(row.get("supervised"), "supervised", optional=True),
        surface=_text(row.get("surface"), "surface", optional=True), mapping_policy_identity=mapping_policy.identity,
        source_manifest_identity=manifest.identity, raw_content_hash=raw_hash, parsed_artifact_identity=parsed_identity,
        source_ref=source_ref, source_tags=tuple(sorted(tags.items())),
    )

def parse_parking_inventory(*, source_evidence, artifact_store: ArtifactStore, reader: ParkingRecordReader,
                            mapping_policy: ParkingMappingPolicy, parsed_artifact_ref: ArtifactRef) -> ParkingInventoryEvidence:
    from .builders import ParkingRawSourceEvidence
    if not isinstance(source_evidence, ParkingRawSourceEvidence):
        raise TypeError("source_evidence must be ParkingRawSourceEvidence")
    manifest = source_evidence.manifest
    if manifest.source_role is not ParkingSourceRole.STATIC_INVENTORY:
        raise ValueError("parking inventory parser requires STATIC_INVENTORY source")
    if mapping_policy.mapping_profile_id == PARKING_OSM_MAPPING_PROFILE_ID:
        if mapping_policy.mapping_profile_version != PARKING_OSM_MAPPING_PROFILE_VERSION:
            raise ValueError("unsupported OSM parking mapping profile version")
        facility_parser = _facility_from_osm_record
    elif mapping_policy.mapping_profile_id == PARKING_NORMALIZED_MAPPING_PROFILE_ID:
        if mapping_policy.mapping_profile_version != PARKING_NORMALIZED_MAPPING_PROFILE_VERSION:
            raise ValueError("unsupported normalized parking mapping profile version")
        facility_parser = _facility_from_normalized_record
    else:
        raise ValueError("unsupported parking inventory mapping profile")
    content = artifact_store.get(source_evidence.raw_artifact.artifact_ref)
    from ..hashing import sha256_bytes
    if sha256_bytes(content) != manifest.content_hash:
        raise ProviderInvariantError("stored parking inventory bytes do not match active manifest content hash")
    records = reader.read_records(content=content, manifest=manifest)
    if not isinstance(records, tuple):
        raise TypeError("ParkingRecordReader must return a tuple")
    canonical_rows = tuple(sorted((_mapping(row, "parking row") for row in records), key=lambda r: (str(r.get("entity_id")), str(r.get("side", "")))))
    parsed = build_parsed_artifact(
        raw_artifact=source_evidence.raw_artifact,
        parser_id=manifest.parser_id,
        parser_version=manifest.parser_version,
        parsed_value=canonical_rows,
        parsed_artifact_ref=parsed_artifact_ref,
    )
    facilities: dict[str, ParkingFacilityEvidence] = {}
    for row in canonical_rows:
        facility = facility_parser(
            row=row, manifest=manifest, mapping_policy=mapping_policy,
            raw_hash=source_evidence.raw_artifact.content_hash,
            parsed_identity=parsed.identity, source_ref=source_evidence.source_metadata.source_id,
        )
        prior = facilities.get(facility.parking_id)
        if prior is None:
            facilities[facility.parking_id] = facility
        elif prior != facility:
            raise ProviderInvariantError("duplicate parking entity ID has conflicting canonical evidence")
    return ParkingInventoryEvidence(
        source_manifest_identity=manifest.identity,
        mapping_policy_identity=mapping_policy.identity,
        raw_artifact=source_evidence.raw_artifact,
        parsed_artifact=parsed,
        source_ref=source_evidence.source_metadata.source_id,
        facilities=tuple(facilities[key] for key in sorted(facilities)),
    )


def _dynamic_state(value: Any, field_name: str, *, ratio: bool = False) -> tuple[ParkingValueState, int | float | None]:
    if value is None:
        return ParkingValueState.MISSING, None
    if ratio:
        return ParkingValueState.VALUE, _parse_ratio(value, field_name)
    return ParkingValueState.VALUE, _parse_nonnegative_int(value, field_name)


def parse_parking_dynamic(*, source_evidence, artifact_store: ArtifactStore, reader: ParkingRecordReader,
                          parsed_artifact_ref: ArtifactRef) -> ParkingDynamicBundleEvidence:
    from .builders import ParkingRawSourceEvidence
    if not isinstance(source_evidence, ParkingRawSourceEvidence):
        raise TypeError("source_evidence must be ParkingRawSourceEvidence")
    manifest = source_evidence.manifest
    if manifest.source_role is not ParkingSourceRole.DYNAMIC_AVAILABILITY:
        raise ValueError("dynamic parking parser requires DYNAMIC_AVAILABILITY source")
    content = artifact_store.get(source_evidence.raw_artifact.artifact_ref)
    from ..hashing import sha256_bytes
    if sha256_bytes(content) != manifest.content_hash:
        raise ProviderInvariantError("stored dynamic parking bytes do not match active manifest content hash")
    records = reader.read_records(content=content, manifest=manifest)
    if not isinstance(records, tuple):
        raise TypeError("ParkingRecordReader must return a tuple")
    canonical_rows = tuple(sorted((_mapping(row, "dynamic parking row") for row in records), key=lambda r: str(r.get("parking_id"))))
    parsed = build_parsed_artifact(
        raw_artifact=source_evidence.raw_artifact,
        parser_id=manifest.parser_id,
        parser_version=manifest.parser_version,
        parsed_value=canonical_rows,
        parsed_artifact_ref=parsed_artifact_ref,
    )
    out: dict[str, ParkingDynamicEvidence] = {}
    for row in canonical_rows:
        parking_id = _text(row.get("parking_id"), "parking_id")
        source_entity_id = _text(row.get("source_entity_id"), "source_entity_id")
        assert parking_id is not None and source_entity_id is not None
        av_state, available_spaces = _dynamic_state(row.get("available_spaces"), "available_spaces")
        occ_state, occupancy = _dynamic_state(row.get("occupancy"), "occupancy", ratio=True)
        timestamp_value = row.get("availability_timestamp")
        timestamp = _parse_timestamp(timestamp_value, "availability_timestamp") if timestamp_value is not None else None
        evidence = ParkingDynamicEvidence(
            parking_id=parking_id, source_entity_id=source_entity_id,
            available_spaces_state=av_state, available_spaces=available_spaces if isinstance(available_spaces, int) else None,
            occupancy_state=occ_state, occupancy=float(occupancy) if occupancy is not None else None,
            availability_timestamp=timestamp,
            source_manifest_identity=manifest.identity,
            raw_content_hash=source_evidence.raw_artifact.content_hash,
            parsed_artifact_identity=parsed.identity,
            source_ref=source_evidence.source_metadata.source_id,
        )
        prior = out.get(parking_id)
        if prior is None:
            out[parking_id] = evidence
        elif prior != evidence:
            raise ProviderInvariantError("duplicate dynamic parking ID has conflicting evidence")
    return ParkingDynamicBundleEvidence(
        source_manifest_identity=manifest.identity,
        raw_artifact=source_evidence.raw_artifact,
        parsed_artifact=parsed,
        source_ref=source_evidence.source_metadata.source_id,
        records=tuple(out[key] for key in sorted(out)),
    )
