from __future__ import annotations

from datetime import datetime, timezone
import os
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy import select, text

from sitescore_api.db import Database
from sitescore_api.db_models import ConsumerModel, DispatchOutboxModel
from sitescore_api.dispatcher import CeleryOutboxDispatcher
from sitescore_api.ingress import build_analysis_ingress_command
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.models import AnalysisRequest

DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="real PostgreSQL outbox test requires SITESCORE_DATABASE_URL")
ADAPTER = TypeAdapter(AnalysisRequest)


class InitiallyFailingCelery:
    def __init__(self) -> None:
        self.fail = True
        self.calls: list[dict[str, object]] = []

    def send_task(self, name, args, task_id):
        self.calls.append({"name": name, "args": list(args), "task_id": task_id})
        if self.fail:
            raise RuntimeError("redis unavailable")


def test_pending_outbox_survives_publish_failure_and_redispatch_reuses_task_id(valid_payloads):
    assert DATABASE_URL is not None
    database = Database(DATABASE_URL)
    with database.engine.begin() as conn:
        conn.execute(text("TRUNCATE dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))
    consumer_id = uuid4()
    with database.session() as session:
        with session.begin():
            session.add(ConsumerModel(consumer_id=consumer_id, name="outbox", active=True, created_at=datetime.now(timezone.utc)))

    celery = InitiallyFailingCelery()
    dispatcher = CeleryOutboxDispatcher(database, celery)  # type: ignore[arg-type]
    backend = PostgresAnalysisLifecycleBackend(database, dispatcher, deadline_seconds=900)
    model = ADAPTER.validate_python(valid_payloads["coffee"])
    command = build_analysis_ingress_command(model, request_id=uuid4(), analysis_id=uuid4())
    accepted = backend.submit(command, model, consumer_id=consumer_id, idempotency_key="outbox-key")

    with database.session() as session:
        pending = session.scalar(select(DispatchOutboxModel).where(DispatchOutboxModel.analysis_id == accepted.analysis_id))
        assert pending is not None
        task_id = pending.task_id
        assert pending.dispatched_at is None
        assert pending.attempt_count == 1

    celery.fail = False
    assert dispatcher.drain_pending(limit=10) == 1
    with database.session() as session:
        current = session.scalar(select(DispatchOutboxModel).where(DispatchOutboxModel.analysis_id == accepted.analysis_id))
        assert current is not None
        assert current.task_id == task_id
        assert current.dispatched_at is not None
        assert current.attempt_count == 2

    assert len(celery.calls) == 2
    assert {call["task_id"] for call in celery.calls} == {str(task_id)}
    assert all(call["name"] == "sitescore_api.execute_analysis" for call in celery.calls)
    assert all(call["args"] == [str(accepted.analysis_id)] for call in celery.calls)
