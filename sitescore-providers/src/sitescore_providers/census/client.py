"""Census-specific raw acquisition client over the provider-neutral HTTP boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from sitescore_data import PersistenceClass

from ..artifacts import ArtifactRef, ArtifactStore, ParsedArtifact, RawAcquisitionArtifact
from ..errors import ProviderMalformedResponseError, ProviderUnavailableError
from ..hashing import canonical_json_bytes, sha256_bytes
from ..http import HTTPRequest, HTTPTransport
from ..identity import ProviderIdentity, build_request_fingerprint
from ..parsing import build_parsed_artifact
from ..policy import ProviderPolicyDecision
from ..results import AcquisitionResult, PolicyRejection, ProviderFailure, ProviderFailureKind
from .models import (
    CENSUS_GEOCODER_BASE_URL,
    CENSUS_PROVIDER_KEY,
    CensusAddressRequest,
    CensusCoordinates,
    CensusGeographyManifest,
)

GEOCODE_OPERATION = "single_address_geocode"
GEOGRAPHY_OPERATION = "coordinate_geography_lookup"
GEOCODE_PARSER_ID = "census_geocoder_json"
GEOCODE_PARSER_VERSION = "v1"
GEOGRAPHY_PARSER_ID = "census_geography_json"
GEOGRAPHY_PARSER_VERSION = "v1"
REQUEST_POLICY_ID = "census_geocoder_request"
REQUEST_POLICY_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class ParsedCensusResponse:
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact
    parsed_value: dict[str, object]


def _provider_identity(
    *, manifest: CensusGeographyManifest, operation: str
) -> ProviderIdentity:
    if operation == GEOCODE_OPERATION:
        return ProviderIdentity(
            provider_key=CENSUS_PROVIDER_KEY,
            domain="geocoding",
            dataset="maf_tiger_address_ranges",
            dataset_release=manifest.geocoder_benchmark,
            vintage=None,
            schema_version=None,
            parser_version=GEOCODE_PARSER_VERSION,
            method_version="census_single_address.v1",
        )
    return ProviderIdentity(
        provider_key=CENSUS_PROVIDER_KEY,
        domain="geography",
        dataset="census_geocoder_geolookup",
        dataset_release=manifest.geocoder_benchmark,
        vintage=manifest.geography_vintage,
        schema_version=None,
        parser_version=GEOGRAPHY_PARSER_VERSION,
        method_version="census_coordinate_lookup.v1",
    )


def _failure(operation: str, kind: ProviderFailureKind, reason: str, *, retryable: bool, status: int | None = None) -> AcquisitionResult:
    return AcquisitionResult.provider_failure(
        ProviderFailure(
            provider_key=CENSUS_PROVIDER_KEY,
            operation=operation,
            kind=kind,
            reason_code=reason,
            retryable=retryable,
            status_code=status,
        )
    )


class CensusGeocoderClient:
    def __init__(
        self,
        *,
        transport: HTTPTransport,
        artifact_store: ArtifactStore,
        base_url: str = CENSUS_GEOCODER_BASE_URL,
    ) -> None:
        if not isinstance(transport, HTTPTransport):
            raise TypeError("transport must implement HTTPTransport")
        if not isinstance(artifact_store, ArtifactStore):
            raise TypeError("artifact_store must implement ArtifactStore")
        if not isinstance(base_url, str) or not base_url or base_url != base_url.rstrip("/"):
            raise ValueError("base_url must be non-empty and must not end with '/'")
        self._transport = transport
        self._artifact_store = artifact_store
        self._base_url = base_url

    def acquire_geocode(
        self,
        *,
        request: CensusAddressRequest,
        persistence_policy: ProviderPolicyDecision,
        retrieved_at: datetime,
    ) -> AcquisitionResult:
        semantic = request.semantic_parameters
        fingerprint = build_request_fingerprint(
            provider_key=CENSUS_PROVIDER_KEY,
            operation=GEOCODE_OPERATION,
            semantic_parameters=semantic,
            dataset="maf_tiger_address_ranges",
            dataset_release=request.manifest.geocoder_benchmark,
            policy_id=REQUEST_POLICY_ID,
            policy_version=REQUEST_POLICY_VERSION,
        )
        query = [
            ("street", request.street),
            ("benchmark", request.manifest.geocoder_benchmark),
            ("format", "json"),
        ]
        if request.city is not None:
            query.append(("city", request.city))
        if request.state is not None:
            query.append(("state", request.state))
        if request.zip_code is not None:
            query.append(("zip", request.zip_code))
        return self._acquire(
            http_request=HTTPRequest(
                method="GET",
                url=f"{self._base_url}/locations/address",
                query=tuple(sorted(query)),
            ),
            operation=GEOCODE_OPERATION,
            fingerprint=fingerprint,
            identity=_provider_identity(manifest=request.manifest, operation=GEOCODE_OPERATION),
            persistence_policy=persistence_policy,
            retrieved_at=retrieved_at,
        )

    def acquire_geography(
        self,
        *,
        coordinates: CensusCoordinates,
        manifest: CensusGeographyManifest,
        persistence_policy: ProviderPolicyDecision,
        retrieved_at: datetime,
    ) -> AcquisitionResult:
        semantic = {
            "latitude": coordinates.latitude,
            "longitude": coordinates.longitude,
            "benchmark": manifest.geocoder_benchmark,
            "vintage": manifest.geography_vintage,
            "layers": tuple(layer.request_layer_id for layer in manifest.supported_layers),
        }
        fingerprint = build_request_fingerprint(
            provider_key=CENSUS_PROVIDER_KEY,
            operation=GEOGRAPHY_OPERATION,
            semantic_parameters=semantic,
            dataset="census_geocoder_geolookup",
            dataset_release=manifest.geocoder_benchmark,
            policy_id=REQUEST_POLICY_ID,
            policy_version=REQUEST_POLICY_VERSION,
        )
        query = (
            ("benchmark", manifest.geocoder_benchmark),
            ("format", "json"),
            ("layers", ",".join(str(layer.request_layer_id) for layer in manifest.supported_layers)),
            ("vintage", manifest.geography_vintage),
            ("x", str(coordinates.longitude)),
            ("y", str(coordinates.latitude)),
        )
        return self._acquire(
            http_request=HTTPRequest(
                method="GET",
                url=f"{self._base_url}/geographies/coordinates",
                query=tuple(sorted(query)),
            ),
            operation=GEOGRAPHY_OPERATION,
            fingerprint=fingerprint,
            identity=_provider_identity(manifest=manifest, operation=GEOGRAPHY_OPERATION),
            persistence_policy=persistence_policy,
            retrieved_at=retrieved_at,
        )

    def parse_geocode_success(self, *, acquisition: AcquisitionResult) -> ParsedCensusResponse:
        return self._parse_success(
            acquisition=acquisition,
            parser_id=GEOCODE_PARSER_ID,
            parser_version=GEOCODE_PARSER_VERSION,
        )

    def parse_geography_success(self, *, acquisition: AcquisitionResult) -> ParsedCensusResponse:
        return self._parse_success(
            acquisition=acquisition,
            parser_id=GEOGRAPHY_PARSER_ID,
            parser_version=GEOGRAPHY_PARSER_VERSION,
        )

    def _parse_success(
        self,
        *,
        acquisition: AcquisitionResult,
        parser_id: str,
        parser_version: str,
    ) -> ParsedCensusResponse:
        if acquisition.artifact is None:
            raise ValueError("only successful acquisitions can be parsed")
        raw_artifact = acquisition.artifact
        raw_bytes = self._artifact_store.get(raw_artifact.artifact_ref)
        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderMalformedResponseError("Census response is not valid UTF-8 JSON") from exc
        if not isinstance(parsed, dict):
            raise ProviderMalformedResponseError("Census response root must be a JSON object")
        parsed_bytes = canonical_json_bytes(parsed)
        parsed_hash = sha256_bytes(parsed_bytes)
        parsed_ref = self._artifact_store.put(content_hash=parsed_hash, content=parsed_bytes)
        parsed_artifact = build_parsed_artifact(
            raw_artifact=raw_artifact,
            parser_id=parser_id,
            parser_version=parser_version,
            parsed_value=parsed,
            parsed_artifact_ref=parsed_ref,
        )
        return ParsedCensusResponse(raw_artifact, parsed_artifact, parsed)

    def _acquire(
        self,
        *,
        http_request: HTTPRequest,
        operation: str,
        fingerprint,
        identity: ProviderIdentity,
        persistence_policy: ProviderPolicyDecision,
        retrieved_at: datetime,
    ) -> AcquisitionResult:
        persistence_class = persistence_policy.persistence.persistence_class
        if persistence_class is PersistenceClass.SOURCE_POLICY:
            return AcquisitionResult.policy_rejected(
                PolicyRejection(
                    policy_id=persistence_policy.policy_id,
                    policy_version=persistence_policy.policy_version,
                    reason_code="persistence_policy_unresolved",
                )
            )
        if persistence_class is PersistenceClass.DO_NOT_PERSIST:
            return AcquisitionResult.policy_rejected(
                # Foundation's artifact contract requires an artifact ref; this client refuses
                # to invent a non-resolvable ref for a do-not-persist response.
                PolicyRejection(
                    policy_id=persistence_policy.policy_id,
                    policy_version=persistence_policy.policy_version,
                    reason_code="artifact_persistence_required",
                )
            )
        try:
            response = self._transport.send(http_request)
        except ProviderUnavailableError:
            return _failure(operation, ProviderFailureKind.UNAVAILABLE, "transport_unavailable", retryable=True)
        status = response.status_code
        if status == 429:
            return _failure(operation, ProviderFailureKind.RATE_LIMIT, "http_429", retryable=True, status=status)
        if status in {401, 403}:
            return _failure(operation, ProviderFailureKind.AUTHENTICATION, "http_authentication", retryable=False, status=status)
        if status >= 500:
            return _failure(operation, ProviderFailureKind.UNAVAILABLE, "http_server_error", retryable=True, status=status)
        if status < 200 or status >= 300:
            return _failure(operation, ProviderFailureKind.INVARIANT, "http_request_rejected", retryable=False, status=status)
        content_hash = sha256_bytes(response.body)
        artifact_ref = self._artifact_store.put(content_hash=content_hash, content=response.body)
        return AcquisitionResult.success(
            RawAcquisitionArtifact(
                provider_identity=identity,
                request_fingerprint=fingerprint,
                media_type="application/json",
                content_hash=content_hash,
                artifact_ref=artifact_ref,
                retrieved_at=retrieved_at,
                persistence=persistence_policy.persistence,
            )
        )
