from __future__ import annotations

import subprocess
import sys
import textwrap


def test_app_h002_construction_time_bindings_reject_post_registration_redirects():
    script = textwrap.dedent(
        r"""
        import inspect

        import sitescore_pipeline
        from sitescore_data.enums import PipelineStatus
        from sitescore_data.schemas.features import NormalizedLocationFeatures
        from sitescore_data.schemas.pipeline import RealDataPipelineResult
        from sitescore_data.schemas.readiness import ScoringReadinessResult

        def terminal_shell():
            terminal = object.__new__(RealDataPipelineResult)
            object.__setattr__(terminal, "status", PipelineStatus.SCORE_READY)
            readiness = object.__new__(ScoringReadinessResult)
            object.__setattr__(readiness, "is_score_ready", True)
            object.__setattr__(readiness, "reason_codes", ())
            object.__setattr__(
                readiness,
                "readiness_fingerprint",
                "controlled-test-ready",
            )
            object.__setattr__(terminal, "scoring_readiness", readiness)
            object.__setattr__(
                terminal,
                "normalized_features",
                object.__new__(NormalizedLocationFeatures),
            )
            return terminal

        def controlled_terminal_factory(**_kwargs):
            return terminal_shell()

        # Test-only fixture: replace the exported pipeline terminal factory before
        # importing the app module. The app installer captures this exact callable
        # in closure state, allowing us to exercise wrapper authority without
        # approving COMB-005 or modifying production readiness semantics.
        sitescore_pipeline.build_real_data_pipeline_result = controlled_terminal_factory
        import sitescore_app.gating as gating

        app_result = gating.build_application_pipeline_result(
            readiness=None,
            sector_key=None,
            resolved_location=None,
            derived_metrics=None,
            source_metadata=(),
            generated_at=None,
        )
        original_terminal = app_result.pipeline_result
        assert (
            gating.require_canonical_application_pipeline_result(app_result)
            is app_result
        )

        scoring_input = gating.build_application_scoring_input(app_result)
        assert (
            gating.require_canonical_application_scoring_input(scoring_input)
            is scoring_input
        )

        forged_terminal = terminal_shell()
        object.__setattr__(app_result, "pipeline_result", forged_terminal)
        try:
            gating.require_canonical_application_pipeline_result(app_result)
        except ValueError as exc:
            assert "integrity violation" in str(exc)
        else:
            raise AssertionError(
                "redirected ApplicationPipelineResult was accepted"
            )

        object.__setattr__(app_result, "pipeline_result", original_terminal)
        assert (
            gating.require_canonical_application_pipeline_result(app_result)
            is app_result
        )

        another_app_result = gating.build_application_pipeline_result(
            readiness=None,
            sector_key=None,
            resolved_location=None,
            derived_metrics=None,
            source_metadata=(),
            generated_at=None,
        )
        object.__setattr__(
            scoring_input,
            "application_pipeline_result",
            another_app_result,
        )
        try:
            gating.require_canonical_application_scoring_input(scoring_input)
        except ValueError as exc:
            assert "integrity violation" in str(exc)
        else:
            raise AssertionError(
                "redirected ApplicationScoringInput was accepted"
            )

        manual = object.__new__(gating.ApplicationPipelineResult)
        object.__setattr__(manual, "pipeline_result", original_terminal)
        try:
            gating.require_canonical_application_pipeline_result(manual)
        except ValueError as exc:
            assert "not canonical" in str(exc)
        else:
            raise AssertionError("manual wrapper was accepted")

        raw_forged = terminal_shell()
        try:
            gating.build_application_scoring_input(raw_forged)
        except TypeError:
            pass
        else:
            raise AssertionError("raw forged terminal was accepted")

        parameters = inspect.signature(
            gating.build_application_scoring_input
        ).parameters
        assert tuple(parameters) == ("application_pipeline_result",)
        for forbidden in (
            "ready",
            "trusted",
            "force",
            "status",
            "readiness_fingerprint",
            "normalized_features",
        ):
            assert forbidden not in parameters
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
