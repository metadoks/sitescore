from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from sitescore_commerce.db import (
    OrderRow,
    OutboxEventRow,
    OutboxReplayAuditRow,
    PaymentPollReceiptRow,
    RecoveryStateRow,
    utcnow,
)
from sitescore_commerce.recovery import (
    RecoveryIngressResult,
    RecoveryStore,
    RecoveryTransportResult,
    canonical_payment_evidence_hash,
)

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


def _force_due(store: CommerceStore, oid):
    with store.session_factory.begin() as session:
        rs = session.get(RecoveryStateRow, oid)
        rs.next_attempt_at = utcnow() - timedelta(seconds=1)
        rs.lease_token = None
        rs.lease_expires_at = None


def test_expired_after_paid_contradiction_fails_closed_with_one_paid_receipt_and_outbox():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    paid = evidence(oid, sid)
    assert store.apply_poll_reconciliation(
        order_id=oid,
        evidence=paid,
        target="paid",
        evidence_sha256=canonical_payment_evidence_hash(paid),
        observed_at=utcnow(),
    ) == ("transitioned", None)
    expired = evidence(oid, sid, status="expired", payment_status="unpaid", payment_intent_id=None)
    assert store.apply_poll_reconciliation(
        order_id=oid,
        evidence=expired,
        target="expired",
        evidence_sha256=canonical_payment_evidence_hash(expired),
        observed_at=utcnow(),
    ) == ("attention", "late_expiration_after_paid")
    order, _, outboxes, receipts, inbox, findings, _ = state(store, oid)
    assert (order.order_state, order.payment_state) == ("paid", "paid")
    assert len(outboxes) == 1 and len(receipts) == 1 and receipts[0].transition_target == "paid"
    assert inbox == [] and findings == []


def test_two_server_poll_workers_converge_to_one_paid_transition_receipt_and_outbox():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); evd = evidence(oid, sid)

    def worker(_):
        local = CommerceStore(DATABASE_URL)
        return local.apply_poll_reconciliation(
            order_id=oid,
            evidence=evd,
            target="paid",
            evidence_sha256=canonical_payment_evidence_hash(evd),
            observed_at=utcnow(),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, range(2)))
    assert sorted(x[0] for x in outcomes) == ["already_terminal", "transitioned"]
    order, _, outboxes, receipts, inbox, findings, _ = state(store, oid)
    assert (order.order_state, order.payment_state) == ("paid", "paid")
    assert len(outboxes) == 1 and len(receipts) == 1
    assert inbox == [] and findings == []


def test_unpublished_response_loss_then_same_identity_retry_converges_to_published():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    uncertain = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.UNCERTAIN, failure_code="n8n_transport_uncertain")])
    first = recovery(store, FixedGateway({sid: evidence(oid, sid)}), uncertain).run_once()
    assert first.deferred == 1 and len(uncertain.calls) == 1
    first_event = uncertain.calls[0]
    _, _, outboxes, _, _, _, _ = state(store, oid)
    assert outboxes[0].published_at is None

    _force_due(store, oid)
    accepted = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])
    second = recovery(store, FixedGateway({sid: evidence(oid, sid)}), accepted).run_once()
    assert second.published == 1 and len(accepted.calls) == 1
    assert accepted.calls[0] == first_event
    _, _, outboxes, _, _, _, _ = state(store, oid)
    assert outboxes[0].outbox_id == first_event.event_id and outboxes[0].published_at is not None


def test_published_replay_response_loss_then_same_identity_replay_converges_without_rewriting_publication_history():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    historical = utcnow() - timedelta(hours=1)
    with store.session_factory.begin() as session:
        order = session.get(OrderRow, oid); order.updated_at = historical
        outbox = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalar_one()
        outbox.published_at = historical
        outbox_id = outbox.outbox_id; occurred_at = outbox.created_at

    uncertain = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.UNCERTAIN, failure_code="n8n_transport_uncertain")])
    first = recovery(store, FixedGateway({sid: evidence(oid, sid)}), uncertain).run_once()
    assert first.deferred == 1 and uncertain.calls[0].event_id == outbox_id and uncertain.calls[0].occurred_at == occurred_at
    _force_due(store, oid)
    with store.session_factory.begin() as session:
        session.get(OrderRow, oid).updated_at = historical
    accepted = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])
    second = recovery(store, FixedGateway({sid: evidence(oid, sid)}), accepted).run_once()
    assert second.replayed == 1 and accepted.calls[0] == uncertain.calls[0]
    with store.session_factory() as session:
        outbox = session.get(OutboxEventRow, outbox_id)
        audits = session.execute(select(OutboxReplayAuditRow).where(OutboxReplayAuditRow.order_id == oid).order_by(OutboxReplayAuditRow.attempted_at)).scalars().all()
        assert outbox.published_at == historical
        assert [x.result for x in audits] == ["uncertain", "accepted"]
        assert all(x.outbox_id == outbox_id for x in audits)


@pytest.mark.parametrize("transport", [RecoveryTransportResult.RETRYABLE_REJECTED])
@pytest.mark.parametrize("status,code", [(429, "n8n_http_429"), (503, "n8n_http_5xx")])
def test_429_and_5xx_are_durable_bounded_backoff_not_hot_loop(transport, status, code):
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    first_n8n = FixedN8n([RecoveryIngressResult(transport, http_status=status, failure_code=code)])
    first = recovery(store, FixedGateway({sid: evidence(oid, sid)}), first_n8n).run_once()
    assert first.deferred == 1
    with store.session_factory() as session:
        rs = session.get(RecoveryStateRow, oid); first_next = rs.next_attempt_at
        assert rs.consecutive_failures == 1 and rs.last_error_code == code
        assert session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalar_one().published_at is None
    _force_due(store, oid)
    second_n8n = FixedN8n([RecoveryIngressResult(transport, http_status=status, failure_code=code)])
    recovery(store, FixedGateway({sid: evidence(oid, sid)}), second_n8n).run_once()
    with store.session_factory() as session:
        rs = session.get(RecoveryStateRow, oid)
        assert rs.consecutive_failures == 2 and rs.next_attempt_at > first_next
        assert (rs.next_attempt_at - rs.last_checked_at).total_seconds() >= 55


def test_paid_provider_response_after_lease_replacement_cannot_transition_or_write_poll_receipt():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    rstore = RecoveryStore(store); now = utcnow(); rstore.seed_candidates(now=now, limit=10)
    claim = rstore.claim_batch(now=now, batch_size=1, lease_seconds=30)[0]

    def replace_lease():
        with store.session_factory.begin() as session:
            row = session.get(RecoveryStateRow, oid)
            row.lease_token = uuid4(); row.lease_expires_at = utcnow() + timedelta(minutes=5)

    svc = recovery(store, FixedGateway({sid: evidence(oid, sid)}, before_return=replace_lease), FixedN8n())
    outcome = svc._process_claim(claim=claim, run_id=uuid4(), now=utcnow())
    assert outcome == "lease_lost"
    order, _, outboxes, receipts, inbox, findings, rs = state(store, oid)
    assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
    assert outboxes == [] and receipts == [] and inbox == [] and findings == []
    assert rs.lease_token != claim.lease_token


@pytest.mark.parametrize(
    "order_state,payment_state,fulfillment_state",
    [
        ("fulfilled", "paid", "completed"),
        ("refunded", "refunded", "analysis_failed"),
        ("expired", "expired", "not_started"),
        ("attention_required", "paid", "analysis_failed"),
    ],
)
def test_terminal_or_attention_orders_age_out_without_provider_or_n8n_io(order_state, payment_state, fulfillment_state):
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    with store.session_factory.begin() as session:
        order = session.get(OrderRow, oid)
        order.order_state = order_state; order.payment_state = payment_state; order.fulfillment_state = fulfillment_state
        order.updated_at = utcnow() - timedelta(days=1)
    gateway = FixedGateway({sid: evidence(oid, sid)})
    n8n = FixedN8n()
    result = recovery(store, gateway, n8n).run_once()
    assert result.claimed == 0
    assert gateway.calls == [] and n8n.calls == []
