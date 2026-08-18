from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .db import Database
from .db_models import AnalysisModel, ReportModel, TERMINAL_STATES
from .execution import CanonicalAnalysisExecutor
from .ingress import build_analysis_ingress_command
from .lifecycle import persist_completed, persist_not_score_ready
from .models import AnalysisRequest
from .report_artifacts import (
    PreparedReportArtifact,
    REPORT_MIME_TYPE,
    REPORT_STATE_FAILED,
    REPORT_STATE_READY,
    ReportArtifactGenerator,
    persist_report_artifact,
)

_REQUEST_ADAPTER = TypeAdapter(AnalysisRequest)
_REPORT_ARTIFACT_FIELDS = (
    "report_id",
    "analysis_id",
    "report_artifact_version",
    "state",
    "analysis_fingerprint",
    "report_schema_version",
    "report_projection_version",
    "narrative_prompt_version",
    "narrative_schema_version",
    "narrative_provider",
    "narrative_model_id",
    "narrative_generation_mode",
    "narrative_fallback_version",
    "presentation_schema_version",
    "presentation_policy_version",
    "template_version",
    "stylesheet_version",
    "chart_version",
    "renderer_version",
    "generated_at",
    "content_sha256",
    "mime_type",
    "filename",
    "byte_length",
    "storage_key",
    "failure_code",
    "failure_message",
)


def _advisory_key(analysis_id: UUID) -> int:
    return int.from_bytes(sha256(analysis_id.bytes).digest()[:8], "big", signed=True)


def _failed_report_artifact(artifact: PreparedReportArtifact) -> PreparedReportArtifact:
    """Preserve provenance/identity while clearing every ready-content binding."""

    return replace(
        artifact,
        state=REPORT_STATE_FAILED,
        content_sha256=None,
        mime_type=None,
        filename=None,
        byte_length=None,
        storage_key=None,
        failure_code="report_generation_failed",
        failure_message="report artifact generation failed",
    )


def _report_row_matches_artifact(row: ReportModel, artifact: PreparedReportArtifact) -> bool:
    """Require exact durable report semantics, never report-id-only idempotence."""

    return all(getattr(row, field) == getattr(artifact, field) for field in _REPORT_ARTIFACT_FIELDS)


class AnalysisWorkerService:
    def __init__(
        self,
        database: Database,
        executor: CanonicalAnalysisExecutor,
        report_artifacts: ReportArtifactGenerator | None = None,
    ) -> None:
        self.database = database
        self.executor = executor
        self.report_artifacts = report_artifacts

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _rollback_quietly(session: Session) -> None:
        try:
            session.rollback()
        except Exception:
            pass

    def _commit_report_metadata(self, session: Session) -> None:
        """Single report metadata commit seam used by deterministic ACK-loss tests."""

        session.commit()

    def _ready_object_matches(self, artifact: PreparedReportArtifact) -> bool:
        """Verify the exact server-owned ready binding without reading report bytes."""

        if (
            self.report_artifacts is None
            or artifact.state != REPORT_STATE_READY
            or artifact.storage_key is None
            or artifact.byte_length is None
            or artifact.mime_type != REPORT_MIME_TYPE
        ):
            return False
        try:
            metadata = self.report_artifacts.storage.head(artifact.storage_key)
        except Exception:
            return False
        return (
            metadata.byte_length == artifact.byte_length
            and metadata.content_type in (None, artifact.mime_type)
        )

    def _reconcile_report_commit(self, artifact: PreparedReportArtifact) -> str:
        """Resolve an ambiguous commit using a fresh independent PostgreSQL session.

        Returns one of: absent, ready, ready_invalid, failed, conflict, unknown.
        No destructive storage action is taken here.
        """

        try:
            with self.database.session() as fresh:
                row = fresh.scalar(
                    select(ReportModel).where(
                        ReportModel.analysis_id == artifact.analysis_id,
                        ReportModel.report_artifact_version == artifact.report_artifact_version,
                    )
                )
                if row is None:
                    return "absent"
                if row.report_id != artifact.report_id:
                    return "conflict"
                if _report_row_matches_artifact(row, artifact):
                    if artifact.state == REPORT_STATE_READY:
                        return "ready" if self._ready_object_matches(artifact) else "ready_invalid"
                    if artifact.state == REPORT_STATE_FAILED:
                        return "failed"
                    return "conflict"
                failed_artifact = _failed_report_artifact(artifact)
                if _report_row_matches_artifact(row, failed_artifact):
                    return "failed"
                return "conflict"
        except Exception:
            return "unknown"

    def _same_identity_state(self, artifact: PreparedReportArtifact) -> str:
        try:
            with self.database.session() as fresh:
                row = fresh.scalar(
                    select(ReportModel).where(
                        ReportModel.analysis_id == artifact.analysis_id,
                        ReportModel.report_artifact_version == artifact.report_artifact_version,
                        ReportModel.report_id == artifact.report_id,
                    )
                )
                if row is None:
                    return "absent"
                return row.state
        except Exception:
            return "unknown"

    def _transition_same_identity_to_failed(self, artifact: PreparedReportArtifact) -> bool:
        """Fail closed for an exact report identity that cannot remain valid ready.

        The transition preserves the row's analytical/provenance identity and only
        clears caller-visible ready content bindings. If commit acknowledgement is
        itself ambiguous, a fresh session reconciles the resulting durable state.
        """

        for _ in range(3):
            try:
                with self.database.session() as fresh:
                    row = fresh.scalar(
                        select(ReportModel)
                        .where(
                            ReportModel.analysis_id == artifact.analysis_id,
                            ReportModel.report_artifact_version == artifact.report_artifact_version,
                            ReportModel.report_id == artifact.report_id,
                        )
                        .with_for_update()
                    )
                    if row is None:
                        return False
                    if row.state == REPORT_STATE_FAILED:
                        return True
                    row.state = REPORT_STATE_FAILED
                    row.content_sha256 = None
                    row.mime_type = None
                    row.filename = None
                    row.byte_length = None
                    row.storage_key = None
                    row.failure_code = "report_generation_failed"
                    row.failure_message = "report artifact generation failed"
                    row.updated_at = self._now()
                    fresh.flush()
                    try:
                        self._commit_report_metadata(fresh)
                        return True
                    except Exception:
                        self._rollback_quietly(fresh)
            except Exception:
                pass
            state = self._same_identity_state(artifact)
            if state == REPORT_STATE_FAILED:
                return True
            if state == "unknown":
                return False
        return False

    def _persist_failed_report_fresh(
        self,
        *,
        analysis_id: UUID,
        artifact: PreparedReportArtifact,
    ) -> None:
        failed_artifact = _failed_report_artifact(artifact)
        try:
            with self.database.session() as fresh:
                row = fresh.scalar(
                    select(AnalysisModel)
                    .where(AnalysisModel.analysis_id == analysis_id)
                    .with_for_update()
                )
                if row is None or row.state != "completed":
                    self._rollback_quietly(fresh)
                    return
                persisted_row = persist_report_artifact(
                    fresh,
                    row,
                    failed_artifact,
                    now=self._now(),
                )
                if not _report_row_matches_artifact(persisted_row, failed_artifact):
                    raise ValueError("existing report row is not semantically equivalent")
                fresh.flush()
                try:
                    self._commit_report_metadata(fresh)
                    return
                except Exception:
                    self._rollback_quietly(fresh)
        except Exception:
            pass
        # A failed-artifact commit may also have lost only its acknowledgement.
        # Fresh reconciliation prevents a duplicate or contradictory write.
        self._reconcile_report_commit(failed_artifact)

    def _persist_report_after_completed(
        self,
        session: Session,
        *,
        analysis_id: UUID,
        artifact: PreparedReportArtifact,
    ) -> None:
        """Persist report state after canonical analysis truth is already durable.

        RPT55-H001 isolates report finalization from canonical analysis completion.
        RPT55-H002 treats a report commit exception as UNKNOWN until a fresh,
        independent database read resolves whether the exact artifact committed.
        Destructive object compensation is never authorized by uncertainty alone.
        """

        try:
            row = session.scalar(
                select(AnalysisModel)
                .where(AnalysisModel.analysis_id == analysis_id)
                .with_for_update()
            )
            if row is None or row.state != "completed":
                session.rollback()
                if self.report_artifacts is not None:
                    self.report_artifacts.compensate(artifact)
                return
            persisted_row = persist_report_artifact(session, row, artifact, now=self._now())
            if not _report_row_matches_artifact(persisted_row, artifact):
                raise ValueError("existing report row is not semantically equivalent")
            # Force ORM/DB constraint failures into this report-specific domain
            # before the commit boundary, while still covering commit failures.
            session.flush()
            self._commit_report_metadata(session)
            return
        except Exception:
            self._rollback_quietly(session)

        reconciliation = self._reconcile_report_commit(artifact)

        # Exact ready metadata really committed and the exact object binding still
        # exists: acknowledgement was lost, so keep both row and object.
        if reconciliation == "ready":
            return

        # A durable failed row already owns this identity. A candidate ready object
        # is unbound and may now be compensated safely.
        if reconciliation == "failed":
            if self.report_artifacts is not None:
                self.report_artifacts.compensate(artifact)
            return

        # A committed ready row whose object binding is already invalid must not
        # remain caller-valid ready. First make the DB state failed, confirm it,
        # then compensate only after the failed state is durable.
        if reconciliation == "ready_invalid":
            if self._transition_same_identity_to_failed(artifact):
                if self.report_artifacts is not None:
                    self.report_artifacts.compensate(artifact)
            return

        # Same server-owned identity but contradictory semantics is not idempotent
        # success. Fail the exact identity closed before any destructive cleanup.
        if reconciliation == "conflict":
            if self._transition_same_identity_to_failed(artifact):
                if self.report_artifacts is not None:
                    self.report_artifacts.compensate(artifact)
            return

        # Database unavailable / commit outcome indeterminate: do not delete an
        # object that may already be referenced by a successfully committed row.
        if reconciliation == "unknown":
            return

        # Fresh DB proves no report row committed. Only now is candidate-object
        # compensation safe, followed by a sanitized failed row in a fresh session.
        assert reconciliation == "absent"
        if self.report_artifacts is not None:
            self.report_artifacts.compensate(artifact)
        self._persist_failed_report_fresh(analysis_id=analysis_id, artifact=artifact)

    def execute_analysis(self, analysis_id: UUID) -> str:
        with self.database.engine.connect() as connection:
            with Session(
                bind=connection,
                expire_on_commit=False,
                future=True,
            ) as session:
                locked = bool(
                    session.execute(
                        text("SELECT pg_try_advisory_lock(:key)"),
                        {"key": _advisory_key(analysis_id)},
                    ).scalar_one()
                )
                if not locked:
                    session.rollback()
                    return "busy"
                session.commit()
                try:
                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if row is None:
                        session.rollback()
                        return "missing"
                    now = self._now()
                    if row.state in TERMINAL_STATES:
                        state = row.state
                        session.rollback()
                        return state
                    if now >= row.deadline_at:
                        row.state = "timed_out"
                        row.updated_at = now
                        row.finished_at = now
                        row.failure_code = "analysis_deadline_exceeded"
                        row.failure_message = "analysis exceeded its server-owned deadline"
                        session.commit()
                        return "timed_out"
                    if row.started_at is None:
                        row.started_at = now
                    row.state = "running"
                    row.updated_at = now
                    payload = dict(row.request_payload)
                    creation_request_id = row.creation_request_id
                    durable_analysis_id = row.analysis_id
                    session.commit()

                    request_model = _REQUEST_ADAPTER.validate_python(payload)
                    command = build_analysis_ingress_command(
                        request_model,
                        request_id=creation_request_id,
                        analysis_id=durable_analysis_id,
                    )
                    outcome = self.executor.execute(command, now=self._now())

                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if row is None:
                        session.rollback()
                        return "missing"
                    completed_at = self._now()
                    if outcome.not_score_ready is not None:
                        persist_not_score_ready(session, row, outcome.not_score_ready, now=completed_at)
                        state = row.state
                        session.commit()
                        return state

                    assert outcome.completed is not None
                    persisted = persist_completed(session, row, outcome.completed, now=completed_at)
                    state = row.state
                    # RPT55-H001: commit canonical analytical truth before entering
                    # the report generation/finalization failure domain.
                    session.commit()

                    if persisted and self.report_artifacts is not None:
                        try:
                            prepared_report = self.report_artifacts.generate(
                                consumer_id=row.consumer_id,
                                analysis_id=row.analysis_id,
                                outcome=outcome.completed,
                                generated_at=completed_at,
                            )
                        except Exception:
                            # Genuine canonical authority is expected to make
                            # ReportArtifactGenerator return a sanitized failed
                            # artifact for report-layer errors. An unexpected
                            # generator exception still cannot regress the already
                            # committed canonical analysis state.
                            return state
                        self._persist_report_after_completed(
                            session,
                            analysis_id=row.analysis_id,
                            artifact=prepared_report,
                        )
                    return state
                except Exception:
                    session.rollback()
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
                    session.commit()
                    return row.state if row is not None else "failed"
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
