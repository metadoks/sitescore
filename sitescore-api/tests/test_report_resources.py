from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from sitescore_api.app import create_app
from sitescore_api.auth import provision_service_key
from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ReportModel
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.report_artifacts import (
    REPORT_ARTIFACT_VERSION,
    REPORT_MIME_TYPE,
    PostgresReportArtifactBackend,
    PreparedReportArtifact,
    StoredObjectMetadata,
    persist_report_artifact,
)
from sitescore_api.settings import Settings

DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="real PostgreSQL report resource tests require SITESCORE_DATABASE_URL")
PEPPER = "test-only-pepper-0123456789-abcdefghijklmnopqrstuvwxyz"


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, payload: bytes, *, content_type: str) -> None:
        self.objects[key] = (bytes(payload), content_type)

    def get(self, key: str, *, max_bytes: int) -> bytes:
        payload = self.objects[key][0]
        if len(payload) > max_bytes:
            raise RuntimeError("too large")
        return payload

    def head(self, key: str) -> StoredObjectMetadata:
        payload, content_type = self.objects[key]
        return StoredObjectMetadata(len(payload), content_type)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class NoopDispatcher:
    def dispatch_analysis(self, analysis_id: UUID) -> None:
        return None


@pytest.fixture
def database():
    assert DATABASE_URL is not None
    db = Database(DATABASE_URL)
    with db.engine.begin() as conn:
        conn.execute(text("TRUNCATE reports, dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))
    return db


def _consumer_and_key(database: Database, scopes: set[str], *, name: str) -> tuple[UUID, str]:
    consumer_id = uuid4()
    with database.session() as session:
        with session.begin():
            session.add(ConsumerModel(
                consumer_id=consumer_id,
                name=name,
                active=True,
                created_at=datetime.now(timezone.utc),
            ))
            session.flush()
            token = provision_service_key(
                session,
                consumer_id=consumer_id,
                scopes=scopes,
                pepper=PEPPER,
            )
    return consumer_id, token


def _analysis(database: Database, consumer_id: UUID, *, state: str = "completed") -> UUID:
    analysis_id = uuid4()
    now = datetime.now(timezone.utc)
    with database.session() as session:
        with session.begin():
            session.add(AnalysisModel(
                analysis_id=analysis_id,
                consumer_id=consumer_id,
                creation_request_id=uuid4(),
                api_version="v1",
                state=state,
                request_payload={"test": True},
                request_hash="0" * 64,
                idempotency_key=f"report-test-{analysis_id}",
                task_id=uuid4(),
                created_at=now,
                updated_at=now,
                started_at=now,
                finished_at=(now if state not in {"queued", "running"} else None),
                deadline_at=now + timedelta(minutes=15),
                result_body=({"view": "not-authority"} if state == "completed" else None),
                readiness_body=None,
                failure_code=None,
                failure_message=None,
            ))
    return analysis_id


def _ready_artifact(analysis_id: UUID, payload: bytes, key: str) -> PreparedReportArtifact:
    now = datetime.now(timezone.utc)
    report_id = uuid4()
    return PreparedReportArtifact(
        report_id=report_id,
        analysis_id=analysis_id,
        report_artifact_version=REPORT_ARTIFACT_VERSION,
        state="ready",
        analysis_fingerprint="a" * 64,
        report_schema_version="sitescore-report-v1",
        report_projection_version="application-analysis-result-v1",
        narrative_prompt_version="sitescore-narrative-prompt-v2",
        narrative_schema_version="sitescore-narrative-v2",
        narrative_provider="openai",
        narrative_model_id=None,
        narrative_generation_mode="deterministic_fallback",
        narrative_fallback_version="sitescore-narrative-fallback-v2",
        presentation_schema_version="sitescore-presentation-v1",
        presentation_policy_version="sitescore-presentation-policy-v1",
        template_version="sitescore-report-template-v1",
        stylesheet_version="sitescore-report-stylesheet-v1",
        chart_version="sitescore-report-charts-v1",
        renderer_version="sitescore-pdf-renderer-v1",
        generated_at=now,
        content_sha256=sha256(payload).hexdigest(),
        mime_type=REPORT_MIME_TYPE,
        filename=f"sitescore-report-{report_id}.pdf",
        byte_length=len(payload),
        storage_key=key,
        failure_code=None,
        failure_message=None,
    )


def _failed_artifact(analysis_id: UUID) -> PreparedReportArtifact:
    now = datetime.now(timezone.utc)
    return PreparedReportArtifact(
        report_id=uuid4(),
        analysis_id=analysis_id,
        report_artifact_version=REPORT_ARTIFACT_VERSION,
        state="failed",
        analysis_fingerprint="b" * 64,
        report_schema_version="sitescore-report-v1",
        report_projection_version="application-analysis-result-v1",
        narrative_prompt_version="sitescore-narrative-prompt-v2",
        narrative_schema_version="sitescore-narrative-v2",
        narrative_provider="openai",
        narrative_model_id=None,
        narrative_generation_mode=None,
        narrative_fallback_version=None,
        presentation_schema_version="sitescore-presentation-v1",
        presentation_policy_version="sitescore-presentation-policy-v1",
        template_version="sitescore-report-template-v1",
        stylesheet_version="sitescore-report-stylesheet-v1",
        chart_version="sitescore-report-charts-v1",
        renderer_version="sitescore-pdf-renderer-v1",
        generated_at=now,
        content_sha256=None,
        mime_type=None,
        filename=None,
        byte_length=None,
        storage_key=None,
        failure_code="report_generation_failed",
        failure_message="report artifact generation failed",
    )


def _persist(database: Database, artifact: PreparedReportArtifact) -> None:
    with database.session() as session:
        with session.begin():
            analysis = session.get(AnalysisModel, artifact.analysis_id)
            assert analysis is not None
            persist_report_artifact(session, analysis, artifact, now=datetime.now(timezone.utc))


def _client(database: Database, storage: FakeStorage) -> TestClient:
    settings = Settings(
        database_url=DATABASE_URL or "",
        broker_url="redis://127.0.0.1:6379/0",
        api_key_pepper=PEPPER,
    )
    lifecycle = PostgresAnalysisLifecycleBackend(database, NoopDispatcher(), deadline_seconds=900)
    reports = PostgresReportArtifactBackend(database, storage, max_bytes=1024 * 1024)
    runtime = SimpleNamespace(settings=settings, database=database, lifecycle=lifecycle, reports=reports)
    return TestClient(create_app(runtime), raise_server_exceptions=False)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_report_resolve_replay_scopes_owner_isolation_and_content(database):
    owner_id, owner = _consumer_and_key(database, {"report:write", "report:read"}, name="owner")
    _, foreign = _consumer_and_key(database, {"report:write", "report:read"}, name="foreign")
    _, read_only = _consumer_and_key(database, {"report:read"}, name="read-only")
    analysis_id = _analysis(database, owner_id)
    payload = b"%PDF-1.7\nSiteScore exact artifact\n%%EOF\n"
    key = f"reports/{owner_id}/{analysis_id}/{REPORT_ARTIFACT_VERSION}.pdf"
    artifact = _ready_artifact(analysis_id, payload, key)
    storage = FakeStorage()
    storage.put(key, payload, content_type=REPORT_MIME_TYPE)
    _persist(database, artifact)
    client = _client(database, storage)

    first = client.post("/v1/reports", json={"analysis_id": str(analysis_id)}, headers=_auth(owner))
    second = client.post("/v1/reports", json={"analysis_id": str(analysis_id)}, headers=_auth(owner))
    assert first.status_code == second.status_code == 200
    assert first.json()["report_id"] == second.json()["report_id"] == str(artifact.report_id)
    assert first.json()["content_path"] == f"/v1/reports/{artifact.report_id}/content"
    assert "storage_key" not in first.text and "bucket" not in first.text

    extra = client.post(
        "/v1/reports",
        json={"analysis_id": str(analysis_id), "storage_key": "attacker"},
        headers=_auth(owner),
    )
    assert extra.status_code == 422
    assert client.post("/v1/reports", json={"analysis_id": str(analysis_id)}, headers=_auth(read_only)).status_code == 403

    foreign_resolve = client.post("/v1/reports", json={"analysis_id": str(analysis_id)}, headers=_auth(foreign))
    foreign_get = client.get(f"/v1/reports/{artifact.report_id}", headers=_auth(foreign))
    missing_get = client.get(f"/v1/reports/{uuid4()}", headers=_auth(foreign))
    assert foreign_resolve.status_code == foreign_get.status_code == missing_get.status_code == 404

    metadata = client.get(f"/v1/reports/{artifact.report_id}", headers=_auth(owner))
    content = client.get(f"/v1/reports/{artifact.report_id}/content", headers=_auth(owner))
    assert metadata.status_code == 200
    assert content.status_code == 200
    assert content.content == payload
    assert content.headers["content-type"].startswith("application/pdf")
    assert content.headers["content-sha256"] == sha256(payload).hexdigest()
    assert content.headers["content-disposition"] == f'attachment; filename="sitescore-report-{artifact.report_id}.pdf"'


def test_not_yet_not_reportable_failed_and_missing_ready_row_are_explicit(database):
    owner_id, token = _consumer_and_key(database, {"report:write", "report:read"}, name="owner")
    storage = FakeStorage()
    client = _client(database, storage)

    queued = _analysis(database, owner_id, state="queued")
    not_ready = _analysis(database, owner_id, state="not_score_ready")
    completed_missing = _analysis(database, owner_id, state="completed")
    assert client.post("/v1/reports", json={"analysis_id": str(queued)}, headers=_auth(token)).json()["error"]["code"] == "report_not_yet_reportable"
    assert client.post("/v1/reports", json={"analysis_id": str(not_ready)}, headers=_auth(token)).json()["error"]["code"] == "analysis_not_reportable"
    missing = client.post("/v1/reports", json={"analysis_id": str(completed_missing)}, headers=_auth(token))
    assert missing.status_code == 500
    assert missing.json()["error"]["code"] == "report_invariant_violation"

    failed_analysis = _analysis(database, owner_id, state="completed")
    failed = _failed_artifact(failed_analysis)
    _persist(database, failed)
    resolved = client.post("/v1/reports", json={"analysis_id": str(failed_analysis)}, headers=_auth(token))
    assert resolved.status_code == 200 and resolved.json()["state"] == "failed"
    assert resolved.json()["content_path"] is None
    download = client.get(f"/v1/reports/{failed.report_id}/content", headers=_auth(token))
    assert download.status_code == 409
    assert download.json()["error"]["code"] == "report_content_unavailable"
    assert not download.content.startswith(b"%PDF-")


def test_tampered_or_missing_object_never_streams(database):
    owner_id, token = _consumer_and_key(database, {"report:read"}, name="owner")
    analysis_id = _analysis(database, owner_id)
    original = b"%PDF-1.7\nORIGINAL\n%%EOF"
    key = f"reports/{owner_id}/{analysis_id}/{REPORT_ARTIFACT_VERSION}.pdf"
    artifact = _ready_artifact(analysis_id, original, key)
    storage = FakeStorage()
    storage.put(key, original, content_type=REPORT_MIME_TYPE)
    _persist(database, artifact)
    client = _client(database, storage)

    storage.put(key, b"%PDF-1.7\nTAMPERED\n%%EOF", content_type=REPORT_MIME_TYPE)
    tampered = client.get(f"/v1/reports/{artifact.report_id}/content", headers=_auth(token))
    assert tampered.status_code == 502
    assert tampered.json()["error"]["code"] == "report_artifact_integrity_failed"
    storage.delete(key)
    missing = client.get(f"/v1/reports/{artifact.report_id}/content", headers=_auth(token))
    assert missing.status_code == 502
    assert missing.json()["error"]["code"] == "report_artifact_integrity_failed"


def test_database_constraints_reject_duplicate_version_and_incoherent_ready(database):
    owner_id, _ = _consumer_and_key(database, {"report:read"}, name="owner")
    analysis_id = _analysis(database, owner_id)
    payload = b"%PDF-1.7\nX\n%%EOF"
    first = _ready_artifact(analysis_id, payload, "reports/one.pdf")
    _persist(database, first)

    with database.session() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(ReportModel(
                    report_id=uuid4(), analysis_id=analysis_id, report_artifact_version=REPORT_ARTIFACT_VERSION,
                    state="ready", analysis_fingerprint="x" * 64,
                    report_schema_version="v", report_projection_version="v",
                    narrative_prompt_version="v", narrative_schema_version="v", narrative_provider="openai",
                    narrative_model_id=None, narrative_generation_mode="deterministic_fallback", narrative_fallback_version="v",
                    presentation_schema_version="v", presentation_policy_version="v", template_version="v",
                    stylesheet_version="v", chart_version="v", renderer_version="v", generated_at=datetime.now(timezone.utc),
                    content_sha256="0" * 64, mime_type="application/pdf", filename="safe.pdf", byte_length=1,
                    storage_key="reports/other.pdf", failure_code=None, failure_message=None,
                    created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
                ))

    other_analysis = _analysis(database, owner_id)
    with database.session() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(ReportModel(
                    report_id=uuid4(), analysis_id=other_analysis, report_artifact_version=REPORT_ARTIFACT_VERSION,
                    state="ready", analysis_fingerprint="x" * 64,
                    report_schema_version="v", report_projection_version="v",
                    narrative_prompt_version="v", narrative_schema_version="v", narrative_provider="openai",
                    narrative_model_id=None, narrative_generation_mode="deterministic_fallback", narrative_fallback_version="v",
                    presentation_schema_version="v", presentation_policy_version="v", template_version="v",
                    stylesheet_version="v", chart_version="v", renderer_version="v", generated_at=datetime.now(timezone.utc),
                    content_sha256=None, mime_type=None, filename=None, byte_length=None, storage_key=None,
                    failure_code=None, failure_message=None,
                    created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
                ))
