from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sitescore_data import PersistenceClass
from sitescore_providers import PersistenceDecision, ProviderPolicyDecision


def test_transient_requires_retention_constraint():
    with pytest.raises(ValueError):
        PersistenceDecision(
            policy_id="p",
            policy_version="v1",
            persistence_class=PersistenceClass.TRANSIENT,
        )


def test_transient_allows_aware_expiry():
    decision = PersistenceDecision(
        policy_id="p",
        policy_version="v1",
        persistence_class=PersistenceClass.TRANSIENT,
        expires_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
    )
    assert decision.persistence_class is PersistenceClass.TRANSIENT


def test_persist_rejects_expiry():
    with pytest.raises(ValueError):
        PersistenceDecision(
            policy_id="p",
            policy_version="v1",
            persistence_class=PersistenceClass.PERSIST,
            max_retention_seconds=10,
        )


def test_do_not_persist_rejects_expiry():
    with pytest.raises(ValueError):
        PersistenceDecision(
            policy_id="p",
            policy_version="v1",
            persistence_class=PersistenceClass.DO_NOT_PERSIST,
            max_retention_seconds=10,
        )



def test_transient_allows_max_retention_only():
    decision = PersistenceDecision(
        policy_id="p",
        policy_version="v1",
        persistence_class=PersistenceClass.TRANSIENT,
        max_retention_seconds=3600,
    )
    assert decision.max_retention_seconds == 3600
    assert decision.expires_at is None


def test_transient_rejects_both_retention_constraints():
    with pytest.raises(ValueError):
        PersistenceDecision(
            policy_id="p",
            policy_version="v1",
            persistence_class=PersistenceClass.TRANSIENT,
            expires_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
            max_retention_seconds=3600,
        )


def test_source_policy_is_unresolved_and_rejects_concrete_retention_fields():
    unresolved = PersistenceDecision(
        policy_id="p",
        policy_version="v1",
        persistence_class=PersistenceClass.SOURCE_POLICY,
    )
    assert unresolved.expires_at is None
    assert unresolved.max_retention_seconds is None

    with pytest.raises(ValueError):
        PersistenceDecision(
            policy_id="p",
            policy_version="v1",
            persistence_class=PersistenceClass.SOURCE_POLICY,
            max_retention_seconds=3600,
        )


def test_reason_codes_tuple_and_unique():
    with pytest.raises(TypeError):
        PersistenceDecision(
            policy_id="p",
            policy_version="v1",
            persistence_class=PersistenceClass.PERSIST,
            reason_codes=["x"],  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        PersistenceDecision(
            policy_id="p",
            policy_version="v1",
            persistence_class=PersistenceClass.PERSIST,
            reason_codes=("x", "x"),
        )


def test_policy_identity_must_match_nested_persistence(policy, persistence):
    with pytest.raises(ValueError):
        ProviderPolicyDecision(
            policy_id="other",
            policy_version="v1",
            persistence=persistence,
            attribution_required=False,
            redistribution_state=policy.redistribution_state,
            commercial_use_state=policy.commercial_use_state,
        )
