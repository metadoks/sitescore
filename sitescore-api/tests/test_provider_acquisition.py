from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import io
import json
import zipfile
from uuid import uuid4

from pydantic import TypeAdapter
from shapely.geometry import Polygon

import sitescore_api.execution as execution_module
from sitescore.config.quality_levels import CoverageLevel, InputQuality
from sitescore_benchmarks import (
    CellResolutionPolicy,
    CellShape,
    CommercialEligibilityPolicy,
    CommercialEvidencePolicy,
    CommercialFrame,
    EqualAreaProjectionPolicy,
    FrameBoundaryMembershipPolicy,
    FrameState,
    LatticePolicy,
    ResolutionState,
    build_benchmark_distribution,
    build_benchmark_measurement_set,
)
from sitescore_data import GeographyType, PersistenceClass
from sitescore_providers import (
    ArtifactRef,
    CommercialUseState,
    PersistenceDecision,
    ProviderPolicyDecision,
    RedistributionState,
    sha256_bytes,
)
from sitescore_providers.acs import (
    ACSAgeCohortSpec,
    ACSDatasetManifest,
    ACSGeographyCompatibility,
    ACSProduct,
    ACSVariableManifest,
    ACSVariableRole,
    ACSVariableSpec,
    AgeCohortAggregationPolicy,
)
from sitescore_providers.census import (
    CensusBenchmarkVintageCompatibility,
    CensusGeographyLayerSpec,
    CensusGeographyManifest,
    GeocodeAcceptancePolicy,
)
from sitescore_providers.http import HTTPResponse
from sitescore_providers.overture.models import (
    CommercialSemanticClass,
    CompetitionEligibilityState,
    EntityDedupPolicy,
    OvertureCompetitionTaxonomyMapping,
    OvertureOperatingStatus,
    OverturePlacesReleaseManifest,
    OvertureTaxonomyRule,
    PlaceLifecyclePolicy,
    TaxonomyMatchField,
    TaxonomyResolutionPolicy,
)
from sitescore_providers.overture.reader import OverturePartitionDescriptor
from sitescore_providers.pedestrian.client import ValhallaJSONResponse
from sitescore_providers.pedestrian.models import (
    PedestrianAreaPolicy,
    PedestrianGeometryPolicy,
    PedestrianGraphCompatibility,
    PedestrianNetworkManifest,
    PedestrianRoutingEngineManifest,
    ValhallaExecutionBinding,
    ValhallaIsochroneExecutionPolicy,
    WalkingBudgetPolicy,
    WalkingBudgetScale,
)
from sitescore_providers.transit import (
    GTFSFeedManifest,
    GTFSFrequencyPolicy,
    GTFSServiceCalendarPolicy,
    GTFSStopHierarchyPolicy,
    TransitBoardingPolicy,
    TransitSourceBundle,
    TransitWeeklyProfilePolicy,
)
from sitescore_spatial import (
    GeographyIdentity,
    GeometryCanonicalizationPolicy,
    build_boundary_geometry_artifact,
    build_crs_identity,
    build_geometry_engine_identity,
    build_geometry_source_identity,
    canonicalize_geometry,
)

from sitescore_api.acquisition import (
    ACSAcquisitionConfig,
    CanonicalAcquisitionDeployment,
    CanonicalProviderEvidenceSource,
    CensusAcquisitionConfig,
    ExecutionQualityConfig,
    OvertureAcquisitionConfig,
    OverturePartitionInput,
    PedestrianAcquisitionConfig,
    TransitAcquisitionConfig,
    TransitReachabilityInput,
)
from sitescore_api.execution import CanonicalAnalysisExecutor
from sitescore_api.ingress import build_analysis_ingress_command
from sitescore_api.models import AnalysisRequest

NOW = datetime(2026, 8, 17, 15, 0, tzinfo=timezone.utc)
ADAPTER = TypeAdapter(AnalysisRequest)
NETWORK_BYTES = b"provider-acquisition-network"
OVERTURE_BYTES = b"provider-acquisition-overture-partition"


class MemoryArtifactStore:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def put(self, *, content_hash, content: bytes):
        ref = ArtifactRef(f"artifact://sha256/{content_hash.digest}")
        self.values[str(ref)] = content
        return ref

    def get(self, artifact_ref):
        return self.values[str(artifact_ref)]

    def exists(self, artifact_ref):
        return str(artifact_ref) in self.values


class ProviderHTTPTransport:
    def __init__(self) -> None:
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        if request.url.endswith("/locations/address"):
            body = {
                "result": {
                    "input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}},
                    "addressMatches": [
                        {
                            "tigerLine": {"side": "L", "tigerLineId": "76355984"},
                            "coordinates": {"x": -76.92748724230096, "y": 38.84601622386617},
                            "matchedAddress": "4600 SILVER HILL RD, WASHINGTON, DC, 20233",
                        }
                    ],
                }
            }
            return HTTPResponse(200, (), json.dumps(body, separators=(",", ":")).encode())
        if request.url.endswith("/geographies/coordinates"):
            body = {
                "result": {
                    "input": {
                        "benchmark": {"benchmarkName": "Public_AR_ACS2024"},
                        "vintage": {"vintageName": "ACS2024_ACS2024"},
                    },
                    "geographies": {
                        "States": [{"GEOID": "24", "NAME": "Maryland"}],
                        "Counties": [{"GEOID": "24033", "NAME": "Prince George's County"}],
                        "Census Tracts": [{"GEOID": "24033802405", "NAME": "Census Tract 8024.05"}],
                        "Census Block Groups": [{"GEOID": "240338024052", "NAME": "Block Group 2"}],
                    },
                }
            }
            return HTTPResponse(200, (), json.dumps(body, separators=(",", ":")).encode())

        query = dict(request.query)
        variables = tuple(query["get"].split(","))
        values = {
            "B01003_001E": "1000", "B01003_001M": "10", "B01003_001EA": None, "B01003_001MA": None,
            "B01001_003E": "200", "B01001_003M": "5", "B01001_003EA": None, "B01001_003MA": None,
            "B01001_027E": "200", "B01001_027M": "5", "B01001_027EA": None, "B01001_027MA": None,
            "B01001_011E": "300", "B01001_011M": "5", "B01001_011EA": None, "B01001_011MA": None,
            "B01001_035E": "300", "B01001_035M": "5", "B01001_035EA": None, "B01001_035MA": None,
            "B19013_001E": "80000", "B19013_001M": "5000", "B19013_001EA": None, "B19013_001MA": None,
        }
        header = list(variables) + ["state", "county", "tract", "block group"]
        row = [values[v] for v in variables] + ["24", "033", "802405", "2"]
        return HTTPResponse(200, (), json.dumps([header, row], separators=(",", ":")).encode())


class ValhallaTransport:
    def __init__(self) -> None:
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        sent = json.loads(request.body)
        origin = sent["locations"][0]
        features = []
        for index, contour in enumerate(sent["contours"]):
            lon = origin["lon"]
            lat = origin["lat"]
            offset = 0.01 + index * 0.005
            ring = [
                [lon - offset, lat - offset],
                [lon + offset, lat - offset],
                [lon + offset, lat + offset],
                [lon - offset, lat + offset],
                [lon - offset, lat - offset],
            ]
            features.append(
                {
                    "type": "Feature",
                    "properties": {"metric": "time", "contour": contour["time"]},
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                }
            )
        features.extend(
            [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"type": "MultiPoint", "coordinates": [[origin["lon"], origin["lat"]]]},
                },
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"type": "MultiPoint", "coordinates": [[origin["lon"] + 0.0001, origin["lat"] + 0.0001]]},
                },
            ]
        )
        body = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), sort_keys=True).encode()
        return ValhallaJSONResponse(200, body, "application/geo+json")


class ArtifactLoader:
    def __init__(self, store: MemoryArtifactStore, gtfs_bytes: bytes) -> None:
        self.store = store
        self.gtfs_bytes = gtfs_bytes
        self.area_calls = 0
        self.overture_calls = 0
        self.transit_calls = 0

    def load_pedestrian_network_bytes(self, *, resolved_location):
        return NETWORK_BYTES

    def load_pedestrian_area_km2(self, *, resolved_location, evidence):
        self.area_calls += 1
        return {item.scale_id: 1.0 + index for index, item in enumerate(evidence.contours)}

    def load_overture_partitions(self, *, resolved_location, sector, manifest):
        self.overture_calls += 1
        content_hash = sha256_bytes(OVERTURE_BYTES)
        ref = self.store.put(content_hash=content_hash, content=OVERTURE_BYTES)
        descriptor = OverturePartitionDescriptor("part_a", ref, content_hash)
        row = {
            "id": "p1",
            "theme": "places",
            "type": "place",
            "geometry": {"type": "Point", "coordinates": [resolved_location.longitude, resolved_location.latitude]},
            "basic_category": "cafe",
            "taxonomy": {"primary": "cafe", "hierarchy": ["food_and_drink", "cafe"], "alternates": []},
            "operating_status": "open",
            "confidence": 0.9,
            "sources": [{"dataset": "meta", "license": "CDLA-Permissive-2.0", "record_id": "p1"}],
        }
        return (
            OverturePartitionInput(
                descriptor=descriptor,
                records=(row,),
                parsed_artifact_ref=ArtifactRef("artifact://parsed/overture/part_a"),
                source_reference="s3://overture/2026-06-17.0/part_a.parquet",
            ),
        )

    def load_gtfs_zip_bytes(self, *, resolved_location, bundle):
        return self.gtfs_bytes

    def load_transit_reachability(self, *, resolved_location, bundle, walk_catchment_ref):
        self.transit_calls += 1
        return TransitReachabilityInput(("s1",), "provider_bound_walk_membership")


class BenchmarkLoader:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def load_distributions(self, *, sector, geography_ref):
        self.calls.append((sector, geography_ref))
        return self.values


def _persist_policy(policy_id: str, *, license_class: str = "provider-policy") -> ProviderPolicyDecision:
    persistence = PersistenceDecision(policy_id, "v1", PersistenceClass.PERSIST)
    return ProviderPolicyDecision(
        policy_id=policy_id,
        policy_version="v1",
        persistence=persistence,
        attribution_required=False,
        redistribution_state=RedistributionState.ALLOWED,
        commercial_use_state=CommercialUseState.ALLOWED,
        license_class=license_class,
    )


def _census_manifest():
    compatibility = CensusBenchmarkVintageCompatibility(
        "acs2024_pair", "v1", "Public_AR_ACS2024", "ACS2024_ACS2024"
    )
    return CensusGeographyManifest(
        "v1",
        compatibility,
        (
            CensusGeographyLayerSpec(GeographyType.STATE, 101, ("States",), True),
            CensusGeographyLayerSpec(GeographyType.COUNTY, 102, ("Counties",), True),
            CensusGeographyLayerSpec(GeographyType.TRACT, 103, ("Census Tracts",), True),
            CensusGeographyLayerSpec(GeographyType.BLOCK_GROUP, 104, ("Census Block Groups",), True),
        ),
    )


def _acs_manifest():
    variables = (
        ACSVariableSpec("total_population", ACSVariableRole.TOTAL_POPULATION, "B01003_001E", "B01003_001M", "B01003_001EA", "B01003_001MA", "people"),
        ACSVariableSpec("age_0_24_a", ACSVariableRole.AGE_COMPONENT, "B01001_003E", "B01001_003M", "B01001_003EA", "B01001_003MA", "people", "age"),
        ACSVariableSpec("age_0_24_b", ACSVariableRole.AGE_COMPONENT, "B01001_027E", "B01001_027M", "B01001_027EA", "B01001_027MA", "people", "age"),
        ACSVariableSpec("age_25_plus_a", ACSVariableRole.AGE_COMPONENT, "B01001_011E", "B01001_011M", "B01001_011EA", "B01001_011MA", "people", "age"),
        ACSVariableSpec("age_25_plus_b", ACSVariableRole.AGE_COMPONENT, "B01001_035E", "B01001_035M", "B01001_035EA", "B01001_035MA", "people", "age"),
        ACSVariableSpec("household_income", ACSVariableRole.HOUSEHOLD_INCOME, "B19013_001E", "B19013_001M", "B19013_001EA", "B19013_001MA", "usd_per_household"),
    )
    return ACSDatasetManifest(
        "v1",
        "2024",
        "2020-2024",
        ACSProduct.DETAILED_TABLES,
        "acs/acs5",
        ACSVariableManifest("site_demographics", "v1", variables),
        ACSGeographyCompatibility(
            "acs_2024_census2024",
            "v1",
            ("ACS2024_ACS2024",),
            (GeographyType.TRACT, GeographyType.BLOCK_GROUP),
        ),
        "v1",
    )


def _age_policy():
    return AgeCohortAggregationPolicy(
        "standard_age_v1",
        "v1",
        (
            ACSAgeCohortSpec("under_25", 0, 25, ("age_0_24_a", "age_0_24_b")),
            ACSAgeCohortSpec("age_25_plus", 25, None, ("age_25_plus_a", "age_25_plus_b")),
        ),
    )


def _pedestrian_config():
    network = PedestrianNetworkManifest(
        "v1",
        "openstreetmap",
        "osm_extract",
        "us_dc_metro",
        sha256_bytes(NETWORK_BYTES),
        "2026-08-10",
        "osm_pbf",
        "pbf_v1",
        "v1",
        "trusted_extract",
        "v1",
    )
    engine = PedestrianRoutingEngineManifest(
        "v1", "valhalla", "3.8.3", "mjolnir_tiles", "v1", "pedestrian", "valhalla_pedestrian_v1", (), "v1"
    )
    compatibility = PedestrianGraphCompatibility(
        "dc_walk_graph",
        "v1",
        network,
        engine,
        sha256_bytes(b"graph-content"),
        ArtifactRef("artifact://graph/dc_walk.tar"),
    )
    execution = ValhallaExecutionBinding(
        "dc_valhalla_deployment",
        "v1",
        compatibility,
        ValhallaIsochroneExecutionPolicy("valhalla_isochrone_limits", "v1", 4, 60.0),
    )
    budget = WalkingBudgetPolicy(
        "walking_budget",
        "v1",
        (WalkingBudgetScale("walk_300s", 300.0), WalkingBudgetScale("walk_600s", 600.0)),
    )
    geometry = PedestrianGeometryPolicy(
        "valhalla_geojson", "v1", "epsg_4326", "geojson", True, 1.0, None, "v1"
    )
    return PedestrianAcquisitionConfig(
        budget_policy=budget,
        graph_compatibility=compatibility,
        execution_binding=execution,
        geometry_policy=geometry,
        routing_persistence_policy=_persist_policy("route_policy"),
        network_persistence_policy=_persist_policy("osm_policy", license_class="ODbL-1.0"),
        area_policy=PedestrianAreaPolicy("walk_area", "v1", "precomputed_equal_area", "v1"),
        endpoint_url="http://valhalla.test/isochrone",
        analysis_scale_id="walk_600s",
    )


def _overture_config():
    manifest = OverturePlacesReleaseManifest(
        "v1", "2026-06-17.0", "v1.17.0", "opc", "2026.07", "overture_release_read", "v1", "v1"
    )
    resolution = TaxonomyResolutionPolicy("hierarchy_first_v1", "v1")
    mapping = OvertureCompetitionTaxonomyMapping(
        "sector_competition",
        "v1",
        manifest.identity,
        manifest.taxonomy_id,
        manifest.taxonomy_version,
        resolution,
        (
            OvertureTaxonomyRule(
                "food_cafe",
                TaxonomyMatchField.PRIMARY,
                "cafe",
                CommercialSemanticClass.FOOD_DRINK,
                CompetitionEligibilityState.INCLUDED,
            ),
        ),
    )
    return OvertureAcquisitionConfig(
        manifest,
        mapping,
        _persist_policy("overture_policy"),
        EntityDedupPolicy("exact_place_id", "v1"),
        PlaceLifecyclePolicy(
            "active_place_status",
            "v1",
            (OvertureOperatingStatus.OPEN,),
            (OvertureOperatingStatus.PERMANENTLY_CLOSED,),
        ),
    )


def _gtfs_bytes() -> bytes:
    files = {
        "agency.txt": "agency_name,agency_url,agency_timezone\nAgency,https://example.test,America/New_York\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\ns1,Stop 1,38.846,-76.927,0,\n",
        "routes.txt": "route_id,route_type\nr1,3\n",
        "trips.txt": "route_id,service_id,trip_id\nr1,svc,t1\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nt1,08:00:00,08:00:00,s1,1,0\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nsvc,1,1,1,1,1,1,1,20260101,20261231\n",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return buffer.getvalue()


def _transit_config(gtfs_bytes: bytes):
    manifest = GTFSFeedManifest(
        "v1",
        "dc_bus",
        "test_agency",
        "2026-08-01",
        "gtfs_static_v1",
        "v1",
        sha256_bytes(gtfs_bytes),
        "static_feed",
        "v1",
    )
    bundle = TransitSourceBundle(
        "dc_transit_bundle",
        "v1",
        manifest,
        GTFSServiceCalendarPolicy("calendar_policy", "v1"),
        GTFSStopHierarchyPolicy("hierarchy_policy", "v1"),
        TransitBoardingPolicy("boarding_policy", "v1"),
        GTFSFrequencyPolicy("frequency_policy", "v1"),
        (),
    )
    start = date(2026, 8, 17)
    profile = TransitWeeklyProfilePolicy(
        "typical_week",
        "v1",
        "median_same_weekday_hour",
        tuple(start + timedelta(days=index) for index in range(7)),
    )
    return TransitAcquisitionConfig(bundle, _persist_policy("gtfs_policy"), profile)


def _benchmark_distributions():
    engine = build_geometry_engine_identity()
    crs = build_crs_identity("EPSG:3857")
    canon = GeometryCanonicalizationPolicy()
    geography = GeographyIdentity("BENCHMARK_AREA", "provider-boundary-area", "boundary-def-2026")
    geometry = canonicalize_geometry(
        Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
        crs_identity=crs,
        policy=canon,
        engine=engine,
    )
    source = build_geometry_source_identity(
        provider="test-provider",
        dataset="benchmark-boundary",
        release="2026-08-17",
        vintage="2026",
        schema_version="1",
        source_crs_identity=crs,
        raw_content=b"provider-boundary-benchmark-frame",
    )
    boundary = build_boundary_geometry_artifact(
        geography_identity=geography,
        geometry_role="BENCHMARK_BOUNDARY",
        source_identity=source,
        canonical_geometry=geometry,
        parser_id="provider-boundary-parser",
        parser_version="1",
        canonicalization_policy=canon,
        engine=engine,
        source_refs=("source.provider-boundary",),
        generated_at=NOW,
        raw_artifact_ref="artifact.provider-boundary",
    )
    lattice = LatticePolicy(
        "provider-boundary-lattice",
        "1.0",
        EqualAreaProjectionPolicy("provider-boundary-equal-area", "1.0", "UNRESOLVED", ResolutionState.UNRESOLVED),
        CellResolutionPolicy("provider-boundary-cell-resolution", "1.0", ResolutionState.UNRESOLVED),
        CellShape.SQUARE,
        None,
        None,
        "AXIS_ALIGNED",
        "INTEGER_IJ",
        "1.0",
        canon,
        engine,
    )
    frame = CommercialFrame(
        geography,
        boundary,
        lattice,
        FrameBoundaryMembershipPolicy("provider-boundary-membership", "1.0", ResolutionState.UNRESOLVED),
        CommercialEligibilityPolicy(
            "provider-boundary-commercial-eligibility",
            "1.0",
            CommercialEvidencePolicy(
                "provider-boundary-commercial-evidence",
                "1.0",
                ("qualifying_place",),
                ("authoritative_noncommercial",),
            ),
        ),
        (),
        FrameState.UNRESOLVED,
        ("boundary_membership_policy_unresolved", "lattice_policy_unresolved"),
        NOW,
    )
    return {
        key: build_benchmark_distribution(build_benchmark_measurement_set(frame, (), metric_key=key))
        for key in (
            "walkable_population",
            "target_population_density",
            "competition_pressure",
            "walkable_reach_area_km2",
            "transit_service_departure_equivalents_per_hour",
            "household_income",
        )
    }


def _deployment():
    store = MemoryArtifactStore()
    http = ProviderHTTPTransport()
    valhalla = ValhallaTransport()
    gtfs_bytes = _gtfs_bytes()
    artifact_loader = ArtifactLoader(store, gtfs_bytes)
    benchmark_loader = BenchmarkLoader(_benchmark_distributions())
    deployment = CanonicalAcquisitionDeployment(
        http_transport=http,
        valhalla_transport=valhalla,
        artifact_store=store,
        artifact_loader=artifact_loader,
        benchmark_loader=benchmark_loader,
        census=CensusAcquisitionConfig(
            _census_manifest(),
            GeocodeAcceptancePolicy("census_acceptance", "v1"),
            _persist_policy("census_policy"),
        ),
        acs=ACSAcquisitionConfig(
            _acs_manifest(),
            _age_policy(),
            _persist_policy("acs_policy"),
            "ci-test-api-key",
        ),
        pedestrian=_pedestrian_config(),
        overture=_overture_config(),
        transit=_transit_config(gtfs_bytes),
        quality=ExecutionQualityConfig(
            2,
            {name: CoverageLevel.FULL for name in ("demand", "competition", "accessibility", "economics")},
            {name: InputQuality.USER for name in ("rent", "price", "capacity", "schedule")},
        ),
    )
    return deployment, http, valhalla, artifact_loader, benchmark_loader, store


def test_external_request_flows_through_frozen_provider_acquisition_to_not_score_ready(monkeypatch, valid_payloads):
    deployment, http, valhalla, artifacts, benchmarks, store = _deployment()
    source = CanonicalProviderEvidenceSource(deployment)
    calls = {"count": 0}

    def forbidden_core_analyze(_value):
        calls["count"] += 1
        raise AssertionError("core analyze must remain unreachable for canonical NOT_SCORE_READY")

    monkeypatch.setattr(execution_module, "analyze_application_core_input", forbidden_core_analyze)
    executor = CanonicalAnalysisExecutor(source)
    request = ADAPTER.validate_python(valid_payloads["coffee"])
    command = build_analysis_ingress_command(request, request_id=uuid4(), analysis_id=uuid4())

    result = executor.execute(command, now=NOW)

    assert result.completed is None
    assert result.not_score_ready is not None
    assert result.not_score_ready.readiness_projection["is_score_ready"] is False
    assert calls["count"] == 0

    census_address_request = next(item for item in http.requests if item.url.endswith("/locations/address"))
    census_query = dict(census_address_request.query)
    assert census_query["street"] == request.location.street
    assert census_query["zip"] == request.location.zip_code
    assert any(item.url.endswith("/geographies/coordinates") for item in http.requests)
    assert any("api.census.gov" in item.url for item in http.requests)
    assert len(valhalla.requests) == 1
    assert artifacts.area_calls == 1
    assert artifacts.overture_calls == 1
    assert artifacts.transit_calls == 1
    assert len(benchmarks.calls) == 1
    assert store.values

    evidence = source.acquire(command, now=NOW)
    assert evidence.resolved_location.formatted_address.startswith("4600 SILVER HILL RD")
    assert len(evidence.resolved_location.source_refs) == 2
    assert all(ref.startswith("source.") for ref in evidence.resolved_location.source_refs)
    assert evidence.demographics.geography_ref.geography_type is GeographyType.BLOCK_GROUP
    assert evidence.isochrone.source_refs
    assert evidence.transit.source_refs
