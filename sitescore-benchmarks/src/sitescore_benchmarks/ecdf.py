from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import math

from .distribution import BenchmarkDistributionArtifact, BenchmarkDistributionState
from .hashing import semantic_hash


Numeric = int | float


def _canonical_ratio(value: Numeric) -> tuple[int, int]:
    if isinstance(value, bool):
        raise TypeError("bool is not a canonical ECDF numeric value")
    if isinstance(value, int):
        numerator, denominator = value, 1
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("ECDF numeric value must be finite")
        numerator, denominator = value.as_integer_ratio()
    else:
        raise TypeError("ECDF numeric value must be a finite int or float")

    if numerator == 0:
        return (0, 1)
    divisor = math.gcd(abs(numerator), denominator)
    numerator //= divisor
    denominator //= divisor
    if denominator < 0:
        numerator = -numerator
        denominator = -denominator
    return (numerator, denominator)


def _fraction(value: Numeric) -> Fraction:
    numerator, denominator = _canonical_ratio(value)
    return Fraction(numerator, denominator)


def _sorted_canonical_ratios(values: tuple[Numeric, ...]) -> tuple[tuple[int, int], ...]:
    ratios = tuple(_canonical_ratio(value) for value in values)
    return tuple(sorted(ratios, key=lambda ratio: Fraction(ratio[0], ratio[1])))


@dataclass(frozen=True, slots=True)
class NumericComparisonPolicy:
    policy_id: str
    policy_version: str
    equality_rule: str
    ordering_rule: str
    tolerance_rule: str

    @property
    def identity_id(self) -> str:
        return semantic_hash(self.semantic_record())

    def semantic_record(self) -> dict[str, str]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "equality_rule": self.equality_rule,
            "ordering_rule": self.ordering_rule,
            "tolerance_rule": self.tolerance_rule,
        }


EXACT_NUMERIC_COMPARISON_V1 = NumericComparisonPolicy(
    policy_id="ecdf_numeric_comparison",
    policy_version="1.0",
    equality_rule="EXACT_CANONICAL_NUMERIC_VALUE",
    ordering_rule="EXACT_CANONICAL_NUMERIC_ORDER",
    tolerance_rule="NO_TOLERANCE_NO_ROUNDING_NO_QUANTIZATION",
)


@dataclass(frozen=True, slots=True)
class MidEcdfPolicy:
    policy_id: str
    policy_version: str
    comparison_policy: NumericComparisonPolicy
    formula_rule: str
    interpolation_rule: str

    def __post_init__(self) -> None:
        if not isinstance(self.comparison_policy, NumericComparisonPolicy):
            raise TypeError("comparison_policy must be NumericComparisonPolicy")

    @property
    def identity_id(self) -> str:
        return semantic_hash(self.semantic_record())

    def semantic_record(self) -> dict[str, str]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "comparison_policy_id": self.comparison_policy.identity_id,
            "formula_rule": self.formula_rule,
            "interpolation_rule": self.interpolation_rule,
        }


MID_ECDF_V1 = MidEcdfPolicy(
    policy_id="mid_ecdf",
    policy_version="1.0",
    comparison_policy=EXACT_NUMERIC_COMPARISON_V1,
    formula_rule="BELOW_PLUS_HALF_EQUAL_DIVIDED_BY_N",
    interpolation_rule="STEP_FUNCTION_NO_INTERPOLATION",
)


def _require_supported_comparison_policy(policy: NumericComparisonPolicy) -> None:
    if not isinstance(policy, NumericComparisonPolicy):
        raise TypeError("comparison_policy must be NumericComparisonPolicy")
    if policy.identity_id != EXACT_NUMERIC_COMPARISON_V1.identity_id:
        raise ValueError("unsupported ECDF numeric comparison semantics")


def _require_supported_ecdf_policy(policy: MidEcdfPolicy) -> None:
    if not isinstance(policy, MidEcdfPolicy):
        raise TypeError("policy must be MidEcdfPolicy")
    if policy.identity_id != MID_ECDF_V1.identity_id:
        raise ValueError("unsupported mid-ECDF semantics")


@dataclass(frozen=True, slots=True)
class CanonicalNumericSample:
    values: tuple[Numeric, ...]
    comparison_policy: NumericComparisonPolicy = EXACT_NUMERIC_COMPARISON_V1

    def __post_init__(self) -> None:
        if not isinstance(self.values, tuple):
            raise TypeError("values must be tuple")
        _require_supported_comparison_policy(self.comparison_policy)
        for value in self.values:
            _canonical_ratio(value)

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def canonical_values(self) -> tuple[tuple[int, int], ...]:
        return _sorted_canonical_ratios(self.values)

    @property
    def sample_id(self) -> str:
        return semantic_hash(self.semantic_record())

    def semantic_record(self) -> dict[str, object]:
        return {
            "comparison_policy_id": self.comparison_policy.identity_id,
            "canonical_values": self.canonical_values,
            "count": self.count,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkNumericSample:
    distribution: BenchmarkDistributionArtifact
    comparison_policy: NumericComparisonPolicy = EXACT_NUMERIC_COMPARISON_V1

    def __post_init__(self) -> None:
        if not isinstance(self.distribution, BenchmarkDistributionArtifact):
            raise TypeError("distribution must be BenchmarkDistributionArtifact")
        _require_supported_comparison_policy(self.comparison_policy)
        if self.distribution.state is not BenchmarkDistributionState.AVAILABLE:
            raise ValueError(
                "benchmark numeric sample requires AVAILABLE benchmark distribution; "
                f"state={self.distribution.state.value}"
            )
        if not self.distribution.observations:
            raise ValueError("AVAILABLE benchmark distribution must contain numeric observations")
        self.numeric_sample.semantic_record()

    @property
    def numeric_sample(self) -> CanonicalNumericSample:
        return CanonicalNumericSample(
            tuple(observation.value for observation in self.distribution.observations),
            self.comparison_policy,
        )

    @property
    def observation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(observation.observation_id for observation in self.distribution.observations))

    @property
    def sample_id(self) -> str:
        return semantic_hash({
            "distribution_id": self.distribution.distribution_id,
            "comparison_policy_id": self.comparison_policy.identity_id,
            "numeric_sample_id": self.numeric_sample.sample_id,
            "observation_ids": self.observation_ids,
        })


class MidEcdfState(str, Enum):
    AVAILABLE = "AVAILABLE"
    EMPTY_SAMPLE = "EMPTY_SAMPLE"


@dataclass(frozen=True, slots=True)
class MidEcdfEvaluation:
    sample: CanonicalNumericSample
    query: Numeric
    policy: MidEcdfPolicy = MID_ECDF_V1

    def __post_init__(self) -> None:
        if not isinstance(self.sample, CanonicalNumericSample):
            raise TypeError("sample must be CanonicalNumericSample")
        _require_supported_ecdf_policy(self.policy)
        if self.sample.comparison_policy.identity_id != self.policy.comparison_policy.identity_id:
            raise ValueError("sample and mid-ECDF comparison policies must match")
        _canonical_ratio(self.query)

    @property
    def state(self) -> MidEcdfState:
        return MidEcdfState.EMPTY_SAMPLE if self.sample.count == 0 else MidEcdfState.AVAILABLE

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return ("empty_numeric_sample",) if self.state is MidEcdfState.EMPTY_SAMPLE else ()

    @property
    def n(self) -> int:
        return self.sample.count

    @property
    def below_count(self) -> int:
        query = _fraction(self.query)
        return sum(
            Fraction(numerator, denominator) < query
            for numerator, denominator in self.sample.canonical_values
        )

    @property
    def equal_count(self) -> int:
        query_ratio = _canonical_ratio(self.query)
        return sum(ratio == query_ratio for ratio in self.sample.canonical_values)

    @property
    def percentile(self) -> float | None:
        if self.state is MidEcdfState.EMPTY_SAMPLE:
            return None
        numerator = 2 * self.below_count + self.equal_count
        denominator = 2 * self.n
        value = numerator / denominator
        if not 0.0 <= value <= 1.0:
            raise ValueError("mid-ECDF percentile must be within [0, 1]")
        return value

    @property
    def evaluation_id(self) -> str:
        return semantic_hash({
            "sample_id": self.sample.sample_id,
            "policy_id": self.policy.identity_id,
            "comparison_policy_id": self.policy.comparison_policy.identity_id,
            "query": _canonical_ratio(self.query),
            "state": self.state.value,
            "reason_codes": self.reason_codes,
            "n": self.n,
            "below_count": self.below_count,
            "equal_count": self.equal_count,
            "percentile": self.percentile,
        })


@dataclass(frozen=True, slots=True)
class BenchmarkMidEcdfEvaluation:
    benchmark_sample: BenchmarkNumericSample
    query: Numeric
    policy: MidEcdfPolicy = MID_ECDF_V1

    def __post_init__(self) -> None:
        if not isinstance(self.benchmark_sample, BenchmarkNumericSample):
            raise TypeError("benchmark_sample must be BenchmarkNumericSample")
        _require_supported_ecdf_policy(self.policy)
        if self.benchmark_sample.comparison_policy.identity_id != self.policy.comparison_policy.identity_id:
            raise ValueError("benchmark sample and mid-ECDF comparison policies must match")
        _canonical_ratio(self.query)
        self.evaluation.evaluation_id

    @property
    def evaluation(self) -> MidEcdfEvaluation:
        return MidEcdfEvaluation(self.benchmark_sample.numeric_sample, self.query, self.policy)

    @property
    def state(self) -> MidEcdfState:
        return self.evaluation.state

    @property
    def n(self) -> int:
        return self.evaluation.n

    @property
    def below_count(self) -> int:
        return self.evaluation.below_count

    @property
    def equal_count(self) -> int:
        return self.evaluation.equal_count

    @property
    def percentile(self) -> float | None:
        return self.evaluation.percentile

    @property
    def evaluation_id(self) -> str:
        return semantic_hash({
            "benchmark_sample_id": self.benchmark_sample.sample_id,
            "distribution_id": self.benchmark_sample.distribution.distribution_id,
            "numeric_evaluation_id": self.evaluation.evaluation_id,
        })


def build_numeric_sample(
    values: tuple[Numeric, ...],
    *,
    comparison_policy: NumericComparisonPolicy = EXACT_NUMERIC_COMPARISON_V1,
) -> CanonicalNumericSample:
    return CanonicalNumericSample(values, comparison_policy)


def build_benchmark_numeric_sample(
    distribution: BenchmarkDistributionArtifact,
    *,
    comparison_policy: NumericComparisonPolicy = EXACT_NUMERIC_COMPARISON_V1,
) -> BenchmarkNumericSample:
    return BenchmarkNumericSample(distribution, comparison_policy)


def evaluate_mid_ecdf(
    sample: CanonicalNumericSample,
    query: Numeric,
    *,
    policy: MidEcdfPolicy = MID_ECDF_V1,
) -> MidEcdfEvaluation:
    return MidEcdfEvaluation(sample, query, policy)


def evaluate_benchmark_mid_ecdf(
    distribution: BenchmarkDistributionArtifact,
    query: Numeric,
    *,
    policy: MidEcdfPolicy = MID_ECDF_V1,
) -> BenchmarkMidEcdfEvaluation:
    sample = build_benchmark_numeric_sample(
        distribution,
        comparison_policy=policy.comparison_policy,
    )
    return BenchmarkMidEcdfEvaluation(sample, query, policy)
