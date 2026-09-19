"""GTFS Static acquisition boundary for exact ZIP bytes."""
from __future__ import annotations
from datetime import datetime
from .models import GTFSFeedManifest, GTFS_PROVIDER_KEY, GTFS_DATASET
from ..artifacts import ArtifactStore, RawAcquisitionArtifact
from ..hashing import sha256_bytes
from ..identity import build_request_fingerprint
from ..policy import PersistenceDecision
from ..errors import ProviderInvariantError


def build_gtfs_acquisition_fingerprint(*, manifest:GTFSFeedManifest, persistence:PersistenceDecision):
    return build_request_fingerprint(provider_key=GTFS_PROVIDER_KEY,operation="acquire_static_feed",
      semantic_parameters={"feed_id":manifest.feed_id,"dataset_release":manifest.dataset_release,"feed_content_hash":str(manifest.feed_content_hash)},
      dataset=f"{GTFS_DATASET}:{manifest.feed_id}",dataset_release=manifest.dataset_release,
      policy_id=persistence.policy_id,policy_version=persistence.policy_version)


def acquire_gtfs_zip_bytes(*, content:bytes, manifest:GTFSFeedManifest, artifact_store:ArtifactStore,
                           retrieved_at:datetime, persistence:PersistenceDecision)->RawAcquisitionArtifact:
    """Persist exact static-feed ZIP bytes; locator/download URL is deliberately not semantic identity."""
    if not isinstance(content,bytes): raise TypeError("content must be bytes")
    actual=sha256_bytes(content)
    if actual!=manifest.feed_content_hash: raise ProviderInvariantError("GTFS ZIP bytes do not match pinned manifest content hash")
    fp=build_gtfs_acquisition_fingerprint(manifest=manifest,persistence=persistence)
    ref=artifact_store.put(content_hash=actual,content=content)
    return RawAcquisitionArtifact(provider_identity=manifest.provider_identity,request_fingerprint=fp,media_type="application/zip",
      content_hash=actual,artifact_ref=ref,retrieved_at=retrieved_at,persistence=persistence)
