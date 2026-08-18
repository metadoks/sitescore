from __future__ import annotations

from pathlib import Path
import os
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_TESTS = REPO_ROOT / "sitescore-report" / "tests"
DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")


def _run(body: str, *, database: bool = False) -> None:
    if database and not DATABASE_URL:
        pytest.skip("real PostgreSQL live-authority worker test requires SITESCORE_DATABASE_URL")
    sys.path.insert(0, str(REPORT_TESTS))
    try:
        from test_report_projection_authority import _run as locked_report_run
        locked_report_run(body)
    finally:
        sys.path.pop(0)


def test_genuine_completed_outcome_generates_exact_pdf_and_forgery_is_rejected():
    _run(r'''
from datetime import datetime, timezone
from sitescore_api.outcomes import CanonicalCompletedOutcome, build_canonical_completed_outcome
from sitescore_api.report_artifacts import ReportArtifactGenerator, StoredObjectMetadata

class MemoryStorage:
    def __init__(self): self.objects = {}
    def put(self, key, payload, *, content_type): self.objects[key] = (bytes(payload), content_type)
    def get(self, key, *, max_bytes): return self.objects[key][0]
    def head(self, key):
        payload, content_type = self.objects[key]
        return StoredObjectMetadata(len(payload), content_type)
    def delete(self, key): self.objects.pop(key, None)

source = build_scored("coffee")
outcome = build_canonical_completed_outcome(source)
storage = MemoryStorage()
generator = ReportArtifactGenerator(storage, max_bytes=2_000_000)
artifact = generator.generate(
    consumer_id=__import__("uuid").uuid4(),
    analysis_id=__import__("uuid").uuid4(),
    outcome=outcome,
    generated_at=datetime.now(timezone.utc),
)
assert artifact.state == "ready"
assert artifact.analysis_fingerprint == source.core_result.analysis_fingerprint
assert artifact.content_sha256 is not None and len(artifact.content_sha256) == 64
assert artifact.storage_key in storage.objects
payload = storage.objects[artifact.storage_key][0]
assert payload.startswith(b"%PDF-")
assert len(payload) == artifact.byte_length

forged = object.__new__(CanonicalCompletedOutcome)
object.__setattr__(forged, "application_analysis_result", source)
object.__setattr__(forged, "result_body", source.core_result.to_dict())
try:
    generator.generate(
        consumer_id=__import__("uuid").uuid4(),
        analysis_id=__import__("uuid").uuid4(),
        outcome=forged,
        generated_at=datetime.now(timezone.utc),
    )
except ValueError as exc:
    assert "server-owned" in str(exc)
else:
    raise AssertionError("forged completed outcome must not become report authority")
''')


def test_worker_passes_exact_live_identity_and_report_failure_preserves_completed():
    _run(r'''
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, text

from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ReportModel
from sitescore_api.execution import ExecutionResult
from sitescore_api.outcomes import build_canonical_completed_outcome
from sitescore_api.report_artifacts import ReportArtifactGenerator
from sitescore_api.worker import AnalysisWorkerService

class FailingStorage:
    def put(self, key, payload, *, content_type): raise RuntimeError("provider secret must not persist")
    def get(self, key, *, max_bytes): raise AssertionError("not called")
    def head(self, key): raise AssertionError("not called")
    def delete(self, key): return None

source = build_scored("restaurant")
outcome = build_canonical_completed_outcome(source)

class ExactExecutor:
    def __init__(self): self.calls = 0
    def execute(self, command, *, now):
        self.calls += 1
        return ExecutionResult(completed=outcome)

class CapturingGenerator(ReportArtifactGenerator):
    def __init__(self):
        super().__init__(FailingStorage(), max_bytes=2_000_000)
        self.seen = []
    def generate(self, **kwargs):
        candidate = kwargs["outcome"]
        assert candidate is outcome
        assert candidate.application_analysis_result is source
        self.seen.append(candidate)
        return super().generate(**kwargs)

database = Database(os.environ["SITESCORE_DATABASE_URL"])
with database.engine.begin() as conn:
    conn.execute(text("TRUNCATE reports, dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))

consumer_id = uuid4(); analysis_id = uuid4(); now = datetime.now(timezone.utc)
payload = {
    "sector": "restaurant",
    "location": {"country_code":"US","street":"123 Main St","city":"Austin","state":"TX","zip_code":"78701"},
    "business_inputs": {
        "seats":60,"turnover_per_day":2.0,"utilization_conservative":0.45,"utilization_base":0.6,
        "utilization_optimistic":0.75,"average_ticket":32.0,"operating_days_per_month":26
    },
    "costs":{"monthly_rent":5000,"fixed_labor":12000,"fixed_overhead":3000},
}
with database.session() as session:
    with session.begin():
        session.add(ConsumerModel(consumer_id=consumer_id, name="live-authority", active=True, created_at=now))
        session.flush()
        session.add(AnalysisModel(
            analysis_id=analysis_id, consumer_id=consumer_id, creation_request_id=uuid4(), api_version="v1",
            state="queued", request_payload=payload, request_hash="0"*64, idempotency_key="live-authority",
            task_id=uuid4(), created_at=now, updated_at=now, started_at=None, finished_at=None,
            deadline_at=now+timedelta(minutes=15), result_body=None, readiness_body=None,
            failure_code=None, failure_message=None,
        ))

executor = ExactExecutor(); generator = CapturingGenerator()
worker = AnalysisWorkerService(database, executor, generator)
assert worker.execute_analysis(analysis_id) == "completed"
assert executor.calls == 1
assert generator.seen == [outcome]
with database.session() as session:
    analysis = session.get(AnalysisModel, analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == analysis_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None
    assert report is not None and report.state == "failed"
    assert report.failure_code == "report_generation_failed"
    assert report.storage_key is None and report.content_sha256 is None and report.byte_length is None
    assert "provider secret" not in (report.failure_message or "")
''', database=True)


def test_post_upload_metadata_failure_compensates_and_never_regresses_completed_analysis():
    _run(r'''
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, text

import sitescore_api.worker as worker_module
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
    def __init__(self): self.calls = 0
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

class NoopDispatcher:
    def dispatch_analysis(self, analysis_id): return None

database = Database(os.environ["SITESCORE_DATABASE_URL"])
with database.engine.begin() as conn:
    conn.execute(text("TRUNCATE reports, dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))

consumer_id = uuid4(); analysis_id = uuid4(); now = datetime.now(timezone.utc)
payload = {
    "sector": "gym",
    "location": {"country_code":"US","street":"123 Main St","city":"Austin","state":"TX","zip_code":"78701"},
    "business_inputs": {
        "members_conservative":250,"members_base":350,"members_optimistic":450,
        "monthly_membership_fee":60.0,"monthly_ancillary_revenue":5000.0
    },
    "costs":{"monthly_rent":5000,"fixed_labor":12000,"fixed_overhead":3000},
}
with database.session() as session:
    with session.begin():
        session.add(ConsumerModel(consumer_id=consumer_id, name="rpt55-h001", active=True, created_at=now))
        session.flush()
        session.add(AnalysisModel(
            analysis_id=analysis_id, consumer_id=consumer_id, creation_request_id=uuid4(), api_version="v1",
            state="queued", request_payload=payload, request_hash="0"*64, idempotency_key="rpt55-h001",
            task_id=uuid4(), created_at=now, updated_at=now, started_at=None, finished_at=None,
            deadline_at=now+timedelta(minutes=15), result_body=None, readiness_body=None,
            failure_code=None, failure_message=None,
        ))

storage = MemoryStorage(); generator = CapturingGenerator(storage); executor = ExactExecutor()
original_persist = worker_module.persist_report_artifact
persist_calls = []
def fail_first_ready_persist(session, analysis, artifact, *, now):
    persist_calls.append(artifact.state)
    if len(persist_calls) == 1:
        assert artifact.state == "ready"
        assert artifact.storage_key in storage.objects
        raise RuntimeError("injected report metadata persistence failure after upload")
    return original_persist(session, analysis, artifact, now=now)
worker_module.persist_report_artifact = fail_first_ready_persist
try:
    worker = AnalysisWorkerService(database, executor, generator)
    assert worker.execute_analysis(analysis_id) == "completed"
finally:
    worker_module.persist_report_artifact = original_persist

assert executor.calls == 1
assert generator.seen == [outcome]
assert generator.generated is not None
assert persist_calls == ["ready", "failed"]
assert storage.delete_calls == [generator.generated.storage_key]
assert generator.generated.storage_key not in storage.objects

with database.session() as session:
    analysis = session.get(AnalysisModel, analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == analysis_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.report_id == generator.generated.report_id
    assert report.state == "failed"
    assert report.failure_code == "report_generation_failed"
    assert report.failure_message == "report artifact generation failed"
    assert report.storage_key is None
    assert report.content_sha256 is None
    assert report.byte_length is None

# Resolver-only POST must expose the same durable failed resource. It has no
# execution authority and therefore cannot rerun the canonical analysis or
# rebuild report authority from AnalysisModel.result_body JSON.
PEPPER = "test-only-rpt55-h001-pepper-0123456789-abcdefghijklmnopqrstuvwxyz"
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
resolved = client.post(
    "/v1/reports",
    json={"analysis_id": str(analysis_id)},
    headers={"Authorization": f"Bearer {token}"},
)
assert resolved.status_code == 200
assert resolved.json()["report_id"] == str(generator.generated.report_id)
assert resolved.json()["state"] == "failed"
assert resolved.json()["content_path"] is None
assert executor.calls == 1
''', database=True)
