from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .analysis_adapter import ApplicationCoreAnalysisInput
from .analysis_use_case import (
    analyze_application_core_input,
    require_canonical_application_analysis_result,
)


@dataclass(frozen=True, slots=True)
class ApplicationHttpResponse:
    """Framework-neutral HTTP-style response data.

    This DTO is transport data only. It is never accepted as application
    execution authority and carries no deserialization or trust semantics.
    """

    status_code: int
    body: dict[str, object]


def _error_response(status_code: int, code: str, message: str) -> ApplicationHttpResponse:
    return ApplicationHttpResponse(
        status_code=status_code,
        body={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


def handle_application_analysis_transport(
    application_core_input: ApplicationCoreAnalysisInput,
) -> ApplicationHttpResponse:
    """Execute the locked application analysis use-case and project transport data.

    The input remains an in-process factory-owned ApplicationCoreAnalysisInput.
    No mapping, JSON payload, token, fingerprint, or caller flag can be promoted
    to application authority by this transport boundary.
    """

    try:
        analysis_result = analyze_application_core_input(application_core_input)
    except (TypeError, ValueError):
        return _error_response(
            400,
            "invalid_application_authority",
            "Invalid application analysis authority.",
        )
    except Exception:
        return _error_response(
            500,
            "analysis_execution_failed",
            "Application analysis failed.",
        )

    try:
        canonical_result = require_canonical_application_analysis_result(
            analysis_result
        )
        core_result = canonical_result.core_result
        body = deepcopy(core_result.to_dict())
    except Exception:
        return _error_response(
            500,
            "analysis_execution_failed",
            "Application analysis failed.",
        )

    return ApplicationHttpResponse(status_code=200, body=body)


__all__ = [
    "ApplicationHttpResponse",
    "handle_application_analysis_transport",
]
