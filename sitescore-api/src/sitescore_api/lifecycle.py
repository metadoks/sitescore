from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import Database
from .db_models import AnalysisModel, DispatchOutboxModel, TERMINAL_STATES
from .errors import AnalysisNotFound, IdempotencyConflict
from .idempotency import canonical_request_hash, canonical_request_json
from .ingress import AnalysisIngressCommand
from .models import AnalysisRequest
from .outcomes import (
    CanonicalCompletedOutcome,
    CanonicalNotScoreReadyOutcome,
    require_canonical_completed_outcome,
    require_canonical_not_score_ready_outcome,
)
from .version import API_VERSION


@dataclass(frozen=True, slots=True)
class AcceptedAnalysisResource:
    analysis_id: UUID
    state: str


@dataclass(frozen=True, slots=True)
class RetrievedAnalysisResource:
    analysis_id: UUID
    state: str
    created_at: datetime
    updated_at: datetime
    result: dict[str, object] | None
    readiness: dict[str, object] | None
    error: dict[str, str] | None


class DispatchTrigger(Protocol):
    def dispatch_analysis(self, analysis_id: UUID) -> None: ...


class AnalysisLifecycleBackend(Protocol):
    def submit(
        self,
        command: AnalysisIngressCommand,
        request_model: AnalysisRequest,
        *,
        consumer_id: UUID,
        idempotency_key: str,
    ) -> AcceptedAnalysisResource: ...

    def retrieve(self, analysis_id: UUID, *, consumer_id: UUID) -> RetrievedAnalysisResource: ...


def analysis_advisory_key(analysis_id: UUID) -> int:
    """Stable server-owned advisory-lock key shared by worker and timeout writers."""

    return int.from_bytes(sha256(analysis_id.bytes).digest()[:8], "big", signed=True)


def try_analysis_timeout_authority(session: Session, analysis_id: UUID) -> bool:
    """Claim this transaction's right to publish timeout when no worker owns execution.

    The canonical worker holds the same key as a session-level advisory lock for its
    entire execution attempt. Timeout writers use the transaction-level variant so a
    live worker attempt and a public terminal timeout can never both own authority.
    """

    return bool(
        session.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": analysis_advisory_key(analysis_id)},
        ).scalar_one()
    )


class PostgresAnalysisLifecycleBackend:
    def __init__(
        self,
        database: Database,
        dispatcher: DispatchTrigger,
        *,
        deadline_seconds: int,
    ) -> None:
        self.database = database
        self.dispatcher = dispatcher
        self.deadline_seconds = deadline_seconds

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def submit(
        self,
        command: AnalysisIngressCommand,
        request_model: AnalysisRequest,
        *,
        consumer_id: UUID,
        idempotency_key: str,
    ) -> AcceptedAnalysisResource:
        request_hash = canonical_request_hash(request_model)
        payload = canonical_request_json(request_model)
        now = self._now()
        task_id = uuid4()
        analysis_id: UUID
        state: str
        with self.database.session() as session:
            try:
                with session.begin():
                    row = AnalysisModel(
                        analysis_id=command.analysis_id,
                        consumer_id=consumer_id,
                        creation_request_id=command.request_id,
                        api_version=API_VERSION,
                        state="queued",
                        request_payload=payload,
                        request_hash=request_hash,
                        idempotency_key=idempotency_key,
                        task_id=task_id,
                        created_at=now,
                        updated_at=now,
                        started_at=None,
                        finished_at=None,
                        deadline_at=now + timedelta(seconds=self.deadline_seconds),
                        canonical_success_at=None,
                        result_body=None,
                        readiness_body=None,
                        failure_code=None,
                        failure_message=None,
                    )
                    session.add(row)
                    session.add(
                        DispatchOutboxModel(
                            analysis_id=command.analysis_id,
                            task_id=task_id,
                            created_at=now,
                            dispatched_at=None,
                            attempt_count=0,
                            last_error_code=None,
                            last_error_message=None,
                        )
                    )
                analysis_id = command.analysis_id
                state = "queued"
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(AnalysisModel).where(
                        AnalysisModel.consumer_id == consumer_id,
                        AnalysisModel.idempotency_key == idempotency_key,
                    )
                )
                if existing is None:
                    raise
                if existing.request_hash != request_hash:
                    raise IdempotencyConflict()
                analysis_id = existing.analysis_id
                state = existing.state

        try:
            self.dispatcher.dispatch_analysis(analysis_id)
        except Exception:
            pass
        return AcceptedAnalysisResource(analysis_id=analysis_id, state=state)

    def retrieve(self, analysis_id: UUID, *, consumer_id: UUID) -> RetrievedAnalysisResource:
        now = self._now()
        with self.database.session() as session:
            with session.begin():
                row = session.scalar(
                    select(AnalysisModel)
                    .where(
                        AnalysisModel.analysis_id == analysis_id,
                        AnalysisModel.consumer_id == consumer_id,
                    )
                    .with_for_update()
                )
                if row is None:
                    raise AnalysisNotFound()
                if (
                    row.state not in TERMINAL_STATES
                    and row.canonical_success_at is None
                    and now >= row.deadline_at
                    and try_analysis_timeout_authority(session, row.analysis_id)
                ):
                    row.state = "timed_out"
                    row.updated_at = now
                    row.finished_at = now
                    row.failure_code = "analysis_deadline_exceeded"
                    row.failure_message = "analysis exceeded its server-owned deadline"
                return _resource(row)


def _resource(row: AnalysisModel) -> RetrievedAnalysisResource:
    error = None
    if row.failure_code is not None:
        error = {"code": row.failure_code, "message": row.failure_message or "analysis failed"}
    return RetrievedAnalysisResource(
        analysis_id=row.analysis_id,
        state=row.state,
        created_at=row.created_at,
        updated_at=row.updated_at,
        result=row.result_body,
        readiness=row.readiness_body,
        error=error,
    )


def persist_not_score_ready(
    session: Session,
    row: AnalysisModel,
    outcome: CanonicalNotScoreReadyOutcome,
    *,
    now: datetime,
) -> bool:
    canonical = require_canonical_not_score_ready_outcome(outcome)
    if row.state in TERMINAL_STATES:
        return False
    if row.canonical_success_at is not None:
        return False
    if now >= row.deadline_at:
        row.state = "timed_out"
        row.finished_at = now
        row.updated_at = now
        row.failure_code = "analysis_deadline_exceeded"
        row.failure_message = "analysis exceeded its server-owned deadline"
        return False
    row.state = "not_score_ready"
    row.result_body = None
    row.readiness_body = canonical.readiness_projection
    row.failure_code = None
    row.failure_message = None
    row.finished_at = now
    row.updated_at = now
    return True


def persist_completed(
    session: Session,
    row: AnalysisModel,
    outcome: CanonicalCompletedOutcome,
    *,
    now: datetime,
) -> bool:
    canonical = require_canonical_completed_outcome(outcome)
    if row.state in TERMINAL_STATES:
        return False
    if row.canonical_success_at is None:
        if now >= row.deadline_at:
            row.state = "timed_out"
            row.finished_at = now
            row.updated_at = now
            row.failure_code = "analysis_deadline_exceeded"
            row.failure_message = "analysis exceeded its server-owned deadline"
            return False
        row.canonical_success_at = now
    elif row.canonical_success_at >= row.deadline_at:
        raise ValueError("canonical success marker must precede the analysis deadline")
    row.state = "completed"
    row.result_body = canonical.result_body
    row.readiness_body = None
    row.failure_code = None
    row.failure_message = None
    row.finished_at = now
    row.updated_at = now
    return True
