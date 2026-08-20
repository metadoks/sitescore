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
from sqlalchemy.exc import IntegrityError

from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import (
    CheckoutSessionRow,
    CommerceStore,
    OrderRow,
    OutboxEventRow,
    OutboxReplayAuditRow,
    PaymentPollReceiptRow,
    RecoveryFindingRow,
    StripeEventInboxRow,
    utcnow,
)
from sitescore_commerce.recovery import RecoveryIngressResult, RecoveryTransportResult
from sitescore_commerce.recovery_lineage import LineageRecoveryService
from sitescore_commerce.settings import STRIPE_API_VERSION

from conftest import valid_order
from test_recovery_postgres import (
    FixedGateway,
    FixedN8n,
    evidence,
    make_order,
    runtime,
    settings,
    transition_paid_by_poll,
)

DATABASE_URL = os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")
ROOT = Path(__file__).resolve().parents[1]


def _cfg():
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return cfg


def _lineage(store: CommerceStore, gateway, n8n) -> LineageRecoveryService:
    return LineageRecoveryService(
        settings=settings(),
        runtime=runtime(),
        commerce_store=store,
        evidence_gateway=gateway,
        n8n=n8n,
    )


def _clean_0004() -> None:
    command.upgrade(_cfg(), "head")
    command.downgrade(_cfg(), "0004_delivery_email")
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


def _legacy_order() -> tuple[CommerceStore, object, str]:
    store = CommerceStore(DATABASE_URL)
    oid, sid = make_order(store)
    return store, oid, sid


def _insert_legacy_received(*, event_id: str, event_type: str, session_id: str | None) -> None:
    engine = sa.create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                INSERT INTO commerce.stripe_event_inbox (
                    stripe_event_id, stripe_event_type, stripe_object_id,
                    event_api_version, livemode, event_created_at,
                    raw_body_sha256, processing_state, failure_code,
                    received_at, processed_at, attempt_count
                ) VALUES (
                    :event_id, :event_type, :session_id,
                    :api_version, false, :event_created_at,
                    :raw_hash, 'received', NULL,
                    :received_at, NULL, 1
                )
                """
            ),
            {
                "event_id": event_id,
                "event_type": event_type,
                "session_id": session_id,
                "api_version": STRIPE_API_VERSION,
                "event_created_at": datetime(2026, 8, 20, tzinfo=timezone.utc),
                "raw_hash": hashlib.sha256(event_id.encode("utf-8")).hexdigest(),
                "received_at": utcnow() - timedelta(minutes=10),
            },
        )


def _state(store: CommerceStore, oid, event_id: str):
    with store.session_factory() as session:
        order = session.get(OrderRow, oid)
        checkout = session.get(CheckoutSessionRow, oid)
        inbox = session.get(StripeEventInboxRow, event_id)
        outboxes = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalars().all()
        receipts = session.execute(select(PaymentPollReceiptRow).where(PaymentPollReceiptRow.order_id == oid)).scalars().all()
        findings = session.execute(select(RecoveryFindingRow).where(RecoveryFindingRow.order_id == oid)).scalars().all()
        return order, checkout, inbox, outboxes, receipts, findings


@pytest.mark.parametrize(
    "event_type,status,payment_status,payment_intent,target_order,target_payment",
    [
        ("checkout.session.completed", "complete", "paid", "pi_legacy_paid", "paid", "paid"),
        ("checkout.session.expired", "expired", "unpaid", None, "expired", "expired"),
    ],
)
def test_populated_0004_legacy_received_event_survives_upgrade_and_resumes_original_identity(
    event_type,
    status,
    payment_status,
    payment_intent,
    target_order,
    target_payment,
):
    _clean_0004()
    store, oid, sid = _legacy_order()
    event_id = f"evt_legacy_{uuid4().hex}"
    _insert_legacy_received(event_id=event_id, event_type=event_type, session_id=sid)

    # This is the data-preserving production upgrade under review. The new
    # candidate_order_id column did not exist when the event was inserted.
    command.upgrade(_cfg(), "0005_recovery_reconciliation")

    evd = evidence(
        oid,
        sid,
        status=status,
        payment_status=payment_status,
        payment_intent_id=payment_intent,
    )
    gateway = FixedGateway({sid: evd})
    n8n = FixedN8n()
    result = _lineage(store, gateway, n8n).run_once()

    order, checkout, inbox, outboxes, receipts, findings = _state(store, oid, event_id)
    assert result.reconciled == 1 and result.attention == 0
    assert gateway.calls == [sid] and n8n.calls == []
    assert (order.order_state, order.payment_state) == (target_order, target_payment)
    assert inbox.processing_state == "processed" and inbox.failure_code is None
    assert inbox.stripe_event_id == event_id and inbox.candidate_order_id is None
    assert checkout.last_reconciliation_event_id == event_id
    assert receipts == [] and findings == []
    if target_order == "paid":
        assert len(outboxes) == 1 and outboxes[0].outbox_type == "order.paid.v1"
    else:
        assert outboxes == []


def test_populated_0004_orphan_legacy_session_is_quarantined_during_0005_upgrade_without_synthetic_lineage():
    _clean_0004()
    store, oid, _ = _legacy_order()
    event_id = f"evt_legacy_orphan_{uuid4().hex}"
    _insert_legacy_received(event_id=event_id, event_type="checkout.session.completed", session_id="cs_test_no_local_binding")

    command.upgrade(_cfg(), "0005_recovery_reconciliation")

    with store.session_factory() as session:
        order = session.get(OrderRow, oid)
        inbox = session.get(StripeEventInboxRow, event_id)
        assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
        assert inbox.candidate_order_id is None
        assert inbox.processing_state == "attention_required"
        assert inbox.failure_code == "legacy_event_session_correlation_invalid"
        assert inbox.processed_at is not None
        assert session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalars().all() == []
        assert session.execute(select(PaymentPollReceiptRow).where(PaymentPollReceiptRow.order_id == oid)).scalars().all() == []


def test_legacy_checkout_session_correlation_is_structurally_unique_in_0004():
    _clean_0004()
    store, oid_a, sid = _legacy_order()
    request = OrderCreateRequest.model_validate(valid_order())
    oid_b = uuid4()
    store.get_or_create_order(
        candidate_order_id=oid_b,
        key_digest=uuid4().hex + uuid4().hex,
        request=request,
        catalog_version="v1",
        price_id="price_1234567890",
        quantity=1,
        operation_version="stripe_checkout_session_v1",
        checkout_success_url=f"https://a.example/success?order_id={oid_b}&session_id={{CHECKOUT_SESSION_ID}}",
        checkout_cancel_url=f"https://a.example/cancel?order_id={oid_b}",
    )
    with pytest.raises((IntegrityError, Exception)) as exc_info:
        store.bind_checkout(
            order_id=oid_b,
            stripe_session_id=sid,
            checkout_url=f"https://checkout.stripe.com/c/pay/{sid}",
            expires_at=None,
        )
    assert exc_info.value is not None
    command.upgrade(_cfg(), "0005_recovery_reconciliation")
    assert oid_a != oid_b


def _prepare_paid(*, published: bool):
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
    store = CommerceStore(DATABASE_URL)
    oid, sid = make_order(store)
    transition_paid_by_poll(store, oid, sid)
    historical = utcnow() - timedelta(hours=1)
    with store.session_factory.begin() as session:
        order = session.get(OrderRow, oid)
        outbox = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalar_one()
        if published:
            order.updated_at = historical
            outbox.published_at = historical
        return store, oid, sid, outbox.outbox_id, outbox.created_at, historical if published else None


def _corrupt_checkout(store: CommerceStore, oid, mutation: str) -> None:
    with store.session_factory.begin() as session:
        checkout = session.get(CheckoutSessionRow, oid)
        if mutation == "missing_payment_intent":
            checkout.stripe_payment_intent_id = None
        elif mutation == "session_not_complete":
            checkout.stripe_session_status = "open"
        elif mutation == "payment_not_paid":
            checkout.stripe_payment_status = "unpaid"
        elif mutation == "livemode_null":
            checkout.stripe_livemode = None
        elif mutation == "livemode_mismatch":
            checkout.stripe_livemode = True
        elif mutation == "session_identity_conflict":
            checkout.stripe_checkout_session_id = f"cs_test_corrupt_{uuid4().hex}"
        elif mutation == "reconciliation_missing":
            checkout.reconciled_at = None
        else:
            raise AssertionError(mutation)


@pytest.mark.parametrize("published", [False, True], ids=["unpublished", "published"])
@pytest.mark.parametrize(
    "mutation",
    [
        "missing_payment_intent",
        "session_not_complete",
        "payment_not_paid",
        "livemode_null",
        "livemode_mismatch",
        "session_identity_conflict",
        "reconciliation_missing",
    ],
)
def test_corrupt_paid_durable_stripe_binding_fails_closed_before_any_n8n_io(mutation, published):
    store, oid, sid, outbox_id, occurred_at, historical = _prepare_paid(published=published)
    _corrupt_checkout(store, oid, mutation)
    gateway = FixedGateway({sid: evidence(oid, sid)})
    n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])

    result = _lineage(store, gateway, n8n).run_once()

    assert result.attention == 1 and result.published == 0 and result.replayed == 0
    assert gateway.calls == [] and n8n.calls == []
    with store.session_factory() as session:
        order = session.get(OrderRow, oid)
        outboxes = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalars().all()
        findings = session.execute(select(RecoveryFindingRow).where(RecoveryFindingRow.order_id == oid)).scalars().all()
        receipts = session.execute(select(PaymentPollReceiptRow).where(PaymentPollReceiptRow.order_id == oid)).scalars().all()
        audits = session.execute(select(OutboxReplayAuditRow).where(OutboxReplayAuditRow.order_id == oid)).scalars().all()
        assert (order.order_state, order.payment_state, order.fulfillment_state) == ("paid", "paid", "not_started")
        assert len(outboxes) == 1 and outboxes[0].outbox_id == outbox_id and outboxes[0].created_at == occurred_at
        assert len(receipts) == 1 and receipts[0].transition_target == "paid"
        assert len(findings) == 1 and findings[0].code.startswith("paid_")
        assert audits == []
        if published:
            assert outboxes[0].published_at == historical
        else:
            assert outboxes[0].published_at is None


@pytest.mark.parametrize("published", [False, True], ids=["publish", "replay"])
def test_valid_paid_durable_binding_still_uses_exact_original_outbox_identity(published):
    store, oid, sid, outbox_id, occurred_at, historical = _prepare_paid(published=published)
    gateway = FixedGateway({sid: evidence(oid, sid)})
    n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])

    result = _lineage(store, gateway, n8n).run_once()

    assert gateway.calls == [] and len(n8n.calls) == 1
    sent = n8n.calls[0]
    assert sent.event_id == outbox_id and sent.order_id == oid and sent.occurred_at == occurred_at
    with store.session_factory() as session:
        outbox = session.get(OutboxEventRow, outbox_id)
        findings = session.execute(select(RecoveryFindingRow).where(RecoveryFindingRow.order_id == oid)).scalars().all()
        assert findings == []
        if published:
            assert result.replayed == 1 and outbox.published_at == historical
        else:
            assert result.published == 1 and outbox.published_at is not None
