from pathlib import Path
import ast
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "sitescore_data"


def test_runtime_dependencies_remain_empty() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == []


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


def test_no_core_weight_or_config_duplication_in_features_source() -> None:
    text = (SRC / "schemas" / "features.py").read_text(encoding="utf-8")
    forbidden = (
        "DEMAND_SUBFEATURE_WEIGHTS",
        "ACCESSIBILITY_SUBFEATURE_WEIGHTS",
        "SECTOR_CATEGORY_WEIGHTS",
        "0.70",
        "0.40",
        "0.30",
        "0.20",
        "0.10",
    )
    for token in forbidden:
        assert token not in text


def test_no_implicit_nondeterministic_defaults_in_checkpoint5_source() -> None:
    text = (SRC / "schemas" / "features.py").read_text(encoding="utf-8")
    for token in (
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "random.",
        "secrets.",
    ):
        assert token not in text
