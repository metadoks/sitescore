from pathlib import Path
import ast
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "sitescore_data"


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


def test_no_implicit_nondeterministic_defaults_in_checkpoint2_source() -> None:
    forbidden_tokens = (
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "random.",
        "secrets.",
    )
    violations: list[tuple[Path, str]] = []

    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append((path, token))

    assert violations == []
