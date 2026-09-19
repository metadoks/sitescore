from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION, CheckoutResult
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.service import OrderService
from sitescore_commerce.settings import STRIPE_API_VERSION, Settings
from conftest import valid_order

class FakeStore:
    def __init__(self):
        self.order_id=None; self.created=0; self.bound=None; self.checkout=None; self.order=None
    def get_or_create_order(self, **kwargs):
        self.created+=1
        if self.order_id is not None: return self.order_id
        self.order_id=kwargs["candidate_order_id"]
        request=kwargs["request"]
        self.order=SimpleNamespace(customer_email=request.customer_email,product_code="location_report_v1",catalog_version=kwargs["catalog_version"],order_state="pending_payment",payment_state="pending",fulfillment_state="not_started")
        self.checkout=SimpleNamespace(order_id=self.order_id,checkout_url=None,checkout_expires_at=None,provider_idempotency_key=f"sitescore:checkout:v1:{self.order_id}",operation_version=kwargs["operation_version"],catalog_version=kwargs["catalog_version"],product_code="location_report_v1",stripe_price_id=kwargs["price_id"],quantity=kwargs["quantity"],customer_email=request.customer_email,success_url=kwargs["checkout_success_url"],cancel_url=kwargs["checkout_cancel_url"])
        return self.order_id
    def load_order_and_checkout(self, _): return self.order,self.checkout
    def bind_checkout(self, *, stripe_session_id, checkout_url, expires_at, **_): self.bound=(stripe_session_id,checkout_url); self.checkout.checkout_url=checkout_url; self.checkout.checkout_expires_at=expires_at; return self.checkout
class FakeGateway:
    def __init__(self): self.calls=[]
    def create_checkout(self, **kwargs):
        self.calls.append(kwargs); operation=kwargs["operation"]
        return CheckoutResult("cs_test_123","https://checkout.stripe.com/c/pay/cs_test_123",datetime(2026,8,20,tzinfo=timezone.utc),"payment",str(operation.order_id),{"sitescore_order_id":str(operation.order_id),"sitescore_product_code":operation.product_code.value,"sitescore_catalog_version":operation.catalog_version})
def settings(price="price_1234567890",success="https://app.example.test/success",cancel="https://app.example.test/cancel"): return Settings("postgresql+psycopg://unused","sk_test_not-real",price,success,cancel,"test")
def test_create_order_uses_server_catalog_and_stays_pending():
    store=FakeStore(); gateway=FakeGateway(); response=OrderService(settings(),store,gateway).create_order(request=OrderCreateRequest.model_validate(valid_order()), idempotency_key="retry-key")
    operation=gateway.calls[0]["operation"]
    assert response.order_state=="pending_payment" and response.payment_state=="pending" and response.fulfillment_state=="not_started"; assert operation.stripe_price_id=="price_1234567890"; assert operation.quantity==1; assert operation.operation_version==CHECKOUT_OPERATION_VERSION; assert operation.provider_idempotency_key==f"sitescore:checkout:v1:{store.order_id}"; assert "session_id={CHECKOUT_SESSION_ID}" in operation.success_url
def test_bound_checkout_is_reused_without_new_provider_call():
    store=FakeStore(); seed_gateway=FakeGateway(); request=OrderCreateRequest.model_validate(valid_order()); OrderService(settings(),store,seed_gateway).create_order(request=request,idempotency_key="retry-key"); store.checkout.checkout_url="https://checkout.stripe.com/existing"; gateway=FakeGateway(); response=OrderService(settings(),store,gateway).create_order(request=request,idempotency_key="retry-key"); assert response.checkout_url.endswith("/existing"); assert gateway.calls==[]
def test_unbound_retry_uses_original_snapshot_after_config_drift():
    store=FakeStore(); request=OrderCreateRequest.model_validate(valid_order()); first=FakeGateway(); service_a=OrderService(settings(price="price_A",success="https://a.example/success",cancel="https://a.example/cancel"),store,first)
    original_bind=store.bind_checkout
    def fail_bind(**_): raise RuntimeError("simulated local bind loss")
    store.bind_checkout=fail_bind
    try:
        service_a.create_order(request=request,idempotency_key="same-key")
    except RuntimeError: pass
    store.bind_checkout=original_bind; retry=FakeGateway(); OrderService(settings(price="price_B",success="https://b.example/success",cancel="https://b.example/cancel"),store,retry).create_order(request=request,idempotency_key="same-key")
    first_op=first.calls[0]["operation"]; retry_op=retry.calls[0]["operation"]
    assert retry_op==first_op; assert retry_op.stripe_price_id=="price_A"; assert retry_op.success_url.startswith("https://a.example/success"); assert retry_op.cancel_url.startswith("https://a.example/cancel")
def test_stripe_version_is_exact_pin(): assert STRIPE_API_VERSION=="2026-07-29.dahlia"
