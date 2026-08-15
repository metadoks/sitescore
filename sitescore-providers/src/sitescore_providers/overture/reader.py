"""Backend-neutral Overture release/partition reader boundary.

Overture is distributed as GeoParquet release artifacts, not a point-query API.
This checkpoint therefore defines a reader protocol and content-addressed partition
identity without selecting S3/Azure/filesystem/Parquet implementations.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol, runtime_checkable, Any

from .._validation import require_aware_datetime, require_canonical_id, require_nonempty_text
from ..artifacts import ArtifactRef, RawAcquisitionArtifact
from ..hashing import ContentHash
from ..identity import build_request_fingerprint
from ..policy import PersistenceDecision
from .models import OverturePlacesReleaseManifest

@dataclass(frozen=True, slots=True)
class OverturePartitionDescriptor:
    partition_id: str
    artifact_ref: ArtifactRef
    content_hash: ContentHash
    media_type: str = "application/vnd.apache.parquet"

    def __post_init__(self) -> None:
        require_canonical_id(self.partition_id, field_name="partition_id")
        if not isinstance(self.artifact_ref, ArtifactRef):
            raise TypeError("artifact_ref must be ArtifactRef")
        if not isinstance(self.content_hash, ContentHash):
            raise TypeError("content_hash must be ContentHash")
        require_nonempty_text(self.media_type, field_name="media_type")


def build_partition_request_fingerprint(*, manifest: OverturePlacesReleaseManifest, descriptor: OverturePartitionDescriptor):
    if not isinstance(manifest, OverturePlacesReleaseManifest):
        raise TypeError("manifest must be OverturePlacesReleaseManifest")
    if not isinstance(descriptor, OverturePartitionDescriptor):
        raise TypeError("descriptor must be OverturePartitionDescriptor")
    return build_request_fingerprint(
        provider_key=manifest.provider_identity.provider_key,
        operation="read_release_partition",
        semantic_parameters={
            "data_release": manifest.data_release,
            "schema_version": manifest.schema_version,
            "theme": manifest.theme,
            "feature_type": manifest.feature_type,
            "partition_id": descriptor.partition_id,
            "content_hash": str(descriptor.content_hash),
        },
        dataset=manifest.provider_identity.dataset,
        dataset_release=manifest.data_release,
        policy_id=manifest.acquisition_id,
        policy_version=manifest.acquisition_version,
    )


def build_partition_raw_artifact(*, manifest: OverturePlacesReleaseManifest, descriptor: OverturePartitionDescriptor, retrieved_at: datetime, persistence: PersistenceDecision) -> RawAcquisitionArtifact:
    require_aware_datetime(retrieved_at, field_name="retrieved_at")
    return RawAcquisitionArtifact(
        provider_identity=manifest.provider_identity,
        request_fingerprint=build_partition_request_fingerprint(manifest=manifest, descriptor=descriptor),
        media_type=descriptor.media_type,
        content_hash=descriptor.content_hash,
        artifact_ref=descriptor.artifact_ref,
        retrieved_at=retrieved_at,
        persistence=persistence,
    )

@runtime_checkable
class OverturePlacesRecordReader(Protocol):
    """Decode one pinned GeoParquet partition into row mappings.

    Concrete Parquet/S3/Azure/filesystem implementations are deliberately deferred.
    """
    def read_records(self, descriptor: OverturePartitionDescriptor) -> tuple[Mapping[str, Any], ...]: ...
