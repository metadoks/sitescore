from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from sitescore_commerce.checkout import CheckoutResult
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.service import OrderService
from sitescore_commerce.settings import STRIPE_API_VERSION, Settings
from conftest import valid_order

class FakeStore:
    def __init__(self):
        self.order_id=uuid4(); self.created=0; self.bound=None; self.checkout=SimpleNamespace(checkout_url=None, checkout_expires_at=None, provider_idempotency_key=f"sitescore:checkout:v1:{self.order_id}"); self.order=SimpleNamespace(customer_email="Customer@example.com",order_state="pending_payment",payment_state="pending",fulfillment_state="not_started")
    def get_or_create_order(self, **_): self.created+=1; return self.order_id
    def load_order_and_checkout(self, _): return self.order,self.checkout
    def bind_checkout(self, *, stripe_session_id, checkout_url, expires_at, **_): self.bound=(stripe_session_id,checkout_url); self.checkout.checkout_url=checkout_url; self.checkout.checkout_expires_at=expires_at; return self.checkout
class FakeGateway:
    def __init__(self): self.calls=[]
    def create_checkout(self, **kwargs):
        self.calls.append(kwargs); order_id=kwargs["order_id"]; entry=kwargs["entry"]
        return CheckoutResult("cs_test_123","https://checkout.stripe.com/c/pay/cs_test_123",datetime(2026,8,20,tzinfo=timezone.utc),"payment",str(order_id),{"sitescore_order_id":str(order_id),"sitescore_product_code":entry.product_code.value,"sitescore_catalog_version":entry.catalog_version})
def settings(): return Settings("postgresql+psycopg://unused","sk_test_not-real","price_1234567890","https://app.example.test/success","https://app.example.test/cancel","test")
def test_create_order_uses_server_catalog_and_stays_pending():
    store=FakeStore(); gateway=FakeGateway(); response=OrderService(settings(),store,gateway).create_order(request=OrderCreateRequest.model_validate(valid_order()), idempotency_key="retry-key")
    assert response.order_state=="pending_payment" and response.payment_state=="pending" and response.fulfillment_state=="not_started"; assert gateway.calls[0]["entry"].stripe_price_id=="price_1234567890"; assert gateway.calls[0]["entry"].quantity==1; assert gateway.calls[0]["provider_idempotency_key"]==f"sitescore:checkout:v1:{store.order_id}"; assert "session_id={CHECKOUT_SESSION_ID}" in gateway.calls[0]["success_url"]
def test_bound_checkout_is_reused_without_new_provider_call():
    store=FakeStore(); store.checkout.checkout_url="https://checkout.stripe.com/existing"; gateway=FakeGateway(); response=OrderService(settings(),store,gateway).create_order(request=OrderCreateRequest.model_validate(valid_order()), idempotency_key="retry-key"); assert response.checkout_url.endswith("/existing"); assert gateway.calls==[]
def test_stripe_version_is_exact_pin(): assert STRIPE_API_VERSION=="2026-07-29.dahlia"
