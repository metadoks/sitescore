"""Immutable scoring-readiness contracts.

These contracts describe whether normalized data-layer features are eligible to
proceed toward category aggregation.  They do not compute category scores,
import core configuration, or call the frozen scoring core.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    ScoreEligibility,
)
from sitescore_data.feature_surface import NORMALIZED_FEATURE_NAMES
from sitescore_data.validation import (
    require_aware_datetime,
    require_canonical_identifier,
)


class ScoringReadinessReason(StrEnum):
    MISSING_REQUIRED_FEATURE = "missing_required_feature"
    FEATURE_UNCALIBRATED = "feature_uncalibrated"
    FEATURE_DIAGNOSTIC_ONLY = "feature_diagnostic_only"
    FEATURE_INELIGIBLE = "feature_ineligible"
    INSUFFICIENT_DATA_QUALITY = "insufficient_data_quality"
    POLICY_NOT_CONFIGURED = "policy_not_configured"
    POLICY_VERSION_MISMATCH = "policy_version_mismatch"
    COMPETITION_MEASUREMENT_MISMATCH = "competition_measurement_mismatch"
    TRANSIT_SOURCE_BUNDLE_MISMATCH = "transit_source_bundle_mismatch"
    ROAD_PARKING_COMPOSITE_UNAVAILABLE = "road_parking_composite_unavailable"
    AGE_FALLBACK_POLICY_INVALID = "age_fallback_policy_invalid"


@dataclass(frozen=True, slots=True)
class PolicyVersionRef:
    """Deterministic identity for one required or resolved policy version."""

    policy_id: str
    version: str

    def __post_init__(self) -> None:
        require_canonical_identifier(self.policy_id, field_name="policy_id")
        if not isinstance(self.version, str):
            raise TypeError("version must be a string")
        if not self.version or self.version != self.version.strip():
            raise ValueError("version must be non-empty and trimmed")




@dataclass(frozen=True, slots=True)
class ApprovedFallbackPolicyRef:
    """Trusted approval identity for one explicitly frozen fallback policy."""

    feature_name: str
    policy_id: str
    policy_version: str

    def __post_init__(self) -> None:
        require_canonical_identifier(self.feature_name, field_name="feature_name")
        require_canonical_identifier(self.policy_id, field_name="policy_id")
        if not isinstance(self.policy_version, str):
            raise TypeError("policy_version must be a string")
        if not self.policy_version or self.policy_version != self.policy_version.strip():
            raise ValueError("policy_version must be non-empty and trimmed")


@dataclass(frozen=True, slots=True)
class FeatureReadinessPolicy:
    """Explicit readiness input for one normalized feature.

    ``fallback_policy_*`` declares the fallback requested by the trusted policy
    resolution input.  It is not itself approval.  Approval must be supplied
    separately as ``ApprovedFallbackPolicyRef`` to the validator.
    """

    feature_name: str
    required: bool
    required_policy_version: str | None = None
    resolved_policy_version: str | None = None
    fallback_policy_id: str | None = None
    fallback_policy_version: str | None = None

    def __post_init__(self) -> None:
        require_canonical_identifier(self.feature_name, field_name="feature_name")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a bool")

        for field_name in (
            "required_policy_version",
            "resolved_policy_version",
            "fallback_policy_id",
            "fallback_policy_version",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string or None")
            if not value or value != value.strip():
                raise ValueError(f"{field_name} must be non-empty and trimmed")

        if (self.fallback_policy_id is None) != (
            self.fallback_policy_version is None
        ):
            raise ValueError(
                "fallback_policy_id and fallback_policy_version must be set together"
            )


@dataclass(frozen=True, slots=True)
class ReadinessCompatibilityInput:
    """Externally resolved benchmark compatibility identities.

    Benchmark-specific identities remain outside generic ``BenchmarkReference``.
    ``None`` means the corresponding compatibility evidence is unresolved.
    """

    competition_benchmark_measurement_definition_id: str | None
    transit_benchmark_source_bundle_fingerprint: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "competition_benchmark_measurement_definition_id",
            "transit_benchmark_source_bundle_fingerprint",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string or None")
            if not value or value != value.strip():
                raise ValueError(f"{field_name} must be non-empty and trimmed")


@dataclass(frozen=True, slots=True)
class ScoringFeatureReadiness:
    feature_name: str
    required: bool
    availability: AvailabilityState
    data_quality: DataQualityState
    score_eligibility: ScoreEligibility
    calibration_state: CalibrationState
    required_policy_version: str | None
    resolved_policy_version: str | None
    fallback_policy_id: str | None
    fallback_policy_version: str | None
    reason_codes: tuple[ScoringReadinessReason, ...]

    def __post_init__(self) -> None:
        require_canonical_identifier(self.feature_name, field_name="feature_name")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a bool")
        if not isinstance(self.availability, AvailabilityState):
            raise TypeError("availability must be an AvailabilityState")
        if not isinstance(self.data_quality, DataQualityState):
            raise TypeError("data_quality must be a DataQualityState")
        if not isinstance(self.score_eligibility, ScoreEligibility):
            raise TypeError("score_eligibility must be a ScoreEligibility")
        if not isinstance(self.calibration_state, CalibrationState):
            raise TypeError("calibration_state must be a CalibrationState")

        for field_name in (
            "required_policy_version",
            "resolved_policy_version",
            "fallback_policy_id",
            "fallback_policy_version",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string or None")
            if not value or value != value.strip():
                raise ValueError(f"{field_name} must be non-empty and trimmed")

        if (self.fallback_policy_id is None) != (
            self.fallback_policy_version is None
        ):
            raise ValueError(
                "fallback_policy_id and fallback_policy_version must be set together"
            )

        if not isinstance(self.reason_codes, tuple):
            raise TypeError("reason_codes must be a tuple")
        if any(
            not isinstance(reason, ScoringReadinessReason)
            for reason in self.reason_codes
        ):
            raise TypeError(
                "reason_codes must contain ScoringReadinessReason values"
            )
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")


@dataclass(frozen=True, slots=True)
class ScoringReadinessResult:
    is_score_ready: bool
    missing_required_features: tuple[str, ...]
    uncalibrated_features: tuple[str, ...]
    insufficient_quality_features: tuple[str, ...]
    incompatible_features: tuple[str, ...]
    reason_codes: tuple[ScoringReadinessReason, ...]
    required_policy_versions: tuple[PolicyVersionRef, ...]
    resolved_policy_versions: tuple[PolicyVersionRef, ...]
    feature_states: tuple[ScoringFeatureReadiness, ...]
    validator_version: str
    evaluated_at: datetime
    readiness_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.is_score_ready, bool):
            raise TypeError("is_score_ready must be a bool")

        for field_name in (
            "missing_required_features",
            "uncalibrated_features",
            "insufficient_quality_features",
            "incompatible_features",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            for value in values:
                require_canonical_identifier(value, field_name=f"{field_name} item")
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")

        if not isinstance(self.reason_codes, tuple):
            raise TypeError("reason_codes must be a tuple")
        if any(
            not isinstance(reason, ScoringReadinessReason)
            for reason in self.reason_codes
        ):
            raise TypeError(
                "reason_codes must contain ScoringReadinessReason values"
            )
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")

        for field_name in (
            "required_policy_versions",
            "resolved_policy_versions",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if any(not isinstance(value, PolicyVersionRef) for value in values):
                raise TypeError(f"{field_name} must contain PolicyVersionRef values")
            policy_ids = tuple(value.policy_id for value in values)
            if len(set(policy_ids)) != len(policy_ids):
                raise ValueError(f"{field_name} policy_id values must be unique")
            if values != tuple(sorted(values, key=lambda item: item.policy_id)):
                raise ValueError(f"{field_name} must be ordered by policy_id")

        if not isinstance(self.feature_states, tuple):
            raise TypeError("feature_states must be a tuple")
        if any(
            not isinstance(value, ScoringFeatureReadiness)
            for value in self.feature_states
        ):
            raise TypeError(
                "feature_states must contain ScoringFeatureReadiness values"
            )
        feature_names = tuple(value.feature_name for value in self.feature_states)
        if len(set(feature_names)) != len(feature_names):
            raise ValueError("feature_states feature_name values must be unique")
        if feature_names != NORMALIZED_FEATURE_NAMES:
            raise ValueError(
                "feature_states must exactly match the frozen V1 normalized feature order"
            )
        if any(not value.required for value in self.feature_states):
            raise ValueError(
                "all frozen V1 feature_states must have required=True"
            )

        summary_reason_map = {
            "missing_required_features": ScoringReadinessReason.MISSING_REQUIRED_FEATURE,
            "uncalibrated_features": ScoringReadinessReason.FEATURE_UNCALIBRATED,
            "insufficient_quality_features": ScoringReadinessReason.INSUFFICIENT_DATA_QUALITY,
        }
        state_by_name = {state.feature_name: state for state in self.feature_states}
        for summary_name, reason in summary_reason_map.items():
            expected = tuple(
                state.feature_name
                for state in self.feature_states
                if reason in state.reason_codes
            )
            if getattr(self, summary_name) != expected:
                raise ValueError(
                    f"{summary_name} must exactly match feature_states reason codes"
                )

        compatibility_reasons = {
            ScoringReadinessReason.COMPETITION_MEASUREMENT_MISMATCH,
            ScoringReadinessReason.TRANSIT_SOURCE_BUNDLE_MISMATCH,
            ScoringReadinessReason.ROAD_PARKING_COMPOSITE_UNAVAILABLE,
        }
        expected_incompatible = tuple(
            state.feature_name
            for state in self.feature_states
            if any(reason in compatibility_reasons for reason in state.reason_codes)
        )
        if self.incompatible_features != expected_incompatible:
            raise ValueError(
                "incompatible_features must exactly match compatibility-related feature reasons"
            )

        expected_global_reasons = tuple(
            dict.fromkeys(
                reason
                for state in self.feature_states
                for reason in state.reason_codes
            )
        )
        if self.reason_codes != expected_global_reasons:
            raise ValueError(
                "reason_codes must exactly match the ordered union of feature-state reasons"
            )

        if not isinstance(self.validator_version, str):
            raise TypeError("validator_version must be a string")
        if not self.validator_version or self.validator_version != self.validator_version.strip():
            raise ValueError("validator_version must be non-empty and trimmed")
        require_aware_datetime(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.readiness_fingerprint, str):
            raise TypeError("readiness_fingerprint must be a string")
        if not self.readiness_fingerprint or self.readiness_fingerprint != self.readiness_fingerprint.strip():
            raise ValueError("readiness_fingerprint must be non-empty and trimmed")

        blocking_collections = (
            self.missing_required_features,
            self.uncalibrated_features,
            self.insufficient_quality_features,
            self.incompatible_features,
        )
        if self.is_score_ready:
            if any(state.reason_codes for state in self.feature_states):
                raise ValueError(
                    "score-ready result must not contain blocking feature-state reasons"
                )
            if any(blocking_collections):
                raise ValueError(
                    "score-ready result must not contain blocking feature collections"
                )
            if self.reason_codes:
                raise ValueError(
                    "score-ready result must not contain blocking reason codes"
                )
        elif not self.reason_codes:
            raise ValueError(
                "non-ready result must contain at least one blocking reason code"
            )
