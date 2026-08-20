from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from conftest import valid_order
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import (
    CheckoutSessionRow,
    CommerceStore,
    OrderRow,
    OutboxEventRow,
    OutboxReplayAuditRow,
    PaymentPollReceiptRow,
    RecoveryFindingRow,
    RecoveryRunRow,
    RecoveryStateRow,
    StripeEventInboxRow,
    utcnow,
)
from sitescore_commerce.recovery import (
    RecoveryClaim,
    RecoveryIngressResult,
    RecoveryRuntimeSettings,
    RecoveryService,
    RecoveryStore,
    RecoveryTransportResult,
    canonical_payment_evidence_hash,
)
from sitescore_commerce.settings import STRIPE_API_VERSION, Settings
from sitescore_commerce.webhook import (
    PaymentWebhookService,
    StripeCheckoutEvidence,
    StripeEventEnvelope,
    StripeLineItemEvidence,
)

DATABASE_URL = os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")
ROOT = Path(__file__).resolve().parents[1]


def cfg():
    c = Config(str(ROOT / "alembic.ini"))
    c.set_main_option("script_location", str(ROOT / "alembic"))
    return c


def reset_db():
    command.upgrade(cfg(), "head")
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


def settings():
    return Settings(
        DATABASE_URL,
        "sk_test_not-real",
        "price_1234567890",
        "https://a.example/success",
        "https://a.example/cancel",
        "test",
        "test-signing-secret",
        False,
    )


def make_order(store: CommerceStore, *, bound: bool = True, age_seconds: int = 3600) -> tuple[UUID, str]:
    request = OrderCreateRequest.model_validate(valid_order())
    candidate = uuid4()
    session_id = f"cs_test_{candidate.hex}"
    oid = store.get_or_create_order(
        candidate_order_id=candidate,
        key_digest=uuid4().hex + uuid4().hex,
        request=request,
        catalog_version="v1",
        price_id="price_1234567890",
        quantity=1,
        operation_version=CHECKOUT_OPERATION_VERSION,
        checkout_success_url=f"https://a.example/success?order_id={candidate}&session_id={{CHECKOUT_SESSION_ID}}",
        checkout_cancel_url=f"https://a.example/cancel?order_id={candidate}",
    )
    if bound:
        store.bind_checkout(
            order_id=oid,
            stripe_session_id=session_id,
            checkout_url=f"https://checkout.stripe.com/c/pay/{session_id}",
            expires_at=None,
        )
    old = utcnow() - timedelta(seconds=age_seconds)
    with store.session_factory.begin() as session:
        order = session.get(OrderRow, oid)
        order.created_at = old
        order.updated_at = old
        checkout = session.get(CheckoutSessionRow, oid)
        checkout.created_at = old
        checkout.updated_at = old
    return oid, session_id


def evidence(
    oid: UUID,
    session_id: str,
    *,
    status: str = "complete",
    payment_status: str = "paid",
    payment_intent_id: str | None = "pi_recovery",
    metadata_order_id: str | None = None,
) -> StripeCheckoutEvidence:
    return StripeCheckoutEvidence(
        session_id,
        "checkout.session",
        "payment",
        False,
        str(oid),
        {
            "sitescore_order_id": metadata_order_id or str(oid),
            "sitescore_product_code": "location_report_v1",
            "sitescore_catalog_version": "v1",
        },
        status,
        payment_status,
        payment_intent_id,
        (StripeLineItemEvidence("price_1234567890", 1, "USD"),),
    )


class FixedGateway:
    def __init__(self, values: dict[str, StripeCheckoutEvidence], before_return=None):
        self.values = values
        self.calls: list[str] = []
        self.before_return = before_return

    def retrieve(self, session_id: str) -> StripeCheckoutEvidence:
        self.calls.append(session_id)
        if self.before_return is not None:
            self.before_return()
        return self.values[session_id]


class FixedN8n:
    def __init__(self, results=None, before_return=None):
        self.results = list(results or [RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])
        self.calls = []
        self.before_return = before_return

    def send(self, event):
        self.calls.append(event)
        if self.before_return is not None:
            self.before_return()
        if len(self.results) > 1:
            return self.results.pop(0)
        return self.results[0]


def runtime(*, batch_size: int = 10):
    return RecoveryRuntimeSettings(
        batch_size=batch_size,
        stale_inbox_seconds=1,
        pending_payment_poll_seconds=1,
        published_replay_seconds=1,
        lease_seconds=30,
        maximum_backoff_seconds=60,
    )


def recovery(store: CommerceStore, gateway: FixedGateway, n8n: FixedN8n, *, batch_size: int = 10) -> RecoveryService:
    return RecoveryService(settings=settings(), runtime=runtime(batch_size=batch_size), commerce_store=store, evidence_gateway=gateway, n8n=n8n)


def state(store: CommerceStore, oid: UUID):
    with store.session_factory() as session:
        order = session.get(OrderRow, oid)
        checkout = session.get(CheckoutSessionRow, oid)
        outbox = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalars().all()
        receipts = session.execute(select(PaymentPollReceiptRow).where(PaymentPollReceiptRow.order_id == oid)).scalars().all()
        inbox = session.execute(select(StripeEventInboxRow).where(StripeEventInboxRow.stripe_object_id == checkout.stripe_checkout_session_id)).scalars().all()
        findings = session.execute(select(RecoveryFindingRow).where(RecoveryFindingRow.order_id == oid)).scalars().all()
        recovery_state = session.get(RecoveryStateRow, oid)
        return order, checkout, outbox, receipts, inbox, findings, recovery_state


def transition_paid_by_poll(store: CommerceStore, oid: UUID, session_id: str):
    evd = evidence(oid, session_id)
    outcome, code = store.apply_poll_reconciliation(
        order_id=oid,
        evidence=evd,
        target="paid",
        evidence_sha256=canonical_payment_evidence_hash(evd),
        observed_at=utcnow(),
    )
    assert (outcome, code) == ("transitioned", None)


def test_missing_webhook_server_poll_paid_is_atomic_and_never_fakes_stripe_event():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), FixedN8n()).run_once()
    order, checkout, outbox, receipts, inbox, findings, _ = state(store, oid)
    assert result.claimed == 1 and result.reconciled == 1
    assert (order.order_state, order.payment_state, order.fulfillment_state) == ("paid", "paid", "not_started")
    assert len(outbox) == 1 and outbox[0].outbox_type == "order.paid.v1" and outbox[0].published_at is None
    assert len(receipts) == 1 and receipts[0].source == "stripe_checkout_server_poll_v1" and receipts[0].transition_target == "paid"
    assert receipts[0].stripe_checkout_session_id == sid and len(receipts[0].evidence_sha256) == 64
    assert inbox == []
    assert checkout.last_reconciliation_event_id is None
    assert findings == []


def test_missing_webhook_server_poll_expired_transitions_without_outbox_or_fake_event():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    evd = evidence(oid, sid, status="expired", payment_status="unpaid", payment_intent_id=None)
    result = recovery(store, FixedGateway({sid: evd}), FixedN8n()).run_once()
    order, checkout, outbox, receipts, inbox, findings, _ = state(store, oid)
    assert result.reconciled == 1
    assert (order.order_state, order.payment_state) == ("expired", "expired")
    assert outbox == [] and inbox == [] and findings == []
    assert len(receipts) == 1 and receipts[0].transition_target == "expired"
    assert checkout.last_reconciliation_event_id is None


def test_valid_open_unpaid_poll_defers_without_receipt_or_business_transition():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    evd = evidence(oid, sid, status="open", payment_status="unpaid", payment_intent_id=None)
    result = recovery(store, FixedGateway({sid: evd}), FixedN8n()).run_once()
    order, _, outbox, receipts, inbox, findings, rs = state(store, oid)
    assert result.deferred == 1 and result.reconciled == 0
    assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
    assert outbox == [] and receipts == [] and inbox == [] and findings == []
    assert rs.last_error_code == "provider_nonterminal" and rs.consecutive_failures == 0


def test_poll_binding_mismatch_records_sanitized_attention_and_never_transitions():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    evd = evidence(oid, sid, metadata_order_id=str(uuid4()))
    result = recovery(store, FixedGateway({sid: evd}), FixedN8n()).run_once()
    order, _, outbox, receipts, inbox, findings, rs = state(store, oid)
    assert result.attention == 1
    assert (order.order_state, order.payment_state) == ("pending_payment", "pending")
    assert outbox == [] and receipts == [] and inbox == []
    assert [x.code for x in findings] == ["provider_binding_mismatch"]
    assert rs.last_outcome == "attention" and rs.last_error_code == "provider_binding_mismatch"


def test_stale_received_inbox_resumes_original_real_event_identity_not_poll_receipt():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    event = StripeEventEnvelope(
        "evt_original_recovery",
        "checkout.session.completed",
        STRIPE_API_VERSION,
        False,
        datetime(2026, 8, 20, tzinfo=timezone.utc),
        sid,
        str(oid),
    )
    store.record_stripe_event(event=event, raw_body_sha256=hashlib.sha256(b"real-event").hexdigest())
    with store.session_factory.begin() as session:
        row = session.get(StripeEventInboxRow, event.event_id)
        row.received_at = utcnow() - timedelta(minutes=10)
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), FixedN8n()).run_once()
    order, checkout, outbox, receipts, inbox, findings, _ = state(store, oid)
    assert result.reconciled == 1
    assert (order.order_state, order.payment_state) == ("paid", "paid")
    assert len(outbox) == 1 and receipts == [] and findings == []
    assert len(inbox) == 1 and inbox[0].stripe_event_id == "evt_original_recovery" and inbox[0].processing_state == "processed"
    assert checkout.last_reconciliation_event_id == "evt_original_recovery"


class FixedVerifier:
    def __init__(self, event): self.event = event
    def verify(self, raw_body, signature): return self.event


class WebhookGateway:
    def __init__(self, value, barrier): self.value = value; self.barrier = barrier
    def retrieve(self, session_id): self.barrier.wait(); return self.value


def test_webhook_and_server_poll_race_converges_to_one_paid_outbox_and_distinct_authority_records():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); evd = evidence(oid, sid)
    event = StripeEventEnvelope("evt_race_recovery", "checkout.session.completed", STRIPE_API_VERSION, False, datetime(2026, 8, 20, tzinfo=timezone.utc), sid, str(oid))
    store.record_stripe_event(event=event, raw_body_sha256=hashlib.sha256(b"race").hexdigest())
    barrier = Barrier(2)

    def webhook_worker():
        local = CommerceStore(DATABASE_URL)
        svc = PaymentWebhookService(settings(), local, FixedVerifier(event), WebhookGateway(evd, barrier))
        svc.handle(raw_body=b"race", signature="sig")

    def poll_worker():
        local = CommerceStore(DATABASE_URL)
        barrier.wait()
        local.apply_poll_reconciliation(order_id=oid, evidence=evd, target="paid", evidence_sha256=canonical_payment_evidence_hash(evd), observed_at=utcnow())

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda fn: fn(), [webhook_worker, poll_worker]))
    order, checkout, outbox, receipts, inbox, _, _ = state(store, oid)
    assert (order.order_state, order.payment_state) == ("paid", "paid")
    assert len(outbox) == 1
    assert len(receipts) in {0, 1}
    assert len(inbox) == 1 and inbox[0].stripe_event_id == event.event_id and inbox[0].processing_state == "processed"
    assert checkout.last_reconciliation_event_id == event.event_id
    if receipts:
        assert receipts[0].source == "stripe_checkout_server_poll_v1"


def test_contradictory_paid_after_expired_poll_fails_closed_without_second_receipt():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    expired = evidence(oid, sid, status="expired", payment_status="unpaid", payment_intent_id=None)
    first = store.apply_poll_reconciliation(order_id=oid, evidence=expired, target="expired", evidence_sha256=canonical_payment_evidence_hash(expired), observed_at=utcnow())
    assert first == ("transitioned", None)
    paid = evidence(oid, sid)
    second = store.apply_poll_reconciliation(order_id=oid, evidence=paid, target="paid", evidence_sha256=canonical_payment_evidence_hash(paid), observed_at=utcnow())
    order, _, outbox, receipts, _, _, _ = state(store, oid)
    assert second == ("attention", "contradictory_terminal_payment_truth")
    assert (order.order_state, order.payment_state) == ("expired", "expired")
    assert outbox == [] and len(receipts) == 1 and receipts[0].transition_target == "expired"


def test_unpublished_paid_outbox_confirmed_2xx_marks_same_event_published():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), n8n).run_once()
    _, _, outbox, _, _, findings, _ = state(store, oid)
    assert result.published == 1 and len(n8n.calls) == 1 and findings == []
    assert len(outbox) == 1 and outbox[0].outbox_id == n8n.calls[0].event_id and outbox[0].published_at is not None
    assert n8n.calls[0].event_type == "order.paid.v1" and n8n.calls[0].order_id == oid


def test_unpublished_outbox_uncertain_response_stays_unpublished_and_backs_off():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.UNCERTAIN, failure_code="n8n_transport_uncertain")])
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), n8n).run_once()
    _, _, outbox, _, _, findings, rs = state(store, oid)
    assert result.deferred == 1 and findings == []
    assert outbox[0].published_at is None
    assert rs.consecutive_failures == 1 and rs.last_outcome == "uncertain" and rs.next_attempt_at > utcnow()


def test_published_stale_nonterminal_replays_exact_same_event_and_preserves_published_at():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    old = utcnow() - timedelta(hours=1)
    with store.session_factory.begin() as session:
        order = session.get(OrderRow, oid); order.updated_at = old
        outbox = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == oid)).scalar_one()
        outbox.published_at = old
        original_id = outbox.outbox_id; original_created = outbox.created_at
    n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=202)])
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), n8n).run_once()
    _, _, outboxes, _, _, findings, _ = state(store, oid)
    with store.session_factory() as session:
        audits = session.execute(select(OutboxReplayAuditRow).where(OutboxReplayAuditRow.order_id == oid)).scalars().all()
    assert result.replayed == 1 and findings == [] and len(n8n.calls) == 1
    replay = n8n.calls[0]
    assert replay.event_id == original_id and replay.order_id == oid and replay.event_type == "order.paid.v1" and replay.occurred_at == original_created
    assert outboxes[0].published_at == old
    assert len(audits) == 1 and audits[0].outbox_id == original_id and audits[0].result == "accepted"


def test_n8n_auth_or_contract_rejection_records_attention_without_hot_loop():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)
    n8n = FixedN8n([RecoveryIngressResult(RecoveryTransportResult.ATTENTION, http_status=401, failure_code="n8n_auth_rejected")])
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), n8n).run_once()
    _, _, outbox, _, _, findings, rs = state(store, oid)
    assert result.attention == 1 and outbox[0].published_at is None
    assert [x.code for x in findings] == ["n8n_auth_rejected"]
    assert rs.last_outcome == "attention" and rs.next_attempt_at > utcnow() + timedelta(days=3000)


def test_paid_order_missing_outbox_is_invariant_finding_not_synthesized_repair():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    with store.session_factory.begin() as session:
        order = session.get(OrderRow, oid)
        order.order_state = "paid"; order.payment_state = "paid"; order.updated_at = utcnow() - timedelta(hours=1)
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), FixedN8n()).run_once()
    order, _, outbox, receipts, inbox, findings, rs = state(store, oid)
    assert result.attention == 1
    assert (order.order_state, order.payment_state) == ("paid", "paid")
    assert outbox == [] and receipts == [] and inbox == []
    assert [x.code for x in findings] == ["paid_outbox_invariant"] and rs.last_outcome == "attention"


def test_claim_batch_is_bounded_and_concurrent_workers_do_not_claim_same_live_lease():
    reset_db(); store = CommerceStore(DATABASE_URL)
    ids = [make_order(store)[0] for _ in range(5)]
    rs = RecoveryStore(store); now = utcnow(); rs.seed_candidates(now=now, limit=20)

    def claim_one(_):
        local = RecoveryStore(CommerceStore(DATABASE_URL))
        return local.claim_batch(now=now, batch_size=1, lease_seconds=30)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim_one, range(2)))
    claimed = [claim.order_id for batch in results for claim in batch]
    assert len(claimed) == 2 and len(set(claimed)) == 2 and set(claimed) <= set(ids)


def test_expired_lease_cannot_be_completed_by_stale_worker_even_before_reclaim():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, _ = make_order(store)
    rs = RecoveryStore(store); now = utcnow(); rs.seed_candidates(now=now, limit=10)
    claim = rs.claim_batch(now=now, batch_size=1, lease_seconds=30)[0]
    with store.session_factory.begin() as session:
        row = session.get(RecoveryStateRow, oid); row.lease_expires_at = now - timedelta(seconds=1)
    assert rs.finish_claim(claim=claim, now=now, action="stale", outcome="deferred", error_code=None, failed=False, next_delay_seconds=1) is False


def test_reclaimed_lease_rejects_previous_worker_result():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, _ = make_order(store)
    rs = RecoveryStore(store); now = utcnow(); rs.seed_candidates(now=now, limit=10)
    first = rs.claim_batch(now=now, batch_size=1, lease_seconds=30)[0]
    with store.session_factory.begin() as session:
        row = session.get(RecoveryStateRow, oid); row.lease_expires_at = now - timedelta(seconds=1)
    second = rs.claim_batch(now=now, batch_size=1, lease_seconds=30)[0]
    assert first.lease_token != second.lease_token
    assert rs.finish_claim(claim=first, now=now, action="old", outcome="deferred", error_code=None, failed=False, next_delay_seconds=1) is False
    assert rs.finish_claim(claim=second, now=now, action="new", outcome="deferred", error_code=None, failed=False, next_delay_seconds=1) is True


def test_external_stripe_poll_occurs_without_recovery_row_lock_or_open_scanner_transaction():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)

    def prove_unlocked():
        local = CommerceStore(DATABASE_URL)
        with local.session_factory.begin() as session:
            row = session.execute(select(RecoveryStateRow).where(RecoveryStateRow.order_id == oid).with_for_update(nowait=True)).scalar_one()
            assert row.lease_token is not None

    gateway = FixedGateway({sid: evidence(oid, sid, status="open", payment_status="unpaid", payment_intent_id=None)}, before_return=prove_unlocked)
    result = recovery(store, gateway, FixedN8n()).run_once()
    assert result.deferred == 1 and gateway.calls == [sid]


def test_external_n8n_replay_occurs_without_recovery_row_lock_or_open_scanner_transaction():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store); transition_paid_by_poll(store, oid, sid)

    def prove_unlocked():
        local = CommerceStore(DATABASE_URL)
        with local.session_factory.begin() as session:
            row = session.execute(select(RecoveryStateRow).where(RecoveryStateRow.order_id == oid).with_for_update(nowait=True)).scalar_one()
            assert row.lease_token is not None

    n8n = FixedN8n(before_return=prove_unlocked)
    result = recovery(store, FixedGateway({sid: evidence(oid, sid)}), n8n).run_once()
    assert result.published == 1 and len(n8n.calls) == 1


def test_batch_size_is_hard_bound_for_one_run():
    reset_db(); store = CommerceStore(DATABASE_URL); mapping = {}
    for _ in range(5):
        oid, sid = make_order(store)
        mapping[sid] = evidence(oid, sid, status="open", payment_status="unpaid", payment_intent_id=None)
    result = recovery(store, FixedGateway(mapping), FixedN8n(), batch_size=2).run_once()
    assert result.claimed == 2 and result.deferred == 2
    with store.session_factory() as session:
        assert session.query(RecoveryStateRow).count() <= 5


def test_candidate_seeding_does_not_starve_new_missing_state_behind_existing_backoff_rows():
    reset_db(); store = CommerceStore(DATABASE_URL); rs = RecoveryStore(store); now = utcnow()
    old_ids = [make_order(store, age_seconds=7200)[0] for _ in range(45)]
    rs.seed_candidates(now=now, limit=100)
    with store.session_factory.begin() as session:
        for oid in old_ids:
            row = session.get(RecoveryStateRow, oid)
            row.next_attempt_at = now + timedelta(days=1)
    new_oid, _ = make_order(store, age_seconds=60)
    rs.seed_candidates(now=now, limit=40)
    with store.session_factory() as session:
        assert session.get(RecoveryStateRow, new_oid) is not None


def test_recovery_run_persists_only_counts_not_customer_or_provider_payloads():
    reset_db(); store = CommerceStore(DATABASE_URL); oid, sid = make_order(store)
    result = recovery(store, FixedGateway({sid: evidence(oid, sid, status="open", payment_status="unpaid", payment_intent_id=None)}), FixedN8n()).run_once()
    with store.session_factory() as session:
        row = session.get(RecoveryRunRow, result.run_id)
        assert row.finished_at is not None and row.claimed == result.claimed and row.deferred == result.deferred
    assert set(result.model_dump()) == {"api_version", "run_id", "claimed", "reconciled", "published", "replayed", "deferred", "attention"}
