from __future__ import annotations

from sitescore_api.app import create_app


def _find_exact_state_enum(value):
    target = {"queued", "running", "completed", "not_score_ready", "failed", "timed_out"}
    if isinstance(value, dict):
        if set(value.get("enum", ())) == target:
            return True
        return any(_find_exact_state_enum(item) for item in value.values())
    if isinstance(value, list):
        return any(_find_exact_state_enum(item) for item in value)
    return False


def test_openapi_exact_v1_analysis_and_report_surface_and_bearer_scheme():
    schema = create_app().openapi()
    assert set(schema["paths"]) == {
        "/v1/analyses",
        "/v1/analyses/{analysis_id}",
        "/v1/reports",
        "/v1/reports/{report_id}",
        "/v1/reports/{report_id}/content",
    }
    security = schema["components"]["securitySchemes"]["ServiceApiKey"]
    assert security["type"] == "http"
    assert security["scheme"] == "bearer"
    for path, method in (
        ("/v1/analyses", "post"),
        ("/v1/analyses/{analysis_id}", "get"),
        ("/v1/reports", "post"),
        ("/v1/reports/{report_id}", "get"),
        ("/v1/reports/{report_id}/content", "get"),
    ):
        assert schema["paths"][path][method]["security"] == [{"ServiceApiKey": []}]


def test_openapi_documents_idempotency_analysis_states_and_strict_report_request():
    schema = create_app().openapi()
    post = schema["paths"]["/v1/analyses"]["post"]
    headers = {item["name"]: item for item in post["parameters"] if item["in"] == "header"}
    assert "Idempotency-Key" in headers
    assert "200 UTF-8 bytes" in headers["Idempotency-Key"]["description"]
    assert _find_exact_state_enum(schema)
    rendered = str(schema)
    assert "ReportResolveRequest" in rendered
    assert "report_id" in rendered
    assert "analysis_id" in rendered


def test_openapi_declares_machine_errors_and_hides_storage_or_internal_authority():
    schema = create_app().openapi()
    post_codes = set(schema["paths"]["/v1/analyses"]["post"]["responses"])
    get_codes = set(schema["paths"]["/v1/analyses/{analysis_id}"]["get"]["responses"])
    report_codes = set(schema["paths"]["/v1/reports/{report_id}/content"]["get"]["responses"])
    assert {"202", "400", "401", "403", "409", "422", "500", "503"}.issubset(post_codes)
    assert {"200", "401", "403", "404", "422", "500", "503"}.issubset(get_codes)
    assert {"200", "401", "403", "404", "409", "422", "500", "502", "503"}.issubset(report_codes)
    rendered = str(schema).lower()
    assert "task_id" not in rendered
    assert "api_key_secret" not in rendered
    assert "storage_key" not in rendered
    assert "bucket" not in rendered
    assert "/payment" not in rendered
    assert "/n8n" not in rendered
