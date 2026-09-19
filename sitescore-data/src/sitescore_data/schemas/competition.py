"""Immutable competition observation, curve, and snapshot contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from sitescore_data.enums import AvailabilityState, DataQualityState
from sitescore_data.schemas.benchmarks import BenchmarkReference
from sitescore_data.validation import (
    require_aware_datetime,
    require_canonical_identifier,
    require_finite_number,
    require_nonnegative_number,
    require_positive_number,
)


def _require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    return value


def _require_unique_source_refs(values: tuple[str, ...], *, field_name: str = "source_refs") -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for value in values:
        require_canonical_identifier(value, field_name=f"{field_name} item")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


def _require_snapshot_quality(
    availability: AvailabilityState,
    data_quality: DataQualityState,
    *,
    snapshot_name: str,
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
        allowed_text = ", ".join(sorted(item.value for item in allowed))
        raise ValueError(
            f"{snapshot_name} availability={availability.value} requires "
            f"data quality in: {allowed_text}"
        )


@dataclass(frozen=True, slots=True)
class CompetitionObservation:
    """One competition measurement at one explicitly identified catchment scale."""

    scale_id: str
    travel_mode: str
    catchment_semantics: str
    travel_cost: float
    travel_cost_unit: str
    competitor_count: int
    catchment_area_km2: float
    competitor_density_per_km2: float
    source_refs: tuple[str, ...]
    method_version: str

    def __post_init__(self) -> None:
        require_canonical_identifier(self.scale_id, field_name="scale_id")
        require_canonical_identifier(self.travel_mode, field_name="travel_mode")
        require_canonical_identifier(
            self.catchment_semantics,
            field_name="catchment_semantics",
        )
        require_positive_number(self.travel_cost, field_name="travel_cost")
        _require_nonempty_text(self.travel_cost_unit, field_name="travel_cost_unit")
        require_nonnegative_number(self.competitor_count, field_name="competitor_count")
        if not isinstance(self.competitor_count, int) or isinstance(
            self.competitor_count, bool
        ):
            raise TypeError("competitor_count must be an int")
        require_positive_number(self.catchment_area_km2, field_name="catchment_area_km2")
        require_nonnegative_number(
            self.competitor_density_per_km2,
            field_name="competitor_density_per_km2",
        )
        expected_density = self.competitor_count / self.catchment_area_km2
        if not math.isclose(
            self.competitor_density_per_km2,
            expected_density,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "competitor_density_per_km2 must equal "
                "competitor_count / catchment_area_km2"
            )
        _require_unique_source_refs(self.source_refs)
        if not self.source_refs:
            raise ValueError("CompetitionObservation requires at least one source_ref")
        _require_nonempty_text(self.method_version, field_name="method_version")


@dataclass(frozen=True, slots=True)
class CompetitionCurve:
    """Deterministically ordered multi-scale competition observations."""

    observations: tuple[CompetitionObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be a tuple")
        if len(self.observations) < 2:
            raise ValueError("CompetitionCurve requires at least two scale observations")
        for observation in self.observations:
            if not isinstance(observation, CompetitionObservation):
                raise TypeError(
                    "observations must contain CompetitionObservation values"
                )
        scale_ids = tuple(observation.scale_id for observation in self.observations)
        if len(set(scale_ids)) != len(scale_ids):
            raise ValueError("CompetitionCurve scale_id values must be unique")
        expected_order = tuple(
            sorted(
                self.observations,
                key=lambda item: (item.travel_cost, item.scale_id),
            )
        )
        if self.observations != expected_order:
            raise ValueError(
                "CompetitionCurve observations must be ordered by "
                "travel_cost then scale_id"
            )


@dataclass(frozen=True, slots=True)
class CompetitionSnapshot:
    """Competition evidence and optional benchmark identity for one site."""

    snapshot_id: str
    measurement_definition_id: str
    curve: CompetitionCurve | None
    benchmark_ref: BenchmarkReference | None
    source_refs: tuple[str, ...]
    availability: AvailabilityState
    data_quality: DataQualityState
    generated_at: datetime

    def __post_init__(self) -> None:
        require_canonical_identifier(self.snapshot_id, field_name="snapshot_id")
        require_canonical_identifier(
            self.measurement_definition_id,
            field_name="measurement_definition_id",
        )
        if self.curve is not None and not isinstance(self.curve, CompetitionCurve):
            raise TypeError("curve must be a CompetitionCurve or None")
        if self.benchmark_ref is not None and not isinstance(
            self.benchmark_ref, BenchmarkReference
        ):
            raise TypeError("benchmark_ref must be a BenchmarkReference or None")
        _require_unique_source_refs(self.source_refs)
        _require_snapshot_quality(
            self.availability,
            self.data_quality,
            snapshot_name="CompetitionSnapshot",
        )
        if self.availability is AvailabilityState.AVAILABLE:
            if self.curve is None:
                raise ValueError("AVAILABLE CompetitionSnapshot requires a curve")
            if not self.source_refs:
                raise ValueError(
                    "AVAILABLE CompetitionSnapshot requires at least one source_ref"
                )
        elif self.curve is not None:
            raise ValueError(
                "non-AVAILABLE CompetitionSnapshot must not contain a curve"
            )

        nested_refs: set[str] = set()
        if self.curve is not None:
            for observation in self.curve.observations:
                nested_refs.update(observation.source_refs)
        if self.benchmark_ref is not None:
            nested_refs.update(self.benchmark_ref.source_refs)
        missing_refs = nested_refs - set(self.source_refs)
        if missing_refs:
            raise ValueError(
                "source_refs must include all curve and benchmark source refs"
            )
        require_aware_datetime(self.generated_at, field_name="generated_at")
