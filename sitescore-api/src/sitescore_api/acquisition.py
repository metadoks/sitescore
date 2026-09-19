from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
from sitescore.config.sectors import Sector
from sitescore_benchmarks import BenchmarkDistributionArtifact
from sitescore_data import DataQualityState, GeographyType
from sitescore_data.schemas.common import SourceMetadata
from sitescore_data.schemas.geography import GeographyRef, ResolvedLocation
from sitescore_providers import (
    ArtifactRef,
    ArtifactStore,
    ProviderPolicyDecision,
    build_source_metadata,
    sha256_bytes,
)
from sitescore_providers.acs import (
    ACSClient,
    ACSDatasetManifest,
    ACSUnsupportedGeography,
    AgeCohortAggregationPolicy,
    build_acs_query_plan,
    build_demographic_snapshot,
    build_evidence_bundle,
    parse_acs_statistical_evidence,
)
from sitescore_providers.census import (
    CensusAddressRequest,
    CensusGeocoderClient,
    CensusGeographyManifest,
    GeocodeAcceptancePolicy,
    build_resolved_location,
    parse_geocode_evidence,
    parse_geography_evidence,
)
from sitescore_providers.http import HTTPTransport
from sitescore_providers.overture.builders import build_competition_snapshot
from sitescore_providers.overture.models import (
    CompetitionCatchmentPolicy,
    CompetitionCatchmentScale,
    CoverageState,
    EntityDedupPolicy,
    OvertureCompetitionTaxonomyMapping,
    OverturePlacesReleaseManifest,
    PlaceLifecyclePolicy,
)
from sitescore_providers.overture.parser import parse_overture_partition
from sitescore_providers.overture.reader import (
    OverturePartitionDescriptor,
    build_partition_raw_artifact,
)
from sitescore_providers.pedestrian.builders import (
    build_network_source_evidence,
    build_pedestrian_frozen_result,
    build_routing_source_metadata,
)
from sitescore_providers.pedestrian.client import (
    PedestrianIsochroneClient,
    ValhallaJSONTransport,
)
from sitescore_providers.pedestrian.models import (
    PedestrianAreaEvidence,
    PedestrianAreaPolicy,
    PedestrianGeometryPolicy,
    PedestrianGraphCompatibility,
    PedestrianIsochroneEvidence,
    PedestrianIsochroneRequest,
    PedestrianRoutingOrigin,
    ValhallaExecutionBinding,
    WalkingBudgetPolicy,
)
from sitescore_providers.pedestrian.parser import parse_valhalla_isochrone_evidence
from sitescore_providers.transit import (
    ReachableTransitStopSet,
    TransitSourceBundle,
    TransitWeeklyProfilePolicy,
    acquire_gtfs_zip_bytes,
    build_transit_snapshot,
    parse_gtfs_zip,
)

from .execution import ExecutionEvidence
from .ingress import AnalysisIngressCommand


class CanonicalAcquisitionError(RuntimeError):
    """A provider/artifact boundary could not produce canonical execution evidence."""


@dataclass(frozen=True, slots=True)
class OverturePartitionInput:
    descriptor: OverturePartitionDescriptor
    records: tuple[Mapping[str, Any], ...]
    parsed_artifact_ref: ArtifactRef
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, OverturePartitionDescriptor):
            raise TypeError("descriptor must be an OverturePartitionDescriptor")
        if not isinstance(self.records, tuple):
            raise TypeError("records must be a tuple")
        if not isinstance(self.parsed_artifact_ref, ArtifactRef):
            raise TypeError("parsed_artifact_ref must be an ArtifactRef")


@dataclass(frozen=True, slots=True)
class TransitReachabilityInput:
    reachable_stop_ids: tuple[str, ...]
    access_geometry_quality: str

    def __post_init__(self) -> None:
        if self.reachable_stop_ids != tuple(sorted(set(self.reachable_stop_ids))):
            raise ValueError("reachable_stop_ids must be unique sorted")
        if not isinstance(self.access_geometry_quality, str) or not self.access_geometry_quality.strip():
            raise ValueError("access_geometry_quality must be non-empty")


@runtime_checkable
class DeploymentArtifactLoader(Protocol):
    """True external artifact/reader boundary; it never returns frozen snapshots/evidence."""

    def load_pedestrian_network_bytes(self, *, resolved_location: ResolvedLocation) -> bytes:
        ...

    def load_pedestrian_area_km2(
        self,
        *,
        resolved_location: ResolvedLocation,
        evidence: PedestrianIsochroneEvidence,
    ) -> Mapping[str, float]:
        ...

    def load_overture_partitions(
        self,
        *,
        resolved_location: ResolvedLocation,
        sector: Sector,
        manifest: OverturePlacesReleaseManifest,
    ) -> tuple[OverturePartitionInput, ...]:
        ...

    def load_gtfs_zip_bytes(
        self,
        *,
        resolved_location: ResolvedLocation,
        bundle: TransitSourceBundle,
    ) -> bytes:
        ...

    def load_transit_reachability(
        self,
        *,
        resolved_location: ResolvedLocation,
        bundle: TransitSourceBundle,
        walk_catchment_ref: str,
    ) -> TransitReachabilityInput:
        ...


@runtime_checkable
class BenchmarkArtifactLoader(Protocol):
    """Server-owned benchmark artifact authority; caller JSON never supplies artifacts."""

    def load_distributions(
        self,
        *,
        sector: Sector,
        geography_ref: GeographyRef,
    ) -> Mapping[str, BenchmarkDistributionArtifact]:
        ...


@dataclass(frozen=True, slots=True)
class CensusAcquisitionConfig:
    geography_manifest: CensusGeographyManifest
    acceptance_policy: GeocodeAcceptancePolicy
    persistence_policy: ProviderPolicyDecision
    geocode_source_reference: str | None = None
    geography_source_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.geography_manifest, CensusGeographyManifest):
            raise TypeError("geography_manifest must be CensusGeographyManifest")
        if not isinstance(self.acceptance_policy, GeocodeAcceptancePolicy):
            raise TypeError("acceptance_policy must be GeocodeAcceptancePolicy")
        if not isinstance(self.persistence_policy, ProviderPolicyDecision):
            raise TypeError("persistence_policy must be ProviderPolicyDecision")


@dataclass(frozen=True, slots=True)
class ACSAcquisitionConfig:
    manifest: ACSDatasetManifest
    age_policy: AgeCohortAggregationPolicy
    persistence_policy: ProviderPolicyDecision
    api_key: str
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, ACSDatasetManifest):
            raise TypeError("manifest must be ACSDatasetManifest")
        if not isinstance(self.age_policy, AgeCohortAggregationPolicy):
            raise TypeError("age_policy must be AgeCohortAggregationPolicy")
        if not isinstance(self.persistence_policy, ProviderPolicyDecision):
            raise TypeError("persistence_policy must be ProviderPolicyDecision")
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError("api_key must be configured")


@dataclass(frozen=True, slots=True)
class PedestrianAcquisitionConfig:
    budget_policy: WalkingBudgetPolicy
    graph_compatibility: PedestrianGraphCompatibility
    execution_binding: ValhallaExecutionBinding
    geometry_policy: PedestrianGeometryPolicy
    routing_persistence_policy: ProviderPolicyDecision
    network_persistence_policy: ProviderPolicyDecision
    area_policy: PedestrianAreaPolicy
    endpoint_url: str
    analysis_scale_id: str
    execution_headers: tuple[tuple[str, str], ...] = ()
    network_source_reference: str | None = None
    routing_source_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.budget_policy, WalkingBudgetPolicy):
            raise TypeError("budget_policy must be WalkingBudgetPolicy")
        if not isinstance(self.graph_compatibility, PedestrianGraphCompatibility):
            raise TypeError("graph_compatibility must be PedestrianGraphCompatibility")
        if not isinstance(self.execution_binding, ValhallaExecutionBinding):
            raise TypeError("execution_binding must be ValhallaExecutionBinding")
        if self.execution_binding.graph_compatibility.identity != self.graph_compatibility.identity:
            raise ValueError("execution_binding must bind graph_compatibility")
        if not isinstance(self.geometry_policy, PedestrianGeometryPolicy):
            raise TypeError("geometry_policy must be PedestrianGeometryPolicy")
        for value in (self.routing_persistence_policy, self.network_persistence_policy):
            if not isinstance(value, ProviderPolicyDecision):
                raise TypeError("pedestrian persistence policies must be ProviderPolicyDecision")
        if not isinstance(self.area_policy, PedestrianAreaPolicy):
            raise TypeError("area_policy must be PedestrianAreaPolicy")
        if not isinstance(self.endpoint_url, str) or not self.endpoint_url.strip():
            raise ValueError("endpoint_url must be configured")
        if not isinstance(self.analysis_scale_id, str) or not self.analysis_scale_id.strip():
            raise ValueError("analysis_scale_id must be configured")
        if self.analysis_scale_id not in {scale.scale_id for scale in self.budget_policy.scales}:
            raise ValueError("analysis_scale_id must reference a configured walking scale")


@dataclass(frozen=True, slots=True)
class OvertureAcquisitionConfig:
    manifest: OverturePlacesReleaseManifest
    taxonomy_mapping: OvertureCompetitionTaxonomyMapping
    persistence_policy: ProviderPolicyDecision
    dedup_policy: EntityDedupPolicy
    lifecycle_policy: PlaceLifecyclePolicy
    spatial_predicate_id: str = "covers"
    spatial_predicate_version: str = "v1"
    projection_area_policy_id: str = "pedestrian_area_evidence"
    projection_area_policy_version: str = "v1"

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, OverturePlacesReleaseManifest):
            raise TypeError("manifest must be OverturePlacesReleaseManifest")
        if not isinstance(self.taxonomy_mapping, OvertureCompetitionTaxonomyMapping):
            raise TypeError("taxonomy_mapping must be OvertureCompetitionTaxonomyMapping")
        if self.taxonomy_mapping.release_manifest_identity != self.manifest.identity:
            raise ValueError("taxonomy mapping must bind the configured Overture manifest")
        if not isinstance(self.persistence_policy, ProviderPolicyDecision):
            raise TypeError("persistence_policy must be ProviderPolicyDecision")
        if not isinstance(self.dedup_policy, EntityDedupPolicy):
            raise TypeError("dedup_policy must be EntityDedupPolicy")
        if not isinstance(self.lifecycle_policy, PlaceLifecyclePolicy):
            raise TypeError("lifecycle_policy must be PlaceLifecyclePolicy")


@dataclass(frozen=True, slots=True)
class TransitAcquisitionConfig:
    bundle: TransitSourceBundle
    persistence_policy: ProviderPolicyDecision
    profile_policy: TransitWeeklyProfilePolicy
    membership_method_id: str = "walk_catchment_stop_membership"
    membership_method_version: str = "v1"
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.bundle, TransitSourceBundle):
            raise TypeError("bundle must be TransitSourceBundle")
        if not isinstance(self.persistence_policy, ProviderPolicyDecision):
            raise TypeError("persistence_policy must be ProviderPolicyDecision")
        if not isinstance(self.profile_policy, TransitWeeklyProfilePolicy):
            raise TypeError("profile_policy must be TransitWeeklyProfilePolicy")
        for name in ("membership_method_id", "membership_method_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be configured")


@dataclass(frozen=True, slots=True)
class ExecutionQualityConfig:
    data_age_years: int
    data_coverage: Mapping[str, CoverageLevel]
    input_qualities: Mapping[str, InputQuality]

    def __post_init__(self) -> None:
        if not isinstance(self.data_age_years, int) or isinstance(self.data_age_years, bool) or self.data_age_years < 0:
            raise ValueError("data_age_years must be a nonnegative integer")
        if set(self.data_coverage) != {"demand", "competition", "accessibility", "economics"}:
            raise ValueError("data_coverage must contain the exact quality dimensions")
        if set(self.input_qualities) != {"rent", "price", "capacity", "schedule"}:
            raise ValueError("input_qualities must contain the exact quality dimensions")
        if any(not isinstance(v, CoverageLevel) for v in self.data_coverage.values()):
            raise TypeError("data_coverage values must be CoverageLevel")
        if any(not isinstance(v, InputQuality) for v in self.input_qualities.values()):
            raise TypeError("input_qualities values must be InputQuality")


@dataclass(frozen=True, slots=True)
class CanonicalAcquisitionDeployment:
    http_transport: HTTPTransport
    valhalla_transport: ValhallaJSONTransport
    artifact_store: ArtifactStore
    artifact_loader: DeploymentArtifactLoader
    benchmark_loader: BenchmarkArtifactLoader
    census: CensusAcquisitionConfig
    acs: ACSAcquisitionConfig
    pedestrian: PedestrianAcquisitionConfig
    overture: OvertureAcquisitionConfig
    transit: TransitAcquisitionConfig
    quality: ExecutionQualityConfig

    def __post_init__(self) -> None:
        if not isinstance(self.http_transport, HTTPTransport):
            raise TypeError("http_transport must implement HTTPTransport")
        if not isinstance(self.valhalla_transport, ValhallaJSONTransport):
            raise TypeError("valhalla_transport must implement ValhallaJSONTransport")
        if not isinstance(self.artifact_store, ArtifactStore):
            raise TypeError("artifact_store must implement ArtifactStore")
        if not isinstance(self.artifact_loader, DeploymentArtifactLoader):
            raise TypeError("artifact_loader must implement DeploymentArtifactLoader")
        if not isinstance(self.benchmark_loader, BenchmarkArtifactLoader):
            raise TypeError("benchmark_loader must implement BenchmarkArtifactLoader")
        expected_types = (
            (self.census, CensusAcquisitionConfig),
            (self.acs, ACSAcquisitionConfig),
            (self.pedestrian, PedestrianAcquisitionConfig),
            (self.overture, OvertureAcquisitionConfig),
            (self.transit, TransitAcquisitionConfig),
            (self.quality, ExecutionQualityConfig),
        )
        for value, expected in expected_types:
            if not isinstance(value, expected):
                raise TypeError(f"deployment member must be {expected.__name__}")


def _require_artifact(result: object, *, label: str):
    artifact = getattr(result, "artifact", None)
    if artifact is None:
        state = getattr(result, "state", None)
        raise CanonicalAcquisitionError(f"{label} acquisition did not produce a canonical artifact: {state}")
    return artifact


def _geographic_level(ref: GeographyRef) -> GeographicLevel:
    if ref.geography_type is GeographyType.BLOCK_GROUP:
        return GeographicLevel.BLOCK_GROUP
    if ref.geography_type is GeographyType.TRACT:
        return GeographicLevel.TRACT
    if ref.geography_type is GeographyType.ZCTA:
        return GeographicLevel.ZIP
    if ref.geography_type is GeographyType.COUNTY:
        return GeographicLevel.COUNTY
    return GeographicLevel.UNKNOWN


def _select_acs_geography(location: ResolvedLocation, manifest: ACSDatasetManifest) -> GeographyRef:
    for wanted in (GeographyType.BLOCK_GROUP, GeographyType.TRACT):
        for ref in location.geography_refs:
            if ref.geography_type is not wanted:
                continue
            planned = build_acs_query_plan(geography_ref=ref, manifest=manifest)
            if not isinstance(planned, ACSUnsupportedGeography):
                return ref
    raise CanonicalAcquisitionError("resolved Census geography is not compatible with the configured ACS manifest")


def _select_pedestrian_catchment(pedestrian_result, config: PedestrianAcquisitionConfig):
    aligned = tuple(zip(config.budget_policy.scales, pedestrian_result.catchments, strict=True))
    for scale, catchment in aligned:
        if scale.scale_id == config.analysis_scale_id:
            return catchment
    raise CanonicalAcquisitionError("analysis_scale_id is not aligned with the frozen pedestrian result")


class CanonicalProviderEvidenceSource:
    """Server-owned provider orchestration. No caller-supplied frozen evidence enters here."""

    def __init__(self, deployment: CanonicalAcquisitionDeployment) -> None:
        if not isinstance(deployment, CanonicalAcquisitionDeployment):
            raise TypeError("deployment must be CanonicalAcquisitionDeployment")
        self._deployment = deployment

    def acquire(self, command: AnalysisIngressCommand, *, now: datetime) -> ExecutionEvidence:
        if not isinstance(command, AnalysisIngressCommand):
            raise TypeError("command must be AnalysisIngressCommand")
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        location, census_sources = self._acquire_location(command, now=now)
        demographics, acs_sources, geography_ref = self._acquire_demographics(location, now=now)
        pedestrian_result, pedestrian_sources = self._acquire_pedestrian(location, now=now)
        selected_catchment = _select_pedestrian_catchment(
            pedestrian_result,
            self._deployment.pedestrian,
        )
        isochrone = next(
            snapshot
            for snapshot in pedestrian_result.snapshots
            if snapshot.catchment_ref == selected_catchment.catchment_id
        )
        competition, competition_sources = self._acquire_competition(
            command,
            location,
            pedestrian_result=pedestrian_result,
            now=now,
        )
        transit, transit_sources = self._acquire_transit(
            location,
            pedestrian_result=pedestrian_result,
            now=now,
        )
        benchmarks = dict(
            self._deployment.benchmark_loader.load_distributions(
                sector=command.sector,
                geography_ref=geography_ref,
            )
        )
        required_benchmarks = {
            "walkable_population",
            "target_population_density",
            "competition_pressure",
            "walkable_reach_area_km2",
            "transit_service_departure_equivalents_per_hour",
            "household_income",
        }
        if set(benchmarks) != required_benchmarks:
            raise CanonicalAcquisitionError("benchmark loader must return the exact V1 direct-feature artifact set")
        if any(not isinstance(value, BenchmarkDistributionArtifact) for value in benchmarks.values()):
            raise CanonicalAcquisitionError("benchmark loader returned a non-BenchmarkDistributionArtifact value")

        sources_by_id: dict[str, SourceMetadata] = {}
        for source in census_sources + acs_sources + pedestrian_sources + competition_sources + transit_sources:
            sources_by_id[source.source_id] = source

        return ExecutionEvidence(
            resolved_location=location,
            demographics=demographics,
            isochrone=isochrone,
            competition=competition,
            transit=transit,
            benchmark_distributions=benchmarks,
            source_metadata=tuple(sources_by_id[key] for key in sorted(sources_by_id)),
            geographic_level=_geographic_level(geography_ref),
            data_age_years=self._deployment.quality.data_age_years,
            data_coverage=dict(self._deployment.quality.data_coverage),
            input_qualities=dict(self._deployment.quality.input_qualities),
        )

    def _acquire_location(
        self,
        command: AnalysisIngressCommand,
        *,
        now: datetime,
    ) -> tuple[ResolvedLocation, tuple[SourceMetadata, ...]]:
        cfg = self._deployment.census
        address = command.address
        request = CensusAddressRequest(
            street=address.street,
            city=address.city,
            state=address.state,
            zip_code=address.zip_code,
            manifest=cfg.geography_manifest,
        )
        client = CensusGeocoderClient(
            transport=self._deployment.http_transport,
            artifact_store=self._deployment.artifact_store,
        )
        geocode_acquisition = client.acquire_geocode(
            request=request,
            persistence_policy=cfg.persistence_policy,
            retrieved_at=now,
        )
        geocode_raw = _require_artifact(geocode_acquisition, label="Census geocode")
        parsed_geocode = client.parse_geocode_success(acquisition=geocode_acquisition)
        geocode = parse_geocode_evidence(
            parsed_value=parsed_geocode.parsed_value,
            parsed_artifact=parsed_geocode.parsed_artifact,
            request_fingerprint=geocode_raw.request_fingerprint,
            manifest=cfg.geography_manifest,
        )
        decision = cfg.acceptance_policy.evaluate(geocode)
        if not decision.accepted or len(geocode.candidates) != 1:
            raise CanonicalAcquisitionError("Census geocode evidence was not accepted by the server-owned policy")
        candidate = geocode.candidates[0]

        geography_acquisition = client.acquire_geography(
            coordinates=candidate.coordinates,
            manifest=cfg.geography_manifest,
            persistence_policy=cfg.persistence_policy,
            retrieved_at=now,
        )
        geography_raw = _require_artifact(geography_acquisition, label="Census geography")
        parsed_geography = client.parse_geography_success(acquisition=geography_acquisition)
        geography = parse_geography_evidence(
            parsed_value=parsed_geography.parsed_value,
            parsed_artifact=parsed_geography.parsed_artifact,
            request_fingerprint=geography_raw.request_fingerprint,
            coordinates=candidate.coordinates,
            manifest=cfg.geography_manifest,
        )
        geocode_source = build_source_metadata(
            raw_artifact=geocode_raw,
            data_quality=DataQualityState.FULL,
            policy=cfg.persistence_policy,
            source_reference=cfg.geocode_source_reference,
        )
        geography_source = build_source_metadata(
            raw_artifact=geography_raw,
            data_quality=DataQualityState.FULL,
            policy=cfg.persistence_policy,
            source_reference=cfg.geography_source_reference,
        )
        resolved = build_resolved_location(
            geocode_evidence=geocode,
            geography_evidence=geography,
            manifest=cfg.geography_manifest,
            acceptance_policy=cfg.acceptance_policy,
            geocode_source=geocode_source,
            geography_source=geography_source,
            generated_at=now,
        )
        return resolved, (geocode_source, geography_source)

    def _acquire_demographics(
        self,
        location: ResolvedLocation,
        *,
        now: datetime,
    ):
        cfg = self._deployment.acs
        geography_ref = _select_acs_geography(location, cfg.manifest)
        plan = build_acs_query_plan(geography_ref=geography_ref, manifest=cfg.manifest)
        if isinstance(plan, ACSUnsupportedGeography):
            raise CanonicalAcquisitionError("configured ACS manifest does not support resolved geography")
        client = ACSClient(
            transport=self._deployment.http_transport,
            artifact_store=self._deployment.artifact_store,
            api_key=cfg.api_key,
        )
        evidence = []
        sources = []
        for request in plan.requests:
            acquired = client.acquire(
                request=request,
                manifest=cfg.manifest,
                persistence_policy=cfg.persistence_policy,
                retrieved_at=now,
            )
            raw = _require_artifact(acquired, label="ACS")
            parsed = client.parse_success(acquisition=acquired, manifest=cfg.manifest)
            parsed_evidence = parse_acs_statistical_evidence(
                response=parsed,
                request=request,
                manifest=cfg.manifest,
            )
            evidence.extend(parsed_evidence.evidence)
            sources.append(
                build_source_metadata(
                    raw_artifact=raw,
                    data_quality=DataQualityState.FULL,
                    policy=cfg.persistence_policy,
                    source_reference=cfg.source_reference,
                )
            )
        bundle = build_evidence_bundle(
            geography_ref=geography_ref,
            manifest=cfg.manifest,
            evidence=tuple(evidence),
        )
        snapshot, _ = build_demographic_snapshot(
            bundle=bundle,
            manifest=cfg.manifest,
            age_policy=cfg.age_policy,
            source_metadata=tuple(sources),
            generated_at=now,
        )
        return snapshot, tuple(sources), geography_ref

    def _acquire_pedestrian(self, location: ResolvedLocation, *, now: datetime):
        cfg = self._deployment.pedestrian
        request = PedestrianIsochroneRequest(
            origin=PedestrianRoutingOrigin.from_resolved_location(location),
            budget_policy=cfg.budget_policy,
            graph_compatibility=cfg.graph_compatibility,
            execution_binding=cfg.execution_binding,
            geometry_policy=cfg.geometry_policy,
        )
        client = PedestrianIsochroneClient(
            transport=self._deployment.valhalla_transport,
            artifact_store=self._deployment.artifact_store,
            endpoint_url=cfg.endpoint_url,
            execution_binding=cfg.execution_binding,
            execution_headers=cfg.execution_headers,
        )
        acquired = client.acquire(
            request=request,
            persistence_policy=cfg.routing_persistence_policy,
            retrieved_at=now,
        )
        _require_artifact(acquired, label="Valhalla isochrone")
        parsed = client.parse_success(acquisition=acquired, request=request)
        evidence = parse_valhalla_isochrone_evidence(response=parsed, request=request)

        network_bytes = self._deployment.artifact_loader.load_pedestrian_network_bytes(
            resolved_location=location
        )
        if not isinstance(network_bytes, bytes):
            raise CanonicalAcquisitionError("pedestrian network artifact loader must return bytes")
        manifest = cfg.graph_compatibility.network_manifest
        if sha256_bytes(network_bytes) != manifest.network_content_hash:
            raise CanonicalAcquisitionError("pedestrian network bytes do not match pinned network manifest")
        network_ref = self._deployment.artifact_store.put(
            content_hash=manifest.network_content_hash,
            content=network_bytes,
        )
        network_source = build_network_source_evidence(
            manifest=manifest,
            artifact_ref=network_ref,
            retrieved_at=now,
            policy=cfg.network_persistence_policy,
            source_reference=cfg.network_source_reference,
        )
        routing_source = build_routing_source_metadata(
            evidence=evidence,
            policy=cfg.routing_persistence_policy,
            source_reference=cfg.routing_source_reference,
        )
        raw_areas = dict(
            self._deployment.artifact_loader.load_pedestrian_area_km2(
                resolved_location=location,
                evidence=evidence,
            )
        )
        expected_scales = {contour.scale_id for contour in evidence.contours}
        if set(raw_areas) != expected_scales:
            raise CanonicalAcquisitionError("pedestrian area artifact loader must cover every requested scale")
        area_evidence = tuple(
            PedestrianAreaEvidence(
                contour.scale_id,
                contour.geometry.identity,
                float(raw_areas[contour.scale_id]),
                cfg.area_policy,
            )
            for contour in evidence.contours
        )
        frozen = build_pedestrian_frozen_result(
            evidence=evidence,
            area_evidence=area_evidence,
            network_source=network_source,
            routing_source_metadata=routing_source,
            generated_at=now,
        )
        return frozen, (network_source.source_metadata, routing_source)

    def _acquire_competition(
        self,
        command: AnalysisIngressCommand,
        location: ResolvedLocation,
        *,
        pedestrian_result,
        now: datetime,
    ):
        cfg = self._deployment.overture
        loaded = self._deployment.artifact_loader.load_overture_partitions(
            resolved_location=location,
            sector=command.sector,
            manifest=cfg.manifest,
        )
        if not isinstance(loaded, tuple):
            raise CanonicalAcquisitionError("Overture artifact loader must return a tuple")
        partitions = []
        for item in loaded:
            if not isinstance(item, OverturePartitionInput):
                raise CanonicalAcquisitionError("Overture loader returned invalid partition input")
            if not self._deployment.artifact_store.exists(item.descriptor.artifact_ref):
                raise CanonicalAcquisitionError("pinned Overture partition artifact is absent from the artifact store")
            raw_bytes = self._deployment.artifact_store.get(item.descriptor.artifact_ref)
            if sha256_bytes(raw_bytes) != item.descriptor.content_hash:
                raise CanonicalAcquisitionError("Overture partition bytes do not match descriptor content hash")
            raw = build_partition_raw_artifact(
                manifest=cfg.manifest,
                descriptor=item.descriptor,
                retrieved_at=now,
                persistence=cfg.persistence_policy.persistence,
            )
            partitions.append(
                parse_overture_partition(
                    raw_artifact=raw,
                    records=item.records,
                    manifest=cfg.manifest,
                    policy=cfg.persistence_policy,
                    parsed_artifact_ref=item.parsed_artifact_ref,
                    source_reference=item.source_reference,
                    partition_id=item.descriptor.partition_id,
                )
            )

        snapshot_by_catchment = {s.catchment_ref: s for s in pedestrian_result.snapshots}
        scales = []
        for budget_scale, catchment in zip(
            self._deployment.pedestrian.budget_policy.scales,
            pedestrian_result.catchments,
            strict=True,
        ):
            snapshot = snapshot_by_catchment[catchment.catchment_id]
            if snapshot.area_km2.value is None:
                raise CanonicalAcquisitionError("pedestrian catchment area unavailable for competition frame")
            scales.append(
                CompetitionCatchmentScale(
                    scale_id=budget_scale.scale_id,
                    travel_mode="walking_network",
                    catchment_semantics="precomputed_network_membership",
                    travel_cost=float(budget_scale.travel_cost_seconds) / 60.0,
                    travel_cost_unit="minutes",
                    area_km2=float(snapshot.area_km2.value),
                    member_place_ids=(),
                    catchment_artifact_ref=catchment.geometry_ref,
                )
            )
        catchment_policy = CompetitionCatchmentPolicy(
            policy_id="api_canonical_pedestrian_catchment",
            policy_version="v1",
            spatial_predicate_id=cfg.spatial_predicate_id,
            spatial_predicate_version=cfg.spatial_predicate_version,
            projection_area_policy_id=cfg.projection_area_policy_id,
            projection_area_policy_version=cfg.projection_area_policy_version,
            scales=tuple(scales),
        )
        snapshot, _ = build_competition_snapshot(
            manifest=cfg.manifest,
            mapping=cfg.taxonomy_mapping,
            dedup_policy=cfg.dedup_policy,
            catchment_policy=catchment_policy,
            lifecycle_policy=cfg.lifecycle_policy,
            partitions=tuple(partitions),
            coverage_state=CoverageState.UNKNOWN,
            generated_at=now,
        )
        return snapshot, tuple(part.source_metadata for part in partitions)

    def _acquire_transit(self, location: ResolvedLocation, *, pedestrian_result, now: datetime):
        cfg = self._deployment.transit
        content = self._deployment.artifact_loader.load_gtfs_zip_bytes(
            resolved_location=location,
            bundle=cfg.bundle,
        )
        if not isinstance(content, bytes):
            raise CanonicalAcquisitionError("GTFS artifact loader must return bytes")
        raw = acquire_gtfs_zip_bytes(
            content=content,
            manifest=cfg.bundle.feed_manifest,
            artifact_store=self._deployment.artifact_store,
            retrieved_at=now,
            persistence=cfg.persistence_policy.persistence,
        )
        feed = parse_gtfs_zip(
            raw_artifact=raw,
            bundle=cfg.bundle,
            artifact_store=self._deployment.artifact_store,
            policy=cfg.persistence_policy,
            source_reference=cfg.source_reference,
        )
        selected_catchment = _select_pedestrian_catchment(
            pedestrian_result,
            self._deployment.pedestrian,
        )
        reachability_input = self._deployment.artifact_loader.load_transit_reachability(
            resolved_location=location,
            bundle=cfg.bundle,
            walk_catchment_ref=selected_catchment.catchment_id,
        )
        if not isinstance(reachability_input, TransitReachabilityInput):
            raise CanonicalAcquisitionError("transit reachability loader returned invalid input")
        reachability = ReachableTransitStopSet(
            source_bundle_fingerprint=cfg.bundle.fingerprint,
            pedestrian_derivation_identity=str(pedestrian_result.derivation.identity),
            walking_budget_policy_identity=str(self._deployment.pedestrian.budget_policy.identity),
            membership_method_id=cfg.membership_method_id,
            membership_method_version=cfg.membership_method_version,
            reachable_stop_ids=reachability_input.reachable_stop_ids,
            walk_catchment_ref=selected_catchment.catchment_id,
            access_geometry_quality=reachability_input.access_geometry_quality,
            source_refs=tuple(sorted({
                pedestrian_result.derivation.network_source_ref,
                pedestrian_result.derivation.routing_source_ref,
            })),
        )
        snapshot = build_transit_snapshot(
            feed=feed,
            reachability=reachability,
            profile_policy=cfg.profile_policy,
            generated_at=now,
        )
        return snapshot, (feed.source_metadata,)
