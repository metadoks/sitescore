from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_core_analysis_input_authority_and_integrity():
    script = textwrap.dedent(
        r'''
        import inspect
        import sitescore_pipeline
        from sitescore_data.enums import AvailabilityState, CalibrationState, DataQualityState, PipelineStatus, ScoreEligibility
        from sitescore_data.schemas.common import MetricValue
        from sitescore_data.schemas.features import NormalizedLocationFeatures
        from sitescore_data.schemas.pipeline import RealDataPipelineResult
        from sitescore_data.schemas.readiness import ScoringReadinessResult
        from sitescore_data.validation import SectorKey

        def metric(value, ref):
            return MetricValue(
                value=value, unit="score_0_100",
                availability=AvailabilityState.AVAILABLE,
                data_quality=DataQualityState.FULL,
                score_eligibility=ScoreEligibility.ELIGIBLE,
                calibration_state=CalibrationState.CALIBRATED,
                is_estimate=False, is_proxy=False,
                source_refs=(ref,), method_version="test/1", reason_codes=(),
            )

        def features():
            value = object.__new__(NormalizedLocationFeatures)
            for name, number in (
                ("walkable_population_score", 10.0),
                ("target_population_density_score", 20.0),
                ("age_target_concentration_score", 30.0),
                ("competition_opportunity_score", 70.0),
                ("walkable_reach_area_score", 40.0),
                ("transit_access_score", 50.0),
                ("road_parking_access_score", 60.0),
                ("household_income_score", 80.0),
            ):
                object.__setattr__(value, name, metric(number, name))
            return value

        def terminal(sector_name):
            ready = object.__new__(ScoringReadinessResult)
            object.__setattr__(ready, "is_score_ready", True)
            object.__setattr__(ready, "reason_codes", ())
            object.__setattr__(ready, "readiness_fingerprint", f"ready-{sector_name}")
            value = object.__new__(RealDataPipelineResult)
            object.__setattr__(value, "status", PipelineStatus.SCORE_READY)
            object.__setattr__(value, "sector_key", SectorKey(sector_name))
            object.__setattr__(value, "scoring_readiness", ready)
            object.__setattr__(value, "normalized_features", features())
            return value

        queue = []
        def controlled_terminal_factory(**_kwargs):
            return queue.pop(0)
        sitescore_pipeline.build_real_data_pipeline_result = controlled_terminal_factory

        import sitescore_app
        import sitescore_app.analysis_adapter as adapter
        import sitescore_app.aggregation as aggregation
        from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
        from sitescore.config.sectors import Sector
        from sitescore.schemas.analysis import AnalysisInput
        from sitescore.schemas.location import CategoryScores
        from sitescore.schemas.revenue_inputs import BeautyRevenueInput, CoffeeRevenueInput, GymRevenueInput, RestaurantRevenueInput
        from sitescore_app import (
            ApplicationCoreAnalysisInput,
            aggregate_application_category_scores,
            build_application_core_analysis_input,
            build_application_pipeline_result,
            build_application_scoring_input,
            require_canonical_application_core_analysis_input,
        )

        revenue_by_sector = {
            "coffee": CoffeeRevenueInput(1000, .5, .01, .02, .03, 2, 10),
            "restaurant": RestaurantRevenueInput(20, 2, .4, .5, .6, 25, 30),
            "gym": GymRevenueInput(1000, .01, .02, .03, 100, 1, 50),
            "beauty": BeautyRevenueInput(5, 40, 1, .4, .5, .6, 30),
        }
        expected_sector = {
            "coffee": Sector.COFFEE,
            "restaurant": Sector.RESTAURANT,
            "gym": Sector.GYM,
            "beauty": Sector.BEAUTY,
        }
        expected_categories = {
            "coffee": (14.0, 70.0, 47.0, 80.0),
            "restaurant": (17.0, 70.0, 49.0, 80.0),
            "gym": (20.0, 70.0, 56.0, 80.0),
            "beauty": (22.0, 70.0, 56.0, 80.0),
        }

        def category(sector_name):
            raw = terminal(sector_name)
            queue.append(raw)
            app_result = build_application_pipeline_result(
                readiness=None, sector_key=None, resolved_location=None,
                derived_metrics=None, source_metadata=(), generated_at=None,
            )
            scoring = build_application_scoring_input(app_result)
            return raw, aggregate_application_category_scores(scoring)

        def build(sector_name, coverage=None, qualities=None):
            raw, cat = category(sector_name)
            coverage = {"demand": CoverageLevel.FULL} if coverage is None else coverage
            qualities = {"rent": InputQuality.USER} if qualities is None else qualities
            wrapper = build_application_core_analysis_input(
                cat,
                revenue_input=revenue_by_sector[sector_name],
                monthly_rent=1000.0,
                fixed_labor=2000.0,
                fixed_overhead=300.0,
                geographic_level=GeographicLevel.TRACT,
                data_age_years=1,
                data_coverage=coverage,
                input_qualities=qualities,
            )
            return raw, cat, wrapper

        def reject(call):
            try:
                call()
            except (TypeError, ValueError):
                return
            raise AssertionError("forged/mutated authority accepted")

        # Exact adaptation for every frozen sector and actual core DTO types.
        for sector_name in revenue_by_sector:
            _, cat, wrapper = build(sector_name)
            assert require_canonical_application_core_analysis_input(wrapper) is wrapper
            core = wrapper.analysis_input
            assert isinstance(core, AnalysisInput)
            assert core.sector is expected_sector[sector_name]
            assert isinstance(core.category_scores, CategoryScores)
            assert (
                core.category_scores.demand,
                core.category_scores.competition,
                core.category_scores.accessibility,
                core.category_scores.economics,
            ) == expected_categories[sector_name]
            assert core.revenue_input is revenue_by_sector[sector_name]

        # Signature has no detached category values, prebuilt CategoryScores or AnalysisInput.
        params = inspect.signature(build_application_core_analysis_input).parameters
        for forbidden in ("demand", "competition", "accessibility", "economics", "category_scores", "analysis_input", "trusted", "ready", "force"):
            assert forbidden not in params

        # Caller mappings are copied and isolated.
        coverage = {"demand": CoverageLevel.FULL}
        qualities = {"rent": InputQuality.USER}
        _, _, isolated = build("coffee", coverage, qualities)
        coverage["demand"] = CoverageLevel.MISSING
        coverage["competition"] = CoverageLevel.FULL
        qualities["rent"] = InputQuality.MISSING
        qualities["price"] = InputQuality.USER
        assert isolated.analysis_input.data_coverage == {"demand": CoverageLevel.FULL}
        assert isolated.analysis_input.input_qualities == {"rent": InputQuality.USER}

        # Wrong sector revenue input and invalid core business values fail through core.
        _, cat, _ = build("coffee")
        reject(lambda: build_application_core_analysis_input(
            cat, revenue_input=revenue_by_sector["gym"], monthly_rent=1.0,
            fixed_labor=1.0, fixed_overhead=1.0,
            geographic_level=GeographicLevel.TRACT, data_age_years=0,
            data_coverage={}, input_qualities={},
        ))
        reject(lambda: build_application_core_analysis_input(
            cat, revenue_input=revenue_by_sector["coffee"], monthly_rent=-1.0,
            fixed_labor=1.0, fixed_overhead=1.0,
            geographic_level=GeographicLevel.TRACT, data_age_years=0,
            data_coverage={}, input_qualities={},
        ))

        # Raw valid core AnalysisInput is not application authority.
        raw_core = AnalysisInput(
            sector=Sector.COFFEE,
            category_scores=CategoryScores(14,70,47,80),
            revenue_input=revenue_by_sector["coffee"],
            monthly_rent=1, fixed_labor=1, fixed_overhead=1,
            geographic_level=GeographicLevel.TRACT, data_age_years=0,
            data_coverage={}, input_qualities={},
        )
        reject(lambda: require_canonical_application_core_analysis_input(raw_core))
        manual = object.__new__(ApplicationCoreAnalysisInput)
        object.__setattr__(manual, "_category_result", cat)
        object.__setattr__(manual, "_analysis_input", raw_core)
        reject(lambda: require_canonical_application_core_analysis_input(manual))

        # 4.1 category mutation before adapter is rejected and trusted bridge is private.
        _, mutated_cat = category("coffee")
        object.__setattr__(mutated_cat, "demand", 99.0)
        reject(lambda: build_application_core_analysis_input(
            mutated_cat, revenue_input=revenue_by_sector["coffee"], monthly_rent=1,
            fixed_labor=1, fixed_overhead=1, geographic_level=GeographicLevel.TRACT,
            data_age_years=0, data_coverage={}, input_qualities={},
        ))
        assert "_resolve_trusted_application_category_authority" not in sitescore_app.__all__
        assert "_resolve_trusted_application_core_analysis_input" not in sitescore_app.__all__

        # Every authority-bearing post-registration surface fails closed.
        def mutation_case(mutator):
            raw, cat_value, wrapper = build("coffee")
            mutator(raw, cat_value, wrapper, wrapper.analysis_input)
            reject(lambda: require_canonical_application_core_analysis_input(wrapper))
            reject(lambda: getattr(wrapper, "analysis_input"))

        mutation_case(lambda _r, _c, w, _a: object.__setattr__(w, "_analysis_input", raw_core))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "sector", Sector.GYM))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "category_scores", CategoryScores(1,2,3,4)))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a.category_scores, "demand", 99.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a.category_scores, "competition", 99.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a.category_scores, "accessibility", 99.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a.category_scores, "economics", 99.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "revenue_input", revenue_by_sector["gym"]))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a.revenue_input, "average_ticket", 999.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "monthly_rent", 9.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "fixed_labor", 9.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "fixed_overhead", 9.0))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "geographic_level", GeographicLevel.COUNTY))
        mutation_case(lambda _r, _c, _w, a: object.__setattr__(a, "data_age_years", 9))
        mutation_case(lambda _r, _c, _w, a: a.data_coverage.__setitem__("demand", CoverageLevel.MISSING))
        mutation_case(lambda _r, _c, _w, a: a.input_qualities.__setitem__("rent", InputQuality.MISSING))
        mutation_case(lambda r, _c, _w, _a: object.__setattr__(r, "sector_key", SectorKey("gym")))
        mutation_case(lambda _r, c, _w, _a: object.__setattr__(c, "economics", 1.0))

        # 4.3 execution symbols are not imported/executed by the adapter module.
        source = inspect.getsource(adapter)
        for forbidden in (
            "sitescore.analyze", "calculate_revenue", "calculate_location_score",
            "calculate_financial_metrics", "calculate_decision", "calculate_confidence",
            "generate_analysis_fingerprint", "SECTOR_CATEGORY_WEIGHTS",
        ):
            assert forbidden not in source
        ''')
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        check=True,
    )
