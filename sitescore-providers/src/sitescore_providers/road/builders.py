"""Road network provenance and pure RoadAccessSnapshot builders."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from sitescore_data import AvailabilityState, DataQualityState, PersistenceClass
from sitescore_data.schemas.common import SourceMetadata
from sitescore_data.schemas.road import RoadAccessSnapshot, RoadObservation, RoadOriginQuality

from ..artifacts import ArtifactRef, ArtifactStore, RawAcquisitionArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical, sha256_bytes
from ..identity import build_request_fingerprint
from ..lineage import build_source_metadata
from ..policy import ProviderPolicyDecision
from .client import routing_provider_identity
from .parser import validate_road_isochrone_evidence
from .models import (
    RoadDerivationEvidence,
    RoadIsochroneEvidence,
    RoadNetworkManifest,
    RoadScaleMeasurementEvidence,
    ROAD_MEASUREMENT_POLICY_GRAMMAR,
)

NETWORK_ACQUISITION_OPERATION = "pinned_road_network_artifact"
NETWORK_ACQUISITION_REQUEST_GRAMMAR = "v1"
NETWORK_ACQUISITION_POLICY_ID = "pinned_road_network_acquisition"
NETWORK_ACQUISITION_POLICY_VERSION = "v1"
ROAD_FROZEN_MAPPING_GRAMMAR = "v1"
ROAD_FROZEN_MAPPING_METHOD = "road_isochrone_mapping.v1"


@dataclass(frozen=True, slots=True)
class RoadNetworkSourceEvidence:
    manifest: RoadNetworkManifest
    raw_artifact: RawAcquisitionArtifact
    source_metadata: SourceMetadata

    def __post_init__(self) -> None:
        if self.raw_artifact.provider_identity != self.manifest.provider_identity:
            raise ValueError("network raw provider identity must match active network manifest")
        if self.raw_artifact.content_hash != self.manifest.network_content_hash:
            raise ValueError("network raw content hash must match active network manifest")
        if self.raw_artifact.media_type != self.manifest.media_type:
            raise ValueError("network raw media_type must match active network manifest")
        if self.raw_artifact.persistence.persistence_class is not PersistenceClass.PERSIST:
            raise ValueError("canonical road network source must be PERSIST for replay")
        identity = self.raw_artifact.provider_identity
        if (
            self.source_metadata.provider != identity.provider_key
            or self.source_metadata.dataset != identity.dataset
            or self.source_metadata.dataset_release != identity.dataset_release
            or self.source_metadata.vintage != identity.vintage
            or self.source_metadata.schema_version != identity.schema_version
            or self.source_metadata.content_hash != str(self.raw_artifact.content_hash)
            or self.source_metadata.persistence_class is not PersistenceClass.PERSIST
        ):
            raise ValueError("network SourceMetadata must match network raw artifact semantics")


@dataclass(frozen=True, slots=True)
class RoadFrozenResult:
    snapshot: RoadAccessSnapshot
    derivation: RoadDerivationEvidence


def build_network_request_fingerprint(manifest: RoadNetworkManifest):
    return build_request_fingerprint(
        provider_key=manifest.source_provider,
        operation=NETWORK_ACQUISITION_OPERATION,
        semantic_parameters={
            "dataset": manifest.dataset,
            "extract_id": manifest.extract_id,
            "source_release": manifest.source_release,
            "format_id": manifest.format_id,
            "format_version": manifest.format_version,
            "media_type": manifest.media_type,
            "network_content_hash": str(manifest.network_content_hash),
            "acquisition_id": manifest.acquisition_id,
            "acquisition_version": manifest.acquisition_version,
        },
        dataset=manifest.dataset,
        dataset_release=manifest.source_release,
        policy_id=NETWORK_ACQUISITION_POLICY_ID,
        policy_version=NETWORK_ACQUISITION_POLICY_VERSION,
        grammar_version=NETWORK_ACQUISITION_REQUEST_GRAMMAR,
    )


def build_network_source_evidence(*, manifest: RoadNetworkManifest, artifact_ref: ArtifactRef,
                                  artifact_store: ArtifactStore, retrieved_at: datetime,
                                  policy: ProviderPolicyDecision, source_reference: str | None = None) -> RoadNetworkSourceEvidence:
    if policy.persistence.persistence_class is not PersistenceClass.PERSIST:
        raise ValueError("canonical pinned road network source requires PERSIST policy")
    actual = artifact_store.get(artifact_ref)
    if sha256_bytes(actual) != manifest.network_content_hash:
        raise ValueError("persisted network artifact bytes do not match RoadNetworkManifest.network_content_hash")
    raw = RawAcquisitionArtifact(
        provider_identity=manifest.provider_identity,
        request_fingerprint=build_network_request_fingerprint(manifest),
        media_type=manifest.media_type,
        content_hash=manifest.network_content_hash,
        artifact_ref=artifact_ref,
        retrieved_at=retrieved_at,
        persistence=policy.persistence,
    )
    metadata = build_source_metadata(raw_artifact=raw, data_quality=DataQualityState.FULL,
                                     policy=policy, source_reference=source_reference)
    return RoadNetworkSourceEvidence(manifest, raw, metadata)


def build_routing_source_metadata(*, evidence: RoadIsochroneEvidence, policy: ProviderPolicyDecision,
                                  source_reference: str | None = None) -> SourceMetadata:
    validate_road_isochrone_evidence(evidence)
    if evidence.raw_artifact.provider_identity != routing_provider_identity(evidence.request):
        raise ValueError("routing raw artifact provider identity does not match active road request")
    return build_source_metadata(raw_artifact=evidence.raw_artifact, data_quality=DataQualityState.FULL,
                                 policy=policy, source_reference=source_reference)


def _validate_routing_metadata(evidence: RoadIsochroneEvidence, metadata: SourceMetadata) -> None:
    expected = routing_provider_identity(evidence.request)
    if (
        metadata.provider != expected.provider_key
        or metadata.dataset != expected.dataset
        or metadata.dataset_release != expected.dataset_release
        or metadata.vintage != expected.vintage
        or metadata.schema_version != expected.schema_version
        or metadata.content_hash != str(evidence.raw_artifact.content_hash)
    ):
        raise ValueError("routing SourceMetadata does not match active road routing evidence")


def build_measurement_policy_identity(*, evidence: RoadIsochroneEvidence, measurements: tuple[RoadScaleMeasurementEvidence, ...]) -> ContentHash:
    if not isinstance(measurements, tuple):
        raise TypeError("measurements must be a tuple")
    by_scale: dict[str, RoadScaleMeasurementEvidence] = {}
    for measurement in measurements:
        if not isinstance(measurement, RoadScaleMeasurementEvidence):
            raise TypeError("measurements must contain RoadScaleMeasurementEvidence")
        if measurement.scale_id in by_scale:
            raise ValueError("duplicate road measurement scale")
        by_scale[measurement.scale_id] = measurement
    expected = tuple(scale.scale_id for scale in evidence.request.budget_policy.scales)
    if set(by_scale) != set(expected):
        raise ValueError("road measurements must cover every requested scale exactly once")
    return hash_canonical({
        "grammar_version": ROAD_MEASUREMENT_POLICY_GRAMMAR,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "per_scale_methods": tuple({
            "scale_id": scale_id,
            "area_policy_identity": str(by_scale[scale_id].area_policy.identity),
            "network_measurement_method_id": by_scale[scale_id].network_measurement_method_id,
            "network_measurement_method_version": by_scale[scale_id].network_measurement_method_version,
        } for scale_id in expected),
    })


def _method_identity(evidence: RoadIsochroneEvidence, measurements: tuple[RoadScaleMeasurementEvidence, ...]) -> ContentHash:
    measurement_policy_identity = build_measurement_policy_identity(evidence=evidence, measurements=measurements)
    return hash_canonical({
        "grammar_version": ROAD_FROZEN_MAPPING_GRAMMAR,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "method": ROAD_FROZEN_MAPPING_METHOD,
        "network_manifest_identity": str(evidence.request.graph_compatibility.network_manifest.identity),
        "graph_compatibility_identity": str(evidence.request.graph_compatibility.identity),
        "routing_engine_manifest_identity": str(evidence.request.engine_manifest.identity),
        "drive_budget_policy_identity": str(evidence.request.budget_policy.identity),
        "execution_binding_identity": str(evidence.request.execution_binding.identity),
        "origin_identity": str(evidence.request.origin.identity),
        "geometry_policy_identity": str(evidence.request.geometry_policy.identity),
        "measurement_policy_identity": str(measurement_policy_identity),
    })


def build_road_access_snapshot(*, evidence: RoadIsochroneEvidence,
                               measurements: tuple[RoadScaleMeasurementEvidence, ...],
                               network_source: RoadNetworkSourceEvidence,
                               routing_source_metadata: SourceMetadata,
                               generated_at: datetime) -> RoadFrozenResult:
    validate_road_isochrone_evidence(evidence)
    if evidence.request.graph_compatibility.network_manifest.identity != network_source.manifest.identity:
        raise ValueError("routing graph/network manifest does not match supplied network source evidence")
    if evidence.warnings:
        raise ValueError("canonical AVAILABLE road snapshot rejects unresolved Valhalla warnings")
    if evidence.routed_origin.snap_state.value != "resolved":
        raise ValueError("canonical AVAILABLE road snapshot requires resolved road snap evidence")
    if evidence.routed_origin.road_origin_quality is RoadOriginQuality.UNRESOLVED:
        raise ValueError("canonical AVAILABLE road snapshot requires resolved road origin quality")
    _validate_routing_metadata(evidence, routing_source_metadata)
    if not isinstance(measurements, tuple):
        raise TypeError("measurements must be a tuple")
    by_scale: dict[str, RoadScaleMeasurementEvidence] = {}
    contours = {c.scale_id: c for c in evidence.contours}
    for m in measurements:
        if not isinstance(m, RoadScaleMeasurementEvidence):
            raise TypeError("measurements must contain RoadScaleMeasurementEvidence")
        if m.scale_id in by_scale:
            raise ValueError("duplicate road measurement scale")
        contour = contours.get(m.scale_id)
        if contour is None or m.geometry_identity != contour.geometry.identity:
            raise ValueError("road measurement geometry must bind exact returned contour")
        by_scale[m.scale_id] = m
    expected = tuple(s.scale_id for s in evidence.request.budget_policy.scales)
    if set(by_scale) != set(expected):
        raise ValueError("road measurements must cover every requested scale exactly once")
    source_refs = tuple(sorted({network_source.source_metadata.source_id, routing_source_metadata.source_id}))
    method_hash = _method_identity(evidence, measurements)
    method_version = f"road.method.sha256_{method_hash.digest}"
    observations = tuple(
        RoadObservation(
            travel_cost_seconds=float(scale.travel_cost_seconds),
            reachable_area_km2=float(by_scale[scale.scale_id].reachable_area_km2),
            reachable_network_length_km=float(by_scale[scale.scale_id].reachable_network_length_km),
            reachable_connector_count=by_scale[scale.scale_id].reachable_connector_count,
            origin_to_network_cost_seconds=float(by_scale[scale.scale_id].origin_to_network_cost_seconds),
            benchmark_percentile=None,
            source_refs=source_refs,
            method_version=method_version,
        )
        for scale in evidence.request.budget_policy.scales
    )
    road_origin_ref = f"road.origin.sha256_{evidence.request.origin.identity.digest}"
    snapshot_hash = hash_canonical({
        "method_identity": str(method_hash),
        "evidence_identity": str(evidence.identity),
        "measurement_ids": tuple(str(by_scale[s].identity) for s in expected),
        "road_origin_ref": road_origin_ref,
        "source_refs": source_refs,
    })
    snapshot_id = f"road.snapshot.sha256_{snapshot_hash.digest}"
    snapshot = RoadAccessSnapshot(
        snapshot_id=snapshot_id,
        road_origin_ref=road_origin_ref,
        road_origin_quality=evidence.routed_origin.road_origin_quality,
        routing_profile_id=evidence.request.engine_manifest.costing_profile_id,
        routing_profile_version=evidence.request.engine_manifest.costing_profile_version,
        observations=observations,
        benchmark_ref=None,
        source_refs=source_refs,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        generated_at=generated_at,
    )
    measurement_policy_identity = build_measurement_policy_identity(evidence=evidence, measurements=measurements)
    derivation = RoadDerivationEvidence(
        isochrone_evidence_identity=evidence.identity,
        measurement_policy_identity=measurement_policy_identity,
        network_source_ref=network_source.source_metadata.source_id,
        routing_source_ref=routing_source_metadata.source_id,
        measurement_evidence_ids=tuple(f"road.measurement.sha256_{by_scale[s].identity.digest}" for s in expected),
        snapshot_id=snapshot_id,
    )
    return RoadFrozenResult(snapshot, derivation)
