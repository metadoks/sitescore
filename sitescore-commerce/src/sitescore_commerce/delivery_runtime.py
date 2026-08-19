from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from .contracts import FulfillmentState, OrderState, PaymentState
from .db import CommerceStore, OrderRow, PersistenceUnavailable, utcnow
from .delivery import (
    DELIVERY_MAX_ATTEMPTS,
    DeliveryAttemptRow,
    DeliveryService,
    DeliveryStore,
    PostmarkGateway,
    SiteScoreDeliveryGateway,
)
from .fulfillment import FulfillmentNotFound
from .settings import Settings


class RuntimeDeliveryService(DeliveryService):
    """Production wrapper for durable retry exhaustion and terminal replay.

    Provider I/O is never re-entered after durable fulfillment success or a
    durable delivery-failed attention state. Retry exhaustion is committed in
    its own transaction before returning to orchestration.
    """

    def _terminal_or_commit_retry_exhaustion(self, order_id: UUID) -> bool:
        try:
            with self.store.session_factory.begin() as session:
                order = session.execute(
                    select(OrderRow).where(OrderRow.order_id == order_id).with_for_update()
                ).scalar_one_or_none()
                if order is None:
                    raise FulfillmentNotFound("order not found")
                if order.order_state == OrderState.FULFILLED.value:
                    return True
                if order.order_state == OrderState.ATTENTION_REQUIRED.value and order.fulfillment_state == FulfillmentState.DELIVERY_FAILED.value:
                    return True
                accepted = session.execute(
                    select(DeliveryAttemptRow.delivery_attempt_id)
                    .where(DeliveryAttemptRow.order_id == order_id, DeliveryAttemptRow.status == "provider_accepted")
                    .limit(1)
                ).scalar_one_or_none()
                if accepted is not None:
                    return False
                attempt_count = session.execute(
                    select(func.count(DeliveryAttemptRow.delivery_attempt_id)).where(DeliveryAttemptRow.order_id == order_id)
                ).scalar_one()
                if int(attempt_count or 0) < DELIVERY_MAX_ATTEMPTS:
                    return False
                order.order_state = OrderState.ATTENTION_REQUIRED.value
                order.payment_state = PaymentState.PAID.value
                order.fulfillment_state = FulfillmentState.DELIVERY_FAILED.value
                order.updated_at = utcnow()
                return True
        except FulfillmentNotFound:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("delivery retry exhaustion could not be persisted") from exc

    def deliver(self, order_id: UUID) -> None:
        if self.store.converge_known_acceptance(order_id):
            return
        if self._terminal_or_commit_retry_exhaustion(order_id):
            return
        super().deliver(order_id)


def build_runtime_delivery_service(settings: Settings, store: CommerceStore) -> DeliveryService:
    return RuntimeDeliveryService(
        settings=settings,
        store=DeliveryStore(store),
        sitescore=SiteScoreDeliveryGateway(settings),
        postmark=PostmarkGateway(settings),
    )
