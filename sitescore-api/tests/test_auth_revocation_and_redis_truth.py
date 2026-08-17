from __future__ import annotations

from datetime import datetime, timezone
import os
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from redis import Redis
from sqlalchemy import select, text

from sitescore_api.app import create_app
from sitescore_api.auth import provision_service_key
from sitescore_api.db import Database
from sitescore_api.db_models import AnalysisModel, ConsumerModel, ServiceApiKeyModel
from sitescore_api.lifecycle import PostgresAnalysisLifecycleBackend
from sitescore_api.settings import Settings

DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")
BROKER_URL = os.getenv("SITESCORE_BROKER_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="real PostgreSQL auth tests require SITESCORE_DATABASE_URL")
PEPPER = "test-only-pepper-0123456789-abcdefghijklmnopqrstuvwxyz"


class NoopDispatcher:
    def dispatch_analysis(self, analysis_id):
        return None


def _client_and_token(database: Database, scopes: set[str]):
    consumer_id = uuid4()
    with database.session() as session:
        with session.begin():
            session.add(ConsumerModel(consumer_id=consumer_id, name="auth-test", active=True, created_at=datetime.now(timezone.utc)))
            session.flush()
            token = provision_service_key(session, consumer_id=consumer_id, scopes=scopes, pepper=PEPPER)
    settings = Settings(database_url=DATABASE_URL or "", broker_url=BROKER_URL or "redis://127.0.0.1:6379/0", api_key_pepper=PEPPER)
    lifecycle = PostgresAnalysisLifecycleBackend(database, NoopDispatcher(), deadline_seconds=900)
    runtime = SimpleNamespace(settings=settings, database=database, lifecycle=lifecycle)
    return TestClient(create_app(runtime), raise_server_exceptions=False), consumer_id, token


@pytest.fixture
def database():
    assert DATABASE_URL is not None
    database = Database(DATABASE_URL)
    with database.engine.begin() as conn:
        conn.execute(text("TRUNCATE dispatch_outbox, analyses, service_api_keys, consumers CASCADE"))
    return database


def test_revoked_key_and_inactive_consumer_fail_closed(database, valid_payloads):
    client, consumer_id, token = _client_and_token(database, {"analysis:write"})
    with database.session() as session:
        with session.begin():
            key = session.scalar(select(ServiceApiKeyModel).where(ServiceApiKeyModel.consumer_id == consumer_id))
            assert key is not None
            key.active = False
            key.revoked_at = datetime.now(timezone.utc)
    revoked = client.post(
        "/v1/analyses",
        json=valid_payloads["coffee"],
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "revoked"},
    )
    assert revoked.status_code == 401
    assert revoked.json()["error"]["code"] == "invalid_api_key"

    client2, consumer2, token2 = _client_and_token(database, {"analysis:write"})
    with database.session() as session:
        with session.begin():
            consumer = session.get(ConsumerModel, consumer2)
            assert consumer is not None
            consumer.active = False
    inactive = client2.post(
        "/v1/analyses",
        json=valid_payloads["coffee"],
        headers={"Authorization": f"Bearer {token2}", "Idempotency-Key": "inactive"},
    )
    assert inactive.status_code == 401
    assert inactive.json()["error"]["code"] == "invalid_api_key"


def test_write_only_key_cannot_get(database, valid_payloads):
    owner_client, _, owner_token = _client_and_token(database, {"analysis:write", "analysis:read"})
    write_client, _, write_token = _client_and_token(database, {"analysis:write"})
    created = owner_client.post(
        "/v1/analyses",
        json=valid_payloads["gym"],
        headers={"Authorization": f"Bearer {owner_token}", "Idempotency-Key": "owner"},
    )
    response = write_client.get(
        f"/v1/analyses/{created.json()['analysis_id']}",
        headers={"Authorization": f"Bearer {write_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_scope"


@pytest.mark.skipif(not BROKER_URL, reason="Redis durability-boundary test requires SITESCORE_BROKER_URL")
def test_redis_flush_does_not_delete_or_change_durable_analysis_resource(database, valid_payloads):
    client, _, token = _client_and_token(database, {"analysis:write", "analysis:read"})
    created = client.post(
        "/v1/analyses",
        json=valid_payloads["restaurant"],
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "redis-loss"},
    )
    assert created.status_code == 202
    analysis_id = created.json()["analysis_id"]
    Redis.from_url(BROKER_URL or "").flushall()
    fetched = client.get(
        f"/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    assert fetched.json()["analysis_id"] == analysis_id
    assert fetched.json()["state"] == "queued"
    with database.session() as session:
        assert session.scalar(select(AnalysisModel).where(AnalysisModel.analysis_id == uuid4())) is None
