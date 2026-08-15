from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
import math
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import AvailabilityState, DataQualityState
from sitescore_data.schemas.road import (
    RoadAccessSnapshot,
    RoadObservation,
    RoadOriginQuality,
)


def observation(**overrides: object) -> RoadObservation:
    values: dict[str, object] = {
        "travel_cost_seconds": 600.0,
        "reachable_area_km2": 10.0,
        "reachable_network_length_km": 30.0,
        "reachable_connector_count": 20,
        "origin_to_network_cost_seconds": 15.0,
        "benchmark_percentile": None,
        "source_refs": ("road_source",),
        "method_version": "road-reach-v1",
    }
    values.update(overrides)
    return RoadObservation(**values)  # type: ignore[arg-type]


def snapshot(**overrides: object) -> RoadAccessSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "road_snapshot_001",
        "road_origin_ref": "road_origin_001",
        "road_origin_quality": RoadOriginQuality.DRIVEWAY,
        "routing_profile_id": "motor_vehicle_default",
        "routing_profile_version": "routing-profile-v1",
        "observations": (
            observation(),
            observation(
                travel_cost_seconds=1200.0,
                reachable_area_km2=25.0,
                reachable_network_length_km=70.0,
                reachable_connector_count=50,
            ),
        ),
        "benchmark_ref": None,
        "source_refs": ("road_source",),
        "availability": AvailabilityState.AVAILABLE,
        "data_quality": DataQualityState.FULL,
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return RoadAccessSnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("travel_cost_seconds", 0),
        ("travel_cost_seconds", -1),
        ("travel_cost_seconds", math.nan),
        ("reachable_area_km2", -1),
        ("reachable_network_length_km", -1),
        ("reachable_connector_count", -1),
        ("origin_to_network_cost_seconds", -1),
        ("reachable_area_km2", math.inf),
    ],
)
def test_road_numeric_invariants(field_name: str, value: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        observation(**{field_name: value})


def test_benchmark_percentile_may_be_absent_when_uncalibrated() -> None:
    assert observation(benchmark_percentile=None).benchmark_percentile is None


def test_benchmark_percentile_must_be_0_to_1_when_present() -> None:
    with pytest.raises(ValueError):
        observation(benchmark_percentile=1.1)


def test_duplicate_travel_cost_scale_rejected() -> None:
    with pytest.raises(ValueError):
        snapshot(observations=(observation(), observation()))


def test_road_observations_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        snapshot(
            observations=(
                observation(travel_cost_seconds=1200.0),
                observation(),
            )
        )


def test_available_road_snapshot_requires_observations_and_lineage() -> None:
    with pytest.raises(ValueError):
        snapshot(observations=())
    with pytest.raises(ValueError):
        snapshot(source_refs=())


def test_missing_road_snapshot_does_not_fabricate_observations() -> None:
    value = snapshot(
        road_origin_quality=RoadOriginQuality.UNRESOLVED,
        observations=(),
        source_refs=(),
        availability=AvailabilityState.MISSING,
        data_quality=DataQualityState.MISSING,
    )
    assert value.observations == ()


def test_road_generated_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        snapshot(generated_at=datetime(2026, 8, 12, 12, 0))


def test_road_schemas_are_immutable() -> None:
    obs = observation()
    snap = snapshot()
    with pytest.raises(FrozenInstanceError):
        obs.reachable_area_km2 = 20.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snap.observations = ()  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_road_schemas_have_no_mutable_annotations() -> None:
    for schema in (RoadObservation, RoadAccessSnapshot):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def test_road_snapshot_carries_reproducible_origin_identity() -> None:
    value = snapshot()
    assert value.road_origin_ref == "road_origin_001"
    assert value.road_origin_quality is RoadOriginQuality.DRIVEWAY
    assert value.routing_profile_id == "motor_vehicle_default"
    assert value.routing_profile_version == "routing-profile-v1"


def test_available_road_snapshot_rejects_unresolved_origin() -> None:
    with pytest.raises(ValueError):
        snapshot(road_origin_quality=RoadOriginQuality.UNRESOLVED)


def test_nonavailable_road_snapshot_may_preserve_unresolved_origin_state() -> None:
    value = snapshot(
        road_origin_quality=RoadOriginQuality.UNRESOLVED,
        observations=(),
        source_refs=(),
        availability=AvailabilityState.MISSING,
        data_quality=DataQualityState.MISSING,
    )
    assert value.road_origin_quality is RoadOriginQuality.UNRESOLVED
