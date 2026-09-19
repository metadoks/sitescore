from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .db import Database
from .db_models import AnalysisModel, ReportModel, TERMINAL_STATES
from .execution import CanonicalAnalysisExecutor
from .ingress import build_analysis_ingress_command
from .lifecycle import (
    analysis_advisory_key,
    persist_completed,
    persist_not_score_ready,
    try_analysis_timeout_authority,
)
from .models import AnalysisRequest
from .outcomes import CanonicalCompletedOutcome
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


class RetryableReportFinalization(RuntimeError):
    """Keep the analysis retryable when terminal pair durability is indeterminate."""


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

    @staticmethod
    def _timeout_row(row: AnalysisModel, *, now: datetime) -> None:
        row.state = "timed_out"
        row.updated_at = now
        row.finished_at = now
        row.failure_code = "analysis_deadline_exceeded"
        row.failure_message = "analysis exceeded its server-owned deadline"

    def _record_canonical_success_boundary(
        self,
        session: Session,
        row: AnalysisModel,
        *,
        success_at: datetime,
    ) -> str:
        """Durably protect a genuine pre-deadline canonical success during report work.

        The marker is coordination evidence only. It is never used as report/scoring
        authority; retries still rerun canonical execution to recover the live object.
        Durable terminal states are immutable and are never repaired/resurrected here.
        """

        if row.canonical_success_at is not None:
            if row.canonical_success_at >= row.deadline_at:
                raise ValueError("canonical success marker must precede the analysis deadline")
            if row.state not in {"queued", "running"}:
                state = row.state
                session.rollback()
                return state
            row.state = "running"
            row.finished_at = None
            row.failure_code = None
            row.failure_message = None
            session.commit()
            return "protected"

        if success_at >= row.deadline_at:
            if row.state not in TERMINAL_STATES:
                self._timeout_row(row, now=success_at)
            state = row.state
            session.commit()
            return state

        if row.state not in {"queued", "running"}:
            state = row.state
            session.rollback()
            return state

        row.canonical_success_at = success_at
        row.state = "running"
        row.updated_at = success_at
        row.finished_at = None
        row.failure_code = None
        row.failure_message = None
        session.commit()
        return "protected"

    def _before_canonical_success_boundary(
        self,
        outcome: CanonicalCompletedOutcome,
        *,
        success_at: datetime,
    ) -> None:
        """No-op seam proving pre-marker timeout races while advisory execution is owned."""

    def _commit_report_metadata(self, session: Session) -> None:
        """Single terminal-pair commit seam used by deterministic ACK-loss tests."""

        session.commit()

    def _before_paired_terminal_commit(self, artifact: PreparedReportArtifact) -> None:
        """No-op seam used to prove process-loss safety before terminal durability."""

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
        """Resolve an ambiguous report-only commit using a fresh PostgreSQL session.

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

    def _reconcile_paired_commit(
        self,
        outcome: CanonicalCompletedOutcome,
        artifact: PreparedReportArtifact,
    ) -> str:
        """Reconcile atomic analysis-completed + terminal-report durability."""

        try:
            with self.database.session() as fresh:
                analysis = fresh.scalar(
                    select(AnalysisModel).where(AnalysisModel.analysis_id == artifact.analysis_id)
                )
                report = fresh.scalar(
                    select(ReportModel).where(
                        ReportModel.analysis_id == artifact.analysis_id,
                        ReportModel.report_artifact_version == artifact.report_artifact_version,
                    )
                )
                if analysis is None:
                    return "missing"
                if analysis.state == "completed":
                    if (
                        analysis.result_body != outcome.result_body
                        or analysis.readiness_body is not None
                        or analysis.failure_code is not None
                        or analysis.failure_message is not None
                    ):
                        return "conflict"
                    if report is None:
                        return "completed_missing"
                    if report.report_id != artifact.report_id:
                        return "conflict"
                    if _report_row_matches_artifact(report, artifact):
                        if artifact.state == REPORT_STATE_READY:
                            return "ready" if self._ready_object_matches(artifact) else "ready_invalid"
                        if artifact.state == REPORT_STATE_FAILED:
                            return "failed"
                    failed_artifact = _failed_report_artifact(artifact)
                    if _report_row_matches_artifact(report, failed_artifact):
                        return "failed"
                    return "conflict"
                if analysis.state in {"queued", "running"}:
                    return "absent" if report is None else "conflict"
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

    def _resource_state(self, artifact: PreparedReportArtifact) -> str:
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
                return row.state
        except Exception:
            return "unknown"

    @staticmethod
    def _fail_row_from_candidate(
        row: ReportModel,
        artifact: PreparedReportArtifact,
        *,
        now: datetime,
    ) -> None:
        """Preserve the durable report_id while aligning failed provenance to candidate."""

        failed = _failed_report_artifact(artifact)
        for field in _REPORT_ARTIFACT_FIELDS:
            if field == "report_id":
                continue
            setattr(row, field, getattr(failed, field))
        row.updated_at = now

    def _transition_same_identity_to_failed(self, artifact: PreparedReportArtifact) -> bool:
        """Fail closed for an exact report identity that cannot remain valid ready."""

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
                    self._fail_row_from_candidate(row, artifact, now=self._now())
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

    def _transition_resource_to_failed(self, artifact: PreparedReportArtifact) -> bool:
        """Fail the actual analysis/version resource even when report_id conflicts."""

        for _ in range(3):
            try:
                with self.database.session() as fresh:
                    row = fresh.scalar(
                        select(ReportModel)
                        .where(
                            ReportModel.analysis_id == artifact.analysis_id,
                            ReportModel.report_artifact_version == artifact.report_artifact_version,
                        )
                        .with_for_update()
                    )
                    if row is None:
                        return False
                    if row.state == REPORT_STATE_FAILED:
                        return True
                    self._fail_row_from_candidate(row, artifact, now=self._now())
                    fresh.flush()
                    try:
                        self._commit_report_metadata(fresh)
                        return True
                    except Exception:
                        self._rollback_quietly(fresh)
            except Exception:
                pass
            state = self._resource_state(artifact)
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
        self._reconcile_report_commit(failed_artifact)

    def _complete_analysis_with_failed_resource(
        self,
        outcome: CanonicalCompletedOutcome,
        artifact: PreparedReportArtifact,
    ) -> str:
        """Pair canonical completion with an already fail-closed terminal resource."""

        try:
            with self.database.session() as fresh:
                analysis = fresh.scalar(
                    select(AnalysisModel)
                    .where(AnalysisModel.analysis_id == artifact.analysis_id)
                    .with_for_update()
                )
                report = fresh.scalar(
                    select(ReportModel)
                    .where(
                        ReportModel.analysis_id == artifact.analysis_id,
                        ReportModel.report_artifact_version == artifact.report_artifact_version,
                    )
                    .with_for_update()
                )
                if analysis is None:
                    return "missing"
                if analysis.state == "completed":
                    return "completed" if report is not None else "retry"
                if analysis.state not in {"queued", "running"}:
                    return analysis.state
                if report is None or report.state != REPORT_STATE_FAILED:
                    return "retry"
                persisted = persist_completed(fresh, analysis, outcome, now=self._now())
                if not persisted:
                    return analysis.state
                fresh.flush()
                self._commit_report_metadata(fresh)
                return "completed"
        except Exception:
            pass

        try:
            with self.database.session() as check:
                analysis = check.scalar(
                    select(AnalysisModel).where(AnalysisModel.analysis_id == artifact.analysis_id)
                )
                report = check.scalar(
                    select(ReportModel).where(
                        ReportModel.analysis_id == artifact.analysis_id,
                        ReportModel.report_artifact_version == artifact.report_artifact_version,
                    )
                )
                if (
                    analysis is not None
                    and analysis.state == "completed"
                    and analysis.result_body == outcome.result_body
                    and analysis.failure_code is None
                    and report is not None
                    and report.state == REPORT_STATE_FAILED
                ):
                    return "completed"
        except Exception:
            pass
        return "retry"

    def _persist_failed_pair_fresh(
        self,
        outcome: CanonicalCompletedOutcome,
        artifact: PreparedReportArtifact,
    ) -> str:
        failed_artifact = _failed_report_artifact(artifact)
        try:
            with self.database.session() as fresh:
                row = fresh.scalar(
                    select(AnalysisModel)
                    .where(AnalysisModel.analysis_id == artifact.analysis_id)
                    .with_for_update()
                )
                if row is None:
                    return "missing"
                if row.state == "completed":
                    report = fresh.scalar(
                        select(ReportModel).where(
                            ReportModel.analysis_id == artifact.analysis_id,
                            ReportModel.report_artifact_version == artifact.report_artifact_version,
                        )
                    )
                    return "completed" if report is not None else "retry"
                if row.state not in {"queued", "running"}:
                    return row.state
                persisted = persist_completed(fresh, row, outcome, now=self._now())
                if not persisted:
                    return row.state
                persisted_report = persist_report_artifact(
                    fresh,
                    row,
                    failed_artifact,
                    now=self._now(),
                )
                if not _report_row_matches_artifact(persisted_report, failed_artifact):
                    raise ValueError("existing report row is not semantically equivalent")
                fresh.flush()
                self._commit_report_metadata(fresh)
                return "completed"
        except Exception:
            pass

        reconciliation = self._reconcile_paired_commit(outcome, failed_artifact)
        if reconciliation in {"failed", "ready"}:
            return "completed"
        if reconciliation == "conflict":
            if self._transition_resource_to_failed(failed_artifact):
                return self._complete_analysis_with_failed_resource(outcome, failed_artifact)
        if reconciliation == "completed_missing":
            self._persist_failed_report_fresh(
                analysis_id=artifact.analysis_id,
                artifact=failed_artifact,
            )
            return "completed" if self._resource_state(failed_artifact) == REPORT_STATE_FAILED else "retry"
        return "retry"

    def _persist_completed_report_pair(
        self,
        session: Session,
        *,
        row: AnalysisModel,
        outcome: CanonicalCompletedOutcome,
        artifact: PreparedReportArtifact,
        completed_at: datetime,
    ) -> str:
        """Atomically expose completed analysis and one terminal report resource."""

        try:
            persisted = persist_completed(session, row, outcome, now=completed_at)
            if not persisted:
                if self.report_artifacts is not None:
                    self.report_artifacts.compensate(artifact)
                session.commit()
                return row.state
            persisted_report = persist_report_artifact(
                session,
                row,
                artifact,
                now=completed_at,
            )
            if not _report_row_matches_artifact(persisted_report, artifact):
                raise ValueError("existing report row is not semantically equivalent")
            session.flush()
            self._commit_report_metadata(session)
            return "completed"
        except Exception:
            self._rollback_quietly(session)

        reconciliation = self._reconcile_paired_commit(outcome, artifact)
        if reconciliation == "ready":
            return "completed"
        if reconciliation == "failed":
            if self.report_artifacts is not None:
                self.report_artifacts.compensate(artifact)
            return "completed"
        if reconciliation in {"ready_invalid", "conflict"}:
            if self._transition_resource_to_failed(artifact):
                if self.report_artifacts is not None:
                    self.report_artifacts.compensate(artifact)
                return self._complete_analysis_with_failed_resource(outcome, artifact)
            return "retry"
        if reconciliation == "completed_missing":
            if self.report_artifacts is not None:
                self.report_artifacts.compensate(artifact)
            self._persist_failed_report_fresh(
                analysis_id=artifact.analysis_id,
                artifact=artifact,
            )
            return "completed" if self._resource_state(artifact) == REPORT_STATE_FAILED else "retry"
        if reconciliation == "unknown":
            return "retry"
        if reconciliation == "missing":
            if self.report_artifacts is not None:
                self.report_artifacts.compensate(artifact)
            return "missing"

        assert reconciliation == "absent"
        if self.report_artifacts is not None:
            self.report_artifacts.compensate(artifact)
        return self._persist_failed_pair_fresh(outcome, artifact)

    def _persist_report_after_completed(
        self,
        session: Session,
        *,
        analysis_id: UUID,
        artifact: PreparedReportArtifact,
    ) -> None:
        """Persist/repair report state for an already-durable completed analysis."""

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
            session.flush()
            self._commit_report_metadata(session)
            return
        except Exception:
            self._rollback_quietly(session)

        reconciliation = self._reconcile_report_commit(artifact)
        if reconciliation == "ready":
            return
        if reconciliation == "failed":
            if self.report_artifacts is not None:
                self.report_artifacts.compensate(artifact)
            return
        if reconciliation == "ready_invalid":
            if self._transition_same_identity_to_failed(artifact):
                if self.report_artifacts is not None:
                    self.report_artifacts.compensate(artifact)
            return
        if reconciliation == "conflict":
            if self._transition_resource_to_failed(artifact):
                if self.report_artifacts is not None:
                    self.report_artifacts.compensate(artifact)
            return
        if reconciliation == "unknown":
            raise RetryableReportFinalization("report finalization requires retry")

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
                        {"key": analysis_advisory_key(analysis_id)},
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
                    if row.canonical_success_at is None and now >= row.deadline_at:
                        self._timeout_row(row, now=now)
                        session.commit()
                        return "timed_out"
                    if row.started_at is None:
                        row.started_at = now
                    row.state = "running"
                    row.updated_at = now
                    payload = dict(row.request_payload)
                    creation_request_id = row.creation_request_id
                    durable_analysis_id = row.analysis_id
                    consumer_id = row.consumer_id
                    session.commit()

                    request_model = _REQUEST_ADAPTER.validate_python(payload)
                    command = build_analysis_ingress_command(
                        request_model,
                        request_id=creation_request_id,
                        analysis_id=durable_analysis_id,
                    )
                    outcome = self.executor.execute(command, now=self._now())
                    outcome_at = self._now()

                    if outcome.completed is not None and self.report_artifacts is not None:
                        self._before_canonical_success_boundary(
                            outcome.completed,
                            success_at=outcome_at,
                        )

                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if row is None:
                        session.rollback()
                        return "missing"
                    if outcome.not_score_ready is not None:
                        if row.canonical_success_at is not None:
                            session.rollback()
                            raise RetryableReportFinalization(
                                "post-success canonical retry did not reproduce completed outcome"
                            )
                        persist_not_score_ready(session, row, outcome.not_score_ready, now=outcome_at)
                        state = row.state
                        session.commit()
                        return state

                    assert outcome.completed is not None
                    if self.report_artifacts is None:
                        persist_completed(session, row, outcome.completed, now=outcome_at)
                        state = row.state
                        session.commit()
                        return state

                    boundary_state = self._record_canonical_success_boundary(
                        session,
                        row,
                        success_at=outcome_at,
                    )
                    if boundary_state != "protected":
                        return boundary_state

                    # Canonical success is now durably protected from lifecycle
                    # timeout writers while the live canonical object is rendered.
                    # A retry still reruns canonical execution; the marker is never
                    # promoted to report/scoring authority.
                    try:
                        prepared_report = self.report_artifacts.generate(
                            consumer_id=consumer_id,
                            analysis_id=analysis_id,
                            outcome=outcome.completed,
                            generated_at=outcome_at,
                        )
                    except Exception as exc:
                        raise RetryableReportFinalization(
                            "report generator requires worker retry"
                        ) from exc

                    self._before_paired_terminal_commit(prepared_report)

                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if row is None:
                        session.rollback()
                        self.report_artifacts.compensate(prepared_report)
                        return "missing"
                    state = self._persist_completed_report_pair(
                        session,
                        row=row,
                        outcome=outcome.completed,
                        artifact=prepared_report,
                        completed_at=outcome_at,
                    )
                    if state == "retry":
                        raise RetryableReportFinalization(
                            "paired report finalization requires worker retry"
                        )
                    return state
                except RetryableReportFinalization:
                    self._rollback_quietly(session)
                    raise
                except Exception as exc:
                    session.rollback()
                    row = session.scalar(
                        select(AnalysisModel)
                        .where(AnalysisModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if (
                        row is not None
                        and row.state not in TERMINAL_STATES
                        and row.canonical_success_at is not None
                    ):
                        session.rollback()
                        raise RetryableReportFinalization(
                            "post-success worker failure requires retry"
                        ) from exc
                    if row is not None and row.state not in TERMINAL_STATES:
                        now = self._now()
                        if now >= row.deadline_at:
                            self._timeout_row(row, now=now)
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
                            {"key": analysis_advisory_key(analysis_id)},
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
                            AnalysisModel.canonical_success_at.is_(None),
                            AnalysisModel.deadline_at <= now,
                        )
                        .with_for_update(skip_locked=True)
                        .limit(limit)
                    )
                )
                for row in rows:
                    if not try_analysis_timeout_authority(session, row.analysis_id):
                        continue
                    self._timeout_row(row, now=now)
                    count += 1
        return count
