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

def test_runtime_dependencies_are_exact_and_exclude_future_systems():
    text=(ROOT/"pyproject.toml").read_text(); required=["fastapi==0.140.0","pydantic==2.13.4","SQLAlchemy==2.0.51","alembic==1.18.5","psycopg[binary]==3.3.4","stripe==15.4.0","httpx==0.28.1"]
    for pin in required: assert pin in text
    for forbidden in ["redis","celery","boto3","postmark","sitescore-api","sitescore-report"]: assert forbidden not in text.lower()

def test_migrations_only_target_commerce_schema():
    for name in ["0001_commerce_order_checkout.py","0002_webhook_payment_authority.py","0003_fulfillment_refund.py"]:
        text=(ROOT/"alembic"/"versions"/name).read_text()
        assert 'schema="commerce"' in text
        # Durable HTTP target snapshot column names may contain "sitescore_api";
        # forbid actual frozen-schema/table references instead.
        assert 'schema="public"' not in text
        assert "sitescore_api." not in text
        assert "api.alembic_version" not in text
        assert 'ForeignKey("api.' not in text
        assert 'ForeignKey("public.' not in text

def test_6_2_runtime_does_not_access_frozen_tables_or_delivery_content():
    text="\n".join(p.read_text() for p in (ROOT/"src").rglob("*.py"))
    for forbidden in ["sitescore_api.","analysis_runs","report_artifacts","/content","celery_app","send_task","boto3","postmark"]: assert forbidden not in text.lower()
