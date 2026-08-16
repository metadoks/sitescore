from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from sitescore_app import (
    ApplicationScoringBlocked,
    ApplicationScoringGateState,
    ApplicationScoringInput,
    build_application_scoring_input,
    evaluate_application_scoring_gate,
    require_canonical_application_scoring_input,
)
from sitescore_data.enums import PipelineStatus
from sitescore_data.schemas.features import NormalizedLocationFeatures
from sitescore_data.schemas.pipeline import RealDataPipelineResult
from sitescore_data.schemas.readiness import ScoringReadinessResult


REPO_ROOT = Path(__file__).resolve().parents[2]


def _terminal_shell(
    status: PipelineStatus,
    *,
    ready: bool | None,
    normalized: bool,
) -> RealDataPipelineResult:
    """Test-local frozen-contract shell for gate-state combinations only.

    Production code never exposes this construction mechanism. Upstream suites own
    full RealDataPipelineResult construction/validation; this fixture isolates the
    FAZ 4 gate without changing frozen production policy to manufacture SCORE_READY.
    """

    result = object.__new__(RealDataPipelineResult)
    object.__setattr__(result, "status", status)

    if ready is None:
        readiness = None
    else:
        readiness = object.__new__(ScoringReadinessResult)
        object.__setattr__(readiness, "is_score_ready", ready)
        object.__setattr__(readiness, "reason_codes", ())
        object.__setattr__(readiness, "readiness_fingerprint", "test-readiness-fingerprint")
    object.__setattr__(result, "scoring_readiness", readiness)

    features = object.__new__(NormalizedLocationFeatures) if normalized else None
    object.__setattr__(result, "normalized_features", features)
    return result


def test_not_score_ready_fails_closed():
    result = _terminal_shell(
        PipelineStatus.NOT_SCORE_READY,
        ready=False,
        normalized=True,
    )
    eligibility = evaluate_application_scoring_gate(result)
    assert eligibility.state is ApplicationScoringGateState.NOT_SCORE_READY
    assert eligibility.is_eligible is False
    with pytest.raises(ApplicationScoringBlocked):
        build_application_scoring_input(result)


def test_pipeline_error_fails_closed():
    result = _terminal_shell(
        PipelineStatus.PIPELINE_ERROR,
        ready=None,
        normalized=False,
    )
    eligibility = evaluate_application_scoring_gate(result)
    assert eligibility.state is ApplicationScoringGateState.PIPELINE_ERROR
    assert eligibility.is_eligible is False
    with pytest.raises(ApplicationScoringBlocked):
        build_application_scoring_input(result)


def test_only_score_ready_plus_true_readiness_and_normalized_surface_is_eligible():
    result = _terminal_shell(
        PipelineStatus.SCORE_READY,
        ready=True,
        normalized=True,
    )
    eligibility = evaluate_application_scoring_gate(result)
    assert eligibility.state is ApplicationScoringGateState.ELIGIBLE
    capability = build_application_scoring_input(result)
    assert capability.pipeline_result is result
    assert require_canonical_application_scoring_input(capability) is capability
    assert capability.readiness_fingerprint == "test-readiness-fingerprint"


@pytest.mark.parametrize(
    ("ready", "normalized"),
    [(False, True), (None, True), (True, False)],
)
def test_inconsistent_score_ready_shell_is_rejected(ready, normalized):
    result = _terminal_shell(
        PipelineStatus.SCORE_READY,
        ready=ready,
        normalized=normalized,
    )
    eligibility = evaluate_application_scoring_gate(result)
    assert eligibility.state is ApplicationScoringGateState.INCONSISTENT_TERMINAL_STATE
    with pytest.raises(ApplicationScoringBlocked):
        build_application_scoring_input(result)


def test_caller_cannot_assert_ready_with_boolean_or_status_arguments():
    signature = inspect.signature(build_application_scoring_input)
    assert tuple(signature.parameters) == ("pipeline_result",)
    for forbidden in ("ready", "is_ready", "is_score_ready", "force", "skip_readiness"):
        assert forbidden not in signature.parameters


def test_application_scoring_input_constructor_and_manual_shell_are_not_authority():
    with pytest.raises(TypeError):
        ApplicationScoringInput()

    forged = object.__new__(ApplicationScoringInput)
    object.__setattr__(
        forged,
        "pipeline_result",
        _terminal_shell(PipelineStatus.SCORE_READY, ready=True, normalized=True),
    )
    with pytest.raises(ValueError, match="not canonical"):
        require_canonical_application_scoring_input(forged)


def test_app_package_does_not_score_or_neutralize_partial_features():
    source = (REPO_ROOT / "sitescore-app" / "src" / "sitescore_app" / "gating.py").read_text()
    assert "analyze(" not in source
    assert "CategoryScores(" not in source
    assert "ReadyCategoryScorePayload(" not in source
    assert "= 50" not in source
    assert "= 0" not in source


def test_no_upstream_package_imports_sitescore_app():
    upstream = (
        "sitescore-core",
        "sitescore-data",
        "sitescore-providers",
        "sitescore-spatial",
        "sitescore-metrics",
        "sitescore-benchmarks",
        "sitescore-pipeline",
    )
    for package in upstream:
        src_root = REPO_ROOT / package / "src"
        for path in src_root.rglob("*.py"):
            assert "sitescore_app" not in path.read_text(encoding="utf-8")


def test_no_http_payment_report_or_ui_dependencies():
    pyproject = (REPO_ROOT / "sitescore-app" / "pyproject.toml").read_text().lower()
    assert '"sitescore-data==0.1.0"' in pyproject
    assert '"sitescore-pipeline==0.1.0"' in pyproject
    for forbidden in (
        "fastapi",
        "flask",
        "django",
        "starlette",
        "stripe",
        "reportlab",
        "weasyprint",
        "celery",
        "redis",
    ):
        assert forbidden not in pyproject
