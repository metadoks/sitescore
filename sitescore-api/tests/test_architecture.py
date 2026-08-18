from __future__ import annotations

import ast
import tomllib
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PACKAGE_ROOT / "src" / "sitescore_api"
REPO_ROOT = PACKAGE_ROOT.parent


def _source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in SRC_ROOT.glob("*.py"))


def test_no_direct_core_analyze_or_engine_imports():
    source = _source()
    assert "sitescore.analyze" not in source
    assert "sitescore.engines" not in source


def test_route_layer_contains_no_scoring_formula_logic():
    tree = ast.parse((SRC_ROOT / "routes.py").read_text(encoding="utf-8"))
    arithmetic_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            assert not isinstance(node.op, arithmetic_ops)
        assert not isinstance(node, ast.AugAssign)


def test_postgresql_is_lifecycle_truth_and_celery_async_result_is_absent():
    source = _source()
    assert "AsyncResult" not in source
    assert "create_all(" not in source
    assert "task_ignore_result=True" in (SRC_ROOT / "celery_app.py").read_text(encoding="utf-8")
    lifecycle = (SRC_ROOT / "lifecycle.py").read_text(encoding="utf-8")
    assert "AnalysisModel" in lifecycle
    assert "DispatchOutboxModel" in lifecycle
    artifacts = (SRC_ROOT / "report_artifacts.py").read_text(encoding="utf-8")
    assert "ReportModel" in artifacts
    assert "redis" not in artifacts.lower()


def test_completed_and_report_authority_cannot_be_arbitrary_json_or_rerun():
    outcomes = (SRC_ROOT / "outcomes.py").read_text(encoding="utf-8")
    lifecycle = (SRC_ROOT / "lifecycle.py").read_text(encoding="utf-8")
    artifacts = (SRC_ROOT / "report_artifacts.py").read_text(encoding="utf-8")
    worker = (SRC_ROOT / "worker.py").read_text(encoding="utf-8")
    assert "ApplicationAnalysisResult" in outcomes
    assert "require_canonical_application_analysis_result" in outcomes
    assert "CanonicalCompletedOutcome" in lifecycle
    assert "require_canonical_completed_outcome(outcome)" in artifacts
    assert "canonical.application_analysis_result" in artifacts
    assert "build_canonical_report_facts(source)" in artifacts
    assert "result_body" not in artifacts
    assert "request_payload" not in artifacts
    assert "executor.execute" in worker
    assert worker.count("executor.execute") == 1
    assert "def complete(" not in lifecycle


def test_worker_payload_and_execution_lock_are_internal_and_postgresql_backed():
    dispatcher = (SRC_ROOT / "dispatcher.py").read_text(encoding="utf-8")
    worker = (SRC_ROOT / "worker.py").read_text(encoding="utf-8")
    assert 'args=[str(analysis_id)]' in dispatcher
    assert "Authorization" not in dispatcher
    assert "api_key" not in dispatcher.lower()
    assert "pg_try_advisory_lock" in worker
    assert "engine.connect()" in worker
    assert "redis" not in worker.lower()
    assert "outcome.completed" in worker
    assert "report_artifacts.generate" in worker


def test_production_runtime_cannot_load_post_provider_execution_evidence_plugin():
    runtime = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
    acquisition = (SRC_ROOT / "acquisition.py").read_text(encoding="utf-8")
    assert "SITESCORE_EVIDENCE_SOURCE_FACTORY" not in runtime
    assert "SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY" in runtime
    assert "type(deployment) is not CanonicalAcquisitionDeployment" in runtime
    assert "CanonicalProviderEvidenceSource(deployment)" in runtime
    for required in (
        "CensusGeocoderClient",
        "ACSClient",
        "PedestrianIsochroneClient",
        "parse_overture_partition",
        "parse_gtfs_zip",
        "BenchmarkArtifactLoader",
    ):
        assert required in acquisition
    assert "AnalysisRequest" not in acquisition
    assert "request_payload" not in acquisition


def test_dependency_contract_is_exact_and_directional():
    data = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == "0.3.0"
    assert data["project"]["dependencies"] == [
        "fastapi==0.140.0",
        "pydantic==2.13.4",
        "SQLAlchemy==2.0.51",
        "alembic==1.18.5",
        "psycopg[binary]==3.3.4",
        "celery==5.6.3",
        "redis==7.4.1",
        "boto3==1.43.55",
        "sitescore-core==0.1.0",
        "sitescore-data==0.1.0",
        "sitescore-providers==0.1.0",
        "sitescore-metrics==0.1.0",
        "sitescore-benchmarks==0.1.0",
        "sitescore-pipeline==0.1.0",
        "sitescore-app==0.1.0",
        "sitescore-report==0.3.0",
    ]
    assert data["project"]["optional-dependencies"]["dev"] == [
        "httpx==0.28.1",
        "pytest==8.4.2",
    ]
    report_source = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (REPO_ROOT / "sitescore-report").rglob("*.py")
    )
    assert "sitescore_api" not in report_source


def test_frozen_sibling_packages_do_not_import_sitescore_api():
    frozen = [
        "sitescore-core",
        "sitescore-data",
        "sitescore-providers",
        "sitescore-spatial",
        "sitescore-metrics",
        "sitescore-benchmarks",
        "sitescore-pipeline",
        "sitescore-app",
    ]
    for package in frozen:
        root = REPO_ROOT / package
        for path in root.rglob("*.py"):
            assert "sitescore_api" not in path.read_text(encoding="utf-8", errors="ignore")


def test_5_5_scope_does_not_introduce_commercial_or_orchestration_dependencies():
    rendered = (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    source = _source()
    for forbidden in ("stripe", "n8n"):
        assert forbidden not in rendered
        assert forbidden not in source.lower()
    artifacts = (SRC_ROOT / "report_artifacts.py").read_text(encoding="utf-8")
    assert "ACL=" not in artifacts
    assert "public-read" not in artifacts
