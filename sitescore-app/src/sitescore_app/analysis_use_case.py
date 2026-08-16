from __future__ import annotations

from dataclasses import dataclass
from weakref import ref

from sitescore.schemas.analysis import AnalysisInput
from sitescore.schemas.canonical import CanonicalAnalysisResult

from .analysis_adapter import (
    ApplicationCoreAnalysisInput,
    _resolve_trusted_application_core_analysis_input,
    _semantic_record,
)


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ApplicationAnalysisResult:
    """Factory-owned application authority over one exact core analysis execution."""

    _application_core_input: ApplicationCoreAnalysisInput
    _core_result: CanonicalAnalysisResult

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApplicationAnalysisResult is factory-owned; use "
            "analyze_application_core_input"
        )

    @property
    def application_core_input(self) -> ApplicationCoreAnalysisInput:
        binding = _resolve_trusted_application_analysis_result(self)
        return binding[1]

    @property
    def core_result(self) -> CanonicalAnalysisResult:
        binding = _resolve_trusted_application_analysis_result(self)
        return binding[4]

    @property
    def analysis_fingerprint(self) -> str:
        binding = _resolve_trusted_application_analysis_result(self)
        return binding[5]


def _install_application_analysis_factories():
    # Capture the exact frozen core orchestration authority at module construction.
    # Production does not import or invoke individual engines, model-version helpers,
    # or fingerprint helpers.
    from sitescore.analyze import analyze as frozen_core_analyze

    bindings: dict[int, tuple[object, ...]] = {}

    def trusted_core_input(
        value: ApplicationCoreAnalysisInput,
    ) -> tuple[AnalysisInput, object]:
        binding = _resolve_trusted_application_core_analysis_input(value)
        analysis_input = binding[14]
        analysis_record = binding[20]
        if not isinstance(analysis_input, AnalysisInput):
            raise RuntimeError("trusted application core input is not AnalysisInput")
        if _semantic_record(analysis_input) != analysis_record:
            raise ValueError("trusted application core input semantic integrity violation")
        return analysis_input, analysis_record

    def register(
        wrapper: ApplicationAnalysisResult,
        application_core_input: ApplicationCoreAnalysisInput,
        analysis_input: AnalysisInput,
        analysis_input_record: object,
        core_result: CanonicalAnalysisResult,
        result_record: object,
    ) -> None:
        object_id = id(wrapper)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            bindings.pop(object_id, None)

        bindings[object_id] = (
            ref(wrapper, cleanup),
            application_core_input,
            analysis_input,
            analysis_input_record,
            core_result,
            core_result.analysis_fingerprint,
            core_result.model_versions,
            _semantic_record(core_result.model_versions),
            core_result.location,
            _semantic_record(core_result.location),
            core_result.financial,
            _semantic_record(core_result.financial),
            core_result.decision,
            _semantic_record(core_result.decision),
            core_result.confidence,
            _semantic_record(core_result.confidence),
            result_record,
        )

    def resolve(value: ApplicationAnalysisResult) -> tuple[object, ...]:
        if not isinstance(value, ApplicationAnalysisResult):
            raise TypeError("value must be an ApplicationAnalysisResult")
        binding = bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("application analysis result is not canonical/factory-owned")

        application_core_input = binding[1]
        analysis_input = binding[2]
        analysis_input_record = binding[3]
        core_result = binding[4]
        fingerprint = binding[5]
        model_versions = binding[6]
        model_versions_record = binding[7]
        location = binding[8]
        location_record = binding[9]
        financial = binding[10]
        financial_record = binding[11]
        decision = binding[12]
        decision_record = binding[13]
        confidence = binding[14]
        confidence_record = binding[15]
        result_record = binding[16]

        if value._application_core_input is not application_core_input:
            raise ValueError("application analysis input binding integrity violation")
        if value._core_result is not core_result:
            raise ValueError("application analysis result redirect/integrity violation")

        current_analysis_input, current_input_record = trusted_core_input(
            application_core_input
        )
        if current_analysis_input is not analysis_input:
            raise ValueError("nested application core input identity integrity violation")
        if current_input_record != analysis_input_record:
            raise ValueError("nested application core input authority changed")

        if core_result.analysis_fingerprint != fingerprint:
            raise ValueError("analysis_fingerprint integrity violation")
        if core_result.model_versions is not model_versions:
            raise ValueError("model_versions identity integrity violation")
        if core_result.location is not location:
            raise ValueError("location result identity integrity violation")
        if core_result.financial is not financial:
            raise ValueError("financial result identity integrity violation")
        if core_result.decision is not decision:
            raise ValueError("decision result identity integrity violation")
        if core_result.confidence is not confidence:
            raise ValueError("confidence result identity integrity violation")

        if _semantic_record(model_versions) != model_versions_record:
            raise ValueError("model_versions semantic integrity violation")
        if _semantic_record(location) != location_record:
            raise ValueError("location result semantic integrity violation")
        if _semantic_record(financial) != financial_record:
            raise ValueError("financial result semantic integrity violation")
        if _semantic_record(decision) != decision_record:
            raise ValueError("decision result semantic integrity violation")
        if _semantic_record(confidence) != confidence_record:
            raise ValueError("confidence result semantic integrity violation")
        if _semantic_record(core_result) != result_record:
            raise ValueError("core CanonicalAnalysisResult semantic integrity violation")
        return binding

    def analyze_application(
        application_core_input: ApplicationCoreAnalysisInput,
    ) -> ApplicationAnalysisResult:
        analysis_input, analysis_input_record = trusted_core_input(
            application_core_input
        )

        # This is the sole production execution call in the app layer.
        core_result = frozen_core_analyze(analysis_input)
        if not isinstance(core_result, CanonicalAnalysisResult):
            raise TypeError("frozen core analyze must return CanonicalAnalysisResult")

        # TOCTOU guard: no downstream authority is granted unless the exact 4.2
        # authority still resolves to the same construction-time input after core
        # execution returns.
        current_analysis_input, current_input_record = trusted_core_input(
            application_core_input
        )
        if current_analysis_input is not analysis_input:
            raise ValueError("application core input redirected during core execution")
        if current_input_record != analysis_input_record:
            raise ValueError("application core input changed during core execution")

        result_record = _semantic_record(core_result)
        wrapper = object.__new__(ApplicationAnalysisResult)
        object.__setattr__(wrapper, "_application_core_input", application_core_input)
        object.__setattr__(wrapper, "_core_result", core_result)
        register(
            wrapper,
            application_core_input,
            analysis_input,
            analysis_input_record,
            core_result,
            result_record,
        )
        return wrapper

    def require(value: ApplicationAnalysisResult) -> ApplicationAnalysisResult:
        resolve(value)
        return value

    return analyze_application, require, resolve


(
    analyze_application_core_input,
    require_canonical_application_analysis_result,
    _resolve_trusted_application_analysis_result,
) = _install_application_analysis_factories()
del _install_application_analysis_factories


__all__ = [
    "ApplicationAnalysisResult",
    "analyze_application_core_input",
    "require_canonical_application_analysis_result",
]
