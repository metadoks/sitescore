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
    "sitescore-benchmarks": {
        "sitescore-spatial==0.1.0",
        "sitescore-metrics==0.1.0",
    },
    "sitescore-pipeline": {
        "sitescore-data==0.1.0",
        "sitescore-benchmarks==0.1.0",
    },
}

ALLOWED_SITESCORE_IMPORTS = {
    "sitescore_core": set(),
    "sitescore_data": set(),
    "sitescore_providers": {"sitescore_data"},
    "sitescore_spatial": set(),
    "sitescore_metrics": {"sitescore_data", "sitescore_providers", "sitescore_spatial"},
    "sitescore_benchmarks": {"sitescore_spatial", "sitescore_metrics"},
    "sitescore_pipeline": {"sitescore_data", "sitescore_benchmarks"},
}


def _source_files(package_dir: str):
    return tuple((REPO_ROOT / package_dir / "src").rglob("*.py"))


def _external_sitescore_imports(package_name: str, package_dir: str) -> set[str]:
    imports: set[str] = set()
    for path in _source_files(package_dir):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("sitescore_"):
                root = node.module.split(".", 1)[0]
                if root != package_name:
                    imports.add(root)
            elif isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("sitescore_"):
                        root = item.name.split(".", 1)[0]
                        if root != package_name:
                            imports.add(root)
    return imports


def _source_text(package_dir: str) -> str:
    return "\n".join(path.read_text() for path in _source_files(package_dir))


def test_final_runtime_dependency_dag_is_exact_and_acyclic():
    for package_dir, expected in EXPECTED_RUNTIME_DEPS.items():
        project = tomllib.loads((REPO_ROOT / package_dir / "pyproject.toml").read_text())
        assert set(project["project"].get("dependencies", [])) == expected


def test_final_source_import_direction_matches_frozen_dag():
    for package_name, package_dir in PACKAGE_DIRS.items():
        actual = _external_sitescore_imports(package_name, package_dir)
        assert actual <= ALLOWED_SITESCORE_IMPORTS[package_name], (package_name, actual)


def test_pipeline_is_not_imported_by_any_upstream_package():
    for package_name, package_dir in PACKAGE_DIRS.items():
        if package_name == "sitescore_pipeline":
            continue
        assert "sitescore_pipeline" not in _source_text(package_dir)


def test_real_data_layers_do_not_leak_category_location_or_product_scoring():
    text = (_source_text("sitescore-benchmarks") + "\n" + _source_text("sitescore-pipeline")).lower()
    for token in (
        "categoryscores",
        "readycategoryscorepayload",
        "locationscore",
        "core.analyze",
        "decisionlayer",
        "dealbreakerpenalty",
        "reportpdf",
        "paymentworkflow",
    ):
        assert token not in text


def test_no_empirical_threshold_weight_or_neutralization_shortcuts_in_real_data_layers():
    text = (_source_text("sitescore-benchmarks") + "\n" + _source_text("sitescore-pipeline")).lower()
    for token in (
        "minimum_n",
        "minimum_sample",
        "coverage_threshold",
        "default_road_weight",
        "default_parking_weight",
        "renormalize_missing",
        "neutral_parking_fallback",
        "neutral_road_fallback",
        "missing_to_zero",
    ):
        assert token not in text


def test_comb005_canonical_production_authority_remains_unapproved():
    assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()
    assert COMB005_V1_POLICY.approval_state is RoadParkingPolicyApprovalState.NOT_APPROVED
    assert COMB005_V1_POLICY.weights == ()
    assert COMB005_V1_POLICY.composition_method == "UNRESOLVED"


def test_age_fallback_is_the_exact_single_frozen_numeric_uncalibrated_exception():
    policy = AGE_TARGET_CONCENTRATION_FALLBACK_V1
    assert policy.policy_id == "age_neutral_fallback"
    assert policy.policy_version == "1.0"
    assert policy.normalized_feature_key == "age_target_concentration_score"
    assert policy.score == 50.0
    assert policy.availability == "available"
    assert policy.score_eligibility == "eligible"
    assert policy.calibration_state == "uncalibrated"
    assert policy.is_proxy is True
    assert policy.reason_code == "age_affinity_not_calibrated"


def test_core_remains_isolated_from_all_other_sitescore_packages():
    core_imports = _external_sitescore_imports("sitescore_core", "sitescore-core")
    assert core_imports == set()
    for package_name, package_dir in PACKAGE_DIRS.items():
        if package_name == "sitescore_core":
            continue
        assert "sitescore_core" not in _source_text(package_dir)
