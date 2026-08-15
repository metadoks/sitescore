"""Immutable pedestrian catchment and isochrone contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data.enums import AvailabilityState, DataQualityState
from sitescore_data.schemas.common import MetricValue
from sitescore_data.validation import (
    require_aware_datetime,
    require_canonical_identifier,
    require_latitude,
    require_longitude,
    require_positive_number,
)


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


@dataclass(frozen=True, slots=True)
class PedestrianCatchmentArtifact:
    """Provider-neutral walking-network catchment policy artifact."""

    catchment_id: str
    origin_location_ref: str
    origin_latitude: float
    origin_longitude: float
    travel_mode: str
    travel_cost_budget_seconds: float
    geometry_ref: str
    source_refs: tuple[str, ...]
    policy_version: str
    generated_at: datetime

    def __post_init__(self) -> None:
        require_canonical_identifier(self.catchment_id, field_name="catchment_id")
        require_canonical_identifier(
            self.origin_location_ref,
            field_name="origin_location_ref",
        )
        require_latitude(self.origin_latitude, field_name="origin_latitude")
        require_longitude(self.origin_longitude, field_name="origin_longitude")
        if self.travel_mode != "walk":
            raise ValueError('travel_mode must be canonical value "walk"')
        require_positive_number(
            self.travel_cost_budget_seconds,
            field_name="travel_cost_budget_seconds",
        )
        _require_nonempty_text(self.geometry_ref, field_name="geometry_ref")
        _require_unique_source_refs(self.source_refs)
        if not self.source_refs:
            raise ValueError(
                "PedestrianCatchmentArtifact requires at least one source_ref"
            )
        _require_nonempty_text(self.policy_version, field_name="policy_version")
        require_aware_datetime(self.generated_at, field_name="generated_at")


@dataclass(frozen=True, slots=True)
class IsochroneSnapshot:
    """Measured isochrone output tied to a pedestrian catchment artifact."""

    snapshot_id: str
    catchment_ref: str
    area_km2: MetricValue
    source_refs: tuple[str, ...]
    availability: AvailabilityState
    data_quality: DataQualityState
    method_version: str
    generated_at: datetime

    def __post_init__(self) -> None:
        require_canonical_identifier(self.snapshot_id, field_name="snapshot_id")
        require_canonical_identifier(self.catchment_ref, field_name="catchment_ref")
        if not isinstance(self.area_km2, MetricValue):
            raise TypeError("area_km2 must be a MetricValue")
        if self.area_km2.unit != "km2":
            raise ValueError('area_km2 MetricValue.unit must be "km2"')
        if self.area_km2.value is not None:
            if self.area_km2.value < 0:
                raise ValueError("area_km2 must be nonnegative")

        _require_unique_source_refs(self.source_refs)
        if not isinstance(self.availability, AvailabilityState):
            raise TypeError("availability must be an AvailabilityState")
        if not isinstance(self.data_quality, DataQualityState):
            raise TypeError("data_quality must be a DataQualityState")

        if self.availability is not self.area_km2.availability:
            raise ValueError(
                "IsochroneSnapshot availability must match area_km2 availability"
            )

        if self.availability is AvailabilityState.AVAILABLE:
            if self.data_quality not in {
                DataQualityState.FULL,
                DataQualityState.DEGRADED,
            }:
                raise ValueError(
                    "AVAILABLE isochrone snapshots require FULL or DEGRADED data quality"
                )
            if not self.source_refs:
                raise ValueError("AVAILABLE isochrone snapshots require source_refs")
            if self.area_km2.availability is not AvailabilityState.AVAILABLE:
                raise ValueError(
                    "AVAILABLE isochrone snapshots require AVAILABLE area_km2"
                )
        elif self.availability is AvailabilityState.NOT_APPLICABLE:
            if self.data_quality is not DataQualityState.NOT_APPLICABLE:
                raise ValueError(
                    "NOT_APPLICABLE isochrone snapshots require NOT_APPLICABLE data quality"
                )
        elif self.availability in {
            AvailabilityState.MISSING,
            AvailabilityState.UNAVAILABLE,
        }:
            if self.data_quality is not DataQualityState.MISSING:
                raise ValueError(
                    "MISSING/UNAVAILABLE isochrone snapshots require MISSING data quality"
                )
        elif self.availability is AvailabilityState.UNKNOWN:
            if self.data_quality not in {
                DataQualityState.DEGRADED,
                DataQualityState.MISSING,
            }:
                raise ValueError(
                    "UNKNOWN isochrone snapshots require DEGRADED or MISSING data quality"
                )

        missing_refs = set(self.area_km2.source_refs) - set(self.source_refs)
        if missing_refs:
            raise ValueError(
                "source_refs must include all area_km2 MetricValue source refs"
            )
        _require_nonempty_text(self.method_version, field_name="method_version")
        require_aware_datetime(self.generated_at, field_name="generated_at")
