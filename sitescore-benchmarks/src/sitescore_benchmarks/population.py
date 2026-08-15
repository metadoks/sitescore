from __future__ import annotations

from dataclasses import dataclass

from sitescore_metrics import (
    DEFINITIONS,
    POLICIES,
    FULL_BINARY64,
    MeasurementPrecisionPolicy,
    MetricDefinition,
    MetricDerivationPolicy,
)

from .contracts import CommercialFrame
from .hashing import semantic_hash
from .validation import text
from .measurement import (
    BENCHMARK_MEASUREMENT_DISTRIBUTION_V1,
    BenchmarkCellMeasurement,
    BenchmarkMeasurementDistributionPolicy,
    validate_canonical_metric_pair,
)


@dataclass(frozen=True, slots=True)
class BenchmarkMeasurementSet:
    frame: CommercialFrame
    definition: MetricDefinition
    derivation_policy: MetricDerivationPolicy
    precision_policy: MeasurementPrecisionPolicy
    attempts: tuple[BenchmarkCellMeasurement, ...]
    measurement_policy: BenchmarkMeasurementDistributionPolicy = BENCHMARK_MEASUREMENT_DISTRIBUTION_V1

    def __post_init__(self) -> None:
        if not isinstance(self.frame, CommercialFrame):
            raise TypeError("frame must be CommercialFrame")
        validate_canonical_metric_pair(self.definition, self.derivation_policy)
        if not isinstance(self.precision_policy, MeasurementPrecisionPolicy):
            raise TypeError("precision_policy must be MeasurementPrecisionPolicy")
        if not isinstance(self.measurement_policy, BenchmarkMeasurementDistributionPolicy):
            raise TypeError("measurement_policy must be BenchmarkMeasurementDistributionPolicy")
        if self.measurement_policy.identity_id != BENCHMARK_MEASUREMENT_DISTRIBUTION_V1.identity_id:
            raise ValueError("unsupported benchmark measurement/distribution semantics")
        if not isinstance(self.attempts, tuple):
            raise TypeError("attempts must be tuple")
        if any(not isinstance(a, BenchmarkCellMeasurement) for a in self.attempts):
            raise TypeError("attempts must contain BenchmarkCellMeasurement")

        cell_ids = tuple(a.frame_cell.cell_id for a in self.attempts)
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("duplicate benchmark measurement attempt for frame cell")
        attempt_ids = tuple(a.attempt_id for a in self.attempts)
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("duplicate benchmark measurement attempt")

        expected = set(self.frame.eligible_cell_ids)
        actual = set(cell_ids)
        if actual != expected:
            raise ValueError(
                "benchmark measurement attempts must exactly cover eligible frame cells; "
                f"missing={tuple(sorted(expected-actual))}, extra={tuple(sorted(actual-expected))}"
            )

        for attempt in self.attempts:
            if attempt.frame.frame_id != self.frame.frame_id:
                raise ValueError("benchmark measurement attempt belongs to a foreign frame")
            if attempt.measurement_policy.identity_id != self.measurement_policy.identity_id:
                raise ValueError("benchmark measurement policy mismatch")
            measurement = attempt.measurement
            if measurement.definition.identity_id != self.definition.identity_id:
                raise ValueError("benchmark measurement definition mismatch")
            if measurement.policy.identity_id != self.derivation_policy.identity_id:
                raise ValueError("benchmark measurement derivation-policy mismatch")
            if measurement.precision_policy.identity_id != self.precision_policy.identity_id:
                raise ValueError("benchmark measurement precision-policy mismatch")
            if measurement.metric_value.unit != self.definition.unit:
                raise ValueError("benchmark measurement unit mismatch")

        object.__setattr__(
            self, "attempts", tuple(sorted(self.attempts, key=lambda a: a.frame_cell.cell_id))
        )

    @property
    def metric_key(self) -> str:
        return self.definition.metric_key

    @property
    def unit(self) -> str:
        return self.definition.unit

    @property
    def measurement_set_id(self) -> str:
        return semantic_hash({
            "frame_id": self.frame.frame_id,
            "metric_definition_id": self.definition.identity_id,
            "metric_derivation_policy_id": self.derivation_policy.identity_id,
            "measurement_precision_policy_id": self.precision_policy.identity_id,
            "unit": self.unit,
            "measurement_policy_id": self.measurement_policy.identity_id,
            "attempt_ids": [a.attempt_id for a in self.attempts],
        })


def build_benchmark_measurement_set(
    frame: CommercialFrame,
    attempts: tuple[BenchmarkCellMeasurement, ...],
    *,
    metric_key: str,
    precision_policy: MeasurementPrecisionPolicy = FULL_BINARY64,
    measurement_policy: BenchmarkMeasurementDistributionPolicy = BENCHMARK_MEASUREMENT_DISTRIBUTION_V1,
) -> BenchmarkMeasurementSet:
    text(metric_key, "metric_key")
    if metric_key not in DEFINITIONS or metric_key not in POLICIES:
        raise ValueError("metric_key is not registered in the canonical V1 metric registry")
    return BenchmarkMeasurementSet(
        frame,
        DEFINITIONS[metric_key],
        POLICIES[metric_key],
        precision_policy,
        attempts,
        measurement_policy,
    )
