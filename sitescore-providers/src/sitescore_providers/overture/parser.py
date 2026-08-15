"""Strict parser for decoded Overture Places GeoParquet row mappings."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any

from ..artifacts import ArtifactRef, RawAcquisitionArtifact
from ..errors import ProviderInvariantError, ProviderMalformedResponseError
from ..lineage import build_source_metadata
from ..parsing import build_parsed_artifact
from ..policy import ProviderPolicyDecision
from sitescore_data import DataQualityState
from .reader import OverturePartitionDescriptor, build_partition_request_fingerprint
from .models import (
    OVERTURE_PARSER_ID, OvertureOperatingStatus, OverturePlaceEvidence,
    OverturePlacesReleaseManifest, OvertureSourceAttribution, OverturePartitionEvidence,
)


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderMalformedResponseError(f"{name} must be a mapping")
    return value


def _optional_cat(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProviderMalformedResponseError(f"{name} must be a non-empty string or null")
    return value


def _tuple_strings(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ProviderMalformedResponseError(f"{name} must be a list/tuple or null")
    out = tuple(value)
    if any(not isinstance(x, str) or not x or x != x.strip() for x in out):
        raise ProviderMalformedResponseError(f"{name} entries must be non-empty strings")
    if len(set(out)) != len(out):
        raise ProviderInvariantError(f"{name} entries must be unique")
    return out


def _coordinates(geometry: Any) -> tuple[float, float]:
    # Reader boundary normalizes GeoParquet WKB into a minimal provider-row point
    # primitive: {"type":"Point", "coordinates":[lon,lat]}. No geometry engine here.
    g = _mapping(geometry, "geometry")
    if g.get("type") != "Point":
        raise ProviderInvariantError("Overture Place geometry must be Point")
    coords = g.get("coordinates")
    if isinstance(coords, (str, bytes)) or not isinstance(coords, Sequence) or len(coords) != 2:
        raise ProviderMalformedResponseError("Point coordinates must contain [longitude, latitude]")
    lon, lat = coords
    if isinstance(lon, bool) or isinstance(lat, bool) or not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        raise ProviderMalformedResponseError("Point coordinates must be numeric")
    return float(lon), float(lat)


def _status(value: Any) -> OvertureOperatingStatus:
    if value is None:
        return OvertureOperatingStatus.UNKNOWN
    try:
        return OvertureOperatingStatus(value)
    except (ValueError, TypeError) as exc:
        raise ProviderMalformedResponseError("unknown Overture operating_status value") from exc


def _sources(value: Any) -> tuple[OvertureSourceAttribution, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ProviderMalformedResponseError("sources must be a sequence or null")
    out = []
    for item in value:
        src = _mapping(item, "source")
        dataset = src.get("dataset")
        if not isinstance(dataset, str) or not dataset:
            raise ProviderMalformedResponseError("source.dataset must be present")
        license_id = src.get("license")
        record_id = src.get("record_id")
        if license_id is not None and not isinstance(license_id, str):
            raise ProviderMalformedResponseError("source.license must be string or null")
        if record_id is not None:
            record_id = str(record_id)
        out.append(OvertureSourceAttribution(dataset=dataset, license_id=license_id, record_id=record_id))
    return tuple(out)


def _canonical_row(row: Mapping[str, Any]) -> dict[str, Any]:
    taxonomy = row.get("taxonomy")
    if taxonomy is None:
        primary = None
        hierarchy = ()
        alternates = ()
    else:
        tax = _mapping(taxonomy, "taxonomy")
        primary = _optional_cat(tax.get("primary"), "taxonomy.primary")
        hierarchy = _tuple_strings(tax.get("hierarchy"), "taxonomy.hierarchy")
        alternates = _tuple_strings(tax.get("alternates"), "taxonomy.alternates")
        if primary is None or not hierarchy:
            raise ProviderInvariantError("valid Overture taxonomy requires non-empty primary and hierarchy")
        if hierarchy[-1] != primary:
            raise ProviderInvariantError("taxonomy.primary must equal taxonomy.hierarchy[-1]")
        if set(alternates) & set(hierarchy):
            raise ProviderInvariantError("taxonomy.alternates must be extras outside the primary hierarchy")
    lon, lat = _coordinates(row.get("geometry"))
    confidence = row.get("confidence")
    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ProviderMalformedResponseError("confidence must be numeric or null")
        confidence = float(confidence)
    return {
        "id": row.get("id"),
        "longitude": lon,
        "latitude": lat,
        "basic_category": row.get("basic_category"),
        "taxonomy_primary": primary,
        "taxonomy_hierarchy": hierarchy,
        "taxonomy_alternates": tuple(sorted(alternates)),
        "operating_status": row.get("operating_status"),
        "confidence": confidence,
        "sources": tuple({"dataset": s.dataset, "license_id": s.license_id, "record_id": s.record_id} for s in sorted(_sources(row.get("sources")), key=lambda s: (s.dataset, s.license_id or "", s.record_id or ""))),
        "theme": row.get("theme"),
        "type": row.get("type"),
    }


def parse_overture_partition(*, raw_artifact: RawAcquisitionArtifact, records: tuple[Mapping[str, Any], ...], manifest: OverturePlacesReleaseManifest, policy: ProviderPolicyDecision, parsed_artifact_ref: ArtifactRef, source_reference: str | None = None, partition_id: str) -> OverturePartitionEvidence:
    if raw_artifact.provider_identity != manifest.provider_identity:
        raise ProviderInvariantError("raw Overture provider identity does not match release manifest")
    expected_request = build_partition_request_fingerprint(
        manifest=manifest,
        descriptor=OverturePartitionDescriptor(
            partition_id=partition_id, artifact_ref=raw_artifact.artifact_ref,
            content_hash=raw_artifact.content_hash, media_type=raw_artifact.media_type,
        ),
    )
    if raw_artifact.request_fingerprint != expected_request:
        raise ProviderInvariantError("raw Overture request fingerprint does not match pinned partition semantics")
    if not isinstance(records, tuple):
        raise TypeError("records must be a tuple")
    canonical_rows = tuple(sorted((_canonical_row(_mapping(r, "place row")) for r in records), key=lambda r: str(r["id"])))
    parsed = build_parsed_artifact(raw_artifact=raw_artifact, parser_id=OVERTURE_PARSER_ID, parser_version=manifest.parser_version, parsed_value=canonical_rows, parsed_artifact_ref=parsed_artifact_ref)
    metadata = build_source_metadata(raw_artifact=raw_artifact, data_quality=DataQualityState.FULL, policy=policy, source_reference=source_reference)
    places = []
    ids = set()
    for row in canonical_rows:
        if row["theme"] != manifest.theme or row["type"] != manifest.feature_type:
            raise ProviderInvariantError("Overture row theme/type does not match release manifest")
        place_id = row["id"]
        if not isinstance(place_id, str) or not place_id:
            raise ProviderMalformedResponseError("Overture place id must be present")
        if place_id in ids:
            prior = next(item for item in canonical_rows if item["id"] == place_id)
            if prior != row:
                raise ProviderInvariantError("duplicate Overture place ID has conflicting rows inside one partition")
            continue
        ids.add(place_id)
        places.append(OverturePlaceEvidence(
            place_id=place_id,
            longitude=row["longitude"], latitude=row["latitude"],
            basic_category=_optional_cat(row["basic_category"], "basic_category"),
            taxonomy_primary=_optional_cat(row["taxonomy_primary"], "taxonomy.primary"),
            taxonomy_hierarchy=_tuple_strings(row["taxonomy_hierarchy"], "taxonomy.hierarchy"),
            taxonomy_alternates=_tuple_strings(row["taxonomy_alternates"], "taxonomy.alternates"),
            operating_status=_status(row["operating_status"]),
            confidence=row["confidence"], source_attributions=tuple(OvertureSourceAttribution(**s) for s in row["sources"]),
            release_manifest_identity=manifest.identity, raw_content_hash=raw_artifact.content_hash,
            parsed_artifact_identity=parsed.identity, source_ref=metadata.source_id,
        ))
    return OverturePartitionEvidence(partition_id=partition_id, raw_artifact=raw_artifact, parsed_artifact=parsed, source_metadata=metadata, places=tuple(places))
