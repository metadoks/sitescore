from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from .auth import AuthenticatedConsumer, authenticate_bearer
from .db import Database
from .errors import AnalysisLifecycleUnavailable, ErrorResponse
from .idempotency import validate_idempotency_key
from .ingress import build_analysis_ingress_command
from .lifecycle import AnalysisLifecycleBackend
from .models import AnalysisRequest
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


def create_v1_router(
    lifecycle_backend: AnalysisLifecycleBackend | None,
    *,
    database: Database | None,
    settings: Settings | None,
) -> APIRouter:
    router = APIRouter(prefix="/v1")

    def authenticate(
        credentials: HTTPAuthorizationCredentials | None,
        *,
        scope: str,
    ) -> AuthenticatedConsumer:
        if database is None or settings is None or lifecycle_backend is None:
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
        consumer = authenticate(credentials, scope="analysis:write")
        key = validate_idempotency_key(idempotency_key)
        request_id: UUID = request.state.request_id
        candidate_analysis_id = uuid4()
        command = build_analysis_ingress_command(
            payload,
            request_id=request_id,
            analysis_id=candidate_analysis_id,
        )
        assert lifecycle_backend is not None
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
        consumer = authenticate(credentials, scope="analysis:read")
        assert lifecycle_backend is not None
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

    return router
