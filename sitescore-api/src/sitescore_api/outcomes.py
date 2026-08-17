from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from weakref import ref

from sitescore_app import (
    ApplicationAnalysisResult,
    ApplicationPipelineResult,
    ApplicationScoringGateState,
    evaluate_application_scoring_gate,
    require_canonical_application_analysis_result,
    require_canonical_application_pipeline_result,
)


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class CanonicalNotScoreReadyOutcome:
    application_pipeline_result: ApplicationPipelineResult
    readiness_projection: dict[str, object]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("CanonicalNotScoreReadyOutcome is server-factory owned")


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class CanonicalCompletedOutcome:
    application_analysis_result: ApplicationAnalysisResult
    result_body: dict[str, object]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("CanonicalCompletedOutcome is server-factory owned")


def _install_factories():
    not_ready_registry: dict[int, tuple[object, ...]] = {}
    completed_registry: dict[int, tuple[object, ...]] = {}

    def build_not_ready(value: ApplicationPipelineResult) -> CanonicalNotScoreReadyOutcome:
        canonical = require_canonical_application_pipeline_result(value)
        eligibility = evaluate_application_scoring_gate(canonical.pipeline_result)
        if eligibility.state is not ApplicationScoringGateState.NOT_SCORE_READY:
            raise ValueError("canonical pipeline authority is not NOT_SCORE_READY")
        readiness = canonical.pipeline_result.scoring_readiness
        projection: dict[str, object] = {
            "gate_state": eligibility.state.value,
            "gate_reason_codes": [item.value for item in eligibility.reason_codes],
            "upstream_readiness_reasons": [item.value for item in eligibility.upstream_readiness_reasons],
        }
        if readiness is not None:
            projection.update(
                {
                    "is_score_ready": readiness.is_score_ready,
                    "readiness_reason_codes": [item.value for item in readiness.reason_codes],
                    "readiness_fingerprint": readiness.readiness_fingerprint,
                }
            )
        outcome = object.__new__(CanonicalNotScoreReadyOutcome)
        object.__setattr__(outcome, "application_pipeline_result", canonical)
        object.__setattr__(outcome, "readiness_projection", deepcopy(projection))
        object_id = id(outcome)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            not_ready_registry.pop(object_id, None)

        not_ready_registry[object_id] = (ref(outcome, cleanup), canonical, deepcopy(projection))
        return outcome

    def require_not_ready(value: CanonicalNotScoreReadyOutcome) -> CanonicalNotScoreReadyOutcome:
        if not isinstance(value, CanonicalNotScoreReadyOutcome):
            raise TypeError("canonical not-score-ready outcome required")
        binding = not_ready_registry.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("not-score-ready outcome is not canonical/server-owned")
        canonical = require_canonical_application_pipeline_result(binding[1])
        eligibility = evaluate_application_scoring_gate(canonical.pipeline_result)
        if eligibility.state is not ApplicationScoringGateState.NOT_SCORE_READY:
            raise ValueError("not-score-ready authority changed")
        if value.application_pipeline_result is not canonical:
            raise ValueError("not-score-ready outcome binding integrity violation")
        if value.readiness_projection != binding[2]:
            raise ValueError("not-score-ready projection integrity violation")
        return value

    def build_completed(value: ApplicationAnalysisResult) -> CanonicalCompletedOutcome:
        canonical = require_canonical_application_analysis_result(value)
        body = deepcopy(canonical.core_result.to_dict())
        outcome = object.__new__(CanonicalCompletedOutcome)
        object.__setattr__(outcome, "application_analysis_result", canonical)
        object.__setattr__(outcome, "result_body", body)
        object_id = id(outcome)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            completed_registry.pop(object_id, None)

        completed_registry[object_id] = (ref(outcome, cleanup), canonical, deepcopy(body))
        return outcome

    def require_completed(value: CanonicalCompletedOutcome) -> CanonicalCompletedOutcome:
        if not isinstance(value, CanonicalCompletedOutcome):
            raise TypeError("canonical completed outcome required")
        binding = completed_registry.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("completed outcome is not canonical/server-owned")
        canonical = require_canonical_application_analysis_result(binding[1])
        if value.application_analysis_result is not canonical:
            raise ValueError("completed outcome binding integrity violation")
        current = canonical.core_result.to_dict()
        if current != binding[2] or value.result_body != binding[2]:
            raise ValueError("completed canonical result integrity violation")
        return value

    return build_not_ready, require_not_ready, build_completed, require_completed


(
    build_canonical_not_score_ready_outcome,
    require_canonical_not_score_ready_outcome,
    build_canonical_completed_outcome,
    require_canonical_completed_outcome,
) = _install_factories()
del _install_factories
