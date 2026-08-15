from pathlib import Path
import ast
import tomllib


def source_root():
    return Path(__file__).parents[1] / "src" / "sitescore_benchmarks"


def source_text():
    return "\n".join(p.read_text() for p in source_root().glob("*.py"))


def test_no_forbidden_domain_imports():
    text = source_text()
    for name in ("sitescore_core", "sitescore_pipeline", "sitescore_data", "sitescore_providers"):
        assert name not in text


def test_provider_neutral_no_structural_provider_schema():
    text = source_text().lower()
    for token in ("overture", "google_places", "tigerline", "census_api", "openstreetmap", "osm_"):
        assert token not in text


def test_no_later_checkpoint_scope_after_feature_normalization():
    text = source_text().lower()
    for token in (
        "normalizedlocationfeatures",
        "road_parking_access_score",
        "scoringreadiness",
        "realdatapipelineresult",
        "categoryscores",
        "core.analyze",
    ):
        assert token not in text
    for token in (
        "road_weight",
        "parking_weight",
        "renormalize_missing",
        "neutral_parking_fallback",
        "neutral_road_fallback",
    ):
        assert token not in text


def test_only_approved_sitescore_dependencies_imported():
    imports = set()
    for p in source_root().glob("*.py"):
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("sitescore_"):
                imports.add(node.module.split(".")[0])
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("sitescore_"):
                        imports.add(item.name.split(".")[0])
    assert imports <= {"sitescore_spatial", "sitescore_metrics"}
    assert "sitescore_metrics" in imports


def test_metrics_dependency_is_exactly_pinned():
    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    dependencies = set(project["project"]["dependencies"])
    assert "sitescore-spatial==0.1.0" in dependencies
    assert "sitescore-metrics==0.1.0" in dependencies
    lock = (root / "requirements.lock").read_text().splitlines()
    assert "sitescore-spatial==0.1.0" in lock
    assert "sitescore-metrics==0.1.0" in lock


def test_no_hidden_production_constants():
    text = source_text().lower()
    for token in (
        "250.0", "500.0", "1000.0", "centroid", "representative_point",
        "majority_overlap", "overlap_threshold", "minimum_n", "coverage_threshold",
        "1e-6", "1e-9", "epsilon", "relative_tolerance", "absolute_tolerance",
    ):
        assert token not in text
