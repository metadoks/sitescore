from __future__ import annotations

import ast
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "sitescore_data"
PROVIDER_ROOTS = {"requests", "httpx", "aiohttp", "urllib3"}


def _module_name(path: Path) -> str:
    relative = path.relative_to(ROOT / "src").with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _dependency_graph() -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
    module_paths = {
        _module_name(path): path
        for path in SRC.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    graph = {name: set() for name in module_paths}
    provider_imports: list[tuple[str, str]] = []

    for name, path in module_paths.items():
        is_package = path.name == "__init__.py"
        current_package = name if is_package else name.rsplit(".", 1)[0]
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base_parts = current_package.split(".") if current_package else []
                    up = node.level - 1
                    if up:
                        base_parts = base_parts[:-up]
                    if node.module:
                        base_parts.extend(node.module.split("."))
                    targets.append(".".join(base_parts))
                elif node.module:
                    targets.append(node.module)

            for target in targets:
                root = target.split(".", 1)[0]
                if root in PROVIDER_ROOTS:
                    provider_imports.append((name, target))
                if target == "sitescore" or target.startswith("sitescore."):
                    raise AssertionError(f"forbidden core import: {name} -> {target}")
                matches = [
                    candidate
                    for candidate in module_paths
                    if target == candidate or target.startswith(candidate + ".")
                ]
                if matches:
                    candidate = max(matches, key=len)
                    if candidate != name:
                        graph[name].add(candidate)

    return graph, provider_imports


def test_final_freeze_dependency_graph_has_no_cycles_or_provider_dependencies() -> None:
    graph, provider_imports = _dependency_graph()
    assert provider_imports == []

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise AssertionError(f"circular dependency detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def test_final_freeze_runtime_dependencies_remain_empty() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == []
