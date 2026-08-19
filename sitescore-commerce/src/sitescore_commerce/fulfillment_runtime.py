from __future__ import annotations

from uuid import UUID

from .contracts import FulfillmentState, OrderState, PaymentState
from .db import CommerceStore
from .fulfillment import (
    FulfillmentService,
    FulfillmentStore,
    SiteScoreHttpGateway,
    StripeRefundGateway,
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
