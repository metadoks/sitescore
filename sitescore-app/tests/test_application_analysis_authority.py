from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_application_analysis_authority_and_single_core_execution():
    script = textwrap.dedent(
        r'''
        import inspect

        import sitescore_pipeline
        import sitescore.analyze as core_analyze_module
        from sitescore.analyze import analyze as real_core_analyze
        from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
        from sitescore.config.sectors import Sector
        from sitescore.schemas.analysis import AnalysisInput
        from sitescore.schemas.revenue_inputs import (
            BeautyRevenueInput,
            CoffeeRevenueInput,
            GymRevenueInput,
            RestaurantRevenueInput,
        )
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

        call_count = 0
        seen_inputs = []
        mutate_during = False

        def wrapped_core_analyze(data):
            global call_count
            call_count += 1
            seen_inputs.append(data)
            result = real_core_analyze(data)
            if mutate_during:
                object.__setattr__(data, "monthly_rent", data.monthly_rent + 1.0)
            return result

        core_analyze_module.analyze = wrapped_core_analyze

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
            values = {
                "walkable_population_score": 10.0,
                "target_population_density_score": 20.0,
                "age_target_concentration_score": 30.0,
                "competition_opportunity_score": 70.0,
                "walkable_reach_area_score": 40.0,
                "transit_access_score": 50.0,
                "road_parking_access_score": 60.0,
                "household_income_score": 80.0,
            }
            for name, raw in values.items():
                object.__setattr__(value, name, score_metric(raw, f"test.{name}"))
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
            return terminals.pop(0)
        sitescore_pipeline.build_real_data_pipeline_result = controlled_terminal_factory

        import sitescore_app
        from sitescore_app import (
            ApplicationAnalysisResult,
            ApplicationCoreAnalysisInput,
            aggregate_application_category_scores,
            analyze_application_core_input,
            build_application_core_analysis_input,
            build_application_pipeline_result,
            build_application_scoring_input,
            require_canonical_application_analysis_result,
        )

        assert "_resolve_trusted_application_core_analysis_input" not in sitescore_app.__all__
        assert "_resolve_trusted_application_analysis_result" not in sitescore_app.__all__
        signature = inspect.signature(analyze_application_core_input)
        assert list(signature.parameters) == ["application_core_input"]

        revenue_by_sector = {
            "coffee": CoffeeRevenueInput(1000, .5, .01, .02, .03, 2, 8),
            "restaurant": RestaurantRevenueInput(40, 2, .4, .6, .8, 25, 30),
            "gym": GymRevenueInput(10000, .01, .02, .03, 1000, .1, 50),
            "beauty": BeautyRevenueInput(4, 40, 1, .4, .6, .8, 60),
        }

        def build_authority(sector):
            terminal = terminal_shell(sector)
            terminals.append(terminal)
            pipeline = build_application_pipeline_result(
                readiness=None, sector_key=None, resolved_location=None,
                derived_metrics=None, source_metadata=(), generated_at=None,
            )
            scoring = build_application_scoring_input(pipeline)
            category = aggregate_application_category_scores(scoring)
            core_input = build_application_core_analysis_input(
                category,
                revenue_input=revenue_by_sector[sector],
                monthly_rent=1000.0,
                fixed_labor=2000.0,
                fixed_overhead=500.0,
                geographic_level=GeographicLevel.TRACT,
                data_age_years=1,
                data_coverage={
                    "demand": CoverageLevel.FULL,
                    "competition": CoverageLevel.FULL,
                    "accessibility": CoverageLevel.FULL,
                    "economics": CoverageLevel.FULL,
                },
                input_qualities={
                    "rent": InputQuality.USER,
                    "price": InputQuality.USER,
                    "capacity": InputQuality.USER,
                    "schedule": InputQuality.USER,
                },
            )
            return terminal, category, core_input

        results = {}
        for sector in ("coffee", "restaurant", "gym", "beauty"):
            _, _, core_input = build_authority(sector)
            before = call_count
            exact_input = core_input.analysis_input
            app_result = analyze_application_core_input(core_input)
            assert call_count == before + 1
            assert seen_inputs[-1] is exact_input
            assert app_result.application_core_input is core_input
            assert app_result.core_result.analysis_fingerprint == app_result.analysis_fingerprint
            assert require_canonical_application_analysis_result(app_result) is app_result
            results[sector] = (core_input, app_result)

        # Equivalent controlled semantics remain deterministically fingerprint-equal.
        _, _, coffee_again_input = build_authority("coffee")
        coffee_again = analyze_application_core_input(coffee_again_input)
        assert coffee_again.analysis_fingerprint == results["coffee"][1].analysis_fingerprint
        assert coffee_again is not results["coffee"][1]

        def expect_type_failure(fn):
            try:
                fn()
            except TypeError:
                return
            raise AssertionError("expected TypeError")

        def expect_value_failure(fn):
            try:
                fn()
            except ValueError:
                return
            raise AssertionError("expected ValueError")

        # Raw core DTO and manual/copy core authority are not application execution authority.
        raw = results["coffee"][0].analysis_input
        expect_type_failure(lambda: analyze_application_core_input(raw))
        manual_core = object.__new__(ApplicationCoreAnalysisInput)
        object.__setattr__(manual_core, "_category_result", results["coffee"][0].category_result)
        object.__setattr__(manual_core, "_analysis_input", raw)
        before = call_count
        expect_value_failure(lambda: analyze_application_core_input(manual_core))
        assert call_count == before

        # Mutation before execution blocks the core call.
        _, _, pre_mutated = build_authority("gym")
        object.__setattr__(pre_mutated.analysis_input, "monthly_rent", 9999.0)
        before = call_count
        expect_value_failure(lambda: analyze_application_core_input(pre_mutated))
        assert call_count == before

        # Controlled mutation during the one core call prevents downstream authority registration.
        _, _, during = build_authority("beauty")
        mutate_during = True
        before = call_count
        expect_value_failure(lambda: analyze_application_core_input(during))
        assert call_count == before + 1
        mutate_during = False

        # Manual/copy application result shells are rejected.
        core_input, canonical = results["restaurant"]
        manual_result = object.__new__(ApplicationAnalysisResult)
        object.__setattr__(manual_result, "_application_core_input", core_input)
        object.__setattr__(manual_result, "_core_result", canonical.core_result)
        expect_value_failure(lambda: require_canonical_application_analysis_result(manual_result))

        # Wrapper redirections are rejected.
        other_input, other_result = results["gym"]
        object.__setattr__(canonical, "_application_core_input", other_input)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(canonical, "_application_core_input", core_input)
        object.__setattr__(canonical, "_core_result", other_result.core_result)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(canonical, "_core_result", results["restaurant"][1]._core_result)

        # Core result and nested result mutations fail closed.
        core_result = canonical.core_result
        original_fp = core_result.analysis_fingerprint
        object.__setattr__(core_result, "analysis_fingerprint", original_fp + "x")
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result, "analysis_fingerprint", original_fp)

        original_versions = core_result.model_versions
        object.__setattr__(core_result, "model_versions", other_result.core_result.model_versions)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result, "model_versions", original_versions)

        original_location = core_result.location.base_score
        object.__setattr__(core_result.location, "base_score", original_location + 1.0)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result.location, "base_score", original_location)

        original_profit = core_result.financial.operating_profit_base
        object.__setattr__(core_result.financial, "operating_profit_base", original_profit + 1.0)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result.financial, "operating_profit_base", original_profit)

        original_revenue = core_result.financial.revenue.base
        object.__setattr__(core_result.financial.revenue, "base", original_revenue + 1.0)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result.financial.revenue, "base", original_revenue)

        original_headline = core_result.decision.headline
        object.__setattr__(core_result.decision, "headline", original_headline + "x")
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result.decision, "headline", original_headline)

        original_conf = core_result.confidence.overall_score
        object.__setattr__(core_result.confidence, "overall_score", original_conf + 1.0)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result.confidence, "overall_score", original_conf)

        # Nested canonical 4.2 mutation after registration invalidates 4.3 authority.
        object.__setattr__(core_input.analysis_input, "fixed_overhead", 777.0)
        expect_value_failure(lambda: require_canonical_application_analysis_result(canonical))

        # Source-level firewall: app orchestrator invokes only core analyze, not individual engines/fingerprint helpers.
        import pathlib
        source = pathlib.Path(sitescore_app.__file__).with_name("analysis_use_case.py").read_text()
        for forbidden in (
            "calculate_revenue", "calculate_location_score", "calculate_financial_metrics",
            "calculate_decision", "calculate_confidence", "generate_analysis_fingerprint",
            "current_model_versions", "SECTOR_CATEGORY_WEIGHTS",
        ):
            assert forbidden not in source
        for transport in ("FastAPI", "Flask", "Django", "Starlette", "Stripe", "n8n"):
            assert transport not in source
        assert source.count("frozen_core_analyze(analysis_input)") == 1
        '''
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
