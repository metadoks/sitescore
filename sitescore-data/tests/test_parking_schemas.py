from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.parking import (
    ParkingAccessClass,
    ParkingMode,
    ParkingObservation,
    ParkingSnapshot,
)


def metric(
    value: int | float | None,
    unit: str,
    *,
    availability: AvailabilityState = AvailabilityState.AVAILABLE,
    quality: DataQualityState = DataQualityState.FULL,
    source_ref: str = "parking_source",
) -> MetricValue:
    if availability is AvailabilityState.AVAILABLE:
        eligibility = ScoreEligibility.DIAGNOSTIC_ONLY
        calibration = CalibrationState.UNCALIBRATED
        refs = (source_ref,)
    elif availability is AvailabilityState.NOT_APPLICABLE:
        eligibility = ScoreEligibility.NOT_APPLICABLE
        calibration = CalibrationState.NOT_APPLICABLE
        refs = ()
    else:
        eligibility = ScoreEligibility.INELIGIBLE
        calibration = CalibrationState.UNCALIBRATED
        refs = ()
    return MetricValue(
        value=value,
        unit=unit,
        availability=availability,
        data_quality=quality,
        score_eligibility=eligibility,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=False,
        source_refs=refs,
        method_version="parking-metric-v1",
    )


def unknown_metric(unit: str) -> MetricValue:
    return metric(
        None,
        unit,
        availability=AvailabilityState.UNKNOWN,
        quality=DataQualityState.DEGRADED,
    )


def not_applicable_metric(unit: str) -> MetricValue:
    return metric(
        None,
        unit,
        availability=AvailabilityState.NOT_APPLICABLE,
        quality=DataQualityState.NOT_APPLICABLE,
    )


def observation(**overrides: object) -> ParkingObservation:
    values: dict[str, object] = {
        "parking_id": "parking_001",
        "parking_mode": ParkingMode.OFF_STREET,
        "access_class": ParkingAccessClass.PUBLIC,
        "generic_public_supply_eligible": True,
        "capacity": unknown_metric("spaces"),
        "motor_vehicle_reachable": True,
        "walk_time_to_site_seconds": metric(120.0, "seconds"),
        "curb_length_m": not_applicable_metric("m"),
        "occupancy": unknown_metric("ratio"),
        "available_spaces": unknown_metric("spaces"),
        "availability_timestamp": None,
        "source_ref": "parking_source",
    }
    values.update(overrides)
    return ParkingObservation(**values)  # type: ignore[arg-type]


def summary_metric(value: int | float, unit: str) -> MetricValue:
    return metric(value, unit)


def snapshot(**overrides: object) -> ParkingSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "parking_snapshot_001",
        "observations": (observation(),),
        "mapped_public_facility_count": summary_metric(1, "count"),
        "known_public_offstreet_capacity": summary_metric(0, "spaces"),
        "unknown_capacity_facility_count": summary_metric(1, "count"),
        "mapped_legal_curb_length_m": summary_metric(0.0, "m"),
        "known_onstreet_capacity": summary_metric(0, "spaces"),
        "dynamic_availability_present": False,
        "source_refs": ("parking_source",),
        "availability": AvailabilityState.AVAILABLE,
        "data_quality": DataQualityState.DEGRADED,
        "score_eligibility": ScoreEligibility.DIAGNOSTIC_ONLY,
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return ParkingSnapshot(**values)  # type: ignore[arg-type]


def test_unknown_capacity_is_none_not_zero() -> None:
    value = observation()
    assert value.capacity.availability is AvailabilityState.UNKNOWN
    assert value.capacity.value is None


def test_observed_zero_capacity_is_valid() -> None:
    value = observation(capacity=metric(0, "spaces"))
    assert value.capacity.value == 0
    assert value.capacity.availability is AvailabilityState.AVAILABLE


def test_static_supply_and_curb_length_are_dimensionally_separate() -> None:
    value = snapshot()
    assert value.known_public_offstreet_capacity.unit == "spaces"
    assert value.mapped_legal_curb_length_m.unit == "m"


def test_private_and_customer_only_are_not_generic_public_supply() -> None:
    for access_class in (
        ParkingAccessClass.PRIVATE,
        ParkingAccessClass.CUSTOMERS,
    ):
        value = observation(
            access_class=access_class,
            generic_public_supply_eligible=False,
        )
        assert value.generic_public_supply_eligible is False

        with pytest.raises(ValueError):
            observation(
                access_class=access_class,
                generic_public_supply_eligible=True,
            )


def test_public_and_permissive_are_generic_public_supply() -> None:
    for access_class in (
        ParkingAccessClass.PUBLIC,
        ParkingAccessClass.PERMISSIVE,
    ):
        assert observation(
            access_class=access_class,
            generic_public_supply_eligible=True,
        ).generic_public_supply_eligible


def test_diagnostic_only_snapshot_is_valid() -> None:
    value = snapshot(score_eligibility=ScoreEligibility.DIAGNOSTIC_ONLY)
    assert value.score_eligibility is ScoreEligibility.DIAGNOSTIC_ONLY


def test_dynamic_availability_is_not_inferred_as_zero_when_absent() -> None:
    value = observation()
    assert value.occupancy.value is None
    assert value.available_spaces.value is None


def test_dynamic_presence_must_match_available_dynamic_measurements() -> None:
    dynamic_obs = observation(
        occupancy=metric(0.5, "ratio"),
        available_spaces=metric(5, "spaces"),
        availability_timestamp=datetime(
            2026, 8, 12, 11, 55, tzinfo=timezone.utc
        ),
    )
    with pytest.raises(ValueError):
        snapshot(observations=(dynamic_obs,), dynamic_availability_present=False)

    value = snapshot(
        observations=(dynamic_obs,),
        dynamic_availability_present=True,
    )
    assert value.dynamic_availability_present is True


def test_parking_snapshot_requires_explicit_lineage_when_available() -> None:
    with pytest.raises(ValueError):
        snapshot(source_refs=())


def test_parking_generated_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        snapshot(generated_at=datetime(2026, 8, 12, 12, 0))


def test_parking_schemas_are_immutable() -> None:
    obs = observation()
    snap = snapshot()
    with pytest.raises(FrozenInstanceError):
        obs.parking_id = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snap.observations = ()  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_parking_schemas_have_no_mutable_annotations() -> None:
    for schema in (ParkingObservation, ParkingSnapshot):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def test_parking_observation_preserves_independent_metric_provenance() -> None:
    routing_walk_time = metric(
        120.0,
        "seconds",
        source_ref="routing_source",
    )
    obs = observation(walk_time_to_site_seconds=routing_walk_time)
    assert obs.source_ref == "parking_source"
    assert obs.walk_time_to_site_seconds.source_refs == ("routing_source",)

    with pytest.raises(ValueError):
        snapshot(observations=(obs,))

    value = snapshot(
        observations=(obs,),
        source_refs=("parking_source", "routing_source"),
    )
    assert "routing_source" in value.source_refs


def test_dynamic_measurements_require_aware_availability_timestamp() -> None:
    with pytest.raises(ValueError):
        observation(
            occupancy=metric(0.5, "ratio"),
            availability_timestamp=None,
        )

    with pytest.raises(ValueError):
        observation(
            available_spaces=metric(1, "spaces"),
            availability_timestamp=datetime(2026, 8, 12, 11, 55),
        )

    value = observation(
        available_spaces=metric(1, "spaces"),
        availability_timestamp=datetime(
            2026, 8, 12, 11, 55, tzinfo=timezone.utc
        ),
    )
    assert value.availability_timestamp is not None


def test_static_parking_observation_does_not_accept_dynamic_timestamp() -> None:
    with pytest.raises(ValueError):
        observation(
            availability_timestamp=datetime(
                2026, 8, 12, 11, 55, tzinfo=timezone.utc
            )
        )


def test_available_spaces_cannot_exceed_observed_capacity() -> None:
    timestamp = datetime(2026, 8, 12, 11, 55, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        observation(
            capacity=metric(10, "spaces"),
            available_spaces=metric(11, "spaces"),
            availability_timestamp=timestamp,
        )

    with pytest.raises(ValueError):
        observation(
            capacity=metric(0, "spaces"),
            available_spaces=metric(1, "spaces"),
            availability_timestamp=timestamp,
        )


def test_walk_time_is_measurement_not_threshold_based_eligibility() -> None:
    value = observation(
        walk_time_to_site_seconds=metric(900.0, "seconds")
    )
    assert value.walk_time_to_site_seconds.value == 900.0
