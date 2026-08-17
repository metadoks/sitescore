from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict

from .errors import ErrorResponse
from .ingress import build_analysis_ingress_command
from .lifecycle import AnalysisLifecycleBackend
from .models import AnalysisRequest
from .version import API_VERSION


class AcceptedAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    analysis_id: str


class AnalysisResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    analysis_id: str


_ERROR_RESPONSES = {
    422: {"model": ErrorResponse, "description": "Request validation failed"},
    503: {"model": ErrorResponse, "description": "Analysis lifecycle unavailable"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}


def create_v1_router(lifecycle_backend: AnalysisLifecycleBackend) -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.post(
        "/analyses",
        response_model=AcceptedAnalysisResponse,
        status_code=status.HTTP_202_ACCEPTED,
        responses=_ERROR_RESPONSES,
    )
    def submit_analysis(payload: AnalysisRequest, request: Request) -> AcceptedAnalysisResponse:
        request_id: UUID = request.state.request_id
        analysis_id = uuid4()
        command = build_analysis_ingress_command(
            payload,
            request_id=request_id,
            analysis_id=analysis_id,
        )
        accepted = lifecycle_backend.submit(command)
        if accepted.analysis_id != analysis_id:
            raise RuntimeError("lifecycle backend returned mismatched analysis identity")
        return AcceptedAnalysisResponse(
            request_id=str(request_id),
            analysis_id=str(analysis_id),
        )

    @router.get(
        "/analyses/{analysis_id}",
        response_model=AnalysisResourceResponse,
        responses=_ERROR_RESPONSES,
    )
    def get_analysis(analysis_id: UUID, request: Request) -> AnalysisResourceResponse:
        request_id: UUID = request.state.request_id
        resource = lifecycle_backend.retrieve(analysis_id)
        if resource.analysis_id != analysis_id:
            raise RuntimeError("lifecycle backend returned mismatched analysis identity")
        return AnalysisResourceResponse(
            request_id=str(request_id),
            analysis_id=str(resource.analysis_id),
        )

    return router
