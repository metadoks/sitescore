from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import sitescore_app.gating as gating
from sitescore_app import (
    ApplicationPipelineResult,
    ApplicationScoringBlocked,
    ApplicationScoringGateState,
    ApplicationScoringInput,
    build_application_pipeline_result,
    build_application_scoring_input,
    evaluate_application_scoring_gate,
    require_canonical_application_pipeline_result,
    require_canonical_application_scoring_input,
)
from sitescore_data.enums import PipelineStatus
from sitescore_data.schemas.features import NormalizedLocationFeatures
from sitescore_data.schemas.pipeline import RealDataPipelineResult
from sitescore_data.schemas.readiness import ScoringReadinessResult
from sitescore_pipeline import ReadinessEvaluation


REPO_ROOT = Path(__file__).resolve().parents[2]


def _terminal_shell(
    status: PipelineStatus,
    *,
    ready: bool | None,
    normalized: bool,
) -> RealDataPipelineResult:
    """Adversarial caller-fabricated terminal DTO; never canonical authority."""
    result = object.__new__(RealDataPipelineResult)
    object.__setattr__(result, "status", status)

    if ready is None:
        readiness = None
    else:
        readiness = object.__new__(ScoringReadinessResult)
        object.__setattr__(readiness, "is_score_ready", ready)
        object.__setattr__(readiness, "reason_codes", ())
        object.__setattr__(readiness, "readiness_fingerprint", "forged-readiness")
    object.__setattr__(result, "scoring_readiness", readiness)

    features = object.__new__(NormalizedLocationFeatures) if normalized else None
    object.__setattr__(result, "normalized_features", features)
    return result


def _manual_app_result(result: RealDataPipelineResult) -> ApplicationPipelineResult:
    value = object.__new__(ApplicationPipelineResult)
    object.__setattr__(value, "pipeline_result", result)
    return value


def test_not_score_ready_and_pipeline_error_remain_fail_closed():
    not_ready = _terminal_shell(PipelineStatus.NOT_SCORE_READY, ready=False, normalized=True)
    error = _terminal_shell(PipelineStatus.PIPELINE_ERROR, ready=None, normalized=False)

    assert evaluate_application_scoring_gate(not_ready).state is ApplicationScoringGateState.NOT_SCORE_READY
    assert evaluate_application_scoring_gate(error).state is ApplicationScoringGateState.PIPELINE_ERROR

    # Raw terminal DTOs are diagnostic inputs only, never scoring authority.
    with pytest.raises(TypeError):
        build_application_scoring_input(not_ready)
    with pytest.raises(TypeError):
        build_application_scoring_input(error)


def test_app_h001_forged_score_ready_terminal_cannot_authorize_scoring():
    forged = _terminal_shell(PipelineStatus.SCORE_READY, ready=True, normalized=True)

    # Shape inspection may describe it as eligible, but eligibility is not authority.
    assert evaluate_application_scoring_gate(forged).is_eligible is True
    with pytest.raises(TypeError, match="ApplicationPipelineResult"):
        build_application_scoring_input(forged)  # type: ignore[arg-type]


def test_app_h001_manual_wrapper_around_forged_terminal_is_not_authority():
    forged = _terminal_shell(PipelineStatus.SCORE_READY, ready=True, normalized=True)
    manual = _manual_app_result(forged)

    with pytest.raises(ValueError, match="not canonical"):
        require_canonical_application_pipeline_result(manual)
    with pytest.raises(ValueError, match="not canonical"):
        build_application_scoring_input(manual)


def test_app_h001_forged_readiness_evaluation_cannot_enter_app_owned_pipeline_path():
    forged_readiness = object.__new__(ReadinessEvaluation)
    object.__setattr__(forged_readiness, "result", object.__new__(ScoringReadinessResult))

    # The app factory delegates to the closure-captured frozen terminal factory.
    # That factory rejects readiness objects not produced by its own canonical factory
    # before any terminal DTO can be registered by the app.
    with pytest.raises(TypeError, match="exact object returned by canonical"):
        build_application_pipeline_result(
            readiness=forged_readiness,
            sector_key=None,  # type: ignore[arg-type]
            resolved_location=None,
            derived_metrics=None,  # type: ignore[arg-type]
            source_metadata=(),
            generated_at=None,  # type: ignore[arg-type]
        )


def test_app_h001_copied_terminal_fields_do_not_transfer_authority():
    original = _terminal_shell(PipelineStatus.SCORE_READY, ready=True, normalized=True)
    copied = _terminal_shell(PipelineStatus.SCORE_READY, ready=True, normalized=True)
    assert copied is not original
    assert copied.status == original.status
    assert copied.scoring_readiness.is_score_ready is True  # type: ignore[union-attr]

    with pytest.raises(TypeError):
        build_application_scoring_input(copied)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        build_application_scoring_input(_manual_app_result(copied))


def test_detached_status_readiness_fingerprint_and_features_are_not_factory_inputs():
    signature = inspect.signature(build_application_scoring_input)
    assert tuple(signature.parameters) == ("application_pipeline_result",)
    for forbidden in (
        "pipeline_result",
        "ready",
        "is_ready",
        "is_score_ready",
        "force",
        "skip_readiness",
        "status",
        "readiness_fingerprint",
        "normalized_features",
        "category_scores",
        "location_score",
    ):
        assert forbidden not in signature.parameters


def test_application_pipeline_and_scoring_constructors_are_not_authority():
    with pytest.raises(TypeError):
        ApplicationPipelineResult()
    with pytest.raises(TypeError):
        ApplicationScoringInput()

    forged_scoring = object.__new__(ApplicationScoringInput)
    object.__setattr__(
        forged_scoring,
        "application_pipeline_result",
        _manual_app_result(_terminal_shell(PipelineStatus.SCORE_READY, ready=True, normalized=True)),
    )
    with pytest.raises(ValueError, match="not canonical"):
        require_canonical_application_scoring_input(forged_scoring)


def test_frozen_terminal_factory_is_closure_captured_not_module_authority_surface():
    assert "canonical_terminal_factory" not in vars(gating)
    assert "_install_application_factories" not in vars(gating)
    for forbidden in ("_PIPELINE_TOKEN", "_TRUSTED_PIPELINE_RESULT", "trusted"):
        assert forbidden not in vars(gating)


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
