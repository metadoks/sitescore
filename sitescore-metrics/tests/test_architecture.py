from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'sitescore_metrics'

def test_dependency_boundary():
    p=tomllib.loads((ROOT/'pyproject.toml').read_text())
    assert p['project']['dependencies']==['sitescore-data==0.1.0','sitescore-providers==0.1.0','sitescore-spatial==0.1.0']

def test_forbidden_imports_and_scope_absent():
    text='\n'.join(p.read_text() for p in SRC.glob('*.py'))
    for banned in ('sitescore_core','sitescore_benchmarks','sitescore_pipeline'):
        assert banned not in text
    for banned in ('mid_ecdf','NormalizedLocationFeatures','COMB-005','ScoringReadiness','RealDataPipelineResult','CategoryScores','analyze('):
        assert banned not in text

def test_no_benchmark_distribution_code():
    names={p.name for p in SRC.glob('*.py')}
    assert not {'ecdf.py','normalization.py','distribution.py'} & names
