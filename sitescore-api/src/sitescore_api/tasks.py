from __future__ import annotations

from uuid import UUID
from .runtime import build_runtime
from .worker import RetryableReportFinalization

runtime = build_runtime()
celery_app = runtime.celery_app


@celery_app.task(
    bind=True,
    name="sitescore_api.execute_analysis",
    ignore_result=True,
    max_retries=None,
)
def execute_analysis(self, analysis_id: str) -> None:
    try:
        runtime.worker.execute_analysis(UUID(analysis_id))
    except RetryableReportFinalization as exc:
        raise self.retry(exc=exc, countdown=5, max_retries=None)


@celery_app.task(name="sitescore_api.drain_outbox", ignore_result=True)
def drain_outbox() -> None:
    runtime.dispatcher.drain_pending(limit=100)


@celery_app.task(name="sitescore_api.reconcile_timeouts", ignore_result=True)
def reconcile_timeouts() -> None:
    runtime.worker.reconcile_expired(limit=100)
