from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict
from .version import API_VERSION


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: str = API_VERSION
    request_id: str
    error: ErrorBody


class SiteScoreApiError(RuntimeError):
    status_code = 500
    code = "internal_server_error"
    public_message = "an unexpected internal error occurred"
    headers: dict[str, str] = {}


class AnalysisLifecycleUnavailable(SiteScoreApiError):
    status_code = 503
    code = "analysis_lifecycle_unavailable"
    public_message = "analysis lifecycle is unavailable"


class ReportLifecycleUnavailable(SiteScoreApiError):
    status_code = 503
    code = "report_lifecycle_unavailable"
    public_message = "report lifecycle is unavailable"


class IngressCommandValidationError(ValueError):
    pass


class AuthenticationRequired(SiteScoreApiError):
    status_code = 401
    code = "authentication_required"
    public_message = "bearer authentication is required"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidApiKey(SiteScoreApiError):
    status_code = 401
    code = "invalid_api_key"
    public_message = "invalid API key"
    headers = {"WWW-Authenticate": "Bearer"}


class InsufficientScope(SiteScoreApiError):
    status_code = 403
    code = "insufficient_scope"
    public_message = "API key does not grant the required scope"


class IdempotencyKeyRequired(SiteScoreApiError):
    status_code = 400
    code = "idempotency_key_required"
    public_message = "Idempotency-Key is required"


class InvalidIdempotencyKey(SiteScoreApiError):
    status_code = 400
    code = "invalid_idempotency_key"
    public_message = "Idempotency-Key is invalid"


class IdempotencyConflict(SiteScoreApiError):
    status_code = 409
    code = "idempotency_conflict"
    public_message = "Idempotency-Key was already used with a different payload"


class AnalysisNotFound(SiteScoreApiError):
    status_code = 404
    code = "analysis_not_found"
    public_message = "analysis not found"


class ReportNotFound(SiteScoreApiError):
    status_code = 404
    code = "report_not_found"
    public_message = "report not found"


class ReportNotYetReportable(SiteScoreApiError):
    status_code = 409
    code = "report_not_yet_reportable"
    public_message = "analysis is not yet reportable"


class AnalysisNotReportable(SiteScoreApiError):
    status_code = 409
    code = "analysis_not_reportable"
    public_message = "analysis cannot produce a report artifact"


class ReportContentUnavailable(SiteScoreApiError):
    status_code = 409
    code = "report_content_unavailable"
    public_message = "report content is unavailable"


class ReportArtifactIntegrityError(SiteScoreApiError):
    status_code = 502
    code = "report_artifact_integrity_failed"
    public_message = "report artifact integrity verification failed"


class ReportInvariantViolation(SiteScoreApiError):
    status_code = 500
    code = "report_invariant_violation"
    public_message = "report resource invariant failed"


class ExecutionConfigurationError(RuntimeError):
    pass


class CanonicalExecutionFailed(RuntimeError):
    pass
