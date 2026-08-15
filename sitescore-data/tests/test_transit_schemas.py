from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime, timezone
import math
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    ScoreEligibility,
    ValidityState,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.transit import (
    TransitObservation,
    TransitServiceWindow,
    TransitSnapshot,
    TransitStopRef,
)


def metric(
    value: float | None,
    *,
    availability: AvailabilityState = AvailabilityState.AVAILABLE,
    data_quality: DataQualityState = DataQualityState.FULL,
) -> MetricValue:
    if availability is AvailabilityState.AVAILABLE:
        eligibility = ScoreEligibility.ELIGIBLE
        calibration = CalibrationState.CALIBRATED
        refs = ("gtfs_source",)
    else:
        eligibility = ScoreEligibility.INELIGIBLE
        calibration = CalibrationState.CALIBRATED
        refs = ()
    return MetricValue(
        value=value,
        unit="departure_equivalents_per_hour",
        availability=availability,
        data_quality=data_quality,
        score_eligibility=eligibility,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=False,
        source_refs=refs,
        method_version="transit-supply-v1",
    )


def service_window(**overrides: object) -> TransitServiceWindow:
    values: dict[str, object] = {
        "timezone": "America/New_York",
        "validity_state": ValidityState.VALID,
        "validity_start": date(2026, 1, 1),
        "validity_end": date(2026, 12, 31),
        "reference_dates": (
            date(2026, 8, 3),
            date(2026, 8, 4),
            date(2026, 8, 5),
            date(2026, 8, 6),
            date(2026, 8, 7),
            date(2026, 8, 8),
            date(2026, 8, 9),
        ),
        "temporal_policy_version": "typical-week-v1",
        "service_calendar_version": "gtfs-calendar-v1",
    }
    values.update(overrides)
    return TransitServiceWindow(**values)  # type: ignore[arg-type]


def observation(hour: int, total: float = 2.5) -> TransitObservation:
    return TransitObservation(
        hour_of_week=hour,
        scheduled_exact_departures=2,
        frequency_departure_equivalents=total - 2,
        total_departure_equivalents=total,
    )


def zero_observation(hour: int) -> TransitObservation:
    return TransitObservation(
        hour_of_week=hour,
        scheduled_exact_departures=0,
        frequency_departure_equivalents=0.0,
        total_departure_equivalents=0.0,
    )


def profile(total: float = 2.5) -> tuple[TransitObservation, ...]:
    return tuple(observation(hour, total) for hour in range(168))


def stop(**overrides: object) -> TransitStopRef:
    values: dict[str, object] = {
        "feed_id": "mta_gtfs",
        "stop_id": "A01N",
        "location_type": 0,
        "parent_station_id": "A01",
        "canonical_station_id": "A01",
        "latitude": 40.7,
        "longitude": -74.0,
        "access_geometry_quality": "station_point_fallback",
        "reachable_by_walk": True,
        "walk_catchment_ref": "walk_catchment_001",
        "source_ref": "gtfs_source",
    }
    values.update(overrides)
    return TransitStopRef(**values)  # type: ignore[arg-type]


def snapshot(**overrides: object) -> TransitSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "transit_snapshot_001",
        "stops": (stop(),),
        "service_window": service_window(),
        "observations": profile(),
        "service_departure_equivalents_per_hour": metric(2.5),
        "benchmark_ref": None,
        "source_bundle_fingerprint": "sha256:transit-bundle-test",
        "source_refs": ("gtfs_source",),
        "availability": AvailabilityState.AVAILABLE,
        "data_quality": DataQualityState.FULL,
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return TransitSnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hour_of_week": -1},
        {"hour_of_week": 168},
        {"scheduled_exact_departures": -1},
        {"frequency_departure_equivalents": -0.1},
        {"total_departure_equivalents": -0.1},
        {"frequency_departure_equivalents": math.nan},
        {"total_departure_equivalents": math.inf},
    ],
)
def test_transit_observation_numeric_invariants(kwargs: dict[str, object]) -> None:
    values: dict[str, object] = {
        "hour_of_week": 0,
        "scheduled_exact_departures": 2,
        "frequency_departure_equivalents": 0.5,
        "total_departure_equivalents": 2.5,
    }
    values.update(kwargs)
    with pytest.raises((ValueError, TypeError)):
        TransitObservation(**values)  # type: ignore[arg-type]


def test_total_departure_equivalents_must_match_components() -> None:
    with pytest.raises(ValueError):
        TransitObservation(
            hour_of_week=0,
            scheduled_exact_departures=2,
            frequency_departure_equivalents=0.5,
            total_departure_equivalents=3.0,
        )


def test_zero_observed_service_is_valid() -> None:
    observations = tuple(zero_observation(hour) for hour in range(168))
    value = snapshot(
        observations=observations,
        service_departure_equivalents_per_hour=metric(0.0),
    )
    assert value.service_departure_equivalents_per_hour.value == 0.0


def test_available_transit_requires_exactly_168_ordered_hours() -> None:
    with pytest.raises(ValueError):
        snapshot(observations=profile()[:-1])

    unordered = list(profile())
    unordered[0], unordered[1] = unordered[1], unordered[0]
    with pytest.raises(ValueError):
        snapshot(observations=tuple(unordered))


def test_primary_metric_must_equal_profile_mean() -> None:
    with pytest.raises(ValueError):
        snapshot(service_departure_equivalents_per_hour=metric(3.0))


def test_out_of_validity_source_produces_no_numeric_transit() -> None:
    value = snapshot(
        stops=(),
        service_window=service_window(validity_state=ValidityState.OUT_OF_VALIDITY),
        observations=(),
        service_departure_equivalents_per_hour=metric(
            None,
            availability=AvailabilityState.UNAVAILABLE,
            data_quality=DataQualityState.MISSING,
        ),
        source_refs=(),
        availability=AvailabilityState.UNAVAILABLE,
        data_quality=DataQualityState.MISSING,
    )
    assert value.observations == ()
    assert value.service_departure_equivalents_per_hour.value is None


def test_missing_gtfs_is_not_zero_transit() -> None:
    missing = snapshot(
        stops=(),
        service_window=service_window(validity_state=ValidityState.UNKNOWN),
        observations=(),
        service_departure_equivalents_per_hour=metric(
            None,
            availability=AvailabilityState.MISSING,
            data_quality=DataQualityState.MISSING,
        ),
        source_refs=(),
        availability=AvailabilityState.MISSING,
        data_quality=DataQualityState.MISSING,
    )
    assert missing.service_departure_equivalents_per_hour.value is None


def test_service_window_requires_gtfs_semantics() -> None:
    with pytest.raises(ValueError):
        service_window(calendar_exceptions_applied=False)
    with pytest.raises(ValueError):
        service_window(service_day_over_24h_semantics=False)
    with pytest.raises(ValueError):
        service_window(hour_bins=24)


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValueError):
        service_window(timezone="Not/A_Timezone")


def test_duplicate_stop_identity_rejected() -> None:
    with pytest.raises(ValueError):
        snapshot(stops=(stop(), stop()))


def test_transit_generated_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        snapshot(generated_at=datetime(2026, 8, 12, 12, 0))


def test_transit_schemas_are_immutable() -> None:
    obs = observation(0)
    window = service_window()
    snap = snapshot()
    with pytest.raises(FrozenInstanceError):
        obs.hour_of_week = 1  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        window.hour_bins = 24  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snap.observations = ()  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_transit_schemas_have_no_mutable_annotations() -> None:
    for schema in (TransitStopRef, TransitServiceWindow, TransitObservation, TransitSnapshot):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def test_available_transit_requires_reference_dates() -> None:
    with pytest.raises(ValueError):
        snapshot(service_window=service_window(reference_dates=()))


def test_reference_dates_must_fall_within_validity_interval() -> None:
    with pytest.raises(ValueError):
        service_window(reference_dates=(date(2025, 12, 31),))
    with pytest.raises(ValueError):
        service_window(reference_dates=(date(2027, 1, 1),))


def test_transit_stops_must_be_deterministically_ordered() -> None:
    first = stop(
        feed_id="feed_a",
        canonical_station_id="station_a",
        stop_id="stop_a",
    )
    second = stop(
        feed_id="feed_b",
        canonical_station_id="station_b",
        stop_id="stop_b",
    )
    value = snapshot(stops=(first, second))
    assert value.stops == (first, second)
    with pytest.raises(ValueError):
        snapshot(stops=(second, first))


def test_transit_source_bundle_fingerprint_is_required() -> None:
    value = snapshot()
    assert value.source_bundle_fingerprint == "sha256:transit-bundle-test"
    with pytest.raises(ValueError):
        snapshot(source_bundle_fingerprint="")
