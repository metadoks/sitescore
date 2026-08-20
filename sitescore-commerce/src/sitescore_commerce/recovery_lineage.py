from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .checkout import CHECKOUT_OPERATION_VERSION, CheckoutInvariantError
from .db import (
    CheckoutSessionRow,
    CommerceStore,
    OrderRow,
    POLL_RECEIPT_SOURCE,
    PaymentPollReceiptRow,
    PersistenceUnavailable,
    StripeEventInboxRow,
    utcnow,
)
from .dispatcher import OutboxDispatchSettings, PaidOutboxEvent
from .recovery import (
    ReceivedInboxCandidate,
    RecoveryClaim,
    RecoveryN8nIngressClient,
    RecoveryRuntimeSettings,
    RecoveryService,
    RecoveryTransportResult,
    canonical_payment_evidence_hash,
)
from .recovery_atomic import (
    apply_event_reconciliation_with_lease,
    apply_poll_reconciliation_with_lease,
    finish_attention_with_lease,
    mark_inbox_state_with_lease,
    mark_outbox_published_with_lease,
)
from .settings import ConfigurationError, Settings
from .webhook import (
    ASYNC_EVENTS,
    SUPPORTED_EVENTS,
    CheckoutEvidenceGateway,
    StripeCheckoutEvidenceGateway,
)

_ATTENTION_DELAY_SECONDS = 10 * 365 * 24 * 3600


def _safe_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except (TypeError, ValueError, AttributeError):
        return None


class LineageRecoveryService(RecoveryService):
    """Production recovery with signed/legacy lineage and atomic lease fencing.

    New 0.6 Stripe inbox rows carry the candidate order extracted from the verified
    signed Event.  Pre-0005 rows are intentionally distinguishable because that
    column remains NULL after upgrade; those legacy rows may be correlated only by
    their already-stored Stripe Checkout Session identity to exactly one durable
    local checkout binding.  The locally-derived order is never written back into
    candidate_order_id and therefore never masquerades as signed Event evidence.

    After external I/O, recovery business writes lock and validate the exact
    recovery lease inside the same PostgreSQL transaction that applies payment,
    inbox, or outbox truth. A stale worker may still have performed a safe duplicate
    provider read or n8n replay, but cannot write a newer worker's durable result.
    """

    def _correlate_stored_event_order(self, event_id: str) -> tuple[UUID | None, bool]:
        """Return (order_id, is_legacy_local_correlation) without fabricating lineage."""
        try:
            with self.store.session_factory() as session:
                row = session.get(StripeEventInboxRow, event_id)
                if row is None:
                    raise PersistenceUnavailable("recovery Stripe inbox identity is unavailable")

                # A non-NULL value is durable signed-event lineage. It must never be
                # replaced by a locally-derived value when malformed or conflicting.
                if row.candidate_order_id is not None:
                    return _safe_uuid(row.candidate_order_id), False

                # Legacy pre-0005 row: use only the stored real Stripe object/session
                # identity and the UNIQUE checkout binding. No provider/caller input is
                # used and candidate_order_id remains NULL to preserve provenance.
                if not row.stripe_object_id:
                    return None, True
                matches = session.execute(
                    select(CheckoutSessionRow.order_id)
                    .where(CheckoutSessionRow.stripe_checkout_session_id == row.stripe_object_id)
                    .limit(2)
                ).scalars().all()
                if len(matches) != 1:
                    return None, True
                return matches[0], True
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery Stripe inbox lineage is unavailable") from exc

    def _paid_authority_invariant_code(self, order_id: UUID) -> str | None:
        """Validate durable paid Stripe authority before any n8n publish/replay I/O."""
        try:
            with self.store.session_factory() as session:
                order = session.get(OrderRow, order_id)
                checkout = session.get(CheckoutSessionRow, order_id)
                if order is None or checkout is None:
                    return "paid_checkout_binding_missing"

                if checkout.order_id != order.order_id:
                    return "paid_checkout_order_identity_invalid"
                if not checkout.stripe_checkout_session_id:
                    return "paid_checkout_session_missing"
                if checkout.operation_version != CHECKOUT_OPERATION_VERSION:
                    return "paid_checkout_operation_invalid"
                if (
                    checkout.product_code != order.product_code
                    or checkout.catalog_version != order.catalog_version
                    or checkout.customer_email != order.customer_email
                    or checkout.quantity != 1
                    or not checkout.stripe_price_id
                ):
                    return "paid_checkout_catalog_binding_invalid"
                if checkout.stripe_session_status != "complete":
                    return "paid_stripe_session_status_invalid"
                if checkout.stripe_payment_status != "paid":
                    return "paid_stripe_payment_status_invalid"
                if not checkout.stripe_payment_intent_id:
                    return "paid_stripe_payment_intent_missing"
                if checkout.stripe_livemode is not self.settings.stripe_expected_livemode:
                    return "paid_stripe_livemode_invalid"
                if checkout.reconciled_at is None:
                    return "paid_stripe_reconciliation_missing"

                receipts = session.execute(
                    select(PaymentPollReceiptRow)
                    .where(PaymentPollReceiptRow.order_id == order_id)
                    .order_by(PaymentPollReceiptRow.created_at.asc(), PaymentPollReceiptRow.receipt_id.asc())
                ).scalars().all()

                if checkout.last_reconciliation_event_id:
                    inbox = session.get(StripeEventInboxRow, checkout.last_reconciliation_event_id)
                    if inbox is None:
                        return "paid_webhook_lineage_missing"
                    if (
                        inbox.processing_state != "processed"
                        or inbox.stripe_event_type != "checkout.session.completed"
                        or inbox.stripe_object_id != checkout.stripe_checkout_session_id
                        or inbox.livemode is not self.settings.stripe_expected_livemode
                        or (
                            inbox.event_api_version is not None
                            and inbox.event_api_version != self.settings.stripe_api_version
                        )
                    ):
                        return "paid_webhook_lineage_invalid"
                    if (
                        inbox.candidate_order_id is not None
                        and _safe_uuid(inbox.candidate_order_id) != order_id
                    ):
                        return "paid_webhook_order_lineage_invalid"
                else:
                    # Server-poll-paid authority has no fake Event identity. It must
                    # instead have the immutable local poll receipt created atomically
                    # with the winning paid transition.
                    if len(receipts) != 1:
                        return "paid_poll_lineage_missing"
                    receipt = receipts[0]
                    if (
                        receipt.source != POLL_RECEIPT_SOURCE
                        or receipt.transition_target != "paid"
                        or receipt.stripe_checkout_session_id != checkout.stripe_checkout_session_id
                        or receipt.observed_session_status != "complete"
                        or receipt.observed_payment_status != "paid"
                        or receipt.observed_payment_intent_id != checkout.stripe_payment_intent_id
                        or receipt.observed_livemode is not self.settings.stripe_expected_livemode
                        or len(receipt.evidence_sha256 or "") != 64
                    ):
                        return "paid_poll_lineage_invalid"
                return None
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("paid recovery authority validation is unavailable") from exc

    def _finish_attention(
        self,
        claim: RecoveryClaim,
        *,
        run_id: UUID,
        now,
        action: str,
        code: str,
    ) -> bool:
        return finish_attention_with_lease(
            self.commerce_store,
            run_id=run_id,
            order_id=claim.order_id,
            lease_token=claim.lease_token,
            action=action,
            code=code,
            now=now,
            next_attempt_at=now + timedelta(seconds=_ATTENTION_DELAY_SECONDS),
        )

    def _finish_inbox_without_transition(
        self,
        *,
        claim: RecoveryClaim,
        run_id: UUID,
        event_id: str,
        inbox_state: str,
        code: str,
        action: str,
        now,
    ) -> str:
        if not mark_inbox_state_with_lease(
            self.commerce_store,
            order_id=claim.order_id,
            lease_token=claim.lease_token,
            event_id=event_id,
            state=inbox_state,
            failure_code=code,
            processed_at=now,
        ):
            return "lease_lost"
        if inbox_state == "attention_required":
            return "attention" if self._finish_attention(
                claim,
                run_id=run_id,
                now=utcnow(),
                action=action,
                code=code,
            ) else "lease_lost"
        finished = self.store.finish_claim(
            claim=claim,
            now=utcnow(),
            action=action,
            outcome="deferred",
            error_code=code,
            failed=False,
            next_delay_seconds=min(
                self.runtime.pending_payment_poll_seconds,
                self.runtime.maximum_backoff_seconds,
            ),
        )
        return "deferred" if finished else "lease_lost"

    def _resume_inbox(
        self,
        *,
        claim: RecoveryClaim,
        run_id: UUID,
        event: ReceivedInboxCandidate,
        now,
    ) -> tuple[str, str | None]:
        candidate_order_id, legacy_correlation = self._correlate_stored_event_order(event.event_id)
        if candidate_order_id != claim.order_id:
            code = (
                "legacy_event_session_correlation_invalid"
                if legacy_correlation
                else "event_order_correlation_invalid"
            )
            outcome = self._finish_inbox_without_transition(
                claim=claim,
                run_id=run_id,
                event_id=event.event_id,
                inbox_state="attention_required",
                code=code,
                action="resume_stripe_inbox",
                now=utcnow(),
            )
            return outcome, None
        if event.api_version is not None and event.api_version != self.settings.stripe_api_version:
            return self._finish_inbox_without_transition(
                claim=claim,
                run_id=run_id,
                event_id=event.event_id,
                inbox_state="attention_required",
                code="event_api_version_mismatch",
                action="resume_stripe_inbox",
                now=utcnow(),
            ), None
        if event.livemode is not self.settings.stripe_expected_livemode:
            return self._finish_inbox_without_transition(
                claim=claim,
                run_id=run_id,
                event_id=event.event_id,
                inbox_state="attention_required",
                code="event_livemode_mismatch",
                action="resume_stripe_inbox",
                now=utcnow(),
            ), None
        if event.event_type in ASYNC_EVENTS or event.event_type not in SUPPORTED_EVENTS:
            return self._finish_inbox_without_transition(
                claim=claim,
                run_id=run_id,
                event_id=event.event_id,
                inbox_state="ignored",
                code="unsupported_event",
                action="resume_stripe_inbox",
                now=utcnow(),
            ), None
        if not event.session_id:
            return self._finish_inbox_without_transition(
                claim=claim,
                run_id=run_id,
                event_id=event.event_id,
                inbox_state="attention_required",
                code="event_correlation_invalid",
                action="resume_stripe_inbox",
                now=utcnow(),
            ), None

        try:
            evidence = self._validated_evidence(claim.order_id, event.session_id)
        except CheckoutInvariantError:
            return self._finish_inbox_without_transition(
                claim=claim,
                run_id=run_id,
                event_id=event.event_id,
                inbox_state="attention_required",
                code="provider_binding_mismatch",
                action="resume_stripe_inbox",
                now=utcnow(),
            ), None

        if event.event_type == "checkout.session.completed":
            if evidence.status != "complete" or evidence.payment_status != "paid" or not evidence.payment_intent_id:
                return self._finish_inbox_without_transition(
                    claim=claim,
                    run_id=run_id,
                    event_id=event.event_id,
                    inbox_state="attention_required",
                    code="payment_not_authoritative",
                    action="resume_stripe_inbox",
                    now=utcnow(),
                ), None
            target = "paid"
        else:
            if evidence.status != "expired" or evidence.payment_status != "unpaid":
                return self._finish_inbox_without_transition(
                    claim=claim,
                    run_id=run_id,
                    event_id=event.event_id,
                    inbox_state="attention_required",
                    code="expiration_not_authoritative",
                    action="resume_stripe_inbox",
                    now=utcnow(),
                ), None
            target = "expired"

        outcome, code = apply_event_reconciliation_with_lease(
            self.commerce_store,
            order_id=claim.order_id,
            lease_token=claim.lease_token,
            event_id=event.event_id,
            evidence=evidence,
            target=target,
        )
        if outcome == "lease_lost":
            return "lease_lost", None
        if outcome == "attention":
            return (
                "attention"
                if self._finish_attention(
                    claim,
                    run_id=run_id,
                    now=utcnow(),
                    action="resume_stripe_inbox",
                    code=code or "payment_transition_attention",
                )
                else "lease_lost"
            ), None
        if outcome == "already_terminal":
            finished = self.store.finish_claim(
                claim=claim,
                now=utcnow(),
                action="resume_stripe_inbox",
                outcome="deferred",
                error_code=None,
                failed=False,
                next_delay_seconds=0,
            )
            return ("deferred" if finished else "lease_lost"), None
        finished = self.store.finish_claim(
            claim=claim,
            now=utcnow(),
            action="resume_stripe_inbox",
            outcome="reconciled",
            error_code=None,
            failed=False,
            next_delay_seconds=0,
        )
        return ("reconciled" if finished else "lease_lost"), None

    def _poll_payment(
        self,
        *,
        claim: RecoveryClaim,
        run_id: UUID,
        snapshot,
        now,
    ) -> tuple[str, str | None]:
        if not snapshot.stripe_checkout_session_id:
            self._finish_deferred(claim, now=now, action="poll_checkout", code="checkout_not_bound")
            return "deferred", None
        try:
            evidence = self._validated_evidence(claim.order_id, snapshot.stripe_checkout_session_id)
        except CheckoutInvariantError:
            return (
                "attention"
                if self._finish_attention(
                    claim,
                    run_id=run_id,
                    now=utcnow(),
                    action="poll_checkout",
                    code="provider_binding_mismatch",
                )
                else "lease_lost"
            ), None

        observed_at = utcnow()
        target: str | None = None
        if evidence.status == "complete" and evidence.payment_status == "paid" and evidence.payment_intent_id:
            target = "paid"
        elif evidence.status == "expired" and evidence.payment_status == "unpaid" and evidence.payment_intent_id is None:
            target = "expired"
        elif evidence.status in {"open", "complete"} and evidence.payment_status == "unpaid":
            finished = self.store.finish_claim(
                claim=claim,
                now=observed_at,
                action="poll_checkout",
                outcome="deferred",
                error_code="provider_nonterminal",
                failed=False,
                next_delay_seconds=min(
                    self.runtime.pending_payment_poll_seconds,
                    self.runtime.maximum_backoff_seconds,
                ),
            )
            return ("deferred" if finished else "lease_lost"), None
        else:
            return (
                "attention"
                if self._finish_attention(
                    claim,
                    run_id=run_id,
                    now=observed_at,
                    action="poll_checkout",
                    code="provider_payment_evidence_invalid",
                )
                else "lease_lost"
            ), None

        outcome, code = apply_poll_reconciliation_with_lease(
            self.commerce_store,
            order_id=claim.order_id,
            lease_token=claim.lease_token,
            evidence=evidence,
            target=target,
            evidence_sha256=canonical_payment_evidence_hash(evidence),
            observed_at=observed_at,
        )
        if outcome == "lease_lost":
            return "lease_lost", None
        if outcome == "attention":
            return (
                "attention"
                if self._finish_attention(
                    claim,
                    run_id=run_id,
                    now=utcnow(),
                    action="poll_checkout",
                    code=code or "payment_transition_attention",
                )
                else "lease_lost"
            ), None
        final_outcome = "reconciled" if outcome == "transitioned" else "deferred"
        finished = self.store.finish_claim(
            claim=claim,
            now=utcnow(),
            action="poll_checkout",
            outcome=final_outcome,
            error_code=None,
            failed=False,
            next_delay_seconds=0 if outcome == "transitioned" else self.runtime.pending_payment_poll_seconds,
        )
        return (final_outcome if finished else "lease_lost"), None

    def _send_outbox(
        self,
        *,
        claim: RecoveryClaim,
        run_id: UUID,
        event: PaidOutboxEvent,
        published_at,
        now,
    ) -> tuple[str, str | None]:
        # R65-F: orchestration replay is permitted only when the durable local
        # paid reconciliation authority is still coherent. Contradictory/missing
        # Stripe binding is an operator-attention finding, never an n8n trigger.
        authority_code = self._paid_authority_invariant_code(claim.order_id)
        if authority_code is not None:
            finished = self._finish_attention(
                claim,
                run_id=run_id,
                now=utcnow(),
                action="verify_paid_authority",
                code=authority_code,
            )
            return ("attention" if finished else "lease_lost"), authority_code

        result = self.n8n.send(event)
        after_io = utcnow()

        # A published-event replay really happened even if the lease expired while
        # awaiting the response. Preserve that append-only transport audit, but never
        # overwrite recovery state owned by a newer lease.
        if published_at is not None:
            self.store.record_replay(run_id=run_id, event=event, result=result, now=after_io)

        if result.result is RecoveryTransportResult.ACCEPTED:
            if published_at is None:
                if not mark_outbox_published_with_lease(
                    self.commerce_store,
                    order_id=claim.order_id,
                    lease_token=claim.lease_token,
                    event_id=event.event_id,
                    published_at=after_io,
                ):
                    return "lease_lost", None
                finished = self.store.finish_claim(
                    claim=claim,
                    now=utcnow(),
                    action="publish_paid_outbox",
                    outcome="published",
                    error_code=None,
                    failed=False,
                    next_delay_seconds=self.runtime.published_replay_seconds,
                )
                return ("published" if finished else "lease_lost"), None
            finished = self.store.finish_claim(
                claim=claim,
                now=after_io,
                action="replay_paid_outbox",
                outcome="replayed",
                error_code=None,
                failed=False,
                next_delay_seconds=self.runtime.published_replay_seconds,
            )
            return ("replayed" if finished else "lease_lost"), None

        if result.result in {RecoveryTransportResult.UNCERTAIN, RecoveryTransportResult.RETRYABLE_REJECTED}:
            finished = self.store.finish_claim(
                claim=claim,
                now=after_io,
                action="publish_paid_outbox" if published_at is None else "replay_paid_outbox",
                outcome=result.result.value,
                error_code=result.failure_code,
                failed=True,
                next_delay_seconds=self._backoff(claim.consecutive_failures),
            )
            return ("deferred" if finished else "lease_lost"), result.failure_code

        finished = self._finish_attention(
            claim,
            run_id=run_id,
            now=after_io,
            action="publish_paid_outbox" if published_at is None else "replay_paid_outbox",
            code=result.failure_code or "n8n_attention",
        )
        return ("attention" if finished else "lease_lost"), result.failure_code


def build_recovery_service(settings: Settings, store: CommerceStore) -> RecoveryService:
    runtime = RecoveryRuntimeSettings.from_env()
    dispatch_settings = OutboxDispatchSettings.from_env()
    if dispatch_settings.database_url != settings.database_url:
        raise ConfigurationError("recovery n8n dispatch database configuration mismatch")
    return LineageRecoveryService(
        settings=settings,
        runtime=runtime,
        commerce_store=store,
        evidence_gateway=StripeCheckoutEvidenceGateway(settings),
        n8n=RecoveryN8nIngressClient(dispatch_settings),
    )
