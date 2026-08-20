from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from sitescore_commerce.dispatcher import OutboxDispatchSettings, PaidOutboxEvent
from sitescore_commerce.recovery import (
    RecoveryN8nIngressClient,
    RecoveryRuntimeSettings,
    RecoveryTransportResult,
)
from sitescore_commerce.settings import ConfigurationError


def dispatch_settings():
    return OutboxDispatchSettings(
        database_url="postgresql+psycopg://unused",
        webhook_url="https://n8n.example.test/webhook/sitescore-order-paid-v1",
        ingress_secret="i" * 32,
        timeout_seconds=5,
    )


def event():
    return PaidOutboxEvent(
        event_id=uuid4(),
        event_type="order.paid.v1",
        order_id=uuid4(),
        occurred_at=datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
    )


def test_recovery_runtime_defaults_are_server_owned_and_bounded(monkeypatch):
    for name in [
        "COMMERCE_RECOVERY_BATCH_SIZE",
        "COMMERCE_RECOVERY_STALE_INBOX_SECONDS",
        "COMMERCE_RECOVERY_PENDING_PAYMENT_SECONDS",
        "COMMERCE_RECOVERY_PUBLISHED_REPLAY_SECONDS",
        "COMMERCE_RECOVERY_LEASE_SECONDS",
        "COMMERCE_RECOVERY_MAX_BACKOFF_SECONDS",
    ]:
        monkeypatch.delenv(name, raising=False)
    value = RecoveryRuntimeSettings.from_env()
    assert value == RecoveryRuntimeSettings(
        batch_size=10,
        stale_inbox_seconds=120,
        pending_payment_poll_seconds=300,
        published_replay_seconds=1200,
        lease_seconds=120,
        maximum_backoff_seconds=3600,
    )


@pytest.mark.parametrize(
    "name,value",
    [
        ("COMMERCE_RECOVERY_BATCH_SIZE", "0"),
        ("COMMERCE_RECOVERY_BATCH_SIZE", "101"),
        ("COMMERCE_RECOVERY_STALE_INBOX_SECONDS", "29"),
        ("COMMERCE_RECOVERY_PENDING_PAYMENT_SECONDS", "59"),
        ("COMMERCE_RECOVERY_PUBLISHED_REPLAY_SECONDS", "119"),
        ("COMMERCE_RECOVERY_LEASE_SECONDS", "29"),
        ("COMMERCE_RECOVERY_MAX_BACKOFF_SECONDS", "59"),
        ("COMMERCE_RECOVERY_BATCH_SIZE", "caller-controlled"),
    ],
)
def test_recovery_runtime_rejects_unbounded_or_invalid_values(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError):
        RecoveryRuntimeSettings.from_env()


def send_with_status(status: int):
    def handler(request: httpx.Request):
        assert request.method == "POST"
        assert request.url.path == "/webhook/sitescore-order-paid-v1"
        assert request.headers["Authorization"] == "Bearer " + "i" * 32
        return httpx.Response(status, request=request)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return RecoveryN8nIngressClient(dispatch_settings(), client=client).send(event())


@pytest.mark.parametrize("status", [200, 202, 204])
def test_recovery_n8n_2xx_is_transport_acceptance_only(status):
    result = send_with_status(status)
    assert result.result is RecoveryTransportResult.ACCEPTED and result.http_status == status


@pytest.mark.parametrize("status", [429, 500, 503])
def test_recovery_n8n_retryable_statuses_remain_retryable(status):
    result = send_with_status(status)
    assert result.result is RecoveryTransportResult.RETRYABLE_REJECTED
    assert result.failure_code in {"n8n_http_429", "n8n_http_5xx"}


@pytest.mark.parametrize("status,code", [(401, "n8n_auth_rejected"), (403, "n8n_auth_rejected"), (400, "n8n_contract_rejected"), (422, "n8n_contract_rejected"), (409, "n8n_unexpected_response")])
def test_recovery_n8n_nonretryable_contract_or_auth_statuses_require_attention(status, code):
    result = send_with_status(status)
    assert result.result is RecoveryTransportResult.ATTENTION
    assert result.failure_code == code


def test_recovery_n8n_timeout_is_uncertain_not_accepted_or_attention():
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("lost response", request=request)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = RecoveryN8nIngressClient(dispatch_settings(), client=client).send(event())
    assert result.result is RecoveryTransportResult.UNCERTAIN
    assert result.failure_code == "n8n_transport_uncertain"
