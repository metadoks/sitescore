from __future__ import annotations

from dataclasses import dataclass
import importlib
import os

from .celery_app import build_celery
from .db import Database
from .dispatcher import CeleryOutboxDispatcher
from .execution import CanonicalAnalysisExecutor, ExecutionEvidenceSource, MissingExecutionEvidenceSource
from .lifecycle import PostgresAnalysisLifecycleBackend
from .settings import Settings
from .worker import AnalysisWorkerService


def _load_evidence_source() -> ExecutionEvidenceSource:
    spec = os.getenv("SITESCORE_EVIDENCE_SOURCE_FACTORY")
    if not spec:
        return MissingExecutionEvidenceSource()
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise ValueError("SITESCORE_EVIDENCE_SOURCE_FACTORY must use module:callable")
    factory = getattr(importlib.import_module(module_name), attr)
    source = factory()
    if not hasattr(source, "acquire"):
        raise TypeError("evidence source factory must return an acquire-capable object")
    return source


@dataclass(frozen=True, slots=True)
class Runtime:
    settings: Settings
    database: Database
    celery_app: object
    dispatcher: CeleryOutboxDispatcher
    lifecycle: PostgresAnalysisLifecycleBackend
    worker: AnalysisWorkerService


def build_runtime(
    settings: Settings | None = None,
    *,
    evidence_source: ExecutionEvidenceSource | None = None,
) -> Runtime:
    settings = settings or Settings.from_env()
    database = Database(settings.database_url)
    celery_app = build_celery(settings)
    dispatcher = CeleryOutboxDispatcher(database, celery_app)
    lifecycle = PostgresAnalysisLifecycleBackend(
        database,
        dispatcher,
        deadline_seconds=settings.analysis_deadline_seconds,
    )
    executor = CanonicalAnalysisExecutor(evidence_source or _load_evidence_source())
    worker = AnalysisWorkerService(database, executor)
    return Runtime(settings, database, celery_app, dispatcher, lifecycle, worker)
