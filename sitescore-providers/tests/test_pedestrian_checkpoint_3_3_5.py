from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from sitescore_data import DataQualityState, PersistenceClass
from sitescore_data.schemas.geography import ResolvedLocation
from sitescore_data.schemas.common import SourceMetadata

from sitescore_providers.artifacts import ArtifactRef
from sitescore_providers.hashing import sha256_bytes
from sitescore_providers.policy import (
    CommercialUseState,
    PersistenceDecision,
    ProviderPolicyDecision,
    RedistributionState,
)
from sitescore_providers.results import AcquisitionState, ProviderFailureKind
from sitescore_providers.pedestrian.models import (
    CanonicalPedestrianGeometry,
    OriginSnapState,
    PedestrianAreaEvidence,
    PedestrianAreaPolicy,
    PedestrianGeometryPolicy,
    PedestrianGraphCompatibility,
    PedestrianIsochroneRequest,
    PedestrianNetworkManifest,
    PedestrianRoutingEngineManifest,
    PedestrianRoutingOrigin,
    ValhallaExecutionBinding,
    ValhallaIsochroneExecutionPolicy,
    WalkingBudgetPolicy,
    WalkingBudgetScale,
)
from sitescore_providers.pedestrian.client import (
    PedestrianIsochroneClient,
    ValhallaJSONResponse,
    build_isochrone_request_fingerprint,
    build_valhalla_isochrone_body,
)
from sitescore_providers.pedestrian.parser import (
    canonicalize_geometry,
    parse_valhalla_isochrone_evidence,
)
from sitescore_providers.pedestrian.builders import (
    build_network_source_evidence,
    build_pedestrian_frozen_result,
    build_routing_source_metadata,
)

NOW = datetime(2026, 8, 13, 0, 0, tzinfo=timezone.utc)


class MemoryStore:
    def __init__(self):
        self.values: dict[str, bytes] = {}

    def put(self, *, content_hash, content: bytes) -> ArtifactRef:
        ref = ArtifactRef(f"artifact://sha256/{content_hash.digest}")
        self.values[str(ref)] = content
        return ref

    def get(self, artifact_ref: ArtifactRef) -> bytes:
        return self.values[str(artifact_ref)]

    def exists(self, artifact_ref: ArtifactRef) -> bool:
        return str(artifact_ref) in self.values


class FakeTransport:
    def __init__(self, response: ValhallaJSONResponse):
        self.response = response
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return self.response


class FailingTransport:
    def send(self, request):
        from sitescore_providers.errors import ProviderUnavailableError
        raise ProviderUnavailableError("down")


def persist_policy(policy_id="pedestrian_policy"):
    persistence = PersistenceDecision(policy_id, "v1", PersistenceClass.PERSIST)
    return ProviderPolicyDecision(
        policy_id=policy_id,
        policy_version="v1",
        persistence=persistence,
        attribution_required=True,
        redistribution_state=RedistributionState.ALLOWED,
        commercial_use_state=CommercialUseState.ALLOWED,
        license_class="ODbL-1.0" if policy_id == "osm_policy" else "provider-policy",
    )


def transient_policy():
    persistence = PersistenceDecision("route_policy", "v1", PersistenceClass.TRANSIENT, max_retention_seconds=3600)
    return ProviderPolicyDecision(
        policy_id="route_policy",
        policy_version="v1",
        persistence=persistence,
        attribution_required=False,
        redistribution_state=RedistributionState.UNKNOWN,
        commercial_use_state=CommercialUseState.UNKNOWN,
    )


def network_manifest(content=b"osm-network", release="2026-08-10"):
    return PedestrianNetworkManifest(
        manifest_version="v1",
        source_provider="openstreetmap",
        dataset="osm_extract",
        extract_id="us_ny_metro",
        network_content_hash=sha256_bytes(content),
        source_release=release,
        format_id="osm_pbf",
        format_version="pbf_v1",
        parser_build_version="v1",
        acquisition_id="trusted_extract",
        acquisition_version="v1",
    )


def engine_manifest(version="3.8.3", options=()):
    return PedestrianRoutingEngineManifest(
        manifest_version="v1",
        engine_id="valhalla",
        engine_version=version,
        graph_build_method="mjolnir_tiles",
        graph_build_version="v1",
        costing_profile_id="pedestrian",
        costing_profile_version="valhalla_pedestrian_v1",
        costing_options=options,
        request_grammar_version="v1",
    )


def compatibility(network=None, engine=None, graph=b"graph", graph_artifact_ref="artifact://graph/ny_walk.tar"):
    network = network or network_manifest()
    engine = engine or engine_manifest()
    return PedestrianGraphCompatibility(
        compatibility_id="ny_walk_graph",
        compatibility_version="v1",
        network_manifest=network,
        routing_engine_manifest=engine,
        graph_content_hash=sha256_bytes(graph),
        graph_artifact_ref=ArtifactRef(graph_artifact_ref),
    )


def execution_policy(max_contours=4, max_time=60.0):
    return ValhallaIsochroneExecutionPolicy(
        policy_id="valhalla_isochrone_limits",
        policy_version="v1",
        max_contours=max_contours,
        max_time_contour_minutes=max_time,
    )


def execution_binding(compat=None, policy=None, binding_version="v1"):
    compat = compat or compatibility()
    return ValhallaExecutionBinding(
        binding_id="ny_valhalla_deployment",
        binding_version=binding_version,
        graph_compatibility=compat,
        execution_policy=policy or execution_policy(),
    )


def location(lat=40.74, lon=-73.99):
    return ResolvedLocation(
        latitude=lat,
        longitude=lon,
        formatted_address="1 Test St, New York, NY",
        country_code="US",
        geography_refs=(),
        source_refs=("source.geocode",),
        resolution_method_version="census.v1",
        generated_at=NOW,
    )


def budget(costs=(300.0, 600.0)):
    return WalkingBudgetPolicy(
        policy_id="walking_budget",
        policy_version="v1",
        scales=tuple(WalkingBudgetScale(f"walk_{int(c)}s", c) for c in costs),
    )


def geometry_policy(denoise=1.0):
    return PedestrianGeometryPolicy(
        policy_id="valhalla_geojson",
        policy_version="v1",
        crs_id="epsg_4326",
        representation="geojson",
        polygons=True,
        denoise=denoise,
        generalize_meters=None,
        canonical_geometry_version="v1",
    )


def request(loc=None, budgets=None, compat=None, geo=None, binding=None):
    compat = compat or compatibility()
    binding = binding or execution_binding(compat)
    return PedestrianIsochroneRequest(
        origin=PedestrianRoutingOrigin.from_resolved_location(loc or location()),
        budget_policy=budgets or budget(),
        graph_compatibility=compat,
        execution_binding=binding,
        geometry_policy=geo or geometry_policy(),
    )


def polygon(offset=0.0, reverse=False):
    ring = [
        [-74.00 + offset, 40.73],
        [-73.98 + offset, 40.73],
        [-73.98 + offset, 40.75],
        [-74.00 + offset, 40.75],
        [-74.00 + offset, 40.73],
    ]
    if reverse:
        ring = list(reversed(ring))
    return {"type": "Polygon", "coordinates": [ring]}


def response_payload(req=None, include_locations=True, omit_scale=None, duplicate_scale=None, reverse_geometry=False):
    req = req or request()
    features = []
    for idx, scale in enumerate(req.budget_policy.scales):
        if scale.scale_id == omit_scale:
            continue
        feature = {
            "type": "Feature",
            "properties": {"metric": "time", "contour": float(scale.travel_cost_seconds) / 60.0},
            "geometry": polygon(idx * 0.001, reverse_geometry),
        }
        features.append(feature)
        if scale.scale_id == duplicate_scale:
            features.append(feature)
    if include_locations:
        features += [
            {"type": "Feature", "properties": {}, "geometry": {"type": "MultiPoint", "coordinates": [[req.origin.longitude, req.origin.latitude]]}},
            {"type": "Feature", "properties": {}, "geometry": {"type": "MultiPoint", "coordinates": [[req.origin.longitude + 0.0001, req.origin.latitude + 0.0001]]}},
        ]
    return {"type": "FeatureCollection", "features": features}


def acquire_and_parse(req=None, payload=None, persistence=None):
    req = req or request()
    payload = payload or response_payload(req)
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    store = MemoryStore()
    transport = FakeTransport(ValhallaJSONResponse(200, body, "application/geo+json"))
    client = PedestrianIsochroneClient(
        transport=transport,
        artifact_store=store,
        endpoint_url="http://valhalla.test/isochrone",
        execution_binding=req.execution_binding,
    )
    policy = persistence or persist_policy("route_policy")
    acquired = client.acquire(request=req, persistence_policy=policy, retrieved_at=NOW)
    assert acquired.state is AcquisitionState.SUCCESS
    parsed = client.parse_success(acquisition=acquired, request=req)
    evidence = parse_valhalla_isochrone_evidence(response=parsed, request=req)
    return client, acquired, parsed, evidence, policy


def test_network_manifest_deterministic_and_content_sensitive():
    a = network_manifest(); b = network_manifest()
    assert a.identity == b.identity
    assert a.identity != network_manifest(b"different").identity


def test_network_manifest_rejects_mutable_identity():
    with pytest.raises(ValueError): network_manifest(release="current")
    with pytest.raises(ValueError): network_manifest(release="latest")


def test_engine_profile_identity_is_deterministic_and_option_sensitive():
    assert engine_manifest().identity == engine_manifest().identity
    assert engine_manifest().identity != engine_manifest(options=(("walking_speed", 4.8),)).identity
    assert engine_manifest().identity != engine_manifest(version="3.8.2").identity


def test_graph_compatibility_binds_real_manifest_objects():
    a = compatibility(); b = compatibility(network=network_manifest(b"other"))
    assert a.identity != b.identity and a.graph_build_identity != b.graph_build_identity


def test_walking_budget_accepts_one_or_many_scales_without_global_radius():
    assert len(budget((300.0,)).scales) == 1
    assert len(budget().scales) == 2


def test_budget_policy_deterministic_and_budget_change_sensitive():
    assert budget().identity == budget().identity
    assert budget().identity != budget((300.0, 900.0)).identity


def test_request_fingerprint_deterministic_and_parameter_order_independent():
    r1 = request(compat=compatibility(engine=engine_manifest(options=(("alley_factor", 2.0), ("walking_speed", 5.0)))))
    r2 = request(compat=compatibility(engine=engine_manifest(options=(("alley_factor", 2.0), ("walking_speed", 5.0)))))
    assert build_isochrone_request_fingerprint(r1) == build_isochrone_request_fingerprint(r2)


def test_request_fingerprint_changes_for_origin_budget_profile_or_network():
    base = build_isochrone_request_fingerprint(request())
    assert base != build_isochrone_request_fingerprint(request(loc=location(40.741, -73.99)))
    assert base != build_isochrone_request_fingerprint(request(budgets=budget((300.0, 900.0))))
    assert base != build_isochrone_request_fingerprint(request(compat=compatibility(engine=engine_manifest(options=(("walking_speed", 4.5),)))))
    assert base != build_isochrone_request_fingerprint(request(compat=compatibility(network=network_manifest(b"other"))))


def test_execution_endpoint_headers_and_secrets_not_in_fingerprint_or_body():
    req = request()
    fingerprint = build_isochrone_request_fingerprint(req)
    body = build_valhalla_isochrone_body(req)
    transport = FakeTransport(ValhallaJSONResponse(500, b"{}"))
    client = PedestrianIsochroneClient(
        transport=transport, artifact_store=MemoryStore(), endpoint_url="https://router.example/isochrone",
        execution_binding=req.execution_binding,
        execution_headers=(("Authorization", "Bearer SUPERSECRET"),),
    )
    result = client.acquire(request=req, persistence_policy=persist_policy("route_policy"), retrieved_at=NOW)
    assert result.state is AcquisitionState.PROVIDER_FAILURE
    assert b"SUPERSECRET" not in body
    assert fingerprint == build_isochrone_request_fingerprint(req)


def test_valhalla_body_uses_lon_lat_correctly_and_time_minutes():
    req = request()
    payload = json.loads(build_valhalla_isochrone_body(req))
    assert payload["locations"] == [{"lat": 40.74, "lon": -73.99}]
    assert payload["contours"] == [{"time": 5.0}, {"time": 10.0}]
    assert payload["costing"] == "pedestrian" and payload["show_locations"] is True


def test_origin_coordinate_bounds_and_bool_rejected():
    with pytest.raises(ValueError): request(loc=location(91.0, 0.0))
    with pytest.raises(TypeError): PedestrianRoutingOrigin("location.x", sha256_bytes(b"x"), True, 1.0)


def test_parser_requires_all_requested_scales_and_rejects_duplicates():
    req = request()
    _,_,parsed,_,_ = acquire_and_parse(req=req)
    # baseline parses; now separate malformed payloads
    with pytest.raises(Exception): acquire_and_parse(req=req, payload=response_payload(req, omit_scale="walk_600s"))
    with pytest.raises(Exception): acquire_and_parse(req=req, payload=response_payload(req, duplicate_scale="walk_300s"))


def test_parser_rejects_malformed_contour_geometry():
    req = request(); payload = response_payload(req)
    payload["features"][0]["geometry"] = {"type": "Polygon", "coordinates": [[[-74,40],[-73,40],[-74,40]]]}
    with pytest.raises(Exception): acquire_and_parse(req=req, payload=payload)


def test_missing_show_locations_is_unknown_not_zero():
    req=request(); _,_,_,evidence,_=acquire_and_parse(req=req,payload=response_payload(req,include_locations=False))
    assert evidence.routed_origin.snap_state is OriginSnapState.UNKNOWN
    assert all(c.travel_cost_seconds > 0 for c in evidence.contours)


def test_identical_exact_and_snapped_coordinates_are_ambiguous_unknown():
    req=request(); payload=response_payload(req,include_locations=False)
    exact=[req.origin.longitude,req.origin.latitude]
    payload["features"] += [
        {"type":"Feature","properties":{},"geometry":{"type":"MultiPoint","coordinates":[exact]}},
        {"type":"Feature","properties":{},"geometry":{"type":"MultiPoint","coordinates":[exact]}},
    ]
    _,_,_,evidence,_=acquire_and_parse(req=req,payload=payload)
    assert evidence.routed_origin.snap_state is OriginSnapState.UNKNOWN
    assert evidence.routed_origin.routed_latitude is None
    assert evidence.routed_origin.routed_longitude is None


def test_geometry_ring_orientation_and_start_order_are_canonical():
    req=request()
    g1=canonicalize_geometry(geometry=polygon(reverse=False),request=req)
    g2=canonicalize_geometry(geometry=polygon(reverse=True),request=req)
    assert g1.coordinates == g2.coordinates and g1.identity == g2.identity


def test_multipolygon_processing_order_is_canonical():
    req=request()
    p1=polygon(0.0)["coordinates"]; p2=polygon(0.02)["coordinates"]
    g1=canonicalize_geometry(geometry={"type":"MultiPolygon","coordinates":[p1,p2]},request=req)
    g2=canonicalize_geometry(geometry={"type":"MultiPolygon","coordinates":[p2,p1]},request=req)
    assert g1.identity == g2.identity


def test_area_policy_identity_is_method_sensitive():
    a=PedestrianAreaPolicy("geodesic_area","v1","geodesic_wgs84","v1")
    b=PedestrianAreaPolicy("geodesic_area","v1","equal_area_projection","v1")
    assert a.identity != b.identity


def _sources_and_result(req=None, area_method="geodesic_wgs84", generated=NOW):
    req=req or request()
    _,_,_,evidence,route_policy=acquire_and_parse(req=req)
    network=build_network_source_evidence(
        manifest=req.graph_compatibility.network_manifest,
        artifact_ref=ArtifactRef("artifact://network/osm.pbf"),
        retrieved_at=NOW,
        policy=persist_policy("osm_policy"),
        source_reference="https://planet.openstreetmap.org/",
    )
    routing_meta=build_routing_source_metadata(
        evidence=evidence,
        policy=route_policy,
        source_reference="https://router.example/isochrone",
    )
    policy=PedestrianAreaPolicy("walk_area","v1",area_method,"v1")
    areas=tuple(PedestrianAreaEvidence(c.scale_id,c.geometry.identity,1.0+i,policy) for i,c in enumerate(evidence.contours))
    result=build_pedestrian_frozen_result(
        evidence=evidence, area_evidence=areas, network_source=network,
        routing_source_metadata=routing_meta, generated_at=generated,
    )
    return evidence, network, routing_meta, result


def test_frozen_catchment_and_isochrone_mapping_per_scale():
    evidence,network,routing,result=_sources_and_result()
    assert len(result.catchments)==len(evidence.contours)==2
    assert len(result.snapshots)==2
    for c,s in zip(result.catchments,result.snapshots):
        assert c.travel_mode == "walk"
        assert s.catchment_ref == c.catchment_id
        assert s.area_km2.unit == "km2"
        assert s.area_km2.score_eligibility.value == "diagnostic_only"
        assert s.area_km2.calibration_state.value == "uncalibrated"
        assert network.source_metadata.source_id in s.source_refs
        assert routing.source_id in s.source_refs


def test_network_and_routing_source_identities_are_not_conflated():
    _,network,routing,result=_sources_and_result()
    assert network.source_metadata.source_id != routing.source_id
    assert set(result.snapshots[0].source_refs)=={network.source_metadata.source_id,routing.source_id}


def test_wrong_network_graph_pair_rejected_at_frozen_builder():
    req=request(); _,_,_,evidence,route_policy=acquire_and_parse(req=req)
    wrong_network=build_network_source_evidence(
        manifest=network_manifest(b"wrong"), artifact_ref=ArtifactRef("artifact://network/wrong.pbf"),
        retrieved_at=NOW, policy=persist_policy("osm_policy"),
    )
    routing=build_routing_source_metadata(evidence=evidence,policy=route_policy)
    ap=PedestrianAreaPolicy("walk_area","v1","geodesic_wgs84","v1")
    areas=tuple(PedestrianAreaEvidence(c.scale_id,c.geometry.identity,1.0,ap) for c in evidence.contours)
    with pytest.raises(ValueError):
        build_pedestrian_frozen_result(evidence=evidence,area_evidence=areas,network_source=wrong_network,routing_source_metadata=routing,generated_at=NOW)


def test_unresolved_snap_cannot_become_available_zero_snapshot():
    req=request(); _,_,_,evidence,route_policy=acquire_and_parse(req=req,payload=response_payload(req,include_locations=False))
    network=build_network_source_evidence(manifest=req.graph_compatibility.network_manifest,artifact_ref=ArtifactRef("artifact://network/osm.pbf"),retrieved_at=NOW,policy=persist_policy("osm_policy"))
    routing=build_routing_source_metadata(evidence=evidence,policy=route_policy)
    ap=PedestrianAreaPolicy("walk_area","v1","geodesic_wgs84","v1")
    areas=tuple(PedestrianAreaEvidence(c.scale_id,c.geometry.identity,0.0,ap) for c in evidence.contours)
    with pytest.raises(ValueError): build_pedestrian_frozen_result(evidence=evidence,area_evidence=areas,network_source=network,routing_source_metadata=routing,generated_at=NOW)


def test_genuine_zero_precomputed_area_is_preserved_when_snap_resolved():
    req=request(); _,_,_,evidence,route_policy=acquire_and_parse(req=req)
    network=build_network_source_evidence(manifest=req.graph_compatibility.network_manifest,artifact_ref=ArtifactRef("artifact://network/osm.pbf"),retrieved_at=NOW,policy=persist_policy("osm_policy"))
    routing=build_routing_source_metadata(evidence=evidence,policy=route_policy)
    ap=PedestrianAreaPolicy("walk_area","v1","geodesic_wgs84","v1")
    areas=tuple(PedestrianAreaEvidence(c.scale_id,c.geometry.identity,0.0,ap) for c in evidence.contours)
    result=build_pedestrian_frozen_result(evidence=evidence,area_evidence=areas,network_source=network,routing_source_metadata=routing,generated_at=NOW)
    assert all(s.area_km2.value == 0.0 for s in result.snapshots)


def test_area_method_change_changes_derived_snapshot_identity():
    _,_,_,a=_sources_and_result(area_method="geodesic_wgs84")
    _,_,_,b=_sources_and_result(area_method="equal_area_v2")
    assert tuple(s.snapshot_id for s in a.snapshots) != tuple(s.snapshot_id for s in b.snapshots)


def test_same_inputs_and_same_generated_at_same_frozen_primitives():
    _,_,_,a=_sources_and_result(generated=NOW)
    _,_,_,b=_sources_and_result(generated=NOW)
    assert a.catchments == b.catchments and a.snapshots == b.snapshots


def test_explicit_generated_at_participates_in_frozen_primitive_equality_not_ids():
    later=datetime(2026,8,13,1,0,tzinfo=timezone.utc)
    _,_,_,a=_sources_and_result(generated=NOW)
    _,_,_,b=_sources_and_result(generated=later)
    assert a.snapshots != b.snapshots
    assert tuple(s.snapshot_id for s in a.snapshots)==tuple(s.snapshot_id for s in b.snapshots)


def test_provider_failure_is_typed_and_never_zero_reach():
    req=request(); client=PedestrianIsochroneClient(transport=FailingTransport(),artifact_store=MemoryStore(),endpoint_url="http://router/isochrone",execution_binding=req.execution_binding)
    result=client.acquire(request=req,persistence_policy=persist_policy("route_policy"),retrieved_at=NOW)
    assert result.state is AcquisitionState.PROVIDER_FAILURE
    assert result.failure.kind is ProviderFailureKind.UNAVAILABLE
    assert result.artifact is None


def test_network_source_requires_persist_for_canonical_replay():
    manifest=network_manifest(); p=PersistenceDecision("osm_policy","v1",PersistenceClass.TRANSIENT,max_retention_seconds=3600)
    policy=ProviderPolicyDecision("osm_policy","v1",p,True,RedistributionState.ALLOWED,CommercialUseState.ALLOWED,license_class="ODbL-1.0")
    with pytest.raises(ValueError): build_network_source_evidence(manifest=manifest,artifact_ref=ArtifactRef("artifact://network/x"),retrieved_at=NOW,policy=policy)


def test_no_radius_straight_line_demographic_or_out_of_scope_logic():
    root=Path(__file__).resolve().parents[1]/"src"/"sitescore_providers"/"pedestrian"
    text="\n".join(p.read_text().lower() for p in root.glob("*.py"))
    for forbidden in ("walk_radius", "straight_line", "walkable_population", "target_population_density", "ecdf", "normalization", "gtfs", "parking"):
        assert forbidden not in text


def test_no_sitescore_core_imports_in_pedestrian_module():
    root=Path(__file__).resolve().parents[1]/"src"/"sitescore_providers"/"pedestrian"
    text="\n".join(p.read_text() for p in root.glob("*.py"))
    assert "sitescore_core" not in text and "sitescore.core" not in text

def test_valhalla_no_suitable_edges_is_distinct_typed_condition_not_zero_reach():
    req=request(); body=json.dumps({"error_code":171,"error":"No suitable edges near location","status_code":400}).encode()
    client=PedestrianIsochroneClient(
        transport=FakeTransport(ValhallaJSONResponse(400,body)),
        artifact_store=MemoryStore(),endpoint_url="http://router/isochrone",
        execution_binding=req.execution_binding
    )
    result=client.acquire(request=req,persistence_policy=persist_policy("route_policy"),retrieved_at=NOW)
    assert result.state is AcquisitionState.PROVIDER_FAILURE
    assert result.failure.kind is ProviderFailureKind.INVARIANT
    assert result.failure.reason_code == "no_suitable_edges_near_location"
    assert result.artifact is None

def test_frozen_builder_revalidates_manual_evidence_request_lineage():
    req=request(); _,_,_,evidence,route_policy=acquire_and_parse(req=req)
    wrong_req=request(loc=location(40.742,-73.99))
    fabricated=replace(evidence, request=wrong_req)
    network=build_network_source_evidence(manifest=req.graph_compatibility.network_manifest,artifact_ref=ArtifactRef("artifact://network/osm.pbf"),retrieved_at=NOW,policy=persist_policy("osm_policy"))
    with pytest.raises(Exception): build_routing_source_metadata(evidence=fabricated,policy=route_policy)


def test_frozen_builder_revalidates_parser_identity():
    req=request(); _,_,_,evidence,route_policy=acquire_and_parse(req=req)
    fabricated=replace(evidence, parsed_artifact=replace(evidence.parsed_artifact, parser_id="wrong_parser"))
    with pytest.raises(Exception): build_routing_source_metadata(evidence=fabricated,policy=route_policy)


def test_execution_limits_at_limit_are_accepted_and_change_request_identity():
    compat = compatibility()
    p1 = execution_policy(max_contours=2, max_time=10.0)
    p2 = execution_policy(max_contours=3, max_time=10.0)
    r1 = request(budgets=budget((300.0, 600.0)), compat=compat, binding=execution_binding(compat, p1))
    r2 = request(budgets=budget((300.0, 600.0)), compat=compat, binding=execution_binding(compat, p2))
    assert build_isochrone_request_fingerprint(r1) != build_isochrone_request_fingerprint(r2)
    assert len(json.loads(build_valhalla_isochrone_body(r1))["contours"]) == 2


def test_execution_limits_reject_over_max_contours_before_transport():
    compat = compatibility()
    binding = execution_binding(compat, execution_policy(max_contours=1, max_time=60.0))
    with pytest.raises(ValueError, match="max_contours"):
        request(budgets=budget((300.0, 600.0)), compat=compat, binding=binding)


def test_execution_limits_reject_over_max_time_before_transport():
    compat = compatibility()
    binding = execution_binding(compat, execution_policy(max_contours=4, max_time=5.0))
    with pytest.raises(ValueError, match="max_time_contour"):
        request(budgets=budget((300.0, 360.0)), compat=compat, binding=binding)


def test_client_rejects_request_for_different_deployment_binding_before_network():
    compat_a = compatibility(graph=b"graph-a")
    compat_b = compatibility(graph=b"graph-b")
    req = request(compat=compat_a, binding=execution_binding(compat_a))
    transport = FakeTransport(ValhallaJSONResponse(200, b"{}"))
    client = PedestrianIsochroneClient(
        transport=transport,
        artifact_store=MemoryStore(),
        endpoint_url="http://router/isochrone",
        execution_binding=execution_binding(compat_b),
    )
    with pytest.raises(ValueError, match="deployment client"):
        client.acquire(request=req, persistence_policy=persist_policy("route_policy"), retrieved_at=NOW)
    assert transport.requests == []


def test_execution_binding_engine_or_service_config_change_changes_identity():
    compat_a = compatibility(engine=engine_manifest(version="3.8.3"))
    compat_b = compatibility(engine=engine_manifest(version="3.8.2"))
    a = execution_binding(compat_a, execution_policy(max_contours=4, max_time=60.0))
    b = execution_binding(compat_b, execution_policy(max_contours=4, max_time=60.0))
    c = execution_binding(compat_a, execution_policy(max_contours=4, max_time=45.0))
    assert a.identity != b.identity
    assert a.identity != c.identity


def test_valhalla_warnings_are_retained_but_rejected_for_canonical_available_snapshot():
    req = request()
    payload = response_payload(req)
    payload["warnings"] = [{"code": 9999, "text": "unknown execution warning"}]
    _, _, _, evidence, route_policy = acquire_and_parse(req=req, payload=payload)
    assert len(evidence.warnings) == 1
    assert evidence.warnings[0].state.value == "unresolved"

    network = build_network_source_evidence(
        manifest=req.graph_compatibility.network_manifest,
        artifact_ref=ArtifactRef("artifact://network/osm.pbf"),
        retrieved_at=NOW,
        policy=persist_policy("osm_policy"),
    )
    routing = build_routing_source_metadata(evidence=evidence, policy=route_policy)
    ap = PedestrianAreaPolicy("walk_area", "v1", "geodesic_wgs84", "v1")
    areas = tuple(PedestrianAreaEvidence(c.scale_id, c.geometry.identity, 1.0, ap) for c in evidence.contours)
    with pytest.raises(ValueError, match="warnings"):
        build_pedestrian_frozen_result(
            evidence=evidence,
            area_evidence=areas,
            network_source=network,
            routing_source_metadata=routing,
            generated_at=NOW,
        )


def test_show_locations_feature_order_reversal_does_not_change_snap_semantics():
    req = request()
    payload = response_payload(req)
    locations = [f for f in payload["features"] if f["geometry"]["type"] == "MultiPoint"]
    contours = [f for f in payload["features"] if f["geometry"]["type"] != "MultiPoint"]
    payload["features"] = contours + list(reversed(locations))
    _, _, _, evidence, _ = acquire_and_parse(req=req, payload=payload)
    assert evidence.routed_origin.snap_state is OriginSnapState.RESOLVED
    assert evidence.routed_origin.routed_longitude == pytest.approx(req.origin.longitude + 0.0001)
    assert evidence.routed_origin.routed_latitude == pytest.approx(req.origin.latitude + 0.0001)


def test_missing_one_show_locations_role_stays_unknown():
    req = request()
    payload = response_payload(req, include_locations=False)
    payload["features"].append({
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "MultiPoint", "coordinates": [[req.origin.longitude, req.origin.latitude]]},
    })
    _, _, _, evidence, _ = acquire_and_parse(req=req, payload=payload)
    assert evidence.routed_origin.snap_state is OriginSnapState.UNKNOWN


def test_network_source_rejects_raw_content_hash_not_equal_manifest_hash():
    from sitescore_providers.pedestrian.builders import PedestrianNetworkSourceEvidence
    network = build_network_source_evidence(
        manifest=network_manifest(),
        artifact_ref=ArtifactRef("artifact://network/osm.pbf"),
        retrieved_at=NOW,
        policy=persist_policy("osm_policy"),
    )
    wrong_raw = replace(network.raw_artifact, content_hash=sha256_bytes(b"wrong-network-content"))
    with pytest.raises(ValueError, match="content hash"):
        PedestrianNetworkSourceEvidence(network.manifest, wrong_raw, network.source_metadata)


def test_graph_artifact_ref_is_replay_provenance_not_semantic_execution_identity():
    compat_a = compatibility(graph=b"same-graph", graph_artifact_ref="artifact://graph/location-a.tar")
    compat_b = compatibility(graph=b"same-graph", graph_artifact_ref="artifact://graph/location-b.tar")
    assert compat_a.graph_artifact_ref != compat_b.graph_artifact_ref
    assert compat_a.identity == compat_b.identity

    binding_a = execution_binding(compat_a)
    binding_b = execution_binding(compat_b)
    assert binding_a.identity == binding_b.identity

    request_a = request(compat=compat_a, binding=binding_a)
    request_b = request(compat=compat_b, binding=binding_b)
    assert build_isochrone_request_fingerprint(request_a) == build_isochrone_request_fingerprint(request_b)


def test_graph_content_hash_remains_semantic_for_compatibility_binding_and_request():
    compat_a = compatibility(graph=b"graph-a", graph_artifact_ref="artifact://graph/same-path.tar")
    compat_b = compatibility(graph=b"graph-b", graph_artifact_ref="artifact://graph/same-path.tar")
    assert compat_a.identity != compat_b.identity

    binding_a = execution_binding(compat_a)
    binding_b = execution_binding(compat_b)
    assert binding_a.identity != binding_b.identity
    assert build_isochrone_request_fingerprint(request(compat=compat_a, binding=binding_a)) != build_isochrone_request_fingerprint(request(compat=compat_b, binding=binding_b))


def test_execution_policy_and_engine_profile_remain_semantic_after_artifact_ref_exclusion():
    compat = compatibility(graph=b"same-graph")
    binding_a = execution_binding(compat, execution_policy(max_contours=4, max_time=60.0))
    binding_b = execution_binding(compat, execution_policy(max_contours=4, max_time=45.0))
    assert binding_a.identity != binding_b.identity
    assert build_isochrone_request_fingerprint(request(compat=compat, binding=binding_a)) != build_isochrone_request_fingerprint(request(compat=compat, binding=binding_b))

    changed_engine = compatibility(graph=b"same-graph", engine=engine_manifest(options=(("walking_speed", 4.8),)))
    changed_binding = execution_binding(changed_engine)
    assert binding_a.identity != changed_binding.identity
    assert build_isochrone_request_fingerprint(request(compat=compat, binding=binding_a)) != build_isochrone_request_fingerprint(request(compat=changed_engine, binding=changed_binding))
