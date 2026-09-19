from __future__ import annotations
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"/"sitescore_providers"
def roots(path):
    tree=ast.parse(path.read_text()); out=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): out.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: out.add(n.module.split('.')[0])
    return out

def test_runtime_dependency_still_sitescore_data_only():
    text=(ROOT/"pyproject.toml").read_text()
    assert '"sitescore-data==0.1.0"' in text
    for x in ("pyarrow","geopandas","shapely","duckdb","boto3","httpx","requests","sitescore-core"):
        assert x not in text.lower()

def test_no_core_or_future_provider_dependencies():
    files=list(SRC.rglob("*.py")); imported=set().union(*(roots(p) for p in files))
    assert "sitescore_core" not in imported
    for x in ("pyarrow","geopandas","shapely","duckdb","boto3"):
        assert x not in imported
    parts={part.lower() for p in files for part in p.parts}
    for x in ("valhalla","gtfs","osm","mapbox"):
        assert x not in parts

def test_overture_reader_is_protocol_boundary_not_storage_backend():
    text=(SRC/"overture"/"reader.py").read_text().lower()
    assert "protocol" in text
    assert "s3 client" not in text and "azure client" not in text and "pyarrow" not in text
