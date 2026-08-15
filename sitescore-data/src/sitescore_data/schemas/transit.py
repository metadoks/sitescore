"""Immutable GTFS-derived transit service contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sitescore_data.enums import AvailabilityState, DataQualityState, ValidityState
from sitescore_data.schemas.benchmarks import BenchmarkReference
from sitescore_data.schemas.common import MetricValue
from sitescore_data.validation import (
    require_aware_datetime,
    require_bounded_number,
    require_canonical_identifier,
    require_latitude,
    require_longitude,
    require_nonnegative_number,
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


def _require_snapshot_quality(
    availability: AvailabilityState,
    data_quality: DataQualityState,
) -> None:
    if not isinstance(availability, AvailabilityState):
        raise TypeError("availability must be an AvailabilityState")
    if not isinstance(data_quality, DataQualityState):
        raise TypeError("data_quality must be a DataQualityState")
    allowed = {
        AvailabilityState.AVAILABLE: {DataQualityState.FULL, DataQualityState.DEGRADED},
        AvailabilityState.MISSING: {DataQualityState.MISSING},
        AvailabilityState.UNAVAILABLE: {DataQualityState.MISSING},
        AvailabilityState.UNKNOWN: {DataQualityState.DEGRADED, DataQualityState.MISSING},
        AvailabilityState.NOT_APPLICABLE: {DataQualityState.NOT_APPLICABLE},
    }[availability]
    if data_quality not in allowed:
        raise ValueError("TransitSnapshot availability/data_quality are inconsistent")


@dataclass(frozen=True, slots=True)
class TransitStopRef:
    """Reference to one GTFS stop/platform with canonical station grouping metadata."""

    feed_id: str
    stop_id: str
    location_type: int
    parent_station_id: str | None
    canonical_station_id: str
    latitude: float
    longitude: float
    access_geometry_quality: str
    reachable_by_walk: bool
    walk_catchment_ref: str
    source_ref: str

    def __post_init__(self) -> None:
        require_canonical_identifier(self.feed_id, field_name="feed_id")
        _require_nonempty_text(self.stop_id, field_name="stop_id")
        require_nonnegative_number(self.location_type, field_name="location_type")
        if not isinstance(self.location_type, int) or isinstance(self.location_type, bool):
            raise TypeError("location_type must be an int")
        if self.parent_station_id is not None:
            _require_nonempty_text(self.parent_station_id, field_name="parent_station_id")
        _require_nonempty_text(
            self.canonical_station_id,
            field_name="canonical_station_id",
        )
        require_latitude(self.latitude, field_name="latitude")
        require_longitude(self.longitude, field_name="longitude")
        require_canonical_identifier(
            self.access_geometry_quality,
            field_name="access_geometry_quality",
        )
        if not isinstance(self.reachable_by_walk, bool):
            raise TypeError("reachable_by_walk must be a bool")
        require_canonical_identifier(
            self.walk_catchment_ref,
            field_name="walk_catchment_ref",
        )
        require_canonical_identifier(self.source_ref, field_name="source_ref")


@dataclass(frozen=True, slots=True)
class TransitServiceWindow:
    """Versioned temporal semantics for one canonical typical-week profile."""

    timezone: str
    validity_state: ValidityState
    validity_start: date | None
    validity_end: date | None
    reference_dates: tuple[date, ...]
    temporal_policy_version: str
    service_calendar_version: str
    profile_type: str = "typical_published_week"
    hour_bins: int = 168
    calendar_exceptions_applied: bool = True
    service_day_over_24h_semantics: bool = True

    def __post_init__(self) -> None:
        _require_nonempty_text(self.timezone, field_name="timezone")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        if not isinstance(self.validity_state, ValidityState):
            raise TypeError("validity_state must be a ValidityState")
        if self.validity_start is not None and not isinstance(self.validity_start, date):
            raise TypeError("validity_start must be a date or None")
        if self.validity_end is not None and not isinstance(self.validity_end, date):
            raise TypeError("validity_end must be a date or None")
        if (
            self.validity_start is not None
            and self.validity_end is not None
            and self.validity_end < self.validity_start
        ):
            raise ValueError("validity_end must be >= validity_start")
        if not isinstance(self.reference_dates, tuple):
            raise TypeError("reference_dates must be a tuple")
        if any(not isinstance(item, date) for item in self.reference_dates):
            raise TypeError("reference_dates must contain date values")
        if len(set(self.reference_dates)) != len(self.reference_dates):
            raise ValueError("reference_dates must not contain duplicates")
        if self.reference_dates != tuple(sorted(self.reference_dates)):
            raise ValueError("reference_dates must be deterministically sorted")
        if self.validity_start is not None and any(
            item < self.validity_start for item in self.reference_dates
        ):
            raise ValueError(
                "reference_dates must not precede validity_start"
            )
        if self.validity_end is not None and any(
            item > self.validity_end for item in self.reference_dates
        ):
            raise ValueError(
                "reference_dates must not exceed validity_end"
            )
        _require_nonempty_text(
            self.temporal_policy_version,
            field_name="temporal_policy_version",
        )
        _require_nonempty_text(
            self.service_calendar_version,
            field_name="service_calendar_version",
        )
        if self.profile_type != "typical_published_week":
            raise ValueError('profile_type must be "typical_published_week"')
        if self.hour_bins != 168:
            raise ValueError("hour_bins must equal 168")
        if self.calendar_exceptions_applied is not True:
            raise ValueError("calendar + calendar_dates semantics must be applied")
        if self.service_day_over_24h_semantics is not True:
            raise ValueError("GTFS >24:00 service-day semantics must be preserved")


@dataclass(frozen=True, slots=True)
class TransitObservation:
    """One hour-of-week service-supply observation."""

    hour_of_week: int
    scheduled_exact_departures: int
    frequency_departure_equivalents: float
    total_departure_equivalents: float

    def __post_init__(self) -> None:
        if not isinstance(self.hour_of_week, int) or isinstance(self.hour_of_week, bool):
            raise TypeError("hour_of_week must be an int")
        require_bounded_number(
            self.hour_of_week,
            low=0,
            high=167,
            field_name="hour_of_week",
        )
        require_nonnegative_number(
            self.scheduled_exact_departures,
            field_name="scheduled_exact_departures",
        )
        if not isinstance(self.scheduled_exact_departures, int) or isinstance(
            self.scheduled_exact_departures, bool
        ):
            raise TypeError("scheduled_exact_departures must be an int")
        require_nonnegative_number(
            self.frequency_departure_equivalents,
            field_name="frequency_departure_equivalents",
        )
        require_nonnegative_number(
            self.total_departure_equivalents,
            field_name="total_departure_equivalents",
        )
        expected = (
            self.scheduled_exact_departures + self.frequency_departure_equivalents
        )
        if not math.isclose(
            self.total_departure_equivalents,
            expected,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "total_departure_equivalents must equal scheduled exact "
                "+ frequency departure equivalents"
            )


@dataclass(frozen=True, slots=True)
class TransitSnapshot:
    """Canonical GTFS scheduled/headway service-supply snapshot."""

    snapshot_id: str
    stops: tuple[TransitStopRef, ...]
    service_window: TransitServiceWindow
    observations: tuple[TransitObservation, ...]
    service_departure_equivalents_per_hour: MetricValue
    benchmark_ref: BenchmarkReference | None
    source_bundle_fingerprint: str
    source_refs: tuple[str, ...]
    availability: AvailabilityState
    data_quality: DataQualityState
    generated_at: datetime

    def __post_init__(self) -> None:
        require_canonical_identifier(self.snapshot_id, field_name="snapshot_id")
        if not isinstance(self.stops, tuple):
            raise TypeError("stops must be a tuple")
        for stop in self.stops:
            if not isinstance(stop, TransitStopRef):
                raise TypeError("stops must contain TransitStopRef values")
        stop_keys = tuple((stop.feed_id, stop.stop_id) for stop in self.stops)
        if len(set(stop_keys)) != len(stop_keys):
            raise ValueError("stops must not contain duplicate feed_id/stop_id pairs")
        expected_stop_order = tuple(
            sorted(
                self.stops,
                key=lambda stop: (
                    stop.feed_id,
                    stop.canonical_station_id,
                    stop.stop_id,
                ),
            )
        )
        if self.stops != expected_stop_order:
            raise ValueError(
                "stops must be deterministically ordered by "
                "feed_id, canonical_station_id, stop_id"
            )
        if not isinstance(self.service_window, TransitServiceWindow):
            raise TypeError("service_window must be a TransitServiceWindow")
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be a tuple")
        for observation in self.observations:
            if not isinstance(observation, TransitObservation):
                raise TypeError("observations must contain TransitObservation values")
        if not isinstance(self.service_departure_equivalents_per_hour, MetricValue):
            raise TypeError(
                "service_departure_equivalents_per_hour must be a MetricValue"
            )
        if self.service_departure_equivalents_per_hour.unit != (
            "departure_equivalents_per_hour"
        ):
            raise ValueError(
                "service_departure_equivalents_per_hour must use unit "
                '"departure_equivalents_per_hour"'
            )
        if self.benchmark_ref is not None and not isinstance(
            self.benchmark_ref, BenchmarkReference
        ):
            raise TypeError("benchmark_ref must be a BenchmarkReference or None")
        _require_nonempty_text(
            self.source_bundle_fingerprint,
            field_name="source_bundle_fingerprint",
        )
        _require_unique_source_refs(self.source_refs)
        _require_snapshot_quality(self.availability, self.data_quality)
        if (
            self.service_departure_equivalents_per_hour.availability
            is not self.availability
        ):
            raise ValueError(
                "TransitSnapshot availability must equal primary metric availability"
            )

        if self.availability is AvailabilityState.AVAILABLE:
            if self.service_window.validity_state not in {
                ValidityState.VALID,
                ValidityState.DERIVED_VALIDITY,
            }:
                raise ValueError(
                    "AVAILABLE TransitSnapshot requires VALID or DERIVED_VALIDITY window"
                )
            if not self.service_window.reference_dates:
                raise ValueError(
                    "AVAILABLE TransitSnapshot requires at least one reference date"
                )
            if len(self.observations) != 168:
                raise ValueError("AVAILABLE transit profile must contain 168 observations")
            hours = tuple(item.hour_of_week for item in self.observations)
            if hours != tuple(range(168)):
                raise ValueError(
                    "transit observations must be unique and ordered hour_of_week 0..167"
                )
            if not self.source_refs:
                raise ValueError("AVAILABLE TransitSnapshot requires source_refs")
            expected_mean = sum(
                item.total_departure_equivalents for item in self.observations
            ) / 168.0
            value = self.service_departure_equivalents_per_hour.value
            assert value is not None
            if not math.isclose(value, expected_mean, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(
                    "service_departure_equivalents_per_hour must equal "
                    "the 168-hour profile mean"
                )
        else:
            if self.observations:
                raise ValueError(
                    "non-AVAILABLE TransitSnapshot must not fabricate service observations"
                )

        if self.service_window.validity_state is ValidityState.OUT_OF_VALIDITY:
            if self.availability is AvailabilityState.AVAILABLE:
                raise ValueError("OUT_OF_VALIDITY transit source cannot be AVAILABLE")
            if self.observations:
                raise ValueError("OUT_OF_VALIDITY transit source must not produce observations")

        nested_refs = {stop.source_ref for stop in self.stops}
        nested_refs.update(self.service_departure_equivalents_per_hour.source_refs)
        if self.benchmark_ref is not None:
            nested_refs.update(self.benchmark_ref.source_refs)
        if nested_refs - set(self.source_refs):
            raise ValueError("source_refs must include all nested transit source refs")
        require_aware_datetime(self.generated_at, field_name="generated_at")
