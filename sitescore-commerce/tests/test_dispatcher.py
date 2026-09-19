from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from sitescore_commerce import __version__
from sitescore_commerce.dispatcher import (
    DispatchResult,
    DispatchState,
    N8nWebhookClient,
    OutboxDispatchSettings,
    PaidOutboxDispatcher,
    PaidOutboxEvent,
)
from sitescore_commerce.settings import ConfigurationError


class FakeStore:
    def __init__(self, event: PaidOutboxEvent | None):
        self.event = event
        self.marked = []
        self.transaction_open = False
        self.load_calls = 0

    def load_next_unpublished(self):
        self.load_calls += 1
        self.transaction_open = True
        try:
            return self.event if not self.marked else None
        finally:
            self.transaction_open = False

    def mark_published(self, event_id):
        self.transaction_open = True
        try:
            self.marked.append(event_id)
        finally:
            self.transaction_open = False


class FakeHttpClient:
    def __init__(self, store, outcomes):
        self.store = store
        self.outcomes = list(outcomes)
        self.calls = []

    def post(self, url, **kwargs):
        assert self.store.transaction_open is False
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome, request=httpx.Request("POST", url))


def settings(secret="ingress-secret-" + "x" * 24):
    return OutboxDispatchSettings(
        database_url="postgresql+psycopg://unused",
        webhook_url="https://n8n.example.test/webhook/sitescore-order-paid-v1",
        ingress_secret=secret,
        timeout_seconds=5,
    )


def event():
    return PaidOutboxEvent(
        event_id=uuid4(),
        event_type="order.paid.v1",
        order_id=uuid4(),
        occurred_at=datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc),
    )


def test_checkpoint_package_version_is_0_6_0():
    assert __version__ == "0.6.0"


def test_payload_is_minimal_server_owned_identity_only():
    item = event()
    assert item.payload() == {
        "event_id": str(item.event_id),
        "event_type": "order.paid.v1",
        "order_id": str(item.order_id),
        "occurred_at": "2026-08-19T12:00:00Z",
    }


def test_2xx_marks_same_durable_event_published_after_http():
    item = event()
    store = FakeStore(item)
    http = FakeHttpClient(store, [202])
    webhook = N8nWebhookClient(settings(), client=http)
    result = PaidOutboxDispatcher(store, webhook).dispatch_once()

    assert result == DispatchResult(
        DispatchState.PUBLISHED,
        event_id=item.event_id,
        order_id=item.order_id,
        http_status=202,
    )
    assert store.marked == [item.event_id]
    url, kwargs = http.calls[0]
    assert url.endswith("/webhook/sitescore-order-paid-v1")
    assert kwargs["json"] == item.payload()
    assert set(kwargs["json"]) == {"event_id", "event_type", "order_id", "occurred_at"}
    assert kwargs["headers"]["Authorization"].startswith("Bearer ingress-secret-")
    assert "analysis" not in repr(kwargs["json"]).lower()
    assert "payment" not in repr(kwargs["json"]).lower()


@pytest.mark.parametrize("status", [400, 401, 409, 429, 500, 503])
def test_non_2xx_never_marks_published(status):
    item = event()
    store = FakeStore(item)
    http = FakeHttpClient(store, [status])
    result = PaidOutboxDispatcher(store, N8nWebhookClient(settings(), client=http)).dispatch_once()
    assert result.state is DispatchState.UNPUBLISHED
    assert result.event_id == item.event_id
    assert store.marked == []


def test_timeout_or_uncertain_response_replays_exact_same_event_identity():
    item = event()
    store = FakeStore(item)
    timeout = httpx.ReadTimeout(
        "simulated response loss",
        request=httpx.Request("POST", settings().webhook_url),
    )
    http = FakeHttpClient(store, [timeout, 202])
    dispatcher = PaidOutboxDispatcher(store, N8nWebhookClient(settings(), client=http))

    first = dispatcher.dispatch_once()
    assert first.state is DispatchState.UNPUBLISHED
    assert store.marked == []

    second = dispatcher.dispatch_once()
    assert second.state is DispatchState.PUBLISHED
    assert store.marked == [item.event_id]
    assert http.calls[0][1]["json"] == http.calls[1][1]["json"] == item.payload()


def test_no_event_is_clean_noop():
    store = FakeStore(None)
    http = FakeHttpClient(store, [])
    result = PaidOutboxDispatcher(store, N8nWebhookClient(settings(), client=http)).dispatch_once()
    assert result.state is DispatchState.EMPTY
    assert http.calls == []
    assert store.marked == []


def test_dispatch_settings_require_https_in_production_and_distinct_role_secrets(monkeypatch):
    monkeypatch.setenv("COMMERCE_ENV", "production")
    monkeypatch.setenv("SITESCORE_COMMERCE_DATABASE_URL", "postgresql+psycopg://db")
    monkeypatch.setenv("COMMERCE_N8N_ORDER_PAID_WEBHOOK_URL", "http://n8n.example.test/webhook/x")
    monkeypatch.setenv("COMMERCE_N8N_INGRESS_SECRET", "x" * 32)
    monkeypatch.setenv("COMMERCE_AUTOMATION_API_KEY", "y" * 32)
    with pytest.raises(ConfigurationError, match="production"):
        OutboxDispatchSettings.from_env()

    monkeypatch.setenv("COMMERCE_N8N_ORDER_PAID_WEBHOOK_URL", "https://n8n.example.test/webhook/x")
    monkeypatch.setenv("COMMERCE_N8N_INGRESS_SECRET", "z" * 32)
    monkeypatch.setenv("COMMERCE_AUTOMATION_API_KEY", "z" * 32)
    with pytest.raises(ConfigurationError, match="distinct"):
        OutboxDispatchSettings.from_env()


def test_dispatch_settings_accept_local_http_for_test(monkeypatch):
    monkeypatch.setenv("COMMERCE_ENV", "test")
    monkeypatch.setenv("SITESCORE_COMMERCE_DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1/sitescore")
    monkeypatch.setenv("COMMERCE_N8N_ORDER_PAID_WEBHOOK_URL", "http://127.0.0.1:5678/webhook/sitescore-order-paid-v1")
    monkeypatch.setenv("COMMERCE_N8N_INGRESS_SECRET", "i" * 32)
    monkeypatch.setenv("COMMERCE_AUTOMATION_API_KEY", "a" * 32)
    value = OutboxDispatchSettings.from_env()
    assert value.webhook_url.endswith("/webhook/sitescore-order-paid-v1")
    assert value.timeout_seconds == 10.0
