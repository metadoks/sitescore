from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from sitescore_api.app import create_app


def _uuid4(value: str) -> UUID:
    parsed = UUID(value)
    assert parsed.version == 4
    return parsed


def test_unconfigured_production_fails_closed_with_503(valid_payloads):
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.post(
        "/v1/analyses",
        json=valid_payloads["coffee"],
        headers={"Authorization": "Bearer not-a-real-key", "Idempotency-Key": "k1"},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "analysis_lifecycle_unavailable"
    assert response.headers["x-request-id"] == body["request_id"]
    _uuid4(body["request_id"])


def test_malformed_analysis_uuid_uses_stable_validation_envelope():
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get("/v1/analyses/not-a-uuid")
    assert response.status_code == 422
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "request_validation_failed"
    assert response.headers["x-request-id"] == body["request_id"]


def test_validation_detail_does_not_echo_input_value(valid_payloads):
    client = TestClient(create_app(), raise_server_exceptions=False)
    payload = deepcopy(valid_payloads["coffee"])
    secretish = "DO-NOT-ECHO-ME"
    payload["business_inputs"]["average_ticket"] = secretish
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    assert secretish not in response.text


def test_caller_request_id_never_becomes_server_request_id(valid_payloads):
    client = TestClient(create_app(), raise_server_exceptions=False)
    caller = str(uuid4())
    response = client.post(
        "/v1/analyses",
        json=valid_payloads["gym"],
        headers={
            "Authorization": "Bearer invalid",
            "Idempotency-Key": "k2",
            "X-Request-ID": caller,
        },
    )
    body = response.json()
    assert body["request_id"] != caller
    _uuid4(body["request_id"])


def test_unknown_route_and_wrong_method_keep_stable_envelopes():
    client = TestClient(create_app(), raise_server_exceptions=False)
    missing = client.get("/v1/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "route_not_found"
    wrong = client.delete("/v1/analyses")
    assert wrong.status_code == 405
    assert wrong.json()["error"]["code"] == "method_not_allowed"
