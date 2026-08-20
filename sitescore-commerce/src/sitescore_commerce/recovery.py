from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from .checkout import CheckoutInvariantError
from .contracts import OrderState, PaymentState
from .db import (
    CheckoutSessionRow,
    CommerceStore,
    OrderRow,
    OutboxEventRow,
    OutboxReplayAuditRow,
    PAID_OUTBOX_TYPE,
    PaymentPollReceiptRow,
    PersistenceUnavailable,
    RecoveryFindingRow,
    RecoveryRunRow,
    RecoveryStateRow,
    StripeEventInboxRow,
    utcnow,
)
from .dispatcher import OutboxDispatchSettings, PaidOutboxEvent
from .settings import ConfigurationError, Settings
from .webhook import (
    ASYNC_EVENTS,
    SUPPORTED_EVENTS,
    CheckoutEvidenceGateway,
    PaymentProviderUnavailable,
    StripeCheckoutEvidence,
    StripeCheckoutEvidenceGateway,
    validate_binding,
)

RECOVERY_API_VERSION = "2026-08-20"
_ACTIVE_ORDER_STATES = {
    OrderState.PENDING_PAYMENT.value,
    OrderState.PAID.value,
    OrderState.FULFILLMENT_IN_PROGRESS.value,
}
_ATTENTION_DELAY_SECONDS = 10 * 365 * 24 * 3600


class RecoveryTransportResult(StrEnum):
    ACCEPTED = "accepted"
    UNCERTAIN = "uncertain"
    RETRYABLE_REJECTED = "retryable_rejected"
    ATTENTION = "attention"


@dataclass(frozen=True)
class RecoveryIngressResult:
    result: RecoveryTransportResult
    http_status: int | None = None
    failure_code: str | None = None


@dataclass(frozen=True)
class RecoveryClaim:
    order_id: UUID
    lease_token: UUID
    consecutive_failures: int


@dataclass(frozen=True)
class RecoverySnapshot:
    order_id: UUID
    order_state: str
    payment_state: str
    fulfillment_state: str
    order_updated_at: datetime
    stripe_checkout_session_id: str | None
    outboxes: tuple[PaidOutboxEvent, ...]
    published_at_by_id: dict[UUID, datetime | None]


@dataclass(frozen=True)
class ReceivedInboxCandidate:
    event_id: str
    event_type: str
    session_id: str | None
    api_version: str | None
    livemode: bool
    received_at: datetime


class RecoveryRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: str = RECOVERY_API_VERSION
    run_id: UUID
    claimed: int
    reconciled: int
    published: int
    replayed: int
    deferred: int
    attention: int


@dataclass(frozen=True)
class RecoveryRuntimeSettings:
    batch_size: int = 10
    stale_inbox_seconds: int = 120
    pending_payment_poll_seconds: int = 300
    published_replay_seconds: int = 1200
    lease_seconds: int = 120
    maximum_backoff_seconds: int = 3600

    @staticmethod
    def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
        raw = os.getenv(name, str(default)).strip()
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigurationError(f"{name} must be an integer") from exc
        if value < minimum or value > maximum:
            raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
        return value

    @classmethod
    def from_env(cls) -> "RecoveryRuntimeSettings":
        return cls(
            batch_size=cls._bounded_int("COMMERCE_RECOVERY_BATCH_SIZE", 10, 1, 100),
            stale_inbox_seconds=cls._bounded_int("COMMERCE_RECOVERY_STALE_INBOX_SECONDS", 120, 30, 86400),
            pending_payment_poll_seconds=cls._bounded_int("COMMERCE_RECOVERY_PENDING_PAYMENT_SECONDS", 300, 60, 86400),
            published_replay_seconds=cls._bounded_int("COMMERCE_RECOVERY_PUBLISHED_REPLAY_SECONDS", 1200, 120, 604800),
            lease_seconds=cls._bounded_int("COMMERCE_RECOVERY_LEASE_SECONDS", 120, 30, 900),
            maximum_backoff_seconds=cls._bounded_int("COMMERCE_RECOVERY_MAX_BACKOFF_SECONDS", 3600, 60, 86400),
        )


class RecoveryN8nIngressClient:
    def __init__(self, settings: OutboxDispatchSettings, *, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client or httpx.Client(timeout=settings.timeout_seconds, follow_redirects=False)

    def send(self, event: PaidOutboxEvent) -> RecoveryIngressResult:
        try:
            response = self.client.post(
                self.settings.webhook_url,
                headers={
                    "Authorization": f"Bearer {self.settings.ingress_secret}",
                    "Content-Type": "application/json",
                },
                json=event.payload(),
            )
        except httpx.RequestError:
            return RecoveryIngressResult(RecoveryTransportResult.UNCERTAIN, failure_code="n8n_transport_uncertain")
        status = response.status_code
        if 200 <= status < 300:
            return RecoveryIngressResult(RecoveryTransportResult.ACCEPTED, http_status=status)
        if status == 429:
            return RecoveryIngressResult(RecoveryTransportResult.RETRYABLE_REJECTED, http_status=status, failure_code="n8n_http_429")
        if 500 <= status < 600:
            return RecoveryIngressResult(RecoveryTransportResult.RETRYABLE_REJECTED, http_status=status, failure_code="n8n_http_5xx")
        if status in {401, 403}:
            return RecoveryIngressResult(RecoveryTransportResult.ATTENTION, http_status=status, failure_code="n8n_auth_rejected")
        if status in {400, 422}:
            return RecoveryIngressResult(RecoveryTransportResult.ATTENTION, http_status=status, failure_code="n8n_contract_rejected")
        return RecoveryIngressResult(RecoveryTransportResult.ATTENTION, http_status=status, failure_code="n8n_unexpected_response")


class RecoveryStore:
    def __init__(self, commerce_store: CommerceStore):
        self.commerce_store = commerce_store
        self.session_factory = commerce_store.session_factory

    def begin_run(self, run_id: UUID, now: datetime) -> None:
        try:
            with self.session_factory.begin() as session:
                session.add(RecoveryRunRow(run_id=run_id, started_at=now, finished_at=None, claimed=0, reconciled=0, published=0, replayed=0, deferred=0, attention=0))
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery run could not be started") from exc

    def finish_run(self, response: RecoveryRunResponse, now: datetime) -> None:
        try:
            with self.session_factory.begin() as session:
                row = session.execute(select(RecoveryRunRow).where(RecoveryRunRow.run_id == response.run_id).with_for_update()).scalar_one()
                row.finished_at = now
                row.claimed = response.claimed
                row.reconciled = response.reconciled
                row.published = response.published
                row.replayed = response.replayed
                row.deferred = response.deferred
                row.attention = response.attention
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery run could not be finalized") from exc

    def seed_candidates(self, *, now: datetime, limit: int) -> None:
        try:
            with self.session_factory.begin() as session:
                order_ids = session.execute(
                    select(OrderRow.order_id)
                    .where(OrderRow.order_state.in_(_ACTIVE_ORDER_STATES))
                    .order_by(OrderRow.updated_at.asc(), OrderRow.order_id.asc())
                    .limit(limit)
                ).scalars().all()
                for order_id in order_ids:
                    session.execute(
                        pg_insert(RecoveryStateRow)
                        .values(
                            order_id=order_id,
                            attempt_count=0,
                            consecutive_failures=0,
                            next_attempt_at=now,
                            last_checked_at=None,
                            last_action=None,
                            last_outcome=None,
                            last_error_code=None,
                            lease_token=None,
                            lease_expires_at=None,
                            created_at=now,
                            updated_at=now,
                        )
                        .on_conflict_do_nothing(index_elements=[RecoveryStateRow.order_id])
                    )
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery candidates could not be seeded") from exc

    def claim_batch(self, *, now: datetime, batch_size: int, lease_seconds: int) -> tuple[RecoveryClaim, ...]:
        claims: list[RecoveryClaim] = []
        try:
            with self.session_factory.begin() as session:
                rows = session.execute(
                    select(RecoveryStateRow)
                    .join(OrderRow, OrderRow.order_id == RecoveryStateRow.order_id)
                    .where(
                        OrderRow.order_state.in_(_ACTIVE_ORDER_STATES),
                        RecoveryStateRow.next_attempt_at <= now,
                        or_(RecoveryStateRow.lease_token.is_(None), RecoveryStateRow.lease_expires_at <= now),
                    )
                    .order_by(RecoveryStateRow.next_attempt_at.asc(), RecoveryStateRow.created_at.asc(), RecoveryStateRow.order_id.asc())
                    .with_for_update(skip_locked=True)
                    .limit(batch_size)
                ).scalars().all()
                for row in rows:
                    token = uuid4()
                    previous_failures = row.consecutive_failures
                    row.lease_token = token
                    row.lease_expires_at = now + timedelta(seconds=lease_seconds)
                    row.attempt_count += 1
                    row.last_checked_at = now
                    row.updated_at = now
                    claims.append(RecoveryClaim(row.order_id, token, previous_failures))
            return tuple(claims)
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery candidates could not be claimed") from exc

    def finish_claim(
        self,
        *,
        claim: RecoveryClaim,
        now: datetime,
        action: str,
        outcome: str,
        error_code: str | None,
        failed: bool,
        next_delay_seconds: int,
    ) -> bool:
        code = error_code[:80] if error_code else None
        try:
            with self.session_factory.begin() as session:
                row = session.execute(select(RecoveryStateRow).where(RecoveryStateRow.order_id == claim.order_id).with_for_update()).scalar_one_or_none()
                if row is None or row.lease_token != claim.lease_token:
                    return False
                row.last_action = action[:64]
                row.last_outcome = outcome[:64]
                row.last_error_code = code
                row.consecutive_failures = row.consecutive_failures + 1 if failed else 0
                row.next_attempt_at = now + timedelta(seconds=next_delay_seconds)
                row.lease_token = None
                row.lease_expires_at = None
                row.updated_at = now
                return True
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery lease result could not be persisted") from exc

    def record_finding(self, *, run_id: UUID, order_id: UUID, code: str, now: datetime) -> None:
        try:
            with self.session_factory.begin() as session:
                session.add(RecoveryFindingRow(finding_id=uuid4(), run_id=run_id, order_id=order_id, code=code[:80], created_at=now))
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery finding could not be persisted") from exc

    def record_replay(self, *, run_id: UUID, event: PaidOutboxEvent, result: RecoveryIngressResult, now: datetime) -> None:
        try:
            with self.session_factory.begin() as session:
                session.add(OutboxReplayAuditRow(
                    replay_attempt_id=uuid4(),
                    run_id=run_id,
                    order_id=event.order_id,
                    outbox_id=event.event_id,
                    attempted_at=now,
                    result=result.result.value,
                    failure_code=(result.failure_code or "")[:80] or None,
                ))
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery replay audit could not be persisted") from exc

    def mark_outbox_published(self, event_id: UUID, now: datetime) -> None:
        try:
            with self.session_factory.begin() as session:
                row = session.execute(select(OutboxEventRow).where(OutboxEventRow.outbox_id == event_id, OutboxEventRow.outbox_type == PAID_OUTBOX_TYPE).with_for_update()).scalar_one_or_none()
                if row is None:
                    raise PersistenceUnavailable("recovery outbox identity is unavailable")
                if row.published_at is None:
                    row.published_at = now
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery outbox publish result could not be persisted") from exc

    def load_snapshot(self, order_id: UUID) -> RecoverySnapshot:
        try:
            with self.session_factory() as session:
                order = session.get(OrderRow, order_id)
                checkout = session.get(CheckoutSessionRow, order_id)
                if order is None or checkout is None:
                    raise PersistenceUnavailable("recovery order binding is unavailable")
                rows = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == order_id, OutboxEventRow.outbox_type == PAID_OUTBOX_TYPE).order_by(OutboxEventRow.created_at.asc(), OutboxEventRow.outbox_id.asc())).scalars().all()
                events = tuple(PaidOutboxEvent(row.outbox_id, row.outbox_type, row.order_id, row.created_at) for row in rows)
                return RecoverySnapshot(
                    order_id=order.order_id,
                    order_state=order.order_state,
                    payment_state=order.payment_state,
                    fulfillment_state=order.fulfillment_state,
                    order_updated_at=order.updated_at,
                    stripe_checkout_session_id=checkout.stripe_checkout_session_id,
                    outboxes=events,
                    published_at_by_id={row.outbox_id: row.published_at for row in rows},
                )
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery order snapshot is unavailable") from exc

    def load_stale_received_event(self, *, order_id: UUID, cutoff: datetime) -> ReceivedInboxCandidate | None:
        try:
            with self.session_factory() as session:
                checkout = session.get(CheckoutSessionRow, order_id)
                if checkout is None or checkout.stripe_checkout_session_id is None:
                    return None
                row = session.execute(
                    select(StripeEventInboxRow)
                    .where(
                        StripeEventInboxRow.processing_state == "received",
                        StripeEventInboxRow.stripe_object_id == checkout.stripe_checkout_session_id,
                        StripeEventInboxRow.received_at <= cutoff,
                    )
                    .order_by(StripeEventInboxRow.received_at.asc(), StripeEventInboxRow.stripe_event_id.asc())
                    .limit(1)
                ).scalar_one_or_none()
                if row is None:
                    return None
                return ReceivedInboxCandidate(row.stripe_event_id, row.stripe_event_type, row.stripe_object_id, row.event_api_version, row.livemode, row.received_at)
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery Stripe inbox lookup is unavailable") from exc

    def lease_is_current(self, claim: RecoveryClaim, now: datetime) -> bool:
        try:
            with self.session_factory() as session:
                row = session.get(RecoveryStateRow, claim.order_id)
                return bool(row is not None and row.lease_token == claim.lease_token and row.lease_expires_at is not None and row.lease_expires_at > now)
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery lease state is unavailable") from exc


def canonical_payment_evidence_hash(evidence: StripeCheckoutEvidence) -> str:
    payload = {
        "session_id": evidence.session_id,
        "object_type": evidence.object_type,
        "mode": evidence.mode,
        "livemode": evidence.livemode,
        "client_reference_id": evidence.client_reference_id,
        "metadata": dict(sorted(evidence.metadata.items())),
        "status": evidence.status,
        "payment_status": evidence.payment_status,
        "payment_intent_id": evidence.payment_intent_id,
        "line_items": [
            {"price_id": item.price_id, "quantity": item.quantity, "currency": item.currency}
            for item in evidence.line_items
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class RecoveryService:
    def __init__(
        self,
        *,
        settings: Settings,
        runtime: RecoveryRuntimeSettings,
        commerce_store: CommerceStore,
        evidence_gateway: CheckoutEvidenceGateway,
        n8n: RecoveryN8nIngressClient,
    ):
        self.settings = settings
        self.runtime = runtime
        self.commerce_store = commerce_store
        self.store = RecoveryStore(commerce_store)
        self.evidence_gateway = evidence_gateway
        self.n8n = n8n

    def _backoff(self, previous_failures: int) -> int:
        exponent = min(previous_failures, 12)
        return min(30 * (2 ** exponent), self.runtime.maximum_backoff_seconds)

    def _finish_deferred(self, claim: RecoveryClaim, *, now: datetime, action: str, code: str | None = None, failed: bool = False) -> None:
        delay = self._backoff(claim.consecutive_failures) if failed else min(self.runtime.pending_payment_poll_seconds, self.runtime.maximum_backoff_seconds)
        self.store.finish_claim(claim=claim, now=now, action=action, outcome="deferred", error_code=code, failed=failed, next_delay_seconds=delay)

    def _finish_attention(self, claim: RecoveryClaim, *, run_id: UUID, now: datetime, action: str, code: str) -> None:
        self.store.record_finding(run_id=run_id, order_id=claim.order_id, code=code, now=now)
        self.store.finish_claim(claim=claim, now=now, action=action, outcome="attention", error_code=code, failed=True, next_delay_seconds=_ATTENTION_DELAY_SECONDS)

    def _validated_evidence(self, order_id: UUID, session_id: str) -> StripeCheckoutEvidence:
        order, checkout = self.commerce_store.load_order_and_checkout(order_id)
        evidence = self.evidence_gateway.retrieve(session_id)
        if evidence.session_id != session_id:
            raise CheckoutInvariantError("provider session identity mismatch")
        validate_binding(evidence=evidence, order=order, checkout=checkout, expected_livemode=self.settings.stripe_expected_livemode)
        return evidence

    def _resume_inbox(self, *, claim: RecoveryClaim, run_id: UUID, event: ReceivedInboxCandidate, now: datetime) -> tuple[str, str | None]:
        if event.api_version is not None and event.api_version != self.settings.stripe_api_version:
            self.commerce_store.mark_event_attention(event.event_id, "event_api_version_mismatch")
            self._finish_attention(claim, run_id=run_id, now=now, action="resume_stripe_inbox", code="event_api_version_mismatch")
            return "attention", None
        if event.livemode is not self.settings.stripe_expected_livemode:
            self.commerce_store.mark_event_attention(event.event_id, "event_livemode_mismatch")
            self._finish_attention(claim, run_id=run_id, now=now, action="resume_stripe_inbox", code="event_livemode_mismatch")
            return "attention", None
        if event.event_type in ASYNC_EVENTS or event.event_type not in SUPPORTED_EVENTS:
            self.commerce_store.mark_event_ignored(event.event_id, "unsupported_event")
            self._finish_deferred(claim, now=now, action="resume_stripe_inbox", code="unsupported_event")
            return "deferred", None
        if not event.session_id:
            self.commerce_store.mark_event_attention(event.event_id, "event_correlation_invalid")
            self._finish_attention(claim, run_id=run_id, now=now, action="resume_stripe_inbox", code="event_correlation_invalid")
            return "attention", None
        try:
            evidence = self._validated_evidence(claim.order_id, event.session_id)
        except CheckoutInvariantError:
            self.commerce_store.mark_event_attention(event.event_id, "provider_binding_mismatch")
            self._finish_attention(claim, run_id=run_id, now=now, action="resume_stripe_inbox", code="provider_binding_mismatch")
            return "attention", None
        if event.event_type == "checkout.session.completed":
            if evidence.status != "complete" or evidence.payment_status != "paid" or not evidence.payment_intent_id:
                self.commerce_store.mark_event_attention(event.event_id, "payment_not_authoritative")
                self._finish_attention(claim, run_id=run_id, now=now, action="resume_stripe_inbox", code="payment_not_authoritative")
                return "attention", None
            target = "paid"
        else:
            if evidence.status != "expired" or evidence.payment_status != "unpaid":
                self.commerce_store.mark_event_attention(event.event_id, "expiration_not_authoritative")
                self._finish_attention(claim, run_id=run_id, now=now, action="resume_stripe_inbox", code="expiration_not_authoritative")
                return "attention", None
            target = "expired"
        if not self.store.lease_is_current(claim, utcnow()):
            return "lease_lost", None
        self.commerce_store.apply_reconciliation(event_id=event.event_id, order_id=claim.order_id, evidence=evidence, target=target)
        self.store.finish_claim(claim=claim, now=utcnow(), action="resume_stripe_inbox", outcome="reconciled", error_code=None, failed=False, next_delay_seconds=0)
        return "reconciled", None

    def _poll_payment(self, *, claim: RecoveryClaim, run_id: UUID, snapshot: RecoverySnapshot, now: datetime) -> tuple[str, str | None]:
        if not snapshot.stripe_checkout_session_id:
            self._finish_deferred(claim, now=now, action="poll_checkout", code="checkout_not_bound")
            return "deferred", None
        try:
            evidence = self._validated_evidence(claim.order_id, snapshot.stripe_checkout_session_id)
        except CheckoutInvariantError:
            self._finish_attention(claim, run_id=run_id, now=now, action="poll_checkout", code="provider_binding_mismatch")
            return "attention", None
        if not self.store.lease_is_current(claim, utcnow()):
            return "lease_lost", None
        target: str | None = None
        if evidence.status == "complete" and evidence.payment_status == "paid" and evidence.payment_intent_id:
            target = "paid"
        elif evidence.status == "expired" and evidence.payment_status == "unpaid" and evidence.payment_intent_id is None:
            target = "expired"
        elif evidence.status == "open" and evidence.payment_status == "unpaid":
            self._finish_deferred(claim, now=utcnow(), action="poll_checkout", code="provider_nonterminal")
            return "deferred", None
        elif evidence.status == "complete" and evidence.payment_status == "unpaid":
            self._finish_deferred(claim, now=utcnow(), action="poll_checkout", code="provider_nonterminal")
            return "deferred", None
        else:
            self._finish_attention(claim, run_id=run_id, now=utcnow(), action="poll_checkout", code="provider_payment_evidence_invalid")
            return "attention", None
        outcome, code = self.commerce_store.apply_poll_reconciliation(
            order_id=claim.order_id,
            evidence=evidence,
            target=target,
            evidence_sha256=canonical_payment_evidence_hash(evidence),
            observed_at=utcnow(),
        )
        if outcome == "attention":
            self._finish_attention(claim, run_id=run_id, now=utcnow(), action="poll_checkout", code=code or "payment_transition_attention")
            return "attention", None
        self.store.finish_claim(claim=claim, now=utcnow(), action="poll_checkout", outcome="reconciled" if outcome == "transitioned" else "deferred", error_code=None, failed=False, next_delay_seconds=0 if outcome == "transitioned" else self.runtime.pending_payment_poll_seconds)
        return "reconciled" if outcome == "transitioned" else "deferred", None

    def _send_outbox(self, *, claim: RecoveryClaim, run_id: UUID, event: PaidOutboxEvent, published_at: datetime | None, now: datetime) -> tuple[str, str | None]:
        result = self.n8n.send(event)
        after_io = utcnow()
        if not self.store.lease_is_current(claim, after_io):
            return "lease_lost", None
        if published_at is not None:
            self.store.record_replay(run_id=run_id, event=event, result=result, now=after_io)
        if result.result is RecoveryTransportResult.ACCEPTED:
            if published_at is None:
                self.store.mark_outbox_published(event.event_id, after_io)
                self.store.finish_claim(claim=claim, now=after_io, action="publish_paid_outbox", outcome="published", error_code=None, failed=False, next_delay_seconds=self.runtime.published_replay_seconds)
                return "published", None
            self.store.finish_claim(claim=claim, now=after_io, action="replay_paid_outbox", outcome="replayed", error_code=None, failed=False, next_delay_seconds=self.runtime.published_replay_seconds)
            return "replayed", None
        if result.result in {RecoveryTransportResult.UNCERTAIN, RecoveryTransportResult.RETRYABLE_REJECTED}:
            self.store.finish_claim(claim=claim, now=after_io, action="publish_paid_outbox" if published_at is None else "replay_paid_outbox", outcome=result.result.value, error_code=result.failure_code, failed=True, next_delay_seconds=self._backoff(claim.consecutive_failures))
            return "deferred", result.failure_code
        self._finish_attention(claim, run_id=run_id, now=after_io, action="publish_paid_outbox" if published_at is None else "replay_paid_outbox", code=result.failure_code or "n8n_attention")
        return "attention", result.failure_code

    def _process_claim(self, *, claim: RecoveryClaim, run_id: UUID, now: datetime) -> str:
        snapshot = self.store.load_snapshot(claim.order_id)
        if snapshot.order_state not in _ACTIVE_ORDER_STATES:
            self.store.finish_claim(claim=claim, now=now, action="terminal_noop", outcome="deferred", error_code=None, failed=False, next_delay_seconds=_ATTENTION_DELAY_SECONDS)
            return "deferred"

        stale_event = self.store.load_stale_received_event(order_id=claim.order_id, cutoff=now - timedelta(seconds=self.runtime.stale_inbox_seconds))
        if stale_event is not None:
            outcome, _ = self._resume_inbox(claim=claim, run_id=run_id, event=stale_event, now=now)
            return outcome

        if snapshot.order_state == OrderState.PENDING_PAYMENT.value and snapshot.payment_state == PaymentState.PENDING.value:
            if snapshot.order_updated_at > now - timedelta(seconds=self.runtime.pending_payment_poll_seconds):
                self._finish_deferred(claim, now=now, action="poll_checkout", code="pending_payment_not_stale")
                return "deferred"
            outcome, _ = self._poll_payment(claim=claim, run_id=run_id, snapshot=snapshot, now=now)
            return outcome

        if snapshot.payment_state in {PaymentState.PAID.value, PaymentState.REFUND_PENDING.value} and snapshot.order_state in {OrderState.PAID.value, OrderState.FULFILLMENT_IN_PROGRESS.value}:
            if len(snapshot.outboxes) != 1:
                self._finish_attention(claim, run_id=run_id, now=now, action="verify_paid_outbox", code="paid_outbox_invariant")
                return "attention"
            event = snapshot.outboxes[0]
            published_at = snapshot.published_at_by_id[event.event_id]
            if published_at is None:
                outcome, _ = self._send_outbox(claim=claim, run_id=run_id, event=event, published_at=None, now=now)
                return outcome
            replay_cutoff = now - timedelta(seconds=self.runtime.published_replay_seconds)
            newest_authority_time = max(snapshot.order_updated_at, published_at)
            if newest_authority_time > replay_cutoff:
                self._finish_deferred(claim, now=now, action="replay_paid_outbox", code="published_order_not_stale")
                return "deferred"
            outcome, _ = self._send_outbox(claim=claim, run_id=run_id, event=event, published_at=published_at, now=now)
            return outcome

        self._finish_deferred(claim, now=now, action="no_recovery_action", code="state_not_recoverable")
        return "deferred"

    def run_once(self) -> RecoveryRunResponse:
        run_id = uuid4()
        started = utcnow()
        self.store.begin_run(run_id, started)
        self.store.seed_candidates(now=started, limit=max(self.runtime.batch_size * 4, self.runtime.batch_size))
        claims = self.store.claim_batch(now=started, batch_size=self.runtime.batch_size, lease_seconds=self.runtime.lease_seconds)
        counts = {"reconciled": 0, "published": 0, "replayed": 0, "deferred": 0, "attention": 0}
        for claim in claims:
            try:
                outcome = self._process_claim(claim=claim, run_id=run_id, now=utcnow())
                if outcome in counts:
                    counts[outcome] += 1
                elif outcome == "lease_lost":
                    counts["deferred"] += 1
            except PaymentProviderUnavailable:
                self._finish_deferred(claim, now=utcnow(), action="stripe_provider", code="stripe_provider_unavailable", failed=True)
                counts["deferred"] += 1
            except PersistenceUnavailable:
                # The claim lease will expire if even the result write cannot be persisted.
                try:
                    self._finish_deferred(claim, now=utcnow(), action="recovery_persistence", code="recovery_persistence_unavailable", failed=True)
                except PersistenceUnavailable:
                    pass
                counts["deferred"] += 1
            except Exception:
                # No raw exception/provider body is persisted or returned.  The durable lease
                # remains recoverable and the sanitized code prevents a hot loop.
                try:
                    self._finish_deferred(claim, now=utcnow(), action="recovery_internal", code="recovery_internal_error", failed=True)
                except PersistenceUnavailable:
                    pass
                counts["deferred"] += 1
        response = RecoveryRunResponse(run_id=run_id, claimed=len(claims), **counts)
        self.store.finish_run(response, utcnow())
        return response


def build_recovery_service(settings: Settings, store: CommerceStore) -> RecoveryService:
    runtime = RecoveryRuntimeSettings.from_env()
    dispatch_settings = OutboxDispatchSettings.from_env()
    if dispatch_settings.database_url != settings.database_url:
        raise ConfigurationError("recovery n8n dispatch database configuration mismatch")
    return RecoveryService(
        settings=settings,
        runtime=runtime,
        commerce_store=store,
        evidence_gateway=StripeCheckoutEvidenceGateway(settings),
        n8n=RecoveryN8nIngressClient(dispatch_settings),
    )
