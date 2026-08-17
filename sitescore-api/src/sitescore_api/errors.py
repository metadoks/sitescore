from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .version import API_VERSION


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    error: ErrorBody


class AnalysisLifecycleUnavailable(RuntimeError):
    pass


class IngressCommandValidationError(ValueError):
    pass
