from __future__ import annotations

import subprocess
import sys
import textwrap


def test_app_h002_construction_time_bindings_reject_post_registration_redirects_and_semantic_mutation():
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

        def unavailable_road_metric():
            return MetricValue(
                value=None,
                unit="score_0_100",
                availability=AvailabilityState.UNKNOWN,
                data_quality=DataQualityState.DEGRADED,
                score_eligibility=ScoreEligibility.INELIGIBLE,
                calibration_state=CalibrationState.UNCALIBRATED,
                is_estimate=False,
                is_proxy=False,
                source_refs=(),
                method_version=None,
                reason_codes=("comb005.not_approved",),
            )

        def forged_road_metric():
            return MetricValue(
                value=77.0,
                unit="score_0_100",
                availability=AvailabilityState.AVAILABLE,
                data_quality=DataQualityState.FULL,
                score_eligibility=ScoreEligibility.ELIGIBLE,
                calibration_state=CalibrationState.CALIBRATED,
                is_estimate=False,
                is_proxy=False,
                source_refs=("forged.road",),
                method_version="forged/1",
                reason_codes=(),
            )

        def normalized_shell():
            value = object.__new__(NormalizedLocationFeatures)
            object.__setattr__(
                value,
                "road_parking_access_score",
                unavailable_road_metric(),
            )
            return value

        def readiness_shell(ready, fingerprint):
            value = object.__new__(ScoringReadinessResult)
            object.__setattr__(value, "is_score_ready", ready)
            object.__setattr__(value, "reason_codes", ())
            object.__setattr__(value, "readiness_fingerprint", fingerprint)
            return value

        def terminal_shell(
            *,
            status=PipelineStatus.SCORE_READY,
            ready=True,
            sector="coffee",
            fingerprint="controlled-test-ready",
        ):
            terminal = object.__new__(RealDataPipelineResult)
            object.__setattr__(terminal, "status", status)
            object.__setattr__(terminal, "sector_key", SectorKey(sector))
            object.__setattr__(
                terminal,
                "scoring_readiness",
                readiness_shell(ready, fingerprint),
            )
            object.__setattr__(
                terminal,
                "normalized_features",
                normalized_shell(),
            )
            return terminal

        terminals = []

        def controlled_terminal_factory(**_kwargs):
            if not terminals:
                raise AssertionError("controlled terminal queue is empty")
            return terminals.pop(0)

        # Test-only fixture: replace the exported pipeline terminal factory before
        # importing the app module. The app installer captures this exact callable
        # in closure state, allowing controlled SCORE_READY capability tests without
        # approving COMB-005 or changing frozen pipeline semantics.
        sitescore_pipeline.build_real_data_pipeline_result = controlled_terminal_factory
        import sitescore_app.gating as gating

        def build_app_result(terminal):
            terminals.append(terminal)
            return gating.build_application_pipeline_result(
                readiness=None,
                sector_key=None,
                resolved_location=None,
                derived_metrics=None,
                source_metadata=(),
                generated_at=None,
            )

        def expect_integrity_failure(callable_):
            try:
                callable_()
            except ValueError as exc:
                assert "integrity violation" in str(exc)
            else:
                raise AssertionError("mutated canonical authority was accepted")

        # Existing APP-H002 redirect protection remains effective.
        original_terminal = terminal_shell()
        app_result = build_app_result(original_terminal)
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
        expect_integrity_failure(
            lambda: gating.require_canonical_application_pipeline_result(app_result)
        )

        object.__setattr__(app_result, "pipeline_result", original_terminal)
        assert (
            gating.require_canonical_application_pipeline_result(app_result)
            is app_result
        )

        another_app_result = build_app_result(terminal_shell())
        object.__setattr__(
            scoring_input,
            "application_pipeline_result",
            another_app_result,
        )
        expect_integrity_failure(
            lambda: gating.require_canonical_application_scoring_input(scoring_input)
        )

        # A. SAME exact NOT_SCORE_READY terminal cannot be upgraded by status mutation.
        terminal_a = terminal_shell(
            status=PipelineStatus.NOT_SCORE_READY,
            ready=False,
            fingerprint="real-not-ready-a",
        )
        app_a = build_app_result(terminal_a)
        object.__setattr__(terminal_a, "status", PipelineStatus.SCORE_READY)
        expect_integrity_failure(lambda: gating.build_application_scoring_input(app_a))

        # B. SAME exact readiness object cannot be changed False -> True.
        terminal_b = terminal_shell(
            status=PipelineStatus.NOT_SCORE_READY,
            ready=False,
            fingerprint="real-not-ready-b",
        )
        app_b = build_app_result(terminal_b)
        object.__setattr__(terminal_b.scoring_readiness, "is_score_ready", True)
        expect_integrity_failure(lambda: gating.build_application_scoring_input(app_b))

        # C. SAME normalized feature object cannot receive forged numeric/calibrated
        # road/parking authority.
        terminal_c = terminal_shell(
            status=PipelineStatus.NOT_SCORE_READY,
            ready=False,
            fingerprint="real-not-ready-c",
        )
        app_c = build_app_result(terminal_c)
        object.__setattr__(
            terminal_c.normalized_features,
            "road_parking_access_score",
            forged_road_metric(),
        )
        expect_integrity_failure(lambda: gating.build_application_scoring_input(app_c))

        # D. SAME terminal cannot redirect the authority sector.
        terminal_d = terminal_shell(
            status=PipelineStatus.NOT_SCORE_READY,
            ready=False,
            fingerprint="real-not-ready-d",
        )
        app_d = build_app_result(terminal_d)
        object.__setattr__(terminal_d, "sector_key", SectorKey("gym"))
        expect_integrity_failure(lambda: gating.build_application_scoring_input(app_d))

        # E. SAME readiness object cannot alter readiness-fingerprint semantics.
        terminal_e = terminal_shell(
            status=PipelineStatus.NOT_SCORE_READY,
            ready=False,
            fingerprint="real-not-ready-e",
        )
        app_e = build_app_result(terminal_e)
        object.__setattr__(
            terminal_e.scoring_readiness,
            "readiness_fingerprint",
            "forged-ready-fingerprint",
        )
        expect_integrity_failure(lambda: gating.build_application_scoring_input(app_e))

        # F/G. A legitimate controlled scoring capability is closure-bound to the
        # exact construction-time terminal semantics. Post-grant mutation invalidates
        # canonicality and its public properties fail closed instead of following the
        # mutated terminal.
        terminal_fg = terminal_shell(
            status=PipelineStatus.SCORE_READY,
            ready=True,
            sector="coffee",
            fingerprint="legitimate-controlled-ready",
        )
        app_fg = build_app_result(terminal_fg)
        scoring_fg = gating.build_application_scoring_input(app_fg)

        assert scoring_fg.pipeline_result is terminal_fg
        assert scoring_fg.sector_key == SectorKey("coffee")
        assert scoring_fg.normalized_features is terminal_fg.normalized_features
        assert (
            scoring_fg.readiness_fingerprint
            == "legitimate-controlled-ready"
        )

        object.__setattr__(terminal_fg, "sector_key", SectorKey("beauty"))
        expect_integrity_failure(
            lambda: gating.require_canonical_application_scoring_input(scoring_fg)
        )
        for accessor in (
            lambda: scoring_fg.pipeline_result,
            lambda: scoring_fg.sector_key,
            lambda: scoring_fg.normalized_features,
            lambda: scoring_fg.readiness_fingerprint,
        ):
            expect_integrity_failure(accessor)

        # Manual / copied authority remains rejected.
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

        # No caller-visible authority registry / resolver is exported.
        for forbidden in (
            "pipeline_bindings",
            "scoring_bindings",
            "terminal_authority_record",
            "semantic_record",
            "resolve_scoring_authority",
        ):
            assert forbidden not in vars(gating)
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
