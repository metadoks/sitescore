from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'sitescore_providers'

def roots(path):
    tree=ast.parse(path.read_text()); out=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): out.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: out.add(n.module.split('.')[0])
    return out

def test_runtime_dependency_remains_sitescore_data_only():
    text=(ROOT/'pyproject.toml').read_text().lower()
    assert '"sitescore-data==0.1.0"' in text
    for x in ('requests','httpx','aiohttp','shapely','geopandas','pyproj','duckdb','pandas','sitescore-core'):
        assert x not in text

def test_parking_uses_no_third_party_or_core():
    imported=set().union(*(roots(p) for p in (SRC/'parking').glob('*.py')))
    for x in ('requests','httpx','aiohttp','shapely','geopandas','pyproj','duckdb','pandas','sitescore_core'):
        assert x not in imported

def test_parking_scope_has_no_composite_ecdf_or_normalization():
    text='\n'.join(p.read_text().lower() for p in (SRC/'parking').glob('*.py'))
    assert 'road_parking_access_score' not in text
    assert 'ecdf' not in text
    assert 'percentile' not in text
    assert 'normalized_parking_score' not in text

def test_no_future_app_core_adapter_modules():
    parts={part.lower() for p in SRC.rglob('*.py') for part in p.parts}
    assert 'sitescore_app' not in parts
    assert 'core_adapter' not in parts
