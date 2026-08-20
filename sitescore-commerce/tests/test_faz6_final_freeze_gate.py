from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMERCE = ROOT / "sitescore-commerce"
SRC = COMMERCE / "src" / "sitescore_commerce"
DOC = COMMERCE / "docs" / "FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md"
ORDER_WORKFLOW = ROOT / "automation" / "n8n" / "workflows" / "sitescore-order-paid-v1.json"
RECOVERY_WORKFLOW = ROOT / "automation" / "n8n" / "workflows" / "sitescore-recovery-schedule-v1.json"
RUNTIME = ROOT / "automation" / "n8n" / "runtime" / "docker-compose.yml"

FAZ6_START = "0e370940ee5c8c1253db72fa7e33078fb4ef3b2c"
FAZ6_LOCKED_MAIN = "287367ce8eb708efce0ebae0a2f9c90d681cce01"
ORDER_WORKFLOW_SHA256 = "02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1"
RECOVERY_WORKFLOW_SHA256 = "f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c"

LOCK_CHAIN = (
    ("af3b9567d644f6bcf0410af704dd7d86de41b5ce", FAZ6_START, "8a4e358709ae7a662bf079722db042fb6e319ffd"),
    ("8027239b4b168e98e8ee16e15787366632017156", "af3b9567d644f6bcf0410af704dd7d86de41b5ce", "719a17c4359524337f57298252a59ccb89dcd0aa"),
    ("acc213ac52f980789164d9fedcd4e18deeefcf75", "8027239b4b168e98e8ee16e15787366632017156", "3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628"),
    ("7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba", "acc213ac52f980789164d9fedcd4e18deeefcf75", "64887a560c4af492312e726f990363fc5010345d"),
    ("bdf43a891ca14941ba2f2c4f115e4a15bec0015a", "7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba", "1f22c4a09c08c2803c746b87a20209d7fdf6c574"),
    (FAZ6_LOCKED_MAIN, "bdf43a891ca14941ba2f2c4f115e4a15bec0015a", "4ed902dd9ebf230dcb983392705ab0d95bb0c846"),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_exact_lock_provenance_and_linear_main_parentage():
    for merge_sha, expected_parent_1, expected_parent_2 in LOCK_CHAIN:
        parents = _git("show", "-s", "--format=%P", merge_sha).split()
        assert parents == [expected_parent_1, expected_parent_2]
    assert _git("merge-base", FAZ6_START, FAZ6_LOCKED_MAIN) == FAZ6_START


def test_faz6_history_did_not_mutate_frozen_faz3_4_5_source():
    changed = [p for p in _git("diff", "--name-only", FAZ6_START, FAZ6_LOCKED_MAIN).splitlines() if p]
    assert changed
    assert all(path.startswith("sitescore-commerce/") or path.startswith("automation/n8n/") for path in changed)


def test_frozen_runtime_version_dependency_and_migration_head():
    pyproject = (COMMERCE / "pyproject.toml").read_text()
    init = (SRC / "__init__.py").read_text()
    assert 'version = "0.6.0"' in pyproject
    assert '__version__ = "0.6.0"' in init
    for pin in (
        "fastapi==0.140.0",
        "pydantic==2.13.4",
        "SQLAlchemy==2.0.51",
        "alembic==1.18.5",
        "psycopg[binary]==3.3.4",
        "stripe==15.4.0",
        "httpx==0.28.1",
    ):
        assert pin in pyproject

    expected = [
        ("0001_commerce_order_checkout.py", "0001_commerce_order_checkout", None),
        ("0002_webhook_payment_authority.py", "0002_webhook_payment_authority", "0001_commerce_order_checkout"),
        ("0003_fulfillment_refund.py", "0003_fulfillment_refund", "0002_webhook_payment_authority"),
        ("0004_delivery_email.py", "0004_delivery_email", "0003_fulfillment_refund"),
        ("0005_recovery_reconciliation.py", "0005_recovery_reconciliation", "0004_delivery_email"),
    ]
    for filename, revision, down_revision in expected:
        text = (COMMERCE / "alembic" / "versions" / filename).read_text()
        assert f'revision = "{revision}"' in text
        expected_down = "None" if down_revision is None else f'"{down_revision}"'
        assert f"down_revision = {expected_down}" in text


def test_n8n_runtime_and_locked_workflow_bytes_are_exact():
    runtime = RUNTIME.read_text()
    assert "n8nio/n8n:2.33.4" in runtime
    for floating in ("n8nio/n8n:latest", "n8nio/n8n:stable", "n8nio/n8n:next", "n8nio/n8n:beta"):
        assert floating not in runtime
    assert _sha256(ORDER_WORKFLOW) == ORDER_WORKFLOW_SHA256
    assert _sha256(RECOVERY_WORKFLOW) == RECOVERY_WORKFLOW_SHA256


def test_public_http_surface_is_exact_and_automation_posts_are_server_owned_empty_body():
    text = (SRC / "api.py").read_text()
    routes = set(re.findall(r'@app\.(get|post)\("([^"]+)"', text))
    assert routes == {
        ("post", "/v1/orders"),
        ("post", "/v1/webhooks/stripe"),
        ("post", "/v1/automation/orders/{order_id}/advance"),
        ("post", "/v1/automation/orders/{order_id}/deliver"),
        ("get", "/v1/automation/orders/{order_id}"),
        ("post", "/v1/automation/recovery/run"),
        ("get", "/d/{opaque_token}"),
    }
    assert text.count("authorize_automation(authorization)") >= 4
    for phrase in (
        "automation advance request body must be empty",
        "automation delivery request body must be empty",
        "automation recovery request body must be empty",
    ):
        assert phrase in text
    for header in ("Cache-Control", "private, no-store", "Referrer-Policy", "no-referrer", "X-Content-Type-Options", "nosniff"):
        assert header in text


def test_commerce_runtime_does_not_import_frozen_sitescore_authority():
    forbidden_prefixes = (
        "sitescore_api",
        "sitescore_report",
        "sitescore_pipeline",
        "sitescore_benchmarks",
        "sitescore_metrics",
        "sitescore_spatial",
        "sitescore_providers",
        "sitescore_data",
        "sitescore_core",
    )
    offenders: list[tuple[str, str]] = []
    for path in SRC.rglob("*.py"):
        for module in _imports(path):
            if module.startswith(forbidden_prefixes):
                offenders.append((str(path.relative_to(ROOT)), module))
    assert offenders == []


def test_n8n_is_orchestration_only_and_scheduler_is_minimal():
    order = json.loads(ORDER_WORKFLOW.read_text())
    recovery = json.loads(RECOVERY_WORKFLOW.read_text())
    order_types = {node["type"] for node in order["nodes"]}
    assert not any("code" in value.lower() or "function" in value.lower() for value in order_types)
    assert order_types <= {
        "n8n-nodes-base.webhook",
        "n8n-nodes-base.if",
        "n8n-nodes-base.respondToWebhook",
        "n8n-nodes-base.httpRequest",
        "n8n-nodes-base.wait",
        "n8n-nodes-base.noOp",
        "n8n-nodes-base.stopAndError",
    }
    assert [node["type"] for node in recovery["nodes"]] == [
        "n8n-nodes-base.scheduleTrigger",
        "n8n-nodes-base.httpRequest",
    ]
    scheduler_blob = json.dumps(recovery, sort_keys=True).lower()
    assert "/v1/automation/recovery/run" in scheduler_blob
    assert "commerce_automation_api_key" in scheduler_blob
    for forbidden in (
        "stripe_secret_key",
        "stripe_webhook_secret",
        "postmark",
        "sitescore_api_service_key",
        "postgresql://",
        "redis://",
        "aws_secret",
        "customer_email",
        "recipient",
        "opaque_token",
        "/v1/analyses",
        "/v1/reports",
    ):
        assert forbidden not in scheduler_blob


def test_delivery_capability_and_email_acceptance_semantics_remain_locked():
    text = (SRC / "delivery.py").read_text()
    assert "DELIVERY_GRANT_TTL = timedelta(days=7)" in text
    assert "TOKEN_BYTES = 32" in text
    assert "secrets.token_urlsafe(TOKEN_BYTES)" in text
    assert "hashlib.sha256(raw_token.encode(\"ascii\"))" in text
    assert "provider_accepted" in text
    assert "provider_uncertain" in text
    assert "PostmarkUncertain" in text
    assert "POSTMARK_ENDPOINT = \"https://api.postmarkapp.com/email/withTemplate\"" in text


def test_recovery_keeps_lease_fencing_and_same_paid_outbox_identity_contract():
    recovery = (SRC / "recovery.py").read_text()
    atomic = (SRC / "recovery_atomic.py").read_text()
    lineage = (SRC / "recovery_lineage.py").read_text()
    db = (SRC / "db.py").read_text()
    migration = (COMMERCE / "alembic" / "versions" / "0005_recovery_reconciliation.py").read_text()
    combined = "\n".join((recovery, atomic, lineage, db, migration))
    assert "skip_locked=True" in combined
    assert "lease_token" in combined and "lease_expires_at" in combined
    assert "PAID_OUTBOX_TYPE" in combined
    assert "stripe_checkout_server_poll_v1" in combined
    assert "payment_poll_receipt" in combined.lower() or "PaymentPollReceiptRow" in combined
    assert "evt_" not in re.sub(r"event_id|stripe_event_id", "", "\n".join((recovery, atomic, lineage)))


def test_final_audit_contains_required_truth_disclaimer_and_state_money_matrix():
    text = DOC.read_text()
    normalized = text.lower().replace("**", "")
    assert "Mathematically validated scoring engine; empirical validation pending." in text
    assert "not empirical business-outcome validation" in normalized
    for required in (
        "pending payment",
        "expired/unpaid",
        "paid + analysis pending/running",
        "paid + report pending",
        "paid + delivery pending",
        "paid + provider_uncertain delivery",
        "paid + delivery_failed/attention",
        "fulfilled",
        "refund pending",
        "refunded",
        "corrupt/impossible",
    ):
        assert required in text
    assert "does **not** claim exactly-once" in text
