from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .hashing import semantic_hash
from .measurement import BenchmarkCellMeasurement, BenchmarkMetricCompatibility
from .population import BenchmarkMeasurementSet


class BenchmarkDistributionState(str, Enum):
    AVAILABLE = "AVAILABLE"
    EMPTY_ELIGIBLE_POPULATION = "EMPTY_ELIGIBLE_POPULATION"
    NO_NUMERIC_OBSERVATIONS = "NO_NUMERIC_OBSERVATIONS"
    INCOMPATIBLE_MEASUREMENT_LINEAGE = "INCOMPATIBLE_MEASUREMENT_LINEAGE"


def _compatibility(attempt: BenchmarkCellMeasurement) -> BenchmarkMetricCompatibility:
    return BenchmarkMetricCompatibility(attempt.measurement)


def _numeric_exclusion_reason(attempt: BenchmarkCellMeasurement) -> str | None:
    measurement = attempt.measurement
    value = measurement.metric_value.value
    if value is None:
        if measurement.reason_codes:
            return measurement.reason_codes[0]
        return f"availability_{measurement.metric_value.availability.value}"
    if measurement.metric_value.availability.value != "available":
        return f"availability_{measurement.metric_value.availability.value}"
    if measurement.metric_value.score_eligibility.value != "eligible":
        return f"score_eligibility_{measurement.metric_value.score_eligibility.value}"
    if not math.isfinite(float(value)):
        raise ValueError("canonical benchmark numeric candidate must be finite")
    return None


@dataclass(frozen=True, slots=True)
class BenchmarkCoverage:
    measurement_set: BenchmarkMeasurementSet

    def __post_init__(self) -> None:
        if not isinstance(self.measurement_set, BenchmarkMeasurementSet):
            raise TypeError("measurement_set must be BenchmarkMeasurementSet")
        self.semantic_record()

    @property
    def eligible_cell_count(self) -> int:
        return len(self.measurement_set.frame.eligible_cell_ids)

    @property
    def attempt_count(self) -> int:
        return len(self.measurement_set.attempts)

    @property
    def numeric_candidate_attempts(self):
        return tuple(a for a in self.measurement_set.attempts if _numeric_exclusion_reason(a) is None)

    @property
    def non_numeric_attempts(self):
        return tuple(a for a in self.measurement_set.attempts if _numeric_exclusion_reason(a) is not None)

    @property
    def compatibility_identities(self) -> tuple[str, ...]:
        return tuple(sorted({_compatibility(a).identity_id for a in self.measurement_set.attempts}))

    @property
    def has_compatibility_conflict(self) -> bool:
        return len(self.compatibility_identities) > 1

    @property
    def numeric_included_attempts(self):
        return () if self.has_compatibility_conflict else self.numeric_candidate_attempts

    @property
    def incompatible_numeric_attempts(self):
        return self.numeric_candidate_attempts if self.has_compatibility_conflict else ()

    @property
    def numeric_candidate_count(self) -> int:
        return len(self.numeric_candidate_attempts)

    @property
    def numeric_included_count(self) -> int:
        return len(self.numeric_included_attempts)

    @property
    def non_numeric_count(self) -> int:
        return len(self.non_numeric_attempts)

    @property
    def incompatible_numeric_count(self) -> int:
        return len(self.incompatible_numeric_attempts)

    @property
    def excluded_count(self) -> int:
        return self.non_numeric_count + self.incompatible_numeric_count

    @property
    def reason_counts(self) -> tuple[tuple[str, int], ...]:
        counts: dict[str, int] = {}
        for attempt in self.non_numeric_attempts:
            reason = _numeric_exclusion_reason(attempt)
            counts[reason] = counts.get(reason, 0) + 1
        if self.has_compatibility_conflict:
            counts["measurement_compatibility_mismatch"] = self.incompatible_numeric_count
        return tuple(sorted(counts.items()))

    @property
    def coverage_id(self) -> str:
        return semantic_hash(self.semantic_record())

    def semantic_record(self) -> dict[str, object]:
        if self.attempt_count != self.eligible_cell_count:
            raise ValueError("coverage attempt count must equal eligible-cell count")
        if self.numeric_included_count + self.excluded_count != self.attempt_count:
            raise ValueError("coverage accounting does not reconcile to complete attempt population")
        return {
            "measurement_set_id": self.measurement_set.measurement_set_id,
            "eligible_cell_count": self.eligible_cell_count,
            "attempt_count": self.attempt_count,
            "numeric_candidate_count": self.numeric_candidate_count,
            "numeric_included_count": self.numeric_included_count,
            "non_numeric_count": self.non_numeric_count,
            "incompatible_numeric_count": self.incompatible_numeric_count,
            "excluded_count": self.excluded_count,
            "reason_counts": self.reason_counts,
            "compatibility_identities": self.compatibility_identities,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkObservation:
    attempt: BenchmarkCellMeasurement

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, BenchmarkCellMeasurement):
            raise TypeError("attempt must be BenchmarkCellMeasurement")
        reason = _numeric_exclusion_reason(self.attempt)
        if reason is not None:
            raise ValueError(f"benchmark observation requires canonical numeric measurement: {reason}")

    @property
    def value(self) -> int | float:
        value = self.attempt.measurement.metric_value.value
        if value is None:
            raise ValueError("numeric benchmark observation cannot have value=None")
        return value

    @property
    def unit(self) -> str:
        return self.attempt.measurement.metric_value.unit

    @property
    def compatibility(self) -> BenchmarkMetricCompatibility:
        return _compatibility(self.attempt)

    @property
    def observation_id(self) -> str:
        return semantic_hash({
            "attempt_id": self.attempt.attempt_id,
            "frame_cell_id": self.attempt.frame_cell.cell_id,
            "measurement_id": self.attempt.measurement.measurement_id,
            "compatibility_id": self.compatibility.identity_id,
            "value": self.value,
            "unit": self.unit,
        })


@dataclass(frozen=True, slots=True)
class BenchmarkDistributionArtifact:
    measurement_set: BenchmarkMeasurementSet

    def __post_init__(self) -> None:
        if not isinstance(self.measurement_set, BenchmarkMeasurementSet):
            raise TypeError("measurement_set must be BenchmarkMeasurementSet")
        self.coverage.semantic_record()

    @property
    def coverage(self) -> BenchmarkCoverage:
        return BenchmarkCoverage(self.measurement_set)

    @property
    def state(self) -> BenchmarkDistributionState:
        if self.coverage.eligible_cell_count == 0:
            return BenchmarkDistributionState.EMPTY_ELIGIBLE_POPULATION
        if self.coverage.has_compatibility_conflict:
            return BenchmarkDistributionState.INCOMPATIBLE_MEASUREMENT_LINEAGE
        if self.coverage.numeric_included_count == 0:
            return BenchmarkDistributionState.NO_NUMERIC_OBSERVATIONS
        return BenchmarkDistributionState.AVAILABLE

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return {
            BenchmarkDistributionState.EMPTY_ELIGIBLE_POPULATION: ("empty_eligible_benchmark_population",),
            BenchmarkDistributionState.INCOMPATIBLE_MEASUREMENT_LINEAGE: ("measurement_compatibility_mismatch",),
            BenchmarkDistributionState.NO_NUMERIC_OBSERVATIONS: ("no_numeric_benchmark_observations",),
            BenchmarkDistributionState.AVAILABLE: (),
        }[self.state]

    @property
    def compatibility(self) -> BenchmarkMetricCompatibility | None:
        if self.coverage.has_compatibility_conflict or not self.measurement_set.attempts:
            return None
        return _compatibility(self.measurement_set.attempts[0])

    @property
    def observations(self) -> tuple[BenchmarkObservation, ...]:
        return tuple(BenchmarkObservation(a) for a in self.coverage.numeric_included_attempts)

    @property
    def distribution_id(self) -> str:
        return semantic_hash({
            "measurement_set_id": self.measurement_set.measurement_set_id,
            "measurement_policy_id": self.measurement_set.measurement_policy.identity_id,
            "frame_id": self.measurement_set.frame.frame_id,
            "metric_definition_id": self.measurement_set.definition.identity_id,
            "metric_derivation_policy_id": self.measurement_set.derivation_policy.identity_id,
            "measurement_precision_policy_id": self.measurement_set.precision_policy.identity_id,
            "unit": self.measurement_set.unit,
            "state": self.state.value,
            "reason_codes": self.reason_codes,
            "coverage_id": self.coverage.coverage_id,
            "compatibility_id": self.compatibility.identity_id if self.compatibility else None,
            "observation_ids": [o.observation_id for o in self.observations],
        })


def build_benchmark_distribution(measurement_set: BenchmarkMeasurementSet) -> BenchmarkDistributionArtifact:
    return BenchmarkDistributionArtifact(measurement_set)
