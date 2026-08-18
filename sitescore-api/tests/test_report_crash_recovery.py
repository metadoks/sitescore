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
        pytest.skip("real PostgreSQL report crash-recovery test requires SITESCORE_DATABASE_URL")
    sys.path.insert(0, str(REPORT_TESTS))
    try:
        from test_report_projection_authority import _run as locked_report_run
        locked_report_run(body)
    finally:
        sys.path.pop(0)


def test_h003_process_loss_generator_exception_and_unknown_commit_are_recoverable():
    _run(r'''
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, text

from sitescore_api.celery_app import build_celery
from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ReportModel
from sitescore_api.execution import ExecutionResult
from sitescore_api.outcomes import build_canonical_completed_outcome
from sitescore_api.report_artifacts import ReportArtifactGenerator, StoredObjectMetadata
from sitescore_api.settings import Settings
from sitescore_api.worker import AnalysisWorkerService, RetryableReportFinalization


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
        self.generated = []

    def generate(self, **kwargs):
        assert kwargs["outcome"] is outcome
        artifact = super().generate(**kwargs)
        self.generated.append(artifact)
        return artifact


class SimulatedProcessLoss(BaseException):
    pass


class CrashBeforePairWorker(AnalysisWorkerService):
    def _before_paired_terminal_commit(self, artifact):
        raise SimulatedProcessLoss("synthetic process loss before terminal pair commit")


class RaisingGenerator(ReportArtifactGenerator):
    def generate(self, **kwargs):
        raise RuntimeError("unexpected generator boundary failure")


class UnknownCommitWorker(AnalysisWorkerService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.injected = False
        self.unknown_once = False

    def _commit_report_metadata(self, session):
        if not self.injected:
            self.injected = True
            session.rollback()
            raise RuntimeError("synthetic database commit transport failure")
        return super()._commit_report_metadata(session)

    def _reconcile_paired_commit(self, outcome, artifact):
        if self.injected and not self.unknown_once:
            self.unknown_once = True
            return "unknown"
        return super()._reconcile_paired_commit(outcome, artifact)


database = Database(os.environ["SITESCORE_DATABASE_URL"])
with database.engine.begin() as conn:
    conn.execute(text("TRUNCATE reports, dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))


def seed(label):
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
                    name=label,
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
                    idempotency_key=label,
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
    return consumer_id, analysis_id


# Production Celery semantics must redeliver a process-lost late-ack task.
settings = Settings(
    database_url=os.environ["SITESCORE_DATABASE_URL"],
    broker_url="redis://127.0.0.1:6379/0",
    api_key_pepper="h003-test-pepper-0123456789-abcdefghijklmnopqrstuvwxyz",
)
celery = build_celery(settings)
assert celery.conf.task_acks_late is True
assert celery.conf.task_reject_on_worker_lost is True

# 5.1 — process-loss-equivalent after live canonical success and PDF preparation,
# but before the paired terminal DB commit. Analysis must remain nonterminal.
_, crash_analysis_id = seed("rpt55-h003-crash")
crash_storage = MemoryStorage()
crash_executor = ExactExecutor()
crash_generator = CapturingGenerator(crash_storage)
crash_worker = CrashBeforePairWorker(database, crash_executor, crash_generator)
try:
    crash_worker.execute_analysis(crash_analysis_id)
except SimulatedProcessLoss:
    pass
else:
    raise AssertionError("process-loss seam must escape normal worker return")

with database.session() as session:
    analysis = session.get(AnalysisModel, crash_analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == crash_analysis_id))
    assert analysis is not None and analysis.state == "running"
    assert analysis.result_body is None
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is None

# Fresh worker redelivery is worker authority, not POST/JSON authority. It reruns
# the canonical executor and reaches one durable terminal analysis/report pair.
fresh_crash_worker = AnalysisWorkerService(
    database,
    crash_executor,
    CapturingGenerator(crash_storage),
)
assert fresh_crash_worker.execute_analysis(crash_analysis_id) == "completed"
assert crash_executor.calls == 2
with database.session() as session:
    analysis = session.get(AnalysisModel, crash_analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == crash_analysis_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state in {"ready", "failed"}

# 5.2 — unexpected generator boundary exception must not produce a normal
# completed+missing return. It is an explicit worker-retry condition.
_, generator_analysis_id = seed("rpt55-h003-generator")
generator_storage = MemoryStorage()
generator_executor = ExactExecutor()
raising_worker = AnalysisWorkerService(
    database,
    generator_executor,
    RaisingGenerator(generator_storage, max_bytes=2_000_000),
)
try:
    raising_worker.execute_analysis(generator_analysis_id)
except RetryableReportFinalization:
    pass
else:
    raise AssertionError("unexpected generator exception must request worker retry")
with database.session() as session:
    analysis = session.get(AnalysisModel, generator_analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == generator_analysis_id))
    assert analysis is not None and analysis.state == "running"
    assert analysis.result_body is None
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is None

fresh_generator_worker = AnalysisWorkerService(
    database,
    generator_executor,
    CapturingGenerator(generator_storage),
)
assert fresh_generator_worker.execute_analysis(generator_analysis_id) == "completed"
assert generator_executor.calls == 2
with database.session() as session:
    analysis = session.get(AnalysisModel, generator_analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == generator_analysis_id))
    assert analysis is not None and analysis.state == "completed"
    assert report is not None and report.state in {"ready", "failed"}
    assert analysis.failure_code is None and analysis.failure_message is None

# 5.3 — commit not actually performed + temporarily unavailable reconciliation.
# Unknown must retain the candidate object and request worker retry; after DB
# recovery a fresh worker deterministically replaces/reconciles it and terminates.
_, unknown_analysis_id = seed("rpt55-h003-unknown")
unknown_storage = MemoryStorage()
unknown_executor = ExactExecutor()
unknown_generator = CapturingGenerator(unknown_storage)
unknown_worker = UnknownCommitWorker(database, unknown_executor, unknown_generator)
try:
    unknown_worker.execute_analysis(unknown_analysis_id)
except RetryableReportFinalization:
    pass
else:
    raise AssertionError("unknown paired commit must request worker retry")
assert unknown_worker.injected is True and unknown_worker.unknown_once is True
assert len(unknown_generator.generated) == 1
unknown_artifact = unknown_generator.generated[0]
assert unknown_artifact.storage_key in unknown_storage.objects
with database.session() as session:
    analysis = session.get(AnalysisModel, unknown_analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == unknown_analysis_id))
    assert analysis is not None and analysis.state == "running"
    assert analysis.result_body is None
    assert report is None

fresh_unknown_worker = AnalysisWorkerService(
    database,
    unknown_executor,
    CapturingGenerator(unknown_storage),
)
assert fresh_unknown_worker.execute_analysis(unknown_analysis_id) == "completed"
assert unknown_executor.calls == 2
with database.session() as session:
    analysis = session.get(AnalysisModel, unknown_analysis_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == unknown_analysis_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state in {"ready", "failed"}
''')


def test_h004_different_report_id_conflict_fails_actual_resource_closed():
    _run(r'''
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, text

from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ReportModel
from sitescore_api.execution import ExecutionResult
from sitescore_api.outcomes import build_canonical_completed_outcome
from sitescore_api.report_artifacts import (
    ReportArtifactGenerator,
    StoredObjectMetadata,
    persist_report_artifact,
)
from sitescore_api.worker import AnalysisWorkerService


class AuditedStorage:
    def __init__(self):
        self.objects = {}
        self.delete_calls = []
        self.database = None
        self.analysis_id = None

    def put(self, key, payload, *, content_type):
        self.objects[key] = (bytes(payload), content_type)

    def get(self, key, *, max_bytes):
        return self.objects[key][0]

    def head(self, key):
        payload, content_type = self.objects[key]
        return StoredObjectMetadata(len(payload), content_type)

    def delete(self, key):
        # Destructive compensation is allowed only after the actual durable
        # conflicting row is already fail-closed.
        if self.database is not None and self.analysis_id is not None:
            with self.database.session() as session:
                row = session.scalar(
                    select(ReportModel).where(ReportModel.analysis_id == self.analysis_id)
                )
                assert row is not None and row.state == "failed"
                assert row.storage_key is None and row.content_sha256 is None
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
        self.generated = None
    def generate(self, **kwargs):
        artifact = super().generate(**kwargs)
        self.generated = artifact
        return artifact


database = Database(os.environ["SITESCORE_DATABASE_URL"])
with database.engine.begin() as conn:
    conn.execute(text("TRUNCATE reports, dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))

consumer_id = uuid4(); analysis_id = uuid4(); now = datetime.now(timezone.utc)
payload = {
    "sector": "gym",
    "location": {
        "country_code": "US", "street": "123 Main St", "city": "Austin",
        "state": "TX", "zip_code": "78701"
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
    "costs": {"monthly_rent": 5000, "fixed_labor": 12000, "fixed_overhead": 3000},
}
with database.session() as session:
    with session.begin():
        session.add(ConsumerModel(
            consumer_id=consumer_id, name="rpt55-h004", active=True, created_at=now
        ))
        session.flush()
        session.add(AnalysisModel(
            analysis_id=analysis_id, consumer_id=consumer_id, creation_request_id=uuid4(),
            api_version="v1", state="queued", request_payload=payload, request_hash="0" * 64,
            idempotency_key="rpt55-h004", task_id=uuid4(), created_at=now, updated_at=now,
            started_at=None, finished_at=None, deadline_at=now + timedelta(minutes=15),
            result_body=None, readiness_body=None, failure_code=None, failure_message=None,
        ))

storage = AuditedStorage(); storage.database = database; storage.analysis_id = analysis_id
preexisting_generator = ReportArtifactGenerator(storage, max_bytes=2_000_000)
preexisting = preexisting_generator.generate(
    consumer_id=consumer_id,
    analysis_id=analysis_id,
    outcome=outcome,
    generated_at=now,
)
assert preexisting.state == "ready"
with database.session() as session:
    with session.begin():
        analysis = session.get(AnalysisModel, analysis_id)
        assert analysis is not None and analysis.state == "queued"
        persist_report_artifact(session, analysis, preexisting, now=now)

executor = ExactExecutor(); candidate_generator = CapturingGenerator(storage)
worker = AnalysisWorkerService(database, executor, candidate_generator)
assert worker.execute_analysis(analysis_id) == "completed"
assert executor.calls == 1
candidate = candidate_generator.generated
assert candidate is not None and candidate.report_id != preexisting.report_id

with database.session() as session:
    analysis = session.get(AnalysisModel, analysis_id)
    actual = session.scalar(
        select(ReportModel).where(
            ReportModel.analysis_id == analysis_id,
            ReportModel.report_artifact_version == candidate.report_artifact_version,
        )
    )
    assert analysis is not None and analysis.state == "completed"
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert actual is not None
    # H004: actual durable conflicting resource identity is preserved and failed.
    assert actual.report_id == preexisting.report_id
    assert actual.report_id != candidate.report_id
    assert actual.state == "failed"
    assert actual.storage_key is None
    assert actual.content_sha256 is None
    assert actual.byte_length is None
    assert actual.mime_type is None
    assert actual.filename is None
    assert actual.failure_code == "report_generation_failed"
    assert actual.failure_message == "report artifact generation failed"

assert storage.delete_calls == [candidate.storage_key]
assert candidate.storage_key not in storage.objects
''')
