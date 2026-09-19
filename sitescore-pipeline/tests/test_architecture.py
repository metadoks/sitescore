from pathlib import Path
import inspect

import sitescore_pipeline.integration as integration


def test_pipeline_package_has_no_core_or_reverse_dependency_imports():
    source = Path(integration.__file__).read_text().lower()
    assert "sitescore_core" not in source
    assert "core.analyze" not in source
    assert "categoryscores" not in source
    assert "readycategoryscorepayload" not in source


def test_terminal_factory_derives_status_instead_of_accepting_it():
    params = inspect.signature(integration.build_real_data_pipeline_result).parameters
    assert "status" not in params
    assert "reason_codes" not in params


def test_readiness_factory_derives_summary_and_fingerprint():
    params = inspect.signature(integration.derive_scoring_readiness).parameters
    for forbidden in (
        "is_score_ready",
        "readiness_fingerprint",
        "missing_required_features",
        "uncalibrated_features",
        "incompatible_features",
        "reason_codes",
    ):
        assert forbidden not in params


def test_canonical_assembly_does_not_accept_arbitrary_normalized_feature_surface():
    params = inspect.signature(integration.assemble_normalized_location_features).parameters
    assert set(params) == {
        "direct_results",
        "age_fallback",
        "road_parking_result",
        "benchmark_bindings",
        "generated_at",
    }
    for forbidden in ("features", "metric_values", "scores", "status"):
        assert forbidden not in params


def test_pyproject_dependencies_are_one_way_and_exact_pinned():
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    text = pyproject.read_text()
    assert '"sitescore-data==0.1.0"' in text
    assert '"sitescore-benchmarks==0.1.0"' in text
    assert "sitescore-core" not in text
    assert "sitescore-pipeline" not in text.split("dependencies =", 1)[1]
