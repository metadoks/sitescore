from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sitescore_commerce.api import create_app
from sitescore_commerce.fulfillment import AutomationStatus, AutomationUnauthorized, FulfillmentInvariantError, FulfillmentNotFound, SiteScoreProviderUnavailable


class DummyOrderService:
    pass


class DummyWebhookService:
    pass


class AutomationService:
    def __init__(self):
        self.key = "automation-key-test-0123456789"
        self.calls = []
        self.order_id = uuid4()
        self.result = AutomationStatus(self.order_id, "fulfillment_in_progress", "paid", "analysis_running", True, False, "advance")
        self.error = None

    def authorize_automation(self, authorization):
        self.calls.append(("auth", authorization))
        if authorization != f"Bearer {self.key}":
            raise AutomationUnauthorized("secret detail")

    def advance(self, order_id):
        self.calls.append(("advance", order_id))
        if self.error:
            raise self.error
        return replace(self.result, order_id=order_id)

    def status(self, order_id):
        self.calls.append(("status", order_id))
        if self.error:
            raise self.error
        return replace(self.result, order_id=order_id)


def client(service=None):
    return TestClient(create_app(service=DummyOrderService(), webhook_service=DummyWebhookService(), fulfillment_service=service or AutomationService()))


@pytest.mark.parametrize("method,path_suffix",[("get",""),("post","/advance")])
@pytest.mark.parametrize("authorization",[None,"","Bearer wrong","Basic nope","bearer automation-key-test-0123456789"])
def test_automation_requires_exact_bearer_before_order_lookup(method,path_suffix,authorization):
    service=AutomationService(); c=client(service); oid=uuid4(); headers={}
    if authorization is not None: headers["Authorization"]=authorization
    response=getattr(c,method)(f"/v1/automation/orders/{oid}{path_suffix}",headers=headers)
    assert response.status_code==401
    assert response.json()=={"error":{"code":"automation_unauthorized","message":"automation authentication failed"}}
    assert all(call[0]=="auth" for call in service.calls)
    assert service.key not in response.text


def test_advance_accepts_only_order_id_trigger_and_empty_body():
    service=AutomationService(); c=client(service); oid=uuid4(); headers={"Authorization":f"Bearer {service.key}"}
    response=c.post(f"/v1/automation/orders/{oid}/advance",headers=headers)
    assert response.status_code==200
    assert service.calls==[("auth",headers["Authorization"]),("advance",oid)]


@pytest.mark.parametrize("payload",[
    {"paid":True}, {"refund":True}, {"refund_amount":1}, {"analysis_id":str(uuid4())}, {"report_id":str(uuid4())},
    {"payment_intent":"pi_forged"}, {"refund_id":"re_forged"}, {"fulfillment_state":"completed"}, {}, [], "advance",
])
def test_advance_rejects_any_request_body_without_invoking_state_machine(payload):
    service=AutomationService(); c=client(service); oid=uuid4(); headers={"Authorization":f"Bearer {service.key}"}
    response=c.post(f"/v1/automation/orders/{oid}/advance",headers=headers,json=payload)
    assert response.status_code==400
    assert response.json()["error"]["code"]=="request_validation_failed"
    assert service.calls==[("auth",headers["Authorization"])]


def test_status_response_is_sanitized_and_has_no_provider_truth():
    service=AutomationService(); c=client(service); oid=uuid4(); response=c.get(f"/v1/automation/orders/{oid}",headers={"Authorization":f"Bearer {service.key}"})
    assert response.status_code==200
    assert response.json()=={
        "api_version":"v1","order_id":str(oid),"order_state":"fulfillment_in_progress","payment_state":"paid",
        "fulfillment_state":"analysis_running","retryable":True,"terminal":False,"next_action":"advance",
    }
    for forbidden in ["stripe","payment_intent","analysis_id","report_id","service_key","target_id","raw"]:
        assert forbidden not in response.text.lower()


@pytest.mark.parametrize("error,status,code",[
    (FulfillmentNotFound("db identity"),404,"order_not_found"),
    (FulfillmentInvariantError("secret invariant"),409,"fulfillment_invariant_conflict"),
    (SiteScoreProviderUnavailable("upstream 503 secret",retryable=True),503,"sitescore_provider_unavailable"),
    (SiteScoreProviderUnavailable("id mismatch secret",retryable=False),502,"sitescore_provider_unavailable"),
])
def test_automation_errors_are_sanitized(error,status,code):
    service=AutomationService(); service.error=error; c=client(service); oid=uuid4(); response=c.get(f"/v1/automation/orders/{oid}",headers={"Authorization":f"Bearer {service.key}"})
    assert response.status_code==status and response.json()["error"]["code"]==code
    assert str(error) not in response.text
