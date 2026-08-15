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
    for x in ('pandas','partridge','gtfs_kit','requests','httpx','aiohttp','shapely','geopandas','duckdb','boto3','sitescore-core'):
        assert x not in text

def test_transit_uses_stdlib_and_data_contract_only():
    imported=set().union(*(roots(p) for p in (SRC/'transit').glob('*.py')))
    for x in ('pandas','partridge','gtfs_kit','requests','httpx','aiohttp','shapely','geopandas','duckdb','boto3','sitescore_core'):
        assert x not in imported

def test_no_future_domain_implementations_added():
    parts={part.lower() for p in SRC.rglob('*.py') for part in p.parts}
    for x in ('normalization','benchmark_ecdf'):
        assert x not in parts

def test_no_gtfs_realtime_implementation():
    transit='\n'.join(p.read_text().lower() for p in (SRC/'transit').glob('*.py'))
    assert 'tripupdate' not in transit
    assert 'vehicleposition' not in transit
    assert 'gtfs_realtime' not in transit

def test_no_stop_count_metric_substitution():
    builders=(SRC/'transit'/'builders.py').read_text().lower()
    assert 'reachable_stop_count' not in builders
