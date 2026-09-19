from __future__ import annotations
from uuid import uuid4
from fastapi.testclient import TestClient
from sitescore_commerce.api import create_app
from sitescore_commerce.contracts import OrderCreateResponse
from sitescore_commerce.db import IdempotencyConflict, PersistenceUnavailable
from conftest import valid_order
class Service:
    def __init__(self,error=None): self.error=error; self.calls=[]
    def create_order(self,*,request,idempotency_key):
        self.calls.append((request,idempotency_key))
        if self.error: raise self.error
        return OrderCreateResponse(request_id=uuid4(),order_id=uuid4(),product_code="location_report_v1",order_state="pending_payment",payment_state="pending",fulfillment_state="not_started",checkout_url="https://checkout.stripe.com/c/pay/test")
class DummyWebhook: pass
class DummyAutomation: pass
def client(service): return TestClient(create_app(service=service,webhook_service=DummyWebhook(),fulfillment_service=DummyAutomation()))
def test_post_orders_requires_idempotency_key():
    r=client(Service()).post("/v1/orders",json=valid_order()); assert r.status_code==400 and r.json()["error"]["code"]=="request_validation_failed"
def test_post_orders_returns_pending_resource_without_stripe_session_id():
    r=client(Service()).post("/v1/orders",headers={"Idempotency-Key":"abc"},json=valid_order()); body=r.json(); assert r.status_code==201; assert body["order_state"]=="pending_payment" and body["payment_state"]=="pending" and body["fulfillment_state"]=="not_started"; assert "stripe_checkout_session_id" not in body and "canonical_request_hash" not in body
def test_strict_body_rejects_paid_forgery():
    p=valid_order(); p["paid"]=True; assert client(Service()).post("/v1/orders",headers={"Idempotency-Key":"abc"},json=p).status_code==422
def test_idempotency_conflict_is_sanitized():
    r=client(Service(IdempotencyConflict("internal hash secret"))).post("/v1/orders",headers={"Idempotency-Key":"abc"},json=valid_order()); assert r.status_code==409; assert "internal hash secret" not in r.text
def test_persistence_error_is_sanitized():
    r=client(Service(PersistenceUnavailable("postgresql://user:password@db"))).post("/v1/orders",headers={"Idempotency-Key":"abc"},json=valid_order()); assert r.status_code==503; assert "password" not in r.text
