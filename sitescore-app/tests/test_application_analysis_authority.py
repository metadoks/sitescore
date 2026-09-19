from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_application_analysis_authority_and_single_core_execution():
    script = textwrap.dedent(r'''
        import inspect
        import pathlib
        import sitescore_pipeline
        import sitescore.analyze as core_analyze_module
        from sitescore.analyze import analyze as real_core_analyze
        from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
        from sitescore.schemas.revenue_inputs import BeautyRevenueInput, CoffeeRevenueInput, GymRevenueInput, RestaurantRevenueInput
        from sitescore_data.enums import AvailabilityState, CalibrationState, DataQualityState, PipelineStatus, ScoreEligibility
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

        def metric(value, name):
            return MetricValue(
                value=value, unit="score_0_100",
                availability=AvailabilityState.AVAILABLE,
                data_quality=DataQualityState.FULL,
                score_eligibility=ScoreEligibility.ELIGIBLE,
                calibration_state=CalibrationState.CALIBRATED,
                is_estimate=False, is_proxy=False,
                source_refs=(f"test.{name}",), method_version="test/1", reason_codes=(),
            )

        def normalized_shell():
            value = object.__new__(NormalizedLocationFeatures)
            for name, raw in {
                "walkable_population_score": 10.0,
                "target_population_density_score": 20.0,
                "age_target_concentration_score": 30.0,
                "competition_opportunity_score": 70.0,
                "walkable_reach_area_score": 40.0,
                "transit_access_score": 50.0,
                "road_parking_access_score": 60.0,
                "household_income_score": 80.0,
            }.items():
                object.__setattr__(value, name, metric(raw, name))
            return value

        def terminal_shell(sector):
            readiness = object.__new__(ScoringReadinessResult)
            object.__setattr__(readiness, "is_score_ready", True)
            object.__setattr__(readiness, "reason_codes", ())
            object.__setattr__(readiness, "readiness_fingerprint", f"ready-{sector}")
            terminal = object.__new__(RealDataPipelineResult)
            object.__setattr__(terminal, "status", PipelineStatus.SCORE_READY)
            object.__setattr__(terminal, "sector_key", SectorKey(sector))
            object.__setattr__(terminal, "scoring_readiness", readiness)
            object.__setattr__(terminal, "normalized_features", normalized_shell())
            return terminal

        terminals = []
        sitescore_pipeline.build_real_data_pipeline_result = lambda **_kwargs: terminals.pop(0)

        import sitescore_app
        from sitescore_app import (
            ApplicationAnalysisResult, ApplicationCoreAnalysisInput,
            aggregate_application_category_scores, analyze_application_core_input,
            build_application_core_analysis_input, build_application_pipeline_result,
            build_application_scoring_input, require_canonical_application_analysis_result,
        )

        assert list(inspect.signature(analyze_application_core_input).parameters) == ["application_core_input"]
        assert "_resolve_trusted_application_core_analysis_input" not in sitescore_app.__all__
        assert "_resolve_trusted_application_analysis_result" not in sitescore_app.__all__

        revenue = {
            "coffee": CoffeeRevenueInput(1000, .5, .01, .02, .03, 2, 8),
            "restaurant": RestaurantRevenueInput(40, 2, .4, .6, .8, 25, 30),
            "gym": GymRevenueInput(10000, .01, .02, .03, 1000, .1, 50),
            "beauty": BeautyRevenueInput(4, 40, 1, .4, .6, .8, 60),
        }

        def build_authority(sector):
            terminals.append(terminal_shell(sector))
            pipeline = build_application_pipeline_result(
                readiness=None, sector_key=None, resolved_location=None,
                derived_metrics=None, source_metadata=(), generated_at=None,
            )
            scoring = build_application_scoring_input(pipeline)
            category = aggregate_application_category_scores(scoring)
            return build_application_core_analysis_input(
                category, revenue_input=revenue[sector], monthly_rent=1000.0,
                fixed_labor=2000.0, fixed_overhead=500.0,
                geographic_level=GeographicLevel.TRACT, data_age_years=1,
                data_coverage={k: CoverageLevel.FULL for k in ("demand", "competition", "accessibility", "economics")},
                input_qualities={k: InputQuality.USER for k in ("rent", "price", "capacity", "schedule")},
            )

        results = {}
        for sector in ("coffee", "restaurant", "gym", "beauty"):
            core_input = build_authority(sector)
            exact_input = core_input.analysis_input
            before = call_count
            result = analyze_application_core_input(core_input)
            assert call_count == before + 1
            assert seen_inputs[-1] is exact_input
            assert result.application_core_input is core_input
            assert result.core_result.analysis_fingerprint == result.analysis_fingerprint
            assert require_canonical_application_analysis_result(result) is result
            results[sector] = (core_input, result)

        again = analyze_application_core_input(build_authority("coffee"))
        assert again.analysis_fingerprint == results["coffee"][1].analysis_fingerprint
        assert again is not results["coffee"][1]

        def fails(exc, fn):
            try:
                fn()
            except exc:
                return
            raise AssertionError(f"expected {exc.__name__}")

        raw = results["coffee"][0].analysis_input
        fails(TypeError, lambda: analyze_application_core_input(raw))
        manual_core = object.__new__(ApplicationCoreAnalysisInput)
        object.__setattr__(manual_core, "_category_result", results["coffee"][0].category_result)
        object.__setattr__(manual_core, "_analysis_input", raw)
        before = call_count
        fails(ValueError, lambda: analyze_application_core_input(manual_core))
        assert call_count == before

        pre = build_authority("gym")
        object.__setattr__(pre.analysis_input, "monthly_rent", 9999.0)
        before = call_count
        fails(ValueError, lambda: analyze_application_core_input(pre))
        assert call_count == before

        during = build_authority("beauty")
        mutate_during = True
        before = call_count
        fails(ValueError, lambda: analyze_application_core_input(during))
        assert call_count == before + 1
        mutate_during = False

        core_input, canonical = results["restaurant"]
        original_core_result = canonical.core_result
        manual_result = object.__new__(ApplicationAnalysisResult)
        object.__setattr__(manual_result, "_application_core_input", core_input)
        object.__setattr__(manual_result, "_core_result", original_core_result)
        fails(ValueError, lambda: require_canonical_application_analysis_result(manual_result))

        other_input, other_result = results["gym"]
        object.__setattr__(canonical, "_application_core_input", other_input)
        fails(ValueError, lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(canonical, "_application_core_input", core_input)
        object.__setattr__(canonical, "_core_result", other_result.core_result)
        fails(ValueError, lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(canonical, "_core_result", original_core_result)
        assert canonical.core_result is original_core_result

        core_result = canonical.core_result
        fp = core_result.analysis_fingerprint
        object.__setattr__(core_result, "analysis_fingerprint", fp + "x")
        fails(ValueError, lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result, "analysis_fingerprint", fp)

        versions = core_result.model_versions
        object.__setattr__(core_result, "model_versions", other_result.core_result.model_versions)
        fails(ValueError, lambda: require_canonical_application_analysis_result(canonical))
        object.__setattr__(core_result, "model_versions", versions)

        for obj, field in (
            (core_result.location, "base_score"),
            (core_result.financial, "operating_profit_base"),
            (core_result.financial.revenue, "base"),
            (core_result.decision, "headline"),
            (core_result.confidence, "overall_score"),
        ):
            original = getattr(obj, field)
            replacement = original + "x" if isinstance(original, str) else original + 1.0
            object.__setattr__(obj, field, replacement)
            fails(ValueError, lambda: require_canonical_application_analysis_result(canonical))
            object.__setattr__(obj, field, original)

        object.__setattr__(core_input.analysis_input, "fixed_overhead", 777.0)
        fails(ValueError, lambda: require_canonical_application_analysis_result(canonical))

        source = pathlib.Path(sitescore_app.__file__).with_name("analysis_use_case.py").read_text()
        for forbidden in (
            "calculate_revenue", "calculate_location_score", "calculate_financial_metrics",
            "calculate_decision", "calculate_confidence", "generate_analysis_fingerprint",
            "current_model_versions", "SECTOR_CATEGORY_WEIGHTS", "FastAPI", "Flask",
            "Django", "Starlette", "Stripe", "n8n",
        ):
            assert forbidden not in source
        assert source.count("frozen_core_analyze(analysis_input)") == 1
    ''')
    completed = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
