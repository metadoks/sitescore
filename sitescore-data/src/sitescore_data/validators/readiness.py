"""Pure deterministic scoring-readiness validation."""

from __future__ import annotations

from datetime import datetime

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    ScoreEligibility,
)
from sitescore_data.feature_surface import NORMALIZED_FEATURE_NAMES
from sitescore_data.schemas.features import (
    NormalizedLocationFeatures,
    ReadyCategoryScorePayload,
)
from sitescore_data.schemas.readiness import (
    ApprovedFallbackPolicyRef,
    FeatureReadinessPolicy,
    PolicyVersionRef,
    ReadinessCompatibilityInput,
    ScoringFeatureReadiness,
    ScoringReadinessReason,
    ScoringReadinessResult,
)
from sitescore_data.validation import SectorKey, require_aware_datetime



AGE_FEATURE_NAME = "age_target_concentration_score"
AGE_FALLBACK_REASON = "age_affinity_not_calibrated"
V1_AGE_FALLBACK_POLICY_ID = "age_neutral_fallback"
V1_AGE_FALLBACK_POLICY_VERSION = "1.0"


class ScoringReadinessValidator:
    """Validate whether normalized features may proceed to category aggregation.

    The validator is pure: all timestamps, trusted policy-resolution states,
    compatibility identities, approved fallback references, and readiness
    fingerprint references are caller supplied. ``readiness_fingerprint`` is
    preserved as an external identity/reference in this checkpoint; it is not
    content-bound or generated here. The validator does not aggregate category
    values or access external systems.
    """

    def __init__(self, *, validator_version: str) -> None:
        if not isinstance(validator_version, str):
            raise TypeError("validator_version must be a string")
        if not validator_version or validator_version != validator_version.strip():
            raise ValueError("validator_version must be non-empty and trimmed")
        self._validator_version = validator_version

    def validate(
        self,
        *,
        features: NormalizedLocationFeatures,
        feature_policies: tuple[FeatureReadinessPolicy, ...],
        compatibility: ReadinessCompatibilityInput,
        approved_fallback_policies: tuple[ApprovedFallbackPolicyRef, ...],
        evaluated_at: datetime,
        readiness_fingerprint: str,
    ) -> ScoringReadinessResult:
        if not isinstance(features, NormalizedLocationFeatures):
            raise TypeError("features must be NormalizedLocationFeatures")
        if not isinstance(feature_policies, tuple):
            raise TypeError("feature_policies must be a tuple")
        if any(
            not isinstance(policy, FeatureReadinessPolicy)
            for policy in feature_policies
        ):
            raise TypeError(
                "feature_policies must contain FeatureReadinessPolicy values"
            )
        if not isinstance(compatibility, ReadinessCompatibilityInput):
            raise TypeError("compatibility must be a ReadinessCompatibilityInput")
        if not isinstance(approved_fallback_policies, tuple):
            raise TypeError("approved_fallback_policies must be a tuple")
        if any(
            not isinstance(item, ApprovedFallbackPolicyRef)
            for item in approved_fallback_policies
        ):
            raise TypeError(
                "approved_fallback_policies must contain ApprovedFallbackPolicyRef values"
            )
        approval_keys = tuple(
            (item.feature_name, item.policy_id, item.policy_version)
            for item in approved_fallback_policies
        )
        if len(set(approval_keys)) != len(approval_keys):
            raise ValueError("approved_fallback_policies must not contain duplicates")
        if any(
            item.feature_name != AGE_FEATURE_NAME
            for item in approved_fallback_policies
        ):
            raise ValueError(
                "V1 approved fallback policies may target only "
                "age_target_concentration_score"
            )
        approved_fallback_keys = set(approval_keys)

        require_aware_datetime(evaluated_at, field_name="evaluated_at")
        if not isinstance(readiness_fingerprint, str):
            raise TypeError("readiness_fingerprint must be a string")
        if not readiness_fingerprint or readiness_fingerprint != readiness_fingerprint.strip():
            raise ValueError("readiness_fingerprint must be non-empty and trimmed")

        policy_by_feature = {
            policy.feature_name: policy
            for policy in feature_policies
        }
        if len(policy_by_feature) != len(feature_policies):
            raise ValueError("feature_policies feature_name values must be unique")
        if set(policy_by_feature) != set(NORMALIZED_FEATURE_NAMES):
            raise ValueError(
                "feature_policies must cover exactly the frozen V1 normalized feature surface"
            )
        if any(not policy.required for policy in feature_policies):
            raise ValueError(
                "frozen V1 readiness requires all normalized features; "
                "required=False is not a valid canonical V1 policy"
            )

        feature_states: list[ScoringFeatureReadiness] = []
        missing: list[str] = []
        uncalibrated: list[str] = []
        insufficient_quality: list[str] = []
        incompatible: list[str] = []
        global_reasons: list[ScoringReadinessReason] = []

        required_versions: list[PolicyVersionRef] = []
        resolved_versions: list[PolicyVersionRef] = []

        for feature_name in NORMALIZED_FEATURE_NAMES:
            metric = getattr(features, feature_name)
            policy = policy_by_feature[feature_name]
            reasons: list[ScoringReadinessReason] = []

            resolved_policy_version = self._resolved_policy_version(
                feature_name=feature_name,
                features=features,
                policy=policy,
            )

            if policy.required_policy_version is not None:
                required_versions.append(
                    PolicyVersionRef(
                        policy_id=feature_name,
                        version=policy.required_policy_version,
                    )
                )
                if resolved_policy_version is None:
                    reasons.append(ScoringReadinessReason.POLICY_NOT_CONFIGURED)
                elif resolved_policy_version != policy.required_policy_version:
                    reasons.append(ScoringReadinessReason.POLICY_VERSION_MISMATCH)

            if resolved_policy_version is not None:
                resolved_versions.append(
                    PolicyVersionRef(
                        policy_id=feature_name,
                        version=resolved_policy_version,
                    )
                )

            if policy.required:
                if metric.availability is not AvailabilityState.AVAILABLE:
                    reasons.append(ScoringReadinessReason.MISSING_REQUIRED_FEATURE)
                    missing.append(feature_name)

                if metric.data_quality not in {
                    DataQualityState.FULL,
                    DataQualityState.DEGRADED,
                }:
                    reasons.append(ScoringReadinessReason.INSUFFICIENT_DATA_QUALITY)
                    insufficient_quality.append(feature_name)

                if metric.score_eligibility is ScoreEligibility.DIAGNOSTIC_ONLY:
                    reasons.append(ScoringReadinessReason.FEATURE_DIAGNOSTIC_ONLY)
                elif metric.score_eligibility is not ScoreEligibility.ELIGIBLE:
                    reasons.append(ScoringReadinessReason.FEATURE_INELIGIBLE)

                if metric.calibration_state is CalibrationState.UNCALIBRATED:
                    if self._valid_age_fallback(
                        feature_name=feature_name,
                        metric=metric,
                        policy=policy,
                        approved_fallback_keys=approved_fallback_keys,
                    ):
                        pass
                    else:
                        reasons.append(ScoringReadinessReason.FEATURE_UNCALIBRATED)
                        uncalibrated.append(feature_name)
                        if feature_name == AGE_FEATURE_NAME and (
                            policy.fallback_policy_id is not None
                            or policy.fallback_policy_version is not None
                        ):
                            reasons.append(
                                ScoringReadinessReason.AGE_FALLBACK_POLICY_INVALID
                            )

            if feature_name == "competition_opportunity_score" and policy.required:
                competition_reasons = self._competition_compatibility_reasons(
                    features=features,
                    compatibility=compatibility,
                )
                reasons.extend(competition_reasons)
                if competition_reasons:
                    incompatible.append(feature_name)

            if feature_name == "transit_access_score" and policy.required:
                transit_reasons = self._transit_compatibility_reasons(
                    features=features,
                    compatibility=compatibility,
                )
                reasons.extend(transit_reasons)
                if transit_reasons:
                    incompatible.append(feature_name)

            if feature_name == "road_parking_access_score" and policy.required:
                if (
                    metric.availability is not AvailabilityState.AVAILABLE
                    or metric.score_eligibility is not ScoreEligibility.ELIGIBLE
                    or metric.calibration_state is not CalibrationState.CALIBRATED
                    or features.road_parking_composite_policy_version is None
                ):
                    reasons.append(
                        ScoringReadinessReason.ROAD_PARKING_COMPOSITE_UNAVAILABLE
                    )
                    incompatible.append(feature_name)

            reasons = list(dict.fromkeys(reasons))
            global_reasons.extend(reasons)

            feature_states.append(
                ScoringFeatureReadiness(
                    feature_name=feature_name,
                    required=policy.required,
                    availability=metric.availability,
                    data_quality=metric.data_quality,
                    score_eligibility=metric.score_eligibility,
                    calibration_state=metric.calibration_state,
                    required_policy_version=policy.required_policy_version,
                    resolved_policy_version=resolved_policy_version,
                    fallback_policy_id=policy.fallback_policy_id,
                    fallback_policy_version=policy.fallback_policy_version,
                    reason_codes=tuple(reasons),
                )
            )

        global_reasons = list(dict.fromkeys(global_reasons))
        missing = list(dict.fromkeys(missing))
        uncalibrated = list(dict.fromkeys(uncalibrated))
        insufficient_quality = list(dict.fromkeys(insufficient_quality))
        incompatible = list(dict.fromkeys(incompatible))

        is_ready = not global_reasons

        return ScoringReadinessResult(
            is_score_ready=is_ready,
            missing_required_features=tuple(missing),
            uncalibrated_features=tuple(uncalibrated),
            insufficient_quality_features=tuple(insufficient_quality),
            incompatible_features=tuple(incompatible),
            reason_codes=tuple(global_reasons),
            required_policy_versions=tuple(
                sorted(required_versions, key=lambda item: item.policy_id)
            ),
            resolved_policy_versions=tuple(
                sorted(resolved_versions, key=lambda item: item.policy_id)
            ),
            feature_states=tuple(feature_states),
            validator_version=self._validator_version,
            evaluated_at=evaluated_at,
            readiness_fingerprint=readiness_fingerprint,
        )

    @staticmethod
    def _resolved_policy_version(
        *,
        feature_name: str,
        features: NormalizedLocationFeatures,
        policy: FeatureReadinessPolicy,
    ) -> str | None:
        feature_metadata_versions = {
            "competition_opportunity_score": (
                features.competition_normalization_policy_version
            ),
            "transit_access_score": (
                features.transit_normalization_policy_version
            ),
            "road_parking_access_score": (
                features.road_parking_composite_policy_version
            ),
        }
        if feature_name in feature_metadata_versions:
            actual = feature_metadata_versions[feature_name]
            if (
                policy.resolved_policy_version is not None
                and actual is not None
                and policy.resolved_policy_version != actual
            ):
                return actual
            return actual
        return policy.resolved_policy_version

    @staticmethod
    def _valid_age_fallback(
        *,
        feature_name,
        metric,
        policy,
        approved_fallback_keys,
    ) -> bool:
        if feature_name != AGE_FEATURE_NAME:
            return False
        if policy.fallback_policy_id is None or policy.fallback_policy_version is None:
            return False
        approval_key = (
            feature_name,
            policy.fallback_policy_id,
            policy.fallback_policy_version,
        )
        if approval_key not in approved_fallback_keys:
            return False
        if approval_key != (
            AGE_FEATURE_NAME,
            V1_AGE_FALLBACK_POLICY_ID,
            V1_AGE_FALLBACK_POLICY_VERSION,
        ):
            return False
        return (
            metric.value == 50
            and metric.availability is AvailabilityState.AVAILABLE
            and metric.calibration_state is CalibrationState.UNCALIBRATED
            and metric.score_eligibility is ScoreEligibility.ELIGIBLE
            and metric.is_proxy is True
            and AGE_FALLBACK_REASON in metric.reason_codes
        )

    @staticmethod
    def _competition_compatibility_reasons(
        *,
        features: NormalizedLocationFeatures,
        compatibility: ReadinessCompatibilityInput,
    ) -> tuple[ScoringReadinessReason, ...]:
        if (
            features.competition_benchmark_ref is None
            or features.competition_measurement_definition_id is None
            or compatibility.competition_benchmark_measurement_definition_id is None
        ):
            return (ScoringReadinessReason.COMPETITION_MEASUREMENT_MISMATCH,)
        if (
            features.competition_measurement_definition_id
            != compatibility.competition_benchmark_measurement_definition_id
        ):
            return (ScoringReadinessReason.COMPETITION_MEASUREMENT_MISMATCH,)
        return ()

    @staticmethod
    def _transit_compatibility_reasons(
        *,
        features: NormalizedLocationFeatures,
        compatibility: ReadinessCompatibilityInput,
    ) -> tuple[ScoringReadinessReason, ...]:
        if (
            features.transit_benchmark_ref is None
            or features.transit_source_bundle_fingerprint is None
            or compatibility.transit_benchmark_source_bundle_fingerprint is None
        ):
            return (ScoringReadinessReason.TRANSIT_SOURCE_BUNDLE_MISMATCH,)
        if (
            features.transit_source_bundle_fingerprint
            != compatibility.transit_benchmark_source_bundle_fingerprint
        ):
            return (ScoringReadinessReason.TRANSIT_SOURCE_BUNDLE_MISMATCH,)
        return ()


def create_ready_category_score_payload(
    *,
    readiness: ScoringReadinessResult,
    sector_key: SectorKey,
    demand: float,
    competition: float,
    accessibility: float,
    economics: float,
    feature_contract_version: str,
    normalization_policy_version: str,
) -> ReadyCategoryScorePayload:
    """Gate precomputed category values behind a successful readiness result.

    This function performs no weighting and no category aggregation.
    """

    if not isinstance(readiness, ScoringReadinessResult):
        raise TypeError("readiness must be a ScoringReadinessResult")
    if readiness.is_score_ready is not True:
        raise ValueError(
            "ReadyCategoryScorePayload requires is_score_ready=True"
        )

    return ReadyCategoryScorePayload(
        sector_key=sector_key,
        demand=demand,
        competition=competition,
        accessibility=accessibility,
        economics=economics,
        readiness_fingerprint=readiness.readiness_fingerprint,
        feature_contract_version=feature_contract_version,
        normalization_policy_version=normalization_policy_version,
    )
