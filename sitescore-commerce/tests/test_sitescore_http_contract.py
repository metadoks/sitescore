from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from sitescore_commerce.fulfillment import ANALYSIS_OPERATION_VERSION, AnalysisOperation, SiteScoreHttpGateway, SiteScoreProviderUnavailable
from sitescore_commerce.settings import Settings


def settings():
    return Settings(
        "postgresql+psycopg://unused/test",
        "sk_test_not-real",
        "price_1234567890",
        "https://app.example/success",
        "https://app.example/cancel",
        "test",
        "test-signing-secret",
        False,
        "2026-07-29.dahlia",
        "https://sitescore.example",
        "ssk1_key-id.service-secret-0123456789",
        "target-v1",
        10,
        "automation-key-test-0123456789",
    )


class Response:
    def __init__(self,status,payload): self.status_code=status; self.payload=payload
    def json(self): return self.payload


def test_analysis_post_uses_frozen_bearer_auth_exact_durable_payload_and_idempotency(monkeypatch):
    oid=uuid4(); aid=uuid4(); payload={"sector":"coffee","location":{"country_code":"US","street":"1 Main St","city":"Boston","state":"MA"},"business_inputs":{"target_population":10000,"target_rate":0.5,"capture_rate_conservative":0.01,"capture_rate_base":0.02,"capture_rate_optimistic":0.03,"visit_frequency_per_month":3,"average_ticket":8},"costs":{"monthly_rent":5000,"fixed_labor":12000,"fixed_overhead":2500}}; calls=[]
    def request(method,url,**kwargs): calls.append((method,url,kwargs)); return Response(201,{"api_version":"v1","analysis_id":str(aid),"state":"queued"})
    monkeypatch.setattr(httpx,"request",request); gateway=SiteScoreHttpGateway(settings()); op=AnalysisOperation(oid,"target-v1","https://sitescore.example",ANALYSIS_OPERATION_VERSION,f"sitescore:analysis:v1:{oid}",payload,"a"*64,None,None,None,None); evidence=gateway.submit_analysis(op); assert evidence.analysis_id==aid and evidence.state=="queued"; method,url,kwargs=calls[0]; assert method=="POST" and url=="https://sitescore.example/v1/analyses"; assert kwargs["json"]==payload and kwargs["headers"]["Idempotency-Key"]==f"sitescore:analysis:v1:{oid}"; assert kwargs["headers"]["Authorization"]=="Bearer ssk1_key-id.service-secret-0123456789"


def test_report_resolver_uses_only_bound_analysis_id_and_bearer_auth(monkeypatch):
    aid=uuid4(); rid=uuid4(); calls=[]
    def request(method,url,**kwargs): calls.append((method,url,kwargs)); return Response(201,{"api_version":"v1","report_id":str(rid),"analysis_id":str(aid),"state":"ready"})
    monkeypatch.setattr(httpx,"request",request); evidence=SiteScoreHttpGateway(settings()).resolve_report(base_url="https://sitescore.example",analysis_id=aid); assert evidence.report_id==rid and evidence.analysis_id==aid and evidence.state=="ready"; method,url,kwargs=calls[0]; assert method=="POST" and url=="https://sitescore.example/v1/reports" and kwargs["json"]=={"analysis_id":str(aid)} and "Idempotency-Key" not in kwargs["headers"]; assert kwargs["headers"]["Authorization"].startswith("Bearer ssk1_")


def test_upstream_error_does_not_echo_service_secret(monkeypatch):
    secret=settings().sitescore_api_service_key
    def request(*args,**kwargs): raise httpx.ConnectError(f"connection failed with credential {secret}")
    monkeypatch.setattr(httpx,"request",request); gateway=SiteScoreHttpGateway(settings())
    with pytest.raises(SiteScoreProviderUnavailable) as exc: gateway.get_analysis(base_url="https://sitescore.example",analysis_id=uuid4())
    assert secret not in str(exc.value) and exc.value.code=="sitescore_network_error" and exc.value.retryable is True
