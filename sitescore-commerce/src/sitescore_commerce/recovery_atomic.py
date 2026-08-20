from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .db import (
    CommerceStore,
    OutboxEventRow,
    PAID_OUTBOX_TYPE,
    POLL_RECEIPT_SOURCE,
    PaymentPollReceiptRow,
    PersistenceUnavailable,
    RecoveryFindingRow,
    RecoveryStateRow,
    StripeEventInboxRow,
    OrderRow,
    CheckoutSessionRow,
    utcnow,
)


def _lease_row_is_current(row: RecoveryStateRow | None, *, lease_token: UUID, now: datetime) -> bool:
    return bool(
        row is not None
        and row.lease_token == lease_token
        and row.lease_expires_at is not None
        and row.lease_expires_at > now
    )


def _lock_current_lease(session, *, order_id: UUID, lease_token: UUID, now: datetime) -> RecoveryStateRow | None:
    row = session.execute(
        select(RecoveryStateRow)
        .where(RecoveryStateRow.order_id == order_id)
        .with_for_update()
    ).scalar_one_or_none()
    return row if _lease_row_is_current(row, lease_token=lease_token, now=now) else None


def apply_event_reconciliation_with_lease(
    store: CommerceStore,
    *,
    order_id: UUID,
    lease_token: UUID,
    event_id: str,
    evidence: object,
    target: str,
) -> tuple[str, str | None]:
    """Fence a recovery worker before applying real-event payment truth."""
    try:
        with store.session_factory.begin() as session:
            write_now = utcnow()
            if _lock_current_lease(session, order_id=order_id, lease_token=lease_token, now=write_now) is None:
                return "lease_lost", None
            inbox = session.execute(
                select(StripeEventInboxRow)
                .where(StripeEventInboxRow.stripe_event_id == event_id)
                .with_for_update()
            ).scalar_one()
            if inbox.processing_state != "received":
                return "already_terminal", None
            order = session.execute(select(OrderRow).where(OrderRow.order_id == order_id).with_for_update()).scalar_one()
            checkout = session.execute(
                select(CheckoutSessionRow).where(CheckoutSessionRow.order_id == order_id).with_for_update()
            ).scalar_one()
            _, failure_code = store._apply_payment_transition_locked(
                session=session,
                order=order,
                checkout=checkout,
                evidence=evidence,
                target=target,
                event_id=event_id,
            )
            completed_at = utcnow()
            if failure_code is not None:
                inbox.processing_state = "attention_required"
                inbox.failure_code = failure_code
                inbox.processed_at = completed_at
                return "attention", failure_code
            inbox.processing_state = "processed"
            inbox.failure_code = None
            inbox.processed_at = completed_at
            return "reconciled", None
    except PersistenceUnavailable:
        raise
    except SQLAlchemyError as exc:
        raise PersistenceUnavailable("lease-fenced Stripe event reconciliation failed") from exc


def apply_poll_reconciliation_with_lease(
    store: CommerceStore,
    *,
    order_id: UUID,
    lease_token: UUID,
    evidence: object,
    target: str,
    evidence_sha256: str,
    observed_at: datetime,
) -> tuple[str, str | None]:
    """Fence server-poll payment truth and its immutable receipt in one transaction."""
    try:
        with store.session_factory.begin() as session:
            write_now = utcnow()
            if _lock_current_lease(session, order_id=order_id, lease_token=lease_token, now=write_now) is None:
                return "lease_lost", None
            order = session.execute(select(OrderRow).where(OrderRow.order_id == order_id).with_for_update()).scalar_one()
            checkout = session.execute(
                select(CheckoutSessionRow).where(CheckoutSessionRow.order_id == order_id).with_for_update()
            ).scalar_one()
            transitioned, failure_code = store._apply_payment_transition_locked(
                session=session,
                order=order,
                checkout=checkout,
                evidence=evidence,
                target=target,
                event_id=None,
            )
            if failure_code is not None:
                return "attention", failure_code
            if not transitioned:
                return "already_terminal", None
            session.add(
                PaymentPollReceiptRow(
                    receipt_id=uuid4(),
                    order_id=order_id,
                    source=POLL_RECEIPT_SOURCE,
                    stripe_checkout_session_id=evidence.session_id,
                    observed_session_status=evidence.status,
                    observed_payment_status=evidence.payment_status,
                    observed_payment_intent_id=evidence.payment_intent_id,
                    observed_livemode=evidence.livemode,
                    evidence_sha256=evidence_sha256,
                    transition_target=target,
                    observed_at=observed_at,
                    created_at=utcnow(),
                )
            )
            return "transitioned", None
    except IntegrityError as exc:
        raise PersistenceUnavailable("payment poll reconciliation receipt conflicted with durable authority") from exc
    except PersistenceUnavailable:
        raise
    except SQLAlchemyError as exc:
        raise PersistenceUnavailable("lease-fenced payment poll reconciliation failed") from exc


def mark_outbox_published_with_lease(
    store: CommerceStore,
    *,
    order_id: UUID,
    lease_token: UUID,
    event_id: UUID,
    published_at: datetime,
) -> bool:
    """Mark publication only while the exact recovery lease is current."""
    try:
        with store.session_factory.begin() as session:
            write_now = utcnow()
            if _lock_current_lease(session, order_id=order_id, lease_token=lease_token, now=write_now) is None:
                return False
            row = session.execute(
                select(OutboxEventRow)
                .where(
                    OutboxEventRow.outbox_id == event_id,
                    OutboxEventRow.order_id == order_id,
                    OutboxEventRow.outbox_type == PAID_OUTBOX_TYPE,
                )
                .with_for_update()
            ).scalar_one_or_none()
            if row is None:
                raise PersistenceUnavailable("recovery outbox event identity is unavailable")
            if row.published_at is None:
                row.published_at = published_at
            return True
    except PersistenceUnavailable:
        raise
    except SQLAlchemyError as exc:
        raise PersistenceUnavailable("lease-fenced outbox publish result failed") from exc


def finish_attention_with_lease(
    store: CommerceStore,
    *,
    run_id: UUID,
    order_id: UUID,
    lease_token: UUID,
    action: str,
    code: str,
    now: datetime,
    next_attempt_at: datetime,
) -> bool:
    """Persist finding and recovery-state attention result under one lease fence."""
    bounded_code = code[:80]
    try:
        with store.session_factory.begin() as session:
            row = _lock_current_lease(session, order_id=order_id, lease_token=lease_token, now=now)
            if row is None:
                return False
            session.add(
                RecoveryFindingRow(
                    finding_id=uuid4(),
                    run_id=run_id,
                    order_id=order_id,
                    code=bounded_code,
                    created_at=now,
                )
            )
            row.last_action = action[:64]
            row.last_outcome = "attention"
            row.last_error_code = bounded_code
            row.consecutive_failures += 1
            row.next_attempt_at = next_attempt_at
            row.lease_token = None
            row.lease_expires_at = None
            row.updated_at = now
            return True
    except SQLAlchemyError as exc:
        raise PersistenceUnavailable("lease-fenced recovery attention result failed") from exc
