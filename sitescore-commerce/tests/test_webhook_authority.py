from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sitescore_commerce.api import create_app
from sitescore_commerce.checkout import CheckoutInvariantError
from sitescore_commerce.settings import STRIPE_API_VERSION, Settings
from sitescore_commerce.webhook import (
    MAX_WEBHOOK_BODY_BYTES,
    PaymentProviderUnavailable,
    PaymentWebhookService,
    StripeCheckoutEvidence,
    StripeEventEnvelope,
    StripeLineItemEvidence,
    StripeWebhookVerifier,
    WebhookVerificationError,
    validate_binding,
)

SECRET = "unit-test-signing-secret"


def settings(*, livemode=False):
    return Settings(
        "postgresql://unused",
        "sk_test_not-real",
        "price_1234567890",
        "https://example.com/success",
        "https://example.com/cancel",
        "test",
        SECRET,
        livemode,
    )


def event_payload(*, event_id="evt_123", event_type="checkout.session.completed", order_id=None, session_id="cs_test_123", api_version=STRIPE_API_VERSION, livemode=False, payment_status="paid"):
    order_id = order_id or str(uuid4())
    return {
        "id": event_id,
        "object": "event",
        "api_version": api_version,
        "created": int(time.time()),
        "livemode": livemode,
        "type": event_type,
        "data": {"object": {"id": session_id, "object": "checkout.session", "client_reference_id": order_id, "metadata": {"sitescore_order_id": order_id}, "payment_status": payment_status}},
    }


def signed(payload: dict, *, timestamp=None):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(SECRET.encode(), f"{timestamp}.".encode() + raw, hashlib.sha256).hexdigest()
    return raw, f"t={timestamp},v1={digest}"


def test_official_stripe_signature_verifier_uses_exact_raw_body():
    payload = event_payload()
    raw, signature = signed(payload)
    verifier = StripeWebhookVerifier(settings())
    assert verifier.verify(raw, signature).event_id == payload["id"]
    with pytest.raises(WebhookVerificationError):
        verifier.verify(raw + b" ", signature)


def test_stale_stripe_signature_fails_tolerance():
    raw, signature = signed(event_payload(), timestamp=int(time.time()) - 301)
    with pytest.raises(WebhookVerificationError):
        StripeWebhookVerifier(settings()).verify(raw, signature)


class MemoryStore:
    def __init__(self, order, checkout):
        self.order = order
        self.checkout = checkout
        self.events = {}
        self.outbox = []
        self.applied = []

    def record_stripe_event(self, *, event, raw_body_sha256):
        old = self.events.get(event.event_id)
        identity = (event.event_type, event.checkout_session_id, event.api_version, event.livemode, event.created_at, raw_body_sha256)
        if old is None:
            self.events[event.event_id] = {"identity": identity, "state": "received", "code": None}
        elif old["identity"] != identity:
            from sitescore_commerce.db import EventIdentityConflict
            raise EventIdentityConflict("conflict")

    def get_event_state(self, event_id):
        return self.events[event_id]["state"]

    def mark_event_attention(self, event_id, code):
        self.events[event_id]["state"] = "attention_required"; self.events[event_id]["code"] = code

    def mark_event_ignored(self, event_id, code):
        self.events[event_id]["state"] = "ignored"; self.events[event_id]["code"] = code

    def load_order_and_checkout(self, order_id):
        return self.order, self.checkout

    def apply_reconciliation(self, *, event_id, order_id, evidence, target):
        self.applied.append((event_id, order_id, evidence, target)); self.events[event_id]["state"] = "processed"


class FixedVerifier:
    def __init__(self, envelope): self.envelope = envelope
    def verify(self, raw_body, signature): return self.envelope


class FixedGateway:
    def __init__(self, evidence=None, exc=None): self.evidence=evidence; self.exc=exc; self.calls=0
    def retrieve(self, session_id):
        self.calls += 1
        if self.exc: raise self.exc
        return self.evidence


def authority_case(*, event_type="checkout.session.completed", api_version=STRIPE_API_VERSION, event_livemode=False, evidence_overrides=None):
    order_id = uuid4(); session_id="cs_test_authority"
    order = SimpleNamespace(order_id=order_id, product_code="location_report_v1", catalog_version="v1", order_state="pending_payment", payment_state="pending", fulfillment_state="not_started")
    checkout = SimpleNamespace(stripe_checkout_session_id=session_id, stripe_price_id="price_1234567890", quantity=1)
    envelope = StripeEventEnvelope("evt_authority", event_type, api_version, event_livemode, datetime.now(timezone.utc), session_id, str(order_id))
    values = dict(session_id=session_id, object_type="checkout.session", mode="payment", livemode=event_livemode, client_reference_id=str(order_id), metadata={"sitescore_order_id":str(order_id),"sitescore_product_code":"location_report_v1","sitescore_catalog_version":"v1"}, status="complete", payment_status="paid", payment_intent_id="pi_123", line_items=(StripeLineItemEvidence("price_1234567890",1,"USD"),))
    values.update(evidence_overrides or {})
    evidence = StripeCheckoutEvidence(**values)
    store=MemoryStore(order,checkout); gateway=FixedGateway(evidence)
    svc=PaymentWebhookService(settings(livemode=event_livemode),store,FixedVerifier(envelope),gateway)
    return svc,store,gateway,evidence


def test_completed_event_is_trigger_not_truth_when_provider_unpaid():
    svc,store,_,_=authority_case(evidence_overrides={"payment_status":"unpaid","payment_intent_id":None})
    assert svc.handle(raw_body=b"x",signature="sig")=={"status":"accepted"}
    assert store.applied==[] and store.events["evt_authority"]["code"]=="payment_not_authoritative"


@pytest.mark.parametrize("overrides", [
    {"session_id":"cs_wrong"},
    {"object_type":"payment_intent"},
    {"mode":"subscription"},
    {"client_reference_id":str(uuid4())},
    {"metadata":{"sitescore_order_id":"wrong","sitescore_product_code":"location_report_v1","sitescore_catalog_version":"v1"}},
    {"metadata":{"sitescore_order_id":"PLACEHOLDER","sitescore_product_code":"wrong","sitescore_catalog_version":"v1"}},
    {"metadata":{"sitescore_order_id":"PLACEHOLDER","sitescore_product_code":"location_report_v1","sitescore_catalog_version":"wrong"}},
    {"line_items":(StripeLineItemEvidence("price_wrong",1,"USD"),)},
    {"line_items":(StripeLineItemEvidence("price_1234567890",2,"USD"),)},
    {"line_items":(StripeLineItemEvidence("price_1234567890",1,"EUR"),)},
    {"line_items":()},
])
def test_binding_mismatches_never_apply_payment(overrides):
    svc,store,_,evidence=authority_case()
    fixed=dict(overrides)
    if "metadata" in fixed:
        fixed["metadata"]={k:(str(store.order.order_id) if v=="PLACEHOLDER" else v) for k,v in fixed["metadata"].items()}
    bad=StripeCheckoutEvidence(**{**evidence.__dict__,**fixed})
    svc.evidence_gateway=FixedGateway(bad)
    svc.handle(raw_body=b"x",signature="sig")
    assert store.applied==[]


def test_livemode_and_api_version_mismatch_stop_before_provider_retrieve():
    svc,store,gateway,_=authority_case(api_version="wrong")
    svc.handle(raw_body=b"x",signature="sig"); assert gateway.calls==0; assert store.events["evt_authority"]["code"]=="event_api_version_mismatch"
    svc,store,gateway,_=authority_case(event_livemode=True); svc.settings=Settings("postgresql://unused","sk","price_1234567890","https://example.com/s","https://example.com/c","test",SECRET,False)
    svc.handle(raw_body=b"x",signature="sig"); assert gateway.calls==0; assert store.events["evt_authority"]["code"]=="event_livemode_mismatch"


def test_paid_requires_payment_intent_identity_and_rejects_no_payment_required():
    for overrides in ({"payment_intent_id":None},{"payment_status":"no_payment_required","payment_intent_id":None}):
        svc,store,_,_=authority_case(evidence_overrides=overrides); svc.handle(raw_body=b"x",signature="sig"); assert store.applied==[]


def test_expired_requires_provider_expired_and_unpaid():
    svc,store,_,_=authority_case(event_type="checkout.session.expired",evidence_overrides={"status":"expired","payment_status":"unpaid","payment_intent_id":None})
    svc.handle(raw_body=b"x",signature="sig"); assert store.applied[-1][3]=="expired"


def test_unsupported_and_async_signed_events_are_ignored_without_provider_call():
    for event_type in ("customer.created","checkout.session.async_payment_succeeded","checkout.session.async_payment_failed"):
        svc,store,gateway,_=authority_case(event_type=event_type); svc.handle(raw_body=b"x",signature="sig"); assert gateway.calls==0; assert store.events["evt_authority"]["state"]=="ignored"


def test_provider_timeout_leaves_inbox_retryable_received():
    svc,store,_,_=authority_case(); svc.evidence_gateway=FixedGateway(exc=PaymentProviderUnavailable("timeout"))
    with pytest.raises(PaymentProviderUnavailable): svc.handle(raw_body=b"x",signature="sig")
    assert store.events["evt_authority"]["state"]=="received" and store.applied==[]


def test_api_missing_signature_and_oversize_fail_before_service_mutation():
    class DummyOrder: pass
    class CountingWebhook:
        def __init__(self): self.calls=0
        def handle(self,**kwargs): self.calls+=1; return {"status":"accepted"}
    webhook=CountingWebhook(); client=TestClient(create_app(service=DummyOrder(),webhook_service=webhook),raise_server_exceptions=False)
    response=client.post("/v1/webhooks/stripe",content=b"{}")
    assert response.status_code==400 and webhook.calls==0
    response=client.post("/v1/webhooks/stripe",content=b"x"*(MAX_WEBHOOK_BODY_BYTES+1),headers={"Stripe-Signature":"sig"})
    assert response.status_code==413 and webhook.calls==0
