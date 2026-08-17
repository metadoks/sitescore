from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from threading import Event
from uuid import uuid4

from pydantic import TypeAdapter
import pytest
from sqlalchemy import text

from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel
from sitescore_api.ingress import build_analysis_ingress_command
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.models import AnalysisRequest
from sitescore_api.worker import AnalysisWorkerService

DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="real PostgreSQL worker tests require SITESCORE_DATABASE_URL")
ADAPTER = TypeAdapter(AnalysisRequest)


class NoopDispatcher:
    def dispatch_analysis(self, analysis_id):
        return None


class RaisingExecutor:
    def __init__(self, message: str = "provider-secret-do-not-leak") -> None:
        self.message = message
        self.calls = 0

    def execute(self, command, *, now):
        self.calls += 1
        raise RuntimeError(self.message)


class BlockingExecutor(RaisingExecutor):
    def __init__(self) -> None:
        super().__init__()
        self.entered = Event()
        self.release = Event()

    def execute(self, command, *, now):
        self.calls += 1
        self.entered.set()
        assert self.release.wait(timeout=10)
        raise RuntimeError("simulated worker crash")


def _setup(database: Database, payload, *, key: str = "worker-key"):
    consumer_id = uuid4()
    with database.session() as session:
        with session.begin():
            session.add(
                ConsumerModel(
                    consumer_id=consumer_id,
                    name="worker-test",
                    active=True,
                    created_at=datetime.now(timezone.utc),
                )
            )
    model = ADAPTER.validate_python(payload)
    command = build_analysis_ingress_command(model, request_id=uuid4(), analysis_id=uuid4())
    backend = PostgresAnalysisLifecycleBackend(database, NoopDispatcher(), deadline_seconds=900)
    return backend.submit(command, model, consumer_id=consumer_id, idempotency_key=key)


@pytest.fixture
def database():
    assert DATABASE_URL is not None
    database = Database(DATABASE_URL)
    with database.engine.begin() as conn:
        conn.execute(text("TRUNCATE dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))
    return database


def test_unexpected_execution_failure_is_safe_terminal_failed(database, valid_payloads):
    accepted = _setup(database, valid_payloads["gym"])
    secret = "provider-secret-do-not-leak"
    executor = RaisingExecutor(secret)
    worker = AnalysisWorkerService(database, executor)  # type: ignore[arg-type]
    assert worker.execute_analysis(accepted.analysis_id) == "failed"
    with database.session() as session:
        row = session.get(AnalysisModel, accepted.analysis_id)
        assert row is not None
        assert row.state == "failed"
        assert row.failure_code == "analysis_execution_failed"
        assert secret not in (row.failure_message or "")
        assert row.result_body is None


def test_expired_queued_record_becomes_timed_out_and_is_immutable(database, valid_payloads):
    accepted = _setup(database, valid_payloads["coffee"])
    with database.session() as session:
        with session.begin():
            row = session.get(AnalysisModel, accepted.analysis_id)
            assert row is not None
            row.deadline_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    executor = RaisingExecutor()
    worker = AnalysisWorkerService(database, executor)  # type: ignore[arg-type]
    assert worker.execute_analysis(accepted.analysis_id) == "timed_out"
    assert worker.execute_analysis(accepted.analysis_id) == "timed_out"
    assert executor.calls == 0
    with database.session() as session:
        row = session.get(AnalysisModel, accepted.analysis_id)
        assert row is not None
        assert row.state == "timed_out"
        assert row.failure_code == "analysis_deadline_exceeded"


def test_existing_terminal_completed_state_is_not_reexecuted_or_regressed(database, valid_payloads):
    accepted = _setup(database, valid_payloads["restaurant"])
    with database.session() as session:
        with session.begin():
            row = session.get(AnalysisModel, accepted.analysis_id)
            assert row is not None
            now = datetime.now(timezone.utc)
            row.state = "completed"
            row.result_body = {"test_structural_terminal": True}
            row.finished_at = now
            row.updated_at = now
    executor = RaisingExecutor()
    worker = AnalysisWorkerService(database, executor)  # type: ignore[arg-type]
    assert worker.execute_analysis(accepted.analysis_id) == "completed"
    assert executor.calls == 0
    with database.session() as session:
        row = session.get(AnalysisModel, accepted.analysis_id)
        assert row is not None
        assert row.state == "completed"
        assert row.result_body == {"test_structural_terminal": True}


def test_duplicate_delivery_cannot_execute_concurrently(database, valid_payloads):
    accepted = _setup(database, valid_payloads["beauty"])
    executor = BlockingExecutor()
    worker = AnalysisWorkerService(database, executor)  # type: ignore[arg-type]

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(worker.execute_analysis, accepted.analysis_id)
        assert executor.entered.wait(timeout=10)
        second = pool.submit(worker.execute_analysis, accepted.analysis_id)
        assert second.result(timeout=10) == "busy"
        executor.release.set()
        assert first.result(timeout=10) == "failed"
    assert executor.calls == 1
