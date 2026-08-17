from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


PUBLIC_STATES = (
    "queued",
    "running",
    "completed",
    "not_score_ready",
    "failed",
    "timed_out",
)
TERMINAL_STATES = ("completed", "not_score_ready", "failed", "timed_out")


class Base(DeclarativeBase):
    pass


class ConsumerModel(Base):
    __tablename__ = "consumers"

    consumer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ServiceApiKeyModel(Base):
    __tablename__ = "service_api_keys"
    __table_args__ = (
        UniqueConstraint("key_id", name="uq_service_api_keys_key_id"),
        Index("ix_service_api_keys_consumer", "consumer_id"),
    )

    record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    consumer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("consumers.consumer_id", ondelete="CASCADE"), nullable=False
    )
    secret_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    consumer: Mapped[ConsumerModel] = relationship(lazy="joined")


class AnalysisModel(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        UniqueConstraint("consumer_id", "idempotency_key", name="uq_analysis_consumer_idempotency"),
        CheckConstraint(
            "state IN ('queued','running','completed','not_score_ready','failed','timed_out')",
            name="ck_analysis_public_state",
        ),
        CheckConstraint(
            "NOT (state = 'not_score_ready' AND result_body IS NOT NULL)",
            name="ck_not_score_ready_no_scored_result",
        ),
        CheckConstraint(
            "NOT (state IN ('queued','running') AND finished_at IS NOT NULL)",
            name="ck_nonterminal_not_finished",
        ),
        Index("ix_analysis_consumer_analysis", "consumer_id", "analysis_id"),
        Index("ix_analysis_deadline", "state", "deadline_at"),
    )

    analysis_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    consumer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("consumers.consumer_id", ondelete="RESTRICT"), nullable=False
    )
    creation_request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    api_version: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    request_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    task_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result_body: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    readiness_body: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(500), nullable=True)


class DispatchOutboxModel(Base):
    __tablename__ = "dispatch_outbox"
    __table_args__ = (
        UniqueConstraint("analysis_id", name="uq_dispatch_outbox_analysis"),
        Index("ix_dispatch_outbox_pending", "dispatched_at", "created_at"),
    )

    outbox_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.analysis_id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(300), nullable=True)
