from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .db import OutboxEventRow, PAID_OUTBOX_TYPE, PersistenceUnavailable, utcnow
from .settings import ConfigurationError, _require, _validate_http_base, _validate_secret


class DispatchTransportError(RuntimeError):
    """The n8n ingress could not be reached with a definite accepted response."""


class DispatchRejected(RuntimeError):
    """The n8n ingress returned a non-2xx response."""


class DispatchState(str, Enum):
    EMPTY = "empty"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"


@dataclass(frozen=True)
class PaidOutboxEvent:
    event_id: UUID
    event_type: str
    order_id: UUID
    occurred_at: datetime

    def payload(self) -> dict[str, str]:
        occurred = self.occurred_at
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        occurred = occurred.astimezone(timezone.utc)
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "order_id": str(self.order_id),
            "occurred_at": occurred.isoformat().replace("+00:00", "Z"),
        }


@dataclass(frozen=True)
class DispatchResult:
    state: DispatchState
    event_id: UUID | None = None
    order_id: UUID | None = None
    http_status: int | None = None


@dataclass(frozen=True)
class OutboxDispatchSettings:
    database_url: str
    webhook_url: str
    ingress_secret: str
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> "OutboxDispatchSettings":
        environment = os.getenv("COMMERCE_ENV", "production").strip().lower()
        if environment not in {"production", "development", "test"}:
            raise ConfigurationError("COMMERCE_ENV must be production, development, or test")
        webhook_url = _validate_http_base(
            _require("COMMERCE_N8N_ORDER_PAID_WEBHOOK_URL"),
            environment=environment,
            label="n8n order-paid webhook URL",
        )
        ingress_secret = _validate_secret(
            "COMMERCE_N8N_INGRESS_SECRET",
            _require("COMMERCE_N8N_INGRESS_SECRET"),
            minimum=24,
        )
        automation_secret = os.getenv("COMMERCE_AUTOMATION_API_KEY", "").strip()
        if automation_secret and automation_secret == ingress_secret:
            raise ConfigurationError(
                "COMMERCE_N8N_INGRESS_SECRET must be distinct from COMMERCE_AUTOMATION_API_KEY"
            )
        raw_timeout = os.getenv("COMMERCE_N8N_TIMEOUT_SECONDS", "10").strip()
        try:
            timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise ConfigurationError("COMMERCE_N8N_TIMEOUT_SECONDS must be numeric") from exc
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or timeout_seconds > 30:
            raise ConfigurationError("COMMERCE_N8N_TIMEOUT_SECONDS must be >0 and <=30")
        return cls(
            database_url=_require("SITESCORE_COMMERCE_DATABASE_URL"),
            webhook_url=webhook_url,
            ingress_secret=ingress_secret,
            timeout_seconds=timeout_seconds,
        )


class OutboxDispatchStore:
    """Narrow persistence boundary for normal order.paid.v1 delivery.

    Each method owns and closes its own database transaction/session.  The
    caller therefore cannot accidentally hold a row lock across n8n HTTP I/O.
    Multiple dispatchers may read the same unpublished row and send duplicates;
    the transport contract is deliberately at-least-once.
    """

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def load_next_unpublished(self) -> PaidOutboxEvent | None:
        try:
            with self.session_factory() as session:
                row = session.execute(
                    select(OutboxEventRow)
                    .where(
                        OutboxEventRow.outbox_type == PAID_OUTBOX_TYPE,
                        OutboxEventRow.payload_version == "1",
                        OutboxEventRow.published_at.is_(None),
                    )
                    .order_by(OutboxEventRow.created_at.asc(), OutboxEventRow.outbox_id.asc())
                    .limit(1)
                ).scalar_one_or_none()
                if row is None:
                    return None
                return PaidOutboxEvent(
                    event_id=row.outbox_id,
                    event_type=row.outbox_type,
                    order_id=row.order_id,
                    occurred_at=row.created_at,
                )
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("commerce outbox is unavailable") from exc

    def mark_published(self, event_id: UUID) -> None:
        try:
            with self.session_factory.begin() as session:
                row = session.execute(
                    select(OutboxEventRow)
                    .where(
                        OutboxEventRow.outbox_id == event_id,
                        OutboxEventRow.outbox_type == PAID_OUTBOX_TYPE,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if row is None:
                    raise PersistenceUnavailable("commerce outbox event identity is unavailable")
                if row.published_at is None:
                    row.published_at = utcnow()
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("commerce outbox publish state could not be persisted") from exc


class N8nWebhookClient:
    def __init__(
        self,
        settings: OutboxDispatchSettings,
        *,
        client: httpx.Client | None = None,
    ):
        self.settings = settings
        self.client = client or httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
        )

    def send(self, event: PaidOutboxEvent) -> int:
        try:
            response = self.client.post(
                self.settings.webhook_url,
                headers={
                    "Authorization": f"Bearer {self.settings.ingress_secret}",
                    "Content-Type": "application/json",
                },
                json=event.payload(),
            )
        except httpx.RequestError as exc:
            raise DispatchTransportError("n8n ingress transport did not confirm acceptance") from exc
        if 200 <= response.status_code < 300:
            return response.status_code
        raise DispatchRejected(f"n8n ingress rejected event with HTTP {response.status_code}")


class PaidOutboxDispatcher:
    def __init__(
        self,
        store: OutboxDispatchStore,
        webhook: N8nWebhookClient,
    ):
        self.store = store
        self.webhook = webhook

    def dispatch_once(self) -> DispatchResult:
        event = self.store.load_next_unpublished()
        if event is None:
            return DispatchResult(DispatchState.EMPTY)

        try:
            http_status = self.webhook.send(event)
        except (DispatchTransportError, DispatchRejected):
            # Uncertain delivery and definite non-2xx both remain unpublished.
            # The same durable event identity is retried by a later invocation.
            return DispatchResult(
                DispatchState.UNPUBLISHED,
                event_id=event.event_id,
                order_id=event.order_id,
            )

        self.store.mark_published(event.event_id)
        return DispatchResult(
            DispatchState.PUBLISHED,
            event_id=event.event_id,
            order_id=event.order_id,
            http_status=http_status,
        )


def build_dispatcher(settings: OutboxDispatchSettings | None = None) -> PaidOutboxDispatcher:
    resolved = settings or OutboxDispatchSettings.from_env()
    store = OutboxDispatchStore(resolved.database_url)
    return PaidOutboxDispatcher(store, N8nWebhookClient(resolved))


def main() -> int:
    result = build_dispatcher().dispatch_once()
    if result.state is DispatchState.UNPUBLISHED:
        print("OUTBOX_DISPATCH=UNPUBLISHED")
        return 1
    if result.state is DispatchState.EMPTY:
        print("OUTBOX_DISPATCH=EMPTY")
        return 0
    print("OUTBOX_DISPATCH=PUBLISHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
