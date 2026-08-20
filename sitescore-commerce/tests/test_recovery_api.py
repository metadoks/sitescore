from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from sitescore_commerce.api import create_app
from sitescore_commerce.fulfillment import AutomationUnauthorized
from sitescore_commerce.recovery import RecoveryRunResponse


class NoopOrderService:
    def create_order(self, **kwargs):
        raise AssertionError("order service must not be called")


class NoopWebhookService:
    def handle(self, **kwargs):
        raise AssertionError("webhook service must not be called")


class AutomationAuthority:
    def __init__(self, token: str = "automation-test-token"):
        self.token = token

    def authorize_automation(self, authorization: str | None) -> None:
        if authorization != f"Bearer {self.token}":
            raise AutomationUnauthorized("invalid automation credential")


class Recovery:
    def __init__(self):
        self.calls = 0
        self.run_id = uuid4()

    def run_once(self) -> RecoveryRunResponse:
        self.calls += 1
        return RecoveryRunResponse(
            run_id=self.run_id,
            claimed=3,
            reconciled=1,
            published=1,
            replayed=0,
            deferred=1,
            attention=0,
        )


def client(recovery: Recovery | None = None):
    recovery = recovery or Recovery()
    app = create_app(
        service=NoopOrderService(),
        webhook_service=NoopWebhookService(),
        fulfillment_service=AutomationAuthority(),
        recovery_service=recovery,
    )
    return TestClient(app), recovery


def test_recovery_endpoint_requires_existing_automation_bearer():
    c, recovery = client()
    response = c.post("/v1/automation/recovery/run", content=b"")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "automation_unauthorized"
    assert recovery.calls == 0


def test_recovery_endpoint_rejects_any_request_body_and_does_not_run():
    c, recovery = client()
    response = c.post(
        "/v1/automation/recovery/run",
        headers={"Authorization": "Bearer automation-test-token", "Content-Type": "application/json"},
        content=b"{}",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "request_validation_failed"
    assert recovery.calls == 0


def test_recovery_endpoint_returns_only_bounded_run_counts():
    c, recovery = client()
    response = c.post(
        "/v1/automation/recovery/run",
        headers={"Authorization": "Bearer automation-test-token"},
        content=b"",
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "api_version": "2026-08-20",
        "run_id": str(recovery.run_id),
        "claimed": 3,
        "reconciled": 1,
        "published": 1,
        "replayed": 0,
        "deferred": 1,
        "attention": 0,
    }
    for forbidden in ["order_id", "stripe", "email", "recipient", "token", "report_id", "provider"]:
        assert forbidden not in response.text.lower()
    assert recovery.calls == 1
