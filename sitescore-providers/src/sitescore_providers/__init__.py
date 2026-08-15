"""SiteScore provider-neutral acquisition foundation."""

from .artifacts import ArtifactRef, ArtifactStore, ParsedArtifact, RawAcquisitionArtifact
from .baseline import assert_sitescore_data_compatibility

# Runtime guard: package version only; git commit/tag remain repository preflight.
assert_sitescore_data_compatibility()
from .errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderInvariantError,
    ProviderMalformedResponseError,
    ProviderPolicyError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from .hashing import CANONICALIZATION_VERSION, ContentHash, HashAlgorithm, canonical_json_bytes, hash_canonical, sha256_bytes
from .identity import ProviderIdentity, RequestFingerprint, build_request_fingerprint
from .lineage import build_source_metadata
from .parsing import build_parsed_artifact
from .policy import (
    CommercialUseState,
    PersistenceDecision,
    ProviderPolicyDecision,
    ProviderPolicyRegistry,
    RedistributionState,
    RequestedUse,
)
from .results import AcquisitionResult, AcquisitionState, PolicyRejection, ProviderFailure, ProviderFailureKind

__all__ = [
    "AcquisitionResult",
    "AcquisitionState",
    "ArtifactRef",
    "ArtifactStore",
    "CANONICALIZATION_VERSION",
    "CommercialUseState",
    "ContentHash",
    "HashAlgorithm",
    "ParsedArtifact",
    "PersistenceDecision",
    "PolicyRejection",
    "ProviderAuthenticationError",
    "ProviderError",
    "ProviderFailure",
    "ProviderFailureKind",
    "ProviderIdentity",
    "ProviderInvariantError",
    "ProviderMalformedResponseError",
    "ProviderPolicyDecision",
    "ProviderPolicyError",
    "ProviderPolicyRegistry",
    "ProviderQuotaError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "RawAcquisitionArtifact",
    "RedistributionState",
    "RequestFingerprint",
    "RequestedUse",
    "assert_sitescore_data_compatibility",
    "build_parsed_artifact",
    "build_request_fingerprint",
    "build_source_metadata",
    "canonical_json_bytes",
    "hash_canonical",
    "sha256_bytes",
]
