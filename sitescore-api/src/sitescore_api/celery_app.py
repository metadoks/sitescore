from __future__ import annotations

from celery import Celery
from .settings import Settings


def build_celery(settings: Settings) -> Celery:
    app = Celery("sitescore_api", broker=settings.broker_url, backend=None)
    app.conf.update(
        task_ignore_result=True,
        task_store_errors_even_if_ignored=False,
        task_acks_late=True,
        task_acks_on_failure_or_timeout=True,
        worker_prefetch_multiplier=1,
        task_soft_time_limit=settings.worker_soft_time_limit_seconds,
        task_time_limit=settings.worker_hard_time_limit_seconds,
        beat_schedule={
            "sitescore-outbox-drain": {
                "task": "sitescore_api.drain_outbox",
                "schedule": 10.0,
            },
            "sitescore-timeout-reconcile": {
                "task": "sitescore_api.reconcile_timeouts",
                "schedule": 15.0,
            },
        },
    )
    return app
