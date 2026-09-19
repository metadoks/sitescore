"""Deterministic parsed-artifact construction helpers."""

from __future__ import annotations

from typing import Any

from ._validation import require_nonempty_text
from .artifacts import ArtifactRef, ParsedArtifact, RawAcquisitionArtifact
from .hashing import CANONICALIZATION_VERSION, hash_canonical


def build_parsed_artifact(
    *,
    raw_artifact: RawAcquisitionArtifact,
    parser_id: str,
    parser_version: str,
    parsed_value: Any,
    parsed_artifact_ref: ArtifactRef,
) -> ParsedArtifact:
    """Build deterministic content and derivation identities.

    ``parsed_content_hash`` hashes only the canonical parsed primitive.
    ``derivation_fingerprint`` additionally commits to raw lineage, parser
    identity/version, and the canonicalization grammar version. Therefore
    equal semantic parsed output has one content identity even when produced
    from different raw bytes or parser versions, while artifact identity
    remains lineage-aware.
    """

    if not isinstance(raw_artifact, RawAcquisitionArtifact):
        raise TypeError("raw_artifact must be a RawAcquisitionArtifact")
    require_nonempty_text(parser_id, field_name="parser_id")
    require_nonempty_text(parser_version, field_name="parser_version")
    if not isinstance(parsed_artifact_ref, ArtifactRef):
        raise TypeError("parsed_artifact_ref must be an ArtifactRef")

    parsed_content_hash = hash_canonical(parsed_value)
    derivation_fingerprint = hash_canonical(
        {
            "raw_content_hash": str(raw_artifact.content_hash),
            "parser_id": parser_id,
            "parser_version": parser_version,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "parsed_content_hash": str(parsed_content_hash),
        }
    )
    return ParsedArtifact(
        raw_content_hash=raw_artifact.content_hash,
        parser_id=parser_id,
        parser_version=parser_version,
        canonicalization_version=CANONICALIZATION_VERSION,
        parsed_content_hash=parsed_content_hash,
        derivation_fingerprint=derivation_fingerprint,
        parsed_artifact_ref=parsed_artifact_ref,
    )
