"""Provider-neutral persistence and policy interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from sitescore_data import PersistenceClass

from ._validation import (
    require_aware_datetime,
    require_canonical_id,
    require_optional_aware_datetime,
    require_optional_nonempty_text,
    require_secret_free_reference,
    require_positive_int,
)


@dataclass(frozen=True, slots=True)
class PersistenceDecision:
    """Provider-neutral retention decision.

    ``SOURCE_POLICY`` denotes unresolved source-level retention and therefore
    carries no concrete temporal fields. Once external/source policy is
    resolved, callers construct a new concrete ``PERSIST``, ``TRANSIENT``, or
    ``DO_NOT_PERSIST`` decision. ``TRANSIENT`` carries exactly one temporal
    constraint: absolute ``expires_at`` or relative ``max_retention_seconds``.
    """

    policy_id: str
    policy_version: str
    persistence_class: PersistenceClass
    expires_at: datetime | None = None
    max_retention_seconds: int | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        if not isinstance(self.policy_version, str) or not self.policy_version or self.policy_version != self.policy_version.strip():
            raise ValueError("policy_version must be non-empty and trimmed")
        if not isinstance(self.persistence_class, PersistenceClass):
            raise TypeError("persistence_class must be a PersistenceClass")
        require_optional_aware_datetime(self.expires_at, field_name="expires_at")
        require_positive_int(self.max_retention_seconds, field_name="max_retention_seconds")
        if not isinstance(self.reason_codes, tuple):
            raise TypeError("reason_codes must be a tuple")
        for code in self.reason_codes:
            require_canonical_id(code, field_name="reason_code")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")

        if self.persistence_class is PersistenceClass.TRANSIENT:
            has_expiry = self.expires_at is not None
            has_max_retention = self.max_retention_seconds is not None
            if has_expiry == has_max_retention:
                raise ValueError(
                    "TRANSIENT persistence requires exactly one of expires_at or max_retention_seconds"
                )
        elif self.persistence_class in {
            PersistenceClass.PERSIST,
            PersistenceClass.DO_NOT_PERSIST,
            PersistenceClass.SOURCE_POLICY,
        }:
            if self.expires_at is not None or self.max_retention_seconds is not None:
                raise ValueError(f"{self.persistence_class.value} persistence cannot carry retention expiry")


class RedistributionState(StrEnum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class CommercialUseState(StrEnum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RequestedUse:
    use_case: str
    commercial: bool
    redistribution_requested: bool

    def __post_init__(self) -> None:
        require_canonical_id(self.use_case, field_name="use_case")
        if not isinstance(self.commercial, bool):
            raise TypeError("commercial must be a bool")
        if not isinstance(self.redistribution_requested, bool):
            raise TypeError("redistribution_requested must be a bool")


@dataclass(frozen=True, slots=True)
class ProviderPolicyDecision:
    policy_id: str
    policy_version: str
    persistence: PersistenceDecision
    attribution_required: bool
    redistribution_state: RedistributionState
    commercial_use_state: CommercialUseState
    license_class: str | None = None
    policy_reference: str | None = None

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        if not isinstance(self.policy_version, str) or not self.policy_version or self.policy_version != self.policy_version.strip():
            raise ValueError("policy_version must be non-empty and trimmed")
        if not isinstance(self.persistence, PersistenceDecision):
            raise TypeError("persistence must be a PersistenceDecision")
        if self.persistence.policy_id != self.policy_id or self.persistence.policy_version != self.policy_version:
            raise ValueError("policy identity must match the nested persistence decision")
        if not isinstance(self.attribution_required, bool):
            raise TypeError("attribution_required must be a bool")
        if not isinstance(self.redistribution_state, RedistributionState):
            raise TypeError("redistribution_state must be a RedistributionState")
        if not isinstance(self.commercial_use_state, CommercialUseState):
            raise TypeError("commercial_use_state must be a CommercialUseState")
        require_optional_nonempty_text(self.license_class, field_name="license_class")
        require_secret_free_reference(self.policy_reference, field_name="policy_reference")


@runtime_checkable
class ProviderPolicyRegistry(Protocol):
    def resolve(
        self,
        *,
        provider_key: str,
        dataset: str,
        operation: str,
        requested_use: RequestedUse,
    ) -> ProviderPolicyDecision:
        """Resolve generic policy semantics without embedding provider-specific tables."""
        ...
