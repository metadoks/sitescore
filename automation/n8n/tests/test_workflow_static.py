from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflows" / "sitescore-order-paid-v1.json"
RUNTIME = ROOT / "runtime" / "docker-compose.yml"


def load():
    return json.loads(WORKFLOW.read_text())


def by_name(workflow):
    return {node["name"]: node for node in workflow["nodes"]}


def targets(workflow, name, output=0):
    return [item["node"] for item in workflow["connections"].get(name, {}).get("main", [])[output]]


def test_repository_workflow_identity_and_sha_are_stable_shape():
    workflow = load()
    assert workflow["name"] == "SiteScore Order Paid Orchestration v1.0.0"
    assert workflow["meta"]["sitescoreWorkflowVersion"] == "1.0.0"
    assert workflow["meta"]["sitescoreBusinessIdentity"] == "sitescore-order-paid-v1"
    assert workflow["active"] is False
    assert len(hashlib.sha256(WORKFLOW.read_bytes()).hexdigest()) == 64


def test_zero_code_nodes_and_native_node_inventory_only():
    workflow = load()
    types = {node["type"] for node in workflow["nodes"]}
    assert not any("code" in value.lower() or "function" in value.lower() for value in types)
    assert types <= {"n8n-nodes-base.webhook","n8n-nodes-base.if","n8n-nodes-base.respondToWebhook","n8n-nodes-base.httpRequest","n8n-nodes-base.wait","n8n-nodes-base.noOp","n8n-nodes-base.stopAndError"}


def test_export_has_no_literal_secret_or_privileged_provider_material():
    text = WORKFLOW.read_text()
    for pattern in [r"sk_live_[A-Za-z0-9]+",r"sk_test_[A-Za-z0-9]+",r"whsec_[A-Za-z0-9]+",r"ssk1_[A-Za-z0-9]",r"AKIA[0-9A-Z]{16}",r"postgresql(?:\+psycopg)?://",r"redis://"]:
        assert re.search(pattern, text) is None
    lowered = text.lower()
    for forbidden in ["stripe_secret_key","stripe_webhook_secret","postmark","sitescore_api_service_key","s3_","aws_secret","database_url","/v1/analyses","/v1/reports","/content"]:
        assert forbidden not in lowered


def test_ingress_is_transport_authenticated_with_distinct_env_role():
    workflow = load(); nodes = by_name(workflow)
    assert nodes["Order Paid Ingress"]["parameters"]["path"] == "sitescore-order-paid-v1"
    auth = json.dumps(nodes["Authenticate Ingress"])
    assert "COMMERCE_N8N_INGRESS_SECRET" in auth
    assert "COMMERCE_AUTOMATION_API_KEY" not in auth
    assert targets(workflow, "Order Paid Ingress") == ["Authenticate Ingress"]
    assert targets(workflow, "Authenticate Ingress", 1) == ["Reject Unauthorized"]
    assert nodes["Reject Unauthorized"]["parameters"]["options"]["responseCode"] == 401


def test_trigger_validation_precedes_acceptance_and_commerce_lookup():
    workflow = load(); nodes = by_name(workflow); validate = json.dumps(nodes["Validate Trigger"])
    for required in ["event_id","event_type","order_id","occurred_at","order.paid.v1"]: assert required in validate
    assert targets(workflow, "Authenticate Ingress", 0) == ["Validate Trigger"]
    assert targets(workflow, "Validate Trigger", 0) == ["Accept Trigger"]
    assert targets(workflow, "Validate Trigger", 1) == ["Reject Invalid Trigger"]
    assert nodes["Reject Invalid Trigger"]["parameters"]["options"]["responseCode"] == 400
    assert nodes["Accept Trigger"]["parameters"]["options"]["responseCode"] == 202
    assert targets(workflow, "Accept Trigger") == ["Get Commerce State"]


def test_only_commerce_automation_http_boundary_is_used():
    workflow = load(); nodes = by_name(workflow)
    http_nodes = [node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.httpRequest"]
    assert {node["name"] for node in http_nodes} == {"Get Commerce State", "Advance Commerce"}
    for node in http_nodes:
        blob = json.dumps(node)
        assert "SITESCORE_COMMERCE_AUTOMATION_BASE_URL" in blob
        assert "COMMERCE_AUTOMATION_API_KEY" in blob
        assert "COMMERCE_N8N_INGRESS_SECRET" not in blob
        assert node.get("retryOnFail") is True and node.get("maxTries") == 3 and node.get("waitBetweenTries") == 2000
    get = nodes["Get Commerce State"]["parameters"]; advance = nodes["Advance Commerce"]["parameters"]
    assert "/v1/automation/orders/" in get["url"]
    assert advance["method"] == "POST" and advance["url"].endswith(" + '/advance' }}")
    assert advance.get("sendBody") is not True and "bodyParameters" not in advance and "jsonBody" not in advance


def test_state_machine_branches_only_on_commerce_projection():
    workflow = load()
    assert targets(workflow, "Get Commerce State") == ["Terminal State?"]
    assert targets(workflow, "Terminal State?", 0) == ["Stop Terminal"]
    assert targets(workflow, "Terminal State?", 1) == ["Delivery Boundary?"]
    assert targets(workflow, "Delivery Boundary?", 0) == ["Stop At Delivery Pending"]
    assert targets(workflow, "Advance Requested?", 0) == ["Advance Commerce"]
    assert targets(workflow, "Refund Requested?", 0) == ["Advance Commerce"]
    assert targets(workflow, "Wait Requested?", 0) == ["Within Poll Horizon?"]
    assert targets(workflow, "No Action?", 0) == ["Stop No Action"]
    assert targets(workflow, "Advance Commerce") == ["Get Commerce State"]
    assert targets(workflow, "Wait Before Poll") == ["Get Commerce State"]
    blob = json.dumps(workflow)
    for action in ["advance","refund","wait","delivery","none"]: assert action in blob
    for forbidden in ["analysis_id","report_id","refund_amount","refund_reason","payment_intent","paid=true","fulfilled"]: assert forbidden not in blob.lower()


def test_wait_is_finite_configurable_and_poll_horizon_fails_without_business_mutation():
    workflow = load(); nodes = by_name(workflow)
    assert "SITESCORE_N8N_POLL_SECONDS" in json.dumps(nodes["Wait Before Poll"])
    assert "SITESCORE_N8N_MAX_POLLS" in json.dumps(nodes["Within Poll Horizon?"])
    assert targets(workflow, "Within Poll Horizon?", 1) == ["Fail Poll Horizon"]
    assert nodes["Fail Poll Horizon"]["type"] == "n8n-nodes-base.stopAndError"


def test_runtime_definition_pins_exact_n8n_and_only_narrow_business_credentials():
    text = RUNTIME.read_text(); assert "n8nio/n8n:2.33.4" in text
    for floating in ["n8nio/n8n:latest","n8nio/n8n:stable","n8nio/n8n:next","n8nio/n8n:beta"]: assert floating not in text
    assert "COMMERCE_N8N_INGRESS_SECRET" in text and "COMMERCE_AUTOMATION_API_KEY" in text and "SITESCORE_COMMERCE_AUTOMATION_BASE_URL" in text
    lowered = text.lower()
    for forbidden in ["stripe_secret_key","stripe_webhook_secret","sitescore_api_service_key","postmark","postgresql://","redis://","aws_secret","s3_"]: assert forbidden not in lowered
