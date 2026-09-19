from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"/"sitescore_providers"


def imports(path):
    tree=ast.parse(path.read_text())
    result=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): result.extend(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module: result.append(node.module)
    return result


def test_runtime_dependency_stays_sitescore_data_only():
    text=(ROOT/"pyproject.toml").read_text().lower()
    assert '"sitescore-data==0.1.0"' in text
    for package in ("httpx","requests","aiohttp","shapely","geopandas","pyproj","duckdb","boto3"):
        assert package not in text


def test_pedestrian_uses_stdlib_only_and_no_core():
    external={"httpx","requests","aiohttp","shapely","geopandas","pyproj","duckdb","boto3"}
    for path in (SRC/"pedestrian").glob("*.py"):
        roots={name.split('.')[0] for name in imports(path)}
        assert not roots.intersection(external)
        assert "sitescore_core" not in roots and "sitescore" not in roots


def test_out_of_scope_provider_modules_absent():
    names={p.name.lower() for p in SRC.rglob("*.py")}
    assert not {"gtfs.py","road.py","parking.py"}.intersection(names)
