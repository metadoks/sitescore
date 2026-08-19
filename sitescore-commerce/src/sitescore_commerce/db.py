from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .contracts import FulfillmentState, OrderCreateRequest, OrderState, PaymentState, ProductCode

SCHEMA = "commerce"
PAID_OUTBOX_TYPE = "order.paid.v1"


class PersistenceUnavailable(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
    pass


class EventIdentityConflict(RuntimeError):
    pass


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ORDER_STATES = tuple(x.value for x in OrderState)
PAYMENT_STATES = tuple(x.value for x in PaymentState)
FULFILLMENT_STATES = tuple(x.value for x in FulfillmentState)


def _sql_values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


class OrderRow(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(f"order_state IN ({_sql_values(ORDER_STATES)})", name="ck_orders_order_state"),
        CheckConstraint(f"payment_state IN ({_sql_values(PAYMENT_STATES)})", name="ck_orders_payment_state"),
        CheckConstraint(f"fulfillment_state IN ({_sql_values(FULFILLMENT_STATES)})", name="ck_orders_fulfillment_state"),
        {"schema": SCHEMA},
    )
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    product_code: Mapped[str] = mapped_column(String(64), nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    purchase_intent: Mapped[dict] = mapped_column(JSONB, nullable=False)
    canonical_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    order_state: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_state: Mapped[str] = mapped_column(String(40), nullable=False)
    fulfillment_state: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderIdempotencyRow(Base):
    __tablename__ = "order_idempotency"
    __table_args__ = (UniqueConstraint("order_id", name="uq_order_idempotency_order_id"), {"schema": SCHEMA})
    key_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CheckoutSessionRow(Base):
    __tablename__ = "checkout_sessions"
    __table_args__ = (
        UniqueConstraint("stripe_checkout_session_id", name="uq_checkout_sessions_stripe_id"),
        UniqueConstraint("provider_idempotency_key", name="uq_checkout_sessions_provider_key"),
        CheckConstraint("quantity = 1", name="ck_checkout_sessions_quantity_v1"),
        CheckConstraint("checkout_url IS NULL OR stripe_checkout_session_id IS NOT NULL", name="ck_checkout_sessions_url_requires_binding"),
        {"schema": SCHEMA},
    )
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), primary_key=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(32), nullable=False)
    product_code: Mapped[str] = mapped_column(String(64), nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    success_url: Mapped[str] = mapped_column(Text, nullable=False)
    cancel_url: Mapped[str] = mapped_column(Text, nullable=False)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkout_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_session_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    stripe_payment_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    stripe_livemode: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reconciliation_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StripeEventInboxRow(Base):
    __tablename__ = "stripe_event_inbox"
    __table_args__ = (
        CheckConstraint("processing_state IN ('received','processed','ignored','attention_required')", name="ck_stripe_event_inbox_state"),
        {"schema": SCHEMA},
    )
    stripe_event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    stripe_event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    stripe_object_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_api_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    livemode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_state: Mapped[str] = mapped_column(String(40), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)


class OutboxEventRow(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("order_id", "outbox_type", name="uq_outbox_order_type"),
        CheckConstraint("outbox_type = 'order.paid.v1'", name="ck_outbox_type_6_1"),
        {"schema": SCHEMA},
    )
    outbox_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), nullable=False)
    outbox_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_version: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommerceStore:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def provider_operation_key(order_id: UUID) -> str:
        return f"sitescore:checkout:v1:{order_id}"

    def get_or_create_order(self, *, candidate_order_id: UUID, key_digest: str, request: OrderCreateRequest, catalog_version: str, price_id: str, quantity: int, operation_version: str, checkout_success_url: str, checkout_cancel_url: str) -> UUID:
        request_hash = request.canonical_hash()
        try:
            with self.session_factory.begin() as session:
                existing = session.get(OrderIdempotencyRow, key_digest)
                if existing is not None:
                    if existing.canonical_request_hash != request_hash:
                        raise IdempotencyConflict("idempotency key was already used with a different request")
                    return existing.order_id
                order_id = candidate_order_id
                now = utcnow()
                session.add(OrderRow(order_id=order_id, product_code=ProductCode.LOCATION_REPORT_V1.value, catalog_version=catalog_version, customer_email=request.customer_email, purchase_intent=request.model_dump(mode="json"), canonical_request_hash=request_hash, order_state=OrderState.PENDING_PAYMENT.value, payment_state=PaymentState.PENDING.value, fulfillment_state=FulfillmentState.NOT_STARTED.value, created_at=now, updated_at=now))
                session.flush()
                session.add(OrderIdempotencyRow(key_digest=key_digest, canonical_request_hash=request_hash, order_id=order_id, created_at=now))
                session.flush()
                session.add(CheckoutSessionRow(order_id=order_id, provider_idempotency_key=self.provider_operation_key(order_id), operation_version=operation_version, catalog_version=catalog_version, product_code=ProductCode.LOCATION_REPORT_V1.value, stripe_price_id=price_id, quantity=quantity, customer_email=request.customer_email, success_url=checkout_success_url, cancel_url=checkout_cancel_url, created_at=now, updated_at=now))
                return order_id
        except IdempotencyConflict:
            raise
        except IntegrityError:
            try:
                with self.session_factory() as session:
                    existing = session.get(OrderIdempotencyRow, key_digest)
                    if existing is None:
                        raise PersistenceUnavailable("order idempotency race could not be reconciled")
                    if existing.canonical_request_hash != request_hash:
                        raise IdempotencyConflict("idempotency key was already used with a different request")
                    return existing.order_id
            except (IdempotencyConflict, PersistenceUnavailable):
                raise
            except SQLAlchemyError as exc:
                raise PersistenceUnavailable("commerce persistence is unavailable") from exc
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("commerce persistence is unavailable") from exc

    def load_order_and_checkout(self, order_id: UUID) -> tuple[OrderRow, CheckoutSessionRow]:
        try:
            with self.session_factory() as session:
                order = session.get(OrderRow, order_id)
                checkout = session.get(CheckoutSessionRow, order_id)
                if order is None or checkout is None:
                    raise PersistenceUnavailable("commerce order binding is unavailable")
                session.expunge(order)
                session.expunge(checkout)
                return order, checkout
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("commerce persistence is unavailable") from exc

    def bind_checkout(self, *, order_id: UUID, stripe_session_id: str, checkout_url: str, expires_at: datetime | None) -> CheckoutSessionRow:
        try:
            with self.session_factory.begin() as session:
                row = session.execute(select(CheckoutSessionRow).where(CheckoutSessionRow.order_id == order_id).with_for_update()).scalar_one()
                if row.stripe_checkout_session_id is not None:
                    if row.stripe_checkout_session_id != stripe_session_id:
                        raise PersistenceUnavailable("checkout binding invariant failed")
                    return row
                row.stripe_checkout_session_id = stripe_session_id
                row.checkout_url = checkout_url
                row.checkout_expires_at = expires_at
                row.updated_at = utcnow()
                session.flush()
                return row
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("commerce checkout binding could not be persisted") from exc

    def record_stripe_event(self, *, event: object, raw_body_sha256: str) -> None:
        now = utcnow()
        values = dict(
            stripe_event_id=event.event_id,
            stripe_event_type=event.event_type,
            stripe_object_id=event.checkout_session_id,
            event_api_version=event.api_version,
            livemode=event.livemode,
            event_created_at=event.created_at,
            raw_body_sha256=raw_body_sha256,
        )
        try:
            with self.session_factory.begin() as session:
                row = session.get(StripeEventInboxRow, event.event_id)
                if row is None:
                    session.add(StripeEventInboxRow(**values, processing_state="received", failure_code=None, received_at=now, processed_at=None, attempt_count=1))
                    return
                essential = (row.stripe_event_type, row.stripe_object_id, row.event_api_version, row.livemode, row.event_created_at, row.raw_body_sha256)
                incoming = (event.event_type, event.checkout_session_id, event.api_version, event.livemode, event.created_at, raw_body_sha256)
                if essential != incoming:
                    raise EventIdentityConflict("duplicate Stripe event identity conflicts with durable inbox")
                row.attempt_count += 1
        except EventIdentityConflict:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("Stripe event inbox is unavailable") from exc

    def get_event_state(self, event_id: str) -> str:
        try:
            with self.session_factory() as session:
                row = session.get(StripeEventInboxRow, event_id)
                if row is None:
                    raise PersistenceUnavailable("Stripe event inbox identity is unavailable")
                return row.processing_state
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("Stripe event inbox is unavailable") from exc

    def _finish_event(self, event_id: str, state: str, code: str | None) -> None:
        try:
            with self.session_factory.begin() as session:
                row = session.execute(select(StripeEventInboxRow).where(StripeEventInboxRow.stripe_event_id == event_id).with_for_update()).scalar_one()
                if row.processing_state == "processed":
                    return
                row.processing_state = state
                row.failure_code = code
                row.processed_at = utcnow()
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("Stripe event inbox update failed") from exc

    def mark_event_attention(self, event_id: str, code: str) -> None:
        self._finish_event(event_id, "attention_required", code)

    def mark_event_ignored(self, event_id: str, code: str) -> None:
        self._finish_event(event_id, "ignored", code)

    def apply_reconciliation(self, *, event_id: str, order_id: UUID, evidence: object, target: str) -> None:
        try:
            with self.session_factory.begin() as session:
                inbox = session.execute(select(StripeEventInboxRow).where(StripeEventInboxRow.stripe_event_id == event_id).with_for_update()).scalar_one()
                if inbox.processing_state == "processed":
                    return
                order = session.execute(select(OrderRow).where(OrderRow.order_id == order_id).with_for_update()).scalar_one()
                checkout = session.execute(select(CheckoutSessionRow).where(CheckoutSessionRow.order_id == order_id).with_for_update()).scalar_one()
                if checkout.stripe_checkout_session_id is not None and checkout.stripe_checkout_session_id != evidence.session_id:
                    inbox.processing_state = "attention_required"
                    inbox.failure_code = "local_session_binding_conflict"
                    inbox.processed_at = utcnow()
                    return
                if checkout.stripe_checkout_session_id is None:
                    checkout.stripe_checkout_session_id = evidence.session_id
                now = utcnow()
                checkout.stripe_payment_intent_id = evidence.payment_intent_id
                checkout.stripe_session_status = evidence.status
                checkout.stripe_payment_status = evidence.payment_status
                checkout.stripe_livemode = evidence.livemode
                checkout.reconciled_at = now
                checkout.last_reconciliation_event_id = event_id
                checkout.updated_at = now

                if target == "paid":
                    if order.order_state == OrderState.EXPIRED.value or order.payment_state == PaymentState.EXPIRED.value:
                        inbox.processing_state = "attention_required"
                        inbox.failure_code = "contradictory_terminal_payment_truth"
                        inbox.processed_at = now
                        return
                    if order.order_state == OrderState.PENDING_PAYMENT.value and order.payment_state == PaymentState.PENDING.value:
                        order.order_state = OrderState.PAID.value
                        order.payment_state = PaymentState.PAID.value
                        order.updated_at = now
                        existing = session.execute(select(OutboxEventRow).where(OutboxEventRow.order_id == order_id, OutboxEventRow.outbox_type == PAID_OUTBOX_TYPE)).scalar_one_or_none()
                        if existing is None:
                            session.add(OutboxEventRow(outbox_id=uuid4(), order_id=order_id, outbox_type=PAID_OUTBOX_TYPE, payload_version="1", payload={"order_id": str(order_id), "event_type": PAID_OUTBOX_TYPE, "payload_version": 1}, created_at=now, published_at=None))
                    elif order.order_state != OrderState.PAID.value or order.payment_state != PaymentState.PAID.value:
                        inbox.processing_state = "attention_required"
                        inbox.failure_code = "invalid_payment_state_transition"
                        inbox.processed_at = now
                        return
                elif target == "expired":
                    if order.order_state == OrderState.PAID.value or order.payment_state == PaymentState.PAID.value:
                        inbox.processing_state = "attention_required"
                        inbox.failure_code = "late_expiration_after_paid"
                        inbox.processed_at = now
                        return
                    if order.order_state == OrderState.PENDING_PAYMENT.value and order.payment_state == PaymentState.PENDING.value:
                        order.order_state = OrderState.EXPIRED.value
                        order.payment_state = PaymentState.EXPIRED.value
                        order.updated_at = now
                    elif order.order_state != OrderState.EXPIRED.value or order.payment_state != PaymentState.EXPIRED.value:
                        inbox.processing_state = "attention_required"
                        inbox.failure_code = "invalid_expiration_state_transition"
                        inbox.processed_at = now
                        return
                else:
                    raise PersistenceUnavailable("unsupported reconciliation target")
                inbox.processing_state = "processed"
                inbox.failure_code = None
                inbox.processed_at = now
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("payment reconciliation could not be persisted") from exc
