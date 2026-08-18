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
        pytest.skip("real PostgreSQL H006 terminal-immutability test requires SITESCORE_DATABASE_URL")
    sys.path.insert(0, str(REPORT_TESTS))
    try:
        from test_report_projection_authority import _run as locked_report_run
        locked_report_run(body)
    finally:
        sys.path.pop(0)


def test_h006_pre_marker_timeout_races_never_publish_revocable_terminal_state():
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


class ControlledClockWorker(AnalysisWorkerService):
    def __init__(self, *args, clock, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock = clock

    def _now(self):
        return self.clock


class PreMarkerBlockingWorker(ControlledClockWorker):
    def __init__(self, *args, entered, release, **kwargs):
        super().__init__(*args, **kwargs)
        self.entered = entered
        self.release = release

    def _before_canonical_success_boundary(self, outcome_arg, *, success_at):
        assert outcome_arg is outcome
        self.entered.set()
        assert self.release.wait(10), "test did not release pre-marker success seam"


class FixedClockLifecycle(PostgresAnalysisLifecycleBackend):
    def __init__(self, *args, clock, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock = clock

    def _now(self):
        return self.clock


class NoopDispatcher:
    def dispatch_analysis(self, analysis_id):
        return None


class SimulatedProcessLoss(BaseException):
    pass


class BlockingLossExecutor:
    def __init__(self, entered, release):
        self.entered = entered
        self.release = release
        self.calls = 0

    def execute(self, command, *, now):
        self.calls += 1
        self.entered.set()
        assert self.release.wait(10), "test did not release no-success executor"
        raise SimulatedProcessLoss("synthetic worker loss before canonical success")


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


# 6.1 — exact canonical success exists only in worker memory. The worker still
# owns the session advisory execution lock, but canonical_success_at has not been
# committed yet. Owner polling after deadline must not publish timed_out.
poll_deadline = base + timedelta(seconds=30)
poll_consumer, poll_id = seed("rpt55-h006-poll-race", deadline_at=poll_deadline)
poll_entered = Event(); poll_release = Event()
poll_executor = ExactExecutor(); poll_storage = MemoryStorage()
poll_worker = PreMarkerBlockingWorker(
    database,
    poll_executor,
    ReportArtifactGenerator(poll_storage, max_bytes=2_000_000),
    clock=base + timedelta(seconds=1),
    entered=poll_entered,
    release=poll_release,
)
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(poll_worker.execute_analysis, poll_id)
    assert poll_entered.wait(10)
    with database.session() as session:
        row = session.get(AnalysisModel, poll_id)
        assert row is not None and row.state == "running"
        assert row.canonical_success_at is None
        assert row.failure_code is None and row.failure_message is None

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
        assert row.canonical_success_at is None
        assert row.failure_code is None and row.failure_message is None

    poll_release.set()
    assert future.result(timeout=20) == "completed"

with database.session() as session:
    analysis = session.get(AnalysisModel, poll_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == poll_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.canonical_success_at == base + timedelta(seconds=1)
    assert analysis.result_body == outcome.result_body
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state in {"ready", "failed"}

# 6.2 — the periodic timeout reconciler exercises the same pre-marker interval.
# It must skip the active execution owner instead of committing a terminal timeout.
reconcile_deadline = base + timedelta(seconds=40)
_, reconcile_id = seed("rpt55-h006-reconcile-race", deadline_at=reconcile_deadline)
reconcile_entered = Event(); reconcile_release = Event()
reconcile_executor = ExactExecutor(); reconcile_storage = MemoryStorage()
active_worker = PreMarkerBlockingWorker(
    database,
    reconcile_executor,
    ReportArtifactGenerator(reconcile_storage, max_bytes=2_000_000),
    clock=base + timedelta(seconds=2),
    entered=reconcile_entered,
    release=reconcile_release,
)
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(active_worker.execute_analysis, reconcile_id)
    assert reconcile_entered.wait(10)
    timeout_writer = ControlledClockWorker(
        database,
        ExactExecutor(),
        None,
        clock=reconcile_deadline + timedelta(seconds=1),
    )
    assert timeout_writer.reconcile_expired() == 0
    with database.session() as session:
        row = session.get(AnalysisModel, reconcile_id)
        assert row is not None and row.state == "running"
        assert row.canonical_success_at is None
        assert row.failure_code is None and row.failure_message is None

    reconcile_release.set()
    assert future.result(timeout=20) == "completed"

with database.session() as session:
    analysis = session.get(AnalysisModel, reconcile_id)
    report = session.scalar(select(ReportModel).where(ReportModel.analysis_id == reconcile_id))
    assert analysis is not None and analysis.state == "completed"
    assert analysis.canonical_success_at == base + timedelta(seconds=2)
    assert analysis.failure_code is None and analysis.failure_message is None
    assert report is not None and report.state in {"ready", "failed"}

# 6.3 — terminal states are immutable. Worker entry returns them without invoking
# canonical execution, and the canonical-success boundary itself cannot resurrect
# an already durable timed_out row even with a pre-deadline live success timestamp.
terminal_specs = {
    "timed_out": {
        "failure_code": "analysis_deadline_exceeded",
        "failure_message": "analysis exceeded its server-owned deadline",
        "result_body": None,
        "readiness_body": None,
        "canonical_success_at": None,
    },
    "failed": {
        "failure_code": "analysis_execution_failed",
        "failure_message": "analysis execution failed",
        "result_body": None,
        "readiness_body": None,
        "canonical_success_at": None,
    },
    "not_score_ready": {
        "failure_code": None,
        "failure_message": None,
        "result_body": None,
        "readiness_body": {"status": "not_score_ready"},
        "canonical_success_at": None,
    },
    "completed": {
        "failure_code": None,
        "failure_message": None,
        "result_body": outcome.result_body,
        "readiness_body": None,
        "canonical_success_at": base + timedelta(seconds=3),
    },
}
terminal_executor = ExactExecutor()
terminal_worker = ControlledClockWorker(
    database,
    terminal_executor,
    ReportArtifactGenerator(MemoryStorage(), max_bytes=2_000_000),
    clock=base + timedelta(seconds=5),
)
terminal_ids = {}
for index, (state, spec) in enumerate(terminal_specs.items(), start=1):
    _, analysis_id = seed(
        f"rpt55-h006-terminal-{state}",
        deadline_at=base + timedelta(minutes=10 + index),
    )
    terminal_ids[state] = analysis_id
    with database.session() as session:
        with session.begin():
            row = session.get(AnalysisModel, analysis_id)
            assert row is not None
            row.state = state
            row.updated_at = base + timedelta(seconds=4)
            row.finished_at = base + timedelta(seconds=4)
            row.failure_code = spec["failure_code"]
            row.failure_message = spec["failure_message"]
            row.result_body = spec["result_body"]
            row.readiness_body = spec["readiness_body"]
            row.canonical_success_at = spec["canonical_success_at"]

for state, analysis_id in terminal_ids.items():
    with database.session() as session:
        before = session.get(AnalysisModel, analysis_id)
        assert before is not None
        snapshot = (
            before.state,
            before.updated_at,
            before.finished_at,
            before.canonical_success_at,
            before.result_body,
            before.readiness_body,
            before.failure_code,
            before.failure_message,
        )
    assert terminal_worker.execute_analysis(analysis_id) == state
    with database.session() as session:
        after = session.get(AnalysisModel, analysis_id)
        assert after is not None
        assert (
            after.state,
            after.updated_at,
            after.finished_at,
            after.canonical_success_at,
            after.result_body,
            after.readiness_body,
            after.failure_code,
            after.failure_message,
        ) == snapshot

assert terminal_executor.calls == 0

with database.session() as session:
    timed_out_row = session.scalar(
        select(AnalysisModel)
        .where(AnalysisModel.analysis_id == terminal_ids["timed_out"])
        .with_for_update()
    )
    assert timed_out_row is not None and timed_out_row.state == "timed_out"
    boundary_state = terminal_worker._record_canonical_success_boundary(
        session,
        timed_out_row,
        success_at=base + timedelta(seconds=1),
    )
    assert boundary_state == "timed_out"

with database.session() as session:
    timed_out_row = session.get(AnalysisModel, terminal_ids["timed_out"])
    assert timed_out_row is not None and timed_out_row.state == "timed_out"
    assert timed_out_row.canonical_success_at is None
    assert timed_out_row.failure_code == "analysis_deadline_exceeded"

# 6.4 — advisory coordination is temporary, not a timeout bypass. While a live
# worker owns execution but has NOT achieved canonical success, an expired poll
# returns nonterminal instead of publishing a revocable timeout. Once that worker
# is lost and its advisory lock releases with no success marker, normal polling
# converges to a stable timed_out terminal state.
loss_deadline = base + timedelta(seconds=60)
loss_consumer, loss_id = seed("rpt55-h006-no-success-loss", deadline_at=loss_deadline)
loss_entered = Event(); loss_release = Event()
loss_executor = BlockingLossExecutor(loss_entered, loss_release)
loss_worker = ControlledClockWorker(
    database,
    loss_executor,
    None,
    clock=base + timedelta(seconds=4),
)
loss_backend = FixedClockLifecycle(
    database,
    NoopDispatcher(),
    deadline_seconds=900,
    clock=loss_deadline + timedelta(seconds=1),
)
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(loss_worker.execute_analysis, loss_id)
    assert loss_entered.wait(10)
    in_flight = loss_backend.retrieve(loss_id, consumer_id=loss_consumer)
    assert in_flight.state == "running"
    assert in_flight.error is None
    with database.session() as session:
        row = session.get(AnalysisModel, loss_id)
        assert row is not None and row.state == "running"
        assert row.canonical_success_at is None

    loss_release.set()
    try:
        future.result(timeout=20)
    except SimulatedProcessLoss:
        pass
    else:
        raise AssertionError("synthetic worker loss must escape normal worker handling")

with database.session() as session:
    row = session.get(AnalysisModel, loss_id)
    assert row is not None and row.state == "running"
    assert row.canonical_success_at is None

expired = loss_backend.retrieve(loss_id, consumer_id=loss_consumer)
assert expired.state == "timed_out"
assert expired.error is not None and expired.error["code"] == "analysis_deadline_exceeded"
with database.session() as session:
    row = session.get(AnalysisModel, loss_id)
    assert row is not None and row.state == "timed_out"
    assert row.canonical_success_at is None
    assert row.failure_code == "analysis_deadline_exceeded"

# Repeated terminal reads remain stable; there is no terminal resurrection path.
again = loss_backend.retrieve(loss_id, consumer_id=loss_consumer)
assert again.state == "timed_out"
assert again.error is not None and again.error["code"] == "analysis_deadline_exceeded"
''')
