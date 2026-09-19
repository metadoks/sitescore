"""Immutable motor-vehicle network accessibility contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sitescore_data.enums import AvailabilityState, DataQualityState
from sitescore_data.schemas.benchmarks import BenchmarkReference
from sitescore_data.validation import (
    require_aware_datetime,
    require_bounded_number,
    require_canonical_identifier,
    require_nonnegative_number,
    require_positive_number,
)


class RoadOriginQuality(StrEnum):
    VEHICLE_ENTRANCE = "vehicle_entrance"
    DRIVEWAY = "driveway"
    ROAD_SEGMENT_FALLBACK = "road_segment_fallback"
    UNRESOLVED = "unresolved"


def _require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    return value


def _require_unique_source_refs(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError("source_refs must be a tuple")
    for value in values:
        require_canonical_identifier(value, field_name="source_refs item")
    if len(set(values)) != len(values):
        raise ValueError("source_refs must not contain duplicates")
    return values


def _require_snapshot_quality(
    availability: AvailabilityState,
    data_quality: DataQualityState,
) -> None:
    allowed = {
        AvailabilityState.AVAILABLE: {DataQualityState.FULL, DataQualityState.DEGRADED},
        AvailabilityState.MISSING: {DataQualityState.MISSING},
        AvailabilityState.UNAVAILABLE: {DataQualityState.MISSING},
        AvailabilityState.UNKNOWN: {DataQualityState.DEGRADED, DataQualityState.MISSING},
        AvailabilityState.NOT_APPLICABLE: {DataQualityState.NOT_APPLICABLE},
    }
    if not isinstance(availability, AvailabilityState):
        raise TypeError("availability must be an AvailabilityState")
    if not isinstance(data_quality, DataQualityState):
        raise TypeError("data_quality must be a DataQualityState")
    if data_quality not in allowed[availability]:
        raise ValueError("RoadAccessSnapshot availability/data_quality are inconsistent")


@dataclass(frozen=True, slots=True)
class RoadObservation:
    """One motor-vehicle network reachability observation at one travel-cost scale."""

    travel_cost_seconds: float
    reachable_area_km2: float
    reachable_network_length_km: float
    reachable_connector_count: int
    origin_to_network_cost_seconds: float
    benchmark_percentile: float | None
    source_refs: tuple[str, ...]
    method_version: str

    def __post_init__(self) -> None:
        require_positive_number(
            self.travel_cost_seconds,
            field_name="travel_cost_seconds",
        )
        require_nonnegative_number(
            self.reachable_area_km2,
            field_name="reachable_area_km2",
        )
        require_nonnegative_number(
            self.reachable_network_length_km,
            field_name="reachable_network_length_km",
        )
        require_nonnegative_number(
            self.reachable_connector_count,
            field_name="reachable_connector_count",
        )
        if not isinstance(self.reachable_connector_count, int) or isinstance(
            self.reachable_connector_count, bool
        ):
            raise TypeError("reachable_connector_count must be an int")
        require_nonnegative_number(
            self.origin_to_network_cost_seconds,
            field_name="origin_to_network_cost_seconds",
        )
        if self.benchmark_percentile is not None:
            require_bounded_number(
                self.benchmark_percentile,
                low=0.0,
                high=1.0,
                field_name="benchmark_percentile",
            )
        _require_unique_source_refs(self.source_refs)
        if not self.source_refs:
            raise ValueError("RoadObservation requires at least one source_ref")
        _require_nonempty_text(self.method_version, field_name="method_version")


@dataclass(frozen=True, slots=True)
class RoadAccessSnapshot:
    """Multi-scale road-network accessibility evidence."""

    snapshot_id: str
    road_origin_ref: str
    road_origin_quality: RoadOriginQuality
    routing_profile_id: str
    routing_profile_version: str
    observations: tuple[RoadObservation, ...]
    benchmark_ref: BenchmarkReference | None
    source_refs: tuple[str, ...]
    availability: AvailabilityState
    data_quality: DataQualityState
    generated_at: datetime

    def __post_init__(self) -> None:
        require_canonical_identifier(self.snapshot_id, field_name="snapshot_id")
        require_canonical_identifier(
            self.road_origin_ref, field_name="road_origin_ref"
        )
        if not isinstance(self.road_origin_quality, RoadOriginQuality):
            raise TypeError("road_origin_quality must be a RoadOriginQuality")
        require_canonical_identifier(
            self.routing_profile_id, field_name="routing_profile_id"
        )
        _require_nonempty_text(
            self.routing_profile_version, field_name="routing_profile_version"
        )
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be a tuple")
        for observation in self.observations:
            if not isinstance(observation, RoadObservation):
                raise TypeError("observations must contain RoadObservation values")
        scales = tuple(item.travel_cost_seconds for item in self.observations)
        if len(set(scales)) != len(scales):
            raise ValueError("road travel-cost scales must be unique")
        if scales != tuple(sorted(scales)):
            raise ValueError("road observations must be ordered by travel_cost_seconds")
        if self.benchmark_ref is not None and not isinstance(
            self.benchmark_ref, BenchmarkReference
        ):
            raise TypeError("benchmark_ref must be a BenchmarkReference or None")
        _require_unique_source_refs(self.source_refs)
        _require_snapshot_quality(self.availability, self.data_quality)
        if self.availability is AvailabilityState.AVAILABLE:
            if self.road_origin_quality is RoadOriginQuality.UNRESOLVED:
                raise ValueError(
                    "AVAILABLE RoadAccessSnapshot requires a resolved road origin"
                )
            if not self.observations:
                raise ValueError("AVAILABLE RoadAccessSnapshot requires observations")
            if not self.source_refs:
                raise ValueError("AVAILABLE RoadAccessSnapshot requires source_refs")
        elif self.observations:
            raise ValueError(
                "non-AVAILABLE RoadAccessSnapshot must not contain observations"
            )
        nested_refs: set[str] = set()
        for observation in self.observations:
            nested_refs.update(observation.source_refs)
        if self.benchmark_ref is not None:
            nested_refs.update(self.benchmark_ref.source_refs)
        if nested_refs - set(self.source_refs):
            raise ValueError("source_refs must include all road/benchmark source refs")
        require_aware_datetime(self.generated_at, field_name="generated_at")
