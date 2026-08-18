from __future__ import annotations

import ast
from pathlib import Path
import tomllib

from sitescore_report import ReportFinancialFacts, ReportRevenueFacts

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
SRC_ROOT = PACKAGE_ROOT / "src" / "sitescore_report"


def test_package_dependency_contract_is_exact_and_directional():
    project = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
    assert project["project"]["name"] == "sitescore-report"
    assert project["project"]["version"] == "0.2.0"
    assert project["project"]["dependencies"] == [
        "sitescore-app==0.1.0",
        "sitescore-core==0.1.0",
        "openai==3.2.0",
        "pydantic==2.13.4",
    ]
    assert project["project"]["optional-dependencies"]["dev"] == ["pytest==8.4.2"]

    forbidden_dependencies = (
        "jinja", "weasyprint", "matplotlib", "boto", "sqlalchemy",
        "alembic", "celery", "redis", "fastapi", "stripe", "sitescore-api",
    )
    rendered = repr(project["project"]["dependencies"] + project["project"]["optional-dependencies"]["dev"]).lower()
    assert all(name not in rendered for name in forbidden_dependencies)


def test_production_imports_do_not_bypass_application_or_add_rendering_runtime():
    forbidden_modules = {
        "sitescore.analyze",
        "sitescore.engines",
        "sitescore_api",
        "jinja2",
        "weasyprint",
        "matplotlib",
        "boto3",
        "sqlalchemy",
        "alembic",
        "celery",
        "redis",
        "fastapi",
        "stripe",
    }
    for path in SRC_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert not any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for forbidden in forbidden_modules
                ), (path, name)


def test_narrative_production_surface_has_no_rendering_or_html_authority():
    narrative = (SRC_ROOT / "narrative.py").read_text().lower()
    assert "sitescore.analyze" not in narrative
    assert "sitescore.engines" not in narrative
    assert "sitescore_api" not in narrative
    assert "jinja" not in narrative
    assert "weasyprint" not in narrative
    assert "matplotlib" not in narrative
    assert "boto3" not in narrative
    assert "stripe" not in narrative
    assert "n8n" not in narrative
    assert "<html" not in narrative
    assert "<style" not in narrative


def test_frozen_and_locked_upstream_packages_do_not_import_report_package():
    upstream = (
        "sitescore-core",
        "sitescore-data",
        "sitescore-providers",
        "sitescore-spatial",
        "sitescore-metrics",
        "sitescore-benchmarks",
        "sitescore-pipeline",
        "sitescore-app",
        "sitescore-api",
    )
    for package in upstream:
        source_root = REPO_ROOT / package / "src"
        if not source_root.exists():
            continue
        for path in source_root.rglob("*.py"):
            text = path.read_text()
            assert "sitescore_report" not in text, path
            assert "sitescore-report" not in text, path


def test_optional_none_financial_fact_remains_none_without_presentation_default():
    facts = ReportFinancialFacts(
        revenue=ReportRevenueFacts(conservative=1.0, base=2.0, optimistic=3.0),
        variable_cost_base=0.5,
        contribution_margin_base=1.5,
        fixed_costs=1.0,
        operating_profit_base=0.5,
        break_even_revenue=1.0,
        bec_base=2.0,
        bec_conservative=1.0,
        rent_burden_pct=10.0,
        rent_burden_severity="normal",
        operating_margin_pct=25.0,
        break_even_volume=None,
        stress_test_failed=False,
    )
    assert facts.break_even_volume is None
