from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .contracts import FulfillmentState, OrderCreateRequest, OrderState, PaymentState, ProductCode

SCHEMA = "commerce"


class PersistenceUnavailable(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
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
        CheckConstraint("(stripe_checkout_session_id IS NULL AND checkout_url IS NULL) OR (stripe_checkout_session_id IS NOT NULL AND checkout_url IS NOT NULL)", name="ck_checkout_sessions_binding_pair"),
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommerceStore:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def provider_operation_key(order_id: UUID) -> str:
        return f"sitescore:checkout:v1:{order_id}"

    def get_or_create_order(
        self,
        *,
        key_digest: str,
        request: OrderCreateRequest,
        catalog_version: str,
        price_id: str,
        quantity: int,
        operation_version: str,
        checkout_success_url: str,
        checkout_cancel_url: str,
    ) -> UUID:
        request_hash = request.canonical_hash()
        try:
            with self.session_factory.begin() as session:
                existing = session.get(OrderIdempotencyRow, key_digest)
                if existing is not None:
                    if existing.canonical_request_hash != request_hash:
                        raise IdempotencyConflict("idempotency key was already used with a different request")
                    return existing.order_id
                order_id = uuid4()
                now = utcnow()
                session.add(OrderRow(order_id=order_id, product_code=ProductCode.LOCATION_REPORT_V1.value, catalog_version=catalog_version, customer_email=request.customer_email, purchase_intent=request.model_dump(mode="json"), canonical_request_hash=request_hash, order_state=OrderState.PENDING_PAYMENT.value, payment_state=PaymentState.PENDING.value, fulfillment_state=FulfillmentState.NOT_STARTED.value, created_at=now, updated_at=now))
                # No ORM relationships are defined between these persistence rows on purpose.
                # Flush the parent explicitly so PostgreSQL FK ordering is deterministic,
                # then flush the idempotency claim so concurrent losers fail before a
                # checkout-operation row is authored. All three writes remain in one DB transaction.
                session.flush()
                session.add(OrderIdempotencyRow(key_digest=key_digest, canonical_request_hash=request_hash, order_id=order_id, created_at=now))
                session.flush()
                session.add(CheckoutSessionRow(
                    order_id=order_id,
                    provider_idempotency_key=self.provider_operation_key(order_id),
                    operation_version=operation_version,
                    catalog_version=catalog_version,
                    product_code=ProductCode.LOCATION_REPORT_V1.value,
                    stripe_price_id=price_id,
                    quantity=quantity,
                    customer_email=request.customer_email,
                    success_url=checkout_success_url,
                    cancel_url=checkout_cancel_url,
                    created_at=now,
                    updated_at=now,
                ))
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
