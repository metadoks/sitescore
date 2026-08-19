from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from sitescore_commerce.api import create_app
from sitescore_commerce.delivery import DeliveryCapabilityUnavailable, DownloadPayload
from sitescore_commerce.fulfillment import AutomationStatus, AutomationUnauthorized


class StubOrder: pass
class StubWebhook: pass


class FulfillmentStub:
    def __init__(self): self.auth=[]
    def authorize_automation(self,value):
        self.auth.append(value)
        if value!="Bearer automation-secret": raise AutomationUnauthorized("bad")
    def status(self,oid):
        return AutomationStatus(oid,"fulfilled","paid","completed",False,True,"none")
    def advance(self,oid): return self.status(oid)


class DeliveryStub:
    def __init__(self): self.delivered=[]; self.downloaded=[]
    def deliver(self,oid): self.delivered.append(oid)
    def download(self,token):
        self.downloaded.append(token)
        if token=="unknown": raise DeliveryCapabilityUnavailable("no")
        return DownloadPayload(b"%PDF-1.7\napi\n%%EOF\n","verified-report.pdf","a"*64)


def client():
    fulfillment=FulfillmentStub(); delivery=DeliveryStub()
    app=create_app(service=StubOrder(),webhook_service=StubWebhook(),fulfillment_service=fulfillment,delivery_service=delivery)
    return TestClient(app),fulfillment,delivery


def test_delivery_automation_requires_same_bearer_and_empty_body_and_exposes_no_token():
    c,f,d=client(); oid=uuid4()
    assert c.post(f"/v1/automation/orders/{oid}/deliver").status_code==401
    assert c.post(f"/v1/automation/orders/{oid}/deliver",headers={"Authorization":"Bearer automation-secret"},json={"report_id":str(uuid4())}).status_code==400
    response=c.post(f"/v1/automation/orders/{oid}/deliver",headers={"Authorization":"Bearer automation-secret"},content=b"")
    assert response.status_code==200 and d.delivered==[oid]
    assert response.json()=={"api_version":"v1","order_id":str(oid),"order_state":"fulfilled","payment_state":"paid","fulfillment_state":"completed","retryable":False,"terminal":True,"next_action":"none"}
    text=response.text.lower()
    for forbidden in ["token","recipient","postmark","report_id","messageid","download_url"]: assert forbidden not in text


def test_public_download_returns_only_verified_pdf_with_private_headers():
    c,_,d=client(); token="A"*43; response=c.get(f"/d/{token}")
    assert response.status_code==200 and response.content.startswith(b"%PDF-") and d.downloaded==[token]
    assert response.headers["content-type"]=="application/pdf"
    assert response.headers["content-disposition"]=='attachment; filename="verified-report.pdf"'
    assert response.headers["cache-control"]=="private, no-store"
    assert response.headers["referrer-policy"]=="no-referrer"
    assert response.headers["x-content-type-options"]=="nosniff"
    assert response.headers["content-sha256"]=="a"*64


def test_invalid_capability_response_is_sanitized():
    c,_,_=client(); response=c.get("/d/unknown")
    assert response.status_code==404
    assert response.json()=={"error":{"code":"download_unavailable","message":"download is unavailable"}}
    text=response.text.lower()
    for forbidden in ["bucket","s3","authorization","service_key","postmark","report_id"]: assert forbidden not in text
