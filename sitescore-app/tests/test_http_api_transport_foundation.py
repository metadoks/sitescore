from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_http_api_transport_foundation():
    script = textwrap.dedent(r'''
        import copy
        import inspect
        import json
        import pathlib

        import sitescore_pipeline
        from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
        from sitescore.schemas.revenue_inputs import BeautyRevenueInput, CoffeeRevenueInput, GymRevenueInput, RestaurantRevenueInput
        from sitescore_benchmarks.composite import (
            APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1,
            COMB005_V1_POLICY,
            RoadParkingPolicyApprovalState,
        )
        from sitescore_data.enums import AvailabilityState, CalibrationState, DataQualityState, PipelineStatus, ScoreEligibility
        from sitescore_data.schemas.common import MetricValue
        from sitescore_data.schemas.features import NormalizedLocationFeatures
        from sitescore_data.schemas.pipeline import RealDataPipelineResult
        from sitescore_data.schemas.readiness import ScoringReadinessResult
        from sitescore_data.validation import SectorKey

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
        import sitescore_app.transport as transport_module
        from sitescore_app import (
            ApplicationCoreAnalysisInput,
            ApplicationHttpResponse,
            aggregate_application_category_scores,
            build_application_core_analysis_input,
            build_application_pipeline_result,
            build_application_scoring_input,
            handle_application_analysis_transport,
        )

        assert list(inspect.signature(handle_application_analysis_transport).parameters) == ["application_core_input"]
        assert "ApplicationHttpResponse" in sitescore_app.__all__
        assert "handle_application_analysis_transport" in sitescore_app.__all__

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

        real_application_analyze = transport_module.analyze_application_core_input
        delegate_calls = []

        def counted_application_analyze(value):
            result = real_application_analyze(value)
            delegate_calls.append((value, result))
            return result

        transport_module.analyze_application_core_input = counted_application_analyze

        authority = build_authority("coffee")
        response = handle_application_analysis_transport(authority)
        assert isinstance(response, ApplicationHttpResponse)
        assert response.status_code == 200
        assert len(delegate_calls) == 1
        assert delegate_calls[0][0] is authority

        canonical = delegate_calls[0][1]
        exact_dict = canonical.core_result.to_dict()
        assert response.body == exact_dict
        assert response.body is not exact_dict
        assert response.body["analysis_fingerprint"] == canonical.analysis_fingerprint
        assert json.loads(json.dumps(response.body)) == response.body

        second = handle_application_analysis_transport(build_authority("coffee"))
        assert second.status_code == 200
        assert len(delegate_calls) == 2
        assert second.body == response.body

        original_headline = canonical.core_result.decision.headline
        response.body["decision"]["headline"] = "transport-only mutation"
        assert canonical.core_result.decision.headline == original_headline

        snapshot_response = handle_application_analysis_transport(build_authority("restaurant"))
        snapshot_result = delegate_calls[-1][1]
        snapshot = copy.deepcopy(snapshot_response.body)
        nested_decision = snapshot_result.core_result.decision
        nested_original = nested_decision.headline
        object.__setattr__(nested_decision, "headline", "canonical mutation after response")
        assert snapshot_response.body == snapshot
        object.__setattr__(nested_decision, "headline", nested_original)

        raw_analysis_input = authority.analysis_input
        raw_response = handle_application_analysis_transport(raw_analysis_input)
        assert raw_response.status_code == 400
        assert raw_response.body == {
            "error": {
                "code": "invalid_application_authority",
                "message": "Invalid application analysis authority.",
            }
        }

        raw_core_result = canonical.core_result
        raw_core_response = handle_application_analysis_transport(raw_core_result)
        assert raw_core_response.status_code == 400
        assert raw_core_response.body["error"]["code"] == "invalid_application_authority"

        manual = object.__new__(ApplicationCoreAnalysisInput)
        object.__setattr__(manual, "_category_result", authority.category_result)
        object.__setattr__(manual, "_analysis_input", authority.analysis_input)
        manual_response = handle_application_analysis_transport(manual)
        assert manual_response.status_code == 400
        assert manual_response.body["error"]["code"] == "invalid_application_authority"

        mutated = build_authority("gym")
        object.__setattr__(mutated.analysis_input, "monthly_rent", 9999.0)
        mutated_response = handle_application_analysis_transport(mutated)
        assert mutated_response.status_code == 400
        assert mutated_response.body["error"]["code"] == "invalid_application_authority"

        body_reuse = handle_application_analysis_transport(snapshot_response.body)
        assert body_reuse.status_code == 400
        assert body_reuse.body["error"]["code"] == "invalid_application_authority"

        secret = "SENSITIVE-INTERNAL-/tmp/provider-secret-api-key"
        def invalid_failure(_value):
            raise ValueError(secret)
        transport_module.analyze_application_core_input = invalid_failure
        invalid_error = handle_application_analysis_transport(build_authority("beauty"))
        assert invalid_error.status_code == 400
        assert invalid_error.body["error"]["code"] == "invalid_application_authority"
        assert secret not in json.dumps(invalid_error.body)

        def unexpected_failure(_value):
            raise RuntimeError(secret)
        transport_module.analyze_application_core_input = unexpected_failure
        unexpected = handle_application_analysis_transport(build_authority("beauty"))
        assert unexpected.status_code == 500
        assert unexpected.body == {
            "error": {
                "code": "analysis_execution_failed",
                "message": "Application analysis failed.",
            }
        }
        assert secret not in json.dumps(unexpected.body)

        transport_module.analyze_application_core_input = real_application_analyze

        assert COMB005_V1_POLICY.approval_state is RoadParkingPolicyApprovalState.NOT_APPROVED
        assert COMB005_V1_POLICY.weights == ()
        assert COMB005_V1_POLICY.composition_method == "UNRESOLVED"
        assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()

        source_path = pathlib.Path(sitescore_app.__file__).with_name("transport.py")
        source = source_path.read_text()
        for forbidden in (
            "from sitescore.analyze", "calculate_revenue", "calculate_location_score",
            "calculate_financial_metrics", "calculate_decision", "calculate_confidence",
            "generate_analysis_fingerprint", "current_model_versions", "from_dict",
            "deserialize", "FastAPI", "Starlette", "Flask", "Django", "Pydantic",
            "Uvicorn", "Gunicorn", "OpenAPI", "CORS", "rate_limit", "Stripe", "n8n",
        ):
            assert forbidden not in source
        assert source.count("analyze_application_core_input(application_core_input)") == 1

        pyproject = (pathlib.Path(sitescore_app.__file__).parents[2] / "pyproject.toml").read_text()
        assert 'version = "0.1.0"' in pyproject
        assert '"sitescore-data==0.1.0"' in pyproject
        assert '"sitescore-pipeline==0.1.0"' in pyproject
        assert '"sitescore-core==0.1.0"' in pyproject
        for forbidden_dependency in ("fastapi", "starlette", "flask", "django", "pydantic", "uvicorn", "gunicorn"):
            assert forbidden_dependency not in pyproject.lower()
    ''')
    completed = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
