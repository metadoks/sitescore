from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from conftest import valid_order
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import (
    CommerceStore,
    EventIdentityConflict,
    OrderRow,
    OutboxEventRow,
    PaymentPollReceiptRow,
    RecoveryFindingRow,
    RecoveryStateRow,
    StripeEventInboxRow,
    utcnow,
)
from sitescore_commerce.recovery import RecoveryIngressResult, RecoveryRuntimeSettings, RecoveryTransportResult
from sitescore_commerce.recovery_lineage import LineageRecoveryService
from sitescore_commerce.settings import STRIPE_API_VERSION, Settings
from sitescore_commerce.webhook import StripeEventEnvelope

DATABASE_URL = os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")
ROOT = Path(__file__).resolve().parents[1]


def _cfg():
    c = Config(str(ROOT / "alembic.ini"))
    c.set_main_option("script_location", str(ROOT / "alembic"))
    return c


def _reset():
    command.upgrade(_cfg(), "head")
    engine = sa.create_engine(DATABASE_URL)
    with engine.begin() as conn:
        for table in (
            "recovery_findings",
            "outbox_replay_audit",
            "payment_poll_receipts",
            "recovery_state",
            "recovery_runs",
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


def _order(store: CommerceStore):
    request = OrderCreateRequest.model_validate(valid_order())
    oid = uuid4(); sid = f"cs_test_{oid.hex}"
    store.get_or_create_order(
        candidate_order_id=oid,
        key_digest=(uuid4().hex + uuid4().hex),
        request=request,
        catalog_version="v1",
        price_id="price_1234567890",
        quantity=1,
        operation_version=CHECKOUT_OPERATION_VERSION,
        checkout_success_url=f"https://a.example/success?order_id={oid}&session_id={{CHECKOUT_SESSION_ID}}",
        checkout_cancel_url=f"https://a.example/cancel?order_id={oid}",
    )
    store.bind_checkout(order_id=oid, stripe_session_id=sid, checkout_url=f"https://checkout.stripe.com/c/pay/{sid}", expires_at=None)
    with store.session_factory.begin() as session:
        row = session.get(OrderRow, oid); row.updated_at = utcnow() - timedelta(hours=1)
    return oid, sid


def _event(oid, sid, *, event_id="evt_lineage"):
    return StripeEventEnvelope(
        event_id,
        "checkout.session.completed",
        STRIPE_API_VERSION,
        False,
        datetime(2026, 8, 20, tzinfo=timezone.utc),
        sid,
        str(oid),
    )


def test_verified_event_persists_candidate_order_id_as_duplicate_identity_material():
    _reset(); store = CommerceStore(DATABASE_URL); oid, sid = _order(store)
    original = _event(oid, sid)
    store.record_stripe_event(event=original, raw_body_sha256=hashlib.sha256(b"original").hexdigest())
    with store.session_factory() as session:
        row = session.get(StripeEventInboxRow, original.event_id)
        assert row.candidate_order_id == str(oid)
    conflicting = StripeEventEnvelope(
        original.event_id,
        original.event_type,
        original.api_version,
        original.livemode,
        original.created_at,
        original.checkout_session_id,
        str(uuid4()),
    )
    with pytest.raises(EventIdentityConflict):
        store.record_stripe_event(event=conflicting, raw_body_sha256=hashlib.sha256(b"conflict").hexdigest())
    with store.session_factory() as session:
        row = session.get(StripeEventInboxRow, original.event_id)
        assert row.candidate_order_id == str(oid)
        assert row.attempt_count == 1


class NeverGateway:
    def __init__(self): self.calls = []
    def retrieve(self, session_id):
        self.calls.append(session_id)
        raise AssertionError("provider must not be called after stored Event lineage mismatch")


class NeverN8n:
    def send(self, event):
        raise AssertionError("n8n must not be called for Stripe lineage attention")


def test_stale_received_event_candidate_mismatch_is_attention_before_provider_io():
    _reset(); store = CommerceStore(DATABASE_URL); oid, sid = _order(store)
    event = _event(oid, sid, event_id="evt_lineage_mismatch")
    store.record_stripe_event(event=event, raw_body_sha256=hashlib.sha256(b"signed").hexdigest())
    with store.session_factory.begin() as session:
        row = session.get(StripeEventInboxRow, event.event_id)
        row.received_at = utcnow() - timedelta(minutes=10)
        row.candidate_order_id = str(uuid4())
    gateway = NeverGateway()
    svc = LineageRecoveryService(
        settings=Settings(DATABASE_URL, "provider-test-value", "price_1234567890", "https://a.example/success", "https://a.example/cancel", "test", "signing-test-value", False),
        runtime=RecoveryRuntimeSettings(batch_size=10, stale_inbox_seconds=1, pending_payment_poll_seconds=1, published_replay_seconds=1, lease_seconds=30, maximum_backoff_seconds=60),
        commerce_store=store,
        evidence_gateway=gateway,
        n8n=NeverN8n(),
    )
    result = svc.run_once()
    assert result.claimed == 1 and result.attention == 1 and result.reconciled == 0
    assert gateway.calls == []
    with store.session_factory() as session:
        order = session.get(OrderRow, oid)
        inbox = session.get(StripeEventInboxRow, event.event_id)
        findings = session.execute(select(RecoveryFindingRow).where(RecoveryFindingRow.order_id == oid)).scalars().all()
        state = session.get(RecoveryStateRow, oid)
        assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
        assert session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalars().all() == []
        assert session.execute(select(PaymentPollReceiptRow).where(PaymentPollReceiptRow.order_id == oid)).scalars().all() == []
        assert inbox.processing_state == "attention_required" and inbox.failure_code == "event_order_correlation_invalid"
        assert [x.code for x in findings] == ["event_order_correlation_invalid"]
        assert state.last_outcome == "attention" and state.last_error_code == "event_order_correlation_invalid"
