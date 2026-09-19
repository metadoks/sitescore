from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect

DATABASE_URL = os.getenv("SITESCORE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="real PostgreSQL migration test requires SITESCORE_DATABASE_URL")
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _config() -> Config:
    return Config(str(PACKAGE_ROOT / "alembic.ini"))


def test_fresh_upgrade_0001_to_0002_to_0003_downgrade_and_reupgrade_on_postgresql():
    assert DATABASE_URL is not None
    cfg = _config()
    command.downgrade(cfg, "base")
    engine = create_engine(DATABASE_URL)
    all_tables = {"consumers", "service_api_keys", "analyses", "dispatch_outbox", "reports"}
    assert not (all_tables & set(inspect(engine).get_table_names()))

    command.upgrade(cfg, "0001_faz5_1")
    first_tables = set(inspect(engine).get_table_names())
    assert {"consumers", "service_api_keys", "analyses", "dispatch_outbox"}.issubset(first_tables)
    assert "reports" not in first_tables
    assert "canonical_success_at" not in {
        item["name"] for item in inspect(engine).get_columns("analyses")
    }

    command.upgrade(cfg, "0002_faz5_5")
    tables = set(inspect(engine).get_table_names())
    assert all_tables.issubset(tables)
    analysis_unique = {item["name"] for item in inspect(engine).get_unique_constraints("analyses")}
    report_unique = {item["name"] for item in inspect(engine).get_unique_constraints("reports")}
    report_checks = {item["name"] for item in inspect(engine).get_check_constraints("reports")}
    assert "uq_analysis_consumer_idempotency" in analysis_unique
    assert "uq_reports_analysis_artifact_version" in report_unique
    assert {"ck_report_state", "ck_report_state_coherence"}.issubset(report_checks)
    assert any(item["referred_table"] == "analyses" for item in inspect(engine).get_foreign_keys("reports"))
    assert "canonical_success_at" not in {
        item["name"] for item in inspect(engine).get_columns("analyses")
    }

    command.upgrade(cfg, "0003_faz5_5")
    analysis_columns = {item["name"] for item in inspect(engine).get_columns("analyses")}
    analysis_checks = {item["name"] for item in inspect(engine).get_check_constraints("analyses")}
    assert "canonical_success_at" in analysis_columns
    assert {
        "ck_canonical_success_before_deadline",
        "ck_canonical_success_state",
    }.issubset(analysis_checks)

    command.downgrade(cfg, "0002_faz5_5")
    assert "canonical_success_at" not in {
        item["name"] for item in inspect(engine).get_columns("analyses")
    }
    assert "reports" in set(inspect(engine).get_table_names())

    command.downgrade(cfg, "0001_faz5_1")
    assert "reports" not in set(inspect(engine).get_table_names())
    assert {"consumers", "service_api_keys", "analyses", "dispatch_outbox"}.issubset(
        set(inspect(engine).get_table_names())
    )
    command.upgrade(cfg, "head")
    assert all_tables.issubset(set(inspect(engine).get_table_names()))
    assert "canonical_success_at" in {
        item["name"] for item in inspect(engine).get_columns("analyses")
    }
