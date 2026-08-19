from __future__ import annotations

import hashlib
import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID, uuid4

import httpx
import pytest

from sitescore_commerce.delivery import (
    DELIVERY_GRANT_TTL,
    POSTMARK_ENDPOINT,
    DeliveryUpstreamUnavailable,
    PostmarkGateway,
    PostmarkRejected,
    PostmarkUncertain,
    SiteScoreDeliveryGateway,
    generate_delivery_token,
    token_digest,
)
from sitescore_commerce.settings import Settings


def settings(**overrides) -> Settings:
    values = dict(
        database_url="postgresql+psycopg://localhost/test",
        stripe_secret_key="sk_test_not-real",
        stripe_price_location_report_v1="price_1234567890",
        success_url_base="https://app.example/success",
        cancel_url_base="https://app.example/cancel",
        environment="test",
        stripe_webhook_secret="test-signing-secret",
        stripe_expected_livemode=False,
        sitescore_api_base_url="http://127.0.0.1:18081",
        sitescore_api_service_key="ssk1_key.secret-secret-secret-secret-0123456789",
        sitescore_api_target_id="test-v1",
        sitescore_api_timeout_seconds=1.0,
        commerce_automation_api_key="automation-key-test-0123456789",
        postmark_server_token="postmark-test-token-not-real",
        postmark_from_email="reports@sitescore.example",
        postmark_template_alias="sitescore-report-v1",
        postmark_timeout_seconds=1.0,
        commerce_public_base_url="https://commerce.example",
    )
    values.update(overrides)
    return Settings(**values)


def test_delivery_token_has_256_bits_source_and_digest_only_shape():
    first = generate_delivery_token(); second = generate_delivery_token()
    assert first != second
    assert len(first) >= 43 and len(second) >= 43
    assert all(ch.isalnum() or ch in "-_" for ch in first)
    digest = token_digest(first)
    assert len(digest) == 64 and digest == hashlib.sha256(first.encode("ascii")).hexdigest()
    assert first not in digest
    assert DELIVERY_GRANT_TTL == timedelta(days=7)


class FakePostmark:
    def __init__(self, *, status=200, payload=None, delay=0.0):
        self.status = status
        self.payload = payload if payload is not None else {
            "To": "customer@example.com",
            "SubmittedAt": "2026-08-20T00:15:30.0000000Z",
            "MessageID": "00000000-0000-4000-8000-000000000777",
            "ErrorCode": 0,
            "Message": "OK",
        }
        self.delay = delay
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                import time
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                outer.requests.append((self.path, dict(self.headers), json.loads(body)))
                if outer.delay:
                    time.sleep(outer.delay)
                data = json.dumps(outer.payload).encode()
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try: self.wfile.write(data)
                except BrokenPipeError: pass
            def log_message(self, *args): pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def endpoint(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}/email/withTemplate"

    def close(self):
        self.server.shutdown(); self.thread.join(timeout=2); self.server.server_close()


def send(fake: FakePostmark, **kwargs):
    gateway = PostmarkGateway(settings(), endpoint=fake.endpoint)
    return gateway.send(
        recipient=kwargs.get("recipient", "customer@example.com"),
        order_id=UUID("00000000-0000-4000-8000-000000000001"),
        report_id=UUID("00000000-0000-4000-8000-000000000002"),
        download_url="https://commerce.example/d/transient-token-not-persisted",
        expires_at=kwargs.get("expires_at") or __import__("datetime").datetime.datetime(2026,8,27,tzinfo=__import__("datetime").datetime.timezone.utc),
    )


def test_postmark_wire_contract_is_server_owned_and_acceptance_is_validated():
    fake=FakePostmark()
    try:
        evidence=send(fake)
        assert evidence.message_id=="00000000-0000-4000-8000-000000000777"
        path,headers,body=fake.requests[0]
        assert path=="/email/withTemplate"
        assert headers["X-Postmark-Server-Token"]=="postmark-test-token-not-real"
        assert headers["Accept"]=="application/json"
        assert body["From"]=="reports@sitescore.example"
        assert body["To"]=="customer@example.com"
        assert body["TemplateAlias"]=="sitescore-report-v1"
        assert body["MessageStream"]=="outbound"
        assert body["TemplateModel"]["secure_download_url"].startswith("https://commerce.example/d/")
        assert body["TemplateModel"]["expires_in_days"]==7
    finally: fake.close()


@pytest.mark.parametrize("payload,code",[
    ({"To":"customer@example.com","SubmittedAt":"2026-08-20T00:15:30Z","MessageID":"00000000-0000-4000-8000-000000000777","ErrorCode":10},"postmark_error_10"),
    ({"To":"customer@example.com","SubmittedAt":"2026-08-20T00:15:30Z","MessageID":"","ErrorCode":0},"postmark_message_id_missing"),
    ({"To":"customer@example.com","SubmittedAt":"2026-08-20T00:15:30Z","MessageID":"not-a-uuid","ErrorCode":0},"postmark_message_id_invalid"),
    ({"To":"other@example.com","SubmittedAt":"2026-08-20T00:15:30Z","MessageID":"00000000-0000-4000-8000-000000000777","ErrorCode":0},"postmark_recipient_mismatch"),
    ({"To":"customer@example.com","SubmittedAt":"not-time","MessageID":"00000000-0000-4000-8000-000000000777","ErrorCode":0},"postmark_submitted_at_invalid"),
])
def test_postmark_http_200_is_not_enough(payload,code):
    fake=FakePostmark(payload=payload)
    try:
        with pytest.raises(PostmarkRejected) as exc: send(fake)
        assert exc.value.code==code
    finally: fake.close()


def test_postmark_non_200_and_timeout_are_not_fabricated_acceptance():
    fake=FakePostmark(status=503,payload={"ErrorCode":500,"Message":"no"})
    try:
        with pytest.raises(PostmarkRejected) as exc: send(fake)
        assert exc.value.retryable is True
    finally: fake.close()
    slow=FakePostmark(delay=.2)
    try:
        gateway=PostmarkGateway(settings(postmark_timeout_seconds=.05),endpoint=slow.endpoint)
        with pytest.raises(PostmarkUncertain):
            gateway.send(recipient="customer@example.com",order_id=uuid4(),report_id=uuid4(),download_url="https://commerce.example/d/x",expires_at=__import__("datetime").datetime.datetime.now(__import__("datetime").datetime.timezone.utc))
    finally: slow.close()


def test_official_postmark_endpoint_is_exact_template_send_endpoint():
    assert POSTMARK_ENDPOINT == "https://api.postmarkapp.com/email/withTemplate"


def test_sitescore_report_and_content_verification_fail_closed(monkeypatch):
    report_id=uuid4(); analysis_id=uuid4(); payload=b"%PDF-1.7\nverified\n%%EOF\n"; digest=hashlib.sha256(payload).hexdigest()
    resource={"report_id":str(report_id),"analysis_id":str(analysis_id),"state":"ready","content_sha256":digest,"mime_type":"application/pdf","filename":"report.pdf","byte_length":len(payload)}
    calls=[]
    def get(url,headers,timeout):
        calls.append((url,headers.copy()))
        if url.endswith("/content"):
            return httpx.Response(200,headers={"Content-Type":"application/pdf","Content-SHA256":digest,"Content-Length":str(len(payload))},content=payload)
        return httpx.Response(200,json=resource)
    monkeypatch.setattr(httpx,"get",get)
    gateway=SiteScoreDeliveryGateway(settings())
    evidence=gateway.get_report(base_url="https://sitescore.example",report_id=report_id,analysis_id=analysis_id)
    content=gateway.get_content(base_url="https://sitescore.example",evidence=evidence)
    assert content.content==payload and content.content_sha256==digest
    assert all(call[1]["Authorization"].startswith("Bearer ssk1_") for call in calls)

    bad=dict(resource,analysis_id=str(uuid4()))
    monkeypatch.setattr(httpx,"get",lambda *a,**k:httpx.Response(200,json=bad))
    with pytest.raises(DeliveryUpstreamUnavailable): gateway.get_report(base_url="https://sitescore.example",report_id=report_id,analysis_id=analysis_id)


@pytest.mark.parametrize("header_hash,mime,content",[
    ("0"*64,"application/pdf",b"%PDF-1.7\nverified\n%%EOF\n"),
    (None,"application/pdf",b"%PDF-1.7\nverified\n%%EOF\n"),
    ("MATCH","text/plain",b"%PDF-1.7\nverified\n%%EOF\n"),
    ("MATCH","application/pdf",b"not-a-pdf"),
])
def test_sitescore_content_mime_hash_and_pdf_integrity_are_mandatory(monkeypatch,header_hash,mime,content):
    report_id=uuid4(); analysis_id=uuid4(); expected=b"%PDF-1.7\nexpected\n%%EOF\n"; digest=hashlib.sha256(expected).hexdigest()
    from sitescore_commerce.delivery import ReportResourceEvidence
    evidence=ReportResourceEvidence(report_id,analysis_id,"ready",digest,"application/pdf","report.pdf",len(expected))
    headers={"Content-Type":mime,"Content-Length":str(len(content))}
    if header_hash is not None: headers["Content-SHA256"]=digest if header_hash=="MATCH" else header_hash
    monkeypatch.setattr(httpx,"get",lambda *a,**k:httpx.Response(200,headers=headers,content=content))
    with pytest.raises(DeliveryUpstreamUnavailable): SiteScoreDeliveryGateway(settings()).get_content(base_url="https://sitescore.example",evidence=evidence)
