from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from .checkout import CheckoutInvariantError
from .db import CommerceStore, EventIdentityConflict, PersistenceUnavailable
from .settings import Settings

MAX_WEBHOOK_BODY_BYTES = 256 * 1024
WEBHOOK_SIGNATURE_TOLERANCE_SECONDS = 300
SUPPORTED_EVENTS = frozenset({"checkout.session.completed", "checkout.session.expired"})
ASYNC_EVENTS = frozenset({"checkout.session.async_payment_succeeded", "checkout.session.async_payment_failed"})


class WebhookVerificationError(ValueError):
    pass


class WebhookBodyTooLarge(ValueError):
    pass


class PaymentProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class StripeEventEnvelope:
    event_id: str
    event_type: str
    api_version: str | None
    livemode: bool
    created_at: datetime
    checkout_session_id: str | None
    candidate_order_id: str | None


@dataclass(frozen=True)
class StripeLineItemEvidence:
    price_id: str
    quantity: int
    currency: str


@dataclass(frozen=True)
class StripeCheckoutEvidence:
    session_id: str
    object_type: str
    mode: str
    livemode: bool
    client_reference_id: str
    metadata: dict[str, str]
    status: str
    payment_status: str
    payment_intent_id: str | None
    line_items: tuple[StripeLineItemEvidence, ...]


class WebhookVerifier(Protocol):
    def verify(self, raw_body: bytes, signature: str) -> StripeEventEnvelope: ...


class CheckoutEvidenceGateway(Protocol):
    def retrieve(self, session_id: str) -> StripeCheckoutEvidence: ...


def _stripe_value(obj: Any, key: str, default: Any = None) -> Any:
    try:
        return obj[key]
    except (KeyError, TypeError, AttributeError):
        return default


class StripeWebhookVerifier:
    def __init__(self, settings: Settings):
        self._secret = settings.stripe_webhook_secret

    def verify(self, raw_body: bytes, signature: str) -> StripeEventEnvelope:
        try:
            import stripe
            event = stripe.Webhook.construct_event(
                payload=raw_body,
                sig_header=signature,
                secret=self._secret,
                tolerance=WEBHOOK_SIGNATURE_TOLERANCE_SECONDS,
            )
        except Exception as exc:
            raise WebhookVerificationError("Stripe webhook signature verification failed") from exc
        try:
            data_object = event["data"]["object"]
            event_id = str(event["id"])
            event_type = str(event["type"])
            created_at = datetime.fromtimestamp(int(event["created"]), tz=timezone.utc)
            api_version_raw = _stripe_value(event, "api_version")
            api_version = str(api_version_raw) if api_version_raw is not None else None
            livemode = bool(event["livemode"])
            object_id_raw = _stripe_value(data_object, "id")
            object_id = str(object_id_raw) if object_id_raw else None
            metadata = _stripe_value(data_object, "metadata", {}) or {}
            candidate_order_id = _stripe_value(data_object, "client_reference_id") or _stripe_value(metadata, "sitescore_order_id")
            candidate_order_id = str(candidate_order_id) if candidate_order_id else None
        except Exception as exc:
            raise WebhookVerificationError("verified Stripe event schema is malformed") from exc
        if not event_id.startswith("evt_"):
            raise WebhookVerificationError("verified Stripe event identity is malformed")
        return StripeEventEnvelope(
            event_id=event_id,
            event_type=event_type,
            api_version=api_version,
            livemode=livemode,
            created_at=created_at,
            checkout_session_id=object_id,
            candidate_order_id=candidate_order_id,
        )


class StripeCheckoutEvidenceGateway:
    def __init__(self, settings: Settings):
        from stripe import StripeClient
        self._client = StripeClient(settings.stripe_secret_key)
        self._api_version = settings.stripe_api_version

    def retrieve(self, session_id: str) -> StripeCheckoutEvidence:
        options = {"stripe_version": self._api_version}
        try:
            session = self._client.v1.checkout.sessions.retrieve(session_id, options=options)
            items = self._client.v1.checkout.sessions.list_line_items(session_id, params={"limit": 2}, options=options)
        except Exception as exc:
            raise PaymentProviderUnavailable("Stripe Checkout reconciliation is unavailable") from exc
        line_items: list[StripeLineItemEvidence] = []
        for item in list(getattr(items, "data", []) or []):
            price = getattr(item, "price", None)
            line_items.append(
                StripeLineItemEvidence(
                    price_id=str(getattr(price, "id", "")),
                    quantity=int(getattr(item, "quantity", 0) or 0),
                    currency=str(getattr(price, "currency", "") or "").upper(),
                )
            )
        metadata = {str(k): str(v) for k, v in dict(getattr(session, "metadata", {}) or {}).items()}
        payment_intent = getattr(session, "payment_intent", None)
        if payment_intent is not None and not isinstance(payment_intent, str):
            payment_intent = getattr(payment_intent, "id", None)
        return StripeCheckoutEvidence(
            session_id=str(getattr(session, "id", "")),
            object_type=str(getattr(session, "object", "")),
            mode=str(getattr(session, "mode", "")),
            livemode=bool(getattr(session, "livemode", False)),
            client_reference_id=str(getattr(session, "client_reference_id", "")),
            metadata=metadata,
            status=str(getattr(session, "status", "")),
            payment_status=str(getattr(session, "payment_status", "")),
            payment_intent_id=str(payment_intent) if payment_intent else None,
            line_items=tuple(line_items),
        )


def _safe_uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except (TypeError, ValueError):
        return None


def validate_binding(*, evidence: StripeCheckoutEvidence, order: Any, checkout: Any, expected_livemode: bool) -> None:
    if evidence.object_type != "checkout.session":
        raise CheckoutInvariantError("Stripe object type mismatch")
    if evidence.mode != "payment":
        raise CheckoutInvariantError("Checkout mode mismatch")
    if evidence.livemode is not expected_livemode:
        raise CheckoutInvariantError("Checkout livemode mismatch")
    if evidence.client_reference_id != str(order.order_id):
        raise CheckoutInvariantError("Checkout client reference mismatch")
    expected_metadata = {
        "sitescore_order_id": str(order.order_id),
        "sitescore_product_code": order.product_code,
        "sitescore_catalog_version": order.catalog_version,
    }
    for key, expected in expected_metadata.items():
        if evidence.metadata.get(key) != expected:
            raise CheckoutInvariantError("Checkout metadata binding mismatch")
    if checkout.stripe_checkout_session_id is not None and evidence.session_id != checkout.stripe_checkout_session_id:
        raise CheckoutInvariantError("Checkout Session identity mismatch")
    if len(evidence.line_items) != 1:
        raise CheckoutInvariantError("Checkout line-item count mismatch")
    item = evidence.line_items[0]
    if item.price_id != checkout.stripe_price_id:
        raise CheckoutInvariantError("Checkout Price binding mismatch")
    if item.quantity != checkout.quantity or item.quantity != 1:
        raise CheckoutInvariantError("Checkout quantity mismatch")
    if item.currency != "USD":
        raise CheckoutInvariantError("Checkout currency mismatch")


@dataclass
class PaymentWebhookService:
    settings: Settings
    store: CommerceStore
    verifier: WebhookVerifier
    evidence_gateway: CheckoutEvidenceGateway

    def handle(self, *, raw_body: bytes, signature: str | None) -> dict[str, str]:
        if len(raw_body) > MAX_WEBHOOK_BODY_BYTES:
            raise WebhookBodyTooLarge("Stripe webhook body exceeds 256 KiB")
        if not signature:
            raise WebhookVerificationError("Stripe-Signature header is required")
        event = self.verifier.verify(raw_body, signature)
        raw_hash = hashlib.sha256(raw_body).hexdigest()
        self.store.record_stripe_event(event=event, raw_body_sha256=raw_hash)

        if event.api_version is not None and event.api_version != self.settings.stripe_api_version:
            self.store.mark_event_attention(event.event_id, "event_api_version_mismatch")
            return {"status": "accepted"}
        if event.livemode is not self.settings.stripe_expected_livemode:
            self.store.mark_event_attention(event.event_id, "event_livemode_mismatch")
            return {"status": "accepted"}
        if event.event_type in ASYNC_EVENTS or event.event_type not in SUPPORTED_EVENTS:
            self.store.mark_event_ignored(event.event_id, "unsupported_event")
            return {"status": "accepted"}
        state = self.store.get_event_state(event.event_id)
        if state in {"processed", "ignored", "attention_required"}:
            return {"status": "accepted"}

        order_id = _safe_uuid(event.candidate_order_id)
        if order_id is None or not event.checkout_session_id:
            self.store.mark_event_attention(event.event_id, "event_correlation_invalid")
            return {"status": "accepted"}
        try:
            order, checkout = self.store.load_order_and_checkout(order_id)
        except PersistenceUnavailable:
            self.store.mark_event_attention(event.event_id, "local_order_not_found")
            return {"status": "accepted"}

        evidence = self.evidence_gateway.retrieve(event.checkout_session_id)
        if evidence.session_id != event.checkout_session_id:
            self.store.mark_event_attention(event.event_id, "provider_session_id_mismatch")
            return {"status": "accepted"}
        try:
            validate_binding(evidence=evidence, order=order, checkout=checkout, expected_livemode=self.settings.stripe_expected_livemode)
        except CheckoutInvariantError:
            self.store.mark_event_attention(event.event_id, "provider_binding_mismatch")
            return {"status": "accepted"}

        if event.event_type == "checkout.session.completed":
            if evidence.status != "complete" or evidence.payment_status != "paid" or not evidence.payment_intent_id:
                self.store.mark_event_attention(event.event_id, "payment_not_authoritative")
                return {"status": "accepted"}
            self.store.apply_reconciliation(
                event_id=event.event_id,
                order_id=order_id,
                evidence=evidence,
                target="paid",
            )
        elif event.event_type == "checkout.session.expired":
            if evidence.status != "expired" or evidence.payment_status != "unpaid":
                self.store.mark_event_attention(event.event_id, "expiration_not_authoritative")
                return {"status": "accepted"}
            self.store.apply_reconciliation(
                event_id=event.event_id,
                order_id=order_id,
                evidence=evidence,
                target="expired",
            )
        return {"status": "accepted"}
