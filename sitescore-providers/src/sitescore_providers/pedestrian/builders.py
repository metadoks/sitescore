"""Pedestrian network provenance and pure frozen catchment/isochrone builders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    PersistenceClass,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue, SourceMetadata
from sitescore_data.schemas.pedestrian import IsochroneSnapshot, PedestrianCatchmentArtifact

from ..artifacts import ArtifactRef, RawAcquisitionArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from ..identity import build_request_fingerprint
from ..lineage import build_source_metadata
from ..policy import PersistenceDecision, ProviderPolicyDecision
from .client import routing_provider_identity
from .parser import validate_pedestrian_isochrone_evidence
from .models import (
    WALK_TRAVEL_MODE,
    PedestrianAreaEvidence,
    PedestrianAreaPolicy,
    PedestrianDerivationEvidence,
    PedestrianIsochroneEvidence,
    PedestrianNetworkManifest,
)

NETWORK_ACQUISITION_OPERATION = "pinned_pedestrian_network_artifact"
NETWORK_ACQUISITION_REQUEST_GRAMMAR = "v1"
NETWORK_ACQUISITION_POLICY_ID = "pinned_pedestrian_network_acquisition"
NETWORK_ACQUISITION_POLICY_VERSION = "v1"
PEDESTRIAN_FROZEN_MAPPING_GRAMMAR = "v1"
PEDESTRIAN_FROZEN_MAPPING_METHOD = "pedestrian_isochrone_mapping"


@dataclass(frozen=True, slots=True)
class PedestrianNetworkSourceEvidence:
    manifest: PedestrianNetworkManifest
    raw_artifact: RawAcquisitionArtifact
    source_metadata: SourceMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, PedestrianNetworkManifest):
            raise TypeError("manifest must be a PedestrianNetworkManifest")
        if not isinstance(self.raw_artifact, RawAcquisitionArtifact):
            raise TypeError("raw_artifact must be a RawAcquisitionArtifact")
        if not isinstance(self.source_metadata, SourceMetadata):
            raise TypeError("source_metadata must be SourceMetadata")
        if self.raw_artifact.provider_identity != self.manifest.provider_identity:
            raise ValueError("network raw provider identity must match active network manifest")
        if self.raw_artifact.content_hash != self.manifest.network_content_hash:
            raise ValueError("network raw content hash must match active network manifest")
        if self.raw_artifact.persistence.persistence_class is not PersistenceClass.PERSIST:
            raise ValueError("canonical pedestrian network source must be PERSIST for replay")
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
class PedestrianFrozenResult:
    catchments: tuple[PedestrianCatchmentArtifact, ...]
    snapshots: tuple[IsochroneSnapshot, ...]
    derivation: PedestrianDerivationEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.catchments, tuple) or not isinstance(self.snapshots, tuple):
            raise TypeError("catchments and snapshots must be tuples")
        if len(self.catchments) != len(self.snapshots) or not self.catchments:
            raise ValueError("pedestrian frozen result requires aligned non-empty catchments and snapshots")
        if not isinstance(self.derivation, PedestrianDerivationEvidence):
            raise TypeError("derivation must be PedestrianDerivationEvidence")


def build_network_request_fingerprint(manifest: PedestrianNetworkManifest):
    if not isinstance(manifest, PedestrianNetworkManifest):
        raise TypeError("manifest must be a PedestrianNetworkManifest")
    return build_request_fingerprint(
        provider_key=manifest.source_provider,
        operation=NETWORK_ACQUISITION_OPERATION,
        semantic_parameters={
            "dataset": manifest.dataset,
            "extract_id": manifest.extract_id,
            "source_release": manifest.source_release,
            "format_id": manifest.format_id,
            "format_version": manifest.format_version,
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


def build_network_source_evidence(
    *,
    manifest: PedestrianNetworkManifest,
    artifact_ref: ArtifactRef,
    retrieved_at: datetime,
    policy: ProviderPolicyDecision,
    source_reference: str | None = None,
) -> PedestrianNetworkSourceEvidence:
    if not isinstance(policy, ProviderPolicyDecision):
        raise TypeError("policy must be a ProviderPolicyDecision")
    if policy.persistence.persistence_class is not PersistenceClass.PERSIST:
        raise ValueError("canonical pinned pedestrian network source requires PERSIST policy")
    raw = RawAcquisitionArtifact(
        provider_identity=manifest.provider_identity,
        request_fingerprint=build_network_request_fingerprint(manifest),
        media_type="application/vnd.openstreetmap.data+pbf",
        content_hash=manifest.network_content_hash,
        artifact_ref=artifact_ref,
        retrieved_at=retrieved_at,
        persistence=policy.persistence,
    )
    metadata = build_source_metadata(
        raw_artifact=raw,
        data_quality=DataQualityState.FULL,
        policy=policy,
        source_reference=source_reference,
    )
    return PedestrianNetworkSourceEvidence(manifest, raw, metadata)


def build_routing_source_metadata(
    *,
    evidence: PedestrianIsochroneEvidence,
    policy: ProviderPolicyDecision,
    source_reference: str | None = None,
) -> SourceMetadata:
    if not isinstance(evidence, PedestrianIsochroneEvidence):
        raise TypeError("evidence must be PedestrianIsochroneEvidence")
    validate_pedestrian_isochrone_evidence(evidence)
    if evidence.raw_artifact.provider_identity != routing_provider_identity(evidence.request):
        raise ValueError("routing raw artifact provider identity does not match active pedestrian request")
    return build_source_metadata(
        raw_artifact=evidence.raw_artifact,
        data_quality=DataQualityState.FULL,
        policy=policy,
        source_reference=source_reference,
    )


def _validate_routing_metadata(evidence: PedestrianIsochroneEvidence, metadata: SourceMetadata) -> None:
    expected = routing_provider_identity(evidence.request)
    if (
        metadata.provider != expected.provider_key
        or metadata.dataset != expected.dataset
        or metadata.dataset_release != expected.dataset_release
        or metadata.vintage != expected.vintage
        or metadata.schema_version != expected.schema_version
        or metadata.content_hash != str(evidence.raw_artifact.content_hash)
    ):
        raise ValueError("routing SourceMetadata does not match active pedestrian routing evidence")


def _method_identity(
    *, evidence: PedestrianIsochroneEvidence, area_policy: PedestrianAreaPolicy
) -> ContentHash:
    return hash_canonical({
        "grammar_version": PEDESTRIAN_FROZEN_MAPPING_GRAMMAR,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "method": PEDESTRIAN_FROZEN_MAPPING_METHOD,
        "network_manifest_identity": str(evidence.request.graph_compatibility.network_manifest.identity),
        "graph_compatibility_identity": str(evidence.request.graph_compatibility.identity),
        "routing_engine_manifest_identity": str(evidence.request.engine_manifest.identity),
        "walking_budget_policy_identity": str(evidence.request.budget_policy.identity),
        "execution_binding_identity": str(evidence.request.execution_binding.identity),
        "execution_policy_identity": str(evidence.request.execution_binding.execution_policy.identity),
        "origin_identity": str(evidence.request.origin.identity),
        "geometry_policy_identity": str(evidence.request.geometry_policy.identity),
        "area_policy_identity": str(area_policy.identity),
    })


def build_pedestrian_frozen_result(
    *,
    evidence: PedestrianIsochroneEvidence,
    area_evidence: tuple[PedestrianAreaEvidence, ...],
    network_source: PedestrianNetworkSourceEvidence,
    routing_source_metadata: SourceMetadata,
    generated_at: datetime,
) -> PedestrianFrozenResult:
    """Map resolved network-derived evidence into one frozen pair per walking scale.

    Area calculation is deliberately external/precomputed in this checkpoint;
    each ``PedestrianAreaEvidence`` binds the numeric area to an exact geometry
    identity and a versioned area-method policy.
    """

    if not isinstance(evidence, PedestrianIsochroneEvidence):
        raise TypeError("evidence must be PedestrianIsochroneEvidence")
    validate_pedestrian_isochrone_evidence(evidence)
    if not isinstance(network_source, PedestrianNetworkSourceEvidence):
        raise TypeError("network_source must be PedestrianNetworkSourceEvidence")
    if not isinstance(routing_source_metadata, SourceMetadata):
        raise TypeError("routing_source_metadata must be SourceMetadata")
    if not isinstance(area_evidence, tuple):
        raise TypeError("area_evidence must be a tuple")
    if evidence.request.graph_compatibility.network_manifest.identity != network_source.manifest.identity:
        raise ValueError("routing graph/network manifest does not match supplied network source evidence")
    if evidence.warnings:
        raise ValueError("canonical AVAILABLE pedestrian snapshots reject unresolved Valhalla warnings")
    if evidence.routed_origin.snap_state.value != "resolved":
        raise ValueError("canonical AVAILABLE pedestrian snapshots require resolved graph snap evidence")
    _validate_routing_metadata(evidence, routing_source_metadata)

    expected_by_scale = {contour.scale_id: contour for contour in evidence.contours}
    areas_by_scale: dict[str, PedestrianAreaEvidence] = {}
    for area in area_evidence:
        if not isinstance(area, PedestrianAreaEvidence):
            raise TypeError("area_evidence entries must be PedestrianAreaEvidence")
        if area.scale_id in areas_by_scale:
            raise ValueError("duplicate pedestrian area scale")
        contour = expected_by_scale.get(area.scale_id)
        if contour is None:
            raise ValueError("area evidence references an unrequested pedestrian scale")
        if area.geometry_identity != contour.geometry.identity:
            raise ValueError("area evidence geometry identity must match contour geometry")
        areas_by_scale[area.scale_id] = area
    if set(areas_by_scale) != set(expected_by_scale):
        raise ValueError("area evidence must cover every requested pedestrian scale exactly once")

    area_policies = {str(area.area_policy.identity) for area in area_evidence}
    if len(area_policies) != 1:
        raise ValueError("all pedestrian scales in one derivation must use the same area policy identity")
    area_policy = area_evidence[0].area_policy
    method_hash = _method_identity(evidence=evidence, area_policy=area_policy)
    method_version = f"pedestrian.method.sha256_{method_hash.digest}"
    source_refs = tuple(sorted({network_source.source_metadata.source_id, routing_source_metadata.source_id}))

    catchments: list[PedestrianCatchmentArtifact] = []
    snapshots: list[IsochroneSnapshot] = []
    for scale in evidence.request.budget_policy.scales:
        contour = expected_by_scale[scale.scale_id]
        area = areas_by_scale[scale.scale_id]
        geometry_ref = f"geometry.sha256_{contour.geometry.identity.digest}"
        catchment_hash = hash_canonical({
            "method_identity": str(method_hash),
            "origin_identity": str(evidence.request.origin.identity),
            "scale_id": scale.scale_id,
            "travel_cost_seconds": float(scale.travel_cost_seconds),
            "geometry_identity": str(contour.geometry.identity),
            "source_refs": source_refs,
        })
        catchment_id = f"pedestrian.catchment.sha256_{catchment_hash.digest}"
        catchment = PedestrianCatchmentArtifact(
            catchment_id=catchment_id,
            origin_location_ref=evidence.request.origin.resolved_location_ref,
            origin_latitude=evidence.request.origin.latitude,
            origin_longitude=evidence.request.origin.longitude,
            travel_mode=WALK_TRAVEL_MODE,
            travel_cost_budget_seconds=float(scale.travel_cost_seconds),
            geometry_ref=geometry_ref,
            source_refs=source_refs,
            policy_version=method_version,
            generated_at=generated_at,
        )
        metric = MetricValue(
            value=float(area.area_km2),
            unit="km2",
            availability=AvailabilityState.AVAILABLE,
            data_quality=DataQualityState.FULL,
            score_eligibility=ScoreEligibility.DIAGNOSTIC_ONLY,
            calibration_state=CalibrationState.UNCALIBRATED,
            is_estimate=False,
            is_proxy=False,
            source_refs=source_refs,
            method_version=f"{area.area_policy.method_id}.{area.area_policy.method_version}",
            reason_codes=(),
        )
        snapshot_hash = hash_canonical({
            "method_identity": str(method_hash),
            "isochrone_evidence_identity": str(evidence.identity),
            "catchment_id": catchment_id,
            "area_evidence_identity": str(area.identity),
            "source_refs": source_refs,
        })
        snapshot = IsochroneSnapshot(
            snapshot_id=f"pedestrian.isochrone.sha256_{snapshot_hash.digest}",
            catchment_ref=catchment_id,
            area_km2=metric,
            source_refs=source_refs,
            availability=AvailabilityState.AVAILABLE,
            data_quality=DataQualityState.FULL,
            method_version=method_version,
            generated_at=generated_at,
        )
        catchments.append(catchment)
        snapshots.append(snapshot)

    derivation = PedestrianDerivationEvidence(
        isochrone_evidence_identity=evidence.identity,
        area_policy_identity=area_policy.identity,
        network_source_ref=network_source.source_metadata.source_id,
        routing_source_ref=routing_source_metadata.source_id,
        catchment_refs=tuple(c.catchment_id for c in catchments),
        snapshot_ids=tuple(s.snapshot_id for s in snapshots),
    )
    return PedestrianFrozenResult(tuple(catchments), tuple(snapshots), derivation)
