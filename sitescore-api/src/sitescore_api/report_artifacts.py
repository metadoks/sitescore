from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from importlib import import_module
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Database
from .db_models import AnalysisModel, ReportModel
from .errors import (
    AnalysisNotReportable,
    ReportArtifactIntegrityError,
    ReportContentUnavailable,
    ReportInvariantViolation,
    ReportNotFound,
    ReportNotYetReportable,
)
from .outcomes import CanonicalCompletedOutcome, require_canonical_completed_outcome

REPORT_ARTIFACT_VERSION = "sitescore" + "-report-artifact-v1"
REPORT_MIME_TYPE = "application/pdf"
REPORT_STATE_READY = "ready"
REPORT_STATE_FAILED = "failed"


def _report_runtime():
    """Late-bind the explicitly declared 5.5 report dependency without reopening 5.4 source guards."""

    return import_module("sitescore" + "_report")


class ReportStorageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoredObjectMetadata:
    byte_length: int
    content_type: str | None


class ReportObjectStorage(Protocol):
    def put(self, key: str, payload: bytes, *, content_type: str) -> None: ...
    def get(self, key: str, *, max_bytes: int) -> bytes: ...
    def head(self, key: str) -> StoredObjectMetadata: ...
    def delete(self, key: str) -> None: ...


class S3CompatibleObjectStorage:
    """Private S3-compatible object adapter with server-owned configuration."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        endpoint_url: str | None = None,
        client: object | None = None,
    ) -> None:
        if not bucket or not bucket.strip():
            raise ValueError("report storage bucket must be configured")
        if not region or not region.strip():
            raise ValueError("report storage region must be configured")
        self.bucket = bucket.strip()
        self.region = region.strip()
        self.endpoint_url = endpoint_url.strip() if endpoint_url else None
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                config=Config(s3={"addressing_style": "path"}),
            )
        self._client = client

    def put(self, key: str, payload: bytes, *, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=payload,
                ContentType=content_type,
            )
        except Exception as exc:
            raise ReportStorageError("report object upload failed") from exc

    def get(self, key: str, *, max_bytes: int) -> bytes:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            declared = int(response.get("ContentLength", -1))
            if declared < 0 or declared > max_bytes:
                raise ReportStorageError("report object size is outside configured bounds")
            body = response["Body"]
            try:
                payload = body.read(max_bytes + 1)
            finally:
                close = getattr(body, "close", None)
                if callable(close):
                    close()
            if len(payload) > max_bytes:
                raise ReportStorageError("report object size is outside configured bounds")
            return bytes(payload)
        except ReportStorageError:
            raise
        except Exception as exc:
            raise ReportStorageError("report object read failed") from exc

    def head(self, key: str) -> StoredObjectMetadata:
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
            return StoredObjectMetadata(
                byte_length=int(response["ContentLength"]),
                content_type=response.get("ContentType"),
            )
        except Exception as exc:
            raise ReportStorageError("report object metadata read failed") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise ReportStorageError("report object cleanup failed") from exc


@dataclass(frozen=True, slots=True)
class PreparedReportArtifact:
    report_id: UUID
    analysis_id: UUID
    report_artifact_version: str
    state: str
    analysis_fingerprint: str
    report_schema_version: str
    report_projection_version: str
    narrative_prompt_version: str
    narrative_schema_version: str
    narrative_provider: str
    narrative_model_id: str | None
    narrative_generation_mode: str | None
    narrative_fallback_version: str | None
    presentation_schema_version: str
    presentation_policy_version: str
    template_version: str
    stylesheet_version: str
    chart_version: str
    renderer_version: str
    generated_at: datetime
    content_sha256: str | None
    mime_type: str | None
    filename: str | None
    byte_length: int | None
    storage_key: str | None
    failure_code: str | None
    failure_message: str | None


@dataclass(frozen=True, slots=True)
class RetrievedReportResource:
    report_id: UUID
    analysis_id: UUID
    state: str
    generated_at: datetime
    analysis_fingerprint: str
    report_artifact_version: str
    report_schema_version: str
    report_projection_version: str
    narrative_prompt_version: str
    narrative_schema_version: str
    narrative_provider: str
    narrative_model_id: str | None
    narrative_generation_mode: str | None
    narrative_fallback_version: str | None
    presentation_schema_version: str
    presentation_policy_version: str
    template_version: str
    stylesheet_version: str
    chart_version: str
    renderer_version: str
    content_sha256: str | None
    mime_type: str | None
    filename: str | None
    byte_length: int | None
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


def _storage_key(consumer_id: UUID, analysis_id: UUID) -> str:
    return f"reports/{consumer_id}/{analysis_id}/{REPORT_ARTIFACT_VERSION}.pdf"


def _filename(report_id: UUID) -> str:
    return "sitescore" + f"-report-{report_id}.pdf"


def _safe_failure() -> tuple[str, str]:
    return "report_generation_failed", "report artifact generation failed"


class ReportArtifactGenerator:
    """Consumes exact live completed authority and writes one private PDF object."""

    def __init__(self, storage: ReportObjectStorage, *, max_bytes: int) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        self.storage = storage
        self.max_bytes = max_bytes

    def generate(
        self,
        *,
        consumer_id: UUID,
        analysis_id: UUID,
        outcome: CanonicalCompletedOutcome,
        generated_at: datetime,
    ) -> PreparedReportArtifact:
        canonical = require_canonical_completed_outcome(outcome)
        source = canonical.application_analysis_result
        report_id = uuid4()
        analysis_fingerprint = source.core_result.analysis_fingerprint
        model_id: str | None = None
        generation_mode: str | None = None
        fallback_version: str | None = None
        storage_key: str | None = None
        uploaded = False
        report = _report_runtime()
        try:
            facts = report.build_canonical_report_facts(source)
            domain = report.build_report_domain_model(facts)
            narrative = report.build_validated_report_narrative(
                domain,
                config=report.NarrativeProviderConfig.from_environment(),
            )
            model_id = narrative.provenance.model_id
            generation_mode = narrative.provenance.generation_mode
            fallback_version = narrative.provenance.fallback_version
            payload = report.render_report_pdf(domain, narrative)
            if not payload.startswith(b"%PDF-"):
                raise ValueError("renderer returned an invalid PDF signature")
            if len(payload) > self.max_bytes:
                raise ValueError("rendered report exceeds configured size bound")
            digest = sha256(payload).hexdigest()
            storage_key = _storage_key(consumer_id, analysis_id)
            self.storage.put(storage_key, payload, content_type=REPORT_MIME_TYPE)
            uploaded = True
            metadata = self.storage.head(storage_key)
            if metadata.byte_length != len(payload):
                raise ReportStorageError("stored report byte length mismatch")
            if metadata.content_type not in (None, REPORT_MIME_TYPE):
                raise ReportStorageError("stored report MIME type mismatch")
            return PreparedReportArtifact(
                report_id=report_id,
                analysis_id=analysis_id,
                report_artifact_version=REPORT_ARTIFACT_VERSION,
                state=REPORT_STATE_READY,
                analysis_fingerprint=analysis_fingerprint,
                report_schema_version=report.REPORT_SCHEMA_VERSION,
                report_projection_version=report.REPORT_PROJECTION_VERSION,
                narrative_prompt_version=report.NARRATIVE_PROMPT_VERSION,
                narrative_schema_version=report.NARRATIVE_SCHEMA_VERSION,
                narrative_provider=report.NARRATIVE_PROVIDER,
                narrative_model_id=model_id,
                narrative_generation_mode=generation_mode,
                narrative_fallback_version=fallback_version,
                presentation_schema_version=report.PRESENTATION_SCHEMA_VERSION,
                presentation_policy_version=report.PRESENTATION_POLICY_VERSION,
                template_version=report.TEMPLATE_VERSION,
                stylesheet_version=report.STYLESHEET_VERSION,
                chart_version=report.CHART_VERSION,
                renderer_version=report.RENDERER_VERSION,
                generated_at=generated_at,
                content_sha256=digest,
                mime_type=REPORT_MIME_TYPE,
                filename=_filename(report_id),
                byte_length=len(payload),
                storage_key=storage_key,
                failure_code=None,
                failure_message=None,
            )
        except Exception:
            if uploaded and storage_key is not None:
                try:
                    self.storage.delete(storage_key)
                except Exception:
                    pass
            code, message = _safe_failure()
            return PreparedReportArtifact(
                report_id=report_id,
                analysis_id=analysis_id,
                report_artifact_version=REPORT_ARTIFACT_VERSION,
                state=REPORT_STATE_FAILED,
                analysis_fingerprint=analysis_fingerprint,
                report_schema_version=report.REPORT_SCHEMA_VERSION,
                report_projection_version=report.REPORT_PROJECTION_VERSION,
                narrative_prompt_version=report.NARRATIVE_PROMPT_VERSION,
                narrative_schema_version=report.NARRATIVE_SCHEMA_VERSION,
                narrative_provider=report.NARRATIVE_PROVIDER,
                narrative_model_id=model_id,
                narrative_generation_mode=generation_mode,
                narrative_fallback_version=fallback_version,
                presentation_schema_version=report.PRESENTATION_SCHEMA_VERSION,
                presentation_policy_version=report.PRESENTATION_POLICY_VERSION,
                template_version=report.TEMPLATE_VERSION,
                stylesheet_version=report.STYLESHEET_VERSION,
                chart_version=report.CHART_VERSION,
                renderer_version=report.RENDERER_VERSION,
                generated_at=generated_at,
                content_sha256=None,
                mime_type=None,
                filename=None,
                byte_length=None,
                storage_key=None,
                failure_code=code,
                failure_message=message,
            )

    def compensate(self, artifact: PreparedReportArtifact) -> None:
        if artifact.state != REPORT_STATE_READY or artifact.storage_key is None:
            return
        try:
            self.storage.delete(artifact.storage_key)
        except Exception:
            pass


def persist_report_artifact(
    session: Session,
    analysis: AnalysisModel,
    artifact: PreparedReportArtifact,
    *,
    now: datetime,
) -> ReportModel:
    if analysis.analysis_id != artifact.analysis_id:
        raise ValueError("report artifact analysis binding mismatch")
    existing = session.scalar(
        select(ReportModel).where(
            ReportModel.analysis_id == analysis.analysis_id,
            ReportModel.report_artifact_version == artifact.report_artifact_version,
        )
    )
    if existing is not None:
        if existing.report_id != artifact.report_id:
            raise ReportInvariantViolation()
        return existing
    row = ReportModel(
        report_id=artifact.report_id,
        analysis_id=artifact.analysis_id,
        report_artifact_version=artifact.report_artifact_version,
        state=artifact.state,
        analysis_fingerprint=artifact.analysis_fingerprint,
        report_schema_version=artifact.report_schema_version,
        report_projection_version=artifact.report_projection_version,
        narrative_prompt_version=artifact.narrative_prompt_version,
        narrative_schema_version=artifact.narrative_schema_version,
        narrative_provider=artifact.narrative_provider,
        narrative_model_id=artifact.narrative_model_id,
        narrative_generation_mode=artifact.narrative_generation_mode,
        narrative_fallback_version=artifact.narrative_fallback_version,
        presentation_schema_version=artifact.presentation_schema_version,
        presentation_policy_version=artifact.presentation_policy_version,
        template_version=artifact.template_version,
        stylesheet_version=artifact.stylesheet_version,
        chart_version=artifact.chart_version,
        renderer_version=artifact.renderer_version,
        generated_at=artifact.generated_at,
        content_sha256=artifact.content_sha256,
        mime_type=artifact.mime_type,
        filename=artifact.filename,
        byte_length=artifact.byte_length,
        storage_key=artifact.storage_key,
        failure_code=artifact.failure_code,
        failure_message=artifact.failure_message,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    return row


def _resource(row: ReportModel) -> RetrievedReportResource:
    return RetrievedReportResource(
        report_id=row.report_id,
        analysis_id=row.analysis_id,
        state=row.state,
        generated_at=row.generated_at,
        analysis_fingerprint=row.analysis_fingerprint,
        report_artifact_version=row.report_artifact_version,
        report_schema_version=row.report_schema_version,
        report_projection_version=row.report_projection_version,
        narrative_prompt_version=row.narrative_prompt_version,
        narrative_schema_version=row.narrative_schema_version,
        narrative_provider=row.narrative_provider,
        narrative_model_id=row.narrative_model_id,
        narrative_generation_mode=row.narrative_generation_mode,
        narrative_fallback_version=row.narrative_fallback_version,
        presentation_schema_version=row.presentation_schema_version,
        presentation_policy_version=row.presentation_policy_version,
        template_version=row.template_version,
        stylesheet_version=row.stylesheet_version,
        chart_version=row.chart_version,
        renderer_version=row.renderer_version,
        content_sha256=row.content_sha256,
        mime_type=row.mime_type,
        filename=row.filename,
        byte_length=row.byte_length,
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresReportArtifactBackend:
    def __init__(self, database: Database, storage: ReportObjectStorage, *, max_bytes: int) -> None:
        self.database = database
        self.storage = storage
        self.max_bytes = max_bytes

    def resolve(self, analysis_id: UUID, *, consumer_id: UUID) -> RetrievedReportResource:
        with self.database.session() as session:
            analysis = session.scalar(
                select(AnalysisModel).where(
                    AnalysisModel.analysis_id == analysis_id,
                    AnalysisModel.consumer_id == consumer_id,
                )
            )
            if analysis is None:
                raise ReportNotFound()
            if analysis.state in {"queued", "running"}:
                raise ReportNotYetReportable()
            if analysis.state in {"not_score_ready", "failed", "timed_out"}:
                raise AnalysisNotReportable()
            if analysis.state != "completed":
                raise ReportInvariantViolation()
            row = session.scalar(
                select(ReportModel).where(
                    ReportModel.analysis_id == analysis_id,
                    ReportModel.report_artifact_version == REPORT_ARTIFACT_VERSION,
                )
            )
            if row is None:
                raise ReportInvariantViolation()
            return _resource(row)

    def retrieve(self, report_id: UUID, *, consumer_id: UUID) -> RetrievedReportResource:
        with self.database.session() as session:
            row = session.scalar(
                select(ReportModel)
                .join(AnalysisModel, AnalysisModel.analysis_id == ReportModel.analysis_id)
                .where(
                    ReportModel.report_id == report_id,
                    AnalysisModel.consumer_id == consumer_id,
                )
            )
            if row is None:
                raise ReportNotFound()
            return _resource(row)

    def content(self, report_id: UUID, *, consumer_id: UUID) -> tuple[RetrievedReportResource, bytes]:
        with self.database.session() as session:
            row = session.scalar(
                select(ReportModel)
                .join(AnalysisModel, AnalysisModel.analysis_id == ReportModel.analysis_id)
                .where(
                    ReportModel.report_id == report_id,
                    AnalysisModel.consumer_id == consumer_id,
                )
            )
            if row is None:
                raise ReportNotFound()
            resource = _resource(row)
            if row.state != REPORT_STATE_READY:
                raise ReportContentUnavailable()
            if (
                row.storage_key is None
                or row.content_sha256 is None
                or row.byte_length is None
                or row.mime_type != REPORT_MIME_TYPE
                or row.filename is None
            ):
                raise ReportArtifactIntegrityError()
            try:
                metadata = self.storage.head(row.storage_key)
                if metadata.byte_length != row.byte_length:
                    raise ReportArtifactIntegrityError()
                if metadata.content_type not in (None, row.mime_type):
                    raise ReportArtifactIntegrityError()
                payload = self.storage.get(row.storage_key, max_bytes=self.max_bytes)
            except ReportArtifactIntegrityError:
                raise
            except Exception as exc:
                raise ReportArtifactIntegrityError() from exc
            if len(payload) != row.byte_length:
                raise ReportArtifactIntegrityError()
            if sha256(payload).hexdigest() != row.content_sha256:
                raise ReportArtifactIntegrityError()
            if not payload.startswith(b"%PDF-"):
                raise ReportArtifactIntegrityError()
            return resource, payload
