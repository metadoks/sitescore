from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflows" / "sitescore-recovery-schedule-v1.json"


def load():
    return json.loads(WORKFLOW.read_text())


def test_recovery_schedule_identity_and_native_inventory():
    workflow = load()
    assert workflow["id"] == "sitescoreRecoveryScheduleV1"
    assert workflow["name"] == "SiteScore Recovery Scheduler v1.0.0"
    assert workflow["meta"] == {
        "sitescoreWorkflowVersion": "1.0.0",
        "sitescoreBusinessIdentity": "sitescore-recovery-schedule-v1",
    }
    assert workflow["active"] is False
    assert [node["type"] for node in workflow["nodes"]] == [
        "n8n-nodes-base.scheduleTrigger",
        "n8n-nodes-base.httpRequest",
    ]
    assert not any("code" in node["type"].lower() or "function" in node["type"].lower() for node in workflow["nodes"])


def test_schedule_is_server_owned_five_minutes_and_calls_only_empty_recovery_endpoint():
    workflow = load(); schedule, call = workflow["nodes"]
    interval = schedule["parameters"]["rule"]["interval"]
    assert interval == [{"field": "minutes", "minutesInterval": 5}]
    params = call["parameters"]
    assert params["method"] == "POST"
    assert params["url"] == "={{ $env.SITESCORE_COMMERCE_AUTOMATION_BASE_URL + '/v1/automation/recovery/run' }}"
    headers = params["headerParameters"]["parameters"]
    assert headers == [{"name": "Authorization", "value": "={{ 'Bearer ' + $env.COMMERCE_AUTOMATION_API_KEY }}"}]
    assert params.get("sendBody") is not True
    assert "bodyParameters" not in params and "jsonBody" not in params
    assert workflow["connections"] == {"Recovery Schedule": {"main": [[{"node": "Run Commerce Recovery", "type": "main", "index": 0}]]}}


def test_scheduler_export_has_no_provider_database_storage_or_customer_material():
    text = WORKFLOW.read_text()
    for pattern in [r"sk_live_[A-Za-z0-9]+", r"sk_test_[A-Za-z0-9]+", r"whsec_[A-Za-z0-9]+", r"ssk1_[A-Za-z0-9]", r"AKIA[0-9A-Z]{16}", r"postgresql(?:\+psycopg)?://", r"redis://"]:
        assert re.search(pattern, text) is None
    lowered = text.lower()
    for forbidden in [
        "stripe_secret_key", "stripe_webhook_secret", "postmark", "sitescore_api_service_key",
        "database_url", "aws_secret", "s3_", "customer_email", "recipient", "report_id",
        "delivery_token", "token_digest", "/v1/analyses", "/v1/reports", "/deliver", "/advance",
    ]:
        assert forbidden not in lowered
