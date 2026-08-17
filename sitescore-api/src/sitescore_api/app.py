from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .errors import (
    AnalysisLifecycleUnavailable,
    ErrorBody,
    ErrorResponse,
    IngressCommandValidationError,
)
from .lifecycle import AnalysisLifecycleBackend, UnavailableAnalysisLifecycleBackend
from .routes import create_v1_router
from .version import __version__


def _request_id(request: Request) -> UUID:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, UUID) and request_id.version == 4:
        return request_id
    request_id = uuid4()
    request.state.request_id = request_id
    return request_id


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    body = ErrorResponse(
        request_id=str(request_id),
        error=ErrorBody(code=code, message=message, details=details),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers={"X-Request-ID": str(request_id)},
    )


def _safe_validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for item in exc.errors():
        details.append(
            {
                "location": [str(part) for part in item.get("loc", ())],
                "message": str(item.get("msg", "invalid request")),
                "type": str(item.get("type", "validation_error")),
            }
        )
    return details


def create_app(lifecycle_backend: AnalysisLifecycleBackend | None = None) -> FastAPI:
    backend = lifecycle_backend or UnavailableAnalysisLifecycleBackend()
    app = FastAPI(
        title="SiteScore API",
        version=__version__,
        description=(
            "FAZ 5.0 external ingress foundation. The default backend does not "
            "provide a durable analysis lifecycle."
        ),
    )

    @app.middleware("http")
    async def server_request_id(request: Request, call_next):
        request_id = uuid4()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request_id)
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(request: Request, exc: RequestValidationError):
        return _error_response(
            request,
            status_code=422,
            code="request_validation_failed",
            message="request validation failed",
            details=_safe_validation_details(exc),
        )

    @app.exception_handler(IngressCommandValidationError)
    async def ingress_validation_error(request: Request, exc: IngressCommandValidationError):
        return _error_response(
            request,
            status_code=422,
            code="request_validation_failed",
            message="request validation failed",
        )

    @app.exception_handler(AnalysisLifecycleUnavailable)
    async def lifecycle_unavailable(request: Request, exc: AnalysisLifecycleUnavailable):
        return _error_response(
            request,
            status_code=503,
            code="analysis_lifecycle_unavailable",
            message="analysis lifecycle is unavailable",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return _error_response(
            request,
            status_code=500,
            code="internal_server_error",
            message="an unexpected internal error occurred",
        )

    app.include_router(create_v1_router(backend))
    return app


app = create_app()
