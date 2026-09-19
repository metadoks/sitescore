"""Immutable demographic snapshot contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data.enums import AvailabilityState, DataQualityState
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.geography import GeographyRef
from sitescore_data.validation import (
    require_aware_datetime,
    require_bounded_number,
    require_canonical_identifier,
    require_nonnegative_number,
)


def _require_unique_source_refs(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError("source_refs must be a tuple")
    for value in values:
        require_canonical_identifier(value, field_name="source_refs item")
    if len(set(values)) != len(values):
        raise ValueError("source_refs must not contain duplicates")
    return values


@dataclass(frozen=True, slots=True)
class AgeCohortPopulation:
    """One deterministic demographic age bucket with no sector-affinity meaning."""

    cohort_id: str
    age_min_inclusive: int
    age_max_exclusive: int | None
    population: int
    population_share: float

    def __post_init__(self) -> None:
        require_canonical_identifier(self.cohort_id, field_name="cohort_id")
        require_nonnegative_number(
            self.age_min_inclusive,
            field_name="age_min_inclusive",
        )
        if not isinstance(self.age_min_inclusive, int) or isinstance(
            self.age_min_inclusive, bool
        ):
            raise TypeError("age_min_inclusive must be an int")

        if self.age_max_exclusive is not None:
            require_nonnegative_number(
                self.age_max_exclusive,
                field_name="age_max_exclusive",
            )
            if not isinstance(self.age_max_exclusive, int) or isinstance(
                self.age_max_exclusive, bool
            ):
                raise TypeError("age_max_exclusive must be an int or None")
            if self.age_max_exclusive <= self.age_min_inclusive:
                raise ValueError(
                    "age_max_exclusive must be greater than age_min_inclusive"
                )

        require_nonnegative_number(self.population, field_name="population")
        if not isinstance(self.population, int) or isinstance(self.population, bool):
            raise TypeError("population must be an int")
        require_bounded_number(
            self.population_share,
            low=0.0,
            high=1.0,
            field_name="population_share",
        )


@dataclass(frozen=True, slots=True)
class DemographicSnapshot:
    """Provider-neutral demographic evidence for one geography."""

    geography_ref: GeographyRef
    total_population: MetricValue
    age_cohorts: tuple[AgeCohortPopulation, ...]
    household_income: MetricValue
    source_refs: tuple[str, ...]
    availability: AvailabilityState
    data_quality: DataQualityState
    generated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.geography_ref, GeographyRef):
            raise TypeError("geography_ref must be a GeographyRef")
        if not isinstance(self.total_population, MetricValue):
            raise TypeError("total_population must be a MetricValue")
        if not isinstance(self.household_income, MetricValue):
            raise TypeError("household_income must be a MetricValue")
        if not isinstance(self.age_cohorts, tuple):
            raise TypeError("age_cohorts must be a tuple")
        for cohort in self.age_cohorts:
            if not isinstance(cohort, AgeCohortPopulation):
                raise TypeError("age_cohorts must contain AgeCohortPopulation values")
        cohort_ids = tuple(cohort.cohort_id for cohort in self.age_cohorts)
        if len(set(cohort_ids)) != len(cohort_ids):
            raise ValueError("age_cohorts must not contain duplicate cohort_id values")

        canonical_order = tuple(
            sorted(
                self.age_cohorts,
                key=lambda cohort: (
                    cohort.age_min_inclusive,
                    float("inf")
                    if cohort.age_max_exclusive is None
                    else cohort.age_max_exclusive,
                    cohort.cohort_id,
                ),
            )
        )
        if self.age_cohorts != canonical_order:
            raise ValueError(
                "age_cohorts must be ordered deterministically by age interval"
            )

        for previous, current in zip(
            self.age_cohorts,
            self.age_cohorts[1:],
            strict=False,
        ):
            if previous.age_max_exclusive is None:
                raise ValueError(
                    "an open-ended age cohort must be the final cohort"
                )
            if current.age_min_inclusive < previous.age_max_exclusive:
                raise ValueError("age_cohort intervals must not overlap")

        _require_unique_source_refs(self.source_refs)
        if not isinstance(self.availability, AvailabilityState):
            raise TypeError("availability must be an AvailabilityState")
        if not isinstance(self.data_quality, DataQualityState):
            raise TypeError("data_quality must be a DataQualityState")

        if self.availability is not self.total_population.availability:
            raise ValueError(
                "DemographicSnapshot availability must match "
                "total_population availability"
            )

        if self.availability is AvailabilityState.AVAILABLE:
            if self.data_quality not in {
                DataQualityState.FULL,
                DataQualityState.DEGRADED,
            }:
                raise ValueError(
                    "AVAILABLE demographic snapshots require FULL or DEGRADED data quality"
                )
            if not self.source_refs:
                raise ValueError(
                    "AVAILABLE demographic snapshots require at least one source_ref"
                )
        elif self.availability is AvailabilityState.NOT_APPLICABLE:
            if self.data_quality is not DataQualityState.NOT_APPLICABLE:
                raise ValueError(
                    "NOT_APPLICABLE demographic snapshots require NOT_APPLICABLE data quality"
                )
        elif self.availability in {
            AvailabilityState.MISSING,
            AvailabilityState.UNAVAILABLE,
        }:
            if self.data_quality is not DataQualityState.MISSING:
                raise ValueError(
                    "MISSING/UNAVAILABLE demographic snapshots require MISSING data quality"
                )
        elif self.availability is AvailabilityState.UNKNOWN:
            if self.data_quality not in {
                DataQualityState.DEGRADED,
                DataQualityState.MISSING,
            }:
                raise ValueError(
                    "UNKNOWN demographic snapshots require DEGRADED or MISSING data quality"
                )

        if self.total_population.value is not None:
            require_nonnegative_number(
                self.total_population.value,
                field_name="total_population.value",
            )
            total_population_value = self.total_population.value
            cohort_population_total = sum(
                cohort.population for cohort in self.age_cohorts
            )
            if cohort_population_total > total_population_value:
                raise ValueError(
                    "age cohort populations must not exceed total_population"
                )
            for cohort in self.age_cohorts:
                expected_share = (
                    0.0
                    if total_population_value == 0
                    else cohort.population / total_population_value
                )
                if cohort.population_share != expected_share:
                    raise ValueError(
                        "population_share must equal cohort.population / "
                        "total_population for canonical demographic cohorts"
                    )

        metric_refs = set(self.total_population.source_refs) | set(
            self.household_income.source_refs
        )
        missing_refs = metric_refs - set(self.source_refs)
        if missing_refs:
            raise ValueError(
                "source_refs must include all total_population and household_income source refs"
            )

        require_aware_datetime(self.generated_at, field_name="generated_at")
