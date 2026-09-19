from __future__ import annotations

from sitescore_data import DataQualityState
from sitescore_data.schemas.common import SourceMetadata
from sitescore_providers import build_source_metadata


def test_source_metadata_mapping(raw_artifact, policy):
    result = build_source_metadata(
        raw_artifact=raw_artifact,
        data_quality=DataQualityState.FULL,
        policy=policy,
        source_reference="artifact:raw/example",
    )
    identity = raw_artifact.provider_identity
    assert isinstance(result, SourceMetadata)
    assert result.provider == identity.provider_key
    assert result.dataset == identity.dataset
    assert result.dataset_release == identity.dataset_release
    assert result.vintage == identity.vintage
    assert result.schema_version == identity.schema_version
    assert result.retrieved_at == raw_artifact.retrieved_at
    assert result.content_hash == str(raw_artifact.content_hash)
    assert result.persistence_class == raw_artifact.persistence.persistence_class
    assert result.data_quality is DataQualityState.FULL
    assert result.license_class == policy.license_class
    assert result.attribution_required is True
    assert result.source_reference == "artifact:raw/example"
    assert result.source_id.startswith("source.sha256_")


def test_source_metadata_id_deterministic(raw_artifact, policy):
    a = build_source_metadata(raw_artifact=raw_artifact, data_quality=DataQualityState.FULL, policy=policy)
    b = build_source_metadata(raw_artifact=raw_artifact, data_quality=DataQualityState.FULL, policy=policy)
    assert a.source_id == b.source_id


def test_policy_must_match_raw_persistence(raw_artifact, policy):
    from sitescore_data import PersistenceClass
    from sitescore_providers import PersistenceDecision, ProviderPolicyDecision

    other_persistence = PersistenceDecision(
        policy_id="other_policy",
        policy_version="v1",
        persistence_class=PersistenceClass.PERSIST,
    )
    mismatched = ProviderPolicyDecision(
        policy_id="other_policy",
        policy_version="v1",
        persistence=other_persistence,
        attribution_required=policy.attribution_required,
        redistribution_state=policy.redistribution_state,
        commercial_use_state=policy.commercial_use_state,
    )
    import pytest
    with pytest.raises(ValueError):
        build_source_metadata(raw_artifact=raw_artifact, data_quality=DataQualityState.FULL, policy=mismatched)


def test_source_metadata_rejects_credential_bearing_reference(raw_artifact, policy):
    import pytest
    with pytest.raises(ValueError):
        build_source_metadata(
            raw_artifact=raw_artifact,
            data_quality=DataQualityState.FULL,
            policy=policy,
            source_reference="https://example.test/source?token=secret",
        )
