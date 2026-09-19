"""ACS 5-year Detailed Tables acquisition over the locked provider HTTP boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from sitescore_data import PersistenceClass

from ..artifacts import ArtifactStore, ParsedArtifact, RawAcquisitionArtifact
from ..errors import ProviderMalformedResponseError, ProviderUnavailableError
from ..hashing import canonical_json_bytes, sha256_bytes
from ..http import HTTPRequest, HTTPTransport
from ..identity import ProviderIdentity
from ..parsing import build_parsed_artifact
from ..policy import ProviderPolicyDecision
from ..results import AcquisitionResult, PolicyRejection, ProviderFailure, ProviderFailureKind
from .models import ACS_API_BASE_URL, ACS_PROVIDER_KEY, ACSDatasetManifest, ACSRequest
from .request import ACS_OPERATION

ACS_PARSER_ID = "census_acs_detailed_tables_json"
ACS_METHOD_VERSION = "census_acs5_detailed_tables.v1"


@dataclass(frozen=True, slots=True)
class ParsedACSResponse:
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact
    parsed_value: list[object]

    def __post_init__(self) -> None:
        if not isinstance(self.raw_artifact, RawAcquisitionArtifact):
            raise TypeError("raw_artifact must be a RawAcquisitionArtifact")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be a ParsedArtifact")
        if self.parsed_artifact.raw_content_hash != self.raw_artifact.content_hash:
            raise ValueError("parsed artifact raw_content_hash must match raw artifact content_hash")
        if not isinstance(self.parsed_value, list):
            raise TypeError("parsed_value must be a list")


def _failure(kind: ProviderFailureKind, reason: str, *, retryable: bool, status: int | None = None) -> AcquisitionResult:
    return AcquisitionResult.provider_failure(
        ProviderFailure(
            provider_key=ACS_PROVIDER_KEY,
            operation=ACS_OPERATION,
            kind=kind,
            reason_code=reason,
            retryable=retryable,
            status_code=status,
        )
    )


def _provider_identity(manifest: ACSDatasetManifest) -> ProviderIdentity:
    return ProviderIdentity(
        provider_key=ACS_PROVIDER_KEY,
        domain="demographics",
        dataset=manifest.dataset_identifier,
        dataset_release=manifest.dataset_release,
        vintage=manifest.vintage,
        schema_version=manifest.manifest_version,
        parser_version=manifest.parser_version,
        method_version=ACS_METHOD_VERSION,
    )


class ACSClient:
    def __init__(
        self,
        *,
        transport: HTTPTransport,
        artifact_store: ArtifactStore,
        api_key: str,
        base_url: str = ACS_API_BASE_URL,
    ) -> None:
        if not isinstance(transport, HTTPTransport):
            raise TypeError("transport must implement HTTPTransport")
        if not isinstance(artifact_store, ArtifactStore):
            raise TypeError("artifact_store must implement ArtifactStore")
        if not isinstance(api_key, str) or not api_key or api_key != api_key.strip():
            raise ValueError("api_key must be non-empty and trimmed")
        if not isinstance(base_url, str) or not base_url or base_url != base_url.rstrip("/"):
            raise ValueError("base_url must be non-empty and must not end with '/'")
        self._transport = transport
        self._artifact_store = artifact_store
        self._api_key = api_key  # credential is executor state only; never fingerprint/artifact metadata input
        self._base_url = base_url

    def acquire(
        self,
        *,
        request: ACSRequest,
        manifest: ACSDatasetManifest,
        persistence_policy: ProviderPolicyDecision,
        retrieved_at: datetime,
    ) -> AcquisitionResult:
        if not isinstance(request, ACSRequest):
            raise TypeError("request must be an ACSRequest")
        if not isinstance(manifest, ACSDatasetManifest):
            raise TypeError("manifest must be an ACSDatasetManifest")
        persistence_class = persistence_policy.persistence.persistence_class
        if persistence_class is PersistenceClass.SOURCE_POLICY:
            return AcquisitionResult.policy_rejected(
                PolicyRejection(persistence_policy.policy_id, persistence_policy.policy_version, "persistence_policy_unresolved")
            )
        if persistence_class is PersistenceClass.DO_NOT_PERSIST:
            return AcquisitionResult.policy_rejected(
                PolicyRejection(persistence_policy.policy_id, persistence_policy.policy_version, "artifact_persistence_required")
            )
        http_request = HTTPRequest(
            method="GET",
            url=f"{self._base_url}/{manifest.dataset_release}/{manifest.dataset_identifier}",
            query=tuple(
                sorted(
                    (
                        ("for", request.geography.for_clause),
                        ("get", ",".join(request.variable_ids)),
                        ("in", request.geography.in_clause),
                        ("key", self._api_key),
                    )
                )
            ),
        )
        try:
            response = self._transport.send(http_request)
        except ProviderUnavailableError:
            return _failure(ProviderFailureKind.UNAVAILABLE, "transport_unavailable", retryable=True)
        status = response.status_code
        if status == 429:
            return _failure(ProviderFailureKind.RATE_LIMIT, "http_429", retryable=True, status=status)
        if status in {401, 403}:
            return _failure(ProviderFailureKind.AUTHENTICATION, "http_authentication", retryable=False, status=status)
        if status >= 500:
            return _failure(ProviderFailureKind.UNAVAILABLE, "http_server_error", retryable=True, status=status)
        if status < 200 or status >= 300:
            return _failure(ProviderFailureKind.INVARIANT, "http_request_rejected", retryable=False, status=status)
        content_hash = sha256_bytes(response.body)
        artifact_ref = self._artifact_store.put(content_hash=content_hash, content=response.body)
        return AcquisitionResult.success(
            RawAcquisitionArtifact(
                provider_identity=_provider_identity(manifest),
                request_fingerprint=request.request_fingerprint,
                media_type="application/json",
                content_hash=content_hash,
                artifact_ref=artifact_ref,
                retrieved_at=retrieved_at,
                persistence=persistence_policy.persistence,
            )
        )

    def parse_success(self, *, acquisition: AcquisitionResult, manifest: ACSDatasetManifest) -> ParsedACSResponse:
        if acquisition.artifact is None:
            raise ValueError("only successful acquisitions can be parsed")
        raw_artifact = acquisition.artifact
        raw_bytes = self._artifact_store.get(raw_artifact.artifact_ref)
        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderMalformedResponseError("ACS response is not valid UTF-8 JSON") from exc
        if not isinstance(parsed, list):
            raise ProviderMalformedResponseError("ACS response root must be a JSON array")
        parsed_bytes = canonical_json_bytes(parsed)
        parsed_hash = sha256_bytes(parsed_bytes)
        parsed_ref = self._artifact_store.put(content_hash=parsed_hash, content=parsed_bytes)
        parsed_artifact = build_parsed_artifact(
            raw_artifact=raw_artifact,
            parser_id=ACS_PARSER_ID,
            parser_version=manifest.parser_version,
            parsed_value=parsed,
            parsed_artifact_ref=parsed_ref,
        )
        return ParsedACSResponse(raw_artifact, parsed_artifact, parsed)
