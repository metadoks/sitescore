from __future__ import annotations

import inspect
import math
from pathlib import Path

import pytest

from sitescore_benchmarks import (
    BenchmarkDistributionArtifact,
    BenchmarkDistributionState,
    CanonicalNumericSample,
    EXACT_NUMERIC_COMPARISON_V1,
    MID_ECDF_V1,
    MidEcdfEvaluation,
    MidEcdfState,
    NumericComparisonPolicy,
    build_benchmark_distribution,
    build_benchmark_measurement_set,
    build_benchmark_numeric_sample,
    build_numeric_sample,
    evaluate_benchmark_mid_ecdf,
    evaluate_mid_ecdf,
)
from sitescore_metrics import FULL_BINARY64

from cp344_helpers import (
    complete_attempts,
    competition_attempt,
    income_attempt,
    make_frame,
    transit_attempt,
)


def _sample(*values):
    return build_numeric_sample(tuple(values))


def test_ecdf_001_basic_unique_sample():
    result = evaluate_mid_ecdf(_sample(1, 2, 3), 2)
    assert result.n == 3
    assert result.below_count == 1
    assert result.equal_count == 1
    assert result.percentile == 0.5


def test_ecdf_002_tied_middle_value():
    result = evaluate_mid_ecdf(_sample(1, 2, 2, 2, 3), 2)
    assert result.n == 5
    assert result.below_count == 1
    assert result.equal_count == 3
    assert result.percentile == 0.5


@pytest.mark.parametrize("n", [1, 2, 7])
def test_ecdf_003_all_equal_is_one_half(n):
    result = evaluate_mid_ecdf(build_numeric_sample(tuple(4 for _ in range(n))), 4)
    assert result.equal_count == n
    assert result.percentile == 0.5


def test_ecdf_004_below_minimum_is_zero():
    result = evaluate_mid_ecdf(_sample(1, 2, 3), 0)
    assert result.below_count == 0
    assert result.equal_count == 0
    assert result.percentile == 0.0


def test_ecdf_005_above_maximum_is_one():
    result = evaluate_mid_ecdf(_sample(1, 2, 3), 4)
    assert result.below_count == 3
    assert result.equal_count == 0
    assert result.percentile == 1.0


def test_ecdf_006_observed_minimum_uses_formula_not_clamp():
    result = evaluate_mid_ecdf(_sample(1, 2, 3), 1)
    assert result.below_count == 0
    assert result.equal_count == 1
    assert result.percentile == pytest.approx(1 / 6)
    assert result.percentile != 0.0


def test_ecdf_007_observed_maximum_uses_formula_not_clamp():
    result = evaluate_mid_ecdf(_sample(1, 2, 3), 3)
    assert result.below_count == 2
    assert result.equal_count == 1
    assert result.percentile == pytest.approx(5 / 6)
    assert result.percentile != 1.0


def test_ecdf_008_no_interpolation_step_function():
    result = evaluate_mid_ecdf(_sample(1, 3), 2)
    assert result.below_count == 1
    assert result.equal_count == 0
    assert result.percentile == 0.5
    assert MID_ECDF_V1.interpolation_rule == "STEP_FUNCTION_NO_INTERPOLATION"


def test_ecdf_009_duplicate_multiplicity_is_semantic():
    with_duplicate = _sample(1, 1, 2)
    without_duplicate = _sample(1, 2)
    result_with = evaluate_mid_ecdf(with_duplicate, 1)
    result_without = evaluate_mid_ecdf(without_duplicate, 1)
    assert with_duplicate.sample_id != without_duplicate.sample_id
    assert with_duplicate.count == 3
    assert result_with.equal_count == 2
    assert result_with.percentile == pytest.approx(1 / 3)
    assert result_without.percentile == pytest.approx(1 / 4)


def test_ecdf_010_input_permutation_is_nonsemantic():
    a = _sample(1, 2, 2, 3)
    b = _sample(3, 2, 1, 2)
    assert a.canonical_values == b.canonical_values
    assert a.sample_id == b.sample_id
    assert evaluate_mid_ecdf(a, 2).evaluation_id == evaluate_mid_ecdf(b, 2).evaluation_id


def test_ecdf_011_close_but_unequal_values_are_not_ties():
    close = math.nextafter(1.0, 2.0)
    result = evaluate_mid_ecdf(_sample(1.0, close), 1.0)
    assert close != 1.0
    assert result.equal_count == 1
    assert result.below_count == 0
    assert result.percentile == 0.25


def test_ecdf_012_numeric_equivalent_representations_canonicalize_together():
    a = _sample(1, 0.0)
    b = _sample(1.0, -0.0)
    assert a.canonical_values == b.canonical_values
    assert a.sample_id == b.sample_id
    assert evaluate_mid_ecdf(a, 1).evaluation_id == evaluate_mid_ecdf(b, 1.0).evaluation_id

    mixed = _sample(1, 1.0, -0.0, 0.0)
    one = evaluate_mid_ecdf(mixed, 1.0)
    zero = evaluate_mid_ecdf(mixed, -0.0)
    assert one.equal_count == 2
    assert zero.equal_count == 2
    assert one.percentile == 0.75
    assert zero.percentile == 0.25


def test_ecdf_013_bool_is_rejected_for_sample_and_query():
    with pytest.raises(TypeError, match="bool"):
        _sample(True)
    with pytest.raises(TypeError, match="bool"):
        evaluate_mid_ecdf(_sample(1, 2), False)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_ecdf_014_nonfinite_sample_and_query_are_rejected(bad):
    with pytest.raises(ValueError, match="finite"):
        _sample(bad)
    with pytest.raises(ValueError, match="finite"):
        evaluate_mid_ecdf(_sample(1, 2), bad)


def test_ecdf_014_none_is_not_a_numeric_value():
    with pytest.raises(TypeError, match="finite int or float"):
        _sample(None)
    with pytest.raises(TypeError, match="finite int or float"):
        evaluate_mid_ecdf(_sample(1), None)


def test_ecdf_015_empty_sample_has_explicit_unavailable_state():
    result = evaluate_mid_ecdf(build_numeric_sample(()), 1)
    assert result.state is MidEcdfState.EMPTY_SAMPLE
    assert result.reason_codes == ("empty_numeric_sample",)
    assert result.n == 0
    assert result.below_count == 0
    assert result.equal_count == 0
    assert result.percentile is None


def test_ecdf_016_no_numeric_distribution_cannot_build_benchmark_sample(frame3):
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3,
        complete_attempts(frame3, competition_attempt),
        metric_key="competition_pressure",
    ))
    assert distribution.state is BenchmarkDistributionState.NO_NUMERIC_OBSERVATIONS
    with pytest.raises(ValueError, match="AVAILABLE benchmark distribution"):
        build_benchmark_numeric_sample(distribution)
    with pytest.raises(ValueError, match="AVAILABLE benchmark distribution"):
        evaluate_benchmark_mid_ecdf(distribution, 1)


def test_ecdf_017_incompatible_distribution_cannot_build_benchmark_sample(frame3):
    attempts = list(complete_attempts(frame3, transit_attempt))
    attempts[2] = transit_attempt(frame3, frame3.cells[2], 3, bundle="bundle:foreign")
    distribution = BenchmarkDistributionArtifact(build_benchmark_measurement_set(
        frame3,
        tuple(attempts),
        metric_key="transit_service_departure_equivalents_per_hour",
    ))
    assert distribution.state is BenchmarkDistributionState.INCOMPATIBLE_MEASUREMENT_LINEAGE
    assert distribution.observations == ()
    with pytest.raises(ValueError, match="AVAILABLE benchmark distribution"):
        build_benchmark_numeric_sample(distribution)


@pytest.mark.parametrize("query", [-100, 1, 2, 3, 100])
def test_ecdf_018_available_percentile_is_always_bounded(query):
    result = evaluate_mid_ecdf(_sample(1, 2, 3), query)
    assert result.state is MidEcdfState.AVAILABLE
    assert result.percentile is not None
    assert 0.0 <= result.percentile <= 1.0


def test_ecdf_019_counts_and_percentile_are_derived_not_caller_supplied():
    params = tuple(inspect.signature(MidEcdfEvaluation).parameters)
    assert params == ("sample", "query", "policy")
    for forbidden in ("n", "below_count", "equal_count", "percentile"):
        assert forbidden not in params


def test_ecdf_020_no_feature_score_or_later_checkpoint_leakage():
    import sitescore_benchmarks.ecdf as module

    text = Path(module.__file__).read_text().lower()
    for forbidden in (
        "normalizedlocationfeatures",
        "opportunity_score",
        "competition_score",
        "road_parking_access_score",
        "comb-005",
        "scoringreadiness",
        "realdatapipelineresult",
        "categoryscores",
        "core.analyze",
    ):
        assert forbidden not in text
    assert "100 *" not in text


def test_policy_is_exact_and_separate_from_measurement_precision():
    assert EXACT_NUMERIC_COMPARISON_V1.tolerance_rule == "NO_TOLERANCE_NO_ROUNDING_NO_QUANTIZATION"
    assert MID_ECDF_V1.comparison_policy is EXACT_NUMERIC_COMPARISON_V1
    assert EXACT_NUMERIC_COMPARISON_V1.identity_id != FULL_BINARY64.identity_id
    assert "binary64" not in EXACT_NUMERIC_COMPARISON_V1.identity_id.lower()

    unsupported = NumericComparisonPolicy(
        "ecdf_numeric_comparison",
        "future",
        "EXACT_CANONICAL_NUMERIC_VALUE",
        "EXACT_CANONICAL_NUMERIC_ORDER",
        "NO_TOLERANCE_NO_ROUNDING_NO_QUANTIZATION",
    )
    with pytest.raises(ValueError, match="unsupported ECDF numeric comparison semantics"):
        CanonicalNumericSample((1, 2), unsupported)


def test_available_benchmark_distribution_evaluates_with_domain_lineage(frame3):
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3,
        complete_attempts(frame3, income_attempt),
        metric_key="household_income",
    ))
    assert distribution.state is BenchmarkDistributionState.AVAILABLE
    sample = build_benchmark_numeric_sample(distribution)
    result = evaluate_benchmark_mid_ecdf(distribution, 80002)
    assert sample.distribution.distribution_id == distribution.distribution_id
    assert sample.sample_id != sample.numeric_sample.sample_id
    assert result.benchmark_sample.sample_id == sample.sample_id
    assert result.n == len(distribution.observations) == 3
    assert result.percentile == 0.5


def test_domain_sample_identity_preserves_distribution_lineage_for_equal_values(
    crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy
):
    frame_a = make_frame(
        cell_count=3,
        crs3857=crs3857,
        canon_policy=canon_policy,
        engine=engine,
        boundary_artifact=boundary_artifact,
        geography=geography,
        evidence_policy=evidence_policy,
        eligibility_version="1.0",
    )
    frame_b = make_frame(
        cell_count=3,
        crs3857=crs3857,
        canon_policy=canon_policy,
        engine=engine,
        boundary_artifact=boundary_artifact,
        geography=geography,
        evidence_policy=evidence_policy,
        eligibility_version="1.1",
    )
    dist_a = build_benchmark_distribution(build_benchmark_measurement_set(
        frame_a,
        complete_attempts(frame_a, income_attempt),
        metric_key="household_income",
    ))
    dist_b = build_benchmark_distribution(build_benchmark_measurement_set(
        frame_b,
        complete_attempts(frame_b, income_attempt),
        metric_key="household_income",
    ))
    sample_a = build_benchmark_numeric_sample(dist_a)
    sample_b = build_benchmark_numeric_sample(dist_b)
    assert sample_a.numeric_sample.sample_id == sample_b.numeric_sample.sample_id
    assert dist_a.distribution_id != dist_b.distribution_id
    assert sample_a.sample_id != sample_b.sample_id


def test_query_numeric_representation_does_not_change_identity():
    sample = _sample(0, 1, 2)
    assert evaluate_mid_ecdf(sample, 1).evaluation_id == evaluate_mid_ecdf(sample, 1.0).evaluation_id


def test_sample_multiplicity_survives_canonical_sorting():
    sample = _sample(2, 1, 2, 1, 2)
    assert sample.count == 5
    assert sample.canonical_values.count((1, 1)) == 2
    assert sample.canonical_values.count((2, 1)) == 3
