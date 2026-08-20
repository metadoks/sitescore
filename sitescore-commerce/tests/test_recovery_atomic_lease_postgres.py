from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from sitescore_commerce.db import OutboxEventRow, RecoveryStateRow, StripeEventInboxRow, utcnow
from sitescore_commerce.recovery import RecoveryStore, canonical_payment_evidence_hash
from sitescore_commerce.recovery_atomic import (
    apply_event_reconciliation_with_lease,
    apply_poll_reconciliation_with_lease,
    mark_outbox_published_with_lease,
)
from sitescore_commerce.settings import STRIPE_API_VERSION
from sitescore_commerce.webhook import StripeEventEnvelope

from test_recovery_postgres import (
    CommerceStore,
    DATABASE_URL,
    evidence,
    make_order,
    reset_db,
    state,
    transition_paid_by_poll,
)

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")


def _claim(store: CommerceStore, oid):
    recovery_store = RecoveryStore(store)
    now = utcnow()
    recovery_store.seed_candidates(now=now, limit=10)
    claim = recovery_store.claim_batch(now=now, batch_size=10, lease_seconds=120)
    return next(item for item in claim if item.order_id == oid)


def _replace_lease(store: CommerceStore, oid):
    replacement = uuid4()
    with store.session_factory.begin() as session:
        row = session.get(RecoveryStateRow, oid)
        row.lease_token = replacement
        row.lease_expires_at = utcnow() + timedelta(minutes=5)
    return replacement


def test_stale_poll_worker_cannot_apply_payment_truth_receipt_or_paid_outbox():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    claim = _claim(store, oid); replacement = _replace_lease(store, oid)
    evd = evidence(oid, sid)

    assert apply_poll_reconciliation_with_lease(
        store,
        order_id=oid,
        lease_token=claim.lease_token,
        evidence=evd,
        target="paid",
        evidence_sha256=canonical_payment_evidence_hash(evd),
        observed_at=utcnow(),
    ) == ("lease_lost", None)

    order, checkout, outboxes, receipts, inbox, findings, rs = state(store, oid)
    assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
    assert checkout.stripe_payment_status is None and checkout.last_reconciliation_event_id is None
    assert outboxes == [] and receipts == [] and inbox == [] and findings == []
    assert rs.lease_token == replacement


def test_stale_real_event_worker_cannot_process_inbox_or_apply_payment_truth():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    event = StripeEventEnvelope(
        "evt_atomic_lease_fence",
        "checkout.session.completed",
        STRIPE_API_VERSION,
        False,
        datetime(2026, 8, 20, tzinfo=timezone.utc),
        sid,
        str(oid),
    )
    store.record_stripe_event(event=event, raw_body_sha256=hashlib.sha256(b"atomic-event").hexdigest())
    claim = _claim(store, oid); replacement = _replace_lease(store, oid)

    assert apply_event_reconciliation_with_lease(
        store,
        order_id=oid,
        lease_token=claim.lease_token,
        event_id=event.event_id,
        evidence=evidence(oid, sid),
        target="paid",
    ) == ("lease_lost", None)

    order, checkout, outboxes, receipts, inbox, findings, rs = state(store, oid)
    assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
    assert checkout.stripe_payment_status is None and checkout.last_reconciliation_event_id is None
    assert outboxes == [] and receipts == [] and findings == []
    assert len(inbox) == 1 and inbox[0].processing_state == "received" and inbox[0].processed_at is None
    assert rs.lease_token == replacement


def test_stale_worker_cannot_mark_unpublished_paid_outbox_published():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    transition_paid_by_poll(store, oid, sid)
    claim = _claim(store, oid); replacement = _replace_lease(store, oid)
    with store.session_factory() as session:
        outbox = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalar_one()
        event_id = outbox.outbox_id
        assert outbox.published_at is None

    assert mark_outbox_published_with_lease(
        store,
        order_id=oid,
        lease_token=claim.lease_token,
        event_id=event_id,
        published_at=utcnow(),
    ) is False

    with store.session_factory() as session:
        outbox = session.get(OutboxEventRow, event_id)
        rs = session.get(RecoveryStateRow, oid)
        assert outbox.published_at is None
        assert rs.lease_token == replacement
