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


def test_fresh_upgrade_downgrade_and_reupgrade_on_postgresql():
    assert DATABASE_URL is not None
    cfg = _config()
    command.downgrade(cfg, "base")
    engine = create_engine(DATABASE_URL)
    assert not ({"consumers", "service_api_keys", "analyses", "dispatch_outbox"} & set(inspect(engine).get_table_names()))

    command.upgrade(cfg, "head")
    tables = set(inspect(engine).get_table_names())
    assert {"consumers", "service_api_keys", "analyses", "dispatch_outbox"}.issubset(tables)
    unique = {item["name"] for item in inspect(engine).get_unique_constraints("analyses")}
    assert "uq_analysis_consumer_idempotency" in unique

    command.downgrade(cfg, "base")
    assert not ({"consumers", "service_api_keys", "analyses", "dispatch_outbox"} & set(inspect(engine).get_table_names()))
    command.upgrade(cfg, "head")
    assert {"consumers", "service_api_keys", "analyses", "dispatch_outbox"}.issubset(set(inspect(engine).get_table_names()))
