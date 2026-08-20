from __future__ import annotations
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_runtime_has_no_sitescore_api_import():
    offenders=[]
    for path in (ROOT/"src").rglob("*.py"):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import) and any(alias.name.startswith("sitescore_api") for alias in node.names): offenders.append(str(path))
            elif isinstance(node,ast.ImportFrom) and (node.module or "").startswith("sitescore_api"): offenders.append(str(path))
    assert offenders==[]

def test_runtime_dependencies_are_exact_and_exclude_embedded_future_systems():
    text=(ROOT/"pyproject.toml").read_text(); required=["fastapi==0.140.0","pydantic==2.13.4","SQLAlchemy==2.0.51","alembic==1.18.5","psycopg[binary]==3.3.4","stripe==15.4.0","httpx==0.28.1"]
    for pin in required: assert pin in text
    for forbidden in ["redis","celery","boto3","postmark==","sitescore-api","sitescore-report"]: assert forbidden not in text.lower()
    assert 'version = "0.6.0"' in text

def test_migrations_only_target_commerce_schema():
    for name in ["0001_commerce_order_checkout.py","0002_webhook_payment_authority.py","0003_fulfillment_refund.py","0004_delivery_email.py","0005_recovery_reconciliation.py"]:
        text=(ROOT/"alembic"/"versions"/name).read_text()
        assert 'schema="commerce"' in text
        assert 'schema="public"' not in text
        assert "sitescore_api." not in text
        assert "api.alembic_version" not in text
        assert 'ForeignKey("api.' not in text
        assert 'ForeignKey("public.' not in text

def test_runtime_uses_http_boundaries_not_frozen_tables_or_private_storage():
    text="\n".join(p.read_text() for p in (ROOT/"src").rglob("*.py")).lower()
    for forbidden in ["sitescore_api.","analysis_runs","report_artifacts","celery_app","send_task","boto3","s3compatibleobjectstorage"]:
        assert forbidden not in text
    assert "/v1/reports/" in text
    assert "/content" in text
    assert "api.postmarkapp.com/email/withtemplate" in text
    assert "stripe_checkout_server_poll_v1" in text
