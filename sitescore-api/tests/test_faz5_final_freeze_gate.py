from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
SRC_ROOT = PACKAGE_ROOT / "src" / "sitescore_api"


def test_faz5_final_public_surface_scopes_and_transport_authority_are_closed():
    routes = (SRC_ROOT / "routes.py").read_text(encoding="utf-8")
    auth = (SRC_ROOT / "auth.py").read_text(encoding="utf-8")
    openapi_test = (PACKAGE_ROOT / "tests" / "test_openapi.py").read_text(encoding="utf-8")

    for route in (
        '"/analyses"',
        '"/analyses/{analysis_id}"',
        '"/reports"',
        '"/reports/{report_id}"',
        '"/reports/{report_id}/content"',
    ):
        assert route in routes

    assert 'ALL_SCOPES = frozenset({"analysis:write", "analysis:read", "report:write", "report:read"})' in auth
    assert 'scope="analysis:write"' in routes
    assert 'scope="analysis:read"' in routes
    assert 'scope="report:write"' in routes
    assert 'scope="report:read"' in routes
    assert "This endpoint never reconstructs authority from JSON and never reruns an analysis." in routes
    assert 'set(schema["paths"])' in openapi_test
    assert '"/v1/reports/{report_id}/content"' in openapi_test

    tree = ast.parse(routes)
    arithmetic_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            assert not isinstance(node.op, arithmetic_ops)
        assert not isinstance(node, ast.AugAssign)


def test_faz5_final_worker_report_and_durable_truth_authority_remain_directional():
    worker = (SRC_ROOT / "worker.py").read_text(encoding="utf-8")
    artifacts = (SRC_ROOT / "report_artifacts.py").read_text(encoding="utf-8")
    architecture = (PACKAGE_ROOT / "tests" / "test_architecture.py").read_text(encoding="utf-8")
    celery_app = (SRC_ROOT / "celery_app.py").read_text(encoding="utf-8")

    assert worker.count("executor.execute") == 1
    assert "CanonicalCompletedOutcome" in worker
    assert "report_artifacts.generate" in worker
    assert "analysis_advisory_key" in worker
    assert "pg_try_advisory_lock" in worker

    assert "require_canonical_completed_outcome(outcome)" in artifacts
    assert "canonical.application_analysis_result" in artifacts
    assert "build_canonical_report_facts(source)" in artifacts
    assert "result_body" not in artifacts
    assert "request_payload" not in artifacts
    assert "ReportModel" in artifacts
    assert "redis" not in artifacts.lower()

    assert "sitescore.analyze" in architecture
    assert "sitescore.engines" in architecture
    assert "sitescore_api" in architecture

    assert "task_ignore_result=True" in celery_app
    assert "task_acks_late=True" in celery_app
    assert "task_reject_on_worker_lost=True" in celery_app
    assert "backend=None" in celery_app
    assert '"sitescore_api.reconcile_timeouts"' in celery_app


def test_faz5_final_migration_and_terminal_artifact_contract_is_complete():
    versions = PACKAGE_ROOT / "alembic" / "versions"
    migration_1 = (versions / "0001_faz5_1_consumer_lifecycle.py").read_text(encoding="utf-8")
    migration_2 = (versions / "0002_faz5_5_report_artifact.py").read_text(encoding="utf-8")
    migration_3 = (versions / "0003_faz5_5_canonical_success_boundary.py").read_text(encoding="utf-8")
    models = (SRC_ROOT / "db_models.py").read_text(encoding="utf-8")
    lifecycle = (SRC_ROOT / "lifecycle.py").read_text(encoding="utf-8")

    assert 'revision: str = "0001_faz5_1"' in migration_1
    assert 'revision: str = "0002_faz5_5"' in migration_2
    assert "down_revision" in migration_2 and '"0001_faz5_1"' in migration_2
    assert 'revision: str = "0003_faz5_5"' in migration_3
    assert "down_revision" in migration_3 and '"0002_faz5_5"' in migration_3

    assert 'TERMINAL_STATES = ("completed", "not_score_ready", "failed", "timed_out")' in models
    assert 'REPORT_STATES = ("ready", "failed")' in models
    assert "canonical_success_at" in models
    assert "ck_canonical_success_before_deadline" in models
    assert "ck_canonical_success_state" in models
    assert "try_analysis_timeout_claim" in lifecycle
    assert "row.state not in TERMINAL_STATES" in lifecycle


def test_automation_consumer_handoff_is_durable_complete_and_non_authoritative():
    handoff = (REPO_ROOT / "AUTOMATION_CONSUMER_HANDOFF.md").read_text(encoding="utf-8")

    required = (
        "n8n is an orchestration consumer, not scoring/report truth authority.",
        "FAZ 5 does not contain the production n8n workflow itself.",
        "POST /v1/analyses",
        "GET  /v1/analyses/{analysis_id}",
        "POST /v1/reports",
        "GET  /v1/reports/{report_id}",
        "GET  /v1/reports/{report_id}/content",
        "analysis:write",
        "analysis:read",
        "report:write",
        "report:read",
        "Idempotency-Key",
        "Retry-After",
        "request_id",
        "analysis_id",
        "report_id",
        "queued",
        "running",
        "completed",
        "not_score_ready",
        "failed",
        "timed_out",
        "ready",
        "COMB-005",
        "NOT_APPROVED",
        "SHA-256",
        "%PDF-",
        "polling-only",
        "callback/webhook",
        "consumer-owned",
    )
    for value in required:
        assert value in handoff

    lowered = handoff.lower()
    assert "production n8n workflow itself" in lowered
    assert "must never calculate or override sitescore scoring" in lowered


def test_faz5_final_audit_artifact_preserves_scope_and_freeze_rules():
    audit = (PACKAGE_ROOT / "docs" / "FAZ5_FINAL_INTEGRATED_PRODUCT_AUDIT.md").read_text(
        encoding="utf-8"
    )
    for value in (
        "main@8f757b81c0cb69e5e6be62f45e94ff9a57432cca",
        "CanonicalCompletedOutcome",
        "CanonicalNotScoreReadyOutcome",
        "ValidatedReportNarrative",
        "PreparedReportArtifact",
        "CONTRACT_CHANGE_REQUIRED: 0",
        "DESIGN_DECISION_REVIEW_REQUIRED: 0",
        "ADDITIONAL_REOPEN_REQUIRED: 0",
        "production n8n workflow",
        "FAZ 6",
    ):
        assert value in audit
