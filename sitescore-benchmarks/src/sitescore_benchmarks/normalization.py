from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from sitescore_metrics import DEFINITIONS, POLICIES, DerivedMetricMeasurement, SubjectKind

from .distribution import BenchmarkDistributionArtifact, BenchmarkDistributionState
from .ecdf import (
    MID_ECDF_V1,
    MidEcdfPolicy,
    BenchmarkMidEcdfEvaluation,
    evaluate_benchmark_mid_ecdf,
)
from .hashing import semantic_hash
from .measurement import BenchmarkMetricCompatibility
from .validation import text


class FeatureNormalizationDirection(str, Enum):
    HIGHER_PERCENTILE_IS_BETTER = "HIGHER_PERCENTILE_IS_BETTER"
    LOWER_PERCENTILE_IS_BETTER = "LOWER_PERCENTILE_IS_BETTER"


class FeatureNormalizationState(str, Enum):
    AVAILABLE = "AVAILABLE"
    SITE_METRIC_NOT_AVAILABLE = "SITE_METRIC_NOT_AVAILABLE"
    SITE_METRIC_NOT_ELIGIBLE = "SITE_METRIC_NOT_ELIGIBLE"
    SITE_METRIC_NOT_CALIBRATED = "SITE_METRIC_NOT_CALIBRATED"
    BENCHMARK_NOT_AVAILABLE = "BENCHMARK_NOT_AVAILABLE"
    INCOMPATIBLE = "INCOMPATIBLE"


class SiteBenchmarkCompatibilityState(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"


_DIRECT_FEATURE_MAP = {
    "walkable_population": (
        "walkable_population_score",
        FeatureNormalizationDirection.HIGHER_PERCENTILE_IS_BETTER,
    ),
    "target_population_density": (
        "target_population_density_score",
        FeatureNormalizationDirection.HIGHER_PERCENTILE_IS_BETTER,
    ),
    "competition_pressure": (
        "competition_opportunity_score",
        FeatureNormalizationDirection.LOWER_PERCENTILE_IS_BETTER,
    ),
    "walkable_reach_area_km2": (
        "walkable_reach_area_score",
        FeatureNormalizationDirection.HIGHER_PERCENTILE_IS_BETTER,
    ),
    "transit_service_departure_equivalents_per_hour": (
        "transit_access_score",
        FeatureNormalizationDirection.HIGHER_PERCENTILE_IS_BETTER,
    ),
    "household_income": (
        "household_income_score",
        FeatureNormalizationDirection.HIGHER_PERCENTILE_IS_BETTER,
    ),
}


@dataclass(frozen=True, slots=True)
class FeatureNormalizationPolicy:
    policy_id: str
    policy_version: str
    metric_key: str
    normalized_feature_key: str
    direction: FeatureNormalizationDirection
    ecdf_policy: MidEcdfPolicy = MID_ECDF_V1
    compatibility_rule: str = "EXACT_SITE_BENCHMARK_MEASUREMENT_COMPATIBILITY_V1"

    def __post_init__(self) -> None:
        for name in (
            "policy_id",
            "policy_version",
            "metric_key",
            "normalized_feature_key",
            "compatibility_rule",
        ):
            text(getattr(self, name), name)
        if not isinstance(self.direction, FeatureNormalizationDirection):
            raise TypeError("direction must be FeatureNormalizationDirection")
        if not isinstance(self.ecdf_policy, MidEcdfPolicy):
            raise TypeError("ecdf_policy must be MidEcdfPolicy")
        if self.ecdf_policy.identity_id != MID_ECDF_V1.identity_id:
            raise ValueError("unsupported feature-normalization ECDF semantics")
        if self.compatibility_rule != "EXACT_SITE_BENCHMARK_MEASUREMENT_COMPATIBILITY_V1":
            raise ValueError("unsupported site/benchmark compatibility semantics")
        if self.metric_key not in _DIRECT_FEATURE_MAP:
            raise ValueError("metric is not a direct V1 normalized feature")
        expected_feature, expected_direction = _DIRECT_FEATURE_MAP[self.metric_key]
        if self.normalized_feature_key != expected_feature:
            raise ValueError("normalized feature mapping is frozen for V1")
        if self.direction is not expected_direction:
            raise ValueError("feature normalization direction is frozen for V1")
        if self.metric_key not in DEFINITIONS or self.metric_key not in POLICIES:
            raise ValueError("normalization metric is not in canonical V1 metric registry")
        if (self.policy_id, self.policy_version) != (
            f"feature-normalization:{self.metric_key}",
            "1.0",
        ):
            raise ValueError("feature normalization policy identity is frozen for V1")

    @property
    def metric_definition(self):
        return DEFINITIONS[self.metric_key]

    @property
    def metric_derivation_policy(self):
        return POLICIES[self.metric_key]

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "metric_definition_id": self.metric_definition.identity_id,
            "metric_derivation_policy_id": self.metric_derivation_policy.identity_id,
            "normalized_feature_key": self.normalized_feature_key,
            "direction": self.direction.value,
            "ecdf_policy_id": self.ecdf_policy.identity_id,
            "numeric_comparison_policy_id": self.ecdf_policy.comparison_policy.identity_id,
            "compatibility_rule": self.compatibility_rule,
        })

    def transform_percentile(self, percentile: float) -> float:
        """Pure frozen feature transform; not a domain compatibility authority."""
        if isinstance(percentile, bool) or not isinstance(percentile, (int, float)):
            raise TypeError("percentile must be numeric")
        p = float(percentile)
        if not math.isfinite(p) or not 0.0 <= p <= 1.0:
            raise ValueError("percentile must be finite and within [0,1]")
        if self.direction is FeatureNormalizationDirection.HIGHER_PERCENTILE_IS_BETTER:
            return 100.0 * p
        return 100.0 * (1.0 - p)


def _make_policy(metric_key: str) -> FeatureNormalizationPolicy:
    feature, direction = _DIRECT_FEATURE_MAP[metric_key]
    return FeatureNormalizationPolicy(
        f"feature-normalization:{metric_key}",
        "1.0",
        metric_key,
        feature,
        direction,
    )


FEATURE_NORMALIZATION_POLICIES_V1 = {
    key: _make_policy(key) for key in _DIRECT_FEATURE_MAP
}


def feature_normalization_policy(metric_key: str) -> FeatureNormalizationPolicy:
    text(metric_key, "metric_key")
    try:
        return FEATURE_NORMALIZATION_POLICIES_V1[metric_key]
    except KeyError as exc:
        raise ValueError(
            "metric has no direct V1 feature normalization; age is a dedicated fallback and road/parking is COMB-005 gated"
        ) from exc


def _compatibility_reasons(
    site: BenchmarkMetricCompatibility,
    benchmark: BenchmarkMetricCompatibility | None,
) -> tuple[str, ...]:
    if benchmark is None:
        return ("benchmark_compatibility_unavailable",)
    reasons: list[str] = []
    if site.definition.identity_id != benchmark.definition.identity_id:
        reasons.append("metric_definition_mismatch")
    if site.derivation_policy.identity_id != benchmark.derivation_policy.identity_id:
        reasons.append("metric_derivation_policy_mismatch")
    if site.precision_policy.identity_id != benchmark.precision_policy.identity_id:
        reasons.append("measurement_precision_mismatch")
    if site.unit != benchmark.unit:
        reasons.append("unit_mismatch")
    if site.method_version != benchmark.method_version:
        reasons.append("method_version_mismatch")

    site_bundle = dict(site.source_bundle_compatibility)
    benchmark_bundle = dict(benchmark.source_bundle_compatibility)
    if site_bundle != benchmark_bundle:
        reasons.append("source_bundle_compatibility_mismatch")
        if (
            site_bundle.get("transit_source_bundle_fingerprint")
            != benchmark_bundle.get("transit_source_bundle_fingerprint")
        ) and (
            "transit_source_bundle_fingerprint" in site_bundle
            or "transit_source_bundle_fingerprint" in benchmark_bundle
        ):
            reasons.append("transit_source_bundle_mismatch")
        if (
            site_bundle.get("competition_measurement_definition_id")
            != benchmark_bundle.get("competition_measurement_definition_id")
        ) and (
            "competition_measurement_definition_id" in site_bundle
            or "competition_measurement_definition_id" in benchmark_bundle
        ):
            reasons.append("competition_measurement_definition_mismatch")
    return tuple(reasons)


@dataclass(frozen=True, slots=True)
class SiteBenchmarkCompatibility:
    site_measurement: DerivedMetricMeasurement
    benchmark_distribution: BenchmarkDistributionArtifact

    def __post_init__(self) -> None:
        if not isinstance(self.site_measurement, DerivedMetricMeasurement):
            raise TypeError("site_measurement must be DerivedMetricMeasurement")
        if self.site_measurement.subject.kind is not SubjectKind.SITE:
            raise ValueError("feature normalization requires an actual SITE measurement")
        if not isinstance(self.benchmark_distribution, BenchmarkDistributionArtifact):
            raise TypeError("benchmark_distribution must be BenchmarkDistributionArtifact")
        self.site_compatibility

    @property
    def site_compatibility(self) -> BenchmarkMetricCompatibility:
        return BenchmarkMetricCompatibility(self.site_measurement)

    @property
    def benchmark_compatibility(self) -> BenchmarkMetricCompatibility | None:
        return self.benchmark_distribution.compatibility

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return _compatibility_reasons(self.site_compatibility, self.benchmark_compatibility)

    @property
    def state(self) -> SiteBenchmarkCompatibilityState:
        return (
            SiteBenchmarkCompatibilityState.COMPATIBLE
            if not self.reason_codes
            else SiteBenchmarkCompatibilityState.INCOMPATIBLE
        )

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "site_measurement_id": self.site_measurement.measurement_id,
            "benchmark_distribution_id": self.benchmark_distribution.distribution_id,
            "site_compatibility_id": self.site_compatibility.identity_id,
            "benchmark_compatibility_id": (
                self.benchmark_compatibility.identity_id if self.benchmark_compatibility else None
            ),
            "state": self.state.value,
            "reason_codes": self.reason_codes,
        })


def _site_numeric_gate(measurement: DerivedMetricMeasurement) -> tuple[FeatureNormalizationState | None, tuple[str, ...]]:
    mv = measurement.metric_value
    value = mv.value
    if value is None or mv.availability.value != "available":
        return FeatureNormalizationState.SITE_METRIC_NOT_AVAILABLE, ("site_metric_not_available",)
    if mv.score_eligibility.value != "eligible":
        return FeatureNormalizationState.SITE_METRIC_NOT_ELIGIBLE, ("site_metric_not_eligible",)
    if mv.calibration_state.value != "calibrated":
        return FeatureNormalizationState.SITE_METRIC_NOT_CALIBRATED, ("site_metric_not_calibrated",)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return FeatureNormalizationState.SITE_METRIC_NOT_AVAILABLE, ("site_metric_not_finite_numeric",)
    return None, ()


@dataclass(frozen=True, slots=True)
class FeatureNormalizationResult:
    site_measurement: DerivedMetricMeasurement
    benchmark_distribution: BenchmarkDistributionArtifact
    policy: FeatureNormalizationPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.site_measurement, DerivedMetricMeasurement):
            raise TypeError("site_measurement must be DerivedMetricMeasurement")
        if self.site_measurement.subject.kind is not SubjectKind.SITE:
            raise ValueError("feature normalization requires SITE subject kind")
        if not isinstance(self.benchmark_distribution, BenchmarkDistributionArtifact):
            raise TypeError("benchmark_distribution must be BenchmarkDistributionArtifact")
        if not isinstance(self.policy, FeatureNormalizationPolicy):
            raise TypeError("policy must be FeatureNormalizationPolicy")
        expected = feature_normalization_policy(self.site_measurement.definition.metric_key)
        if self.policy.identity_id != expected.identity_id:
            raise ValueError("normalization policy is not canonical for the site metric")
        self.compatibility

    @property
    def compatibility(self) -> SiteBenchmarkCompatibility:
        return SiteBenchmarkCompatibility(self.site_measurement, self.benchmark_distribution)

    @property
    def state(self) -> FeatureNormalizationState:
        gate_state, _ = _site_numeric_gate(self.site_measurement)
        if gate_state is not None:
            return gate_state
        if self.benchmark_distribution.state is not BenchmarkDistributionState.AVAILABLE:
            return FeatureNormalizationState.BENCHMARK_NOT_AVAILABLE
        if self.compatibility.state is not SiteBenchmarkCompatibilityState.COMPATIBLE:
            return FeatureNormalizationState.INCOMPATIBLE
        return FeatureNormalizationState.AVAILABLE

    @property
    def reason_codes(self) -> tuple[str, ...]:
        gate_state, gate_reasons = _site_numeric_gate(self.site_measurement)
        if gate_state is not None:
            return gate_reasons
        if self.benchmark_distribution.state is not BenchmarkDistributionState.AVAILABLE:
            return (
                "benchmark_not_available",
                f"benchmark_state_{self.benchmark_distribution.state.value.lower()}",
            )
        if self.compatibility.state is not SiteBenchmarkCompatibilityState.COMPATIBLE:
            return self.compatibility.reason_codes
        return ()

    @property
    def ecdf_evaluation(self) -> BenchmarkMidEcdfEvaluation | None:
        if self.state is not FeatureNormalizationState.AVAILABLE:
            return None
        value = self.site_measurement.metric_value.value
        if value is None:
            raise RuntimeError("available normalization cannot have value=None")
        return evaluate_benchmark_mid_ecdf(
            self.benchmark_distribution,
            value,
            policy=self.policy.ecdf_policy,
        )

    @property
    def percentile(self) -> float | None:
        evaluation = self.ecdf_evaluation
        return evaluation.percentile if evaluation is not None else None

    @property
    def score(self) -> float | None:
        percentile = self.percentile
        if percentile is None:
            return None
        score = self.policy.transform_percentile(percentile)
        if not 0.0 <= score <= 100.0:
            raise RuntimeError("canonical feature normalization produced an out-of-range score")
        return score

    @property
    def normalized_feature_key(self) -> str:
        return self.policy.normalized_feature_key

    @property
    def identity_id(self) -> str:
        evaluation = self.ecdf_evaluation
        return semantic_hash({
            "site_measurement_id": self.site_measurement.measurement_id,
            "benchmark_distribution_id": self.benchmark_distribution.distribution_id,
            "site_compatibility_id": self.compatibility.site_compatibility.identity_id,
            "benchmark_compatibility_id": (
                self.compatibility.benchmark_compatibility.identity_id
                if self.compatibility.benchmark_compatibility else None
            ),
            "compatibility_decision_id": self.compatibility.identity_id,
            "normalization_policy_id": self.policy.identity_id,
            "ecdf_evaluation_id": evaluation.evaluation_id if evaluation else None,
            "normalized_feature_key": self.normalized_feature_key,
            "state": self.state.value,
            "reason_codes": self.reason_codes,
            "percentile": self.percentile,
            "score": self.score,
        })


def normalize_feature(
    site_measurement: DerivedMetricMeasurement,
    benchmark_distribution: BenchmarkDistributionArtifact,
) -> FeatureNormalizationResult:
    if not isinstance(site_measurement, DerivedMetricMeasurement):
        raise TypeError("site_measurement must be DerivedMetricMeasurement")
    return FeatureNormalizationResult(
        site_measurement,
        benchmark_distribution,
        feature_normalization_policy(site_measurement.definition.metric_key),
    )


@dataclass(frozen=True, slots=True)
class AgeTargetConcentrationFallbackPolicy:
    policy_id: str = "age_neutral_fallback"
    policy_version: str = "1.0"
    normalized_feature_key: str = "age_target_concentration_score"
    unit: str = "score_0_100"
    score: float = 50.0
    availability: str = "available"
    score_eligibility: str = "eligible"
    calibration_state: str = "uncalibrated"
    is_proxy: bool = True
    reason_code: str = "age_affinity_not_calibrated"

    def __post_init__(self) -> None:
        expected = (
            "age_neutral_fallback",
            "1.0",
            "age_target_concentration_score",
            "score_0_100",
            50.0,
            "available",
            "eligible",
            "uncalibrated",
            True,
            "age_affinity_not_calibrated",
        )
        actual = (
            self.policy_id,
            self.policy_version,
            self.normalized_feature_key,
            self.unit,
            self.score,
            self.availability,
            self.score_eligibility,
            self.calibration_state,
            self.is_proxy,
            self.reason_code,
        )
        if actual != expected:
            raise ValueError("age target-concentration fallback semantics are frozen for V1")

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "normalized_feature_key": self.normalized_feature_key,
            "unit": self.unit,
            "score": self.score,
            "availability": self.availability,
            "score_eligibility": self.score_eligibility,
            "calibration_state": self.calibration_state,
            "is_proxy": self.is_proxy,
            "reason_code": self.reason_code,
        })


AGE_TARGET_CONCENTRATION_FALLBACK_V1 = AgeTargetConcentrationFallbackPolicy()


@dataclass(frozen=True, slots=True)
class AgeTargetConcentrationFallback:
    policy: AgeTargetConcentrationFallbackPolicy = AGE_TARGET_CONCENTRATION_FALLBACK_V1

    def __post_init__(self) -> None:
        if not isinstance(self.policy, AgeTargetConcentrationFallbackPolicy):
            raise TypeError("policy must be AgeTargetConcentrationFallbackPolicy")
        if self.policy.identity_id != AGE_TARGET_CONCENTRATION_FALLBACK_V1.identity_id:
            raise ValueError("unsupported age fallback policy")

    @property
    def normalized_feature_key(self) -> str:
        return self.policy.normalized_feature_key

    @property
    def score(self) -> float:
        return self.policy.score

    @property
    def unit(self) -> str:
        return self.policy.unit

    @property
    def availability(self) -> str:
        return self.policy.availability

    @property
    def score_eligibility(self) -> str:
        return self.policy.score_eligibility

    @property
    def calibration_state(self) -> str:
        return self.policy.calibration_state

    @property
    def is_proxy(self) -> bool:
        return self.policy.is_proxy

    @property
    def method_version(self) -> str:
        return f"{self.policy.policy_id}/{self.policy.policy_version}"

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return (self.policy.reason_code,)

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "policy_id": self.policy.identity_id,
            "normalized_feature_key": self.normalized_feature_key,
            "score": self.score,
            "unit": self.unit,
            "availability": self.availability,
            "score_eligibility": self.score_eligibility,
            "calibration_state": self.calibration_state,
            "is_proxy": self.is_proxy,
            "method_version": self.method_version,
            "reason_codes": self.reason_codes,
        })


def build_age_target_concentration_fallback() -> AgeTargetConcentrationFallback:
    return AgeTargetConcentrationFallback()
