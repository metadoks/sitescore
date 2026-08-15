from pathlib import Path
import ast

def source_text():
    root=Path(__file__).parents[1]/'src'/'sitescore_benchmarks'
    return '\n'.join(p.read_text() for p in root.glob('*.py'))

def test_no_forbidden_domain_imports():
    text=source_text()
    for name in ('sitescore_core','sitescore_metrics','sitescore_pipeline','sitescore_data','sitescore_providers'):
        assert name not in text

def test_provider_neutral_no_structural_provider_schema():
    text=source_text().lower()
    for token in ('overture','google_places','tigerline','census_api','openstreetmap','osm_'):
        assert token not in text

def test_no_metrics_ecdf_normalization_scope():
    text=source_text()
    for token in ('walkable_population','competition_pressure','mid_ecdf','NormalizedLocationFeatures','COMB-005','ScoringReadiness','RealDataPipelineResult','analyze('):
        assert token not in text

def test_only_sitescore_spatial_domain_imported():
    root=Path(__file__).parents[1]/'src'/'sitescore_benchmarks'
    imports=set()
    for p in root.glob('*.py'):
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('sitescore_'): imports.add(n.module.split('.')[0])
            if isinstance(n,ast.Import):
                for x in n.names:
                    if x.name.startswith('sitescore_'): imports.add(x.name.split('.')[0])
    assert imports <= {'sitescore_spatial'}

def test_no_hidden_production_constants():
    text=source_text()
    for token in ('250.0','500.0','1000.0','centroid','representative_point','majority_overlap','overlap_threshold'):
        assert token not in text
