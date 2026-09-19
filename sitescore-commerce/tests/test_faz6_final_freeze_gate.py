from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

from sitescore_commerce.api import create_app

ROOT = Path(__file__).resolve().parents[2]
COMMERCE = ROOT / "sitescore-commerce"
SRC = COMMERCE / "src" / "sitescore_commerce"
DOC = COMMERCE / "docs" / "FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md"
ORDER_WORKFLOW = ROOT / "automation" / "n8n" / "workflows" / "sitescore-order-paid-v1.json"
RECOVERY_WORKFLOW = ROOT / "automation" / "n8n" / "workflows" / "sitescore-recovery-schedule-v1.json"
RUNTIME = ROOT / "automation" / "n8n" / "runtime" / "docker-compose.yml"

FAZ6_START = "0e370940ee5c8c1253db72fa7e33078fb4ef3b2c"
PRE_CORRECTIVE_MAIN = "287367ce8eb708efce0ebae0a2f9c90d681cce01"
FAZ6_LOCKED_MAIN = "df4e3181712e7f426f8f1752628952a620c98f05"
ORDER_WORKFLOW_SHA256 = "02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1"
RECOVERY_WORKFLOW_SHA256 = "f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c"

LOCK_CHAIN = (
    ("af3b9567d644f6bcf0410af704dd7d86de41b5ce", FAZ6_START, "8a4e358709ae7a662bf079722db042fb6e319ffd"),
    ("8027239b4b168e98e8ee16e15787366632017156", "af3b9567d644f6bcf0410af704dd7d86de41b5ce", "719a17c4359524337f57298252a59ccb89dcd0aa"),
    ("acc213ac52f980789164d9fedcd4e18deeefcf75", "8027239b4b168e98e8ee16e15787366632017156", "3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628"),
    ("7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba", "acc213ac52f980789164d9fedcd4e18deeefcf75", "64887a560c4af492312e726f990363fc5010345d"),
    ("bdf43a891ca14941ba2f2c4f115e4a15bec0015a", "7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba", "1f22c4a09c08c2803c746b87a20209d7fdf6c574"),
    (PRE_CORRECTIVE_MAIN, "bdf43a891ca14941ba2f2c4f115e4a15bec0015a", "4ed902dd9ebf230dcb983392705ab0d95bb0c846"),
    (FAZ6_LOCKED_MAIN, PRE_CORRECTIVE_MAIN, "813e3436bc3f899a774c853a6a81ba7924b54c42"),
)

ALLOWED_HTTP_SURFACE = {
    ("POST", "/v1/orders"),
    ("POST", "/v1/webhooks/stripe"),
    ("POST", "/v1/automation/orders/{order_id}/advance"),
    ("POST", "/v1/automation/orders/{order_id}/deliver"),
    ("GET", "/v1/automation/orders/{order_id}"),
    ("POST", "/v1/automation/recovery/run"),
    ("GET", "/d/{opaque_token}"),
}
DIRECT_ROUTE_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head", "trace"})
FORBIDDEN_ROUTE_REGISTRARS = frozenset({
    "include_router", "add_api_route", "route", "add_route", "mount",
    "websocket", "websocket_route", "add_websocket_route",
})


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


def _attribute_chain(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return tuple(reversed(parts))


def _literal_path(call: ast.Call) -> str:
    candidates: list[ast.AST] = []
    if call.args:
        candidates.append(call.args[0])
    candidates.extend(k.value for k in call.keywords if k.arg == "path")
    if len(candidates) != 1:
        raise AssertionError("route registration must declare exactly one literal path")
    value = candidates[0]
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str) or not value.value.startswith("/"):
        raise AssertionError("route registration path must be a literal absolute path")
    return value.value


def _literal_api_route_methods(call: ast.Call) -> tuple[str, ...]:
    values = [k.value for k in call.keywords if k.arg == "methods"]
    if len(values) != 1:
        raise AssertionError("app.api_route must declare one literal methods collection")
    container = values[0]
    if not isinstance(container, (ast.List, ast.Tuple, ast.Set)) or not container.elts:
        raise AssertionError("app.api_route methods must be a non-empty literal collection")
    methods: list[str] = []
    for item in container.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str) or not item.value.strip():
            raise AssertionError("app.api_route methods must contain literal strings")
        methods.append(item.value.strip().upper())
    return tuple(methods)


def _extract_source_http_surface(source: str) -> set[tuple[str, str]]:
    tree = ast.parse(source)
    routes: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        chain = _attribute_chain(node.func)
        if not chain or chain[0] != "app":
            continue
        registrar = chain[-1]
        if len(chain) == 2 and registrar in DIRECT_ROUTE_METHODS:
            routes.add((registrar.upper(), _literal_path(node)))
            continue
        if len(chain) == 2 and registrar == "api_route":
            path = _literal_path(node)
            routes.update((method, path) for method in _literal_api_route_methods(node))
            continue
        if registrar in FORBIDDEN_ROUTE_REGISTRARS or "router" in chain[1:]:
            raise AssertionError(f"unresolved route registration mechanism: {'.'.join(chain)}")
    return routes


def _constructed_runtime_app():
    return create_app(
        service=object(),
        webhook_service=object(),
        fulfillment_service=object(),
    )


def test_final_candidate_is_based_on_corrective_locked_main_and_permanent_diff_is_audit_only():
    assert _git("merge-base", FAZ6_LOCKED_MAIN, "HEAD") == FAZ6_LOCKED_MAIN
    changed = [p for p in _git("diff", "--name-only", FAZ6_LOCKED_MAIN, "HEAD").splitlines() if p]
    permanent = {p for p in changed if not p.startswith(".github/workflows/")}
    assert permanent == {
        "sitescore-commerce/docs/FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md",
        "sitescore-commerce/tests/test_faz6_final_freeze_gate.py",
    }


def test_exact_lock_provenance_including_corrective_merge():
    for merge_sha, parent1, parent2 in LOCK_CHAIN:
        parents = _git("show", "-s", "--format=%P", merge_sha).split()
        assert parents == [parent1, parent2]
    assert _git("merge-base", FAZ6_START, FAZ6_LOCKED_MAIN) == FAZ6_START


def test_faz6_history_never_mutated_frozen_faz3_4_5_source():
    changed = [p for p in _git("diff", "--name-only", FAZ6_START, FAZ6_LOCKED_MAIN).splitlines() if p]
    assert changed
    assert all(p.startswith("sitescore-commerce/") or p.startswith("automation/n8n/") for p in changed)


def test_runtime_http_surface_is_exactly_seven_and_framework_docs_are_absent():
    app = _constructed_runtime_app()
    resolved = {
        (method, route.path)
        for route in app.routes
        for method in (getattr(route, "methods", None) or set())
    }
    assert resolved == ALLOWED_HTTP_SURFACE
    assert len(app.routes) == 7
    paths = {route.path for route in app.routes}
    assert "/openapi.json" not in paths
    assert "/docs" not in paths
    assert "/redoc" not in paths
    assert "/docs/oauth2-redirect" not in paths


def test_source_route_registration_is_fail_closed_defense_in_depth():
    source = (SRC / "api.py").read_text()
    assert _extract_source_http_surface(source) == ALLOWED_HTTP_SURFACE
    base = '@app.get("/ok")\ndef ok():\n    return None\n'
    for method in ("put", "patch", "delete", "options", "head", "trace"):
        drift = base + f'@app.{method}("/drift")\ndef drift():\n    return None\n'
        assert (method.upper(), "/drift") in _extract_source_http_surface(drift)
    for registration in (
        'app.include_router(router)',
        'app.add_api_route("/hidden", endpoint, methods=["GET"])',
        'app.router.add_api_route("/hidden", endpoint, methods=["GET"])',
        'app.api_route(dynamic_path, methods=["GET"])(endpoint)',
        'app.api_route("/hidden", methods=dynamic_methods)(endpoint)',
    ):
        try:
            _extract_source_http_surface(registration)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"route drift silently ignored: {registration}")


def test_commerce_version_dependency_migration_and_http_server_owned_contracts_are_frozen():
    pyproject = (COMMERCE / "pyproject.toml").read_text()
    init = (SRC / "__init__.py").read_text()
    api = (SRC / "api.py").read_text()
    assert 'version = "0.6.0"' in pyproject
    assert '__version__ = "0.6.0"' in init
    for pin in (
        "fastapi==0.140.0", "pydantic==2.13.4", "SQLAlchemy==2.0.51",
        "alembic==1.18.5", "psycopg[binary]==3.3.4", "stripe==15.4.0", "httpx==0.28.1",
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
        wanted = "None" if down_revision is None else f'"{down_revision}"'
        assert f"down_revision = {wanted}" in text
    assert api.count("authorize_automation(authorization)") >= 4
    for phrase in (
        "automation advance request body must be empty",
        "automation delivery request body must be empty",
        "automation recovery request body must be empty",
    ):
        assert phrase in api


def test_n8n_runtime_image_and_workflow_bytes_are_exact():
    runtime = RUNTIME.read_text()
    assert "n8nio/n8n:2.33.4" in runtime
    for floating in ("n8nio/n8n:latest", "n8nio/n8n:stable", "n8nio/n8n:next", "n8nio/n8n:beta"):
        assert floating not in runtime
    assert _sha256(ORDER_WORKFLOW) == ORDER_WORKFLOW_SHA256
    assert _sha256(RECOVERY_WORKFLOW) == RECOVERY_WORKFLOW_SHA256


def test_n8n_remains_orchestration_only_and_recovery_scheduler_is_minimal():
    order = json.loads(ORDER_WORKFLOW.read_text())
    recovery = json.loads(RECOVERY_WORKFLOW.read_text())
    order_types = {node["type"] for node in order["nodes"]}
    assert not any("code" in t.lower() or "function" in t.lower() for t in order_types)
    assert [node["type"] for node in recovery["nodes"]] == [
        "n8n-nodes-base.scheduleTrigger",
        "n8n-nodes-base.httpRequest",
    ]
    blob = json.dumps(recovery, sort_keys=True).lower()
    assert "/v1/automation/recovery/run" in blob
    assert "commerce_automation_api_key" in blob
    for forbidden in (
        "stripe_secret_key", "stripe_webhook_secret", "postmark", "sitescore_api_service_key",
        "postgresql://", "redis://", "aws_secret", "customer_email", "recipient",
        "opaque_token", "/v1/analyses", "/v1/reports",
    ):
        assert forbidden not in blob


def test_commerce_runtime_does_not_import_frozen_sitescore_authority():
    forbidden = (
        "sitescore_api", "sitescore_report", "sitescore_pipeline", "sitescore_benchmarks",
        "sitescore_metrics", "sitescore_spatial", "sitescore_providers", "sitescore_data", "sitescore_core",
    )
    offenders: list[tuple[str, str]] = []
    for path in SRC.rglob("*.py"):
        for module in _imports(path):
            if module.startswith(forbidden):
                offenders.append((str(path.relative_to(ROOT)), module))
    assert offenders == []


def test_delivery_acceptance_token_and_private_storage_semantics_remain_locked():
    delivery = (SRC / "delivery.py").read_text()
    api = (SRC / "api.py").read_text()
    assert "DELIVERY_GRANT_TTL = timedelta(days=7)" in delivery
    assert "TOKEN_BYTES = 32" in delivery
    assert "secrets.token_urlsafe(TOKEN_BYTES)" in delivery
    assert "hashlib.sha256(raw_token.encode(\"ascii\"))" in delivery
    assert "provider_accepted" in delivery and "provider_uncertain" in delivery
    assert "PostmarkUncertain" in delivery
    assert "POSTMARK_ENDPOINT = \"https://api.postmarkapp.com/email/withTemplate\"" in delivery
    for header in ("Cache-Control", "private, no-store", "Referrer-Policy", "no-referrer", "X-Content-Type-Options", "nosniff"):
        assert header in api


def test_recovery_keeps_lease_fencing_real_stripe_lineage_and_same_outbox_identity():
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
    assert "PaymentPollReceiptRow" in combined or "payment_poll_receipt" in combined.lower()
    authority_code = re.sub(r"event_id|stripe_event_id", "", "\n".join((recovery, atomic, lineage)))
    assert "evt_" not in authority_code


def test_final_audit_records_corrective_runtime_truth_and_claim_boundaries():
    text = DOC.read_text()
    normalized = text.lower().replace("**", "")
    assert "main@df4e3181712e7f426f8f1752628952a620c98f05" in text
    assert "#30" in text and "813e3436bc3f899a774c853a6a81ba7924b54c42" in text
    assert "Mathematically validated scoring engine; empirical validation pending." in text
    assert "not empirical business-outcome validation" in normalized
    assert "constructed runtime application" in normalized
    for path in ("/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"):
        assert path in text
    for required in (
        "pending payment", "expired/unpaid", "paid + analysis pending/running",
        "paid + report pending", "paid + delivery pending", "paid + provider_uncertain delivery",
        "paid + delivery_failed/attention", "fulfilled", "refund pending", "refunded", "corrupt/impossible",
    ):
        assert required in text
    assert "does **not** claim exactly-once" in text
