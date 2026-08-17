from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select, text

from .db import Database
from .db_models import AnalysisModel, TERMINAL_STATES
from .execution import CanonicalAnalysisExecutor
from .ingress import build_analysis_ingress_command
from .lifecycle import persist_completed, persist_not_score_ready
from .models import AnalysisRequest

_REQUEST_ADAPTER = TypeAdapter(AnalysisRequest)


def _advisory_key(analysis_id: UUID) -> int:
    return int.from_bytes(sha256(analysis_id.bytes).digest()[:8], "big", signed=True)


class AnalysisWorkerService:
    def __init__(self, database: Database, executor: CanonicalAnalysisExecutor) -> None:
        self.database = database
        self.executor = executor

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def execute_analysis(self, analysis_id: UUID) -> str:
        with self.database.session() as session:
            locked = bool(
                session.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": _advisory_key(analysis_id)},
                ).scalar_one()
            )
            if not locked:
                return "busy"
            try:
                with session.begin():
                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if row is None:
                        return "missing"
                    now = self._now()
                    if row.state in TERMINAL_STATES:
                        return row.state
                    if now >= row.deadline_at:
                        row.state = "timed_out"
                        row.updated_at = now
                        row.finished_at = now
                        row.failure_code = "analysis_deadline_exceeded"
                        row.failure_message = "analysis exceeded its server-owned deadline"
                        return "timed_out"
                    if row.started_at is None:
                        row.started_at = now
                    row.state = "running"
                    row.updated_at = now
                    payload = dict(row.request_payload)
                    creation_request_id = row.creation_request_id
                    durable_analysis_id = row.analysis_id

                request_model = _REQUEST_ADAPTER.validate_python(payload)
                command = build_analysis_ingress_command(
                    request_model,
                    request_id=creation_request_id,
                    analysis_id=durable_analysis_id,
                )
                outcome = self.executor.execute(command, now=self._now())

                with session.begin():
                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if row is None:
                        return "missing"
                    now = self._now()
                    if outcome.not_score_ready is not None:
                        persist_not_score_ready(session, row, outcome.not_score_ready, now=now)
                        return row.state
                    assert outcome.completed is not None
                    persist_completed(session, row, outcome.completed, now=now)
                    return row.state
            except Exception:
                session.rollback()
                with session.begin():
                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if row is not None and row.state not in TERMINAL_STATES:
                        now = self._now()
                        if now >= row.deadline_at:
                            row.state = "timed_out"
                            row.failure_code = "analysis_deadline_exceeded"
                            row.failure_message = "analysis exceeded its server-owned deadline"
                        else:
                            row.state = "failed"
                            row.failure_code = "analysis_execution_failed"
                            row.failure_message = "analysis execution failed"
                        row.finished_at = now
                        row.updated_at = now
                return "failed"
            finally:
                try:
                    session.execute(
                        text("SELECT pg_advisory_unlock(:key)"),
                        {"key": _advisory_key(analysis_id)},
                    )
                    session.commit()
                except Exception:
                    session.rollback()

    def reconcile_expired(self, *, limit: int = 100) -> int:
        now = self._now()
        count = 0
        with self.database.session() as session:
            with session.begin():
                rows = list(
                    session.scalars(
                        select(AnalysisModel)
                        .where(
                            AnalysisModel.state.in_(("queued", "running")),
                            AnalysisModel.deadline_at <= now,
                        )
                        .with_for_update(skip_locked=True)
                        .limit(limit)
                    )
                )
                for row in rows:
                    row.state = "timed_out"
                    row.updated_at = now
                    row.finished_at = now
                    row.failure_code = "analysis_deadline_exceeded"
                    row.failure_message = "analysis exceeded its server-owned deadline"
                    count += 1
        return count
