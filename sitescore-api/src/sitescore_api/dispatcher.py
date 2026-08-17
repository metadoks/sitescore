from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from celery import Celery
from sqlalchemy import select

from .db import Database
from .db_models import DispatchOutboxModel


class CeleryOutboxDispatcher:
    def __init__(self, database: Database, celery_app: Celery) -> None:
        self.database = database
        self.celery_app = celery_app

    def _publish(self, analysis_id: UUID, task_id: UUID) -> None:
        self.celery_app.send_task(
            "sitescore_api.execute_analysis",
            args=[str(analysis_id)],
            task_id=str(task_id),
        )

    def dispatch_analysis(self, analysis_id: UUID) -> None:
        with self.database.session() as session:
            row = session.scalar(
                select(DispatchOutboxModel).where(
                    DispatchOutboxModel.analysis_id == analysis_id,
                    DispatchOutboxModel.dispatched_at.is_(None),
                )
            )
            if row is None:
                return
            task_id = row.task_id
        try:
            self._publish(analysis_id, task_id)
        except Exception:
            with self.database.session() as session:
                with session.begin():
                    current = session.scalar(
                        select(DispatchOutboxModel)
                        .where(DispatchOutboxModel.analysis_id == analysis_id)
                        .with_for_update()
                    )
                    if current is not None and current.dispatched_at is None:
                        current.attempt_count += 1
                        current.last_error_code = "broker_publish_failed"
                        current.last_error_message = "broker publish failed"
            raise
        with self.database.session() as session:
            with session.begin():
                current = session.scalar(
                    select(DispatchOutboxModel)
                    .where(DispatchOutboxModel.analysis_id == analysis_id)
                    .with_for_update()
                )
                if current is not None and current.dispatched_at is None:
                    current.attempt_count += 1
                    current.dispatched_at = datetime.now(timezone.utc)
                    current.last_error_code = None
                    current.last_error_message = None

    def drain_pending(self, *, limit: int = 100) -> int:
        with self.database.session() as session:
            ids = list(
                session.scalars(
                    select(DispatchOutboxModel.analysis_id)
                    .where(DispatchOutboxModel.dispatched_at.is_(None))
                    .order_by(DispatchOutboxModel.created_at)
                    .limit(limit)
                )
            )
        dispatched = 0
        for analysis_id in ids:
            try:
                self.dispatch_analysis(analysis_id)
            except Exception:
                continue
            dispatched += 1
        return dispatched
