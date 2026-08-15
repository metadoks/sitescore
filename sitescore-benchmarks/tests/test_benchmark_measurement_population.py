from cp344_helpers import *


def test_complete_eligible_population_accepted(frame3):
    attempts = complete_attempts(frame3, income_attempt)
    measurement_set = build_benchmark_measurement_set(
        frame3, attempts, metric_key="household_income"
    )
    distribution = build_benchmark_distribution(measurement_set)
    assert distribution.coverage.eligible_cell_count == 3
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.numeric_included_count == 3
    assert len(distribution.observations) == 3
    assert distribution.state is BenchmarkDistributionState.AVAILABLE


def test_missing_eligible_cell_rejected(frame3):
    attempts = complete_attempts(frame3, income_attempt)
    with pytest.raises(ValueError, match="exactly cover eligible frame cells"):
        build_benchmark_measurement_set(frame3, attempts[:-1], metric_key="household_income")


def test_duplicate_attempt_rejected_without_dedup(frame3):
    attempts = complete_attempts(frame3, income_attempt)
    with pytest.raises(ValueError, match="duplicate"):
        build_benchmark_measurement_set(
            frame3, attempts + (attempts[-1],), metric_key="household_income"
        )


def test_foreign_extra_attempt_rejected(
    frame3, crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy
):
    foreign = make_frame(
        cell_count=3, crs3857=crs3857, canon_policy=canon_policy, engine=engine,
        boundary_artifact=boundary_artifact, geography=geography, evidence_policy=evidence_policy,
        eligibility_version="2.0",
    )
    attempts = complete_attempts(frame3, income_attempt)
    extra = income_attempt(foreign, foreign.cells[0], 9)
    with pytest.raises(ValueError, match="exactly cover eligible frame cells"):
        build_benchmark_measurement_set(
            frame3, attempts + (extra,), metric_key="household_income"
        )


def test_wrong_frame_cell_rejected_before_measurement_wrap(
    frame3, crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy
):
    foreign = make_frame(
        cell_count=3, crs3857=crs3857, canon_policy=canon_policy, engine=engine,
        boundary_artifact=boundary_artifact, geography=geography, evidence_policy=evidence_policy,
        eligibility_version="2.0",
    )
    with pytest.raises(ValueError, match="foreign"):
        adapt_benchmark_cell_subject(
            frame3, foreign.cells[0],
            inputs=(MetricEvidence(demo(), "demographic_snapshot"),),
        )


def test_subject_mismatch_cell_a_vs_b_rejected(frame3):
    snapshot = demo()
    inputs = (MetricEvidence(snapshot, "demographic_snapshot"),)
    subject_b = adapt_benchmark_cell_subject(frame3, frame3.cells[1], inputs=inputs)
    measurement = measure_household_income(subject_b, snapshot)
    with pytest.raises(ValueError, match="detached"):
        BenchmarkCellMeasurement(frame3, frame3.cells[0], measurement)


def test_subject_extra_caller_scope_rejected(frame3):
    snapshot = demo()
    inputs = (MetricEvidence(snapshot, "demographic_snapshot"),)
    canonical = adapt_benchmark_cell_subject(frame3, frame3.cells[0], inputs=inputs)
    forged = MeasurementSubject(
        canonical.kind, canonical.subject_contract, canonical.subject_contract_version,
        canonical.semantic_payload, tuple(sorted(canonical.scope_refs + ("caller:forged",))),
    )
    measurement = measure_household_income(forged, snapshot)
    with pytest.raises(ValueError, match="detached"):
        BenchmarkCellMeasurement(frame3, frame3.cells[0], measurement)


def test_subject_adapter_derives_frame_cell_and_evidence_scopes(frame3):
    snapshot = demo()
    subject = adapt_benchmark_cell_subject(
        frame3, frame3.cells[0], inputs=(MetricEvidence(snapshot, "demographic_snapshot"),)
    )
    payload = dict(subject.semantic_payload)
    assert subject.kind is SubjectKind.BENCHMARK_CELL
    assert payload["commercial_frame_id"] == frame3.frame_id
    assert payload["commercial_frame_cell_id"] == frame3.cells[0].cell_id
    assert payload["lattice_cell_id"] == frame3.cells[0].lattice_cell_id
    assert f"geography:{snapshot.geography_ref.geography_id}" in subject.scope_refs
    assert f"benchmark_frame:{frame3.frame_id}" in subject.scope_refs


def test_wrong_metric_rejected_by_measurement_set(frame3):
    attempts = complete_attempts(frame3, area_attempt)
    with pytest.raises(ValueError, match="definition mismatch"):
        build_benchmark_measurement_set(frame3, attempts, metric_key="household_income")


def test_altered_definition_same_key_cannot_masquerade(frame3):
    measurement = income_attempt(frame3, frame3.cells[0], 1).measurement
    fake_definition = MetricDefinition(
        "household_income", "999.0", "usd_per_household",
        MetricImplementationStatus.PASS_THROUGH_PROVIDER_DERIVED,
    )
    with pytest.raises(ValueError, match="canonical V1 registry"):
        DerivedMetricMeasurement(
            fake_definition, measurement.policy, measurement.precision_policy,
            measurement.subject, measurement.inputs, measurement.metric_value,
            measurement.method_version, measurement.reason_codes,
            measurement.source_bundle_compatibility,
        )


def test_altered_policy_same_key_cannot_masquerade(frame3):
    measurement = income_attempt(frame3, frame3.cells[0], 1).measurement
    fake_policy = MetricDerivationPolicy(
        "household_income_passthrough", "999.0", "household_income",
        DerivationStrategy.PASS_THROUGH_PROVIDER_DERIVED,
    )
    with pytest.raises(ValueError, match="canonical V1 registry"):
        DerivedMetricMeasurement(
            measurement.definition, fake_policy, measurement.precision_policy,
            measurement.subject, measurement.inputs, measurement.metric_value,
            measurement.method_version, measurement.reason_codes,
            measurement.source_bundle_compatibility,
        )


def test_precision_mismatch_rejected(frame3):
    precision_v2 = MeasurementPrecisionPolicy("real_unit_full_binary64", "2.0")
    attempts = list(complete_attempts(frame3, income_attempt))
    attempts[0] = income_attempt(frame3, frame3.cells[0], 1, precision=precision_v2)
    with pytest.raises(ValueError, match="precision-policy mismatch"):
        build_benchmark_measurement_set(
            frame3, tuple(attempts), metric_key="household_income"
        )


def test_unit_and_observation_value_are_not_caller_inputs(frame3):
    assert tuple(inspect.signature(BenchmarkObservation).parameters) == ("attempt",)
    assert "unit" not in inspect.signature(BenchmarkMeasurementSet).parameters
    assert "value" not in inspect.signature(BenchmarkDistributionArtifact).parameters
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, complete_attempts(frame3, income_attempt), metric_key="household_income"
    ))
    assert all(o.unit == "usd_per_household" for o in distribution.observations)


def test_unresolved_measurements_preserved_but_not_observed(frame3):
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, complete_attempts(frame3, competition_attempt), metric_key="competition_pressure"
    ))
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.non_numeric_count == 3
    assert distribution.coverage.numeric_included_count == 0
    assert distribution.observations == ()
    assert distribution.state is BenchmarkDistributionState.NO_NUMERIC_OBSERVATIONS


def test_missing_does_not_become_zero(frame3):
    attempts = list(complete_attempts(frame3, area_attempt))
    attempts[1] = area_attempt(frame3, frame3.cells[1], 2, missing=True)
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, tuple(attempts), metric_key="walkable_reach_area_km2"
    ))
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.numeric_included_count == 2
    assert distribution.coverage.non_numeric_count == 1
    assert all(o.value != 0 for o in distribution.observations)
    assert "missing" in dict(distribution.coverage.reason_counts)


def test_numeric_observation_value_is_authoritative_metric_value(frame3):
    attempts = complete_attempts(frame3, income_attempt)
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, attempts, metric_key="household_income"
    ))
    by_cell = {a.frame_cell.cell_id: a for a in attempts}
    for observation in distribution.observations:
        source = by_cell[observation.attempt.frame_cell.cell_id].measurement
        assert observation.value == source.metric_value.value
        assert observation.attempt.measurement.measurement_id == source.measurement_id


def test_nonfinite_has_no_benchmark_bypass(frame3):
    with pytest.raises(ValueError):
        mv(float("inf"), "usd_per_household")
    assert "value" not in inspect.signature(BenchmarkObservation).parameters


def test_transit_same_bundle_distribution_available(frame3):
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, complete_attempts(frame3, transit_attempt),
        metric_key="transit_service_departure_equivalents_per_hour",
    ))
    assert distribution.state is BenchmarkDistributionState.AVAILABLE
    assert distribution.coverage.numeric_included_count == 3
    assert dict(distribution.compatibility.source_bundle_compatibility) == {
        "transit_source_bundle_fingerprint": "bundle:abc"
    }


def _income_attempt_with_semantics(
    frame, cell, n, *, calibration=CalibrationState.CALIBRATED, method="acs-income-v1"
):
    snapshot = demo(n)
    original = snapshot.household_income
    hardened_value = MetricValue(
        original.value,
        original.unit,
        original.availability,
        original.data_quality,
        original.score_eligibility,
        calibration,
        original.is_estimate,
        original.is_proxy,
        original.source_refs,
        method,
        original.reason_codes,
    )
    snapshot = replace(snapshot, household_income=hardened_value)
    return income_attempt(frame, cell, n, snapshot=snapshot)


def test_uncalibrated_available_eligible_numeric_attempt_is_excluded(frame3):
    attempts = tuple(
        _income_attempt_with_semantics(
            frame3, cell, i + 1, calibration=CalibrationState.UNCALIBRATED
        )
        for i, cell in enumerate(frame3.cells)
    )
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, attempts, metric_key="household_income"
    ))
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.numeric_candidate_count == 0
    assert distribution.coverage.numeric_included_count == 0
    assert distribution.coverage.excluded_count == 3
    assert distribution.observations == ()
    assert dict(distribution.coverage.reason_counts) == {
        "calibration_state_uncalibrated": 3
    }
    assert distribution.state is BenchmarkDistributionState.NO_NUMERIC_OBSERVATIONS


def test_mixed_calibration_preserves_complete_population_and_excludes_one(frame3):
    attempts = list(complete_attempts(frame3, income_attempt))
    attempts[2] = _income_attempt_with_semantics(
        frame3, frame3.cells[2], 3, calibration=CalibrationState.UNCALIBRATED
    )
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, tuple(attempts), metric_key="household_income"
    ))
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.numeric_candidate_count == 2
    assert distribution.coverage.numeric_included_count == 2
    assert distribution.coverage.excluded_count == 1
    assert len(distribution.observations) == 2
    assert dict(distribution.coverage.reason_counts) == {
        "calibration_state_uncalibrated": 1
    }
    assert all(o.value != 0 for o in distribution.observations)
    assert distribution.state is BenchmarkDistributionState.AVAILABLE


def test_calibrated_available_eligible_numeric_attempt_remains_included(frame3):
    attempts = tuple(
        _income_attempt_with_semantics(frame3, cell, i + 1)
        for i, cell in enumerate(frame3.cells)
    )
    distribution = build_benchmark_distribution(build_benchmark_measurement_set(
        frame3, attempts, metric_key="household_income"
    ))
    assert distribution.coverage.attempt_count == 3
    assert distribution.coverage.numeric_candidate_count == 3
    assert distribution.coverage.numeric_included_count == 3
    assert len(distribution.observations) == 3
    assert distribution.state is BenchmarkDistributionState.AVAILABLE


def test_numeric_inclusion_policy_identity_declares_calibration_requirement():
    assert BENCHMARK_MEASUREMENT_DISTRIBUTION_V1.numeric_inclusion_rule == (
        "AVAILABLE_SCORE_ELIGIBLE_CALIBRATED_FINITE_VALUE"
    )
