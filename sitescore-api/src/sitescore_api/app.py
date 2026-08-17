from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .errors import (
    ErrorBody,
    ErrorResponse,
    IngressCommandValidationError,
    SiteScoreApiError,
)
from .routes import create_v1_router
from .runtime import Runtime, build_runtime
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
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    body = ErrorResponse(
        request_id=str(request_id),
        error=ErrorBody(code=code, message=message, details=details),
    )
    response_headers = {"X-Request-ID": str(request_id)}
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers=response_headers,
    )


def _safe_validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    return [
        {
            "location": [str(part) for part in item.get("loc", ())],
            "message": str(item.get("msg", "invalid request")),
            "type": str(item.get("type", "validation_error")),
        }
        for item in exc.errors()
    ]


def create_app(
    runtime: Runtime | None = None,
    *,
    load_environment: bool = False,
) -> FastAPI:
    if runtime is None and load_environment:
        try:
            runtime = build_runtime()
        except ValueError:
            # Missing/invalid deployment configuration fails closed at request time.
            runtime = None

    app = FastAPI(
        title="SiteScore API",
        version=__version__,
        description=(
            "FAZ 5.1 machine-consumer API. PostgreSQL is durable lifecycle truth; "
            "Redis/Celery are execution transport only. Current locked COMB-005 "
            "authority is not approved, so the real canonical production path is "
            "expected to terminate as not_score_ready. V1 cancellation and callbacks/webhooks are not supported."
        ),
    )
    app.state.sitescore_runtime = runtime

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

    @app.exception_handler(SiteScoreApiError)
    async def sitescore_api_error(request: Request, exc: SiteScoreApiError):
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.public_message,
            headers=exc.headers,
        )

    @app.exception_handler(404)
    async def route_not_found(request: Request, exc: Exception):
        return _error_response(
            request,
            status_code=404,
            code="route_not_found",
            message="route not found",
        )

    @app.exception_handler(405)
    async def method_not_allowed(request: Request, exc: Exception):
        return _error_response(
            request,
            status_code=405,
            code="method_not_allowed",
            message="method not allowed",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return _error_response(
            request,
            status_code=500,
            code="internal_server_error",
            message="an unexpected internal error occurred",
        )

    app.include_router(
        create_v1_router(
            runtime.lifecycle if runtime is not None else None,
            database=runtime.database if runtime is not None else None,
            settings=runtime.settings if runtime is not None else None,
        )
    )
    return app


app = create_app(load_environment=True)
