from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from sitescore_commerce.db import OutboxEventRow, PersistenceUnavailable, RecoveryStateRow, utcnow
from sitescore_commerce.recovery import RecoveryIngressResult, RecoveryTransportResult
from sitescore_commerce.webhook import PaymentProviderUnavailable

from test_recovery_postgres import (
    CommerceStore,
    DATABASE_URL,
    FixedGateway,
    FixedN8n,
    evidence,
    make_order,
    recovery,
    reset_db,
    state,
    transition_paid_by_poll,
)

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")


class UnavailableStripe:
    def __init__(self): self.calls = []
    def retrieve(self, session_id):
        self.calls.append(session_id)
        raise PaymentProviderUnavailable("simulated provider outage with details that must not persist")


def test_stripe_outage_after_claim_keeps_payment_pending_and_persists_sanitized_backoff_only():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    gateway = UnavailableStripe(); result = recovery(store, gateway, FixedN8n()).run_once()
    assert result.claimed == 1 and result.deferred == 1 and gateway.calls == [sid]
    order, _, outboxes, receipts, inbox, findings, rs = state(store, oid)
    assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
    assert outboxes == [] and receipts == [] and inbox == [] and findings == []
    assert rs.consecutive_failures == 1 and rs.last_error_code == "stripe_provider_unavailable"
    assert "details" not in (rs.last_error_code or "")
    assert rs.next_attempt_at > utcnow()


def test_confirmed_n8n_side_effect_then_db_commit_failure_replays_same_event_identity_after_recovery():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    first_n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])
    first_service = recovery(store, FixedGateway({sid: evidence(oid, sid)}), first_n8n)

    def fail_publish(*args, **kwargs):
        raise PersistenceUnavailable("simulated commit loss after external acceptance")

    first_service.store.mark_outbox_published = fail_publish
    first = first_service.run_once()
    assert first.deferred == 1 and len(first_n8n.calls) == 1
    original_event = first_n8n.calls[0]
    with store.session_factory() as session:
        outbox = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalar_one()
        rs = session.get(RecoveryStateRow, oid)
        assert outbox.outbox_id == original_event.event_id and outbox.published_at is None
        assert rs.last_error_code == "recovery_persistence_unavailable"

    with store.session_factory.begin() as session:
        rs = session.get(RecoveryStateRow, oid)
        rs.next_attempt_at = utcnow() - timedelta(seconds=1)
        rs.lease_token = None; rs.lease_expires_at = None
    second_n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])
    second = recovery(store, FixedGateway({sid: evidence(oid, sid)}), second_n8n).run_once()
    assert second.published == 1 and second_n8n.calls == [original_event]
    with store.session_factory() as session:
        assert session.get(OutboxEventRow, original_event.event_id).published_at is not None
