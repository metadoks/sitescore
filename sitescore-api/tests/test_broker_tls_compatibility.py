from __future__ import annotations

import pytest

from sitescore_api.celery_app import build_celery
from sitescore_api.settings import Settings


_DATABASE_URL = "postgresql://user:password@db.example/sitescore"
_PEPPER = "p" * 32


def _settings(broker_url: str) -> Settings:
    return Settings(
        database_url=_DATABASE_URL,
        broker_url=broker_url,
        api_key_pepper=_PEPPER,
    )


def test_redis_broker_url_is_accepted() -> None:
    settings = _settings("redis://valkey.internal:6379/0")

    assert settings.broker_url == "redis://valkey.internal:6379/0"


def test_rediss_broker_url_is_accepted_without_rewrite() -> None:
    settings = _settings("rediss://valkey.internal:25061/0")

    assert settings.broker_url == "rediss://valkey.internal:25061/0"


def test_from_env_accepts_rediss_broker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITESCORE_DATABASE_URL", _DATABASE_URL)
    monkeypatch.setenv("SITESCORE_BROKER_URL", "rediss://valkey.internal:25061/0")
    monkeypatch.setenv("SITESCORE_API_KEY_PEPPER", _PEPPER)

    settings = Settings.from_env()

    assert settings.broker_url == "rediss://valkey.internal:25061/0"


@pytest.mark.parametrize(
    "broker_url",
    [
        "http://valkey.internal:6379/0",
        "https://valkey.internal:6379/0",
        "amqp://broker.internal",
        "valkey.internal:6379/0",
        "redisx://valkey.internal:6379/0",
    ],
)
def test_unsupported_broker_schemes_are_rejected(broker_url: str) -> None:
    with pytest.raises(ValueError, match="broker_url must use Redis"):
        _settings(broker_url)


def test_build_celery_preserves_rediss_transport_and_frozen_semantics() -> None:
    settings = _settings("rediss://valkey.internal:25061/0")

    app = build_celery(settings)

    assert app.conf.broker_url == settings.broker_url
    assert app.conf.result_backend is None
    assert app.conf.task_ignore_result is True
    assert app.conf.task_store_errors_even_if_ignored is False
    assert app.conf.task_acks_late is True
    assert app.conf.task_acks_on_failure_or_timeout is True
    assert app.conf.task_reject_on_worker_lost is True
    assert app.conf.worker_prefetch_multiplier == 1
    assert app.conf.task_soft_time_limit == settings.worker_soft_time_limit_seconds
    assert app.conf.task_time_limit == settings.worker_hard_time_limit_seconds
    assert app.conf.beat_schedule == {
        "sitescore-outbox-drain": {
            "task": "sitescore_api.drain_outbox",
            "schedule": 10.0,
        },
        "sitescore-timeout-reconcile": {
            "task": "sitescore_api.reconcile_timeouts",
            "schedule": 15.0,
        },
    }
