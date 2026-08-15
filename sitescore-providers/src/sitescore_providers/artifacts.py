"""Immutable acquisition and parsed-artifact lineage records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from ._validation import require_aware_datetime, require_nonempty_text, require_secret_free_reference
from .hashing import CANONICALIZATION_VERSION, ContentHash
from .identity import ProviderIdentity, RequestFingerprint
from .policy import PersistenceDecision


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    value: str

    def __post_init__(self) -> None:
        require_secret_free_reference(self.value, field_name="ArtifactRef.value")
        if "\n" in self.value or "\r" in self.value:
            raise ValueError("ArtifactRef.value must not contain line breaks")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RawAcquisitionArtifact:
    provider_identity: ProviderIdentity
    request_fingerprint: RequestFingerprint
    media_type: str
    content_hash: ContentHash
    artifact_ref: ArtifactRef
    retrieved_at: datetime
    persistence: PersistenceDecision

    def __post_init__(self) -> None:
        if not isinstance(self.provider_identity, ProviderIdentity):
            raise TypeError("provider_identity must be a ProviderIdentity")
        if not isinstance(self.request_fingerprint, RequestFingerprint):
            raise TypeError("request_fingerprint must be a RequestFingerprint")
        require_nonempty_text(self.media_type, field_name="media_type")
        if not isinstance(self.content_hash, ContentHash):
            raise TypeError("content_hash must be a ContentHash")
        if not isinstance(self.artifact_ref, ArtifactRef):
            raise TypeError("artifact_ref must be an ArtifactRef")
        require_aware_datetime(self.retrieved_at, field_name="retrieved_at")
        if not isinstance(self.persistence, PersistenceDecision):
            raise TypeError("persistence must be a PersistenceDecision")

    @property
    def identity(self) -> ContentHash:
        """Exact raw content identity; retrieval time is deliberately excluded."""
        return self.content_hash


@dataclass(frozen=True, slots=True)
class ParsedArtifact:
    raw_content_hash: ContentHash
    parser_id: str
    parser_version: str
    canonicalization_version: str
    parsed_content_hash: ContentHash
    derivation_fingerprint: ContentHash
    parsed_artifact_ref: ArtifactRef

    def __post_init__(self) -> None:
        if not isinstance(self.raw_content_hash, ContentHash):
            raise TypeError("raw_content_hash must be a ContentHash")
        require_nonempty_text(self.parser_id, field_name="parser_id")
        require_nonempty_text(self.parser_version, field_name="parser_version")
        require_nonempty_text(self.canonicalization_version, field_name="canonicalization_version")
        if self.canonicalization_version != CANONICALIZATION_VERSION:
            raise ValueError("unsupported canonicalization_version")
        if not isinstance(self.parsed_content_hash, ContentHash):
            raise TypeError("parsed_content_hash must be a ContentHash")
        if not isinstance(self.derivation_fingerprint, ContentHash):
            raise TypeError("derivation_fingerprint must be a ContentHash")
        if not isinstance(self.parsed_artifact_ref, ArtifactRef):
            raise TypeError("parsed_artifact_ref must be an ArtifactRef")

    @property
    def identity(self) -> ContentHash:
        """Lineage-aware parsed artifact identity, not content-only identity."""
        return self.derivation_fingerprint


@runtime_checkable
class ArtifactStore(Protocol):
    def put(self, *, content_hash: ContentHash, content: bytes) -> ArtifactRef:
        ...

    def get(self, artifact_ref: ArtifactRef) -> bytes:
        ...

    def exists(self, artifact_ref: ArtifactRef) -> bool:
        ...
