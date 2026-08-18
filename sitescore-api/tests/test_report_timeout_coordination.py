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
        pytest.skip("real PostgreSQL report timeout-coordination test requires SITESCORE_DATABASE_URL")
    sys.path.insert(0, str(REPORT_TESTS))
    try:
        from test_report_projection_authority import _run as locked_report_run
        locked_report_run(body)
    finally:
        sys.path.pop(0)


def test_h005_canonical_success_survives_reconciler_polling_and_retry_deadline_crossing():
    _run(r'''
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import uuid4

from sqlalchemy import select, text

from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ReportModel
from sitescore_api.execution import ExecutionResult
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.outcomes import build_canonical_completed_outcome
from sitescore_api.report_artifacts import ReportArtifactGenerator, StoredObjectMetadata
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


class ControlledClockWorker(AnalysisWorkerService):
    def __init__(self, *args, clock, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock = clock

    def _now(self):
        return self.clock


class BlockingGenerator(ReportArtifactGenerator):
    def __init__(self, storage, entered, release):
        super().__init__(storage, max_bytes=2_000_000)
        self.entered = entered
        self.release = release

    def generate(self, **kwargs):
        self.entered.set()
        assert self.release.wait(10), "test did not release blocked report generation"
        return super().generate(**kwargs)


class FixedClockLifecycle(PostgresAnalysisLifecycleBackend):
    def __init__(self, *args, clock, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock = clock

    def _now(self):
        return self.clock


class NoopDispatcher:
    def dispatch_analysis(self, analysis_id):
        return None


class UnknownCommitWorker(ControlledClockWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.injected = False
        self.unknown_once = False

    def _commit_report_metadata(self, session):
        if not self.injected:
            self.injected = True
            session.rollback()
            raise RuntimeError("synthetic paired commit transport failure")
        return super()._commit_report_metadata(session)

    def _reconcile_paired_commit(self, outcome_arg, artifact):
        if self.injected and not self.unknown_once:
            self.unknown_once = True
            return "unknown"
        return super()._reconcile_paired_commit(outcome_arg, artifact)


database = Database(os.environ["SITESCORE_DATABASE_URL"])
with database.engine.begin() as conn:
    conn.execute(text("TRUNCATE reports, dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))

base = datetime.now(timezone.utc)


def seed(label, *, deadline_at):
    consumer_id = uuid4()
    analysis_id = uuid4()
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
                    created_at=base,
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
                    created_at=base,
                    updated_at=base,
                    started_at=None,
                    finished_at=None,
                    deadline_at=deadline_at,
                    canonical_success_at=None,
                    result_body=None,
                    readiness_body=None,
                    failure_code=None,
                    failure_message=None,
                )
            )
    return consumer_id, analysis_id


# 6.1 — canonical success is durably marked before report generation. Once that
# marker exists, the real timeout reconciler must not rewrite success to timed_out.
reconcile_deadline = base + timedelta(seconds=30)
reconcile_consumer, reconcile_id = seed(
    "rpt55-h005-reconciler",
    deadline_at=reconcile_deadline,
)
reconcile_storage = MemoryStorage()
reconcile_executor = ExactExecutor()
entered = Event(); release = Event()
reconcile_worker = ControlledClockWorker(
    database,
    reconcile_executor,
    BlockingGenerator(reconcile_storage, entered, release),
    clock=base + timedelta(seconds=1),
)
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(reconcile_worker.execute_analysis, reconcile_id)
    assert entered.wait(10)
    with database.session() as session:
        row = session.get(AnalysisModel, reconcile_id)
        assert row is not None and row.state == "running"
        assert row.canonical_success_at == base + timedelta(seconds=1)
        assert row.canonical_success_at < row.deadline_at
        assert row.result_body is None
    reconcile_worker.clock = reconcile_deadline + timedelta(seconds=1)
    assert reconcile_worker.reconcile_expired() == 0
    with database.session() as session:
        row = session.get(AnalysisModel, reconcile_id)
        assert row is not None and row.state == "running"
        assert row.canonical_success_at is not None
        assert row.failure_code is None and row.failure_message is None
    release.set()
    assert future.result(timeout=20) == "completed"

with database.session() as session:
    analysis = session.get(AnalysisModel, reconcile_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == reconcile_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.canonical_success_at == base + timedelta(seconds=1)
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state in {"ready", "failed"}

# 6.2 — the real lifecycle retrieval path sees an expired public `running` row,
# but must preserve it once canonical success was achieved before the deadline.
poll_deadline = base + timedelta(seconds=40)
poll_consumer, poll_id = seed("rpt55-h005-poll", deadline_at=poll_deadline)
poll_storage = MemoryStorage(); poll_executor = ExactExecutor()
poll_entered = Event(); poll_release = Event()
poll_worker = ControlledClockWorker(
    database,
    poll_executor,
    BlockingGenerator(poll_storage, poll_entered, poll_release),
    clock=base + timedelta(seconds=2),
)
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(poll_worker.execute_analysis, poll_id)
    assert poll_entered.wait(10)
    backend = FixedClockLifecycle(
        database,
        NoopDispatcher(),
        deadline_seconds=900,
        clock=poll_deadline + timedelta(seconds=1),
    )
    retrieved = backend.retrieve(poll_id, consumer_id=poll_consumer)
    assert retrieved.state == "running"
    assert retrieved.error is None
    with database.session() as session:
        row = session.get(AnalysisModel, poll_id)
        assert row is not None and row.state == "running"
        assert row.canonical_success_at == base + timedelta(seconds=2)
        assert row.failure_code is None
    poll_worker.clock = poll_deadline + timedelta(seconds=1)
    poll_release.set()
    assert future.result(timeout=20) == "completed"

with database.session() as session:
    analysis = session.get(AnalysisModel, poll_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == poll_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state in {"ready", "failed"}

# 6.3 — H002 unknown after a genuine pre-deadline success leaves the success
# marker durable. A fresh worker retry after the original deadline is allowed to
# rerun canonical execution and finish the pair; the API never grants rerun authority.
retry_deadline = base + timedelta(seconds=50)
_, retry_id = seed("rpt55-h005-retry", deadline_at=retry_deadline)
retry_storage = MemoryStorage(); retry_executor = ExactExecutor()
first_retry_worker = UnknownCommitWorker(
    database,
    retry_executor,
    ReportArtifactGenerator(retry_storage, max_bytes=2_000_000),
    clock=base + timedelta(seconds=3),
)
try:
    first_retry_worker.execute_analysis(retry_id)
except RetryableReportFinalization:
    pass
else:
    raise AssertionError("unknown paired commit must request worker retry")
assert first_retry_worker.injected is True and first_retry_worker.unknown_once is True
with database.session() as session:
    analysis = session.get(AnalysisModel, retry_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == retry_id))
    assert analysis is not None and analysis.state == "running"
    assert analysis.canonical_success_at == base + timedelta(seconds=3)
    assert analysis.result_body is None
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is None
assert retry_storage.objects, "unknown outcome must not destructively discard candidate storage"

fresh_retry_worker = ControlledClockWorker(
    database,
    retry_executor,
    ReportArtifactGenerator(retry_storage, max_bytes=2_000_000),
    clock=retry_deadline + timedelta(seconds=5),
)
assert fresh_retry_worker.execute_analysis(retry_id) == "completed"
assert retry_executor.calls == 2
with database.session() as session:
    analysis = session.get(AnalysisModel, retry_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == retry_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.canonical_success_at == base + timedelta(seconds=3)
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state in {"ready", "failed"}

# 6.4 — regression guard: without the durable canonical-success marker, all three
# locked 5.1 timeout writers remain authoritative after deadline.
expired_clock = base + timedelta(hours=1)

retrieve_consumer, retrieve_id = seed(
    "rpt55-h005-pre-success-retrieve",
    deadline_at=base + timedelta(minutes=1),
)
pre_success_backend = FixedClockLifecycle(
    database,
    NoopDispatcher(),
    deadline_seconds=900,
    clock=expired_clock,
)
retrieved = pre_success_backend.retrieve(retrieve_id, consumer_id=retrieve_consumer)
assert retrieved.state == "timed_out"
assert retrieved.error is not None and retrieved.error["code"] == "analysis_deadline_exceeded"

_, reconcile_expired_id = seed(
    "rpt55-h005-pre-success-reconciler",
    deadline_at=base + timedelta(minutes=2),
)
pre_success_reconciler = ControlledClockWorker(
    database,
    ExactExecutor(),
    None,
    clock=expired_clock,
)
assert pre_success_reconciler.reconcile_expired() == 1
with database.session() as session:
    row = session.get(AnalysisModel, reconcile_expired_id)
    assert row is not None and row.state == "timed_out"
    assert row.canonical_success_at is None
    assert row.failure_code == "analysis_deadline_exceeded"

_, execute_expired_id = seed(
    "rpt55-h005-pre-success-execute",
    deadline_at=base + timedelta(minutes=3),
)
entry_executor = ExactExecutor()
pre_success_entry = ControlledClockWorker(
    database,
    entry_executor,
    None,
    clock=expired_clock,
)
assert pre_success_entry.execute_analysis(execute_expired_id) == "timed_out"
assert entry_executor.calls == 0
with database.session() as session:
    row = session.get(AnalysisModel, execute_expired_id)
    assert row is not None and row.state == "timed_out"
    assert row.canonical_success_at is None
    assert row.failure_code == "analysis_deadline_exceeded"
''')
