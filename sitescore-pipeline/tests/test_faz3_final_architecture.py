from __future__ import annotations

import ast
from pathlib import Path
import tomllib

from sitescore_benchmarks import (
    AGE_TARGET_CONCENTRATION_FALLBACK_V1,
    APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1,
    COMB005_V1_POLICY,
    RoadParkingPolicyApprovalState,
)
from sitescore_data.schemas import DerivedLocationMetrics, NormalizedLocationFeatures


REPO_ROOT = Path(__file__).resolve().parents[2]

PACKAGE_DIRS = {
    "sitescore_core": "sitescore-core",
    "sitescore_data": "sitescore-data",
    "sitescore_providers": "sitescore-providers",
    "sitescore_spatial": "sitescore-spatial",
    "sitescore_metrics": "sitescore-metrics",
    "sitescore_benchmarks": "sitescore-benchmarks",
    "sitescore_pipeline": "sitescore-pipeline",
}

EXPECTED_RUNTIME_DEPS = {
    "sitescore-core": set(),
    "sitescore-data": set(),
    "sitescore-providers": {"sitescore-data==0.1.0"},
    "sitescore-spatial": {"shapely==2.1.2", "pyproj==3.7.2"},
    "sitescore-metrics": {
        "sitescore-data==0.1.0",
        "sitescore-providers==0.1.0",
        "sitescore-spatial==0.1.0",
    },
    "sitescore-benchmarks": {"sitescore-spatial==0.1.0", "sitescore-metrics==0.1.0"},
    "sitescore-pipeline": {"sitescore-data==0.1.0", "sitescore-benchmarks==0.1.0"},
}

ALLOWED_IMPORTS = {
    "sitescore_core": set(),
    "sitescore_data": set(),
    "sitescore_providers": {"sitescore_data"},
    "sitescore_spatial": set(),
    "sitescore_metrics": {"sitescore_data", "sitescore_providers", "sitescore_spatial"},
    "sitescore_benchmarks": {"sitescore_spatial", "sitescore_metrics"},
    "sitescore_pipeline": {"sitescore_data", "sitescore_benchmarks"},
}

DERIVED_V1_METRICS = {
    "walkable_population",
    "target_population_density",
    "household_income",
    "household_income_ratio",
    "competition_pressure",
    "walkable_reach_area_km2",
    "transit_service_departure_equivalents_per_hour",
    "road_reachable_area_km2",
    "parking_public_offstreet_capacity",
    "parking_legal_curb_length_m",
}

NORMALIZED_V1_FEATURES = {
    "walkable_population_score",
    "target_population_density_score",
    "age_target_concentration_score",
    "competition_opportunity_score",
    "walkable_reach_area_score",
    "transit_access_score",
    "road_parking_access_score",
    "household_income_score",
}


def _source_files(package_dir: str):
    return tuple((REPO_ROOT / package_dir / "src").rglob("*.py"))


def _source_text(package_dir: str) -> str:
    return "\n".join(path.read_text() for path in _source_files(package_dir))


def _external_imports(package_name: str, package_dir: str) -> set[str]:
    found: set[str] = set()
    for path in _source_files(package_dir):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("sitescore_"):
                root = node.module.split(".", 1)[0]
                if root != package_name:
                    found.add(root)
            elif isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("sitescore_"):
                        root = item.name.split(".", 1)[0]
                        if root != package_name:
                            found.add(root)
    return found


def test_faz3_exact_runtime_dependency_dag_and_versions():
    for package_dir, expected in EXPECTED_RUNTIME_DEPS.items():
        project = tomllib.loads((REPO_ROOT / package_dir / "pyproject.toml").read_text())
        assert project["project"]["version"] == "0.1.0"
        assert set(project["project"].get("dependencies", [])) == expected


def test_faz3_source_import_graph_has_no_reverse_edges_or_core_leakage():
    for package_name, package_dir in PACKAGE_DIRS.items():
        actual = _external_imports(package_name, package_dir)
        assert actual <= ALLOWED_IMPORTS[package_name], (package_name, actual)
    for package_name, package_dir in PACKAGE_DIRS.items():
        if package_name != "sitescore_pipeline":
            assert "sitescore_pipeline" not in _source_text(package_dir)
        if package_name != "sitescore_core":
            assert "sitescore_core" not in _source_text(package_dir)


def test_frozen_data_v1_surfaces_retain_exact_metric_and_feature_slots():
    derived_annotations = set(DerivedLocationMetrics.__annotations__)
    normalized_annotations = set(NormalizedLocationFeatures.__annotations__)
    assert {name for name in derived_annotations if name in DERIVED_V1_METRICS} == DERIVED_V1_METRICS
    assert {name for name in normalized_annotations if name.endswith("_score")} == NORMALIZED_V1_FEATURES


def test_provider_layer_remains_evidence_only_and_contains_all_frozen_families():
    root = REPO_ROOT / "sitescore-providers" / "src" / "sitescore_providers"
    for family in ("acs", "census", "overture", "pedestrian", "transit", "road", "parking"):
        assert (root / family).is_dir(), family
    text = _source_text("sitescore-providers")
    for forbidden in (
        "sitescore_benchmarks",
        "sitescore_pipeline",
        "sitescore_core",
        "NormalizedLocationFeatures",
        "RealDataPipelineResult",
        "CategoryScores",
        "road_parking_access_score",
    ):
        assert forbidden not in text
    for required in ("content_hash", "request_fingerprint", "source_id"):
        assert required in text


def test_global_no_hidden_missingness_or_empirical_shortcuts():
    text = "\n".join(_source_text(package_dir) for package_dir in PACKAGE_DIRS.values()).lower()
    for forbidden in (
        "missing_to_zero",
        "fill_missing_with_zero",
        "neutral_missing_fallback",
        "renormalize_missing",
        "default_road_weight",
        "default_parking_weight",
        "road_parking_50_50",
        "coverage_threshold =",
        "minimum_n =",
        "default_equal_area_crs",
        "default_cell_resolution",
    ):
        assert forbidden not in text


def test_age_fallback_and_comb005_authority_remain_exact():
    age = AGE_TARGET_CONCENTRATION_FALLBACK_V1
    assert age.policy_id == "age_neutral_fallback"
    assert age.policy_version == "1.0"
    assert age.score == 50.0
    assert age.calibration_state == "uncalibrated"
    assert age.is_proxy is True
    assert age.reason_code == "age_affinity_not_calibrated"
    assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()
    assert COMB005_V1_POLICY.approval_state is RoadParkingPolicyApprovalState.NOT_APPROVED
    assert COMB005_V1_POLICY.weights == ()
    assert COMB005_V1_POLICY.composition_method == "UNRESOLVED"


def test_no_faz4_or_product_execution_leaks_into_real_data_packages():
    text = "\n".join(_source_text(package_dir) for package_dir in PACKAGE_DIRS.values()).lower()
    for forbidden in (
        "fastapi",
        "flask",
        "stripe",
        "paypal",
        "reportlab",
        "weasyprint",
        "core.analyze(",
        "paymentworkflow",
        "decisionlayer",
        "reportpdf",
    ):
        assert forbidden not in text


def test_phase_freeze_records_and_34_final_guard_are_present():
    assert (REPO_ROOT / "sitescore-data" / "docs" / "FAZ3_2_FREEZE_RECORD.md").is_file()
    assert (REPO_ROOT / "sitescore-providers" / "docs" / "FAZ3_3_PROVIDER_FREEZE_RECORD.md").is_file()
    assert (REPO_ROOT / "docs" / "FAZ3_4_FINAL_AUDIT_FREEZE_CANDIDATE.md").is_file()
    assert (REPO_ROOT / "sitescore-pipeline" / "tests" / "test_final_phase_architecture.py").is_file()
