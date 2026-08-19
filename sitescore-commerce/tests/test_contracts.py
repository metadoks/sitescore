from __future__ import annotations

import pytest
from pydantic import ValidationError
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.service import InvalidIdempotencyKey, digest_idempotency_key
from conftest import valid_order

FORBIDDEN = {"amount":10,"unit_amount":10,"currency":"USD","stripe_price_id":"price_attacker","discount":"x","coupon":"x","paid":True,"payment_status":"paid","success_url":"https://evil.example/","cancel_url":"https://evil.example/","analysis_id":"x","report_id":"x"}

@pytest.mark.parametrize("sector", ["coffee","restaurant","gym","beauty"])
def test_four_sector_valid_purchase_intent(sector: str) -> None:
    model = OrderCreateRequest.model_validate(valid_order(sector)); assert model.analysis_request.sector == sector; assert model.customer_email == "Customer@example.com"

@pytest.mark.parametrize("field,value", FORBIDDEN.items())
def test_caller_forbidden_fields_fail_closed(field: str, value: object) -> None:
    payload=valid_order(); payload[field]=value
    with pytest.raises(ValidationError): OrderCreateRequest.model_validate(payload)

def test_unknown_product_rejected() -> None:
    payload=valid_order(); payload["product_code"]="attacker_product"
    with pytest.raises(ValidationError): OrderCreateRequest.model_validate(payload)

def test_unknown_nested_analysis_field_rejected() -> None:
    payload=valid_order(); payload["analysis_request"]["trusted"]=True
    with pytest.raises(ValidationError): OrderCreateRequest.model_validate(payload)

def test_canonical_hash_is_normalized_and_deterministic() -> None:
    left=OrderCreateRequest.model_validate(valid_order()); payload=valid_order(); payload["customer_email"]="  Customer@Example.COM  "; right=OrderCreateRequest.model_validate(payload); assert left.canonical_hash()==right.canonical_hash()

def test_idempotency_key_validation_and_digest() -> None:
    assert digest_idempotency_key("caller-key") != "caller-key"; assert digest_idempotency_key("caller-key") == digest_idempotency_key("caller-key")
    with pytest.raises(InvalidIdempotencyKey): digest_idempotency_key(" ")
    with pytest.raises(InvalidIdempotencyKey): digest_idempotency_key("é"*101)
