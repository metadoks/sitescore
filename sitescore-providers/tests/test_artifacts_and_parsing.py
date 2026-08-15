from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from sitescore_providers import ArtifactRef, RawAcquisitionArtifact, build_parsed_artifact, sha256_bytes


def test_raw_identity_is_exact_content_hash(raw_artifact):
    assert raw_artifact.identity == raw_artifact.content_hash


def test_retrieved_at_is_not_raw_identity(raw_artifact):
    later = raw_artifact.retrieved_at.replace(hour=17)
    other = RawAcquisitionArtifact(
        provider_identity=raw_artifact.provider_identity,
        request_fingerprint=raw_artifact.request_fingerprint,
        media_type=raw_artifact.media_type,
        content_hash=raw_artifact.content_hash,
        artifact_ref=raw_artifact.artifact_ref,
        retrieved_at=later,
        persistence=raw_artifact.persistence,
    )
    assert other.identity == raw_artifact.identity


def test_raw_artifact_requires_aware_datetime(raw_artifact):
    with pytest.raises(ValueError):
        RawAcquisitionArtifact(
            provider_identity=raw_artifact.provider_identity,
            request_fingerprint=raw_artifact.request_fingerprint,
            media_type=raw_artifact.media_type,
            content_hash=raw_artifact.content_hash,
            artifact_ref=raw_artifact.artifact_ref,
            retrieved_at=datetime(2026, 8, 12, 16, 0),
            persistence=raw_artifact.persistence,
        )


def test_raw_and_parsed_contracts_are_immutable(raw_artifact):
    with pytest.raises(FrozenInstanceError):
        raw_artifact.media_type = "text/plain"  # type: ignore[misc]
    parsed = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"b": 2, "a": 1},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/a"),
    )
    with pytest.raises(FrozenInstanceError):
        parsed.parser_version = "v2"  # type: ignore[misc]


def test_raw_to_parsed_lineage_deterministic(raw_artifact):
    a = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"b": 2, "a": 1},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/a"),
    )
    b = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"a": 1, "b": 2},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/b"),
    )
    assert a.raw_content_hash == raw_artifact.content_hash
    assert a.parsed_content_hash == b.parsed_content_hash


def test_different_raw_same_parsed_content_splits_content_and_derivation_identity(raw_artifact):
    other_raw = RawAcquisitionArtifact(
        provider_identity=raw_artifact.provider_identity,
        request_fingerprint=raw_artifact.request_fingerprint,
        media_type=raw_artifact.media_type,
        content_hash=sha256_bytes(b'{"ok": true, "extra": null}'),
        artifact_ref=ArtifactRef("artifact:raw/other"),
        retrieved_at=raw_artifact.retrieved_at,
        persistence=raw_artifact.persistence,
    )
    a = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"a": 1},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/a"),
    )
    b = build_parsed_artifact(
        raw_artifact=other_raw,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"a": 1},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/b"),
    )
    assert a.parsed_content_hash == b.parsed_content_hash
    assert a.derivation_fingerprint != b.derivation_fingerprint
    assert a.identity == a.derivation_fingerprint
    assert b.identity == b.derivation_fingerprint


def test_same_raw_parser_value_produces_same_both_identities(raw_artifact):
    a = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"b": 2, "a": 1},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/a"),
    )
    b = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"a": 1, "b": 2},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/b"),
    )
    assert a.parsed_content_hash == b.parsed_content_hash
    assert a.derivation_fingerprint == b.derivation_fingerprint
    assert a.identity == b.identity


def test_parser_version_changes_derivation_not_content_identity(raw_artifact):
    a = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v1",
        parsed_value={"a": 1},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/a"),
    )
    b = build_parsed_artifact(
        raw_artifact=raw_artifact,
        parser_id="json_parser",
        parser_version="v2",
        parsed_value={"a": 1},
        parsed_artifact_ref=ArtifactRef("artifact:parsed/b"),
    )
    assert a.parsed_content_hash == b.parsed_content_hash
    assert a.derivation_fingerprint != b.derivation_fingerprint


@pytest.mark.parametrize(
    "ref",
    [
        "artifact:https://example.test/x?api_key=secret",
        "https://user:password@example.test/object",
        "artifact://bucket/object?access_token=secret",
    ],
)
def test_artifact_ref_rejects_obvious_credentials(ref):
    with pytest.raises(ValueError):
        ArtifactRef(ref)
