from __future__ import annotations

import pytest

from sitescore_providers import build_request_fingerprint


def _fp(params):
    return build_request_fingerprint(
        provider_key="example.provider.v1",
        operation="search",
        semantic_parameters=params,
        dataset="Dataset",
        dataset_release="r1",
        policy_id="policy_v1",
        policy_version="1",
    )


def test_parameter_order_independence():
    assert _fp({"b": 2, "a": 1}) == _fp({"a": 1, "b": 2})


def test_same_input_same_identity():
    assert _fp({"q": "coffee", "limit": 10}) == _fp({"q": "coffee", "limit": 10})


def test_semantic_change_changes_identity():
    assert _fp({"q": "coffee", "limit": 10}) != _fp({"q": "coffee", "limit": 11})


def test_policy_change_changes_identity():
    a = _fp({"q": "coffee"})
    b = build_request_fingerprint(
        provider_key="example.provider.v1",
        operation="search",
        semantic_parameters={"q": "coffee"},
        dataset="Dataset",
        dataset_release="r1",
        policy_id="policy_v1",
        policy_version="2",
    )
    assert a != b


@pytest.mark.parametrize("key", ["api_key", "Authorization", "access-token", "client_secret", "password", "token"])
def test_secret_keys_rejected(key):
    with pytest.raises(ValueError):
        _fp({"query": "coffee", key: "super-secret"})


def test_nested_secret_keys_rejected():
    with pytest.raises(ValueError):
        _fp({"safe": {"authorization_header": "secret"}})


def test_secret_value_is_not_accepted_through_explicit_secret_parameter_name():
    secret = "sk-test-do-not-serialize"
    with pytest.raises(ValueError):
        _fp({"query": "coffee", "api_key": secret})
    # Regression intent: the value is never serialized because validation fails first.


def test_canonicalization_version_is_current_provider_grammar():
    from sitescore_providers import CANONICALIZATION_VERSION

    fingerprint = _fp({"q": "coffee"})
    assert fingerprint.canonicalization_version == CANONICALIZATION_VERSION
    assert f".canonical.{CANONICALIZATION_VERSION}:" in str(fingerprint)


def test_request_grammar_version_change_changes_identity():
    a = _fp({"q": "coffee"})
    b = build_request_fingerprint(
        provider_key="example.provider.v1",
        operation="search",
        semantic_parameters={"q": "coffee"},
        dataset="Dataset",
        dataset_release="r1",
        policy_id="policy_v1",
        policy_version="1",
        grammar_version="v2",
    )
    assert a != b
    assert a.content_hash != b.content_hash


def test_canonicalization_version_participates_in_request_preimage():
    from sitescore_providers.hashing import hash_canonical
    from sitescore_providers.identity import _request_fingerprint_preimage

    common = dict(
        grammar_version="v1",
        provider_key="example.provider.v1",
        operation="search",
        semantic_parameters={"q": "coffee", "limit": 10},
        dataset="Dataset",
        dataset_release="r1",
        policy_id="policy_v1",
        policy_version="1",
    )
    a = _request_fingerprint_preimage(canonicalization_version="v1", **common)
    b = _request_fingerprint_preimage(canonicalization_version="v2", **common)
    assert hash_canonical(a) != hash_canonical(b)
