from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from conftest import valid_order
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import CheckoutSessionRow, CommerceStore, OrderRow
from sitescore_commerce.delivery import (
    DeliveryAttemptRow,
    DeliveryGrantRow,
    DeliveryService,
    DeliveryStore,
    DownloadPayload,
    PostmarkGateway,
    ReportResourceEvidence,
)
from sitescore_commerce.fulfillment import AnalysisEvidence, FulfillmentStore, ReportEvidence
from sitescore_commerce.settings import Settings

DATABASE_URL = os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")
ROOT = Path(__file__).resolve().parents[1]


def cfg() -> Config:
    value = Config(str(ROOT / "alembic.ini"))
    value.set_main_option("script_location", str(ROOT / "alembic"))
    return value


def clean() -> None:
    command.upgrade(cfg(), "head")
    engine = sa.create_engine(DATABASE_URL)
    with engine.begin() as conn:
        for table in (
            "delivery_attempts",
            "delivery_grants",
            "refund_operations",
            "refund_eligibility",
            "fulfillment_bindings",
            "outbox_events",
            "stripe_event_inbox",
            "checkout_sessions",
            "order_idempotency",
            "orders",
        ):
            conn.execute(sa.text(f"DELETE FROM commerce.{table}"))


@pytest.fixture(autouse=True)
def cleanup():
    clean()
    yield
    clean()


def settings() -> Settings:
    return Settings(
        database_url=DATABASE_URL,
        stripe_secret_key="sk_test_not-real",
        stripe_price_location_report_v1="price_1234567890",
        success_url_base="https://app.example/success",
        cancel_url_base="https://app.example/cancel",
        environment="test",
        stripe_webhook_secret="test-signing-secret",
        stripe_expected_livemode=False,
        sitescore_api_base_url="https://sitescore.example",
        sitescore_api_service_key="ssk1_key.secret-secret-secret-secret-0123456789",
        sitescore_api_target_id="target-v1",
        sitescore_api_timeout_seconds=10,
        commerce_automation_api_key="automation-key-test-0123456789",
        postmark_server_token="postmark-test-token-not-real",
        postmark_from_email="reports@sitescore.example",
        postmark_template_alias="sitescore-report-v1",
        postmark_timeout_seconds=10,
        commerce_public_base_url="https://commerce.example",
    )


def ready_order(commerce: CommerceStore):
    request = OrderCreateRequest.model_validate(valid_order())
    candidate = uuid4()
    order_id = commerce.get_or_create_order(
        candidate_order_id=candidate,
        key_digest=uuid4().hex + uuid4().hex,
        request=request,
        catalog_version="v1",
        price_id="price_1234567890",
        quantity=1,
        operation_version=CHECKOUT_OPERATION_VERSION,
        checkout_success_url=f"https://app.example/success?order_id={candidate}&session_id={{CHECKOUT_SESSION_ID}}",
        checkout_cancel_url=f"https://app.example/cancel?order_id={candidate}",
    )
    with commerce.session_factory.begin() as session:
        order = session.get(OrderRow, order_id)
        checkout = session.get(CheckoutSessionRow, order_id)
        order.order_state = "paid"
        order.payment_state = "paid"
        order.fulfillment_state = "not_started"
        checkout.stripe_payment_intent_id = f"pi_{order_id.hex}"
        checkout.stripe_livemode = False
        recipient = order.customer_email
    fulfillment = FulfillmentStore(commerce)
    fulfillment.prepare_analysis_operation(order_id=order_id, settings=settings())
    analysis_id = uuid4()
    report_id = uuid4()
    fulfillment.bind_analysis(order_id=order_id, evidence=AnalysisEvidence(analysis_id, "completed"))
    fulfillment.bind_report(order_id=order_id, evidence=ReportEvidence(report_id, analysis_id, "ready"))
    return order_id, analysis_id, report_id, recipient


class FixedSiteScore:
    def __init__(self, analysis_id: UUID, report_id: UUID):
        self.analysis_id = analysis_id
        self.report_id = report_id
        self.payload = b"%PDF-1.7\npostmark uncertainty\n%%EOF\n"
        self.digest = hashlib.sha256(self.payload).hexdigest()

    def get_report(self, *, base_url, report_id, analysis_id):
        assert report_id == self.report_id and analysis_id == self.analysis_id
        return ReportResourceEvidence(
            self.report_id,
            self.analysis_id,
            "ready",
            self.digest,
            "application/pdf",
            "report.pdf",
            len(self.payload),
        )

    def get_content(self, *, base_url, evidence):
        assert evidence.report_id == self.report_id and evidence.analysis_id == self.analysis_id
        return DownloadPayload(self.payload, "report.pdf", self.digest)


class FakePostmarkHttp:
    def __init__(self, responses: list[tuple[int, bytes]]):
        self.responses = list(responses)
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                outer.requests.append(json.loads(body))
                status, raw = outer.responses.pop(0)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def endpoint(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/email/withTemplate"

    def close(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()


def accepted_body(recipient: str, suffix: int = 77) -> bytes:
    return json.dumps(
        {
            "To": recipient,
            "SubmittedAt": "2026-08-20T06:15:30Z",
            "MessageID": str(UUID(int=suffix)),
            "ErrorCode": 0,
            "Message": "OK",
        }
    ).encode()


def test_raw_truncated_http_200_is_durable_uncertain_then_fresh_replay_converges(monkeypatch):
    commerce = CommerceStore(DATABASE_URL)
    order_id, analysis_id, report_id, recipient = ready_order(commerce)
    fake = FakePostmarkHttp(
        [
            (200, b'{"ErrorCode":0,"MessageID":"00000000-0000-4000-8000-000000000077"'),
            (200, accepted_body(recipient, 78)),
        ]
    )
    try:
        site = FixedSiteScore(analysis_id, report_id)
        service = DeliveryService(settings(), DeliveryStore(commerce), site, PostmarkGateway(settings(), endpoint=fake.endpoint))
        tokens = iter(["U" * 43, "V" * 43])
        monkeypatch.setattr("sitescore_commerce.delivery.generate_delivery_token", lambda: next(tokens))

        service.deliver(order_id)
        with commerce.session_factory() as session:
            order = session.get(OrderRow, order_id)
            attempts = session.query(DeliveryAttemptRow).filter_by(order_id=order_id).order_by(DeliveryAttemptRow.attempt_number).all()
            grants = session.query(DeliveryGrantRow).filter_by(order_id=order_id).all()
            assert (order.order_state, order.payment_state, order.fulfillment_state) == ("fulfillment_in_progress", "paid", "delivery_pending")
            assert len(attempts) == 1 and attempts[0].status == "provider_uncertain"
            assert attempts[0].failure_code == "postmark_malformed_response"
            assert attempts[0].provider_message_id is None
            assert len(grants) == 1 and grants[0].revoked_at is None
        assert FulfillmentStore(commerce).get_status(order_id).next_action == "delivery"

        service.deliver(order_id)
        with commerce.session_factory() as session:
            order = session.get(OrderRow, order_id)
            attempts = session.query(DeliveryAttemptRow).filter_by(order_id=order_id).order_by(DeliveryAttemptRow.attempt_number).all()
            grants = session.query(DeliveryGrantRow).filter_by(order_id=order_id).order_by(DeliveryGrantRow.issued_at).all()
            assert (order.order_state, order.payment_state, order.fulfillment_state) == ("fulfilled", "paid", "completed")
            assert [item.status for item in attempts] == ["provider_uncertain", "provider_accepted"]
            assert attempts[1].provider_message_id == str(UUID(int=78))
            assert len(grants) == 2 and len({item.token_digest for item in grants}) == 2
            assert all(item.revoked_at is None for item in grants)
            assert {item.report_id for item in grants} == {report_id}
        assert service.download("U" * 43).content == site.payload
        assert service.download("V" * 43).content == site.payload
        assert len(fake.requests) == 2
    finally:
        fake.close()


def test_explicit_nonzero_error_code_remains_durable_provider_rejection(monkeypatch):
    commerce = CommerceStore(DATABASE_URL)
    order_id, analysis_id, report_id, recipient = ready_order(commerce)
    body = json.dumps(
        {
            "To": recipient,
            "SubmittedAt": "2026-08-20T06:15:30Z",
            "MessageID": str(UUID(int=79)),
            "ErrorCode": 300,
            "Message": "Invalid email request",
        }
    ).encode()
    fake = FakePostmarkHttp([(200, body)])
    try:
        service = DeliveryService(
            settings(),
            DeliveryStore(commerce),
            FixedSiteScore(analysis_id, report_id),
            PostmarkGateway(settings(), endpoint=fake.endpoint),
        )
        monkeypatch.setattr("sitescore_commerce.delivery.generate_delivery_token", lambda: "W" * 43)
        service.deliver(order_id)
        with commerce.session_factory() as session:
            order = session.get(OrderRow, order_id)
            attempt = session.query(DeliveryAttemptRow).filter_by(order_id=order_id).one()
            assert attempt.status == "provider_rejected"
            assert attempt.failure_code == "postmark_error_300"
            assert attempt.provider_message_id is None
            assert (order.order_state, order.payment_state, order.fulfillment_state) == ("attention_required", "paid", "delivery_failed")
    finally:
        fake.close()
