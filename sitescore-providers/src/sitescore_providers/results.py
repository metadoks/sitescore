"""Typed deterministic acquisition outcomes, separate from domain evidence states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ._validation import require_canonical_id, require_nonempty_text
from .artifacts import RawAcquisitionArtifact


class AcquisitionState(StrEnum):
    SUCCESS = "success"
    PROVIDER_FAILURE = "provider_failure"
    POLICY_REJECTION = "policy_rejection"


class ProviderFailureKind(StrEnum):
    UNAVAILABLE = "unavailable"
    RATE_LIMIT = "rate_limit"
    QUOTA = "quota"
    AUTHENTICATION = "authentication"
    MALFORMED_RESPONSE = "malformed_response"
    INVARIANT = "invariant"


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    provider_key: str
    operation: str
    kind: ProviderFailureKind
    reason_code: str
    retryable: bool
    status_code: int | None = None

    def __post_init__(self) -> None:
        require_canonical_id(self.provider_key, field_name="provider_key")
        require_canonical_id(self.operation, field_name="operation")
        if not isinstance(self.kind, ProviderFailureKind):
            raise TypeError("kind must be a ProviderFailureKind")
        require_canonical_id(self.reason_code, field_name="reason_code")
        if not isinstance(self.retryable, bool):
            raise TypeError("retryable must be a bool")
        if self.status_code is not None:
            if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
                raise TypeError("status_code must be an int")
            if self.status_code < 100 or self.status_code > 599:
                raise ValueError("status_code must be a valid HTTP-style status code")


@dataclass(frozen=True, slots=True)
class PolicyRejection:
    policy_id: str
    policy_version: str
    reason_code: str

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        require_canonical_id(self.reason_code, field_name="reason_code")


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    state: AcquisitionState
    artifact: RawAcquisitionArtifact | None = None
    failure: ProviderFailure | None = None
    policy_rejection: PolicyRejection | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, AcquisitionState):
            raise TypeError("state must be an AcquisitionState")
        present = sum(value is not None for value in (self.artifact, self.failure, self.policy_rejection))
        if present != 1:
            raise ValueError("exactly one acquisition payload must be present")
        if self.state is AcquisitionState.SUCCESS:
            if self.artifact is None or self.failure is not None or self.policy_rejection is not None:
                raise ValueError("SUCCESS requires only an artifact")
        elif self.state is AcquisitionState.PROVIDER_FAILURE:
            if self.failure is None or self.artifact is not None or self.policy_rejection is not None:
                raise ValueError("PROVIDER_FAILURE requires only a failure")
        elif self.state is AcquisitionState.POLICY_REJECTION:
            if self.policy_rejection is None or self.artifact is not None or self.failure is not None:
                raise ValueError("POLICY_REJECTION requires only a policy rejection")

    @classmethod
    def success(cls, artifact: RawAcquisitionArtifact) -> "AcquisitionResult":
        return cls(state=AcquisitionState.SUCCESS, artifact=artifact)

    @classmethod
    def provider_failure(cls, failure: ProviderFailure) -> "AcquisitionResult":
        return cls(state=AcquisitionState.PROVIDER_FAILURE, failure=failure)

    @classmethod
    def policy_rejected(cls, rejection: PolicyRejection) -> "AcquisitionResult":
        return cls(state=AcquisitionState.POLICY_REJECTION, policy_rejection=rejection)
