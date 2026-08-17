from __future__ import annotations

from uuid import UUID
from .runtime import build_runtime

runtime = build_runtime()
celery_app = runtime.celery_app


@celery_app.task(name="sitescore_api.execute_analysis", ignore_result=True)
def execute_analysis(analysis_id: str) -> None:
    runtime.worker.execute_analysis(UUID(analysis_id))


@celery_app.task(name="sitescore_api.drain_outbox", ignore_result=True)
def drain_outbox() -> None:
    runtime.dispatcher.drain_pending(limit=100)


@celery_app.task(name="sitescore_api.reconcile_timeouts", ignore_result=True)
def reconcile_timeouts() -> None:
    runtime.worker.reconcile_expired(limit=100)
