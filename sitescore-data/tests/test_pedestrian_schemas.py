from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
import math
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.pedestrian import IsochroneSnapshot, PedestrianCatchmentArtifact


def catchment(**overrides: object) -> PedestrianCatchmentArtifact:
    values: dict[str, object] = {
        "catchment_id": "walk_catchment_001",
        "origin_location_ref": "location_001",
        "origin_latitude": 40.7128,
        "origin_longitude": -74.006,
        "travel_mode": "walk",
        "travel_cost_budget_seconds": 600.0,
        "geometry_ref": "geometry://walk-catchment-001",
        "source_refs": ("routing_source",),
        "policy_version": "walk-policy-v1",
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return PedestrianCatchmentArtifact(**values)  # type: ignore[arg-type]


def area_metric(value: float = 1.5, source_ref: str = "routing_source") -> MetricValue:
    return MetricValue(
        value=value,
        unit="km2",
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=CalibrationState.CALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(source_ref,),
        method_version="isochrone-area-v1",
    )


def snapshot(**overrides: object) -> IsochroneSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "isochrone_001",
        "catchment_ref": "walk_catchment_001",
        "area_km2": area_metric(),
        "source_refs": ("routing_source",),
        "availability": AvailabilityState.AVAILABLE,
        "data_quality": DataQualityState.FULL,
        "method_version": "isochrone-v1",
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return IsochroneSnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("travel_cost", [0, -1, math.nan, math.inf, -math.inf])
def test_pedestrian_travel_cost_must_be_positive_and_finite(travel_cost: float) -> None:
    with pytest.raises(ValueError):
        catchment(travel_cost_budget_seconds=travel_cost)


def test_travel_mode_is_canonical_walk() -> None:
    with pytest.raises(ValueError):
        catchment(travel_mode="drive")


@pytest.mark.parametrize("area", [-0.1, math.nan, math.inf, -math.inf])
def test_isochrone_area_must_be_nonnegative_and_finite(area: float) -> None:
    if area < 0:
        metric = area_metric(0.0)
        object.__setattr__(metric, "value", area)
        with pytest.raises(ValueError):
            snapshot(area_km2=metric)
    else:
        with pytest.raises(ValueError):
            area_metric(area)


def test_zero_isochrone_area_is_allowed_when_observed() -> None:
    assert snapshot(area_km2=area_metric(0.0)).area_km2.value == 0.0


def test_catchment_requires_explicit_source_lineage() -> None:
    with pytest.raises(ValueError):
        catchment(source_refs=())


def test_isochrone_requires_explicit_source_lineage_when_available() -> None:
    with pytest.raises(ValueError):
        snapshot(source_refs=())


def test_isochrone_metric_lineage_must_be_in_snapshot_lineage() -> None:
    with pytest.raises(ValueError):
        snapshot(area_km2=area_metric(source_ref="other_source"))


def test_generated_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        catchment(generated_at=datetime(2026, 8, 12, 12, 0))
    with pytest.raises(ValueError):
        snapshot(generated_at=datetime(2026, 8, 12, 12, 0))


def test_pedestrian_schemas_are_immutable() -> None:
    value = catchment()
    snap = snapshot()
    with pytest.raises(FrozenInstanceError):
        value.travel_mode = "drive"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snap.source_refs = ()  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_pedestrian_schemas_have_no_mutable_annotations() -> None:
    for schema in (PedestrianCatchmentArtifact, IsochroneSnapshot):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def _nonavailable_area_metric(availability: AvailabilityState) -> MetricValue:
    quality = (
        DataQualityState.NOT_APPLICABLE
        if availability is AvailabilityState.NOT_APPLICABLE
        else DataQualityState.MISSING
    )
    eligibility = (
        ScoreEligibility.NOT_APPLICABLE
        if availability is AvailabilityState.NOT_APPLICABLE
        else ScoreEligibility.INELIGIBLE
    )
    calibration = (
        CalibrationState.NOT_APPLICABLE
        if availability is AvailabilityState.NOT_APPLICABLE
        else CalibrationState.CALIBRATED
    )
    return MetricValue(
        value=None,
        unit="km2",
        availability=availability,
        data_quality=quality,
        score_eligibility=eligibility,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=False,
        source_refs=(),
        method_version="isochrone-area-v1",
    )


@pytest.mark.parametrize(
    "availability",
    [
        AvailabilityState.MISSING,
        AvailabilityState.UNAVAILABLE,
        AvailabilityState.NOT_APPLICABLE,
    ],
)
def test_isochrone_snapshot_availability_tracks_primary_area_metric(
    availability: AvailabilityState,
) -> None:
    quality = (
        DataQualityState.NOT_APPLICABLE
        if availability is AvailabilityState.NOT_APPLICABLE
        else DataQualityState.MISSING
    )

    with pytest.raises(ValueError):
        snapshot(
            availability=availability,
            data_quality=quality,
            area_km2=area_metric(),
        )

    value = snapshot(
        availability=availability,
        data_quality=quality,
        area_km2=_nonavailable_area_metric(availability),
        source_refs=(),
    )
    assert value.availability is availability


def test_pedestrian_budget_has_no_schema_default() -> None:
    budget_field = next(
        field
        for field in fields(PedestrianCatchmentArtifact)
        if field.name == "travel_cost_budget_seconds"
    )
    from dataclasses import MISSING

    assert budget_field.default is MISSING
    assert budget_field.default_factory is MISSING
