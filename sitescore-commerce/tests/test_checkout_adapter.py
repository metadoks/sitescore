from __future__ import annotations
from types import SimpleNamespace
from uuid import uuid4
from sitescore_commerce.checkout import ProductCatalogEntry, StripeCheckoutGateway
from sitescore_commerce.contracts import ProductCode
from sitescore_commerce.settings import STRIPE_API_VERSION
class FakeSessions:
    def __init__(self): self.params=None; self.options=None
    def create(self, *, params, options): self.params=params; self.options=options; return SimpleNamespace(id="cs_test_exact",url="https://checkout.stripe.com/c/pay/cs_test_exact",expires_at=1787200000,mode=params["mode"],client_reference_id=params["client_reference_id"],metadata=params["metadata"])
class FakeClient:
    def __init__(self): self.v1=SimpleNamespace(checkout=SimpleNamespace(sessions=FakeSessions()))
def test_checkout_request_is_server_owned_card_only_and_version_pinned():
    order_id=uuid4(); entry=ProductCatalogEntry(ProductCode.LOCATION_REPORT_V1,"v1",1,"USD","price_server_owned"); gateway=StripeCheckoutGateway.__new__(StripeCheckoutGateway); gateway._client=FakeClient(); gateway._api_version=STRIPE_API_VERSION
    gateway.create_checkout(order_id=order_id,email="customer@example.com",entry=entry,provider_idempotency_key=f"sitescore:checkout:v1:{order_id}",success_url=f"https://app.example/success?order_id={order_id}&session_id={{CHECKOUT_SESSION_ID}}",cancel_url=f"https://app.example/cancel?order_id={order_id}")
    sessions=gateway._client.v1.checkout.sessions; params=sessions.params
    assert params["mode"]=="payment" and params["ui_mode"]=="hosted" and params["payment_method_types"]==["card"]; assert params["line_items"]==[{"price":"price_server_owned","quantity":1}]; assert "price_data" not in params["line_items"][0]; assert "allow_promotion_codes" not in params; assert params["client_reference_id"]==str(order_id); assert sessions.options=={"stripe_version":"2026-07-29.dahlia","idempotency_key":f"sitescore:checkout:v1:{order_id}"}
