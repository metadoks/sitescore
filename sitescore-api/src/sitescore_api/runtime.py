from __future__ import annotations

from dataclasses import dataclass
import importlib
import os

from .acquisition import CanonicalAcquisitionDeployment, CanonicalProviderEvidenceSource
from .celery_app import build_celery
from .db import Database
from .dispatcher import CeleryOutboxDispatcher
from .execution import CanonicalAnalysisExecutor, ExecutionEvidenceSource, MissingExecutionEvidenceSource
from .lifecycle import PostgresAnalysisLifecycleBackend
from .report_artifacts import (
    PostgresReportArtifactBackend,
    ReportArtifactGenerator,
    ReportObjectStorage,
    S3CompatibleObjectStorage,
)
from .settings import Settings
from .worker import AnalysisWorkerService


def _load_production_evidence_source() -> ExecutionEvidenceSource:
    """Load only server-owned deployment boundaries, never assembled execution evidence."""

    spec = os.getenv("SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY")
    if not spec:
        return MissingExecutionEvidenceSource()
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise ValueError("SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY must use module:callable")
    factory = getattr(importlib.import_module(module_name), attr)
    deployment = factory()
    if type(deployment) is not CanonicalAcquisitionDeployment:
        raise TypeError(
            "acquisition deployment factory must return exact CanonicalAcquisitionDeployment"
        )
    return CanonicalProviderEvidenceSource(deployment)


@dataclass(frozen=True, slots=True)
class Runtime:
    settings: Settings
    database: Database
    celery_app: object
    dispatcher: CeleryOutboxDispatcher
    lifecycle: PostgresAnalysisLifecycleBackend
    reports: PostgresReportArtifactBackend
    worker: AnalysisWorkerService


def build_runtime(
    settings: Settings | None = None,
    *,
    evidence_source: ExecutionEvidenceSource | None = None,
    report_storage: ReportObjectStorage | None = None,
) -> Runtime:
    """Build production runtime; explicit evidence/storage arguments are in-process test seams."""

    settings = settings or Settings.from_env()
    database = Database(settings.database_url)
    celery_app = build_celery(settings)
    dispatcher = CeleryOutboxDispatcher(database, celery_app)
    lifecycle = PostgresAnalysisLifecycleBackend(
        database,
        dispatcher,
        deadline_seconds=settings.analysis_deadline_seconds,
    )
    storage = report_storage or S3CompatibleObjectStorage(
        bucket=settings.report_storage_bucket,
        region=settings.report_storage_region,
        endpoint_url=settings.report_storage_endpoint_url,
    )
    reports = PostgresReportArtifactBackend(
        database,
        storage,
        max_bytes=settings.report_max_bytes,
    )
    report_generator = ReportArtifactGenerator(storage, max_bytes=settings.report_max_bytes)
    executor = CanonicalAnalysisExecutor(evidence_source or _load_production_evidence_source())
    worker = AnalysisWorkerService(database, executor, report_generator)
    return Runtime(settings, database, celery_app, dispatcher, lifecycle, reports, worker)
