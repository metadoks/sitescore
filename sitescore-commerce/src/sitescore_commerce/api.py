from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from .checkout import CheckoutInvariantError, CheckoutProviderUnavailable, StripeCheckoutGateway
from .automation_contracts import AutomationOrderResponse
from .contracts import OrderCreateRequest, OrderCreateResponse
from .db import CommerceStore, EventIdentityConflict, IdempotencyConflict, PersistenceUnavailable
from .delivery import DeliveryCapabilityUnavailable, DeliveryInvariantError, DeliveryService, DeliveryUpstreamUnavailable
from .delivery_runtime import build_runtime_delivery_service
from .fulfillment import (
    AutomationUnauthorized,
    FulfillmentInvariantError,
    FulfillmentNotFound,
    FulfillmentService,
    RefundProviderUnavailable,
    SiteScoreProviderUnavailable,
)
from .fulfillment_runtime import build_runtime_fulfillment_service
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


def _automation_response(status: object) -> AutomationOrderResponse:
    return AutomationOrderResponse(
        order_id=status.order_id,
        order_state=status.order_state,
        payment_state=status.payment_state,
        fulfillment_state=status.fulfillment_state,
        retryable=status.retryable,
        terminal=status.terminal,
        next_action=status.next_action,
    )


def create_app(
    *,
    service: OrderService | None = None,
    webhook_service: PaymentWebhookService | None = None,
    fulfillment_service: FulfillmentService | None = None,
    delivery_service: DeliveryService | None = None,
) -> FastAPI:
    app = FastAPI(title="SiteScore Commerce API", version="0.5.0")

    settings: Settings | None = None
    store: CommerceStore | None = None
    # Preserve dependency-injected unit tests: only load environment when an unprovided
    # pre-6.4 production service actually needs construction. A separately injected
    # delivery service never forces environment loading into legacy unit tests.
    if service is None or webhook_service is None or fulfillment_service is None:
        try:
            settings = Settings.from_env()
        except ConfigurationError:
            if service is None or webhook_service is None:
                raise
            settings = None
    if settings is not None:
        store = CommerceStore(settings.database_url)
        if service is None:
            service = OrderService(settings, store, StripeCheckoutGateway(settings))
        if webhook_service is None:
            webhook_service = PaymentWebhookService(settings, store, StripeWebhookVerifier(settings), StripeCheckoutEvidenceGateway(settings))
        if fulfillment_service is None:
            fulfillment_service = build_runtime_fulfillment_service(settings, store)
        if delivery_service is None:
            delivery_service = build_runtime_delivery_service(settings, store)

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

    @app.exception_handler(RefundProviderUnavailable)
    async def refund_provider_unavailable(_: Request, __: RefundProviderUnavailable) -> JSONResponse:
        return _error(503, "refund_provider_unavailable", "refund provider reconciliation is unavailable")

    @app.exception_handler(SiteScoreProviderUnavailable)
    async def sitescore_provider_unavailable(_: Request, exc: SiteScoreProviderUnavailable) -> JSONResponse:
        status = 503 if exc.retryable else 502
        return _error(status, "sitescore_provider_unavailable", "SiteScore fulfillment provider is unavailable")

    @app.exception_handler(DeliveryUpstreamUnavailable)
    async def delivery_upstream_unavailable(_: Request, exc: DeliveryUpstreamUnavailable) -> JSONResponse:
        status = 503 if exc.retryable else 502
        return _error(status, "delivery_upstream_unavailable", "delivery upstream verification is unavailable")

    @app.exception_handler(CheckoutInvariantError)
    async def provider_invariant(_: Request, __: CheckoutInvariantError) -> JSONResponse:
        return _error(502, "checkout_provider_unavailable", "checkout provider response failed validation")

    @app.exception_handler(FulfillmentInvariantError)
    async def fulfillment_invariant(_: Request, __: FulfillmentInvariantError) -> JSONResponse:
        return _error(409, "fulfillment_invariant_conflict", "fulfillment state failed a server authority invariant")

    @app.exception_handler(DeliveryInvariantError)
    async def delivery_invariant(_: Request, __: DeliveryInvariantError) -> JSONResponse:
        return _error(409, "delivery_invariant_conflict", "delivery state failed a server authority invariant")

    @app.exception_handler(DeliveryCapabilityUnavailable)
    async def delivery_capability_unavailable(_: Request, __: DeliveryCapabilityUnavailable) -> JSONResponse:
        return _error(404, "download_unavailable", "download is unavailable")

    @app.exception_handler(FulfillmentNotFound)
    async def fulfillment_not_found(_: Request, __: FulfillmentNotFound) -> JSONResponse:
        return _error(404, "order_not_found", "order not found")

    @app.exception_handler(AutomationUnauthorized)
    async def automation_unauthorized(_: Request, __: AutomationUnauthorized) -> JSONResponse:
        return _error(401, "automation_unauthorized", "automation authentication failed")

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
        if service is None:
            raise ConfigurationError("order service is unavailable")
        return service.create_order(request=body, idempotency_key=idempotency_key)

    @app.post("/v1/webhooks/stripe", status_code=200)
    async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")) -> dict[str, str]:
        raw_body = await _read_webhook_body(request)
        if not stripe_signature:
            raise WebhookVerificationError("Stripe-Signature header is required")
        if webhook_service is None:
            raise ConfigurationError("webhook service is unavailable")
        return await run_in_threadpool(webhook_service.handle, raw_body=raw_body, signature=stripe_signature)

    @app.post("/v1/automation/orders/{order_id}/advance", response_model=AutomationOrderResponse)
    async def advance_order(request: Request, order_id: UUID, authorization: str | None = Header(default=None, alias="Authorization")) -> AutomationOrderResponse:
        if fulfillment_service is None:
            raise ConfigurationError("fulfillment service is unavailable")
        fulfillment_service.authorize_automation(authorization)
        if await request.body():
            return _error(400, "request_validation_failed", "automation advance request body must be empty")
        result = await run_in_threadpool(fulfillment_service.advance, order_id)
        return _automation_response(result)

    @app.post("/v1/automation/orders/{order_id}/deliver", response_model=AutomationOrderResponse)
    async def deliver_order(request: Request, order_id: UUID, authorization: str | None = Header(default=None, alias="Authorization")) -> AutomationOrderResponse:
        if fulfillment_service is None or delivery_service is None:
            raise ConfigurationError("delivery service is unavailable")
        fulfillment_service.authorize_automation(authorization)
        if await request.body():
            return _error(400, "request_validation_failed", "automation delivery request body must be empty")
        await run_in_threadpool(delivery_service.deliver, order_id)
        result = await run_in_threadpool(fulfillment_service.status, order_id)
        return _automation_response(result)

    @app.get("/v1/automation/orders/{order_id}", response_model=AutomationOrderResponse)
    async def get_automation_order(order_id: UUID, authorization: str | None = Header(default=None, alias="Authorization")) -> AutomationOrderResponse:
        if fulfillment_service is None:
            raise ConfigurationError("fulfillment service is unavailable")
        fulfillment_service.authorize_automation(authorization)
        result = await run_in_threadpool(fulfillment_service.status, order_id)
        return _automation_response(result)

    @app.get("/d/{opaque_token}")
    async def download_report(opaque_token: str) -> Response:
        if delivery_service is None:
            raise ConfigurationError("delivery service is unavailable")
        payload = await run_in_threadpool(delivery_service.download, opaque_token)
        return Response(
            content=payload.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{payload.filename}"',
                "Cache-Control": "private, no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Content-SHA256": payload.content_sha256,
            },
        )

    return app
