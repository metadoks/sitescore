from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "sitescore_providers"


def production_python_files():
    return list(SRC.rglob("*.py"))


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_no_sitescore_core_imports():
    assert all("sitescore_core" not in imported_roots(path) for path in production_python_files())


def test_no_out_of_scope_provider_implementations():
    forbidden = {"mapbox", "gtfs"}
    paths = {part.lower() for path in production_python_files() for part in path.parts}
    assert forbidden.isdisjoint(paths)


def test_runtime_dependencies_remain_sitescore_data_only():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"sitescore-data==0.1.0"' in text
    for package in ("httpx", "requests", "aiohttp", "boto3", "sqlalchemy"):
        assert package not in text.lower()


def test_http_implementation_is_stdlib_only():
    roots = set().union(*(imported_roots(path) for path in production_python_files()))
    assert "httpx" not in roots
    assert "requests" not in roots
    assert "aiohttp" not in roots


def test_checkpoint_3_3_1_foundation_files_remain_present():
    for name in (
        "artifacts.py", "baseline.py", "errors.py", "hashing.py", "identity.py",
        "lineage.py", "parsing.py", "policy.py", "results.py", "_validation.py",
    ):
        assert (SRC / name).exists()
