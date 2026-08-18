from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from .auth import AuthenticatedConsumer, authenticate_bearer
from .db import Database
from .errors import AnalysisLifecycleUnavailable, ErrorResponse, ReportLifecycleUnavailable
from .idempotency import validate_idempotency_key
from .ingress import build_analysis_ingress_command
from .lifecycle import AnalysisLifecycleBackend
from .models import AnalysisRequest
from .report_artifacts import PostgresReportArtifactBackend, RetrievedReportResource
from .settings import Settings
from .version import API_VERSION

PublicAnalysisState = Literal[
    "queued",
    "running",
    "completed",
    "not_score_ready",
    "failed",
    "timed_out",
]
PublicReportState = Literal["ready", "failed"]

_bearer = HTTPBearer(auto_error=False, scheme_name="ServiceApiKey")


class AcceptedAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: str = API_VERSION
    request_id: str
    analysis_id: str
    state: PublicAnalysisState


class AnalysisResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: str = API_VERSION
    request_id: str
    analysis_id: str
    state: PublicAnalysisState
    created_at: datetime
    updated_at: datetime
    result: dict[str, object] | None = None
    readiness: dict[str, object] | None = None
    error: dict[str, str] | None = None


class ReportResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_id: UUID


class ReportResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: str = API_VERSION
    request_id: str
    report_id: str
    analysis_id: str
    state: PublicReportState
    generated_at: datetime
    analysis_fingerprint: str
    report_artifact_version: str
    report_schema_version: str
    report_projection_version: str
    narrative_prompt_version: str
    narrative_schema_version: str
    narrative_provider: str
    narrative_model_id: str | None = None
    narrative_generation_mode: str | None = None
    narrative_fallback_version: str | None = None
    presentation_schema_version: str
    presentation_policy_version: str
    template_version: str
    stylesheet_version: str
    chart_version: str
    renderer_version: str
    content_sha256: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    byte_length: int | None = None
    content_path: str | None = None
    error: dict[str, str] | None = None
    created_at: datetime
    updated_at: datetime


_POST_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Missing or invalid Idempotency-Key"},
    401: {"model": ErrorResponse, "description": "Bearer authentication failed"},
    403: {"model": ErrorResponse, "description": "API key lacks analysis:write"},
    409: {"model": ErrorResponse, "description": "Idempotency conflict"},
    422: {"model": ErrorResponse, "description": "Request validation failed"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
    503: {"model": ErrorResponse, "description": "Analysis lifecycle unavailable"},
}
_GET_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Bearer authentication failed"},
    403: {"model": ErrorResponse, "description": "API key lacks analysis:read"},
    404: {"model": ErrorResponse, "description": "Analysis not found for authenticated consumer"},
    422: {"model": ErrorResponse, "description": "Request validation failed"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
    503: {"model": ErrorResponse, "description": "Analysis lifecycle unavailable"},
}
_REPORT_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Bearer authentication failed"},
    403: {"model": ErrorResponse, "description": "API key lacks required report scope"},
    404: {"model": ErrorResponse, "description": "Report/analysis not found for authenticated consumer"},
    409: {"model": ErrorResponse, "description": "Analysis/report is not reportable or content is unavailable"},
    422: {"model": ErrorResponse, "description": "Request validation failed"},
    500: {"model": ErrorResponse, "description": "Durable report invariant failure"},
    502: {"model": ErrorResponse, "description": "Stored report artifact failed integrity verification"},
    503: {"model": ErrorResponse, "description": "Report lifecycle unavailable"},
}


def _report_response(resource: RetrievedReportResource, *, request_id: UUID) -> ReportResourceResponse:
    error = None
    if resource.failure_code is not None:
        error = {
            "code": resource.failure_code,
            "message": resource.failure_message or "report artifact generation failed",
        }
    return ReportResourceResponse(
        request_id=str(request_id),
        report_id=str(resource.report_id),
        analysis_id=str(resource.analysis_id),
        state=resource.state,
        generated_at=resource.generated_at,
        analysis_fingerprint=resource.analysis_fingerprint,
        report_artifact_version=resource.report_artifact_version,
        report_schema_version=resource.report_schema_version,
        report_projection_version=resource.report_projection_version,
        narrative_prompt_version=resource.narrative_prompt_version,
        narrative_schema_version=resource.narrative_schema_version,
        narrative_provider=resource.narrative_provider,
        narrative_model_id=resource.narrative_model_id,
        narrative_generation_mode=resource.narrative_generation_mode,
        narrative_fallback_version=resource.narrative_fallback_version,
        presentation_schema_version=resource.presentation_schema_version,
        presentation_policy_version=resource.presentation_policy_version,
        template_version=resource.template_version,
        stylesheet_version=resource.stylesheet_version,
        chart_version=resource.chart_version,
        renderer_version=resource.renderer_version,
        content_sha256=resource.content_sha256,
        mime_type=resource.mime_type,
        filename=resource.filename,
        byte_length=resource.byte_length,
        content_path=(f"/v1/reports/{resource.report_id}/content" if resource.state == "ready" else None),
        error=error,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


def create_v1_router(
    lifecycle_backend: AnalysisLifecycleBackend | None,
    *,
    report_backend: PostgresReportArtifactBackend | None = None,
    database: Database | None,
    settings: Settings | None,
) -> APIRouter:
    router = APIRouter(prefix="/v1")

    def authenticate(
        credentials: HTTPAuthorizationCredentials | None,
        *,
        scope: str,
        report: bool = False,
    ) -> AuthenticatedConsumer:
        if database is None or settings is None:
            if report:
                raise ReportLifecycleUnavailable()
            raise AnalysisLifecycleUnavailable()
        authorization = None
        if credentials is not None:
            authorization = f"{credentials.scheme} {credentials.credentials}"
        with database.session() as session:
            consumer = authenticate_bearer(
                session,
                authorization,
                pepper=settings.api_key_pepper,
            )
        consumer.require_scope(scope)
        return consumer

    @router.post(
        "/analyses",
        response_model=AcceptedAnalysisResponse,
        status_code=status.HTTP_202_ACCEPTED,
        responses=_POST_RESPONSES,
        summary="Create an idempotent durable analysis resource",
        description="Requires Bearer service API key scope `analysis:write` and `Idempotency-Key`.",
    )
    def submit_analysis(
        payload: AnalysisRequest,
        request: Request,
        response: Response,
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
        idempotency_key: str | None = Header(
            default=None,
            alias="Idempotency-Key",
            description="Opaque retry key; maximum 200 UTF-8 bytes.",
        ),
    ) -> AcceptedAnalysisResponse:
        if lifecycle_backend is None:
            raise AnalysisLifecycleUnavailable()
        consumer = authenticate(credentials, scope="analysis:write")
        key = validate_idempotency_key(idempotency_key)
        request_id: UUID = request.state.request_id
        candidate_analysis_id = uuid4()
        command = build_analysis_ingress_command(
            payload,
            request_id=request_id,
            analysis_id=candidate_analysis_id,
        )
        accepted = lifecycle_backend.submit(
            command,
            payload,
            consumer_id=consumer.consumer_id,
            idempotency_key=key,
        )
        if accepted.state in {"queued", "running"} and settings is not None:
            response.headers["Retry-After"] = str(settings.poll_retry_after_seconds)
        return AcceptedAnalysisResponse(
            request_id=str(request_id),
            analysis_id=str(accepted.analysis_id),
            state=accepted.state,
        )

    @router.get(
        "/analyses/{analysis_id}",
        response_model=AnalysisResourceResponse,
        responses=_GET_RESPONSES,
        summary="Poll an authenticated consumer-owned analysis resource",
        description="Requires Bearer service API key scope `analysis:read`.",
    )
    def get_analysis(
        analysis_id: UUID,
        request: Request,
        response: Response,
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    ) -> AnalysisResourceResponse:
        if lifecycle_backend is None:
            raise AnalysisLifecycleUnavailable()
        consumer = authenticate(credentials, scope="analysis:read")
        resource = lifecycle_backend.retrieve(
            analysis_id,
            consumer_id=consumer.consumer_id,
        )
        if resource.state in {"queued", "running"} and settings is not None:
            response.headers["Retry-After"] = str(settings.poll_retry_after_seconds)
        return AnalysisResourceResponse(
            request_id=str(request.state.request_id),
            analysis_id=str(resource.analysis_id),
            state=resource.state,
            created_at=resource.created_at,
            updated_at=resource.updated_at,
            result=resource.result,
            readiness=resource.readiness,
            error=resource.error,
        )

    @router.post(
        "/reports",
        response_model=ReportResourceResponse,
        responses=_REPORT_RESPONSES,
        summary="Resolve the durable report artifact created by canonical analysis execution",
        description=(
            "Requires `report:write`. This endpoint never reconstructs authority from JSON and never reruns an analysis."
        ),
    )
    def resolve_report(
        payload: ReportResolveRequest,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    ) -> ReportResourceResponse:
        if report_backend is None:
            raise ReportLifecycleUnavailable()
        consumer = authenticate(credentials, scope="report:write", report=True)
        resource = report_backend.resolve(payload.analysis_id, consumer_id=consumer.consumer_id)
        return _report_response(resource, request_id=request.state.request_id)

    @router.get(
        "/reports/{report_id}",
        response_model=ReportResourceResponse,
        responses=_REPORT_RESPONSES,
        summary="Get a consumer-owned durable report resource",
        description="Requires `report:read`.",
    )
    def get_report(
        report_id: UUID,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    ) -> ReportResourceResponse:
        if report_backend is None:
            raise ReportLifecycleUnavailable()
        consumer = authenticate(credentials, scope="report:read", report=True)
        resource = report_backend.retrieve(report_id, consumer_id=consumer.consumer_id)
        return _report_response(resource, request_id=request.state.request_id)

    @router.get(
        "/reports/{report_id}/content",
        responses=_REPORT_RESPONSES,
        summary="Download verified consumer-owned report PDF bytes",
        description="Requires `report:read`; stored bytes are verified before response.",
    )
    def get_report_content(
        report_id: UUID,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    ) -> Response:
        if report_backend is None:
            raise ReportLifecycleUnavailable()
        consumer = authenticate(credentials, scope="report:read", report=True)
        resource, payload = report_backend.content(report_id, consumer_id=consumer.consumer_id)
        assert resource.filename is not None and resource.mime_type is not None
        return Response(
            content=payload,
            media_type=resource.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{resource.filename}"',
                "Content-SHA256": resource.content_sha256 or "",
                "Cache-Control": "private, no-store",
            },
        )

    return router
