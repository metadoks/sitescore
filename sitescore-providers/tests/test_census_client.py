from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

import pytest
from sitescore_data import GeographyType, PersistenceClass

from sitescore_providers import (
    ArtifactRef,
    CommercialUseState,
    PersistenceDecision,
    ProviderPolicyDecision,
    RedistributionState,
)
from sitescore_providers.census import (
    CensusAddressRequest,
    CensusBenchmarkVintageCompatibility,
    CensusCoordinates,
    CensusGeocoderClient,
    CensusGeographyLayerSpec,
    CensusGeographyManifest,
    GEOCODE_PARSER_ID,
    GEOCODE_PARSER_VERSION,
)
from sitescore_providers.errors import ProviderMalformedResponseError, ProviderUnavailableError
from sitescore_providers.hashing import ContentHash
from sitescore_providers.http import HTTPRequest, HTTPResponse
from sitescore_providers.results import AcquisitionState, ProviderFailureKind

def core_layer_specs():
    # Fixture IDs are manifest-bound fake Census layer IDs; production IDs must come from approved config.
    return (
        CensusGeographyLayerSpec(GeographyType.STATE, 101, ("States",), True),
        CensusGeographyLayerSpec(GeographyType.COUNTY, 102, ("Counties",), True),
        CensusGeographyLayerSpec(GeographyType.TRACT, 103, ("Census Tracts",), True),
        CensusGeographyLayerSpec(GeographyType.BLOCK_GROUP, 104, ("Census Block Groups",), True),
    )


def optional_layer_specs():
    return (
        CensusGeographyLayerSpec(GeographyType.CBSA, 201, ("Metropolitan Statistical Areas", "Micropolitan Statistical Areas"), False),
        CensusGeographyLayerSpec(GeographyType.METROPOLITAN_DIVISION, 202, ("Metropolitan Divisions",), False),
        CensusGeographyLayerSpec(GeographyType.CSA, 203, ("Combined Statistical Areas",), False),
        CensusGeographyLayerSpec(GeographyType.ZCTA, 204, ("ZIP Code Tabulation Areas", "2020 Census ZIP Code Tabulation Areas"), False),
    )


NOW = datetime(2026, 8, 12, 18, 0, tzinfo=timezone.utc)


class MemoryArtifactStore:
    def __init__(self):
        self.data: dict[str, bytes] = {}

    def put(self, *, content_hash: ContentHash, content: bytes) -> ArtifactRef:
        ref = ArtifactRef(f"memory:{content_hash.algorithm.value}/{content_hash.digest}")
        self.data[str(ref)] = content
        return ref

    def get(self, artifact_ref: ArtifactRef) -> bytes:
        return self.data[str(artifact_ref)]

    def exists(self, artifact_ref: ArtifactRef) -> bool:
        return str(artifact_ref) in self.data


class FakeTransport:
    def __init__(self, response: HTTPResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests: list[HTTPRequest] = []

    def send(self, request: HTTPRequest) -> HTTPResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def compatibility(
    *,
    compatibility_id: str = "acs2024_pair",
    compatibility_version: str = "v1",
    geocoder_benchmark: str = "Public_AR_ACS2024",
    geography_vintage: str = "ACS2024_ACS2024",
) -> CensusBenchmarkVintageCompatibility:
    return CensusBenchmarkVintageCompatibility(
        compatibility_id=compatibility_id,
        compatibility_version=compatibility_version,
        geocoder_benchmark=geocoder_benchmark,
        geography_vintage=geography_vintage,
    )


def manifest() -> CensusGeographyManifest:
    return CensusGeographyManifest("v1", compatibility(), core_layer_specs())


def policy(*, persistence_class=PersistenceClass.PERSIST) -> ProviderPolicyDecision:
    persistence = PersistenceDecision(
        policy_id="census_policy",
        policy_version="v1",
        persistence_class=persistence_class,
    )
    return ProviderPolicyDecision(
        policy_id="census_policy",
        policy_version="v1",
        persistence=persistence,
        attribution_required=False,
        redistribution_state=RedistributionState.UNKNOWN,
        commercial_use_state=CommercialUseState.UNKNOWN,
    )


def matched_body() -> bytes:
    return json.dumps({
        "result": {
            "input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}},
            "addressMatches": [{
                "tigerLine": {"side": "L", "tigerLineId": "76355984"},
                "coordinates": {"x": -76.9274, "y": 38.8460},
                "matchedAddress": "4600 SILVER HILL RD, WASHINGTON, DC, 20233",
            }],
        }
    }).encode()


def test_deterministic_geocoder_request_and_no_secret_material():
    transport = FakeTransport(HTTPResponse(200, (), matched_body()))
    store = MemoryArtifactStore()
    client = CensusGeocoderClient(transport=transport, artifact_store=store)
    request = CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest())
    first = client.acquire_geocode(request=request, persistence_policy=policy(), retrieved_at=NOW)
    second = client.acquire_geocode(request=request, persistence_policy=policy(), retrieved_at=NOW)
    assert first.artifact.request_fingerprint == second.artifact.request_fingerprint
    http = transport.requests[0]
    assert "/locations/address" in http.url
    assert dict(http.query)["benchmark"] == "Public_AR_ACS2024"
    assert "Current" not in http.effective_url
    assert "api_key" not in http.effective_url.lower()
    assert "authorization" not in http.effective_url.lower()


def test_semantic_address_change_changes_request_fingerprint():
    transport = FakeTransport(HTTPResponse(200, (), matched_body()))
    client = CensusGeocoderClient(transport=transport, artifact_store=MemoryArtifactStore())
    first = client.acquire_geocode(
        request=CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    second = client.acquire_geocode(
        request=CensusAddressRequest("4602 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    assert first.artifact.request_fingerprint != second.artifact.request_fingerprint


def test_coordinate_lookup_sends_x_longitude_y_latitude_and_explicit_vintage():
    body = json.dumps({"result": {"input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}, "vintage": {"vintageName": "ACS2024_ACS2024"}}, "geographies": {}}}).encode()
    transport = FakeTransport(HTTPResponse(200, (), body))
    client = CensusGeocoderClient(transport=transport, artifact_store=MemoryArtifactStore())
    result = client.acquire_geography(
        coordinates=CensusCoordinates(latitude=38.5, longitude=-76.5),
        manifest=manifest(), persistence_policy=policy(), retrieved_at=NOW,
    )
    assert result.state is AcquisitionState.SUCCESS
    query = dict(transport.requests[0].query)
    assert query["x"] == "-76.5"
    assert query["y"] == "38.5"
    assert query["vintage"] == "ACS2024_ACS2024"


def test_raw_to_parsed_lineage_uses_foundation_identity_semantics():
    transport = FakeTransport(HTTPResponse(200, (), matched_body()))
    client = CensusGeocoderClient(transport=transport, artifact_store=MemoryArtifactStore())
    acquisition = client.acquire_geocode(
        request=CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    parsed = client.parse_geocode_success(acquisition=acquisition)
    assert parsed.parsed_artifact.raw_content_hash == acquisition.artifact.content_hash
    assert parsed.parsed_artifact.parsed_content_hash != parsed.parsed_artifact.derivation_fingerprint
    assert parsed.parsed_artifact.identity == parsed.parsed_artifact.derivation_fingerprint


def test_malformed_json_uses_provider_malformed_response_error():
    transport = FakeTransport(HTTPResponse(200, (), b"not-json"))
    client = CensusGeocoderClient(transport=transport, artifact_store=MemoryArtifactStore())
    acquisition = client.acquire_geocode(
        request=CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    with pytest.raises(ProviderMalformedResponseError):
        client.parse_geocode_success(acquisition=acquisition)


@pytest.mark.parametrize(
    "status,kind,retryable",
    [
        (429, ProviderFailureKind.RATE_LIMIT, True),
        (401, ProviderFailureKind.AUTHENTICATION, False),
        (403, ProviderFailureKind.AUTHENTICATION, False),
        (500, ProviderFailureKind.UNAVAILABLE, True),
        (400, ProviderFailureKind.INVARIANT, False),
    ],
)
def test_http_failures_remain_provider_execution_failures(status, kind, retryable):
    client = CensusGeocoderClient(
        transport=FakeTransport(HTTPResponse(status, (), b"error")),
        artifact_store=MemoryArtifactStore(),
    )
    result = client.acquire_geocode(
        request=CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    assert result.state is AcquisitionState.PROVIDER_FAILURE
    assert result.failure.kind is kind
    assert result.failure.retryable is retryable
    assert not hasattr(result.failure, "availability")


def test_transport_outage_is_provider_unavailable_not_domain_evidence():
    client = CensusGeocoderClient(
        transport=FakeTransport(error=ProviderUnavailableError("offline")),
        artifact_store=MemoryArtifactStore(),
    )
    result = client.acquire_geocode(
        request=CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    assert result.failure.kind is ProviderFailureKind.UNAVAILABLE


def test_do_not_persist_policy_is_rejected_instead_of_inventing_artifact_ref():
    client = CensusGeocoderClient(
        transport=FakeTransport(HTTPResponse(200, (), matched_body())),
        artifact_store=MemoryArtifactStore(),
    )
    result = client.acquire_geocode(
        request=CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(persistence_class=PersistenceClass.DO_NOT_PERSIST), retrieved_at=NOW,
    )
    assert result.state is AcquisitionState.POLICY_REJECTION
    assert result.policy_rejection.reason_code == "artifact_persistence_required"


def test_unresolved_source_policy_is_rejected_before_artifact_storage():
    client = CensusGeocoderClient(
        transport=FakeTransport(HTTPResponse(200, (), matched_body())),
        artifact_store=MemoryArtifactStore(),
    )
    result = client.acquire_geocode(
        request=CensusAddressRequest("4600 Silver Hill Rd", "Washington", "DC", "20233", manifest()),
        persistence_policy=policy(persistence_class=PersistenceClass.SOURCE_POLICY), retrieved_at=NOW,
    )
    assert result.state is AcquisitionState.POLICY_REJECTION
    assert result.policy_rejection.reason_code == "persistence_policy_unresolved"


def test_geocode_fingerprint_excludes_geography_only_manifest_semantics():
    transport = FakeTransport(HTTPResponse(200, (), matched_body()))
    client = CensusGeocoderClient(transport=transport, artifact_store=MemoryArtifactStore())
    first_manifest = manifest()
    second_manifest = CensusGeographyManifest(
        manifest_version="different_pipeline_manifest",
        compatibility=compatibility(compatibility_id="different_pair_review", compatibility_version="v9", geocoder_benchmark=first_manifest.geocoder_benchmark, geography_vintage="DifferentPinnedVintage"),
        supported_layers=(
            CensusGeographyLayerSpec(GeographyType.STATE, 901, ("Different State Alias",), True),
        ),
    )
    address = dict(street="4600 Silver Hill Rd", city="Washington", state="DC", zip_code="20233")
    first = client.acquire_geocode(
        request=CensusAddressRequest(manifest=first_manifest, **address),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    second = client.acquire_geocode(
        request=CensusAddressRequest(manifest=second_manifest, **address),
        persistence_policy=policy(), retrieved_at=NOW,
    )
    assert first.artifact.request_fingerprint == second.artifact.request_fingerprint


def test_geography_request_uses_exact_manifest_layer_ids_and_fingerprint_commits_to_them():
    body = json.dumps({"result": {"input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}, "vintage": {"vintageName": "ACS2024_ACS2024"}}, "geographies": {}}}).encode()
    transport = FakeTransport(HTTPResponse(200, (), body))
    client = CensusGeocoderClient(transport=transport, artifact_store=MemoryArtifactStore())
    first_manifest = manifest()
    changed_layers = CensusGeographyManifest(
        manifest_version=first_manifest.manifest_version,
        compatibility=compatibility(compatibility_id=first_manifest.compatibility_id, compatibility_version=first_manifest.compatibility_version, geocoder_benchmark=first_manifest.geocoder_benchmark, geography_vintage=first_manifest.geography_vintage),
        supported_layers=(
            CensusGeographyLayerSpec(GeographyType.STATE, 999, ("States",), True),
            *first_manifest.supported_layers[1:],
        ),
    )
    coordinates = CensusCoordinates(latitude=38.5, longitude=-76.5)
    first = client.acquire_geography(
        coordinates=coordinates, manifest=first_manifest, persistence_policy=policy(), retrieved_at=NOW,
    )
    second = client.acquire_geography(
        coordinates=coordinates, manifest=changed_layers, persistence_policy=policy(), retrieved_at=NOW,
    )
    first_query = dict(transport.requests[-2].query)
    second_query = dict(transport.requests[-1].query)
    assert first_query["layers"] == "101,102,103,104"
    assert second_query["layers"] == "999,102,103,104"
    assert first.artifact.request_fingerprint != second.artifact.request_fingerprint


def test_required_flag_does_not_change_geography_http_request_fingerprint():
    body = json.dumps({"result": {"input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}, "vintage": {"vintageName": "ACS2024_ACS2024"}}, "geographies": {}}}).encode()
    transport = FakeTransport(HTTPResponse(200, (), body))
    client = CensusGeocoderClient(transport=transport, artifact_store=MemoryArtifactStore())
    first_manifest = manifest()
    changed_requiredness = CensusGeographyManifest(
        first_manifest.manifest_version,
        first_manifest.compatibility,
        (
            CensusGeographyLayerSpec(GeographyType.STATE, 101, ("States",), False),
            *first_manifest.supported_layers[1:],
        ),
    )
    coordinates = CensusCoordinates(latitude=38.5, longitude=-76.5)
    first = client.acquire_geography(coordinates=coordinates, manifest=first_manifest, persistence_policy=policy(), retrieved_at=NOW)
    second = client.acquire_geography(coordinates=coordinates, manifest=changed_requiredness, persistence_policy=policy(), retrieved_at=NOW)
    assert first.artifact.request_fingerprint == second.artifact.request_fingerprint
    assert first_manifest.identity != changed_requiredness.identity
