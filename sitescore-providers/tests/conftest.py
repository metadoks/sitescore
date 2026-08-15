from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sitescore_data import PersistenceClass
from sitescore_providers import (
    ArtifactRef,
    CommercialUseState,
    PersistenceDecision,
    ProviderIdentity,
    ProviderPolicyDecision,
    RawAcquisitionArtifact,
    RedistributionState,
    build_request_fingerprint,
    sha256_bytes,
)


@pytest.fixture
def aware_dt() -> datetime:
    return datetime(2026, 8, 12, 16, 0, tzinfo=timezone.utc)


@pytest.fixture
def provider_identity() -> ProviderIdentity:
    return ProviderIdentity(
        provider_key="example.provider.v1",
        domain="example_domain",
        dataset="Example Dataset",
        dataset_release="2026-08",
        vintage="2026",
        schema_version="1",
        parser_version="parser-v1",
        method_version="method-v1",
    )


@pytest.fixture
def persistence() -> PersistenceDecision:
    return PersistenceDecision(
        policy_id="example_policy",
        policy_version="v1",
        persistence_class=PersistenceClass.PERSIST,
        reason_codes=("approved_persistence",),
    )


@pytest.fixture
def policy(persistence: PersistenceDecision) -> ProviderPolicyDecision:
    return ProviderPolicyDecision(
        policy_id="example_policy",
        policy_version="v1",
        persistence=persistence,
        attribution_required=True,
        redistribution_state=RedistributionState.RESTRICTED,
        commercial_use_state=CommercialUseState.ALLOWED,
        license_class="example-license",
        policy_reference="policy://example/v1",
    )


@pytest.fixture
def raw_artifact(aware_dt, provider_identity, persistence) -> RawAcquisitionArtifact:
    fp = build_request_fingerprint(
        provider_key=provider_identity.provider_key,
        operation="fetch",
        semantic_parameters={"q": "hello", "limit": 5},
        dataset=provider_identity.dataset,
        dataset_release=provider_identity.dataset_release,
        policy_id=persistence.policy_id,
        policy_version=persistence.policy_version,
    )
    return RawAcquisitionArtifact(
        provider_identity=provider_identity,
        request_fingerprint=fp,
        media_type="application/json",
        content_hash=sha256_bytes(b'{"ok":true}'),
        artifact_ref=ArtifactRef("artifact:raw/example"),
        retrieved_at=aware_dt,
        persistence=persistence,
    )
