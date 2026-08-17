from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
import pytest
from sqlalchemy import func, select, text

from sitescore_api.app import create_app
from sitescore_api.auth import provision_service_key
from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, DispatchOutboxModel, ServiceApiKeyModel
from sitescore_api.errors import IdempotencyConflict
from sitescore_api.ingress import build_analysis_ingress_command
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.models import AnalysisRequest
from sitescore_api.settings import Settings

ADAPTER = TypeAdapter(AnalysisRequest)
DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="real PostgreSQL integration requires SITESCORE_DATABASE_URL")
PEPPER = "test-only-pepper-0123456789-abcdefghijklmnopqrstuvwxyz"


class RecordingDispatcher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[UUID] = []

    def dispatch_analysis(self, analysis_id: UUID) -> None:
        self.calls.append(analysis_id)
        if self.fail:
            raise RuntimeError("simulated broker outage secret-do-not-leak")


@pytest.fixture
def database():
    assert DATABASE_URL is not None
    db = Database(DATABASE_URL)
    with db.engine.begin() as conn:
        conn.execute(text("TRUNCATE dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))
    return db


def _consumer_and_key(database: Database, scopes: set[str], *, name: str = "consumer") -> tuple[UUID, str]:
    consumer_id = uuid4()
    with database.session() as session:
        with session.begin():
            session.add(
                ConsumerModel(
                    consumer_id=consumer_id,
                    name=name,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.flush()
            token = provision_service_key(
                session,
                consumer_id=consumer_id,
                scopes=scopes,
                pepper=PEPPER,
            )
    return consumer_id, token


def _client(database: Database, dispatcher: RecordingDispatcher) -> TestClient:
    settings = Settings(
        database_url=DATABASE_URL or "",
        broker_url="redis://127.0.0.1:6379/0",
        api_key_pepper=PEPPER,
    )
    lifecycle = PostgresAnalysisLifecycleBackend(database, dispatcher, deadline_seconds=900)
    runtime = SimpleNamespace(settings=settings, database=database, lifecycle=lifecycle)
    return TestClient(create_app(runtime), raise_server_exceptions=False)


def _headers(token: str, key: str = "idem-1") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": key}


def test_auth_scopes_idempotent_replay_and_raw_secret_absence(database, valid_payloads):
    _, token = _consumer_and_key(database, {"analysis:write", "analysis:read"})
    dispatcher = RecordingDispatcher()
    client = _client(database, dispatcher)

    first = client.post("/v1/analyses", json=valid_payloads["coffee"], headers=_headers(token))
    second = client.post("/v1/analyses", json=valid_payloads["coffee"], headers=_headers(token))
    assert first.status_code == second.status_code == 202
    a, b = first.json(), second.json()
    assert a["analysis_id"] == b["analysis_id"]
    assert a["request_id"] != b["request_id"]
    assert a["state"] == "queued"
    assert first.headers["retry-after"] == "3"

    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisModel)) == 1
        assert session.scalar(select(func.count()).select_from(DispatchOutboxModel)) == 1
        key_row = session.scalar(select(ServiceApiKeyModel))
        analysis = session.scalar(select(AnalysisModel))
        assert key_row is not None and analysis is not None
        assert token not in key_row.secret_digest
        assert token not in str(analysis.request_payload)
        assert len(key_row.secret_digest) == 64


def test_authentication_scope_and_idempotency_errors_are_stable(database, valid_payloads):
    _, read_only = _consumer_and_key(database, {"analysis:read"}, name="read-only")
    _, write_only = _consumer_and_key(database, {"analysis:write"}, name="write-only")
    client = _client(database, RecordingDispatcher())

    missing = client.post("/v1/analyses", json=valid_payloads["gym"], headers={"Idempotency-Key": "x"})
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert missing.headers["www-authenticate"] == "Bearer"

    invalid = client.post(
        "/v1/analyses",
        json=valid_payloads["gym"],
        headers={"Authorization": "Bearer ssk1_unknown.invalid", "Idempotency-Key": "x"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_api_key"

    scope = client.post("/v1/analyses", json=valid_payloads["gym"], headers=_headers(read_only, "x"))
    assert scope.status_code == 403
    assert scope.json()["error"]["code"] == "insufficient_scope"

    no_key = client.post(
        "/v1/analyses",
        json=valid_payloads["gym"],
        headers={"Authorization": f"Bearer {write_only}"},
    )
    assert no_key.status_code == 400
    assert no_key.json()["error"]["code"] == "idempotency_key_required"

    oversized = client.post(
        "/v1/analyses",
        json=valid_payloads["gym"],
        headers=_headers(write_only, "x" * 201),
    )
    assert oversized.status_code == 400
    assert oversized.json()["error"]["code"] == "invalid_idempotency_key"


def test_same_key_different_payload_conflicts_and_cross_consumer_is_independent(database, valid_payloads):
    _, token_a = _consumer_and_key(database, {"analysis:write", "analysis:read"}, name="a")
    _, token_b = _consumer_and_key(database, {"analysis:write", "analysis:read"}, name="b")
    client = _client(database, RecordingDispatcher())
    payload_a = deepcopy(valid_payloads["restaurant"])
    payload_b = deepcopy(payload_a)
    payload_b["costs"]["monthly_rent"] += 100

    a = client.post("/v1/analyses", json=payload_a, headers=_headers(token_a, "shared-key"))
    conflict = client.post("/v1/analyses", json=payload_b, headers=_headers(token_a, "shared-key"))
    b = client.post("/v1/analyses", json=payload_b, headers=_headers(token_b, "shared-key"))
    assert a.status_code == b.status_code == 202
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    assert a.json()["analysis_id"] != b.json()["analysis_id"]


def test_consumer_isolation_hides_foreign_existence(database, valid_payloads):
    _, owner = _consumer_and_key(database, {"analysis:write", "analysis:read"}, name="owner")
    _, foreign = _consumer_and_key(database, {"analysis:read"}, name="foreign")
    client = _client(database, RecordingDispatcher())
    created = client.post("/v1/analyses", json=valid_payloads["beauty"], headers=_headers(owner))
    analysis_id = created.json()["analysis_id"]

    foreign_response = client.get(
        f"/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {foreign}"},
    )
    missing_response = client.get(
        f"/v1/analyses/{uuid4()}",
        headers={"Authorization": f"Bearer {foreign}"},
    )
    assert foreign_response.status_code == missing_response.status_code == 404
    assert foreign_response.json()["error"]["code"] == "analysis_not_found"
    assert missing_response.json()["error"]["code"] == "analysis_not_found"


def test_broker_failure_after_commit_preserves_analysis_and_pending_outbox(database, valid_payloads):
    _, token = _consumer_and_key(database, {"analysis:write", "analysis:read"})
    dispatcher = RecordingDispatcher(fail=True)
    client = _client(database, dispatcher)
    response = client.post("/v1/analyses", json=valid_payloads["coffee"], headers=_headers(token))
    assert response.status_code == 202
    analysis_id = UUID(response.json()["analysis_id"])
    with database.session() as session:
        analysis = session.get(AnalysisModel, analysis_id)
        outbox = session.scalar(select(DispatchOutboxModel).where(DispatchOutboxModel.analysis_id == analysis_id))
        assert analysis is not None and analysis.state == "queued"
        assert outbox is not None and outbox.dispatched_at is None


def test_get_atomically_reconciles_expired_nonterminal(database, valid_payloads):
    consumer_id, token = _consumer_and_key(database, {"analysis:write", "analysis:read"})
    dispatcher = RecordingDispatcher()
    client = _client(database, dispatcher)
    created = client.post("/v1/analyses", json=valid_payloads["coffee"], headers=_headers(token))
    analysis_id = UUID(created.json()["analysis_id"])
    with database.session() as session:
        with session.begin():
            row = session.get(AnalysisModel, analysis_id)
            assert row is not None and row.consumer_id == consumer_id
            row.deadline_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    result = client.get(
        f"/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert result.status_code == 200
    assert result.json()["state"] == "timed_out"
    assert result.json()["error"]["code"] == "analysis_deadline_exceeded"
    assert result.json()["result"] is None


def test_postgresql_unique_constraint_closes_same_payload_race(database, valid_payloads):
    consumer_id, _ = _consumer_and_key(database, {"analysis:write"})
    dispatcher = RecordingDispatcher()
    backend = PostgresAnalysisLifecycleBackend(database, dispatcher, deadline_seconds=900)
    model = ADAPTER.validate_python(valid_payloads["coffee"])

    def submit_once(_index: int):
        command = build_analysis_ingress_command(model, request_id=uuid4(), analysis_id=uuid4())
        return backend.submit(command, model, consumer_id=consumer_id, idempotency_key="race-key").analysis_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(submit_once, range(2)))
    assert ids[0] == ids[1]
    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisModel)) == 1
        assert session.scalar(select(func.count()).select_from(DispatchOutboxModel)) == 1


def test_postgresql_unique_constraint_makes_different_payload_race_deterministic(database, valid_payloads):
    consumer_id, _ = _consumer_and_key(database, {"analysis:write"})
    backend = PostgresAnalysisLifecycleBackend(database, RecordingDispatcher(), deadline_seconds=900)
    p1 = ADAPTER.validate_python(valid_payloads["coffee"])
    changed = deepcopy(valid_payloads["coffee"])
    changed["costs"]["fixed_overhead"] += 1
    p2 = ADAPTER.validate_python(changed)

    def submit(model):
        try:
            command = build_analysis_ingress_command(model, request_id=uuid4(), analysis_id=uuid4())
            backend.submit(command, model, consumer_id=consumer_id, idempotency_key="race-conflict")
            return "accepted"
        except IdempotencyConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit, (p1, p2)))
    assert sorted(outcomes) == ["accepted", "conflict"]
