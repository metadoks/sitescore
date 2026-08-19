from __future__ import annotations

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .checkout import CheckoutInvariantError, CheckoutProviderUnavailable, StripeCheckoutGateway
from .contracts import OrderCreateRequest, OrderCreateResponse
from .db import CommerceStore, EventIdentityConflict, IdempotencyConflict, PersistenceUnavailable
from .service import InvalidIdempotencyKey, OrderService
from .settings import ConfigurationError, Settings
from .webhook import (
    MAX_WEBHOOK_BODY_BYTES,
    PaymentProviderUnavailable,
    PaymentWebhookService,
    StripeCheckoutEvidenceGateway,
    StripeWebhookVerifier,
    WebhookBodyTooLarge,
    WebhookVerificationError,
)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


async def _read_webhook_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_WEBHOOK_BODY_BYTES:
            raise WebhookBodyTooLarge("Stripe webhook body exceeds 256 KiB")
        chunks.append(chunk)
    return b"".join(chunks)


def create_app(*, service: OrderService | None = None, webhook_service: PaymentWebhookService | None = None) -> FastAPI:
    app = FastAPI(title="SiteScore Commerce API", version="0.2.0")
    if service is None or webhook_service is None:
        settings = Settings.from_env()
        store = CommerceStore(settings.database_url)
        if service is None:
            service = OrderService(settings, store, StripeCheckoutGateway(settings))
        if webhook_service is None:
            webhook_service = PaymentWebhookService(settings, store, StripeWebhookVerifier(settings), StripeCheckoutEvidenceGateway(settings))

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

    @app.exception_handler(PaymentProviderUnavailable)
    async def reconciliation_provider_unavailable(_: Request, __: PaymentProviderUnavailable) -> JSONResponse:
        return _error(503, "payment_provider_unavailable", "payment provider reconciliation is unavailable")

    @app.exception_handler(CheckoutInvariantError)
    async def provider_invariant(_: Request, __: CheckoutInvariantError) -> JSONResponse:
        return _error(502, "checkout_provider_unavailable", "checkout provider response failed validation")

    @app.exception_handler(WebhookVerificationError)
    async def webhook_verification(_: Request, __: WebhookVerificationError) -> JSONResponse:
        return _error(400, "stripe_webhook_invalid", "Stripe webhook verification failed")

    @app.exception_handler(WebhookBodyTooLarge)
    async def webhook_too_large(_: Request, __: WebhookBodyTooLarge) -> JSONResponse:
        return _error(413, "stripe_webhook_too_large", "Stripe webhook body exceeds the accepted limit")

    @app.exception_handler(EventIdentityConflict)
    async def webhook_identity_conflict(_: Request, __: EventIdentityConflict) -> JSONResponse:
        return _error(409, "stripe_event_identity_conflict", "Stripe event identity conflicts with durable state")

    @app.post("/v1/orders", response_model=OrderCreateResponse, status_code=201)
    def create_order(body: OrderCreateRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> OrderCreateResponse:
        if idempotency_key is None:
            raise InvalidIdempotencyKey("Idempotency-Key header is required")
        return service.create_order(request=body, idempotency_key=idempotency_key)

    @app.post("/v1/webhooks/stripe", status_code=200)
    async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")) -> dict[str, str]:
        raw_body = await _read_webhook_body(request)
        return await run_in_threadpool(webhook_service.handle, raw_body=raw_body, signature=stripe_signature)

    return app
