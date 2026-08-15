"""Immutable static parking-supply and dynamic parking-availability contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sitescore_data.enums import (
    AvailabilityState,
    DataQualityState,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.validation import (
    require_aware_datetime,
    require_canonical_identifier,
)


class ParkingMode(StrEnum):
    OFF_STREET = "off_street"
    ON_STREET = "on_street"


class ParkingAccessClass(StrEnum):
    PUBLIC = "public"
    PERMISSIVE = "permissive"
    PRIVATE = "private"
    CUSTOMERS = "customers"
    UNKNOWN = "unknown"


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
        raise ValueError("ParkingSnapshot availability/data_quality are inconsistent")


@dataclass(frozen=True, slots=True)
class ParkingObservation:
    """One parking-supply observation with optional dynamic availability evidence."""

    parking_id: str
    parking_mode: ParkingMode
    access_class: ParkingAccessClass
    generic_public_supply_eligible: bool
    capacity: MetricValue
    motor_vehicle_reachable: bool
    walk_time_to_site_seconds: MetricValue
    curb_length_m: MetricValue
    occupancy: MetricValue
    available_spaces: MetricValue
    availability_timestamp: datetime | None
    source_ref: str

    def __post_init__(self) -> None:
        require_canonical_identifier(self.parking_id, field_name="parking_id")
        if not isinstance(self.parking_mode, ParkingMode):
            raise TypeError("parking_mode must be a ParkingMode")
        if not isinstance(self.access_class, ParkingAccessClass):
            raise TypeError("access_class must be a ParkingAccessClass")
        if not isinstance(self.generic_public_supply_eligible, bool):
            raise TypeError("generic_public_supply_eligible must be a bool")
        expected_generic = self.access_class in {
            ParkingAccessClass.PUBLIC,
            ParkingAccessClass.PERMISSIVE,
        }
        if self.generic_public_supply_eligible is not expected_generic:
            raise ValueError(
                "generic_public_supply_eligible must be true only for "
                "PUBLIC/PERMISSIVE parking"
            )
        for field_name in (
            "capacity",
            "walk_time_to_site_seconds",
            "curb_length_m",
            "occupancy",
            "available_spaces",
        ):
            if not isinstance(getattr(self, field_name), MetricValue):
                raise TypeError(f"{field_name} must be a MetricValue")
        if self.capacity.unit != "spaces":
            raise ValueError('capacity must use unit "spaces"')
        if self.capacity.value is not None and self.capacity.value < 0:
            raise ValueError("capacity must be nonnegative")
        if self.walk_time_to_site_seconds.unit != "seconds":
            raise ValueError('walk_time_to_site_seconds must use unit "seconds"')
        if (
            self.walk_time_to_site_seconds.value is not None
            and self.walk_time_to_site_seconds.value < 0
        ):
            raise ValueError("walk_time_to_site_seconds must be nonnegative")
        if self.curb_length_m.unit != "m":
            raise ValueError('curb_length_m must use unit "m"')
        if self.curb_length_m.value is not None and self.curb_length_m.value < 0:
            raise ValueError("curb_length_m must be nonnegative")
        if self.occupancy.unit != "ratio":
            raise ValueError('occupancy must use unit "ratio"')
        if self.occupancy.value is not None and not (0 <= self.occupancy.value <= 1):
            raise ValueError("occupancy must be between 0 and 1")
        if self.available_spaces.unit != "spaces":
            raise ValueError('available_spaces must use unit "spaces"')
        if self.available_spaces.value is not None and self.available_spaces.value < 0:
            raise ValueError("available_spaces must be nonnegative")
        if not isinstance(self.motor_vehicle_reachable, bool):
            raise TypeError("motor_vehicle_reachable must be a bool")

        dynamic_available = any(
            metric.availability is AvailabilityState.AVAILABLE
            for metric in (self.occupancy, self.available_spaces)
        )
        if dynamic_available:
            if self.availability_timestamp is None:
                raise ValueError(
                    "dynamic parking measurements require availability_timestamp"
                )
            require_aware_datetime(
                self.availability_timestamp,
                field_name="availability_timestamp",
            )
        elif self.availability_timestamp is not None:
            raise ValueError(
                "availability_timestamp must be None when no dynamic measurement is available"
            )

        if (
            self.capacity.availability is AvailabilityState.AVAILABLE
            and self.available_spaces.availability is AvailabilityState.AVAILABLE
        ):
            capacity = self.capacity.value
            available = self.available_spaces.value
            assert capacity is not None
            assert available is not None
            if available > capacity:
                raise ValueError(
                    "available_spaces cannot exceed observed capacity"
                )

        require_canonical_identifier(self.source_ref, field_name="source_ref")

        # ``source_ref`` identifies the primary parking evidence record. Nested
        # metrics may legitimately come from additional sources (for example a
        # routing source for walk time), so their provenance is preserved rather
        # than forced to equal the parking record source.


@dataclass(frozen=True, slots=True)
class ParkingSnapshot:
    """Parking evidence bundle with dimensionally separate static/dynamic summaries."""

    snapshot_id: str
    observations: tuple[ParkingObservation, ...]
    mapped_public_facility_count: MetricValue
    known_public_offstreet_capacity: MetricValue
    unknown_capacity_facility_count: MetricValue
    mapped_legal_curb_length_m: MetricValue
    known_onstreet_capacity: MetricValue
    dynamic_availability_present: bool
    source_refs: tuple[str, ...]
    availability: AvailabilityState
    data_quality: DataQualityState
    score_eligibility: ScoreEligibility
    generated_at: datetime

    def __post_init__(self) -> None:
        require_canonical_identifier(self.snapshot_id, field_name="snapshot_id")
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be a tuple")
        for observation in self.observations:
            if not isinstance(observation, ParkingObservation):
                raise TypeError("observations must contain ParkingObservation values")
        ids = tuple(item.parking_id for item in self.observations)
        if len(set(ids)) != len(ids):
            raise ValueError("parking_id values must be unique")
        if ids != tuple(sorted(ids)):
            raise ValueError("parking observations must be deterministically ordered by parking_id")
        summaries = (
            ("mapped_public_facility_count", self.mapped_public_facility_count, "count"),
            ("known_public_offstreet_capacity", self.known_public_offstreet_capacity, "spaces"),
            ("unknown_capacity_facility_count", self.unknown_capacity_facility_count, "count"),
            ("mapped_legal_curb_length_m", self.mapped_legal_curb_length_m, "m"),
            ("known_onstreet_capacity", self.known_onstreet_capacity, "spaces"),
        )
        for field_name, metric, unit in summaries:
            if not isinstance(metric, MetricValue):
                raise TypeError(f"{field_name} must be a MetricValue")
            if metric.unit != unit:
                raise ValueError(f'{field_name} must use unit "{unit}"')
            if metric.value is not None and metric.value < 0:
                raise ValueError(f"{field_name} must be nonnegative")
        if not isinstance(self.dynamic_availability_present, bool):
            raise TypeError("dynamic_availability_present must be a bool")
        _require_unique_source_refs(self.source_refs)
        _require_snapshot_quality(self.availability, self.data_quality)
        if not isinstance(self.score_eligibility, ScoreEligibility):
            raise TypeError("score_eligibility must be a ScoreEligibility")
        if (
            self.availability is not AvailabilityState.AVAILABLE
            and self.score_eligibility is ScoreEligibility.ELIGIBLE
        ):
            raise ValueError("non-AVAILABLE ParkingSnapshot cannot be score-eligible")
        if self.availability is AvailabilityState.NOT_APPLICABLE:
            if self.score_eligibility is not ScoreEligibility.NOT_APPLICABLE:
                raise ValueError(
                    "NOT_APPLICABLE ParkingSnapshot requires NOT_APPLICABLE score eligibility"
                )
        if self.availability is AvailabilityState.AVAILABLE and not self.source_refs:
            raise ValueError("AVAILABLE ParkingSnapshot requires source_refs")

        dynamic_metrics = [
            metric
            for observation in self.observations
            for metric in (observation.occupancy, observation.available_spaces)
            if metric.availability is AvailabilityState.AVAILABLE
        ]
        if self.dynamic_availability_present != bool(dynamic_metrics):
            raise ValueError(
                "dynamic_availability_present must reflect actual dynamic measurements"
            )

        nested_refs = {observation.source_ref for observation in self.observations}
        for observation in self.observations:
            for metric in (
                observation.capacity,
                observation.walk_time_to_site_seconds,
                observation.curb_length_m,
                observation.occupancy,
                observation.available_spaces,
            ):
                nested_refs.update(metric.source_refs)
        for _, metric, _ in summaries:
            nested_refs.update(metric.source_refs)
        if nested_refs - set(self.source_refs):
            raise ValueError("source_refs must include all parking observation/summary refs")
        require_aware_datetime(self.generated_at, field_name="generated_at")
