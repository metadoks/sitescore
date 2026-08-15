"""Valhalla road isochrone acquisition over a minimal JSON POST boundary.

The locked Checkpoint 3.3-1 ``HTTPTransport`` intentionally has no request-body
surface. Current Valhalla 3.8.x removed the legacy ``json`` query parameter, so
this checkpoint defines a narrow provider-specific JSON POST transport instead
of mutating the locked foundation abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import socket
from typing import Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sitescore_data import PersistenceClass

from ..artifacts import ArtifactRef, ArtifactStore, ParsedArtifact, RawAcquisitionArtifact
from ..errors import ProviderMalformedResponseError, ProviderUnavailableError
from ..hashing import canonical_json_bytes, sha256_bytes
from ..identity import ProviderIdentity, RequestFingerprint, build_request_fingerprint
from ..parsing import build_parsed_artifact
from ..policy import ProviderPolicyDecision
from ..results import AcquisitionResult, PolicyRejection, ProviderFailure, ProviderFailureKind
from .models import (
    ROAD_REQUEST_GRAMMAR,
    VALHALLA_ISOCHRONE_DATASET,
    VALHALLA_ISOCHRONE_OPERATION,
    VALHALLA_PARSER_ID,
    VALHALLA_PROVIDER_KEY,
    RoadIsochroneRequest,
    RoadRoutingExecutionBinding,
)

VALHALLA_PARSER_VERSION = "v1"
VALHALLA_REQUEST_POLICY_ID = "valhalla_road_isochrone_request"
VALHALLA_REQUEST_POLICY_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class ValhallaJSONRequest:
    url: str
    body: bytes
    headers: tuple[tuple[str, str], ...] = (("Content-Type", "application/json"),)
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.url, str) or not self.url or self.url != self.url.strip():
            raise ValueError("url must be non-empty and trimmed")
        if not isinstance(self.body, bytes):
            raise TypeError("body must be bytes")
        if not isinstance(self.headers, tuple):
            raise TypeError("headers must be a tuple")
        for item in self.headers:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("headers entries must be (name, value) tuples")
            if not all(isinstance(v, str) and v and v == v.strip() for v in item):
                raise ValueError("header names and values must be non-empty trimmed strings")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise TypeError("timeout_seconds must be numeric")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")


@dataclass(frozen=True, slots=True)
class ValhallaJSONResponse:
    status_code: int
    body: bytes
    media_type: str = "application/json"

    def __post_init__(self) -> None:
        if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
            raise TypeError("status_code must be an int")
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be a valid HTTP status")
        if not isinstance(self.body, bytes):
            raise TypeError("body must be bytes")
        if not isinstance(self.media_type, str) or not self.media_type:
            raise ValueError("media_type must be non-empty")


@runtime_checkable
class ValhallaJSONTransport(Protocol):
    def send(self, request: ValhallaJSONRequest) -> ValhallaJSONResponse:
        ...


class UrllibValhallaJSONTransport:
    """Small stdlib-only JSON POST transport; no retry/logging/auth policy."""

    def send(self, request: ValhallaJSONRequest) -> ValhallaJSONResponse:
        if not isinstance(request, ValhallaJSONRequest):
            raise TypeError("request must be a ValhallaJSONRequest")
        http_request = Request(
            request.url,
            data=request.body,
            method="POST",
            headers=dict(request.headers),
        )
        try:
            with urlopen(http_request, timeout=request.timeout_seconds) as response:  # noqa: S310 - explicit provider URL
                body = response.read()
                media_type = response.headers.get_content_type() or "application/json"
                return ValhallaJSONResponse(response.status, body, media_type)
        except HTTPError as exc:
            return ValhallaJSONResponse(exc.code, exc.read(), exc.headers.get_content_type() if exc.headers else "application/json")
        except (URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise ProviderUnavailableError("Valhalla transport unavailable") from exc


@dataclass(frozen=True, slots=True)
class ParsedValhallaResponse:
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact
    parsed_value: dict[str, object]

    def __post_init__(self) -> None:
        if self.parsed_artifact.raw_content_hash != self.raw_artifact.content_hash:
            raise ValueError("parsed artifact raw lineage must match raw artifact content hash")


def routing_provider_identity(request: RoadIsochroneRequest) -> ProviderIdentity:
    if not isinstance(request, RoadIsochroneRequest):
        raise TypeError("request must be a RoadIsochroneRequest")
    engine = request.engine_manifest
    network = request.graph_compatibility.network_manifest
    return ProviderIdentity(
        provider_key=VALHALLA_PROVIDER_KEY,
        domain="road",
        dataset=VALHALLA_ISOCHRONE_DATASET,
        dataset_release=engine.engine_version,
        vintage=network.source_release,
        schema_version="geojson",
        parser_version=VALHALLA_PARSER_VERSION,
        method_version=f"{engine.costing_profile_id}.{engine.costing_profile_version}",
    )


def build_isochrone_request_fingerprint(request: RoadIsochroneRequest) -> RequestFingerprint:
    if not isinstance(request, RoadIsochroneRequest):
        raise TypeError("request must be a RoadIsochroneRequest")
    engine = request.engine_manifest
    return build_request_fingerprint(
        provider_key=VALHALLA_PROVIDER_KEY,
        operation=VALHALLA_ISOCHRONE_OPERATION,
        semantic_parameters=request.semantic_parameters,
        dataset=VALHALLA_ISOCHRONE_DATASET,
        dataset_release=engine.engine_version,
        policy_id=VALHALLA_REQUEST_POLICY_ID,
        policy_version=VALHALLA_REQUEST_POLICY_VERSION,
        grammar_version=ROAD_REQUEST_GRAMMAR,
    )


def build_valhalla_isochrone_body(request: RoadIsochroneRequest) -> bytes:
    """Build the exact semantic JSON POST payload for the canonical request."""

    if not isinstance(request, RoadIsochroneRequest):
        raise TypeError("request must be a RoadIsochroneRequest")
    engine = request.engine_manifest
    payload: dict[str, object] = {
        "locations": [{"lat": request.origin.latitude, "lon": request.origin.longitude}],
        "costing": "auto",
        "contours": [
            {"time": float(scale.travel_cost_seconds) / 60.0}
            for scale in request.budget_policy.scales
        ],
        "polygons": True,
        "show_locations": True,
        "reverse": False,
    }
    if engine.costing_options:
        payload["costing_options"] = {
            "auto": {key: value for key, value in engine.costing_options}
        }
    if request.geometry_policy.denoise is not None:
        payload["denoise"] = request.geometry_policy.denoise
    if request.geometry_policy.generalize_meters is not None:
        payload["generalize"] = request.geometry_policy.generalize_meters
    return canonical_json_bytes(payload)


def _failure(kind: ProviderFailureKind, reason: str, *, retryable: bool, status: int | None = None) -> AcquisitionResult:
    return AcquisitionResult.provider_failure(
        ProviderFailure(
            provider_key=VALHALLA_PROVIDER_KEY,
            operation=VALHALLA_ISOCHRONE_OPERATION,
            kind=kind,
            reason_code=reason,
            retryable=retryable,
            status_code=status,
        )
    )


class RoadIsochroneClient:
    def __init__(
        self,
        *,
        transport: ValhallaJSONTransport,
        artifact_store: ArtifactStore,
        endpoint_url: str,
        execution_binding: RoadRoutingExecutionBinding,
        execution_headers: tuple[tuple[str, str], ...] = (),
        timeout_seconds: float = 30.0,
    ) -> None:
        if not isinstance(transport, ValhallaJSONTransport):
            raise TypeError("transport must implement ValhallaJSONTransport")
        if not isinstance(artifact_store, ArtifactStore):
            raise TypeError("artifact_store must implement ArtifactStore")
        if not isinstance(endpoint_url, str) or not endpoint_url or endpoint_url != endpoint_url.strip():
            raise ValueError("endpoint_url must be non-empty and trimmed")
        if not endpoint_url.endswith("/isochrone"):
            raise ValueError("endpoint_url must identify the Valhalla /isochrone operation")
        if not isinstance(execution_binding, RoadRoutingExecutionBinding):
            raise TypeError("execution_binding must be a RoadRoutingExecutionBinding")
        if not isinstance(execution_headers, tuple):
            raise TypeError("execution_headers must be a tuple")
        self._transport = transport
        self._artifact_store = artifact_store
        self._endpoint_url = endpoint_url
        self._execution_binding = execution_binding
        self._execution_headers = execution_headers
        self._timeout_seconds = timeout_seconds

    def acquire(
        self,
        *,
        request: RoadIsochroneRequest,
        persistence_policy: ProviderPolicyDecision,
        retrieved_at: datetime,
    ) -> AcquisitionResult:
        if not isinstance(persistence_policy, ProviderPolicyDecision):
            raise TypeError("persistence_policy must be a ProviderPolicyDecision")
        if request.execution_binding.identity != self._execution_binding.identity:
            raise ValueError("request execution binding does not match this Valhalla deployment client")
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
                PolicyRejection(
                    policy_id=persistence_policy.policy_id,
                    policy_version=persistence_policy.policy_version,
                    reason_code="artifact_persistence_required",
                )
            )
        fingerprint = build_isochrone_request_fingerprint(request)
        body = build_valhalla_isochrone_body(request)
        headers = (("Content-Type", "application/json"),) + self._execution_headers
        try:
            response = self._transport.send(
                ValhallaJSONRequest(
                    url=self._endpoint_url,
                    body=body,
                    headers=headers,
                    timeout_seconds=self._timeout_seconds,
                )
            )
        except ProviderUnavailableError:
            return _failure(ProviderFailureKind.UNAVAILABLE, "transport_unavailable", retryable=True)
        status = response.status_code
        if status == 429:
            return _failure(ProviderFailureKind.RATE_LIMIT, "http_429", retryable=True, status=status)
        if status in {401, 403}:
            return _failure(ProviderFailureKind.AUTHENTICATION, "http_authentication", retryable=False, status=status)
        if status >= 500:
            return _failure(ProviderFailureKind.UNAVAILABLE, "http_server_error", retryable=True, status=status)
        if status == 400:
            # Valhalla error code 171 is a distinct location/graph correlation
            # condition (no suitable road edge near the input), not zero reach.
            try:
                error_payload = json.loads(response.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_payload = None
            if isinstance(error_payload, dict) and error_payload.get("error_code") == 171:
                return _failure(
                    ProviderFailureKind.INVARIANT,
                    "no_suitable_edges_near_location",
                    retryable=False,
                    status=status,
                )
        if status < 200 or status >= 300:
            return _failure(ProviderFailureKind.INVARIANT, "http_request_rejected", retryable=False, status=status)
        content_hash = sha256_bytes(response.body)
        artifact_ref = self._artifact_store.put(content_hash=content_hash, content=response.body)
        return AcquisitionResult.success(
            RawAcquisitionArtifact(
                provider_identity=routing_provider_identity(request),
                request_fingerprint=fingerprint,
                media_type=response.media_type,
                content_hash=content_hash,
                artifact_ref=artifact_ref,
                retrieved_at=retrieved_at,
                persistence=persistence_policy.persistence,
            )
        )

    def parse_success(
        self,
        *,
        acquisition: AcquisitionResult,
        request: RoadIsochroneRequest,
    ) -> ParsedValhallaResponse:
        if acquisition.artifact is None:
            raise ValueError("only successful acquisitions can be parsed")
        raw_artifact = acquisition.artifact
        if request.execution_binding.identity != self._execution_binding.identity:
            raise ValueError("request execution binding does not match this Valhalla deployment client")
        expected_fingerprint = build_isochrone_request_fingerprint(request)
        if raw_artifact.request_fingerprint != expected_fingerprint:
            raise ValueError("raw artifact request fingerprint does not match active road request")
        if raw_artifact.provider_identity != routing_provider_identity(request):
            raise ValueError("raw artifact provider identity does not match active road request")
        raw_bytes = self._artifact_store.get(raw_artifact.artifact_ref)
        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderMalformedResponseError("Valhalla response is not valid UTF-8 JSON") from exc
        if not isinstance(parsed, dict):
            raise ProviderMalformedResponseError("Valhalla response root must be a JSON object")
        parsed_bytes = canonical_json_bytes(parsed)
        parsed_hash = sha256_bytes(parsed_bytes)
        parsed_ref = self._artifact_store.put(content_hash=parsed_hash, content=parsed_bytes)
        parsed_artifact = build_parsed_artifact(
            raw_artifact=raw_artifact,
            parser_id=VALHALLA_PARSER_ID,
            parser_version=VALHALLA_PARSER_VERSION,
            parsed_value=parsed,
            parsed_artifact_ref=parsed_ref,
        )
        return ParsedValhallaResponse(raw_artifact, parsed_artifact, parsed)
