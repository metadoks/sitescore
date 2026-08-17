from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from sitescore_api.app import create_app
from sitescore_api.ingress import AnalysisIngressCommand
from sitescore_api.lifecycle import AcceptedAnalysisResource, RetrievedAnalysisResource


class RecordingBackend:
    def __init__(self):
        self.submitted: list[AnalysisIngressCommand] = []
        self.retrieved: list[UUID] = []

    def submit(self, command: AnalysisIngressCommand) -> AcceptedAnalysisResource:
        self.submitted.append(command)
        return AcceptedAnalysisResource(analysis_id=command.analysis_id)

    def retrieve(self, analysis_id: UUID) -> RetrievedAnalysisResource:
        self.retrieved.append(analysis_id)
        return RetrievedAnalysisResource(analysis_id=analysis_id)


class BrokenIdentityBackend(RecordingBackend):
    def submit(self, command: AnalysisIngressCommand) -> AcceptedAnalysisResource:
        return AcceptedAnalysisResource(analysis_id=uuid4())


@pytest.fixture
def default_client():
    return TestClient(create_app(), raise_server_exceptions=False)


def _assert_uuid4(value: str) -> UUID:
    parsed = UUID(value)
    assert parsed.version == 4
    return parsed


def test_default_valid_post_truthfully_returns_503(default_client, valid_payloads):
    response = default_client.post("/v1/analyses", json=valid_payloads["coffee"])
    assert response.status_code == 503
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "analysis_lifecycle_unavailable"
    request_id = _assert_uuid4(body["request_id"])
    assert response.headers["x-request-id"] == str(request_id)
    assert "analysis_id" not in body


def test_default_valid_get_truthfully_returns_503(default_client):
    analysis_id = uuid4()
    response = default_client.get(f"/v1/analyses/{analysis_id}")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "analysis_lifecycle_unavailable"
    assert "analysis_id" not in body
    assert response.headers["x-request-id"] == body["request_id"]


def test_malformed_analysis_uuid_uses_stable_error_envelope(default_client):
    response = default_client.get("/v1/analyses/not-a-uuid")
    assert response.status_code == 422
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "request_validation_failed"
    assert isinstance(body["error"]["details"], list)
    _assert_uuid4(body["request_id"])
    assert response.headers["x-request-id"] == body["request_id"]


def test_body_validation_error_uses_stable_envelope(default_client, valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["score_ready"] = True
    response = default_client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "request_validation_failed"
    assert "detail" not in body
    assert response.headers["x-request-id"] == body["request_id"]


def test_caller_request_id_header_cannot_replace_server_id(default_client, valid_payloads):
    caller = str(uuid4())
    response = default_client.post(
        "/v1/analyses",
        json=valid_payloads["coffee"],
        headers={"X-Request-ID": caller},
    )
    body = response.json()
    assert body["request_id"] != caller
    _assert_uuid4(body["request_id"])


def test_injected_test_backend_can_prove_202_delegation(valid_payloads):
    backend = RecordingBackend()
    client = TestClient(create_app(backend), raise_server_exceptions=False)
    response = client.post("/v1/analyses", json=valid_payloads["gym"])
    assert response.status_code == 202
    body = response.json()
    request_id = _assert_uuid4(body["request_id"])
    analysis_id = _assert_uuid4(body["analysis_id"])
    assert request_id != analysis_id
    assert response.headers["x-request-id"] == str(request_id)
    assert len(backend.submitted) == 1
    command = backend.submitted[0]
    assert command.request_id == request_id
    assert command.analysis_id == analysis_id


def test_injected_test_backend_can_prove_get_delegation():
    backend = RecordingBackend()
    client = TestClient(create_app(backend), raise_server_exceptions=False)
    analysis_id = uuid4()
    response = client.get(f"/v1/analyses/{analysis_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == str(analysis_id)
    assert backend.retrieved == [analysis_id]


def test_backend_identity_mismatch_fails_closed(valid_payloads):
    client = TestClient(create_app(BrokenIdentityBackend()), raise_server_exceptions=False)
    response = client.post("/v1/analyses", json=valid_payloads["coffee"])
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_server_error"
    assert "mismatch" not in body["error"]["message"].lower()
    assert response.headers["x-request-id"] == body["request_id"]
    _assert_uuid4(body["request_id"])


def test_validation_detail_does_not_echo_input_value(default_client, valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    secretish = "DO-NOT-ECHO-ME"
    payload["business_inputs"]["average_ticket"] = secretish
    response = default_client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    assert secretish not in response.text


def test_unknown_v1_route_uses_stable_error_envelope(default_client):
    response = default_client.get("/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "route_not_found"
    assert "detail" not in body
    assert response.headers["x-request-id"] == body["request_id"]
    _assert_uuid4(body["request_id"])


def test_wrong_method_uses_stable_error_envelope(default_client):
    response = default_client.delete("/v1/analyses")
    assert response.status_code == 405
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["error"]["code"] == "method_not_allowed"
    assert "detail" not in body
    assert response.headers["x-request-id"] == body["request_id"]
    _assert_uuid4(body["request_id"])
