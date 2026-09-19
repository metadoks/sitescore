from pathlib import Path
import re


def test_no_site_domain_imports():
    root = Path(__file__).parents[1] / "src" / "sitescore_spatial"
    forbidden = (
        "sitescore_data", "sitescore_providers", "sitescore_core", "sitescore_benchmarks",
        "sitescore_metrics", "sitescore_pipeline", "import sitescore", "from sitescore",
    )
    text = "\n".join(p.read_text() for p in root.glob("*.py"))
    for token in forbidden:
        assert token not in text


def test_no_benchmark_or_scoring_modules_exist():
    root = Path(__file__).parents[1] / "src" / "sitescore_spatial"
    names = {p.name for p in root.glob("*.py")}
    assert "benchmarks.py" not in names
    assert "normalization.py" not in names
    assert "readiness.py" not in names
    assert "pipeline.py" not in names
    assert "scoring.py" not in names


def test_direct_dependencies_are_only_approved_pair():
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    assert '"shapely==2.1.2"' in pyproject
    assert '"pyproj==3.7.2"' in pyproject
    for forbidden in ("geopandas", "pandas", "h3", "duckdb", "rasterio", "fiona"):
        assert forbidden not in pyproject.lower()
