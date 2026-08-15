from cp344_helpers import *


def test_transit_cross_bundle_never_silently_coexists(frame3):
    attempts = list(complete_attempts(frame3, transit_attempt))
    attempts[2] = transit_attempt(frame3, frame3.cells[2], 3, bundle="bundle:foreign")
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, tuple(attempts),
        metric_key="transit_service_departure_equivalents_per_hour",
    ))
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.has_compatibility_conflict
    assert distribution.coverage.numeric_candidate_count == 3
    assert distribution.coverage.numeric_included_count == 0
    assert distribution.coverage.incompatible_numeric_count == 3
    assert distribution.observations == ()
    assert distribution.compatibility is None
    assert distribution.state is BenchmarkDistributionState.INCOMPATIBLE_MEASUREMENT_LINEAGE


def test_competition_unresolved_preserves_measurement_definition_lineage(frame3):
    attempts = complete_attempts(frame3, competition_attempt)
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, attempts, metric_key="competition_pressure"
    ))
    assert distribution.observations == ()
    assert dict(distribution.compatibility.source_bundle_compatibility) == {
        "competition_measurement_definition_id": "measurement_def_1"
    }
    assert all(
        a.measurement.reason_codes == ("competition_reduction_policy_unresolved",)
        for a in attempts
    )


def test_competition_mixed_measurement_definition_is_incompatible(frame3):
    attempts = list(complete_attempts(frame3, competition_attempt))
    attempts[1] = competition_attempt(
        frame3, frame3.cells[1], 2, definition_id="measurement_def_2"
    )
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, tuple(attempts), metric_key="competition_pressure"
    ))
    assert distribution.state is BenchmarkDistributionState.INCOMPATIBLE_MEASUREMENT_LINEAGE
    assert distribution.observations == ()


def test_road_unresolved_preserves_routing_profile_lineage(frame3):
    attempts = complete_attempts(frame3, road_attempt)
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, attempts, metric_key="road_reachable_area_km2"
    ))
    assert distribution.observations == ()
    assert dict(distribution.compatibility.source_bundle_compatibility) == {
        "routing_profile_id": "drive",
        "routing_profile_version": "1.0",
    }
    assert all(
        a.measurement.reason_codes == ("road_reduction_policy_unresolved",)
        for a in attempts
    )


def test_road_mixed_routing_profile_is_incompatible(frame3):
    attempts = list(complete_attempts(frame3, road_attempt))
    attempts[2] = road_attempt(frame3, frame3.cells[2], 3, profile="car")
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, tuple(attempts), metric_key="road_reachable_area_km2"
    ))
    assert distribution.state is BenchmarkDistributionState.INCOMPATIBLE_MEASUREMENT_LINEAGE


def test_parking_metrics_remain_independent_distributions(frame3):
    capacity_attempts = complete_attempts(frame3, parking_attempt)
    curb_attempts = tuple(
        parking_attempt(frame3, cell, i + 1, curb=True)
        for i, cell in enumerate(frame3.cells)
    )
    capacity = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, capacity_attempts, metric_key="parking_public_offstreet_capacity"
    ))
    curb = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, curb_attempts, metric_key="parking_legal_curb_length_m"
    ))
    assert capacity.measurement_set.unit == "spaces"
    assert curb.measurement_set.unit == "m"
    assert capacity.distribution_id != curb.distribution_id
    assert [o.value for o in capacity.observations] != [o.value for o in curb.observations]


def test_empty_eligible_population_is_explicit(
    crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy
):
    frame = make_frame(
        cell_count=0, crs3857=crs3857, canon_policy=canon_policy, engine=engine,
        boundary_artifact=boundary_artifact, geography=geography, evidence_policy=evidence_policy,
    )
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame, (), metric_key="household_income"
    ))
    assert distribution.coverage.eligible_cell_count == 0
    assert distribution.coverage.attempt_count == 0
    assert distribution.observations == ()
    assert distribution.state is BenchmarkDistributionState.EMPTY_ELIGIBLE_POPULATION
    assert distribution.compatibility is None


def test_all_attempts_non_numeric_is_structurally_representable(frame3):
    distribution = BenchmarkDistributionArtifact(build_benchmark_measurement_set(
        frame3, complete_attempts(frame3, competition_attempt), metric_key="competition_pressure"
    ))
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.numeric_candidate_count == 0
    assert distribution.coverage.excluded_count == 3
    assert distribution.state is BenchmarkDistributionState.NO_NUMERIC_OBSERVATIONS


def test_input_order_is_nonsemantic_and_output_is_canonical(frame3):
    attempts = complete_attempts(frame3, income_attempt)
    a = build_benchmark_measurement_set(frame3, attempts, metric_key="household_income")
    b = build_benchmark_measurement_set(
        frame3, tuple(reversed(attempts)), metric_key="household_income"
    )
    assert a.measurement_set_id == b.measurement_set_id
    assert tuple(x.attempt_id for x in a.attempts) == tuple(x.attempt_id for x in b.attempts)
    assert BenchmarkDistributionArtifact(a).distribution_id == BenchmarkDistributionArtifact(b).distribution_id


def test_identity_changes_with_precision_semantics(frame3):
    attempts = complete_attempts(frame3, income_attempt)
    a = build_benchmark_measurement_set(frame3, attempts, metric_key="household_income")
    precision_v2 = MeasurementPrecisionPolicy("real_unit_full_binary64", "2.0")
    attempts_v2 = tuple(
        income_attempt(frame3, cell, i + 1, precision=precision_v2)
        for i, cell in enumerate(frame3.cells)
    )
    b = build_benchmark_measurement_set(
        frame3, attempts_v2, metric_key="household_income", precision_policy=precision_v2
    )
    assert a.measurement_set_id != b.measurement_set_id
    assert BenchmarkDistributionArtifact(a).distribution_id != BenchmarkDistributionArtifact(b).distribution_id


def test_identity_changes_with_source_compatibility(frame3):
    attempts_a = complete_attempts(frame3, transit_attempt)
    attempts_b = tuple(
        transit_attempt(frame3, cell, i + 1, bundle="bundle:def")
        for i, cell in enumerate(frame3.cells)
    )
    a = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, attempts_a, metric_key="transit_service_departure_equivalents_per_hour"
    ))
    b = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, attempts_b, metric_key="transit_service_departure_equivalents_per_hour"
    ))
    assert a.compatibility.identity_id != b.compatibility.identity_id
    assert a.distribution_id != b.distribution_id


def test_generated_at_is_nonsemantic_for_frame_distribution(frame3):
    shifted = replace(frame3, generated_at=datetime(2027, 1, 1, tzinfo=timezone.utc))
    assert shifted.frame_id == frame3.frame_id
    attempts_a = complete_attempts(frame3, income_attempt)
    attempts_b = tuple(
        BenchmarkCellMeasurement(shifted, shifted.cells[i], attempts_a[i].measurement)
        for i in range(len(shifted.cells))
    )
    a = BenchmarkDistributionArtifact(build_benchmark_measurement_set(
        frame3, attempts_a, metric_key="household_income"
    ))
    b = BenchmarkDistributionArtifact(build_benchmark_measurement_set(
        shifted, attempts_b, metric_key="household_income"
    ))
    assert a.distribution_id == b.distribution_id


def test_coverage_is_derived_not_caller_asserted(frame3):
    assert tuple(inspect.signature(BenchmarkCoverage).parameters) == ("measurement_set",)
    attempts = list(complete_attempts(frame3, area_attempt))
    attempts[0] = area_attempt(frame3, frame3.cells[0], 1, missing=True)
    coverage = BenchmarkCoverage(build_benchmark_measurement_set(
        frame3, tuple(attempts), metric_key="walkable_reach_area_km2"
    ))
    assert coverage.attempt_count == coverage.eligible_cell_count == 3
    assert coverage.numeric_included_count == 2
    assert coverage.excluded_count == 1
    assert coverage.numeric_included_count + coverage.excluded_count == coverage.attempt_count


def test_distribution_state_and_observations_are_not_self_asserted(frame3):
    assert tuple(inspect.signature(BenchmarkDistributionArtifact).parameters) == ("measurement_set",)
    assert "state" not in inspect.signature(BenchmarkDistributionArtifact).parameters
    assert "observations" not in inspect.signature(BenchmarkDistributionArtifact).parameters
    assert "eligible_cell_count" not in inspect.signature(BenchmarkCoverage).parameters


def test_metric_key_alone_is_not_contract_authority(frame3):
    attempts = complete_attempts(frame3, income_attempt)
    direct = BenchmarkMeasurementSet(
        frame3, DEFINITIONS["household_income"], POLICIES["household_income"],
        FULL_BINARY64, attempts,
    )
    assert direct.definition is DEFINITIONS["household_income"]
    assert direct.derivation_policy is POLICIES["household_income"]
    assert direct.measurement_set_id


def test_no_ecdf_percentile_or_normalization_surface():
    import sitescore_benchmarks.distribution as module
    text = Path(module.__file__).read_text().lower()
    for token in (
        "mid_ecdf", "percentile", "normalizedlocationfeatures",
        "road_parking_access_score", "scoringreadiness",
        "realdatapipelineresult", "core.analyze",
    ):
        assert token not in text
    public_names = set(dir(module))
    assert not any("percentile" in name.lower() or "ecdf" in name.lower() for name in public_names)


def test_policy_has_no_empirical_threshold_fields():
    params = set(inspect.signature(BenchmarkMeasurementDistributionPolicy).parameters)
    for forbidden in (
        "minimum_n", "coverage_threshold", "cell_size", "equal_area_crs",
        "overlap_threshold", "road_weight", "parking_weight",
    ):
        assert forbidden not in params
