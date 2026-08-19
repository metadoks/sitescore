from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePath
from typing import Any
from urllib.parse import urljoin
from uuid import UUID, uuid4

import httpx
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from .contracts import FulfillmentState, OrderState, PaymentState
from .db import Base, CommerceStore, OrderRow, PersistenceUnavailable, SCHEMA, utcnow
from .fulfillment import FulfillmentBindingRow, FulfillmentInvariantError, FulfillmentNotFound
from .settings import Settings

POSTMARK_ENDPOINT = "https://api.postmarkapp.com/email/withTemplate"
POSTMARK_PROVIDER = "postmark"
POSTMARK_MESSAGE_STREAM = "outbound"
DELIVERY_GRANT_TTL = timedelta(days=7)
DELIVERY_MAX_ATTEMPTS = 3
TOKEN_BYTES = 32
TOKEN_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,126}\.pdf$")
ATTEMPT_STATUSES = frozenset({"prepared", "dispatch_started", "provider_accepted", "provider_rejected", "provider_uncertain"})


class DeliveryInvariantError(RuntimeError):
    pass


class DeliveryCapabilityUnavailable(RuntimeError):
    pass


class DeliveryUpstreamUnavailable(RuntimeError):
    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class PostmarkRejected(RuntimeError):
    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code[:80]
        self.retryable = retryable


class PostmarkUncertain(RuntimeError):
    def __init__(self, code: str = "postmark_transport_uncertain"):
        super().__init__(code)
        self.code = code[:80]


@dataclass(frozen=True)
class DeliveryContext:
    order_id: UUID
    customer_email: str
    order_state: str
    payment_state: str
    fulfillment_state: str
    analysis_id: UUID
    analysis_state: str
    report_id: UUID
    report_state: str
    sitescore_api_base_url: str


@dataclass(frozen=True)
class ReportResourceEvidence:
    report_id: UUID
    analysis_id: UUID
    state: str
    content_sha256: str
    mime_type: str
    filename: str
    byte_length: int


@dataclass(frozen=True)
class PreparedDeliveryAttempt:
    delivery_attempt_id: UUID
    grant_id: UUID
    order_id: UUID
    report_id: UUID
    recipient: str
    template_alias: str
    attempt_number: int
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class PostmarkAcceptance:
    message_id: str
    submitted_at: datetime
    recipient: str


@dataclass(frozen=True)
class DownloadPayload:
    content: bytes
    filename: str
    content_sha256: str


class DeliveryGrantRow(Base):
    __tablename__ = "delivery_grants"
    __table_args__ = (
        UniqueConstraint("token_digest", name="uq_delivery_grants_token_digest"),
        CheckConstraint("token_digest ~ '^[0-9a-f]{64}$'", name="ck_delivery_grants_digest_shape"),
        CheckConstraint("expires_at > issued_at", name="ck_delivery_grants_expiry_after_issue"),
        CheckConstraint("revoked_at IS NULL OR revoked_at >= issued_at", name="ck_delivery_grants_revocation_time"),
        {"schema": SCHEMA},
    )
    grant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), nullable=False)
    report_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeliveryAttemptRow(Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (
        UniqueConstraint("order_id", "attempt_number", name="uq_delivery_attempts_order_number"),
        UniqueConstraint("provider_message_id", name="uq_delivery_attempts_provider_message_id"),
        CheckConstraint("provider = 'postmark'", name="ck_delivery_attempts_provider"),
        CheckConstraint("attempt_number > 0", name="ck_delivery_attempts_positive_number"),
        CheckConstraint(
            "status IN ('prepared','dispatch_started','provider_accepted','provider_rejected','provider_uncertain')",
            name="ck_delivery_attempts_status",
        ),
        {"schema": SCHEMA},
    )
    delivery_attempt_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.orders.order_id"), nullable=False)
    report_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    grant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.delivery_grants.grant_id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    template_alias: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def token_digest(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("ascii")).hexdigest()


def generate_delivery_token() -> str:
    # token_urlsafe(32) is backed by 32 uniformly random bytes = 256 bits of entropy.
    return secrets.token_urlsafe(TOKEN_BYTES)


def _uuid(value: object, code: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise DeliveryUpstreamUnavailable(code, retryable=False) from exc


def _safe_filename(value: object) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > 128:
        raise DeliveryUpstreamUnavailable("sitescore_report_filename_invalid", retryable=False)
    if PurePath(value).name != value or "/" in value or "\\" in value or SAFE_FILENAME_RE.fullmatch(value) is None:
        raise DeliveryUpstreamUnavailable("sitescore_report_filename_invalid", retryable=False)
    return value


def _parse_provider_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PostmarkRejected("postmark_submitted_at_invalid", retryable=False)
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PostmarkRejected("postmark_submitted_at_invalid", retryable=False) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PostmarkRejected("postmark_submitted_at_invalid", retryable=False)
    return parsed.astimezone(timezone.utc)


class DeliveryStore:
    def __init__(self, commerce_store: CommerceStore):
        self.session_factory = commerce_store.session_factory

    @staticmethod
    def _context(order: OrderRow, binding: FulfillmentBindingRow) -> DeliveryContext:
        if binding.analysis_id is None or binding.report_id is None:
            raise DeliveryInvariantError("delivery binding is incomplete")
        return DeliveryContext(
            order_id=order.order_id,
            customer_email=order.customer_email,
            order_state=order.order_state,
            payment_state=order.payment_state,
            fulfillment_state=order.fulfillment_state,
            analysis_id=binding.analysis_id,
            analysis_state=binding.analysis_state or "",
            report_id=binding.report_id,
            report_state=binding.report_state or "",
            sitescore_api_base_url=binding.sitescore_api_base_url,
        )

    @staticmethod
    def _validate_ready_context(order: OrderRow, binding: FulfillmentBindingRow, *, require_pending: bool) -> None:
        if order.payment_state != PaymentState.PAID.value:
            raise DeliveryInvariantError("delivery requires paid payment authority")
        if binding.analysis_id is None or binding.analysis_state != "completed":
            raise DeliveryInvariantError("delivery requires exact completed bound analysis")
        if binding.report_id is None or binding.report_state != "ready":
            raise DeliveryInvariantError("delivery requires exact ready bound report")
        if require_pending:
            if order.order_state != OrderState.FULFILLMENT_IN_PROGRESS.value or order.fulfillment_state != FulfillmentState.DELIVERY_PENDING.value:
                raise DeliveryInvariantError("order is not delivery pending")
        elif order.fulfillment_state not in {
            FulfillmentState.DELIVERY_PENDING.value,
            FulfillmentState.COMPLETED.value,
            FulfillmentState.DELIVERY_FAILED.value,
        }:
            raise DeliveryCapabilityUnavailable("delivery capability is unavailable")

    def load_context(self, order_id: UUID) -> DeliveryContext:
        try:
            with self.session_factory() as session:
                order = session.get(OrderRow, order_id)
                binding = session.get(FulfillmentBindingRow, order_id)
                if order is None:
                    raise FulfillmentNotFound("order not found")
                if binding is None:
                    raise DeliveryInvariantError("fulfillment binding is unavailable")
                self._validate_ready_context(order, binding, require_pending=True)
                return self._context(order, binding)
        except (FulfillmentNotFound, DeliveryInvariantError):
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("delivery context is unavailable") from exc

    def converge_known_acceptance(self, order_id: UUID) -> bool:
        try:
            with self.session_factory.begin() as session:
                order = session.execute(select(OrderRow).where(OrderRow.order_id == order_id).with_for_update()).scalar_one_or_none()
                if order is None:
                    raise FulfillmentNotFound("order not found")
                accepted = session.execute(
                    select(DeliveryAttemptRow)
                    .where(DeliveryAttemptRow.order_id == order_id, DeliveryAttemptRow.status == "provider_accepted")
                    .order_by(DeliveryAttemptRow.attempt_number.asc())
                    .limit(1)
                    .with_for_update()
                ).scalar_one_or_none()
                if accepted is None:
                    return False
                grant = session.get(DeliveryGrantRow, accepted.grant_id)
                binding = session.get(FulfillmentBindingRow, order_id)
                if grant is None or binding is None:
                    raise DeliveryInvariantError("accepted delivery evidence is incomplete")
                if accepted.provider_message_id is None or accepted.provider_submitted_at is None:
                    raise DeliveryInvariantError("accepted provider evidence is incomplete")
                if grant.order_id != order_id or grant.report_id != accepted.report_id:
                    raise DeliveryInvariantError("accepted delivery grant binding mismatch")
                if grant.revoked_at is not None or grant.expires_at <= utcnow():
                    raise DeliveryInvariantError("accepted delivery grant is not valid")
                self._validate_ready_context(order, binding, require_pending=False)
                if binding.report_id != accepted.report_id:
                    raise DeliveryInvariantError("accepted attempt report binding mismatch")
                order.order_state = OrderState.FULFILLED.value
                order.payment_state = PaymentState.PAID.value
                order.fulfillment_state = FulfillmentState.COMPLETED.value
                order.updated_at = utcnow()
                return True
        except (FulfillmentNotFound, DeliveryInvariantError):
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("accepted delivery convergence is unavailable") from exc

    def prepare_attempt(
        self,
        *,
        order_id: UUID,
        evidence: ReportResourceEvidence,
        digest: str,
        template_alias: str,
    ) -> PreparedDeliveryAttempt:
        if TOKEN_DIGEST_RE.fullmatch(digest) is None:
            raise DeliveryInvariantError("delivery token digest is invalid")
        try:
            with self.session_factory.begin() as session:
                order = session.execute(select(OrderRow).where(OrderRow.order_id == order_id).with_for_update()).scalar_one_or_none()
                if order is None:
                    raise FulfillmentNotFound("order not found")
                binding = session.execute(
                    select(FulfillmentBindingRow).where(FulfillmentBindingRow.order_id == order_id).with_for_update()
                ).scalar_one_or_none()
                if binding is None:
                    raise DeliveryInvariantError("fulfillment binding is unavailable")
                self._validate_ready_context(order, binding, require_pending=True)
                if evidence.report_id != binding.report_id or evidence.analysis_id != binding.analysis_id or evidence.state != "ready":
                    raise DeliveryInvariantError("fresh report evidence does not match durable binding")
                accepted = session.execute(
                    select(DeliveryAttemptRow.delivery_attempt_id)
                    .where(DeliveryAttemptRow.order_id == order_id, DeliveryAttemptRow.status == "provider_accepted")
                    .limit(1)
                ).scalar_one_or_none()
                if accepted is not None:
                    raise DeliveryInvariantError("provider acceptance already exists")
                current = session.execute(
                    select(func.max(DeliveryAttemptRow.attempt_number)).where(DeliveryAttemptRow.order_id == order_id)
                ).scalar_one()
                attempt_number = int(current or 0) + 1
                if attempt_number > DELIVERY_MAX_ATTEMPTS:
                    order.order_state = OrderState.ATTENTION_REQUIRED.value
                    order.fulfillment_state = FulfillmentState.DELIVERY_FAILED.value
                    order.updated_at = utcnow()
                    raise DeliveryInvariantError("delivery retry limit is exhausted")
                now = utcnow()
                grant_id = uuid4()
                attempt_id = uuid4()
                expires_at = now + DELIVERY_GRANT_TTL
                session.add(
                    DeliveryGrantRow(
                        grant_id=grant_id,
                        order_id=order_id,
                        report_id=evidence.report_id,
                        token_digest=digest,
                        issued_at=now,
                        expires_at=expires_at,
                        revoked_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.flush()
                session.add(
                    DeliveryAttemptRow(
                        delivery_attempt_id=attempt_id,
                        order_id=order_id,
                        report_id=evidence.report_id,
                        grant_id=grant_id,
                        provider=POSTMARK_PROVIDER,
                        recipient=order.customer_email,
                        template_alias=template_alias,
                        attempt_number=attempt_number,
                        attempt_started_at=now,
                        provider_message_id=None,
                        provider_submitted_at=None,
                        status="prepared",
                        failure_code=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return PreparedDeliveryAttempt(
                    delivery_attempt_id=attempt_id,
                    grant_id=grant_id,
                    order_id=order_id,
                    report_id=evidence.report_id,
                    recipient=order.customer_email,
                    template_alias=template_alias,
                    attempt_number=attempt_number,
                    issued_at=now,
                    expires_at=expires_at,
                )
        except (FulfillmentNotFound, DeliveryInvariantError):
            raise
        except IntegrityError as exc:
            raise DeliveryInvariantError("delivery attempt identity conflict") from exc
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("delivery attempt could not be prepared") from exc

    def mark_dispatch_started(self, attempt_id: UUID) -> None:
        try:
            with self.session_factory.begin() as session:
                row = session.execute(
                    select(DeliveryAttemptRow).where(DeliveryAttemptRow.delivery_attempt_id == attempt_id).with_for_update()
                ).scalar_one_or_none()
                if row is None:
                    raise DeliveryInvariantError("delivery attempt is unavailable")
                if row.status == "prepared":
                    row.status = "dispatch_started"
                    row.updated_at = utcnow()
                elif row.status != "dispatch_started":
                    raise DeliveryInvariantError("delivery attempt cannot be dispatched")
        except DeliveryInvariantError:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("delivery dispatch state could not be persisted") from exc

    def record_accepted(self, attempt_id: UUID, evidence: PostmarkAcceptance) -> None:
        try:
            with self.session_factory.begin() as session:
                attempt = session.execute(
                    select(DeliveryAttemptRow).where(DeliveryAttemptRow.delivery_attempt_id == attempt_id).with_for_update()
                ).scalar_one_or_none()
                if attempt is None:
                    raise DeliveryInvariantError("delivery attempt is unavailable")
                order = session.execute(select(OrderRow).where(OrderRow.order_id == attempt.order_id).with_for_update()).scalar_one()
                grant = session.execute(select(DeliveryGrantRow).where(DeliveryGrantRow.grant_id == attempt.grant_id).with_for_update()).scalar_one()
                binding = session.execute(
                    select(FulfillmentBindingRow).where(FulfillmentBindingRow.order_id == attempt.order_id).with_for_update()
                ).scalar_one()
                if attempt.status == "provider_accepted":
                    if attempt.provider_message_id != evidence.message_id:
                        raise DeliveryInvariantError("provider MessageID rebinding conflict")
                    return
                if attempt.status not in {"prepared", "dispatch_started"}:
                    raise DeliveryInvariantError("delivery attempt cannot accept provider evidence")
                if evidence.recipient != attempt.recipient:
                    raise DeliveryInvariantError("provider recipient evidence mismatch")
                if grant.order_id != attempt.order_id or grant.report_id != attempt.report_id:
                    raise DeliveryInvariantError("delivery grant binding mismatch")
                now = utcnow()
                if grant.revoked_at is not None or grant.expires_at <= now:
                    raise DeliveryInvariantError("accepted attempt grant is not valid")
                self._validate_ready_context(order, binding, require_pending=True)
                if binding.report_id != attempt.report_id:
                    raise DeliveryInvariantError("accepted attempt report binding mismatch")
                attempt.provider_message_id = evidence.message_id
                attempt.provider_submitted_at = evidence.submitted_at
                attempt.status = "provider_accepted"
                attempt.failure_code = None
                attempt.updated_at = now
                order.order_state = OrderState.FULFILLED.value
                order.payment_state = PaymentState.PAID.value
                order.fulfillment_state = FulfillmentState.COMPLETED.value
                order.updated_at = now
        except (DeliveryInvariantError, FulfillmentNotFound):
            raise
        except IntegrityError as exc:
            raise DeliveryInvariantError("provider MessageID is already bound to another attempt") from exc
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("provider acceptance could not be persisted") from exc

    def _record_failure(self, attempt_id: UUID, *, status: str, code: str, retryable: bool) -> None:
        if status not in {"provider_rejected", "provider_uncertain"}:
            raise DeliveryInvariantError("unsupported delivery failure state")
        safe_code = re.sub(r"[^A-Za-z0-9_.-]", "_", code)[:80] or "delivery_failure"
        try:
            with self.session_factory.begin() as session:
                attempt = session.execute(
                    select(DeliveryAttemptRow).where(DeliveryAttemptRow.delivery_attempt_id == attempt_id).with_for_update()
                ).scalar_one_or_none()
                if attempt is None:
                    raise DeliveryInvariantError("delivery attempt is unavailable")
                if attempt.status == "provider_accepted":
                    return
                if attempt.status not in {"prepared", "dispatch_started", "provider_rejected", "provider_uncertain"}:
                    raise DeliveryInvariantError("delivery attempt failure transition is invalid")
                order = session.execute(select(OrderRow).where(OrderRow.order_id == attempt.order_id).with_for_update()).scalar_one()
                attempt.status = status
                attempt.failure_code = safe_code
                attempt.updated_at = utcnow()
                if not retryable or attempt.attempt_number >= DELIVERY_MAX_ATTEMPTS:
                    order.order_state = OrderState.ATTENTION_REQUIRED.value
                    order.payment_state = PaymentState.PAID.value
                    order.fulfillment_state = FulfillmentState.DELIVERY_FAILED.value
                    order.updated_at = utcnow()
        except DeliveryInvariantError:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("delivery failure evidence could not be persisted") from exc

    def record_rejected(self, attempt_id: UUID, *, code: str, retryable: bool) -> None:
        self._record_failure(attempt_id, status="provider_rejected", code=code, retryable=retryable)

    def record_uncertain(self, attempt_id: UUID, *, code: str) -> None:
        self._record_failure(attempt_id, status="provider_uncertain", code=code, retryable=True)

    def resolve_grant(self, digest: str, *, now: datetime | None = None) -> DeliveryContext:
        if TOKEN_DIGEST_RE.fullmatch(digest) is None:
            raise DeliveryCapabilityUnavailable("delivery capability is unavailable")
        instant = now or utcnow()
        try:
            with self.session_factory() as session:
                grant = session.execute(select(DeliveryGrantRow).where(DeliveryGrantRow.token_digest == digest)).scalar_one_or_none()
                if grant is None or grant.revoked_at is not None or grant.expires_at <= instant:
                    raise DeliveryCapabilityUnavailable("delivery capability is unavailable")
                order = session.get(OrderRow, grant.order_id)
                binding = session.get(FulfillmentBindingRow, grant.order_id)
                if order is None or binding is None:
                    raise DeliveryCapabilityUnavailable("delivery capability is unavailable")
                try:
                    self._validate_ready_context(order, binding, require_pending=False)
                except DeliveryInvariantError as exc:
                    raise DeliveryCapabilityUnavailable("delivery capability is unavailable") from exc
                if binding.report_id != grant.report_id:
                    raise DeliveryCapabilityUnavailable("delivery capability is unavailable")
                context = self._context(order, binding)
                if context.report_id != grant.report_id:
                    raise DeliveryCapabilityUnavailable("delivery capability is unavailable")
                return context
        except DeliveryCapabilityUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("delivery capability lookup is unavailable") from exc


class SiteScoreDeliveryGateway:
    def __init__(self, settings: Settings):
        self._service_key = settings.sitescore_api_service_key
        self._timeout = settings.sitescore_api_timeout_seconds

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._service_key}", "Accept": "application/json"}

    @staticmethod
    def _raise_http(status_code: int) -> None:
        if status_code in {429, 500, 502, 503, 504}:
            raise DeliveryUpstreamUnavailable("sitescore_retryable_http_error", retryable=True)
        if status_code in {401, 403}:
            raise DeliveryUpstreamUnavailable("sitescore_auth_error", retryable=False)
        if status_code == 404:
            raise DeliveryUpstreamUnavailable("sitescore_report_not_found", retryable=False)
        if status_code == 409:
            raise DeliveryUpstreamUnavailable("sitescore_report_conflict", retryable=False)
        raise DeliveryUpstreamUnavailable("sitescore_http_error", retryable=False)

    def get_report(self, *, base_url: str, report_id: UUID, analysis_id: UUID) -> ReportResourceEvidence:
        url = urljoin(base_url.rstrip("/") + "/", f"v1/reports/{report_id}")
        try:
            response = httpx.get(url, headers=self._headers, timeout=self._timeout)
        except httpx.RequestError as exc:
            raise DeliveryUpstreamUnavailable("sitescore_network_error", retryable=True) from exc
        if response.status_code != 200:
            self._raise_http(response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise DeliveryUpstreamUnavailable("sitescore_malformed_report", retryable=False) from exc
        if not isinstance(data, dict):
            raise DeliveryUpstreamUnavailable("sitescore_malformed_report", retryable=False)
        observed_report = _uuid(data.get("report_id"), "sitescore_report_id_invalid")
        observed_analysis = _uuid(data.get("analysis_id"), "sitescore_report_analysis_id_invalid")
        if observed_report != report_id or observed_analysis != analysis_id:
            raise DeliveryUpstreamUnavailable("sitescore_report_binding_mismatch", retryable=False)
        if data.get("state") != "ready":
            raise DeliveryUpstreamUnavailable("sitescore_report_not_ready", retryable=False)
        content_sha256 = str(data.get("content_sha256") or "")
        if TOKEN_DIGEST_RE.fullmatch(content_sha256) is None:
            raise DeliveryUpstreamUnavailable("sitescore_report_hash_invalid", retryable=False)
        mime_type = str(data.get("mime_type") or "")
        if mime_type.lower() != "application/pdf":
            raise DeliveryUpstreamUnavailable("sitescore_report_mime_invalid", retryable=False)
        filename = _safe_filename(data.get("filename"))
        byte_length = data.get("byte_length")
        if isinstance(byte_length, bool) or not isinstance(byte_length, int) or byte_length <= 0:
            raise DeliveryUpstreamUnavailable("sitescore_report_length_invalid", retryable=False)
        return ReportResourceEvidence(
            report_id=observed_report,
            analysis_id=observed_analysis,
            state="ready",
            content_sha256=content_sha256,
            mime_type="application/pdf",
            filename=filename,
            byte_length=byte_length,
        )

    def get_content(self, *, base_url: str, evidence: ReportResourceEvidence) -> DownloadPayload:
        url = urljoin(base_url.rstrip("/") + "/", f"v1/reports/{evidence.report_id}/content")
        headers = {"Authorization": f"Bearer {self._service_key}", "Accept": "application/pdf"}
        try:
            response = httpx.get(url, headers=headers, timeout=self._timeout)
        except httpx.RequestError as exc:
            raise DeliveryUpstreamUnavailable("sitescore_content_network_error", retryable=True) from exc
        if response.status_code != 200:
            self._raise_http(response.status_code)
        media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/pdf":
            raise DeliveryUpstreamUnavailable("sitescore_content_mime_mismatch", retryable=False)
        upstream_hash = response.headers.get("Content-SHA256", "").strip().lower()
        if upstream_hash != evidence.content_sha256:
            raise DeliveryUpstreamUnavailable("sitescore_content_hash_header_mismatch", retryable=False)
        content = bytes(response.content)
        if len(content) != evidence.byte_length:
            raise DeliveryUpstreamUnavailable("sitescore_content_length_mismatch", retryable=False)
        reported_length = response.headers.get("Content-Length")
        if reported_length is not None:
            try:
                if int(reported_length) != evidence.byte_length:
                    raise DeliveryUpstreamUnavailable("sitescore_content_length_header_mismatch", retryable=False)
            except ValueError as exc:
                raise DeliveryUpstreamUnavailable("sitescore_content_length_header_invalid", retryable=False) from exc
        local_hash = hashlib.sha256(content).hexdigest()
        if local_hash != evidence.content_sha256:
            raise DeliveryUpstreamUnavailable("sitescore_content_hash_mismatch", retryable=False)
        if not content.startswith(b"%PDF-"):
            raise DeliveryUpstreamUnavailable("sitescore_content_pdf_invalid", retryable=False)
        return DownloadPayload(content=content, filename=evidence.filename, content_sha256=local_hash)


class PostmarkGateway:
    def __init__(self, settings: Settings, *, endpoint: str = POSTMARK_ENDPOINT):
        self._endpoint = endpoint
        self._token = settings.postmark_server_token
        self._from_email = settings.postmark_from_email
        self._template_alias = settings.postmark_template_alias
        self._timeout = settings.postmark_timeout_seconds

    def send(
        self,
        *,
        recipient: str,
        order_id: UUID,
        report_id: UUID,
        download_url: str,
        expires_at: datetime,
    ) -> PostmarkAcceptance:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": self._token,
        }
        body = {
            "From": self._from_email,
            "To": recipient,
            "TemplateAlias": self._template_alias,
            "TemplateModel": {
                "order_reference": str(order_id),
                "report_reference": str(report_id),
                "secure_download_url": download_url,
                "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
                "expires_in_days": 7,
            },
            "MessageStream": POSTMARK_MESSAGE_STREAM,
        }
        try:
            response = httpx.post(self._endpoint, headers=headers, json=body, timeout=self._timeout)
        except httpx.RequestError as exc:
            raise PostmarkUncertain() from exc
        if response.status_code != 200:
            retryable = response.status_code == 429 or response.status_code >= 500
            raise PostmarkRejected(f"postmark_http_{response.status_code}", retryable=retryable)
        try:
            data = response.json()
        except ValueError as exc:
            raise PostmarkRejected("postmark_malformed_response", retryable=False) from exc
        if not isinstance(data, dict):
            raise PostmarkRejected("postmark_malformed_response", retryable=False)
        error_code = data.get("ErrorCode")
        if isinstance(error_code, bool) or not isinstance(error_code, int):
            raise PostmarkRejected("postmark_error_code_invalid", retryable=False)
        if error_code != 0:
            raise PostmarkRejected(f"postmark_error_{error_code}", retryable=False)
        message_id = data.get("MessageID")
        if not isinstance(message_id, str) or not message_id.strip():
            raise PostmarkRejected("postmark_message_id_missing", retryable=False)
        message_id = message_id.strip()
        try:
            UUID(message_id)
        except ValueError as exc:
            raise PostmarkRejected("postmark_message_id_invalid", retryable=False) from exc
        observed_recipient = data.get("To")
        if observed_recipient != recipient:
            raise PostmarkRejected("postmark_recipient_mismatch", retryable=False)
        submitted_at = _parse_provider_timestamp(data.get("SubmittedAt"))
        return PostmarkAcceptance(message_id=message_id, submitted_at=submitted_at, recipient=recipient)


@dataclass
class DeliveryService:
    settings: Settings
    store: DeliveryStore
    sitescore: SiteScoreDeliveryGateway
    postmark: PostmarkGateway

    def deliver(self, order_id: UUID) -> None:
        if self.store.converge_known_acceptance(order_id):
            return
        context = self.store.load_context(order_id)
        report = self.sitescore.get_report(
            base_url=context.sitescore_api_base_url,
            report_id=context.report_id,
            analysis_id=context.analysis_id,
        )
        raw_token = generate_delivery_token()
        digest = token_digest(raw_token)
        prepared = self.store.prepare_attempt(
            order_id=order_id,
            evidence=report,
            digest=digest,
            template_alias=self.settings.postmark_template_alias,
        )
        download_url = f"{self.settings.commerce_public_base_url}/d/{raw_token}"
        self.store.mark_dispatch_started(prepared.delivery_attempt_id)
        try:
            acceptance = self.postmark.send(
                recipient=prepared.recipient,
                order_id=prepared.order_id,
                report_id=prepared.report_id,
                download_url=download_url,
                expires_at=prepared.expires_at,
            )
        except PostmarkUncertain as exc:
            self.store.record_uncertain(prepared.delivery_attempt_id, code=exc.code)
            return
        except PostmarkRejected as exc:
            self.store.record_rejected(prepared.delivery_attempt_id, code=exc.code, retryable=exc.retryable)
            return
        self.store.record_accepted(prepared.delivery_attempt_id, acceptance)

    def download(self, raw_token: str) -> DownloadPayload:
        if not isinstance(raw_token, str) or len(raw_token) < 40 or len(raw_token) > 128:
            raise DeliveryCapabilityUnavailable("delivery capability is unavailable")
        try:
            digest = token_digest(raw_token)
        except (UnicodeEncodeError, AttributeError) as exc:
            raise DeliveryCapabilityUnavailable("delivery capability is unavailable") from exc
        context = self.store.resolve_grant(digest)
        report = self.sitescore.get_report(
            base_url=context.sitescore_api_base_url,
            report_id=context.report_id,
            analysis_id=context.analysis_id,
        )
        return self.sitescore.get_content(base_url=context.sitescore_api_base_url, evidence=report)
