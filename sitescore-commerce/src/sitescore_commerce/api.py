from __future__ import annotations

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from .checkout import CheckoutInvariantError, CheckoutProviderUnavailable, StripeCheckoutGateway
from .contracts import OrderCreateRequest, OrderCreateResponse
from .db import CommerceStore, IdempotencyConflict, PersistenceUnavailable
from .service import InvalidIdempotencyKey, OrderService
from .settings import ConfigurationError, Settings


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(*, service: OrderService | None = None) -> FastAPI:
    app = FastAPI(title="SiteScore Commerce API", version="0.1.0")
    if service is None:
        settings = Settings.from_env()
        service = OrderService(settings, CommerceStore(settings.database_url), StripeCheckoutGateway(settings))

    @app.exception_handler(InvalidIdempotencyKey)
    async def invalid_idempotency(_: Request, exc: InvalidIdempotencyKey) -> JSONResponse:
        return _error(400, "request_validation_failed", str(exc))

    @app.exception_handler(IdempotencyConflict)
    async def idempotency_conflict(_: Request, __: IdempotencyConflict) -> JSONResponse:
        return _error(409, "idempotency_conflict", "Idempotency-Key conflicts with a previous request")

    @app.exception_handler(ConfigurationError)
    async def configuration_unavailable(_: Request, __: ConfigurationError) -> JSONResponse:
        return _error(503, "commerce_configuration_unavailable", "commerce configuration is unavailable")

    @app.exception_handler(PersistenceUnavailable)
    async def persistence_unavailable(_: Request, __: PersistenceUnavailable) -> JSONResponse:
        return _error(503, "commerce_persistence_unavailable", "commerce persistence is unavailable")

    @app.exception_handler(CheckoutProviderUnavailable)
    async def provider_unavailable(_: Request, __: CheckoutProviderUnavailable) -> JSONResponse:
        return _error(503, "checkout_provider_unavailable", "checkout provider is unavailable")

    @app.exception_handler(CheckoutInvariantError)
    async def provider_invariant(_: Request, __: CheckoutInvariantError) -> JSONResponse:
        return _error(502, "checkout_provider_unavailable", "checkout provider response failed validation")

    @app.post("/v1/orders", response_model=OrderCreateResponse, status_code=201)
    def create_order(body: OrderCreateRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> OrderCreateResponse:
        if idempotency_key is None:
            raise InvalidIdempotencyKey("Idempotency-Key header is required")
        return service.create_order(request=body, idempotency_key=idempotency_key)
    return app
