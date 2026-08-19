from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urljoin
from uuid import UUID

import httpx
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from .contracts import FulfillmentState, OrderState, PaymentState
from .db import Base, CheckoutSessionRow, CommerceStore, OrderRow, PersistenceUnavailable, SCHEMA, utcnow
from .settings import Settings

ANALYSIS_OPERATION_VERSION = "sitescore_analysis_v1"
REFUND_OPERATION_VERSION = "stripe_full_refund_v1"
ANALYSIS_PROVIDER_KEY_PREFIX = "sitescore:analysis:v1:"
REFUND_PROVIDER_KEY_PREFIX = "sitescore:refund:v1:"

ANALYSIS_STATES = frozenset({"queued", "running", "completed", "not_score_ready", "failed", "timed_out"})
REPORT_STATES = frozenset({"ready", "failed"})
REFUND_STATUSES = frozenset({"pending", "requires_action", "succeeded", "failed", "canceled"})
REFUND_REASONS = {
    FulfillmentState.NOT_SCORE_READY.value: "analysis_not_score_ready",
    FulfillmentState.ANALYSIS_FAILED.value: "analysis_failed",
    FulfillmentState.ANALYSIS_TIMED_OUT.value: "analysis_timed_out",
    FulfillmentState.REPORT_FAILED.value: "report_failed",
}
REFUND_REASON_STATES = {
    "analysis_not_score_ready": ("analysis", "not_score_ready"),
    "analysis_failed": ("analysis", "failed"),
    "analysis_timed_out": ("analysis", "timed_out"),
    "report_failed": ("report", "failed"),
}


class FulfillmentInvariantError(RuntimeError):
    pass


class FulfillmentNotFound(RuntimeError):
    pass


class AutomationUnauthorized(RuntimeError):
    pass


class SiteScoreProviderUnavailable(RuntimeError):
    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class RefundProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class AnalysisOperation:
    order_id: UUID
    target_id: str
    base_url: str
    operation_version: str
    idempotency_key: str
    request_json: dict[str, Any]
    request_sha256: str
    analysis_id: UUID | None
    analysis_state: str | None
    report_id: UUID | None
    report_state: str | None


@dataclass(frozen=True)
class AnalysisEvidence:
    analysis_id: UUID
    state: str


@dataclass(frozen=True)
class ReportEvidence:
    report_id: UUID
    analysis_id: UUID
    state: str


@dataclass(frozen=True)
class PaymentIntentEvidence:
    payment_intent_id: str
    amount_received: int
    currency: str
    livemode: bool
    metadata: dict[str, str]


@dataclass(frozen=True)
class RefundEvidence:
    refund_id: str
    payment_intent_id: str
    amount: int
    currency: str
    status: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class RefundOperation:
    order_id: UUID
    operation_version: str
    provider_idempotency_key: str
    eligibility_reason: str
    eligibility_resource_type: str
    eligibility_resource_id: UUID
    stripe_payment_intent_id: str
    original_amount_received: int
    currency: str

    @property
    def metadata(self) -> dict[str, str]:
        return {
            "sitescore_order_id": str(self.order_id),
            "sitescore_refund_operation": self.operation_version,
            "sitescore_refund_reason": self.eligibility_reason,
        }


@dataclass(frozen=True)
class AutomationStatus:
    order_id: UUID
    order_state: str
    payment_state: str
    fulfillment_state: str
    retryable: bool
    terminal: bool
    next_action: str


class SiteScoreGateway(Protocol):
    def submit_analysis(self, operation: AnalysisOperation) -> AnalysisEvidence: ...
    def get_analysis(self, *, base_url: str, analysis_id: UUID) -> AnalysisEvidence: ...
    def resolve_report(self, *, base_url: str, analysis_id: UUID) -> ReportEvidence: ...
    def get_report(self, *, base_url: str, report_id: UUID) -> ReportEvidence: ...


class RefundGateway(Protocol):
    def retrieve_payment_intent(self, payment_intent_id: str) -> PaymentIntentEvidence: ...
    def list_refunds(self, payment_intent_id: str) -> tuple[RefundEvidence, ...]: ...
    def create_refund(self, operation: RefundOperation) -> RefundEvidence: ...


class FulfillmentBindingRow(Base):
    __tablename__ = "fulfillment_bindings"
    __table_args__ = (
        UniqueConstraint("analysis_id", name="uq_fulfillment_bindings_analysis_id"),
        UniqueConstraint("report_id", name="uq_fulfillment_bindings_report_id"),
        CheckConstraint(
            "analysis_state IS NULL OR analysis_state IN ('queued','running','completed','not_score_ready','failed','timed_out')",
            name="ck_fulfillment_bindings_analysis_state",
        ),
        CheckConstraint(
            "report_state IS NULL OR report_state IN ('ready','failed')",
            name="ck_fulfillment_bindings_report_state",
        ),
        {"schema": SCHEMA},
    )
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), primary_key=True)
    sitescore_api_target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sitescore_api_base_url: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_operation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    analysis_request_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    analysis_request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    analysis_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    analysis_last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    report_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    report_last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefundEligibilityRow(Base):
    __tablename__ = "refund_eligibility"
    __table_args__ = (
        CheckConstraint(
            "eligibility_reason IN ('analysis_not_score_ready','analysis_failed','analysis_timed_out','report_failed')",
            name="ck_refund_eligibility_reason",
        ),
        CheckConstraint("resource_type IN ('analysis','report')", name="ck_refund_eligibility_resource_type"),
        CheckConstraint(
            "server_observed_terminal_state IN ('not_score_ready','failed','timed_out')",
            name="ck_refund_eligibility_terminal_state",
        ),
        {"schema": SCHEMA},
    )
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), primary_key=True)
    eligibility_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    server_observed_terminal_state: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sitescore_api_target_id: Mapped[str] = mapped_column(String(128), nullable=False)


class RefundOperationRow(Base):
    __tablename__ = "refund_operations"
    __table_args__ = (
        UniqueConstraint("provider_idempotency_key", name="uq_refund_operations_provider_key"),
        UniqueConstraint("stripe_refund_id", name="uq_refund_operations_stripe_refund_id"),
        CheckConstraint("operation_version = 'stripe_full_refund_v1'", name="ck_refund_operations_version"),
        CheckConstraint("original_amount_received > 0", name="ck_refund_operations_positive_amount"),
        CheckConstraint("currency = 'USD'", name="ck_refund_operations_currency"),
        CheckConstraint(
            "stripe_refund_status IS NULL OR stripe_refund_status IN ('pending','requires_action','succeeded','failed','canceled')",
            name="ck_refund_operations_status",
        ),
        {"schema": SCHEMA},
    )
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), primary_key=True)
    operation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    eligibility_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    eligibility_resource_type: Mapped[str] = mapped_column(String(16), nullable=False)
    eligibility_resource_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    stripe_payment_intent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    original_amount_received: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    stripe_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_refund_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    stripe_refund_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _analysis_request_from_order(order: OrderRow) -> dict[str, Any]:
    purchase = order.purchase_intent
    if not isinstance(purchase, dict):
        raise FulfillmentInvariantError("durable purchase intent is invalid")
    payload = purchase.get("analysis_request")
    if not isinstance(payload, dict):
        raise FulfillmentInvariantError("durable analysis request snapshot is unavailable")
    return json.loads(_canonical_json(payload))


def _analysis_provider_key(order_id: UUID) -> str:
    return f"{ANALYSIS_PROVIDER_KEY_PREFIX}{order_id}"


def _refund_provider_key(order_id: UUID) -> str:
    return f"{REFUND_PROVIDER_KEY_PREFIX}{order_id}"


def _operation_from_row(row: FulfillmentBindingRow) -> AnalysisOperation:
    return AnalysisOperation(
        order_id=row.order_id,
        target_id=row.sitescore_api_target_id,
        base_url=row.sitescore_api_base_url,
        operation_version=row.analysis_operation_version,
        idempotency_key=row.analysis_idempotency_key,
        request_json=json.loads(_canonical_json(row.analysis_request_json)),
        request_sha256=row.analysis_request_sha256,
        analysis_id=row.analysis_id,
        analysis_state=row.analysis_state,
        report_id=row.report_id,
        report_state=row.report_state,
    )


def _apply_analysis_state(order: OrderRow, state: str, now: datetime) -> None:
    if state == "queued":
        order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
        order.payment_state = PaymentState.PAID.value
        order.fulfillment_state = FulfillmentState.ANALYSIS_PENDING.value
    elif state == "running":
        order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
        order.payment_state = PaymentState.PAID.value
        order.fulfillment_state = FulfillmentState.ANALYSIS_RUNNING.value
    elif state == "completed":
        order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
        order.payment_state = PaymentState.PAID.value
        order.fulfillment_state = FulfillmentState.REPORT_PENDING.value
    elif state == "not_score_ready":
        order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
        order.payment_state = PaymentState.PAID.value
        order.fulfillment_state = FulfillmentState.NOT_SCORE_READY.value
    elif state == "failed":
        order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
        order.payment_state = PaymentState.PAID.value
        order.fulfillment_state = FulfillmentState.ANALYSIS_FAILED.value
    elif state == "timed_out":
        order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
        order.payment_state = PaymentState.PAID.value
        order.fulfillment_state = FulfillmentState.ANALYSIS_TIMED_OUT.value
    else:
        raise FulfillmentInvariantError("unknown SiteScore analysis state")
    order.updated_at = now


def _apply_report_state(order: OrderRow, state: str, now: datetime) -> None:
    order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
    order.payment_state = PaymentState.PAID.value
    if state == "ready":
        order.fulfillment_state = FulfillmentState.DELIVERY_PENDING.value
    elif state == "failed":
        order.fulfillment_state = FulfillmentState.REPORT_FAILED.value
    else:
        raise FulfillmentInvariantError("unknown SiteScore report state")
    order.updated_at = now


class FulfillmentStore:
    def __init__(self, commerce_store: CommerceStore):
        self._store = commerce_store
        self.session_factory = commerce_store.session_factory

    def _load_order_for_update(self, session: Any, order_id: UUID) -> OrderRow:
        order = session.execute(select(OrderRow).where(OrderRow.order_id == order_id).with_for_update()).scalar_one_or_none()
        if order is None:
            raise FulfillmentNotFound("order not found")
        return order

    def prepare_analysis_operation(self, *, order_id: UUID, settings: Settings) -> AnalysisOperation:
        try:
            with self.session_factory.begin() as session:
                order = self._load_order_for_update(session, order_id)
                if order.payment_state != PaymentState.PAID.value:
                    raise FulfillmentInvariantError("analysis requires a paid order")
                if order.order_state not in {OrderState.PAID.value, OrderState.FULFILLMENT_IN_PROGRESS.value}:
                    raise FulfillmentInvariantError("order state does not permit analysis")
                if order.fulfillment_state in {FulfillmentState.COMPLETED.value, FulfillmentState.DELIVERY_PENDING.value}:
                    raise FulfillmentInvariantError("fulfillment state does not permit analysis creation")

                existing = session.get(FulfillmentBindingRow, order_id)
                if existing is None:
                    payload = _analysis_request_from_order(order)
                    canonical = _canonical_json(payload)
                    now = utcnow()
                    values = dict(
                        order_id=order_id,
                        sitescore_api_target_id=settings.sitescore_api_target_id,
                        sitescore_api_base_url=settings.sitescore_api_base_url,
                        analysis_operation_version=ANALYSIS_OPERATION_VERSION,
                        analysis_idempotency_key=_analysis_provider_key(order_id),
                        analysis_request_json=payload,
                        analysis_request_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                        analysis_id=None,
                        analysis_state=None,
                        analysis_last_observed_at=None,
                        report_id=None,
                        report_state=None,
                        report_last_observed_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                    session.execute(
                        pg_insert(FulfillmentBindingRow)
                        .values(**values)
                        .on_conflict_do_nothing(index_elements=[FulfillmentBindingRow.order_id])
                    )
                    existing = session.execute(
                        select(FulfillmentBindingRow)
                        .where(FulfillmentBindingRow.order_id == order_id)
                        .with_for_update()
                    ).scalar_one()
                    if order.order_state == OrderState.PAID.value:
                        order.order_state = OrderState.FULFILLMENT_IN_PROGRESS.value
                        order.fulfillment_state = FulfillmentState.ANALYSIS_PENDING.value
                        order.updated_at = now

                operation = _operation_from_row(existing)
                if operation.operation_version != ANALYSIS_OPERATION_VERSION:
                    raise FulfillmentInvariantError("unsupported durable analysis operation version")
                if operation.idempotency_key != _analysis_provider_key(order_id):
                    raise FulfillmentInvariantError("analysis idempotency identity drift")
                canonical = _canonical_json(operation.request_json)
                if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != operation.request_sha256:
                    raise FulfillmentInvariantError("durable analysis request hash mismatch")
                if operation.request_json != _analysis_request_from_order(order):
                    raise FulfillmentInvariantError("durable analysis payload/order mismatch")
                return operation
        except (FulfillmentNotFound, FulfillmentInvariantError):
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("fulfillment persistence is unavailable") from exc

    def get_binding(self, order_id: UUID) -> AnalysisOperation | None:
        try:
            with self.session_factory() as session:
                row = session.get(FulfillmentBindingRow, order_id)
                if row is None:
                    return None
                return _operation_from_row(row)
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("fulfillment persistence is unavailable") from exc

    def bind_analysis(self, *, order_id: UUID, evidence: AnalysisEvidence) -> AnalysisOperation:
        if evidence.state not in ANALYSIS_STATES:
            raise FulfillmentInvariantError("unknown SiteScore analysis state")
        try:
            with self.session_factory.begin() as session:
                order = self._load_order_for_update(session, order_id)
                row = session.execute(select(FulfillmentBindingRow).where(FulfillmentBindingRow.order_id == order_id).with_for_update()).scalar_one_or_none()
                if row is None:
                    raise FulfillmentInvariantError("analysis operation snapshot is unavailable")
                if row.analysis_id is not None and row.analysis_id != evidence.analysis_id:
                    raise FulfillmentInvariantError("analysis binding conflict")
                row.analysis_id = evidence.analysis_id
                row.analysis_state = evidence.state
                now = utcnow()
                row.analysis_last_observed_at = now
                row.updated_at = now
                _apply_analysis_state(order, evidence.state, now)
                session.flush()
                return _operation_from_row(row)
        except (FulfillmentNotFound, FulfillmentInvariantError):
            raise
        except IntegrityError as exc:
            raise FulfillmentInvariantError("analysis identity is already bound to another order") from exc
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("analysis binding could not be persisted") from exc

    def bind_report(self, *, order_id: UUID, evidence: ReportEvidence) -> AnalysisOperation:
        if evidence.state not in REPORT_STATES:
            raise FulfillmentInvariantError("unknown SiteScore report state")
        try:
            with self.session_factory.begin() as session:
                order = self._load_order_for_update(session, order_id)
                row = session.execute(select(FulfillmentBindingRow).where(FulfillmentBindingRow.order_id == order_id).with_for_update()).scalar_one_or_none()
                if row is None or row.analysis_id is None or row.analysis_state != "completed":
                    raise FulfillmentInvariantError("report requires a completed bound analysis")
                if evidence.analysis_id != row.analysis_id:
                    raise FulfillmentInvariantError("report analysis binding mismatch")
                if row.report_id is not None and row.report_id != evidence.report_id:
                    raise FulfillmentInvariantError("report binding conflict")
                row.report_id = evidence.report_id
                row.report_state = evidence.state
                now = utcnow()
                row.report_last_observed_at = now
                row.updated_at = now
                _apply_report_state(order, evidence.state, now)
                session.flush()
                return _operation_from_row(row)
        except (FulfillmentNotFound, FulfillmentInvariantError):
            raise
        except IntegrityError as exc:
            raise FulfillmentInvariantError("report identity is already bound to another order") from exc
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("report binding could not be persisted") from exc

    def persist_refund_eligibility(
        self,
        *,
        order_id: UUID,
        reason: str,
        resource_type: str,
        resource_id: UUID,
        terminal_state: str,
    ) -> None:
        expected = REFUND_REASON_STATES.get(reason)
        if expected != (resource_type, terminal_state):
            raise FulfillmentInvariantError("refund eligibility evidence mismatch")
        try:
            with self.session_factory.begin() as session:
                order = self._load_order_for_update(session, order_id)
                binding = session.execute(select(FulfillmentBindingRow).where(FulfillmentBindingRow.order_id == order_id).with_for_update()).scalar_one_or_none()
                if binding is None:
                    raise FulfillmentInvariantError("refund eligibility requires a fulfillment binding")
                if order.order_state == OrderState.FULFILLED.value or order.fulfillment_state == FulfillmentState.COMPLETED.value:
                    raise FulfillmentInvariantError("fulfilled order is not automatically refundable")
                if order.payment_state not in {PaymentState.PAID.value, PaymentState.REFUND_PENDING.value, PaymentState.REFUND_FAILED.value}:
                    raise FulfillmentInvariantError("refund eligibility requires paid money authority")
                existing = session.get(RefundEligibilityRow, order_id)
                if existing is not None:
                    identity = (existing.eligibility_reason, existing.resource_type, existing.resource_id, existing.server_observed_terminal_state, existing.sitescore_api_target_id)
                    incoming = (reason, resource_type, resource_id, terminal_state, binding.sitescore_api_target_id)
                    if identity != incoming:
                        raise FulfillmentInvariantError("refund eligibility identity conflict")
                    return
                session.add(
                    RefundEligibilityRow(
                        order_id=order_id,
                        eligibility_reason=reason,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        server_observed_terminal_state=terminal_state,
                        observed_at=utcnow(),
                        sitescore_api_target_id=binding.sitescore_api_target_id,
                    )
                )
        except (FulfillmentNotFound, FulfillmentInvariantError):
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("refund eligibility could not be persisted") from exc

    def load_refund_context(self, order_id: UUID) -> tuple[OrderRow, CheckoutSessionRow, RefundEligibilityRow, RefundOperationRow | None]:
        try:
            with self.session_factory() as session:
                order = session.get(OrderRow, order_id)
                checkout = session.get(CheckoutSessionRow, order_id)
                eligibility = session.get(RefundEligibilityRow, order_id)
                operation = session.get(RefundOperationRow, order_id)
                if order is None:
                    raise FulfillmentNotFound("order not found")
                if checkout is None or eligibility is None:
                    raise FulfillmentInvariantError("refund context is incomplete")
                for obj in (order, checkout, eligibility, operation):
                    if obj is not None:
                        session.expunge(obj)
                return order, checkout, eligibility, operation
        except (FulfillmentNotFound, FulfillmentInvariantError):
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("refund context is unavailable") from exc

    def prepare_refund_operation(self, *, order_id: UUID, payment_intent: PaymentIntentEvidence) -> RefundOperation:
        try:
            with self.session_factory.begin() as session:
                order = self._load_order_for_update(session, order_id)
                checkout = session.execute(select(CheckoutSessionRow).where(CheckoutSessionRow.order_id == order_id).with_for_update()).scalar_one_or_none()
                eligibility = session.execute(select(RefundEligibilityRow).where(RefundEligibilityRow.order_id == order_id).with_for_update()).scalar_one_or_none()
                if checkout is None or eligibility is None:
                    raise FulfillmentInvariantError("refund operation prerequisites are unavailable")
                if order.order_state == OrderState.FULFILLED.value or order.fulfillment_state == FulfillmentState.COMPLETED.value:
                    raise FulfillmentInvariantError("fulfilled order is not automatically refundable")
                if checkout.stripe_payment_intent_id is None or checkout.stripe_payment_intent_id != payment_intent.payment_intent_id:
                    raise FulfillmentInvariantError("PaymentIntent binding mismatch")
                if payment_intent.amount_received <= 0 or payment_intent.currency != "USD":
                    raise FulfillmentInvariantError("PaymentIntent amount/currency invariant failed")
                existing = session.get(RefundOperationRow, order_id)
                if existing is None:
                    now = utcnow()
                    session.add(
                        RefundOperationRow(
                            order_id=order_id,
                            operation_version=REFUND_OPERATION_VERSION,
                            provider_idempotency_key=_refund_provider_key(order_id),
                            eligibility_reason=eligibility.eligibility_reason,
                            eligibility_resource_type=eligibility.resource_type,
                            eligibility_resource_id=eligibility.resource_id,
                            stripe_payment_intent_id=payment_intent.payment_intent_id,
                            original_amount_received=payment_intent.amount_received,
                            currency=payment_intent.currency,
                            stripe_refund_id=None,
                            stripe_refund_status=None,
                            stripe_refund_amount=None,
                            failure_code=None,
                            created_at=now,
                            updated_at=now,
                            last_reconciled_at=None,
                        )
                    )
                    session.flush()
                    existing = session.get(RefundOperationRow, order_id)
                if existing is None:
                    raise PersistenceUnavailable("refund operation could not be materialized")
                identity = (
                    existing.operation_version,
                    existing.provider_idempotency_key,
                    existing.eligibility_reason,
                    existing.eligibility_resource_type,
                    existing.eligibility_resource_id,
                    existing.stripe_payment_intent_id,
                    existing.original_amount_received,
                    existing.currency,
                )
                expected = (
                    REFUND_OPERATION_VERSION,
                    _refund_provider_key(order_id),
                    eligibility.eligibility_reason,
                    eligibility.resource_type,
                    eligibility.resource_id,
                    payment_intent.payment_intent_id,
                    payment_intent.amount_received,
                    payment_intent.currency,
                )
                if identity != expected:
                    raise FulfillmentInvariantError("durable refund operation identity conflict")
                return RefundOperation(
                    order_id=order_id,
                    operation_version=existing.operation_version,
                    provider_idempotency_key=existing.provider_idempotency_key,
                    eligibility_reason=existing.eligibility_reason,
                    eligibility_resource_type=existing.eligibility_resource_type,
                    eligibility_resource_id=existing.eligibility_resource_id,
                    stripe_payment_intent_id=existing.stripe_payment_intent_id,
                    original_amount_received=existing.original_amount_received,
                    currency=existing.currency,
                )
        except (FulfillmentNotFound, FulfillmentInvariantError, PersistenceUnavailable):
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("refund operation could not be persisted") from exc

    def bind_refund(self, *, operation: RefundOperation, evidence: RefundEvidence, external_full: bool = False) -> None:
        if evidence.status not in REFUND_STATUSES:
            raise FulfillmentInvariantError("unknown Stripe Refund status")
        if evidence.payment_intent_id != operation.stripe_payment_intent_id:
            raise FulfillmentInvariantError("Refund PaymentIntent mismatch")
        if evidence.amount != operation.original_amount_received or evidence.currency != operation.currency:
            raise FulfillmentInvariantError("Refund amount/currency mismatch")
        if not external_full:
            for key, expected in operation.metadata.items():
                if evidence.metadata.get(key) != expected:
                    raise FulfillmentInvariantError("Refund metadata binding mismatch")
        try:
            with self.session_factory.begin() as session:
                order = self._load_order_for_update(session, operation.order_id)
                row = session.execute(select(RefundOperationRow).where(RefundOperationRow.order_id == operation.order_id).with_for_update()).scalar_one_or_none()
                if row is None:
                    raise FulfillmentInvariantError("refund operation snapshot is unavailable")
                if row.stripe_refund_id is not None and row.stripe_refund_id != evidence.refund_id:
                    raise FulfillmentInvariantError("refund binding conflict")
                row.stripe_refund_id = evidence.refund_id or row.stripe_refund_id
                row.stripe_refund_status = evidence.status
                row.stripe_refund_amount = evidence.amount
                row.failure_code = "provider_already_fully_refunded" if external_full else None
                now = utcnow()
                row.updated_at = now
                row.last_reconciled_at = now
                if evidence.status == "succeeded":
                    order.order_state = OrderState.REFUNDED.value
                    order.payment_state = PaymentState.REFUNDED.value
                elif evidence.status == "pending":
                    order.payment_state = PaymentState.REFUND_PENDING.value
                elif evidence.status == "requires_action":
                    order.order_state = OrderState.ATTENTION_REQUIRED.value
                    order.payment_state = PaymentState.REFUND_PENDING.value
                elif evidence.status in {"failed", "canceled"}:
                    order.order_state = OrderState.ATTENTION_REQUIRED.value
                    order.payment_state = PaymentState.REFUND_FAILED.value
                    row.failure_code = f"stripe_refund_{evidence.status}"
                order.updated_at = now
        except (FulfillmentNotFound, FulfillmentInvariantError):
            raise
        except IntegrityError as exc:
            raise FulfillmentInvariantError("Stripe Refund identity is already bound to another order") from exc
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("refund reconciliation could not be persisted") from exc

    def mark_attention(self, *, order_id: UUID, code: str, refund_failure: bool = False) -> None:
        try:
            with self.session_factory.begin() as session:
                order = self._load_order_for_update(session, order_id)
                order.order_state = OrderState.ATTENTION_REQUIRED.value
                if refund_failure:
                    order.payment_state = PaymentState.REFUND_FAILED.value
                order.updated_at = utcnow()
                operation = session.get(RefundOperationRow, order_id)
                if operation is not None:
                    operation.failure_code = code[:80]
                    operation.updated_at = utcnow()
        except FulfillmentNotFound:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("attention state could not be persisted") from exc

    def get_status(self, order_id: UUID) -> AutomationStatus:
        try:
            with self.session_factory() as session:
                order = session.get(OrderRow, order_id)
                if order is None:
                    raise FulfillmentNotFound("order not found")
                state = order.fulfillment_state
                terminal = order.order_state in {OrderState.REFUNDED.value, OrderState.FULFILLED.value, OrderState.EXPIRED.value}
                if state == FulfillmentState.DELIVERY_PENDING.value:
                    next_action = "delivery"
                    retryable = False
                elif state in REFUND_REASONS:
                    next_action = "refund"
                    retryable = True
                elif terminal or order.order_state == OrderState.ATTENTION_REQUIRED.value:
                    next_action = "none"
                    retryable = False
                elif order.payment_state == PaymentState.PAID.value:
                    next_action = "advance"
                    retryable = True
                else:
                    next_action = "wait"
                    retryable = False
                return AutomationStatus(
                    order_id=order.order_id,
                    order_state=order.order_state,
                    payment_state=order.payment_state,
                    fulfillment_state=order.fulfillment_state,
                    retryable=retryable,
                    terminal=terminal,
                    next_action=next_action,
                )
        except FulfillmentNotFound:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("fulfillment status is unavailable") from exc


class SiteScoreHttpGateway:
    def __init__(self, settings: Settings):
        self._service_key = settings.sitescore_api_service_key
        self._timeout = settings.sitescore_api_timeout_seconds

    def _request(self, method: str, *, base_url: str, path: str, json_body: dict[str, Any] | None = None, idempotency_key: str | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._service_key}", "Accept": "application/json"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        try:
            response = httpx.request(method, url, headers=headers, json=json_body, timeout=self._timeout)
        except httpx.RequestError as exc:
            raise SiteScoreProviderUnavailable("sitescore_network_error", retryable=True) from exc
        if response.status_code < 200 or response.status_code >= 300:
            if response.status_code in {429, 500, 502, 503, 504}:
                raise SiteScoreProviderUnavailable("sitescore_retryable_http_error", retryable=True)
            if response.status_code == 404:
                raise SiteScoreProviderUnavailable("sitescore_resource_not_found", retryable=False)
            if response.status_code in {401, 403}:
                raise SiteScoreProviderUnavailable("sitescore_auth_error", retryable=False)
            raise SiteScoreProviderUnavailable("sitescore_http_error", retryable=False)
        try:
            data = response.json()
        except ValueError as exc:
            raise SiteScoreProviderUnavailable("sitescore_malformed_response", retryable=False) from exc
        if not isinstance(data, dict):
            raise SiteScoreProviderUnavailable("sitescore_malformed_response", retryable=False)
        return data

    @staticmethod
    def _uuid(value: object, code: str) -> UUID:
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise SiteScoreProviderUnavailable(code, retryable=False) from exc

    @staticmethod
    def _api_v1(data: dict[str, Any]) -> None:
        if data.get("api_version") != "v1":
            raise SiteScoreProviderUnavailable("sitescore_api_version_mismatch", retryable=False)

    def _analysis(self, data: dict[str, Any], *, expected_id: UUID | None = None) -> AnalysisEvidence:
        self._api_v1(data)
        analysis_id = self._uuid(data.get("analysis_id"), "sitescore_analysis_id_invalid")
        state = str(data.get("state", ""))
        if state not in ANALYSIS_STATES:
            raise SiteScoreProviderUnavailable("sitescore_analysis_state_unknown", retryable=False)
        if expected_id is not None and analysis_id != expected_id:
            raise SiteScoreProviderUnavailable("sitescore_analysis_id_mismatch", retryable=False)
        return AnalysisEvidence(analysis_id=analysis_id, state=state)

    def submit_analysis(self, operation: AnalysisOperation) -> AnalysisEvidence:
        if operation.operation_version != ANALYSIS_OPERATION_VERSION:
            raise FulfillmentInvariantError("unsupported analysis operation version")
        data = self._request(
            "POST",
            base_url=operation.base_url,
            path="/v1/analyses",
            json_body=operation.request_json,
            idempotency_key=operation.idempotency_key,
        )
        return self._analysis(data, expected_id=operation.analysis_id)

    def get_analysis(self, *, base_url: str, analysis_id: UUID) -> AnalysisEvidence:
        return self._analysis(self._request("GET", base_url=base_url, path=f"/v1/analyses/{analysis_id}"), expected_id=analysis_id)

    def _report(self, data: dict[str, Any], *, expected_analysis_id: UUID, expected_report_id: UUID | None = None) -> ReportEvidence:
        self._api_v1(data)
        report_id = self._uuid(data.get("report_id"), "sitescore_report_id_invalid")
        analysis_id = self._uuid(data.get("analysis_id"), "sitescore_report_analysis_id_invalid")
        state = str(data.get("state", ""))
        if state not in REPORT_STATES:
            raise SiteScoreProviderUnavailable("sitescore_report_state_unknown", retryable=False)
        if analysis_id != expected_analysis_id:
            raise SiteScoreProviderUnavailable("sitescore_report_analysis_id_mismatch", retryable=False)
        if expected_report_id is not None and report_id != expected_report_id:
            raise SiteScoreProviderUnavailable("sitescore_report_id_mismatch", retryable=False)
        return ReportEvidence(report_id=report_id, analysis_id=analysis_id, state=state)

    def resolve_report(self, *, base_url: str, analysis_id: UUID) -> ReportEvidence:
        data = self._request("POST", base_url=base_url, path="/v1/reports", json_body={"analysis_id": str(analysis_id)})
        return self._report(data, expected_analysis_id=analysis_id)

    def get_report(self, *, base_url: str, report_id: UUID) -> ReportEvidence:
        data = self._request("GET", base_url=base_url, path=f"/v1/reports/{report_id}")
        analysis_id = self._uuid(data.get("analysis_id"), "sitescore_report_analysis_id_invalid")
        return self._report(data, expected_analysis_id=analysis_id, expected_report_id=report_id)


def _stripe_id(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(getattr(value, "id", ""))


class StripeRefundGateway:
    def __init__(self, settings: Settings):
        from stripe import StripeClient
        self._client = StripeClient(settings.stripe_secret_key)
        self._api_version = settings.stripe_api_version

    @property
    def _options(self) -> dict[str, str]:
        return {"stripe_version": self._api_version}

    @staticmethod
    def _metadata(obj: Any) -> dict[str, str]:
        return {str(k): str(v) for k, v in dict(getattr(obj, "metadata", {}) or {}).items()}

    def retrieve_payment_intent(self, payment_intent_id: str) -> PaymentIntentEvidence:
        try:
            obj = self._client.v1.payment_intents.retrieve(payment_intent_id, options=self._options)
        except Exception as exc:
            raise RefundProviderUnavailable("Stripe PaymentIntent reconciliation is unavailable") from exc
        return PaymentIntentEvidence(
            payment_intent_id=str(getattr(obj, "id", "")),
            amount_received=int(getattr(obj, "amount_received", 0) or 0),
            currency=str(getattr(obj, "currency", "") or "").upper(),
            livemode=bool(getattr(obj, "livemode", False)),
            metadata=self._metadata(obj),
        )

    def _refund(self, obj: Any) -> RefundEvidence:
        return RefundEvidence(
            refund_id=str(getattr(obj, "id", "")),
            payment_intent_id=_stripe_id(getattr(obj, "payment_intent", None)),
            amount=int(getattr(obj, "amount", 0) or 0),
            currency=str(getattr(obj, "currency", "") or "").upper(),
            status=str(getattr(obj, "status", "") or ""),
            metadata=self._metadata(obj),
        )

    def list_refunds(self, payment_intent_id: str) -> tuple[RefundEvidence, ...]:
        try:
            page = self._client.v1.refunds.list(params={"payment_intent": payment_intent_id, "limit": 100}, options=self._options)
        except Exception as exc:
            raise RefundProviderUnavailable("Stripe Refund reconciliation is unavailable") from exc
        return tuple(self._refund(item) for item in list(getattr(page, "data", []) or []))

    def create_refund(self, operation: RefundOperation) -> RefundEvidence:
        params = {
            "payment_intent": operation.stripe_payment_intent_id,
            "amount": operation.original_amount_received,
            "metadata": operation.metadata,
        }
        options = {"stripe_version": self._api_version, "idempotency_key": operation.provider_idempotency_key}
        try:
            obj = self._client.v1.refunds.create(params=params, options=options)
        except Exception as exc:
            raise RefundProviderUnavailable("Stripe Refund creation is unavailable") from exc
        return self._refund(obj)


def validate_payment_intent(*, evidence: PaymentIntentEvidence, order: OrderRow, checkout: CheckoutSessionRow, expected_livemode: bool) -> None:
    if not evidence.payment_intent_id.startswith("pi_"):
        raise FulfillmentInvariantError("PaymentIntent identity is invalid")
    if checkout.stripe_payment_intent_id != evidence.payment_intent_id:
        raise FulfillmentInvariantError("PaymentIntent does not match durable checkout binding")
    if evidence.currency != "USD" or evidence.amount_received <= 0:
        raise FulfillmentInvariantError("PaymentIntent money evidence is invalid")
    if evidence.livemode is not expected_livemode:
        raise FulfillmentInvariantError("PaymentIntent livemode mismatch")
    if evidence.metadata.get("sitescore_order_id") != str(order.order_id):
        raise FulfillmentInvariantError("PaymentIntent order metadata mismatch")
    if evidence.metadata.get("sitescore_product_code") != order.product_code:
        raise FulfillmentInvariantError("PaymentIntent product metadata mismatch")


def validate_refund_for_operation(evidence: RefundEvidence, operation: RefundOperation, *, require_metadata: bool) -> None:
    if not evidence.refund_id.startswith("re_"):
        raise FulfillmentInvariantError("Refund identity is invalid")
    if evidence.status not in REFUND_STATUSES:
        raise FulfillmentInvariantError("unknown Stripe Refund status")
    if evidence.payment_intent_id != operation.stripe_payment_intent_id:
        raise FulfillmentInvariantError("Refund PaymentIntent mismatch")
    if evidence.amount != operation.original_amount_received or evidence.currency != operation.currency:
        raise FulfillmentInvariantError("Refund money binding mismatch")
    if require_metadata:
        for key, expected in operation.metadata.items():
            if evidence.metadata.get(key) != expected:
                raise FulfillmentInvariantError("Refund metadata binding mismatch")


def _is_matching_refund(refund: RefundEvidence, operation: RefundOperation) -> bool:
    return all(refund.metadata.get(k) == v for k, v in operation.metadata.items())


@dataclass
class FulfillmentService:
    settings: Settings
    store: FulfillmentStore
    sitescore: SiteScoreGateway
    refunds: RefundGateway

    def authorize_automation(self, authorization: str | None) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise AutomationUnauthorized("automation credential required")
        supplied = authorization[7:]
        if not supplied or not hmac.compare_digest(supplied, self.settings.commerce_automation_api_key):
            raise AutomationUnauthorized("automation credential invalid")

    def status(self, order_id: UUID) -> AutomationStatus:
        return self.store.get_status(order_id)

    def advance(self, order_id: UUID) -> AutomationStatus:
        status = self.store.get_status(order_id)
        if status.order_state in {OrderState.REFUNDED.value, OrderState.FULFILLED.value, OrderState.EXPIRED.value, OrderState.ATTENTION_REQUIRED.value}:
            return status
        if status.payment_state != PaymentState.PAID.value and status.fulfillment_state not in REFUND_REASONS:
            return status
        if status.fulfillment_state == FulfillmentState.NOT_STARTED.value:
            self._ensure_analysis(order_id)
        elif status.fulfillment_state in {FulfillmentState.ANALYSIS_PENDING.value, FulfillmentState.ANALYSIS_RUNNING.value}:
            self._reconcile_analysis(order_id)
        elif status.fulfillment_state == FulfillmentState.REPORT_PENDING.value:
            self._ensure_report(order_id)
        elif status.fulfillment_state in REFUND_REASONS:
            self._ensure_refund(order_id, status.fulfillment_state)
        return self.store.get_status(order_id)

    def _ensure_analysis(self, order_id: UUID) -> None:
        operation = self.store.prepare_analysis_operation(order_id=order_id, settings=self.settings)
        evidence = self.sitescore.submit_analysis(operation)
        self.store.bind_analysis(order_id=order_id, evidence=evidence)

    def _reconcile_analysis(self, order_id: UUID) -> None:
        operation = self.store.get_binding(order_id)
        if operation is None or operation.analysis_id is None:
            raise FulfillmentInvariantError("bound analysis is unavailable")
        evidence = self.sitescore.get_analysis(base_url=operation.base_url, analysis_id=operation.analysis_id)
        self.store.bind_analysis(order_id=order_id, evidence=evidence)

    def _ensure_report(self, order_id: UUID) -> None:
        operation = self.store.get_binding(order_id)
        if operation is None or operation.analysis_id is None or operation.analysis_state != "completed":
            raise FulfillmentInvariantError("completed bound analysis is required")
        if operation.report_id is None:
            evidence = self.sitescore.resolve_report(base_url=operation.base_url, analysis_id=operation.analysis_id)
        else:
            evidence = self.sitescore.get_report(base_url=operation.base_url, report_id=operation.report_id)
            if evidence.analysis_id != operation.analysis_id:
                raise FulfillmentInvariantError("report analysis binding mismatch")
        self.store.bind_report(order_id=order_id, evidence=evidence)

    def _reprove_eligibility(self, order_id: UUID, fulfillment_state: str) -> tuple[str, str, UUID, str]:
        reason = REFUND_REASONS.get(fulfillment_state)
        if reason is None:
            raise FulfillmentInvariantError("fulfillment state is not refundable")
        operation = self.store.get_binding(order_id)
        if operation is None:
            raise FulfillmentInvariantError("fulfillment binding is unavailable")
        resource_type, terminal_state = REFUND_REASON_STATES[reason]
        if resource_type == "analysis":
            if operation.analysis_id is None:
                raise FulfillmentInvariantError("analysis refund evidence is unavailable")
            evidence = self.sitescore.get_analysis(base_url=operation.base_url, analysis_id=operation.analysis_id)
            if evidence.state != terminal_state:
                raise FulfillmentInvariantError("analysis terminal refund truth changed")
            return reason, resource_type, operation.analysis_id, terminal_state
        if operation.report_id is None:
            raise FulfillmentInvariantError("report refund evidence is unavailable")
        report = self.sitescore.get_report(base_url=operation.base_url, report_id=operation.report_id)
        if report.analysis_id != operation.analysis_id or report.state != terminal_state:
            raise FulfillmentInvariantError("report terminal refund truth changed")
        return reason, resource_type, operation.report_id, terminal_state

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
        if len(matching) > 1:
            self.store.mark_attention(order_id=order_id, code="multiple_matching_refunds", refund_failure=True)
            return
        if matching:
            try:
                validate_refund_for_operation(matching[0], operation, require_metadata=True)
                self.store.bind_refund(operation=operation, evidence=matching[0])
            except FulfillmentInvariantError:
                self.store.mark_attention(order_id=order_id, code="matching_refund_conflict", refund_failure=True)
            return

        if provider_refunds:
            valid_same_pi = [r for r in provider_refunds if r.payment_intent_id == operation.stripe_payment_intent_id and r.currency == operation.currency and r.amount > 0]
            if len(valid_same_pi) == 1 and valid_same_pi[0].status == "succeeded" and valid_same_pi[0].amount == operation.original_amount_received:
                self.store.bind_refund(operation=operation, evidence=valid_same_pi[0], external_full=True)
                return
            self.store.mark_attention(order_id=order_id, code="conflicting_existing_refund", refund_failure=True)
            return

        try:
            evidence = self.refunds.create_refund(operation)
            validate_refund_for_operation(evidence, operation, require_metadata=True)
            self.store.bind_refund(operation=operation, evidence=evidence)
        except FulfillmentInvariantError:
            self.store.mark_attention(order_id=order_id, code="refund_provider_binding_mismatch", refund_failure=True)


def build_fulfillment_service(settings: Settings, commerce_store: CommerceStore) -> FulfillmentService:
    store = FulfillmentStore(commerce_store)
    return FulfillmentService(settings=settings, store=store, sitescore=SiteScoreHttpGateway(settings), refunds=StripeRefundGateway(settings))
