"""Immutable derived-metric and normalized-feature contracts.

This module defines only typed feature surfaces.  It does not implement
normalization, calibration, category aggregation, core adapters, or readiness
validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data.enums import CalibrationState
from sitescore_data.schemas.benchmarks import BenchmarkReference
from sitescore_data.schemas.common import MetricValue
from sitescore_data.validation import (
    SectorKey,
    require_aware_datetime,
    require_bounded_number,
    require_canonical_identifier,
)


def _require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    return value


def _require_optional_nonempty_text(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return _require_nonempty_text(value, field_name=field_name)


def _require_unique_source_refs(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError("source_refs must be a tuple")
    for value in values:
        require_canonical_identifier(
            value,
            field_name="source_refs item",
        )
    if len(set(values)) != len(values):
        raise ValueError("source_refs must not contain duplicates")
    return values


def _require_metric(value: MetricValue, *, field_name: str) -> MetricValue:
    if not isinstance(value, MetricValue):
        raise TypeError(f"{field_name} must be a MetricValue")
    return value


def _require_metric_source_coverage(
    metrics: tuple[MetricValue, ...],
    source_refs: tuple[str, ...],
) -> None:
    nested_refs: set[str] = set()
    for metric in metrics:
        nested_refs.update(metric.source_refs)
    if nested_refs - set(source_refs):
        raise ValueError(
            "source_refs must include all nested MetricValue source refs"
        )


def _require_normalized_score(
    metric: MetricValue,
    *,
    field_name: str,
) -> None:
    _require_metric(metric, field_name=field_name)
    if metric.unit != "score_0_100":
        raise ValueError(
            f'{field_name} must use MetricValue.unit="score_0_100"'
        )
    if metric.value is not None:
        require_bounded_number(
            metric.value,
            low=0.0,
            high=100.0,
            field_name=field_name,
        )


@dataclass(frozen=True, slots=True)
class DerivedLocationMetrics:
    """Provider-neutral derived measurements in real-world units.

    These are measurements/evidence, not normalized scores and not category
    scores.  Uncalibrated reductions remain state-aware ``MetricValue`` values
    rather than being silently converted to numeric scores.
    """

    walkable_population: MetricValue
    target_population_density: MetricValue
    household_income: MetricValue
    household_income_ratio: MetricValue
    competition_pressure: MetricValue
    walkable_reach_area_km2: MetricValue
    transit_service_departure_equivalents_per_hour: MetricValue
    road_reachable_area_km2: MetricValue
    parking_public_offstreet_capacity: MetricValue
    parking_legal_curb_length_m: MetricValue
    demographic_snapshot_ref: str | None
    competition_snapshot_ref: str | None
    road_snapshot_ref: str | None
    parking_snapshot_ref: str | None
    source_refs: tuple[str, ...]
    feature_contract_version: str
    generated_at: datetime

    def __post_init__(self) -> None:
        metrics = (
            self.walkable_population,
            self.target_population_density,
            self.household_income,
            self.household_income_ratio,
            self.competition_pressure,
            self.walkable_reach_area_km2,
            self.transit_service_departure_equivalents_per_hour,
            self.road_reachable_area_km2,
            self.parking_public_offstreet_capacity,
            self.parking_legal_curb_length_m,
        )

        for field_name in (
            "walkable_population",
            "target_population_density",
            "household_income",
            "household_income_ratio",
            "competition_pressure",
            "walkable_reach_area_km2",
            "transit_service_departure_equivalents_per_hour",
            "road_reachable_area_km2",
            "parking_public_offstreet_capacity",
            "parking_legal_curb_length_m",
        ):
            _require_metric(getattr(self, field_name), field_name=field_name)

        for field_name in (
            "competition_pressure",
            "road_reachable_area_km2",
        ):
            metric = getattr(self, field_name)
            if (
                metric.value is not None
                and metric.calibration_state is not CalibrationState.CALIBRATED
            ):
                raise ValueError(
                    f"{field_name} is a scalar multi-scale reduction output and "
                    "must be CALIBRATED when numeric"
                )

        _require_optional_nonempty_text(
            self.demographic_snapshot_ref,
            field_name="demographic_snapshot_ref",
        )
        _require_optional_nonempty_text(
            self.competition_snapshot_ref,
            field_name="competition_snapshot_ref",
        )
        _require_optional_nonempty_text(
            self.road_snapshot_ref,
            field_name="road_snapshot_ref",
        )
        _require_optional_nonempty_text(
            self.parking_snapshot_ref,
            field_name="parking_snapshot_ref",
        )
        _require_unique_source_refs(self.source_refs)
        _require_metric_source_coverage(metrics, self.source_refs)
        _require_nonempty_text(
            self.feature_contract_version,
            field_name="feature_contract_version",
        )
        require_aware_datetime(
            self.generated_at,
            field_name="generated_at",
        )


@dataclass(frozen=True, slots=True)
class NormalizedLocationFeatures:
    """Normalized 0..100 feature surface consumed by later aggregation logic.

    Field names intentionally mirror the frozen V1 subfeature semantics while
    remaining distinct from core configuration objects and category scores.
    """

    walkable_population_score: MetricValue
    target_population_density_score: MetricValue
    age_target_concentration_score: MetricValue
    competition_opportunity_score: MetricValue
    walkable_reach_area_score: MetricValue
    transit_access_score: MetricValue
    road_parking_access_score: MetricValue
    household_income_score: MetricValue
    competition_benchmark_ref: BenchmarkReference | None
    competition_measurement_definition_id: str | None
    competition_normalization_policy_version: str | None
    transit_benchmark_ref: BenchmarkReference | None
    transit_source_bundle_fingerprint: str | None
    transit_normalization_policy_version: str | None
    road_parking_composite_policy_version: str | None
    source_refs: tuple[str, ...]
    feature_contract_version: str
    generated_at: datetime

    def __post_init__(self) -> None:
        score_field_names = (
            "walkable_population_score",
            "target_population_density_score",
            "age_target_concentration_score",
            "competition_opportunity_score",
            "walkable_reach_area_score",
            "transit_access_score",
            "road_parking_access_score",
            "household_income_score",
        )
        metrics = tuple(getattr(self, name) for name in score_field_names)

        for field_name in score_field_names:
            _require_normalized_score(
                getattr(self, field_name),
                field_name=field_name,
            )

        age_score = self.age_target_concentration_score
        if (
            age_score.value is not None
            and age_score.calibration_state is CalibrationState.UNCALIBRATED
        ):
            if age_score.value != 50:
                raise ValueError(
                    "uncalibrated age_target_concentration_score must use "
                    "the frozen V1 neutral fallback value 50"
                )
            if age_score.is_proxy is not True:
                raise ValueError(
                    "uncalibrated age_target_concentration_score must be marked proxy"
                )
            if "age_affinity_not_calibrated" not in age_score.reason_codes:
                raise ValueError(
                    "uncalibrated age_target_concentration_score requires "
                    "age_affinity_not_calibrated reason code"
                )

        if (
            self.competition_benchmark_ref is not None
            and not isinstance(self.competition_benchmark_ref, BenchmarkReference)
        ):
            raise TypeError(
                "competition_benchmark_ref must be a BenchmarkReference or None"
            )
        if (
            self.transit_benchmark_ref is not None
            and not isinstance(self.transit_benchmark_ref, BenchmarkReference)
        ):
            raise TypeError(
                "transit_benchmark_ref must be a BenchmarkReference or None"
            )

        _require_optional_nonempty_text(
            self.competition_measurement_definition_id,
            field_name="competition_measurement_definition_id",
        )
        _require_optional_nonempty_text(
            self.competition_normalization_policy_version,
            field_name="competition_normalization_policy_version",
        )
        _require_optional_nonempty_text(
            self.transit_source_bundle_fingerprint,
            field_name="transit_source_bundle_fingerprint",
        )
        _require_optional_nonempty_text(
            self.transit_normalization_policy_version,
            field_name="transit_normalization_policy_version",
        )
        _require_optional_nonempty_text(
            self.road_parking_composite_policy_version,
            field_name="road_parking_composite_policy_version",
        )

        _require_unique_source_refs(self.source_refs)
        _require_metric_source_coverage(metrics, self.source_refs)

        nested_refs: set[str] = set()
        if self.competition_benchmark_ref is not None:
            nested_refs.update(self.competition_benchmark_ref.source_refs)
        if self.transit_benchmark_ref is not None:
            nested_refs.update(self.transit_benchmark_ref.source_refs)
        if nested_refs - set(self.source_refs):
            raise ValueError(
                "source_refs must include all benchmark reference source refs"
            )

        _require_nonempty_text(
            self.feature_contract_version,
            field_name="feature_contract_version",
        )
        require_aware_datetime(
            self.generated_at,
            field_name="generated_at",
        )


@dataclass(frozen=True, slots=True)
class ReadyCategoryScorePayload:
    """Validated data/app handoff DTO for four complete category scores.

    Checkpoint 5 validates only DTO-local invariants.  The four category values
    are not computed by ``sitescore-data``.  A future application-layer category
    aggregator, using the frozen core configuration, will supply precomputed
    values.  Checkpoint 6 may gate construction through a readiness-success
    factory, but that factory must not perform category aggregation.
    """

    sector_key: SectorKey
    demand: float
    competition: float
    accessibility: float
    economics: float
    readiness_fingerprint: str
    feature_contract_version: str
    normalization_policy_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.sector_key, SectorKey):
            raise TypeError("sector_key must be a SectorKey")

        for field_name in (
            "demand",
            "competition",
            "accessibility",
            "economics",
        ):
            require_bounded_number(
                getattr(self, field_name),
                low=0.0,
                high=100.0,
                field_name=field_name,
            )

        _require_nonempty_text(
            self.readiness_fingerprint,
            field_name="readiness_fingerprint",
        )
        _require_nonempty_text(
            self.feature_contract_version,
            field_name="feature_contract_version",
        )
        _require_nonempty_text(
            self.normalization_policy_version,
            field_name="normalization_policy_version",
        )
