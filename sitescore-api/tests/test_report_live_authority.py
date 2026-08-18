from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import textwrap

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_TESTS = REPO_ROOT / "sitescore-report" / "tests"
DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")


def _prefix() -> str:
    sys.path.insert(0, str(REPORT_TESTS))
    try:
        from test_report_projection_authority import PREFIX
        return PREFIX
    finally:
        sys.path.pop(0)


def _run(body: str, *, database: bool = False) -> None:
    if database and not DATABASE_URL:
        pytest.skip("real PostgreSQL live-authority worker test requires SITESCORE_DATABASE_URL")
    env = dict(os.environ)
    env.pop("SITESCORE_NARRATIVE_MODEL_ID", None)
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(_prefix() + "\n" + body)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


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
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, text

from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ReportModel
from sitescore_api.execution import ExecutionResult
from sitescore_api.outcomes import build_canonical_completed_outcome
from sitescore_api.report_artifacts import ReportArtifactGenerator, StoredObjectMetadata
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
