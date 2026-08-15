"""Provider-neutral lineage and SourceMetadata construction."""

from __future__ import annotations

from sitescore_data import DataQualityState
from sitescore_data.schemas.common import SourceMetadata

from ._validation import require_secret_free_reference
from .artifacts import RawAcquisitionArtifact
from .hashing import hash_canonical
from .policy import ProviderPolicyDecision


def build_source_metadata(
    *,
    raw_artifact: RawAcquisitionArtifact,
    data_quality: DataQualityState,
    policy: ProviderPolicyDecision,
    source_reference: str | None = None,
) -> SourceMetadata:
    """Canonical provider-layer mapping into frozen ``SourceMetadata``."""

    if not isinstance(raw_artifact, RawAcquisitionArtifact):
        raise TypeError("raw_artifact must be a RawAcquisitionArtifact")
    if not isinstance(data_quality, DataQualityState):
        raise TypeError("data_quality must be a DataQualityState")
    if not isinstance(policy, ProviderPolicyDecision):
        raise TypeError("policy must be a ProviderPolicyDecision")
    require_secret_free_reference(source_reference, field_name="source_reference")
    if policy.persistence != raw_artifact.persistence:
        raise ValueError("policy persistence decision must match the raw artifact")

    identity = raw_artifact.provider_identity
    source_identity_hash = hash_canonical(
        {
            "provider_key": identity.provider_key,
            "dataset": identity.dataset,
            "dataset_release": identity.dataset_release,
            "vintage": identity.vintage,
            "schema_version": identity.schema_version,
            "raw_content_hash": str(raw_artifact.content_hash),
        }
    )
    source_id = f"source.{source_identity_hash.algorithm.value}_{source_identity_hash.digest}"

    return SourceMetadata(
        source_id=source_id,
        provider=identity.provider_key,
        dataset=identity.dataset,
        dataset_release=identity.dataset_release,
        vintage=identity.vintage,
        schema_version=identity.schema_version,
        retrieved_at=raw_artifact.retrieved_at,
        content_hash=str(raw_artifact.content_hash),
        persistence_class=raw_artifact.persistence.persistence_class,
        data_quality=data_quality,
        license_class=policy.license_class,
        attribution_required=policy.attribution_required,
        source_reference=source_reference,
    )
