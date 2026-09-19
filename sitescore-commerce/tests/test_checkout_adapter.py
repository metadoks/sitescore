from __future__ import annotations
from types import SimpleNamespace
from uuid import uuid4
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION, CheckoutOperation, StripeCheckoutGateway
from sitescore_commerce.contracts import ProductCode
from sitescore_commerce.settings import STRIPE_API_VERSION
class FakeSessions:
    def __init__(self): self.params=None; self.options=None
    def create(self, *, params, options): self.params=params; self.options=options; return SimpleNamespace(id="cs_test_exact",url="https://checkout.stripe.com/c/pay/cs_test_exact",expires_at=1787200000,mode=params["mode"],client_reference_id=params["client_reference_id"],metadata=params["metadata"])
class FakeClient:
    def __init__(self): self.v1=SimpleNamespace(checkout=SimpleNamespace(sessions=FakeSessions()))
def test_checkout_request_is_server_owned_card_only_and_version_pinned():
    order_id=uuid4(); operation=CheckoutOperation(order_id=order_id,provider_idempotency_key=f"sitescore:checkout:v1:{order_id}",operation_version=CHECKOUT_OPERATION_VERSION,product_code=ProductCode.LOCATION_REPORT_V1,catalog_version="v1",stripe_price_id="price_server_owned",quantity=1,customer_email="customer@example.com",success_url=f"https://app.example/success?order_id={order_id}&session_id={{CHECKOUT_SESSION_ID}}",cancel_url=f"https://app.example/cancel?order_id={order_id}"); gateway=StripeCheckoutGateway.__new__(StripeCheckoutGateway); gateway._client=FakeClient(); gateway._api_version=STRIPE_API_VERSION
    gateway.create_checkout(operation=operation)
    sessions=gateway._client.v1.checkout.sessions; params=sessions.params
    assert params["mode"]=="payment" and params["ui_mode"]=="hosted" and params["payment_method_types"]==["card"]; assert params["line_items"]==[{"price":"price_server_owned","quantity":1}]; assert "price_data" not in params["line_items"][0]; assert "allow_promotion_codes" not in params; assert params["client_reference_id"]==str(order_id); assert params["customer_email"]=="customer@example.com"; assert params["success_url"]==operation.success_url and params["cancel_url"]==operation.cancel_url; assert sessions.options=={"stripe_version":"2026-07-29.dahlia","idempotency_key":f"sitescore:checkout:v1:{order_id}"}
