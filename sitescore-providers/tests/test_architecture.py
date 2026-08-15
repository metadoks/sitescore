from __future__ import annotations

import ast
from pathlib import Path

import sitescore_data

from sitescore_providers.baseline import (
    EXPECTED_SITESCORE_DATA_COMMIT,
    EXPECTED_SITESCORE_DATA_TAG,
    EXPECTED_SITESCORE_DATA_TESTS,
    EXPECTED_SITESCORE_DATA_VERSION,
    assert_sitescore_data_compatibility,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "sitescore_providers"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_frozen_data_runtime_version_guard():
    assert sitescore_data.PACKAGE_VERSION == "0.1.0"
    assert EXPECTED_SITESCORE_DATA_VERSION == "0.1.0"
    assert EXPECTED_SITESCORE_DATA_COMMIT == "f03cbb71bd93c5a3afd78b43991e456595a7f75d"
    assert EXPECTED_SITESCORE_DATA_TAG == "sitescore-data-v0.1.0"
    assert EXPECTED_SITESCORE_DATA_TESTS == 361
    assert_sitescore_data_compatibility()


def test_no_sitescore_core_imports():
    forbidden = {"sitescore", "sitescore_core"}
    for path in SRC.rglob("*.py"):
        for name in _imports(path):
            root = name.split(".", 1)[0]
            assert root not in forbidden, f"forbidden core import {name} in {path}"


def test_http_boundary_uses_stdlib_only_and_no_storage_dependencies():
    external_forbidden = {"requests", "httpx", "aiohttp", "boto3", "psycopg", "sqlalchemy"}
    for path in SRC.rglob("*.py"):
        for name in _imports(path):
            root = name.split(".", 1)[0]
            assert root not in external_forbidden, f"external network/storage dependency {name} in {path}"
            if root in {"urllib", "socket"}:
                allowed = path.name == "http.py" or (path.parent.name in {"pedestrian", "road"} and path.name == "client.py")
                assert allowed, f"stdlib network import must stay behind approved transport boundary: {name} in {path}"


def test_runtime_dependencies_only_sitescore_data():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"sitescore-data==0.1.0"' in text
    for forbidden in ("sitescore-core", "requests", "httpx", "aiohttp", "boto3", "sqlalchemy"):
        assert forbidden not in text


def test_only_in_scope_provider_implementations_exist():
    production_text = "\n".join(path.read_text(encoding="utf-8").lower() for path in SRC.rglob("*.py"))
    for provider_specific in ("google", "mapbox", "mobilitydatabase"):
        assert provider_specific not in production_text
    assert (SRC / "census").is_dir()
    assert (SRC / "acs").is_dir()
    assert (SRC / "overture").is_dir()
    assert (SRC / "pedestrian").is_dir()
    assert (SRC / "transit").is_dir()


def test_no_out_of_scope_domain_provider_modules_exist():
    forbidden_names = {"valhalla.py", "gtfs.py", "parking.py", "osm.py", "mapbox.py"}
    assert not forbidden_names.intersection(path.name for path in SRC.rglob("*.py"))
