from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from .errors import AnalysisLifecycleUnavailable
from .ingress import AnalysisIngressCommand


@dataclass(frozen=True, slots=True)
class AcceptedAnalysisResource:
    analysis_id: UUID


@dataclass(frozen=True, slots=True)
class RetrievedAnalysisResource:
    analysis_id: UUID


class AnalysisLifecycleBackend(Protocol):
    def submit(self, command: AnalysisIngressCommand) -> AcceptedAnalysisResource:
        ...

    def retrieve(self, analysis_id: UUID) -> RetrievedAnalysisResource:
        ...


class UnavailableAnalysisLifecycleBackend:
    """Truthful FAZ 5.0 production default: no durable lifecycle exists yet."""

    def submit(self, command: AnalysisIngressCommand) -> AcceptedAnalysisResource:
        raise AnalysisLifecycleUnavailable("durable analysis lifecycle is unavailable")

    def retrieve(self, analysis_id: UUID) -> RetrievedAnalysisResource:
        raise AnalysisLifecycleUnavailable("durable analysis lifecycle is unavailable")
