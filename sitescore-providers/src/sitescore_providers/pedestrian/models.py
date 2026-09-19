"""Immutable pedestrian network/routing policy and evidence contracts (Checkpoint 3.3-5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sitescore_data.schemas.geography import ResolvedLocation

from .._validation import require_canonical_id, require_finite_number, require_nonempty_text, require_optional_nonempty_text
from ..artifacts import ArtifactRef, ParsedArtifact, RawAcquisitionArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from ..identity import ProviderIdentity, RequestFingerprint

PEDESTRIAN_NETWORK_MANIFEST_GRAMMAR = "v1"
PEDESTRIAN_ROUTING_ENGINE_MANIFEST_GRAMMAR = "v1"
PEDESTRIAN_GRAPH_COMPATIBILITY_GRAMMAR = "v1"
WALKING_BUDGET_POLICY_GRAMMAR = "v1"
PEDESTRIAN_GEOMETRY_POLICY_GRAMMAR = "v1"
PEDESTRIAN_AREA_POLICY_GRAMMAR = "v1"
PEDESTRIAN_AREA_EVIDENCE_GRAMMAR = "v1"
PEDESTRIAN_ORIGIN_GRAMMAR = "v1"
PEDESTRIAN_REQUEST_GRAMMAR = "v1"
PEDESTRIAN_GEOMETRY_GRAMMAR = "v1"
PEDESTRIAN_EVIDENCE_GRAMMAR = "v1"
PEDESTRIAN_DERIVATION_GRAMMAR = "v1"
VALHALLA_EXECUTION_POLICY_GRAMMAR = "v1"
VALHALLA_EXECUTION_BINDING_GRAMMAR = "v1"
VALHALLA_WARNING_GRAMMAR = "v1"

VALHALLA_PROVIDER_KEY = "valhalla"
VALHALLA_ISOCHRONE_DATASET = "valhalla_isochrone"
VALHALLA_ISOCHRONE_OPERATION = "pedestrian_isochrone"
VALHALLA_PARSER_ID = "valhalla_isochrone_geojson"
WALK_TRAVEL_MODE = "walk"


def _reject_mutable_identity(value: str, *, field_name: str) -> str:
    require_nonempty_text(value, field_name=field_name)
    lowered = value.lower()
    if lowered in {"latest", "current", "live", "today", "now"} or "latest" in lowered or "current" in lowered:
        raise ValueError(f"{field_name} must be immutable/pinned, not mutable latest/current/live identity")
    return value


def _require_tuple(value: tuple[Any, ...], *, field_name: str) -> tuple[Any, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    return value


def _require_coordinate(latitude: float, longitude: float, *, prefix: str) -> None:
    require_finite_number(latitude, field_name=f"{prefix}_latitude")
    require_finite_number(longitude, field_name=f"{prefix}_longitude")
    if not -90.0 <= float(latitude) <= 90.0:
        raise ValueError(f"{prefix}_latitude must be in [-90, 90]")
    if not -180.0 <= float(longitude) <= 180.0:
        raise ValueError(f"{prefix}_longitude must be in [-180, 180]")


def _immutable_json_primitive(value: object, *, field_name: str) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        require_finite_number(value, field_name=field_name)
        return value
    if isinstance(value, list):
        return tuple(_immutable_json_primitive(v, field_name=field_name) for v in value)
    if isinstance(value, dict):
        items = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{field_name} mapping keys must be strings")
            items.append((key, _immutable_json_primitive(item, field_name=field_name)))
        return tuple(sorted(items, key=lambda pair: pair[0]))
    raise TypeError(f"{field_name} must be a JSON primitive/array/object")


def _primitive_option(value: object, *, field_name: str) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        require_finite_number(value, field_name=field_name)
        return value
    raise TypeError(f"{field_name} must be a scalar JSON primitive")


@dataclass(frozen=True, slots=True)
class PedestrianNetworkManifest:
    manifest_version: str
    source_provider: str
    dataset: str
    extract_id: str
    network_content_hash: ContentHash
    source_release: str
    format_id: str
    format_version: str
    parser_build_version: str
    acquisition_id: str
    acquisition_version: str

    def __post_init__(self) -> None:
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        require_canonical_id(self.source_provider, field_name="source_provider")
        require_nonempty_text(self.dataset, field_name="dataset")
        require_canonical_id(self.extract_id, field_name="extract_id")
        if not isinstance(self.network_content_hash, ContentHash):
            raise TypeError("network_content_hash must be a ContentHash")
        _reject_mutable_identity(self.source_release, field_name="source_release")
        require_canonical_id(self.format_id, field_name="format_id")
        require_nonempty_text(self.format_version, field_name="format_version")
        require_nonempty_text(self.parser_build_version, field_name="parser_build_version")
        require_canonical_id(self.acquisition_id, field_name="acquisition_id")
        require_nonempty_text(self.acquisition_version, field_name="acquisition_version")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_NETWORK_MANIFEST_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "manifest_version": self.manifest_version,
            "source_provider": self.source_provider,
            "dataset": self.dataset,
            "extract_id": self.extract_id,
            "network_content_hash": str(self.network_content_hash),
            "source_release": self.source_release,
            "format_id": self.format_id,
            "format_version": self.format_version,
            "parser_build_version": self.parser_build_version,
            "acquisition_id": self.acquisition_id,
            "acquisition_version": self.acquisition_version,
        })

    @property
    def provider_identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider_key=self.source_provider,
            domain="pedestrian_network",
            dataset=self.dataset,
            dataset_release=self.source_release,
            vintage=self.source_release,
            schema_version=self.format_version,
            parser_version=self.parser_build_version,
            method_version=f"{self.acquisition_id}.{self.acquisition_version}",
        )


@dataclass(frozen=True, slots=True)
class PedestrianRoutingEngineManifest:
    manifest_version: str
    engine_id: str
    engine_version: str
    graph_build_method: str
    graph_build_version: str
    costing_profile_id: str
    costing_profile_version: str
    costing_options: tuple[tuple[str, object], ...]
    request_grammar_version: str

    def __post_init__(self) -> None:
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        require_canonical_id(self.engine_id, field_name="engine_id")
        _reject_mutable_identity(self.engine_version, field_name="engine_version")
        require_canonical_id(self.graph_build_method, field_name="graph_build_method")
        require_nonempty_text(self.graph_build_version, field_name="graph_build_version")
        require_canonical_id(self.costing_profile_id, field_name="costing_profile_id")
        require_nonempty_text(self.costing_profile_version, field_name="costing_profile_version")
        _require_tuple(self.costing_options, field_name="costing_options")
        keys: list[str] = []
        for item in self.costing_options:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("costing_options entries must be (name, value) tuples")
            require_canonical_id(item[0], field_name="costing option name")
            _primitive_option(item[1], field_name=f"costing option {item[0]}")
            keys.append(item[0])
        if len(keys) != len(set(keys)):
            raise ValueError("costing_options must not contain duplicate keys")
        if tuple(keys) != tuple(sorted(keys)):
            raise ValueError("costing_options must be sorted by option name")
        require_nonempty_text(self.request_grammar_version, field_name="request_grammar_version")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_ROUTING_ENGINE_MANIFEST_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "manifest_version": self.manifest_version,
            "engine_id": self.engine_id,
            "engine_version": self.engine_version,
            "graph_build_method": self.graph_build_method,
            "graph_build_version": self.graph_build_version,
            "costing_profile_id": self.costing_profile_id,
            "costing_profile_version": self.costing_profile_version,
            "costing_options": self.costing_options,
            "request_grammar_version": self.request_grammar_version,
        })


@dataclass(frozen=True, slots=True)
class PedestrianGraphCompatibility:
    """Trusted deployment/config binding of one network snapshot to one built graph/engine.

    This object records an approved configuration boundary; it is not a
    cryptographic certification of how the graph was produced.
    """
    compatibility_id: str
    compatibility_version: str
    network_manifest: PedestrianNetworkManifest
    routing_engine_manifest: PedestrianRoutingEngineManifest
    graph_content_hash: ContentHash
    graph_artifact_ref: ArtifactRef

    def __post_init__(self) -> None:
        require_canonical_id(self.compatibility_id, field_name="compatibility_id")
        require_nonempty_text(self.compatibility_version, field_name="compatibility_version")
        if not isinstance(self.network_manifest, PedestrianNetworkManifest):
            raise TypeError("network_manifest must be a PedestrianNetworkManifest")
        if not isinstance(self.routing_engine_manifest, PedestrianRoutingEngineManifest):
            raise TypeError("routing_engine_manifest must be a PedestrianRoutingEngineManifest")
        if not isinstance(self.graph_content_hash, ContentHash):
            raise TypeError("graph_content_hash must be a ContentHash")
        if not isinstance(self.graph_artifact_ref, ArtifactRef):
            raise TypeError("graph_artifact_ref must be an ArtifactRef")

    @property
    def graph_build_identity(self) -> ContentHash:
        return hash_canonical({
            "network_manifest_identity": str(self.network_manifest.identity),
            "network_content_hash": str(self.network_manifest.network_content_hash),
            "engine_manifest_identity": str(self.routing_engine_manifest.identity),
            "graph_build_method": self.routing_engine_manifest.graph_build_method,
            "graph_build_version": self.routing_engine_manifest.graph_build_version,
            "graph_content_hash": str(self.graph_content_hash),
        })

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_GRAPH_COMPATIBILITY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "compatibility_id": self.compatibility_id,
            "compatibility_version": self.compatibility_version,
            "network_manifest_identity": str(self.network_manifest.identity),
            "routing_engine_manifest_identity": str(self.routing_engine_manifest.identity),
            "graph_build_identity": str(self.graph_build_identity),
        })


@dataclass(frozen=True, slots=True)
class ValhallaIsochroneExecutionPolicy:
    """Trusted deployed Valhalla isochrone service limits used for canonical execution."""

    policy_id: str
    policy_version: str
    max_contours: int
    max_time_contour_minutes: float

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if isinstance(self.max_contours, bool) or not isinstance(self.max_contours, int):
            raise TypeError("max_contours must be an int")
        if self.max_contours <= 0:
            raise ValueError("max_contours must be > 0")
        require_finite_number(self.max_time_contour_minutes, field_name="max_time_contour_minutes")
        if float(self.max_time_contour_minutes) <= 0:
            raise ValueError("max_time_contour_minutes must be > 0")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": VALHALLA_EXECUTION_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "max_contours": self.max_contours,
            "max_time_contour_minutes": float(self.max_time_contour_minutes),
        })


@dataclass(frozen=True, slots=True)
class ValhallaExecutionBinding:
    """Trusted deployment/config attestation for one Valhalla process/service.

    The binding states that the configured endpoint/process is deployed with the
    exact graph/engine compatibility and service-limit policy recorded here. It
    is not a runtime cryptographic attestation. Valhalla status metadata is not
    treated as an exact graph-content hash.
    """

    binding_id: str
    binding_version: str
    graph_compatibility: PedestrianGraphCompatibility
    execution_policy: ValhallaIsochroneExecutionPolicy

    def __post_init__(self) -> None:
        require_canonical_id(self.binding_id, field_name="binding_id")
        require_nonempty_text(self.binding_version, field_name="binding_version")
        if not isinstance(self.graph_compatibility, PedestrianGraphCompatibility):
            raise TypeError("graph_compatibility must be a PedestrianGraphCompatibility")
        if not isinstance(self.execution_policy, ValhallaIsochroneExecutionPolicy):
            raise TypeError("execution_policy must be a ValhallaIsochroneExecutionPolicy")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": VALHALLA_EXECUTION_BINDING_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "binding_id": self.binding_id,
            "binding_version": self.binding_version,
            "graph_compatibility_identity": str(self.graph_compatibility.identity),
            "graph_content_hash": str(self.graph_compatibility.graph_content_hash),
            "routing_engine_manifest_identity": str(self.graph_compatibility.routing_engine_manifest.identity),
            "execution_policy_identity": str(self.execution_policy.identity),
        })


class ValhallaWarningState(StrEnum):
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class ValhallaWarningEvidence:
    """Lossless canonical preservation of one Valhalla top-level warning.

    V1 deliberately does not invent warning-code semantics. Any warning is
    unresolved and therefore disqualifies canonical AVAILABLE output until an
    explicit versioned warning policy is approved.
    """

    warning_primitive: object
    state: ValhallaWarningState = ValhallaWarningState.UNRESOLVED

    def __post_init__(self) -> None:
        if not isinstance(self.state, ValhallaWarningState):
            raise TypeError("state must be a ValhallaWarningState")
        frozen = _immutable_json_primitive(self.warning_primitive, field_name="warning_primitive")
        object.__setattr__(self, "warning_primitive", frozen)

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": VALHALLA_WARNING_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "state": self.state.value,
            "warning": self.warning_primitive,
        })


@dataclass(frozen=True, slots=True)
class WalkingBudgetScale:
    scale_id: str
    travel_cost_seconds: float

    def __post_init__(self) -> None:
        require_canonical_id(self.scale_id, field_name="scale_id")
        require_finite_number(self.travel_cost_seconds, field_name="travel_cost_seconds")
        if float(self.travel_cost_seconds) <= 0:
            raise ValueError("travel_cost_seconds must be > 0")


@dataclass(frozen=True, slots=True)
class WalkingBudgetPolicy:
    policy_id: str
    policy_version: str
    scales: tuple[WalkingBudgetScale, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        _require_tuple(self.scales, field_name="scales")
        if not self.scales:
            raise ValueError("walking budget policy requires at least one scale")
        for scale in self.scales:
            if not isinstance(scale, WalkingBudgetScale):
                raise TypeError("scales must contain WalkingBudgetScale values")
        ids = tuple(scale.scale_id for scale in self.scales)
        costs = tuple(float(scale.travel_cost_seconds) for scale in self.scales)
        if len(ids) != len(set(ids)):
            raise ValueError("walking budget scale_id values must be unique")
        if len(costs) != len(set(costs)):
            raise ValueError("walking budget travel costs must be unique")
        expected = tuple(sorted(self.scales, key=lambda s: (float(s.travel_cost_seconds), s.scale_id)))
        if self.scales != expected:
            raise ValueError("walking budget scales must be deterministically ordered by travel cost then scale_id")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": WALKING_BUDGET_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "scales": tuple({"scale_id": s.scale_id, "travel_cost_seconds": float(s.travel_cost_seconds)} for s in self.scales),
        })


@dataclass(frozen=True, slots=True)
class PedestrianGeometryPolicy:
    policy_id: str
    policy_version: str
    crs_id: str
    representation: str
    polygons: bool = True
    denoise: float | None = None
    generalize_meters: float | None = None
    canonical_geometry_version: str = "v1"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        require_canonical_id(self.crs_id, field_name="crs_id")
        require_canonical_id(self.representation, field_name="representation")
        if not isinstance(self.polygons, bool):
            raise TypeError("polygons must be a bool")
        if not self.polygons:
            raise ValueError("canonical pedestrian reachability requires polygon output")
        if self.denoise is not None:
            require_finite_number(self.denoise, field_name="denoise")
            if not 0.0 <= float(self.denoise) <= 1.0:
                raise ValueError("denoise must be in [0, 1]")
        if self.generalize_meters is not None:
            require_finite_number(self.generalize_meters, field_name="generalize_meters")
            if float(self.generalize_meters) < 0:
                raise ValueError("generalize_meters must be >= 0")
        require_nonempty_text(self.canonical_geometry_version, field_name="canonical_geometry_version")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_GEOMETRY_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "crs_id": self.crs_id,
            "representation": self.representation,
            "polygons": self.polygons,
            "denoise": self.denoise,
            "generalize_meters": self.generalize_meters,
            "canonical_geometry_version": self.canonical_geometry_version,
        })


@dataclass(frozen=True, slots=True)
class PedestrianAreaPolicy:
    policy_id: str
    policy_version: str
    method_id: str
    method_version: str
    output_unit: str = "km2"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        require_canonical_id(self.method_id, field_name="method_id")
        require_nonempty_text(self.method_version, field_name="method_version")
        if self.output_unit != "km2":
            raise ValueError('pedestrian area policy output_unit must be "km2"')

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_AREA_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "output_unit": self.output_unit,
        })


def resolved_location_identity(location: ResolvedLocation) -> ContentHash:
    if not isinstance(location, ResolvedLocation):
        raise TypeError("location must be a ResolvedLocation")
    return hash_canonical({
        "latitude": location.latitude,
        "longitude": location.longitude,
        "formatted_address": location.formatted_address,
        "country_code": location.country_code,
        "geography_refs": tuple({
            "geography_type": g.geography_type.value,
            "geography_id": g.geography_id,
            "name": g.name,
            "country_code": g.country_code,
            "source_ref": g.source_ref,
            "source_version": g.source_version,
        } for g in location.geography_refs),
        "source_refs": location.source_refs,
        "resolution_method_version": location.resolution_method_version,
    })


@dataclass(frozen=True, slots=True)
class PedestrianRoutingOrigin:
    resolved_location_ref: str
    resolved_location_identity: ContentHash
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        require_canonical_id(self.resolved_location_ref, field_name="resolved_location_ref")
        if not isinstance(self.resolved_location_identity, ContentHash):
            raise TypeError("resolved_location_identity must be a ContentHash")
        _require_coordinate(self.latitude, self.longitude, prefix="origin")

    @classmethod
    def from_resolved_location(cls, location: ResolvedLocation) -> "PedestrianRoutingOrigin":
        identity = resolved_location_identity(location)
        return cls(
            resolved_location_ref=f"location.sha256_{identity.digest}",
            resolved_location_identity=identity,
            latitude=location.latitude,
            longitude=location.longitude,
        )

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_ORIGIN_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "resolved_location_ref": self.resolved_location_ref,
            "resolved_location_identity": str(self.resolved_location_identity),
            "latitude": self.latitude,
            "longitude": self.longitude,
        })


@dataclass(frozen=True, slots=True)
class PedestrianIsochroneRequest:
    origin: PedestrianRoutingOrigin
    budget_policy: WalkingBudgetPolicy
    graph_compatibility: PedestrianGraphCompatibility
    execution_binding: ValhallaExecutionBinding
    geometry_policy: PedestrianGeometryPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.origin, PedestrianRoutingOrigin):
            raise TypeError("origin must be a PedestrianRoutingOrigin")
        if not isinstance(self.budget_policy, WalkingBudgetPolicy):
            raise TypeError("budget_policy must be a WalkingBudgetPolicy")
        if not isinstance(self.graph_compatibility, PedestrianGraphCompatibility):
            raise TypeError("graph_compatibility must be a PedestrianGraphCompatibility")
        if not isinstance(self.execution_binding, ValhallaExecutionBinding):
            raise TypeError("execution_binding must be a ValhallaExecutionBinding")
        if self.execution_binding.graph_compatibility.identity != self.graph_compatibility.identity:
            raise ValueError("execution binding graph compatibility must match request graph compatibility")
        if not isinstance(self.geometry_policy, PedestrianGeometryPolicy):
            raise TypeError("geometry_policy must be a PedestrianGeometryPolicy")
        if self.engine_manifest.costing_profile_id != "pedestrian":
            raise ValueError('canonical V1 pedestrian request requires costing_profile_id="pedestrian"')
        if self.geometry_policy.representation != "geojson":
            raise ValueError('canonical V1 pedestrian request requires geometry representation "geojson"')
        if self.geometry_policy.crs_id != "epsg_4326":
            raise ValueError('canonical V1 pedestrian request requires WGS84 GeoJSON coordinates (epsg_4326)')
        execution = self.execution_binding.execution_policy
        if len(self.budget_policy.scales) > execution.max_contours:
            raise ValueError("walking budget exceeds deployed Valhalla max_contours")
        if any(float(scale.travel_cost_seconds) / 60.0 > float(execution.max_time_contour_minutes) for scale in self.budget_policy.scales):
            raise ValueError("walking budget exceeds deployed Valhalla max_time_contour_minutes")

    @property
    def engine_manifest(self) -> PedestrianRoutingEngineManifest:
        return self.graph_compatibility.routing_engine_manifest

    @property
    def semantic_parameters(self) -> dict[str, object]:
        engine = self.engine_manifest
        return {
            "origin": {"latitude": self.origin.latitude, "longitude": self.origin.longitude},
            "contours_seconds": tuple(float(s.travel_cost_seconds) for s in self.budget_policy.scales),
            "network_manifest_identity": str(self.graph_compatibility.network_manifest.identity),
            "graph_build_identity": str(self.graph_compatibility.graph_build_identity),
            "graph_content_hash": str(self.graph_compatibility.graph_content_hash),
            "execution_binding_identity": str(self.execution_binding.identity),
            "execution_policy_identity": str(self.execution_binding.execution_policy.identity),
            "engine_id": engine.engine_id,
            "engine_version": engine.engine_version,
            "costing_profile_id": engine.costing_profile_id,
            "costing_profile_version": engine.costing_profile_version,
            "costing_options": engine.costing_options,
            "polygons": self.geometry_policy.polygons,
            "denoise": self.geometry_policy.denoise,
            "generalize_meters": self.geometry_policy.generalize_meters,
            "show_locations": True,
            "reverse": False,
        }


class OriginSnapState(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RoutedOriginEvidence:
    requested_latitude: float
    requested_longitude: float
    snap_state: OriginSnapState
    routed_latitude: float | None
    routed_longitude: float | None

    def __post_init__(self) -> None:
        _require_coordinate(self.requested_latitude, self.requested_longitude, prefix="requested_origin")
        if not isinstance(self.snap_state, OriginSnapState):
            raise TypeError("snap_state must be an OriginSnapState")
        if self.snap_state is OriginSnapState.RESOLVED:
            if self.routed_latitude is None or self.routed_longitude is None:
                raise ValueError("RESOLVED snap requires routed coordinates")
            _require_coordinate(self.routed_latitude, self.routed_longitude, prefix="routed_origin")
        else:
            if self.routed_latitude is not None or self.routed_longitude is not None:
                raise ValueError("non-RESOLVED snap states cannot carry routed coordinates")


@dataclass(frozen=True, slots=True)
class CanonicalPedestrianGeometry:
    geometry_type: str
    coordinates: tuple[Any, ...]
    crs_id: str
    policy_identity: ContentHash

    def __post_init__(self) -> None:
        if self.geometry_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError("geometry_type must be Polygon or MultiPolygon")
        _require_tuple(self.coordinates, field_name="coordinates")
        require_canonical_id(self.crs_id, field_name="crs_id")
        if not isinstance(self.policy_identity, ContentHash):
            raise TypeError("policy_identity must be a ContentHash")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_GEOMETRY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "geometry_type": self.geometry_type,
            "coordinates": self.coordinates,
            "crs_id": self.crs_id,
            "geometry_policy_identity": str(self.policy_identity),
        })


@dataclass(frozen=True, slots=True)
class PedestrianContourEvidence:
    scale_id: str
    travel_cost_seconds: float
    geometry: CanonicalPedestrianGeometry

    def __post_init__(self) -> None:
        require_canonical_id(self.scale_id, field_name="scale_id")
        require_finite_number(self.travel_cost_seconds, field_name="travel_cost_seconds")
        if float(self.travel_cost_seconds) <= 0:
            raise ValueError("travel_cost_seconds must be > 0")
        if not isinstance(self.geometry, CanonicalPedestrianGeometry):
            raise TypeError("geometry must be CanonicalPedestrianGeometry")


@dataclass(frozen=True, slots=True)
class PedestrianIsochroneEvidence:
    request_fingerprint: RequestFingerprint
    request: PedestrianIsochroneRequest
    routed_origin: RoutedOriginEvidence
    contours: tuple[PedestrianContourEvidence, ...]
    warnings: tuple[ValhallaWarningEvidence, ...]
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact

    def __post_init__(self) -> None:
        if not isinstance(self.request_fingerprint, RequestFingerprint):
            raise TypeError("request_fingerprint must be a RequestFingerprint")
        if not isinstance(self.request, PedestrianIsochroneRequest):
            raise TypeError("request must be a PedestrianIsochroneRequest")
        if not isinstance(self.routed_origin, RoutedOriginEvidence):
            raise TypeError("routed_origin must be a RoutedOriginEvidence")
        _require_tuple(self.contours, field_name="contours")
        if not self.contours:
            raise ValueError("isochrone evidence requires at least one contour")
        for contour in self.contours:
            if not isinstance(contour, PedestrianContourEvidence):
                raise TypeError("contours must contain PedestrianContourEvidence values")
        _require_tuple(self.warnings, field_name="warnings")
        for warning in self.warnings:
            if not isinstance(warning, ValhallaWarningEvidence):
                raise TypeError("warnings must contain ValhallaWarningEvidence values")
        if not isinstance(self.raw_artifact, RawAcquisitionArtifact):
            raise TypeError("raw_artifact must be a RawAcquisitionArtifact")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be a ParsedArtifact")
        if self.raw_artifact.request_fingerprint != self.request_fingerprint:
            raise ValueError("raw request fingerprint must match evidence request fingerprint")
        if self.parsed_artifact.raw_content_hash != self.raw_artifact.content_hash:
            raise ValueError("parsed artifact raw lineage must match raw artifact content hash")
        expected_scales = tuple((s.scale_id, float(s.travel_cost_seconds)) for s in self.request.budget_policy.scales)
        actual_scales = tuple((s.scale_id, float(s.travel_cost_seconds)) for s in self.contours)
        if actual_scales != expected_scales:
            raise ValueError("contours must exactly match requested walking budget scales")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_EVIDENCE_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "request_fingerprint": str(self.request_fingerprint),
            "origin_identity": str(self.request.origin.identity),
            "graph_compatibility_identity": str(self.request.graph_compatibility.identity),
            "budget_policy_identity": str(self.request.budget_policy.identity),
            "geometry_policy_identity": str(self.request.geometry_policy.identity),
            "routed_origin": {
                "snap_state": self.routed_origin.snap_state.value,
                "routed_latitude": self.routed_origin.routed_latitude,
                "routed_longitude": self.routed_origin.routed_longitude,
            },
            "contours": tuple({
                "scale_id": c.scale_id,
                "travel_cost_seconds": float(c.travel_cost_seconds),
                "geometry_identity": str(c.geometry.identity),
            } for c in self.contours),
            "warnings": tuple(str(w.identity) for w in self.warnings),
            "execution_binding_identity": str(self.request.execution_binding.identity),
            "raw_content_hash": str(self.raw_artifact.content_hash),
            "parsed_artifact_identity": str(self.parsed_artifact.identity),
        })


@dataclass(frozen=True, slots=True)
class PedestrianAreaEvidence:
    scale_id: str
    geometry_identity: ContentHash
    area_km2: float
    area_policy: PedestrianAreaPolicy

    def __post_init__(self) -> None:
        require_canonical_id(self.scale_id, field_name="scale_id")
        if not isinstance(self.geometry_identity, ContentHash):
            raise TypeError("geometry_identity must be a ContentHash")
        require_finite_number(self.area_km2, field_name="area_km2")
        if float(self.area_km2) < 0:
            raise ValueError("area_km2 must be >= 0")
        if not isinstance(self.area_policy, PedestrianAreaPolicy):
            raise TypeError("area_policy must be a PedestrianAreaPolicy")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_AREA_EVIDENCE_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "geometry_identity": str(self.geometry_identity),
            "scale_id": self.scale_id,
            "area_km2": float(self.area_km2),
            "area_policy_identity": str(self.area_policy.identity),
        })


@dataclass(frozen=True, slots=True)
class PedestrianDerivationEvidence:
    isochrone_evidence_identity: ContentHash
    area_policy_identity: ContentHash
    network_source_ref: str
    routing_source_ref: str
    catchment_refs: tuple[str, ...]
    snapshot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.isochrone_evidence_identity, ContentHash):
            raise TypeError("isochrone_evidence_identity must be a ContentHash")
        if not isinstance(self.area_policy_identity, ContentHash):
            raise TypeError("area_policy_identity must be a ContentHash")
        require_canonical_id(self.network_source_ref, field_name="network_source_ref")
        require_canonical_id(self.routing_source_ref, field_name="routing_source_ref")
        _require_tuple(self.catchment_refs, field_name="catchment_refs")
        _require_tuple(self.snapshot_ids, field_name="snapshot_ids")
        for ref in self.catchment_refs:
            require_canonical_id(ref, field_name="catchment_ref")
        for ref in self.snapshot_ids:
            require_canonical_id(ref, field_name="snapshot_id")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": PEDESTRIAN_DERIVATION_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "isochrone_evidence_identity": str(self.isochrone_evidence_identity),
            "area_policy_identity": str(self.area_policy_identity),
            "network_source_ref": self.network_source_ref,
            "routing_source_ref": self.routing_source_ref,
            "catchment_refs": self.catchment_refs,
            "snapshot_ids": self.snapshot_ids,
        })
