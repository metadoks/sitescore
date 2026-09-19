from __future__ import annotations

import pytest

from sitescore_benchmarks import (
    FeatureNormalizationState,
    SiteBenchmarkCompatibility,
    SiteBenchmarkCompatibilityState,
    build_benchmark_distribution,
    build_benchmark_measurement_set,
    feature_normalization_policy,
    normalize_feature,
)
from sitescore_metrics import (
    MeasurementSubject,
    MetricEvidence,
    SubjectKind,
    unresolved_competition_pressure,
)

from cp344_helpers import competition, competition_attempt, make_frame


@pytest.fixture
def frame2(crs3857, canon_policy, engine, boundary_artifact, geography, evidence_policy):
    return make_frame(
        cell_count=2,
        crs3857=crs3857,
        canon_policy=canon_policy,
        engine=engine,
        boundary_artifact=boundary_artifact,
        geography=geography,
        evidence_policy=evidence_policy,
    )


def _site_competition(definition_id: str):
    snapshot = competition(99, definition_id=definition_id)
    subject = MeasurementSubject(
        SubjectKind.SITE,
        "sitescore_metrics.site",
        "1.0",
        (("site_id", "site_competition"),),
        tuple(sorted((f"competition:{snapshot.snapshot_id}", "site:site_competition"))),
    )
    return unresolved_competition_pressure(
        subject,
        snapshot,
        expected_measurement_definition_id=definition_id,
    )


def _competition_distribution(frame, definition_id: str):
    attempts = tuple(
        competition_attempt(frame, cell, i + 1, definition_id=definition_id)
        for i, cell in enumerate(frame.cells)
    )
    return build_benchmark_distribution(build_benchmark_measurement_set(
        frame,
        attempts,
        metric_key="competition_pressure",
    ))


def test_competition_measurement_definition_same_lineage_is_compatible_even_while_nonnumeric(frame2):
    site = _site_competition("measurement_def_1")
    benchmark = _competition_distribution(frame2, "measurement_def_1")
    compatibility = SiteBenchmarkCompatibility(site, benchmark)
    assert compatibility.state is SiteBenchmarkCompatibilityState.COMPATIBLE
    assert compatibility.reason_codes == ()
    result = normalize_feature(site, benchmark)
    assert result.state is FeatureNormalizationState.SITE_METRIC_NOT_AVAILABLE
    assert result.score is None


def test_competition_measurement_definition_mismatch_is_explicit(frame2):
    site = _site_competition("measurement_def_2")
    benchmark = _competition_distribution(frame2, "measurement_def_1")
    compatibility = SiteBenchmarkCompatibility(site, benchmark)
    assert compatibility.state is SiteBenchmarkCompatibilityState.INCOMPATIBLE
    assert "competition_measurement_definition_mismatch" in compatibility.reason_codes
    assert compatibility.identity_id


def test_competition_policy_inversion_exists_without_forcing_unresolved_metric_numeric():
    policy = feature_normalization_policy("competition_pressure")
    assert policy.transform_percentile(0.75) == 25.0
    assert _site_competition("measurement_def_1").metric_value.value is None
