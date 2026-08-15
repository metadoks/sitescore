"""Immutable U.S. Census Geocoder / GeoLookup provider evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from sitescore_data import GeographyType

from .._validation import require_canonical_id, require_nonempty_text, require_optional_nonempty_text
from ..artifacts import ParsedArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from ..identity import RequestFingerprint

CENSUS_PROVIDER_KEY = "us_census_geocoder"
CENSUS_GEOCODER_BASE_URL = "https://geocoding.geo.census.gov/geocoder"
CENSUS_COUNTRY_CODE = "US"
CENSUS_MANIFEST_GRAMMAR_VERSION = "v1"

# US V1 intentionally covers the 50 states plus District of Columbia. Census
# Geocoder also supports Puerto Rico and U.S. Island Areas; those require a
# separate country/territory mapping policy and are not silently coerced to US.
US_STATE_AND_DC_FIPS = frozenset({
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13",
    "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
    "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36",
    "37", "38", "39", "40", "41", "42", "44", "45", "46", "47", "48",
    "49", "50", "51", "53", "54", "55", "56",
})


def _reject_mutable_current(value: str, *, field_name: str) -> str:
    require_nonempty_text(value, field_name=field_name)
    if "current" in value.lower():
        raise ValueError(f"{field_name} must be explicitly pinned; mutable 'Current' identity is forbidden")
    return value


def _require_latitude(value: float, *, field_name: str = "latitude") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite numeric latitude")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    if value < -90.0 or value > 90.0:
        raise ValueError(f"{field_name} must be in [-90, 90]")
    return value


def _require_longitude(value: float, *, field_name: str = "longitude") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite numeric longitude")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    if value < -180.0 or value > 180.0:
        raise ValueError(f"{field_name} must be in [-180, 180]")
    return value


@dataclass(frozen=True, slots=True)
class CensusCoordinates:
    """Provider-neutral coordinate order: latitude first, longitude second."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "latitude", _require_latitude(self.latitude))
        object.__setattr__(self, "longitude", _require_longitude(self.longitude))


@dataclass(frozen=True, slots=True)
class CensusGeographyLayerSpec:
    """Manifest-bound Census request layer identity and accepted response aliases.

    ``required`` is deployment/configuration policy for this exact manifest, not an
    intrinsic property of ``GeographyType`` and not part of the HTTP request.
    """

    geography_type: GeographyType
    request_layer_id: int
    response_keys: tuple[str, ...]
    required: bool

    def __post_init__(self) -> None:
        if not isinstance(self.geography_type, GeographyType):
            raise TypeError("geography_type must be a GeographyType")
        if self.geography_type in {GeographyType.CUSTOM, GeographyType.UNKNOWN, GeographyType.COUNTRY}:
            raise ValueError("layer specs must name a concrete Census response geography type")
        if isinstance(self.request_layer_id, bool) or not isinstance(self.request_layer_id, int):
            raise TypeError("request_layer_id must be a positive Census numeric layer ID")
        if self.request_layer_id <= 0:
            raise ValueError("request_layer_id must be positive")
        if not isinstance(self.response_keys, tuple) or not self.response_keys:
            raise TypeError("response_keys must be a non-empty tuple")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a bool")
        for key in self.response_keys:
            require_nonempty_text(key, field_name="response_key")
        if len(set(self.response_keys)) != len(self.response_keys):
            raise ValueError("response_keys must not contain duplicates")


@dataclass(frozen=True, slots=True)
class CensusBenchmarkVintageCompatibility:
    """Trusted deployment/configuration input for one exact Census pair.

    This object records the configuration authority's selected benchmark/vintage
    pair.  It is not a cryptographic approval and the provider package deliberately
    performs no live Census allowlist or auto-discovery.
    """

    compatibility_id: str
    compatibility_version: str
    geocoder_benchmark: str
    geography_vintage: str

    def __post_init__(self) -> None:
        require_canonical_id(self.compatibility_id, field_name="compatibility_id")
        require_nonempty_text(self.compatibility_version, field_name="compatibility_version")
        _reject_mutable_current(self.geocoder_benchmark, field_name="geocoder_benchmark")
        _reject_mutable_current(self.geography_vintage, field_name="geography_vintage")


@dataclass(frozen=True, slots=True)
class CensusGeographyManifest:
    """Exact Census compatibility selection plus manifest-bound layer semantics."""

    manifest_version: str
    compatibility: CensusBenchmarkVintageCompatibility
    supported_layers: tuple[CensusGeographyLayerSpec, ...]

    def __post_init__(self) -> None:
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        if not isinstance(self.compatibility, CensusBenchmarkVintageCompatibility):
            raise TypeError("compatibility must be a CensusBenchmarkVintageCompatibility")
        if not isinstance(self.supported_layers, tuple):
            raise TypeError("supported_layers must be a tuple")
        if not self.supported_layers:
            raise ValueError("supported_layers must not be empty")
        for layer in self.supported_layers:
            if not isinstance(layer, CensusGeographyLayerSpec):
                raise TypeError("supported_layers must contain CensusGeographyLayerSpec values")
        types = tuple(item.geography_type for item in self.supported_layers)
        request_ids = tuple(item.request_layer_id for item in self.supported_layers)
        keys = tuple(key for item in self.supported_layers for key in item.response_keys)
        if len(set(types)) != len(types):
            raise ValueError("supported_layers must not repeat geography types")
        if len(set(request_ids)) != len(request_ids):
            raise ValueError("supported_layers must not repeat Census request layer IDs")
        if len(set(keys)) != len(keys):
            raise ValueError("supported_layers must not repeat response keys")

    @property
    def compatibility_id(self) -> str:
        return self.compatibility.compatibility_id

    @property
    def compatibility_version(self) -> str:
        return self.compatibility.compatibility_version

    @property
    def geocoder_benchmark(self) -> str:
        return self.compatibility.geocoder_benchmark

    @property
    def geography_vintage(self) -> str:
        return self.compatibility.geography_vintage

    @property
    def identity(self) -> ContentHash:
        return hash_canonical(
            {
                "grammar_version": CENSUS_MANIFEST_GRAMMAR_VERSION,
                "canonicalization_version": CANONICALIZATION_VERSION,
                "manifest_version": self.manifest_version,
                "compatibility_id": self.compatibility.compatibility_id,
                "compatibility_version": self.compatibility.compatibility_version,
                "geocoder_benchmark": self.compatibility.geocoder_benchmark,
                "geography_vintage": self.compatibility.geography_vintage,
                "supported_layers": tuple(
                    {
                        "geography_type": item.geography_type.value,
                        "request_layer_id": item.request_layer_id,
                        "response_keys": item.response_keys,
                        "required": item.required,
                    }
                    for item in self.supported_layers
                ),
            }
        )


@dataclass(frozen=True, slots=True)
class CensusAddressRequest:
    street: str
    city: str | None
    state: str | None
    zip_code: str | None
    manifest: CensusGeographyManifest

    def __post_init__(self) -> None:
        require_nonempty_text(self.street, field_name="street")
        require_optional_nonempty_text(self.city, field_name="city")
        require_optional_nonempty_text(self.state, field_name="state")
        require_optional_nonempty_text(self.zip_code, field_name="zip_code")
        if not isinstance(self.manifest, CensusGeographyManifest):
            raise TypeError("manifest must be a CensusGeographyManifest")
        if self.zip_code is None and (self.city is None or self.state is None):
            raise ValueError("Census address requests require street+ZIP or street+city+state")

    @property
    def semantic_parameters(self) -> dict[str, object]:
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "zip": self.zip_code,
            "benchmark": self.manifest.geocoder_benchmark,
        }


class CensusMatchState(StrEnum):
    MATCHED = "matched"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"


class CensusGeocodePrecision(StrEnum):
    ADDRESS_RANGE_INTERPOLATED = "address_range_interpolated"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CensusGeocodeCandidate:
    matched_address: str
    coordinates: CensusCoordinates
    tiger_line_id: str | None
    tiger_line_side: str | None
    census_match_type: str | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.matched_address, field_name="matched_address")
        if not isinstance(self.coordinates, CensusCoordinates):
            raise TypeError("coordinates must be CensusCoordinates")
        require_optional_nonempty_text(self.tiger_line_id, field_name="tiger_line_id")
        require_optional_nonempty_text(self.tiger_line_side, field_name="tiger_line_side")
        require_optional_nonempty_text(self.census_match_type, field_name="census_match_type")


@dataclass(frozen=True, slots=True)
class CensusGeocodeEvidence:
    request_fingerprint: RequestFingerprint
    match_state: CensusMatchState
    candidates: tuple[CensusGeocodeCandidate, ...]
    benchmark: str
    precision: CensusGeocodePrecision
    parsed_artifact: ParsedArtifact

    def __post_init__(self) -> None:
        if not isinstance(self.request_fingerprint, RequestFingerprint):
            raise TypeError("request_fingerprint must be a RequestFingerprint")
        if not isinstance(self.match_state, CensusMatchState):
            raise TypeError("match_state must be a CensusMatchState")
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a tuple")
        for candidate in self.candidates:
            if not isinstance(candidate, CensusGeocodeCandidate):
                raise TypeError("candidates must contain CensusGeocodeCandidate values")
        _reject_mutable_current(self.benchmark, field_name="benchmark")
        if not isinstance(self.precision, CensusGeocodePrecision):
            raise TypeError("precision must be a CensusGeocodePrecision")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be a ParsedArtifact")
        if self.match_state is CensusMatchState.NO_MATCH and self.candidates:
            raise ValueError("NO_MATCH evidence cannot contain candidates")
        if self.match_state is CensusMatchState.MATCHED and len(self.candidates) != 1:
            raise ValueError("MATCHED evidence requires exactly one candidate")
        if self.match_state is CensusMatchState.AMBIGUOUS and len(self.candidates) < 2:
            raise ValueError("AMBIGUOUS evidence requires at least two candidates")


@dataclass(frozen=True, slots=True)
class CensusGeographyRecord:
    geography_type: GeographyType
    geoid: str
    name: str
    response_layer: str

    def __post_init__(self) -> None:
        if not isinstance(self.geography_type, GeographyType):
            raise TypeError("geography_type must be a GeographyType")
        require_nonempty_text(self.geoid, field_name="geoid")
        require_nonempty_text(self.name, field_name="name")
        require_nonempty_text(self.response_layer, field_name="response_layer")


@dataclass(frozen=True, slots=True)
class CensusGeographyEvidence:
    request_fingerprint: RequestFingerprint
    coordinates: CensusCoordinates
    benchmark: str
    geography_vintage: str
    manifest_identity: ContentHash
    records: tuple[CensusGeographyRecord, ...]
    parsed_artifact: ParsedArtifact

    def __post_init__(self) -> None:
        if not isinstance(self.request_fingerprint, RequestFingerprint):
            raise TypeError("request_fingerprint must be a RequestFingerprint")
        if not isinstance(self.coordinates, CensusCoordinates):
            raise TypeError("coordinates must be CensusCoordinates")
        _reject_mutable_current(self.benchmark, field_name="benchmark")
        _reject_mutable_current(self.geography_vintage, field_name="geography_vintage")
        if not isinstance(self.manifest_identity, ContentHash):
            raise TypeError("manifest_identity must be a ContentHash")
        if not isinstance(self.records, tuple):
            raise TypeError("records must be a tuple")
        for record in self.records:
            if not isinstance(record, CensusGeographyRecord):
                raise TypeError("records must contain CensusGeographyRecord values")
        keys = tuple((record.geography_type, record.geoid) for record in self.records)
        if len(set(keys)) != len(keys):
            raise ValueError("geography records must not contain duplicates")
        types = tuple(record.geography_type for record in self.records)
        if len(set(types)) != len(types):
            raise ValueError("a coordinate lookup may resolve at most one record per geography type")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be a ParsedArtifact")
