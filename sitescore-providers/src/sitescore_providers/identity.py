"""Immutable provider and request identities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._validation import require_canonical_id, require_nonempty_text, require_optional_nonempty_text
from .hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical, to_canonical_primitive


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    provider_key: str
    domain: str
    dataset: str
    dataset_release: str | None
    vintage: str | None
    schema_version: str | None
    parser_version: str
    method_version: str

    def __post_init__(self) -> None:
        require_canonical_id(self.provider_key, field_name="provider_key")
        require_canonical_id(self.domain, field_name="domain")
        require_nonempty_text(self.dataset, field_name="dataset")
        require_optional_nonempty_text(self.dataset_release, field_name="dataset_release")
        require_optional_nonempty_text(self.vintage, field_name="vintage")
        require_optional_nonempty_text(self.schema_version, field_name="schema_version")
        require_nonempty_text(self.parser_version, field_name="parser_version")
        require_nonempty_text(self.method_version, field_name="method_version")


@dataclass(frozen=True, slots=True)
class RequestFingerprint:
    grammar_version: str
    canonicalization_version: str
    content_hash: ContentHash

    def __post_init__(self) -> None:
        require_nonempty_text(self.grammar_version, field_name="grammar_version")
        require_nonempty_text(self.canonicalization_version, field_name="canonicalization_version")
        if not isinstance(self.content_hash, ContentHash):
            raise TypeError("content_hash must be a ContentHash")

    def __str__(self) -> str:
        return (
            f"request.{self.grammar_version}.canonical.{self.canonicalization_version}:"
            f"{self.content_hash}"
        )


_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "authorization_header",
        "access_token",
        "refresh_token",
        "client_secret",
        "password",
        "secret",
        "token",
        "x_api_key",
    }
)


def _reject_secret_keys(value: Any, *, path: str = "parameters") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("semantic parameter mappings require string keys")
            normalized = key.strip().lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                raise ValueError(f"secret-bearing parameter key is forbidden in fingerprint input: {path}.{key}")
            _reject_secret_keys(item, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_secret_keys(item, path=f"{path}[{index}]")



def _request_fingerprint_preimage(
    *,
    grammar_version: str,
    canonicalization_version: str,
    provider_key: str,
    operation: str,
    semantic_parameters: Any,
    dataset: str,
    dataset_release: str | None,
    policy_id: str,
    policy_version: str,
) -> dict[str, Any]:
    """Build the version-bound semantic preimage for request fingerprints."""

    return {
        "grammar_version": grammar_version,
        "canonicalization_version": canonicalization_version,
        "provider_key": provider_key,
        "operation": operation,
        "semantic_parameters": semantic_parameters,
        "dataset": dataset,
        "dataset_release": dataset_release,
        "policy_id": policy_id,
        "policy_version": policy_version,
    }

def build_request_fingerprint(
    *,
    provider_key: str,
    operation: str,
    semantic_parameters: dict[str, Any],
    dataset: str,
    dataset_release: str | None,
    policy_id: str,
    policy_version: str,
    grammar_version: str = "v1",
) -> RequestFingerprint:
    """Fingerprint only semantic request inputs; execution metadata is absent by API design."""

    require_canonical_id(provider_key, field_name="provider_key")
    require_canonical_id(operation, field_name="operation")
    require_nonempty_text(dataset, field_name="dataset")
    require_optional_nonempty_text(dataset_release, field_name="dataset_release")
    require_canonical_id(policy_id, field_name="policy_id")
    require_nonempty_text(policy_version, field_name="policy_version")
    require_nonempty_text(grammar_version, field_name="grammar_version")
    if not isinstance(semantic_parameters, dict):
        raise TypeError("semantic_parameters must be a dict")
    _reject_secret_keys(semantic_parameters)
    parameters = to_canonical_primitive(semantic_parameters)
    payload = _request_fingerprint_preimage(
        grammar_version=grammar_version,
        canonicalization_version=CANONICALIZATION_VERSION,
        provider_key=provider_key,
        operation=operation,
        semantic_parameters=parameters,
        dataset=dataset,
        dataset_release=dataset_release,
        policy_id=policy_id,
        policy_version=policy_version,
    )
    return RequestFingerprint(
        grammar_version=grammar_version,
        canonicalization_version=CANONICALIZATION_VERSION,
        content_hash=hash_canonical(payload),
    )
