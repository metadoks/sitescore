from __future__ import annotations

from uuid import UUID

from .contracts import FulfillmentState, OrderState, PaymentState
from .db import CommerceStore
from .fulfillment import (
    FulfillmentInvariantError,
    FulfillmentService,
    FulfillmentStore,
    SiteScoreHttpGateway,
    StripeRefundGateway,
    _is_matching_refund,
    validate_payment_intent,
    validate_refund_for_operation,
)
from .settings import Settings


class FulfillmentRuntimeService(FulfillmentService):
    """Crash-window-aware production state-machine driver.

    Durable authority primitives live in ``fulfillment.py``. This driver decides
    whether a retry must repeat the same durable POST or poll an already-bound
    provider resource, without holding a database transaction over network I/O.
    """

    def advance(self, order_id: UUID):
        status = self.store.get_status(order_id)
        if status.order_state in {
            OrderState.REFUNDED.value,
            OrderState.FULFILLED.value,
            OrderState.EXPIRED.value,
            OrderState.ATTENTION_REQUIRED.value,
        }:
            return status
        if status.payment_state != PaymentState.PAID.value and status.fulfillment_state not in self._refund_states():
            return status

        if status.fulfillment_state == FulfillmentState.NOT_STARTED.value:
            self._ensure_analysis(order_id)
        elif status.fulfillment_state == FulfillmentState.ANALYSIS_PENDING.value:
            binding = self.store.get_binding(order_id)
            if binding is None or binding.analysis_id is None:
                # POST may have succeeded while its response was lost. Re-submit
                # the exact durable target/key/payload; never mint a new identity.
                self._ensure_analysis(order_id)
            else:
                self._reconcile_analysis(order_id)
        elif status.fulfillment_state == FulfillmentState.ANALYSIS_RUNNING.value:
            self._reconcile_analysis(order_id)
        elif status.fulfillment_state == FulfillmentState.REPORT_PENDING.value:
            self._ensure_report(order_id)
        elif status.fulfillment_state in self._refund_states():
            self._ensure_refund(order_id, status.fulfillment_state)
        return self.store.get_status(order_id)

    def _ensure_refund(self, order_id: UUID, fulfillment_state: str) -> None:
        reason, resource_type, resource_id, terminal_state = self._reprove_eligibility(order_id, fulfillment_state)
        self.store.persist_refund_eligibility(
            order_id=order_id,
            reason=reason,
            resource_type=resource_type,
            resource_id=resource_id,
            terminal_state=terminal_state,
        )
        order, checkout, _, _ = self.store.load_refund_context(order_id)
        if checkout.stripe_payment_intent_id is None:
            self.store.mark_attention(order_id=order_id, code="payment_intent_missing")
            return

        payment_intent = self.refunds.retrieve_payment_intent(checkout.stripe_payment_intent_id)
        try:
            validate_payment_intent(
                evidence=payment_intent,
                order=order,
                checkout=checkout,
                expected_livemode=self.settings.stripe_expected_livemode,
            )
        except FulfillmentInvariantError:
            self.store.mark_attention(order_id=order_id, code="payment_intent_binding_mismatch")
            return

        operation = self.store.prepare_refund_operation(order_id=order_id, payment_intent=payment_intent)
        provider_refunds = self.refunds.list_refunds(operation.stripe_payment_intent_id)
        matching = [item for item in provider_refunds if _is_matching_refund(item, operation)]

        # Never silently ignore a second or conflicting provider refund. One
        # provider history shape must map to one deterministic local authority.
        if len(matching) > 1 or (matching and len(provider_refunds) != 1):
            self.store.mark_attention(order_id=order_id, code="conflicting_existing_refunds", refund_failure=True)
            return
        if matching:
            try:
                validate_refund_for_operation(matching[0], operation, require_metadata=True)
                self.store.bind_refund(operation=operation, evidence=matching[0])
            except FulfillmentInvariantError:
                self.store.mark_attention(order_id=order_id, code="matching_refund_conflict", refund_failure=True)
            return

        if provider_refunds:
            if len(provider_refunds) != 1:
                self.store.mark_attention(order_id=order_id, code="conflicting_existing_refunds", refund_failure=True)
                return
            existing = provider_refunds[0]
            sitescore_metadata_keys = set(operation.metadata)
            if sitescore_metadata_keys.intersection(existing.metadata):
                # SiteScore-shaped metadata that does not exactly match this
                # operation is contradictory, not an unattributed external refund.
                self.store.mark_attention(order_id=order_id, code="conflicting_refund_metadata", refund_failure=True)
                return
            if (
                existing.payment_intent_id == operation.stripe_payment_intent_id
                and existing.currency == operation.currency
                and existing.amount == operation.original_amount_received
                and existing.status == "succeeded"
            ):
                self.store.bind_refund(operation=operation, evidence=existing, external_full=True)
                return
            self.store.mark_attention(order_id=order_id, code="conflicting_existing_refund", refund_failure=True)
            return

        try:
            evidence = self.refunds.create_refund(operation)
            validate_refund_for_operation(evidence, operation, require_metadata=True)
            self.store.bind_refund(operation=operation, evidence=evidence)
        except FulfillmentInvariantError:
            self.store.mark_attention(order_id=order_id, code="refund_provider_binding_mismatch", refund_failure=True)

    @staticmethod
    def _refund_states() -> frozenset[str]:
        return frozenset({
            FulfillmentState.NOT_SCORE_READY.value,
            FulfillmentState.ANALYSIS_FAILED.value,
            FulfillmentState.ANALYSIS_TIMED_OUT.value,
            FulfillmentState.REPORT_FAILED.value,
        })


def build_runtime_fulfillment_service(settings: Settings, commerce_store: CommerceStore) -> FulfillmentRuntimeService:
    return FulfillmentRuntimeService(
        settings=settings,
        store=FulfillmentStore(commerce_store),
        sitescore=SiteScoreHttpGateway(settings),
        refunds=StripeRefundGateway(settings),
    )
