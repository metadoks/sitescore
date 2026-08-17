from __future__ import annotations

import ast
import tomllib
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PACKAGE_ROOT / "src" / "sitescore_api"
REPO_ROOT = PACKAGE_ROOT.parent


def test_production_core_imports_are_limited_to_frozen_schema_config_types():
    allowed = {
        "sitescore.config.sectors",
        "sitescore.schemas.revenue_inputs",
    }
    for path in SRC_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom):
                module = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("sitescore"):
                        assert alias.name in allowed, f"forbidden core import {alias.name} in {path.name}"
            if module and module.startswith("sitescore"):
                assert module in allowed, f"forbidden core import {module} in {path.name}"


def test_no_direct_analyze_or_engine_imports():
    source = "\n".join(path.read_text(encoding="utf-8") for path in SRC_ROOT.glob("*.py"))
    assert "sitescore.analyze" not in source
    assert "sitescore.engines" not in source


def test_route_layer_contains_no_arithmetic_formula_logic():
    tree = ast.parse((SRC_ROOT / "routes.py").read_text(encoding="utf-8"))
    forbidden_nodes = (ast.BinOp, ast.AugAssign)
    assert not any(isinstance(node, forbidden_nodes) for node in ast.walk(tree))


def test_default_lifecycle_uses_no_process_local_persistence_container():
    tree = ast.parse((SRC_ROOT / "lifecycle.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Dict, ast.DictComp, ast.ListComp, ast.SetComp)):
            raise AssertionError("default lifecycle module must not create process-local persistence containers")


def test_dependency_contract_is_exact_and_contains_no_5_1_or_later_stack():
    data = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == [
        "fastapi==0.140.0",
        "pydantic==2.13.4",
        "sitescore-core==0.1.0",
    ]
    assert data["project"]["optional-dependencies"]["dev"] == [
        "httpx==0.28.1",
        "pytest==8.4.2",
    ]
    rendered = str(data).lower()
    for forbidden in [
        "sqlalchemy",
        "alembic",
        "celery",
        "redis",
        "openai",
        "jinja2",
        "weasyprint",
        "matplotlib",
        "boto3",
        "stripe",
        "psycopg",
    ]:
        assert forbidden not in rendered


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
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "sitescore_api" not in text
