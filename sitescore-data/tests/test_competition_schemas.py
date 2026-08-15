from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
import math
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import AvailabilityState, DataQualityState
from sitescore_data.schemas.competition import (
    CompetitionCurve,
    CompetitionObservation,
    CompetitionSnapshot,
)


def observation(**overrides: object) -> CompetitionObservation:
    values: dict[str, object] = {
        "scale_id": "walk_600",
        "travel_mode": "walk",
        "catchment_semantics": "network_travel_time",
        "travel_cost": 600.0,
        "travel_cost_unit": "seconds",
        "competitor_count": 10,
        "catchment_area_km2": 2.0,
        "competitor_density_per_km2": 5.0,
        "source_refs": ("competition_source",),
        "method_version": "competition-density-v1",
    }
    values.update(overrides)
    return CompetitionObservation(**values)  # type: ignore[arg-type]


def curve(**overrides: object) -> CompetitionCurve:
    values: dict[str, object] = {
        "observations": (
            observation(),
            observation(
                scale_id="walk_1200",
                travel_cost=1200.0,
                competitor_count=30,
                catchment_area_km2=5.0,
                competitor_density_per_km2=6.0,
            ),
        )
    }
    values.update(overrides)
    return CompetitionCurve(**values)  # type: ignore[arg-type]


def snapshot(**overrides: object) -> CompetitionSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "competition_snapshot_001",
        "measurement_definition_id": "competition_measurement_v1",
        "curve": curve(),
        "benchmark_ref": None,
        "source_refs": ("competition_source",),
        "availability": AvailabilityState.AVAILABLE,
        "data_quality": DataQualityState.FULL,
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return CompetitionSnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("competitor_count", -1),
        ("catchment_area_km2", 0),
        ("catchment_area_km2", -1),
        ("competitor_density_per_km2", -1),
        ("travel_cost", 0),
        ("travel_cost", -1),
        ("travel_cost", math.nan),
        ("catchment_area_km2", math.inf),
        ("competitor_density_per_km2", -math.inf),
    ],
)
def test_competition_numeric_invariants(field_name: str, value: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        observation(**{field_name: value})


def test_density_must_match_count_over_area() -> None:
    with pytest.raises(ValueError):
        observation(competitor_density_per_km2=4.9)


def test_observed_zero_competitor_density_is_valid() -> None:
    value = observation(
        competitor_count=0,
        competitor_density_per_km2=0.0,
    )
    assert value.competitor_density_per_km2 == 0.0


def test_competition_curve_requires_multiple_scales() -> None:
    with pytest.raises(ValueError):
        CompetitionCurve(observations=(observation(),))


def test_duplicate_scale_id_rejected() -> None:
    with pytest.raises(ValueError):
        CompetitionCurve(
            observations=(
                observation(),
                observation(travel_cost=1200.0),
            )
        )


def test_curve_order_is_deterministic() -> None:
    with pytest.raises(ValueError):
        CompetitionCurve(
            observations=(
                observation(
                    scale_id="walk_1200",
                    travel_cost=1200.0,
                    competitor_count=20,
                    catchment_area_km2=4.0,
                    competitor_density_per_km2=5.0,
                ),
                observation(),
            )
        )


def test_available_snapshot_requires_curve_and_lineage() -> None:
    with pytest.raises(ValueError):
        snapshot(curve=None)
    with pytest.raises(ValueError):
        snapshot(source_refs=())


def test_missing_snapshot_does_not_carry_curve() -> None:
    value = snapshot(
        curve=None,
        source_refs=(),
        availability=AvailabilityState.MISSING,
        data_quality=DataQualityState.MISSING,
    )
    assert value.curve is None

    with pytest.raises(ValueError):
        snapshot(
            availability=AvailabilityState.MISSING,
            data_quality=DataQualityState.MISSING,
        )


def test_competition_generated_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        snapshot(generated_at=datetime(2026, 8, 12, 12, 0))


def test_competition_schemas_are_immutable() -> None:
    obs = observation()
    crv = curve()
    snap = snapshot()
    with pytest.raises(FrozenInstanceError):
        obs.competitor_count = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        crv.observations = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snap.source_refs = ()  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_competition_schemas_have_no_mutable_annotations() -> None:
    for schema in (CompetitionObservation, CompetitionCurve, CompetitionSnapshot):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])
