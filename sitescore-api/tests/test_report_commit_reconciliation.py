from __future__ import annotations

from pathlib import Path
import os
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_TESTS = REPO_ROOT / "sitescore-report" / "tests"
DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")


def _run(body: str) -> None:
    if not DATABASE_URL:
        pytest.skip("real PostgreSQL report reconciliation test requires SITESCORE_DATABASE_URL")
    sys.path.insert(0, str(REPORT_TESTS))
    try:
        from test_report_projection_authority import _run as locked_report_run
        locked_report_run(body)
    finally:
        sys.path.pop(0)


def test_ready_commit_ack_loss_reconciles_without_deleting_object_and_mismatch_fails_closed():
    _run(r'''
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from sitescore_api.app import create_app
from sitescore_api.auth import provision_service_key
from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ReportModel
from sitescore_api.execution import ExecutionResult
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.outcomes import build_canonical_completed_outcome
from sitescore_api.report_artifacts import PostgresReportArtifactBackend, ReportArtifactGenerator, StoredObjectMetadata
from sitescore_api.settings import Settings
from sitescore_api.worker import AnalysisWorkerService


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.delete_calls = []

    def put(self, key, payload, *, content_type):
        self.objects[key] = (bytes(payload), content_type)

    def get(self, key, *, max_bytes):
        payload = self.objects[key][0]
        assert len(payload) <= max_bytes
        return payload

    def head(self, key):
        payload, content_type = self.objects[key]
        return StoredObjectMetadata(len(payload), content_type)

    def delete(self, key):
        self.delete_calls.append(key)
        self.objects.pop(key, None)


source = build_scored("gym")
outcome = build_canonical_completed_outcome(source)


class ExactExecutor:
    def __init__(self):
        self.calls = 0

    def execute(self, command, *, now):
        self.calls += 1
        return ExecutionResult(completed=outcome)


class CapturingGenerator(ReportArtifactGenerator):
    def __init__(self, storage):
        super().__init__(storage, max_bytes=2_000_000)
        self.seen = []
        self.generated = None

    def generate(self, **kwargs):
        candidate = kwargs["outcome"]
        assert candidate is outcome
        assert candidate.application_analysis_result is source
        self.seen.append(candidate)
        artifact = super().generate(**kwargs)
        assert artifact.state == "ready"
        assert artifact.storage_key in self.storage.objects
        self.generated = artifact
        return artifact


class AckLossWorker(AnalysisWorkerService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ack_loss_injected = False

    def _commit_report_metadata(self, session):
        # Target only the report-metadata commit seam. The real COMMIT completes
        # first; then the caller loses only the acknowledgement exactly once.
        super()._commit_report_metadata(session)
        if not self.ack_loss_injected:
            self.ack_loss_injected = True
            raise RuntimeError("synthetic report commit acknowledgement loss")


class NoopDispatcher:
    def dispatch_analysis(self, analysis_id):
        return None


database = Database(os.environ["SITESCORE_DATABASE_URL"])
with database.engine.begin() as conn:
    conn.execute(text("TRUNCATE reports, dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))

consumer_id = uuid4()
analysis_id = uuid4()
now = datetime.now(timezone.utc)
payload = {
    "sector": "gym",
    "location": {
        "country_code": "US",
        "street": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
    },
    "business_inputs": {
        "target_population": 80000,
        "penetration_rate_conservative": 0.01,
        "penetration_rate_base": 0.02,
        "penetration_rate_optimistic": 0.03,
        "usable_area": 9000,
        "members_per_area_unit": 0.12,
        "monthly_membership_fee": 55.0,
    },
    "costs": {
        "monthly_rent": 5000,
        "fixed_labor": 12000,
        "fixed_overhead": 3000,
    },
}
with database.session() as session:
    with session.begin():
        session.add(
            ConsumerModel(
                consumer_id=consumer_id,
                name="rpt55-h002",
                active=True,
                created_at=now,
            )
        )
        session.flush()
        session.add(
            AnalysisModel(
                analysis_id=analysis_id,
                consumer_id=consumer_id,
                creation_request_id=uuid4(),
                api_version="v1",
                state="queued",
                request_payload=payload,
                request_hash="0" * 64,
                idempotency_key="rpt55-h002",
                task_id=uuid4(),
                created_at=now,
                updated_at=now,
                started_at=None,
                finished_at=None,
                deadline_at=now + timedelta(minutes=15),
                result_body=None,
                readiness_body=None,
                failure_code=None,
                failure_message=None,
            )
        )

storage = MemoryStorage()
generator = CapturingGenerator(storage)
executor = ExactExecutor()
worker = AckLossWorker(database, executor, generator)

assert worker.execute_analysis(analysis_id) == "completed"
assert worker.ack_loss_injected is True
assert executor.calls == 1
assert generator.seen == [outcome]
assert generator.generated is not None
artifact = generator.generated

# The real report-ready COMMIT happened before the synthetic ACK loss. Fresh
# reconciliation must prove that exact durable row and KEEP the exact object.
with database.session() as session:
    analysis = session.get(AnalysisModel, analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == analysis_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.report_id == artifact.report_id
    assert report.state == "ready"
    assert report.analysis_fingerprint == artifact.analysis_fingerprint
    assert report.content_sha256 == artifact.content_sha256
    assert report.byte_length == artifact.byte_length
    assert report.mime_type == artifact.mime_type
    assert report.filename == artifact.filename
    assert report.storage_key == artifact.storage_key

assert storage.delete_calls == []
assert artifact.storage_key in storage.objects

# Prove the retained ready resource is actually deliverable through the real
# content endpoint, while the canonical executor remains single-shot.
PEPPER = "test-only-rpt55-h002-pepper-0123456789-abcdefghijklmnopqrstuvwxyz"
with database.session() as session:
    with session.begin():
        token = provision_service_key(
            session,
            consumer_id=consumer_id,
            scopes={"report:write", "report:read"},
            pepper=PEPPER,
        )
settings = Settings(
    database_url=os.environ["SITESCORE_DATABASE_URL"],
    broker_url="redis://127.0.0.1:6379/0",
    api_key_pepper=PEPPER,
)
lifecycle = PostgresAnalysisLifecycleBackend(database, NoopDispatcher(), deadline_seconds=900)
reports = PostgresReportArtifactBackend(database, storage, max_bytes=2_000_000)
runtime = SimpleNamespace(settings=settings, database=database, lifecycle=lifecycle, reports=reports)
client = TestClient(create_app(runtime), raise_server_exceptions=False)
metadata = client.get(
    f"/v1/reports/{artifact.report_id}",
    headers={"Authorization": f"Bearer {token}"},
)
assert metadata.status_code == 200
assert metadata.json()["state"] == "ready"
content = client.get(
    f"/v1/reports/{artifact.report_id}/content",
    headers={"Authorization": f"Bearer {token}"},
)
assert content.status_code == 200
assert content.content.startswith(b"%PDF-")
assert executor.calls == 1

# Same report_id is not sufficient for idempotent equivalence. Corrupt one
# content-semantic binding, then exercise the production finalization path with
# the original exact artifact. It must fail closed rather than accept the row.
with database.session() as session:
    with session.begin():
        report = session.scalar(
            select(ReportModel)
            .where(ReportModel.report_id == artifact.report_id)
            .with_for_update()
        )
        assert report is not None
        report.content_sha256 = "f" * 64

with database.session() as session:
    worker._persist_report_after_completed(
        session,
        analysis_id=analysis_id,
        artifact=artifact,
    )

with database.session() as session:
    analysis = session.get(AnalysisModel, analysis_id)
    report = session.get(ReportModel, artifact.report_id)
    assert analysis is not None and analysis.state == "completed"
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state == "failed"
    assert report.storage_key is None
    assert report.content_sha256 is None
    assert report.byte_length is None
    assert report.mime_type is None
    assert report.filename is None
    assert report.failure_code == "report_generation_failed"
    assert report.failure_message == "report artifact generation failed"

assert storage.delete_calls == [artifact.storage_key]
assert artifact.storage_key not in storage.objects
assert executor.calls == 1
''')
