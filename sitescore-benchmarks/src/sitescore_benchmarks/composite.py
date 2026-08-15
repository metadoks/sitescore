from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .hashing import semantic_hash
from .validation import text


ROAD_PARKING_OUTPUT_FEATURE_KEY = "road_parking_access_score"
ROAD_PARKING_OUTPUT_UNIT = "score_0_100"


class RoadParkingComponentKind(str, Enum):
    ROAD_REACHABLE_AREA = "ROAD_REACHABLE_AREA"
    PARKING_PUBLIC_OFFSTREET_CAPACITY = "PARKING_PUBLIC_OFFSTREET_CAPACITY"
    PARKING_LEGAL_CURB_LENGTH = "PARKING_LEGAL_CURB_LENGTH"


_COMPONENT_METRIC_KEYS = {
    RoadParkingComponentKind.ROAD_REACHABLE_AREA: "road_reachable_area_km2",
    RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY: "parking_public_offstreet_capacity",
    RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH: "parking_legal_curb_length_m",
}


class RoadParkingComponentState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNRESOLVED = "UNRESOLVED"
    INCOMPATIBLE = "INCOMPATIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNCALIBRATED = "UNCALIBRATED"


class RoadParkingPolicyApprovalState(str, Enum):
    NOT_APPROVED = "NOT_APPROVED"
    APPROVED = "APPROVED"


class RoadParkingCompositeState(str, Enum):
    POLICY_NOT_APPROVED = "POLICY_NOT_APPROVED"
    INPUT_NOT_AVAILABLE = "INPUT_NOT_AVAILABLE"
    INPUT_NOT_ELIGIBLE = "INPUT_NOT_ELIGIBLE"
    INPUT_NOT_CALIBRATED = "INPUT_NOT_CALIBRATED"
    INPUT_INCOMPATIBLE = "INPUT_INCOMPATIBLE"
    AVAILABLE = "AVAILABLE"


@dataclass(frozen=True, slots=True)
class RoadParkingComponentArtifact:
    """Internal normalized prerequisite artifact, not a downstream feature slot.

    The real-unit road/parking metrics remain distinct upstream.  This artifact only
    represents a future normalized prerequisite with explicit semantic lineage.
    Current canonical production does not construct AVAILABLE instances because
    the required road/parking reductions are not empirically approved.
    """

    component_kind: RoadParkingComponentKind
    metric_key: str
    normalization_lineage_id: str
    state: RoadParkingComponentState
    score: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.component_kind, RoadParkingComponentKind):
            raise TypeError("component_kind must be RoadParkingComponentKind")
        text(self.metric_key, "metric_key")
        text(self.normalization_lineage_id, "normalization_lineage_id")
        if not isinstance(self.state, RoadParkingComponentState):
            raise TypeError("state must be RoadParkingComponentState")
        if self.metric_key != _COMPONENT_METRIC_KEYS[self.component_kind]:
            raise ValueError("component kind and frozen metric key must match")
        if self.state is RoadParkingComponentState.AVAILABLE:
            if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
                raise TypeError("available component score must be numeric")
            score = float(self.score)
            if not math.isfinite(score) or not 0.0 <= score <= 100.0:
                raise ValueError("available component score must be finite and within [0,100]")
        elif self.score is not None:
            raise ValueError("unavailable/unresolved component cannot carry numeric score")

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "component_kind": self.component_kind.value,
            "metric_key": self.metric_key,
            "normalization_lineage_id": self.normalization_lineage_id,
            "state": self.state.value,
            "score": self.score,
        })


_REQUIRED_COMPONENTS_V1 = (
    RoadParkingComponentKind.ROAD_REACHABLE_AREA,
    RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY,
    RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH,
)


@dataclass(frozen=True, slots=True)
class RoadParkingCompositePolicy:
    policy_id: str
    policy_version: str
    approval_state: RoadParkingPolicyApprovalState
    required_components: tuple[RoadParkingComponentKind, ...]
    weights: tuple[float, ...]
    composition_method: str
    missing_side_behavior: str
    output_feature_key: str = ROAD_PARKING_OUTPUT_FEATURE_KEY
    output_unit: str = ROAD_PARKING_OUTPUT_UNIT

    def __post_init__(self) -> None:
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.approval_state, RoadParkingPolicyApprovalState):
            raise TypeError("approval_state must be RoadParkingPolicyApprovalState")
        if self.required_components != _REQUIRED_COMPONENTS_V1:
            raise ValueError("COMB-005 V1 must preserve the three distinct frozen component semantics")
        if self.output_feature_key != ROAD_PARKING_OUTPUT_FEATURE_KEY:
            raise ValueError("COMB-005 output feature key is frozen")
        if self.output_unit != ROAD_PARKING_OUTPUT_UNIT:
            raise ValueError("COMB-005 output unit is frozen")
        if self.missing_side_behavior != "REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION":
            raise ValueError("COMB-005 forbids substitution, neutral fill and renormalization")

        if self.approval_state is RoadParkingPolicyApprovalState.NOT_APPROVED:
            if self.weights:
                raise ValueError("unapproved canonical COMB-005 policy must not carry weights")
            if self.composition_method != "UNRESOLVED":
                raise ValueError("unapproved canonical COMB-005 composition method must remain unresolved")
        else:
            if self.composition_method != "WEIGHTED_LINEAR_SUM_NO_SUBSTITUTION":
                raise ValueError("unsupported controlled COMB-005 composition method")
            if len(self.weights) != len(self.required_components):
                raise ValueError("approved controlled policy must weight every required component")
            if any(isinstance(weight, bool) or not isinstance(weight, (int, float)) for weight in self.weights):
                raise TypeError("weights must be numeric")
            weights = tuple(float(weight) for weight in self.weights)
            if any(not math.isfinite(weight) or weight < 0.0 for weight in weights):
                raise ValueError("weights must be finite and nonnegative")
            if not math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError("controlled policy weights must sum exactly to 1 within structural tolerance")

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "approval_state": self.approval_state.value,
            "required_components": tuple(component.value for component in self.required_components),
            "required_metric_keys": tuple(_COMPONENT_METRIC_KEYS[component] for component in self.required_components),
            "weights": self.weights,
            "composition_method": self.composition_method,
            "missing_side_behavior": self.missing_side_behavior,
            "output_feature_key": self.output_feature_key,
            "output_unit": self.output_unit,
        })


COMB005_V1_POLICY = RoadParkingCompositePolicy(
    policy_id="comb005-road-parking",
    policy_version="UNAPPROVED_V1",
    approval_state=RoadParkingPolicyApprovalState.NOT_APPROVED,
    required_components=_REQUIRED_COMPONENTS_V1,
    weights=(),
    composition_method="UNRESOLVED",
    missing_side_behavior="REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION",
)

# Production registry deliberately contains no approved executable policy.
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1: tuple[RoadParkingCompositePolicy, ...] = ()


def _component_state_result(
    components: tuple[RoadParkingComponentArtifact, ...],
) -> tuple[RoadParkingCompositeState | None, tuple[str, ...]]:
    by_kind = {component.component_kind: component for component in components}
    if len(by_kind) != len(components):
        return RoadParkingCompositeState.INPUT_INCOMPATIBLE, ("duplicate_component_kind",)

    missing = [kind for kind in _REQUIRED_COMPONENTS_V1 if kind not in by_kind]
    if missing:
        return RoadParkingCompositeState.INPUT_NOT_AVAILABLE, tuple(
            f"missing_component:{kind.value}" for kind in missing
        )

    reasons: list[str] = []
    state: RoadParkingCompositeState | None = None
    for kind in _REQUIRED_COMPONENTS_V1:
        component = by_kind[kind]
        if component.state in (RoadParkingComponentState.UNAVAILABLE, RoadParkingComponentState.UNRESOLVED):
            state = state or RoadParkingCompositeState.INPUT_NOT_AVAILABLE
            reasons.append(f"component_not_available:{kind.value}:{component.state.value}")
        elif component.state is RoadParkingComponentState.INELIGIBLE:
            state = state or RoadParkingCompositeState.INPUT_NOT_ELIGIBLE
            reasons.append(f"component_not_eligible:{kind.value}")
        elif component.state is RoadParkingComponentState.UNCALIBRATED:
            state = state or RoadParkingCompositeState.INPUT_NOT_CALIBRATED
            reasons.append(f"component_not_calibrated:{kind.value}")
        elif component.state is RoadParkingComponentState.INCOMPATIBLE:
            state = state or RoadParkingCompositeState.INPUT_INCOMPATIBLE
            reasons.append(f"component_incompatible:{kind.value}")
    return state, tuple(reasons)


@dataclass(frozen=True, slots=True)
class RoadParkingCompositeResult:
    policy: RoadParkingCompositePolicy
    components: tuple[RoadParkingComponentArtifact, ...]
    state: RoadParkingCompositeState
    reason_codes: tuple[str, ...]
    score: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.policy, RoadParkingCompositePolicy):
            raise TypeError("policy must be RoadParkingCompositePolicy")
        if any(not isinstance(component, RoadParkingComponentArtifact) for component in self.components):
            raise TypeError("components must be RoadParkingComponentArtifact instances")
        if not isinstance(self.state, RoadParkingCompositeState):
            raise TypeError("state must be RoadParkingCompositeState")
        if self.state is RoadParkingCompositeState.AVAILABLE:
            if self.policy.approval_state is not RoadParkingPolicyApprovalState.APPROVED:
                raise ValueError("available composite requires an approved actual policy")
            if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
                raise TypeError("available composite score must be numeric")
            score = float(self.score)
            if not math.isfinite(score) or not 0.0 <= score <= 100.0:
                raise ValueError("available composite score must be finite and within [0,100]")
            if self.reason_codes:
                raise ValueError("available composite must not carry failure reasons")
        elif self.score is not None:
            raise ValueError("unavailable/gated composite score must be None")

    @property
    def output_feature_key(self) -> str:
        return ROAD_PARKING_OUTPUT_FEATURE_KEY

    @property
    def unit(self) -> str:
        return ROAD_PARKING_OUTPUT_UNIT

    @property
    def identity_id(self) -> str:
        canonical_components = tuple(sorted(
            ((component.component_kind.value, component.identity_id) for component in self.components),
            key=lambda item: item[0],
        ))
        return semantic_hash({
            "policy_identity_id": self.policy.identity_id,
            "policy_approval_state": self.policy.approval_state.value,
            "components": canonical_components,
            "output_feature_key": self.output_feature_key,
            "unit": self.unit,
            "state": self.state.value,
            "reason_codes": self.reason_codes,
            "score": self.score,
        })


def _compose_with_policy(
    policy: RoadParkingCompositePolicy,
    components: tuple[RoadParkingComponentArtifact, ...],
) -> RoadParkingCompositeResult:
    """Internal controlled composition path; canonical production never accepts caller policy."""
    if policy.approval_state is not RoadParkingPolicyApprovalState.APPROVED:
        return RoadParkingCompositeResult(
            policy,
            components,
            RoadParkingCompositeState.POLICY_NOT_APPROVED,
            ("comb005_policy_not_approved",),
            None,
        )

    input_state, reasons = _component_state_result(components)
    if input_state is not None:
        return RoadParkingCompositeResult(policy, components, input_state, reasons, None)

    by_kind = {component.component_kind: component for component in components}
    values = tuple(float(by_kind[kind].score) for kind in policy.required_components)  # type: ignore[arg-type]
    score = sum(weight * value for weight, value in zip(policy.weights, values, strict=True))
    if not math.isfinite(score) or not 0.0 <= score <= 100.0:
        raise ValueError("COMB-005 composition produced invalid score; clamping is forbidden")
    return RoadParkingCompositeResult(
        policy,
        components,
        RoadParkingCompositeState.AVAILABLE,
        (),
        score,
    )


def evaluate_road_parking_composite(
    components: tuple[RoadParkingComponentArtifact, ...] = (),
) -> RoadParkingCompositeResult:
    """Canonical V1 production gate.

    No caller policy, weights, approval flag or detached score can be supplied.
    Until an empirically approved COMB-005 policy is frozen, production output is
    deterministically unavailable regardless of candidate component availability.
    """
    return _compose_with_policy(COMB005_V1_POLICY, components)
