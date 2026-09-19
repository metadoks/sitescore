"""Versioned Census geocode acceptance policy; no empirical scoring thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .._validation import require_canonical_id, require_nonempty_text
from .models import CensusGeocodeEvidence, CensusMatchState


class CensusAcceptanceReason(StrEnum):
    ACCEPTED_SINGLE_MATCH = "accepted_single_match"
    NO_MATCH = "no_match"
    AMBIGUOUS_MATCH = "ambiguous_match"
    INVALID_COORDINATES = "invalid_coordinates"
    UNACCEPTED_MATCH_TYPE = "unaccepted_match_type"


@dataclass(frozen=True, slots=True)
class GeocodeAcceptanceDecision:
    accepted: bool
    fallback_eligible: bool
    reason: CensusAcceptanceReason

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted must be a bool")
        if not isinstance(self.fallback_eligible, bool):
            raise TypeError("fallback_eligible must be a bool")
        if not isinstance(self.reason, CensusAcceptanceReason):
            raise TypeError("reason must be CensusAcceptanceReason")
        if self.accepted and self.fallback_eligible:
            raise ValueError("accepted geocodes cannot simultaneously be fallback-eligible")


@dataclass(frozen=True, slots=True)
class GeocodeAcceptancePolicy:
    policy_id: str
    policy_version: str
    require_matched_address: bool = True
    fallback_on_no_match: bool = True
    fallback_on_ambiguous: bool = True
    accepted_match_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        for field_name in (
            "require_matched_address",
            "fallback_on_no_match",
            "fallback_on_ambiguous",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a bool")
        if not isinstance(self.accepted_match_types, tuple):
            raise TypeError("accepted_match_types must be a tuple")
        for match_type in self.accepted_match_types:
            require_nonempty_text(match_type, field_name="accepted_match_type")
        if len(set(self.accepted_match_types)) != len(self.accepted_match_types):
            raise ValueError("accepted_match_types must not contain duplicates")

    @property
    def method_version(self) -> str:
        return f"{self.policy_id}.{self.policy_version}"

    def evaluate(self, evidence: CensusGeocodeEvidence) -> GeocodeAcceptanceDecision:
        if not isinstance(evidence, CensusGeocodeEvidence):
            raise TypeError("evidence must be CensusGeocodeEvidence")
        if evidence.match_state is CensusMatchState.NO_MATCH:
            return GeocodeAcceptanceDecision(False, self.fallback_on_no_match, CensusAcceptanceReason.NO_MATCH)
        if evidence.match_state is CensusMatchState.AMBIGUOUS:
            return GeocodeAcceptanceDecision(False, self.fallback_on_ambiguous, CensusAcceptanceReason.AMBIGUOUS_MATCH)
        candidate = evidence.candidates[0]
        if self.require_matched_address and not candidate.matched_address:
            return GeocodeAcceptanceDecision(False, False, CensusAcceptanceReason.INVALID_COORDINATES)
        if self.accepted_match_types:
            if candidate.census_match_type not in self.accepted_match_types:
                return GeocodeAcceptanceDecision(False, False, CensusAcceptanceReason.UNACCEPTED_MATCH_TYPE)
        return GeocodeAcceptanceDecision(True, False, CensusAcceptanceReason.ACCEPTED_SINGLE_MATCH)
