from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
import math
from typing import get_type_hints, get_origin, get_args

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    GeographyType,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.demographics import AgeCohortPopulation, DemographicSnapshot
from sitescore_data.schemas.geography import GeographyRef


def geography() -> GeographyRef:
    return GeographyRef(
        geography_type=GeographyType.BLOCK_GROUP,
        geography_id="360610001001",
        name="Block Group 1",
        country_code="US",
        source_ref="census_geo",
        source_version="2025",
    )


def metric(value: int | float, unit: str, source_ref: str = "census_acs") -> MetricValue:
    return MetricValue(
        value=value,
        unit=unit,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=CalibrationState.CALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(source_ref,),
        method_version="metric-v1",
    )


def cohort(**overrides: object) -> AgeCohortPopulation:
    values: dict[str, object] = {
        "cohort_id": "age_18_24",
        "age_min_inclusive": 18,
        "age_max_exclusive": 25,
        "population": 100,
        "population_share": 0.25,
    }
    values.update(overrides)
    return AgeCohortPopulation(**values)  # type: ignore[arg-type]


def snapshot(**overrides: object) -> DemographicSnapshot:
    values: dict[str, object] = {
        "geography_ref": geography(),
        "total_population": metric(400, "people"),
        "age_cohorts": (cohort(),),
        "household_income": metric(80000, "usd_per_household"),
        "source_refs": ("census_acs",),
        "availability": AvailabilityState.AVAILABLE,
        "data_quality": DataQualityState.FULL,
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return DemographicSnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "age_min,age_max",
    [(-1, 10), (10, 10), (10, 9)],
)
def test_age_bounds_rejected(age_min: int, age_max: int) -> None:
    with pytest.raises(ValueError):
        cohort(age_min_inclusive=age_min, age_max_exclusive=age_max)


def test_open_ended_age_cohort_allowed() -> None:
    value = cohort(age_min_inclusive=65, age_max_exclusive=None)
    assert value.age_max_exclusive is None


def test_negative_population_rejected() -> None:
    with pytest.raises(ValueError):
        cohort(population=-1)


@pytest.mark.parametrize("share", [-0.01, 1.01, math.nan, math.inf, -math.inf])
def test_population_share_must_be_finite_and_bounded(share: float) -> None:
    with pytest.raises(ValueError):
        cohort(population_share=share)


def test_population_share_boundaries_allowed() -> None:
    assert cohort(population_share=0.0).population_share == 0.0
    assert cohort(population_share=1.0).population_share == 1.0


def test_duplicate_cohort_identity_rejected() -> None:
    first = cohort()
    second = cohort(age_min_inclusive=25, age_max_exclusive=35)
    with pytest.raises(ValueError):
        snapshot(age_cohorts=(first, second))


def test_demographic_snapshot_requires_explicit_lineage() -> None:
    with pytest.raises(ValueError):
        snapshot(source_refs=())


def test_metric_lineage_must_be_in_snapshot_lineage() -> None:
    with pytest.raises(ValueError):
        snapshot(total_population=metric(400, "people", "other_source"))


def test_demographic_snapshot_rejects_naive_generated_at() -> None:
    with pytest.raises(ValueError):
        snapshot(generated_at=datetime(2026, 8, 12, 12, 0))


def test_demographic_schemas_are_immutable() -> None:
    value = cohort()
    snap = snapshot()
    with pytest.raises(FrozenInstanceError):
        value.population = 101  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snap.age_cohorts = ()  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_demographic_schemas_have_no_mutable_annotations() -> None:
    for schema in (AgeCohortPopulation, DemographicSnapshot):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def test_population_share_must_match_population_over_total_population() -> None:
    with pytest.raises(ValueError):
        snapshot(
            total_population=metric(1000, "people"),
            age_cohorts=(
                cohort(
                    population=100,
                    population_share=0.90,
                ),
            ),
        )


def test_partial_cohort_set_does_not_need_to_sum_to_one() -> None:
    value = snapshot(
        total_population=metric(1000, "people"),
        age_cohorts=(
            cohort(
                population=100,
                population_share=0.1,
            ),
        ),
    )
    assert sum(item.population_share for item in value.age_cohorts) == 0.1


def test_overlapping_age_intervals_rejected() -> None:
    with pytest.raises(ValueError):
        snapshot(
            total_population=metric(1000, "people"),
            age_cohorts=(
                cohort(
                    cohort_id="age_18_29",
                    age_min_inclusive=18,
                    age_max_exclusive=30,
                    population=100,
                    population_share=0.1,
                ),
                cohort(
                    cohort_id="age_25_34",
                    age_min_inclusive=25,
                    age_max_exclusive=35,
                    population=100,
                    population_share=0.1,
                ),
            ),
        )


def test_duplicate_age_interval_with_different_id_rejected() -> None:
    with pytest.raises(ValueError):
        snapshot(
            total_population=metric(1000, "people"),
            age_cohorts=(
                cohort(
                    cohort_id="age_bucket_a",
                    population=100,
                    population_share=0.1,
                ),
                cohort(
                    cohort_id="age_bucket_b",
                    population=100,
                    population_share=0.1,
                ),
            ),
        )


def test_age_cohorts_must_use_deterministic_interval_order() -> None:
    older = cohort(
        cohort_id="age_25_34",
        age_min_inclusive=25,
        age_max_exclusive=35,
        population=100,
        population_share=0.1,
    )
    younger = cohort(
        cohort_id="age_18_24",
        age_min_inclusive=18,
        age_max_exclusive=25,
        population=100,
        population_share=0.1,
    )
    with pytest.raises(ValueError):
        snapshot(
            total_population=metric(1000, "people"),
            age_cohorts=(older, younger),
        )


def test_demographic_snapshot_availability_tracks_primary_total_population() -> None:
    missing_total = MetricValue(
        value=None,
        unit="people",
        availability=AvailabilityState.MISSING,
        data_quality=DataQualityState.MISSING,
        score_eligibility=ScoreEligibility.INELIGIBLE,
        calibration_state=CalibrationState.CALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(),
        method_version="metric-v1",
    )

    with pytest.raises(ValueError):
        snapshot(
            availability=AvailabilityState.MISSING,
            data_quality=DataQualityState.MISSING,
            total_population=metric(400, "people"),
        )

    value = snapshot(
        availability=AvailabilityState.MISSING,
        data_quality=DataQualityState.MISSING,
        total_population=missing_total,
        age_cohorts=(),
    )
    assert value.availability is AvailabilityState.MISSING
