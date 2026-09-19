from pathlib import Path
import ast
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "sitescore_data"
READINESS_SOURCE = SRC / "validators" / "readiness.py"


def test_sitescore_data_still_does_not_import_sitescore() -> None:
    violations: list[tuple[Path, str]] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "sitescore" or alias.name.startswith("sitescore."):
                        violations.append((path, alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "sitescore" or module.startswith("sitescore."):
                    violations.append((path, module))
    assert violations == []


def test_runtime_dependencies_remain_empty() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == []


def test_readiness_validator_has_no_implicit_nondeterminism_or_provider_access() -> None:
    text = READINESS_SOURCE.read_text(encoding="utf-8")
    forbidden_tokens = (
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "random.",
        "secrets.",
        "requests",
        "httpx",
        "aiohttp",
    )
    for token in forbidden_tokens:
        assert token not in text


def test_no_category_aggregation_or_core_weight_copy_in_readiness_source() -> None:
    text = READINESS_SOURCE.read_text(encoding="utf-8")
    forbidden_tokens = (
        "DEMAND_SUBFEATURE_WEIGHTS",
        "ACCESSIBILITY_SUBFEATURE_WEIGHTS",
        "SECTOR_CATEGORY_WEIGHTS",
        "CATEGORY_WEIGHTS",
    )
    for token in forbidden_tokens:
        assert token not in text

    tree = ast.parse(text)
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "create_ready_category_score_payload"
    )
    assert not any(
        isinstance(node, (ast.Add, ast.Mult, ast.Div))
        for node in ast.walk(factory)
    )


def test_readiness_modules_do_not_generate_current_time() -> None:
    for relative in (
        Path("schemas/readiness.py"),
        Path("validators/readiness.py"),
    ):
        text = (SRC / relative).read_text(encoding="utf-8")
        assert "datetime.now(" not in text
        assert "datetime.utcnow(" not in text
