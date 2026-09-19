from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import uuid4

from .checkout import CHECKOUT_OPERATION_VERSION, CheckoutGateway, CheckoutInvariantError, CheckoutOperation, catalog_from_settings, cancel_url, success_url, validate_checkout_result
from .contracts import FulfillmentState, OrderCreateRequest, OrderCreateResponse, OrderState, PaymentState, ProductCode
from .db import CommerceStore
from .settings import Settings


class InvalidIdempotencyKey(ValueError):
    pass


def digest_idempotency_key(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidIdempotencyKey("Idempotency-Key must be a string")
    if not value.strip():
        raise InvalidIdempotencyKey("Idempotency-Key must not be blank")
    if len(value.encode("utf-8")) > 200:
        raise InvalidIdempotencyKey("Idempotency-Key exceeds 200 UTF-8 bytes")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class OrderService:
    settings: Settings
    store: CommerceStore
    checkout_gateway: CheckoutGateway

    def create_order(self, *, request: OrderCreateRequest, idempotency_key: str) -> OrderCreateResponse:
        key_digest = digest_idempotency_key(idempotency_key)
        entry = catalog_from_settings(self.settings)
        candidate_order_id = uuid4()
        order_id = self.store.get_or_create_order(
            candidate_order_id=candidate_order_id,
            key_digest=key_digest,
            request=request,
            catalog_version=entry.catalog_version,
            price_id=entry.stripe_price_id,
            quantity=entry.quantity,
            operation_version=CHECKOUT_OPERATION_VERSION,
            checkout_success_url=success_url(self.settings, candidate_order_id),
            checkout_cancel_url=cancel_url(self.settings, candidate_order_id),
        )
        order, checkout = self.store.load_order_and_checkout(order_id)
        try:
            operation = CheckoutOperation(
                order_id=order_id,
                provider_idempotency_key=checkout.provider_idempotency_key,
                operation_version=checkout.operation_version,
                product_code=ProductCode(checkout.product_code),
                catalog_version=checkout.catalog_version,
                stripe_price_id=checkout.stripe_price_id,
                quantity=checkout.quantity,
                customer_email=checkout.customer_email,
                success_url=checkout.success_url,
                cancel_url=checkout.cancel_url,
            )
        except (AttributeError, ValueError) as exc:
            raise CheckoutInvariantError("durable checkout operation snapshot is invalid") from exc
        if operation.customer_email != order.customer_email or operation.product_code.value != order.product_code or operation.catalog_version != order.catalog_version:
            raise CheckoutInvariantError("durable checkout operation/order binding mismatch")
        if checkout.checkout_url is None:
            result = self.checkout_gateway.create_checkout(operation=operation)
            validate_checkout_result(result, operation=operation)
            checkout = self.store.bind_checkout(order_id=order_id, stripe_session_id=result.session_id, checkout_url=result.url, expires_at=result.expires_at)
        if order.order_state != OrderState.PENDING_PAYMENT.value or order.payment_state != PaymentState.PENDING.value or order.fulfillment_state != FulfillmentState.NOT_STARTED.value:
            raise RuntimeError("6.0 order state invariant failed")
        if checkout.checkout_url is None:
            raise RuntimeError("checkout binding invariant failed")
        return OrderCreateResponse(request_id=uuid4(), order_id=order_id, product_code=ProductCode.LOCATION_REPORT_V1, order_state=OrderState.PENDING_PAYMENT, payment_state=PaymentState.PENDING, fulfillment_state=FulfillmentState.NOT_STARTED, checkout_url=checkout.checkout_url, checkout_expires_at=checkout.checkout_expires_at.isoformat() if checkout.checkout_expires_at else None)
