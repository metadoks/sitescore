from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_category_aggregation_authority_and_exact_frozen_weight_semantics():
    script = textwrap.dedent(
        r"""
        import inspect

        import sitescore_pipeline
        from sitescore_data.enums import (
            AvailabilityState,
            CalibrationState,
            DataQualityState,
            PipelineStatus,
            ScoreEligibility,
        )
        from sitescore_data.schemas.common import MetricValue
        from sitescore_data.schemas.features import NormalizedLocationFeatures
        from sitescore_data.schemas.pipeline import RealDataPipelineResult
        from sitescore_data.schemas.readiness import ScoringReadinessResult
        from sitescore_data.validation import SectorKey

        def score_metric(value, source_ref):
            return MetricValue(
                value=value,
                unit="score_0_100",
                availability=AvailabilityState.AVAILABLE,
                data_quality=DataQualityState.FULL,
                score_eligibility=ScoreEligibility.ELIGIBLE,
                calibration_state=CalibrationState.CALIBRATED,
                is_estimate=False,
                is_proxy=False,
                source_refs=(source_ref,),
                method_version="test/1",
                reason_codes=(),
            )

        def normalized_shell():
            value = object.__new__(NormalizedLocationFeatures)
            object.__setattr__(value, "walkable_population_score", score_metric(10.0, "test.walkable_population"))
            object.__setattr__(value, "target_population_density_score", score_metric(20.0, "test.target_density"))
            object.__setattr__(value, "age_target_concentration_score", score_metric(30.0, "test.age"))
            object.__setattr__(value, "competition_opportunity_score", score_metric(70.0, "test.competition"))
            object.__setattr__(value, "walkable_reach_area_score", score_metric(40.0, "test.walkable_reach"))
            object.__setattr__(value, "transit_access_score", score_metric(50.0, "test.transit"))
            object.__setattr__(value, "road_parking_access_score", score_metric(60.0, "test.road_parking"))
            object.__setattr__(value, "household_income_score", score_metric(80.0, "test.income"))
            return value

        def readiness_shell(fingerprint):
            value = object.__new__(ScoringReadinessResult)
            object.__setattr__(value, "is_score_ready", True)
            object.__setattr__(value, "reason_codes", ())
            object.__setattr__(value, "readiness_fingerprint", fingerprint)
            return value

        def terminal_shell(sector):
            terminal = object.__new__(RealDataPipelineResult)
            object.__setattr__(terminal, "status", PipelineStatus.SCORE_READY)
            object.__setattr__(terminal, "sector_key", SectorKey(sector))
            object.__setattr__(terminal, "scoring_readiness", readiness_shell(f"ready-{sector}"))
            object.__setattr__(terminal, "normalized_features", normalized_shell())
            return terminal

        terminals = []

        def controlled_terminal_factory(**_kwargs):
            if not terminals:
                raise AssertionError("controlled terminal queue is empty")
            return terminals.pop(0)

        # Test-only canonical SCORE_READY fixture. Production COMB-005 remains
        # unapproved; this only exercises downstream 4.1 mechanics.
        sitescore_pipeline.build_real_data_pipeline_result = controlled_terminal_factory

        import sitescore_app
        import sitescore_app.aggregation as aggregation
        from sitescore.config.sectors import Sector
        from sitescore_app import (
            ApplicationCategoryAggregationResult,
            ApplicationScoringInput,
            aggregate_application_category_scores,
            build_application_pipeline_result,
            build_application_scoring_input,
            require_canonical_application_category_aggregation_result,
        )

        def build_scoring(sector):
            terminal = terminal_shell(sector)
            terminals.append(terminal)
            app_result = build_application_pipeline_result(
                readiness=None,
                sector_key=None,
                resolved_location=None,
                derived_metrics=None,
                source_metadata=(),
                generated_at=None,
            )
            scoring_input = build_application_scoring_input(app_result)
            return terminal, scoring_input

        def expect_type_failure(callable_):
            try:
                callable_()
            except TypeError:
                return
            raise AssertionError("non-ApplicationScoringInput authority was accepted")

        def expect_value_failure(callable_):
            try:
                callable_()
            except ValueError:
                return
            raise AssertionError("forged or mutated authority was accepted")

        expected = {
            "coffee": (Sector.COFFEE, 14.0, 47.0),
            "restaurant": (Sector.RESTAURANT, 17.0, 49.0),
            "gym": (Sector.GYM, 20.0, 56.0),
            "beauty": (Sector.BEAUTY, 22.0, 56.0),
        }

        canonical_results = {}
        for sector_name, (sector_enum, expected_demand, expected_accessibility) in expected.items():
            terminal, scoring_input = build_scoring(sector_name)
            result = aggregate_application_category_scores(scoring_input)
            assert require_canonical_application_category_aggregation_result(result) is result
            assert result.application_scoring_input is scoring_input
            assert result.sector is sector_enum
            assert result.demand == expected_demand
            assert result.competition == 70.0
            assert result.accessibility == expected_accessibility
            assert result.economics == 80.0
            assert scoring_input.normalized_features is terminal.normalized_features
            canonical_results[sector_name] = (terminal, scoring_input, result)

        # Unsupported opaque data-layer SectorKey values fail closed with no alias,
        # default, case repair, fuzzy mapping, or neutral sector behavior.
        _, unsupported_scoring = build_scoring("retail")
        expect_value_failure(
            lambda: aggregate_application_category_scores(unsupported_scoring)
        )

        # Raw/detached data and core objects cannot invoke aggregation authority.
        expect_type_failure(lambda: aggregate_application_category_scores(terminal_shell("coffee")))
        expect_type_failure(lambda: aggregate_application_category_scores(normalized_shell()))
        expect_type_failure(lambda: aggregate_application_category_scores(SectorKey("coffee")))
        expect_type_failure(lambda: aggregate_application_category_scores(Sector.COFFEE))

        coffee_terminal, coffee_scoring, coffee_result = canonical_results["coffee"]

        # Manually allocated/copy-equivalent scoring inputs do not inherit authority.
        manual_scoring = object.__new__(ApplicationScoringInput)
        object.__setattr__(
            manual_scoring,
            "application_pipeline_result",
            coffee_scoring.application_pipeline_result,
        )
        expect_value_failure(lambda: aggregate_application_category_scores(manual_scoring))

        copied_scoring = object.__new__(ApplicationScoringInput)
        object.__setattr__(
            copied_scoring,
            "application_pipeline_result",
            coffee_scoring.application_pipeline_result,
        )
        expect_value_failure(lambda: aggregate_application_category_scores(copied_scoring))

        # Manually allocated/copy-equivalent category result shells are not authority.
        def category_shell(source):
            value = object.__new__(ApplicationCategoryAggregationResult)
            object.__setattr__(value, "application_scoring_input", source.application_scoring_input)
            object.__setattr__(value, "sector", source.sector)
            object.__setattr__(value, "demand", source.demand)
            object.__setattr__(value, "competition", source.competition)
            object.__setattr__(value, "accessibility", source.accessibility)
            object.__setattr__(value, "economics", source.economics)
            return value

        expect_value_failure(
            lambda: require_canonical_application_category_aggregation_result(
                category_shell(coffee_result)
            )
        )
        expect_value_failure(
            lambda: require_canonical_application_category_aggregation_result(
                category_shell(coffee_result)
            )
        )

        # Redirecting a registered result to another canonical scoring input fails.
        _, other_scoring = build_scoring("gym")
        object.__setattr__(coffee_result, "application_scoring_input", other_scoring)
        expect_value_failure(
            lambda: require_canonical_application_category_aggregation_result(coffee_result)
        )
        object.__setattr__(coffee_result, "application_scoring_input", coffee_scoring)
        assert require_canonical_application_category_aggregation_result(coffee_result) is coffee_result

        # Post-registration category value mutation fails closed.
        object.__setattr__(coffee_result, "demand", 99.0)
        expect_value_failure(
            lambda: require_canonical_application_category_aggregation_result(coffee_result)
        )

        # Nested canonical scoring authority mutation after category aggregation
        # invalidates the category authority as well.
        nested_terminal, nested_scoring = build_scoring("restaurant")
        nested_result = aggregate_application_category_scores(nested_scoring)
        object.__setattr__(nested_terminal, "sector_key", SectorKey("beauty"))
        expect_value_failure(
            lambda: require_canonical_application_category_aggregation_result(nested_result)
        )

        # Missing/forged normalized semantics are not repaired locally. Mutating a
        # previously canonical feature invalidates upstream authority and blocks 4.1.
        missing_terminal, missing_scoring = build_scoring("coffee")
        object.__setattr__(
            missing_terminal.normalized_features.walkable_population_score,
            "value",
            None,
        )
        expect_value_failure(
            lambda: aggregate_application_category_scores(missing_scoring)
        )

        # No detached ready/status/fingerprint/features/weights escape hatch exists.
        parameters = inspect.signature(aggregate_application_category_scores).parameters
        assert tuple(parameters) == ("application_scoring_input",)
        for forbidden in (
            "sector",
            "sector_key",
            "normalized_features",
            "readiness_fingerprint",
            "ready",
            "trusted",
            "force",
            "weights",
            "demand",
            "competition",
            "accessibility",
            "economics",
        ):
            assert forbidden not in parameters

        # Closure-owned registries/resolvers/core weight aliases are not caller-visible
        # module authority surfaces.
        for forbidden in (
            "category_bindings",
            "resolve_category_binding",
            "current_scoring_authority",
            "frozen_demand_weights",
            "frozen_accessibility_weights",
            "DEMAND_SUBFEATURE_WEIGHTS",
            "ACCESSIBILITY_SUBFEATURE_WEIGHTS",
        ):
            assert forbidden not in vars(aggregation)
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_checkpoint_4_1_dependency_and_future_scope_firewall():
    aggregation_source = (
        REPO_ROOT / "sitescore-app" / "src" / "sitescore_app" / "aggregation.py"
    ).read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "sitescore-app" / "pyproject.toml").read_text(
        encoding="utf-8"
    )

    assert '"sitescore-core==0.1.0"' in pyproject
    assert pyproject.count("sitescore-core==0.1.0") == 1

    # Production consumes frozen core subfeature authorities directly and contains
    # no local numeric weight table or later Location Score authority.
    assert "sitescore.config.subfeature_weights" in aggregation_source
    assert "DEMAND_SUBFEATURE_WEIGHTS" in aggregation_source
    assert "ACCESSIBILITY_SUBFEATURE_WEIGHTS" in aggregation_source
    assert "SECTOR_CATEGORY_WEIGHTS" not in aggregation_source
    assert "CategoryScores(" not in aggregation_source
    assert "ReadyCategoryScorePayload(" not in aggregation_source
    assert "AnalysisInput(" not in aggregation_source
    assert "analyze(" not in aggregation_source

    for forbidden in (
        "fastapi",
        "flask",
        "django",
        "starlette",
        "stripe",
        "reportlab",
        "weasyprint",
        "celery",
        "redis",
        "n8n",
    ):
        assert forbidden not in aggregation_source.lower()
        assert forbidden not in pyproject.lower()


def test_comb005_production_truth_remains_unapproved_and_nonnumeric():
    from sitescore_benchmarks.composite import (
        APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1,
        COMB005_V1_POLICY,
        RoadParkingPolicyApprovalState,
        evaluate_road_parking_composite,
    )

    assert COMB005_V1_POLICY.approval_state is RoadParkingPolicyApprovalState.NOT_APPROVED
    assert COMB005_V1_POLICY.weights == ()
    assert COMB005_V1_POLICY.composition_method == "UNRESOLVED"
    assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()
    assert evaluate_road_parking_composite().score is None


def test_no_upstream_frozen_package_imports_sitescore_app_after_4_1():
    for package in (
        "sitescore-core",
        "sitescore-data",
        "sitescore-providers",
        "sitescore-spatial",
        "sitescore-metrics",
        "sitescore-benchmarks",
        "sitescore-pipeline",
    ):
        src_root = REPO_ROOT / package / "src"
        for path in src_root.rglob("*.py"):
            assert "sitescore_app" not in path.read_text(encoding="utf-8")
