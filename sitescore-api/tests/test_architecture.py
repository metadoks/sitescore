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
    assert not any(isinstance(node, (ast.BinOp, ast.AugAssign)) for node in ast.walk(tree))


def test_postgresql_is_lifecycle_truth_and_celery_async_result_is_absent():
    source = _source()
    assert "AsyncResult" not in source
    assert "create_all(" not in source
    assert "task_ignore_result=True" in (SRC_ROOT / "celery_app.py").read_text(encoding="utf-8")
    lifecycle = (SRC_ROOT / "lifecycle.py").read_text(encoding="utf-8")
    assert "AnalysisModel" in lifecycle
    assert "DispatchOutboxModel" in lifecycle


def test_completed_authority_cannot_be_arbitrary_json():
    outcomes = (SRC_ROOT / "outcomes.py").read_text(encoding="utf-8")
    lifecycle = (SRC_ROOT / "lifecycle.py").read_text(encoding="utf-8")
    assert "ApplicationAnalysisResult" in outcomes
    assert "require_canonical_application_analysis_result" in outcomes
    assert "CanonicalCompletedOutcome" in lifecycle
    assert "def complete(" not in lifecycle
    assert "arbitrary_dict" not in lifecycle


def test_worker_payload_and_execution_lock_are_internal_and_postgresql_backed():
    dispatcher = (SRC_ROOT / "dispatcher.py").read_text(encoding="utf-8")
    worker = (SRC_ROOT / "worker.py").read_text(encoding="utf-8")
    assert 'args=[str(analysis_id)]' in dispatcher
    assert "Authorization" not in dispatcher
    assert "api_key" not in dispatcher.lower()
    assert "pg_try_advisory_lock" in worker
    assert "redis" not in worker.lower()


def test_dependency_contract_is_exact():
    data = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == "0.2.0"
    assert data["project"]["dependencies"] == [
        "fastapi==0.140.0",
        "pydantic==2.13.4",
        "SQLAlchemy==2.0.51",
        "alembic==1.18.5",
        "psycopg[binary]==3.3.4",
        "celery==5.6.3",
        "redis==7.4.1",
        "sitescore-core==0.1.0",
        "sitescore-data==0.1.0",
        "sitescore-metrics==0.1.0",
        "sitescore-benchmarks==0.1.0",
        "sitescore-pipeline==0.1.0",
        "sitescore-app==0.1.0",
    ]
    assert data["project"]["optional-dependencies"]["dev"] == [
        "httpx==0.28.1",
        "pytest==8.4.2",
    ]


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


def test_no_5_2_or_later_scope_dependencies():
    rendered = (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    for forbidden in ("openai", "jinja2", "weasyprint", "matplotlib", "boto3", "stripe"):
        assert forbidden not in rendered
