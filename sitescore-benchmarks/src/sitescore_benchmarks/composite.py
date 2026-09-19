from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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

_REQUIRED_COMPONENTS_V1 = (
    RoadParkingComponentKind.ROAD_REACHABLE_AREA,
    RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY,
    RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH,
)


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
    """Production-facing prerequisite status/lineage declaration.

    No approved canonical road/parking component-normalization path exists yet.
    Therefore production callers may only represent non-AVAILABLE prerequisite
    states and may never attach a detached numeric score. Synthetic AVAILABLE
    components used to test future composition math live only in tests.
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
            raise ValueError(
                "no canonical approved road/parking component-normalization path exists; "
                "production callers cannot self-assert AVAILABLE components"
            )
        if self.score is not None:
            raise ValueError("production road/parking prerequisite declarations cannot carry numeric scores")

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "component_kind": self.component_kind.value,
            "metric_key": self.metric_key,
            "normalization_lineage_id": self.normalization_lineage_id,
            "state": self.state.value,
            "score": None,
        })


@dataclass(frozen=True, slots=True)
class RoadParkingCompositePolicy:
    """Production policy declaration, not an approval authority.

    The frozen architecture contains no empirically approved COMB-005 policy.
    Consequently this production constructor rejects APPROVED state and any
    executable weight vector. A future approval must arrive through a separately
    frozen canonical authority/registry contract rather than caller assertion.
    """

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
        if self.approval_state is RoadParkingPolicyApprovalState.APPROVED:
            raise ValueError(
                "no approved empirical COMB-005 production authority exists; "
                "caller-created APPROVED policies are forbidden"
            )
        if self.weights:
            raise ValueError("unapproved production COMB-005 policy must not carry weights")
        if self.composition_method != "UNRESOLVED":
            raise ValueError("unapproved production COMB-005 composition method must remain unresolved")

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "approval_state": self.approval_state.value,
            "required_components": tuple(component.value for component in self.required_components),
            "required_metric_keys": tuple(_COMPONENT_METRIC_KEYS[component] for component in self.required_components),
            "weights": (),
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

# There is deliberately no executable/approved V1 policy object.
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1: tuple[RoadParkingCompositePolicy, ...] = ()


@dataclass(frozen=True, slots=True)
class RoadParkingCompositeResult:
    """Derived production result for the current unapproved canonical policy.

    Callers provide only actual production policy/component declarations. State,
    reasons and score are derived properties; they cannot be asserted through the
    constructor. Since no approved canonical policy exists, production AVAILABLE
    is constructively impossible in checkpoint 3.4-7.
    """

    policy: RoadParkingCompositePolicy
    components: tuple[RoadParkingComponentArtifact, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.policy, RoadParkingCompositePolicy):
            raise TypeError("policy must be RoadParkingCompositePolicy")
        if any(not isinstance(component, RoadParkingComponentArtifact) for component in self.components):
            raise TypeError("components must be RoadParkingComponentArtifact instances")
        if self.policy.approval_state is not RoadParkingPolicyApprovalState.NOT_APPROVED:
            raise ValueError("production result requires current canonical unapproved policy semantics")

    @property
    def state(self) -> RoadParkingCompositeState:
        return RoadParkingCompositeState.POLICY_NOT_APPROVED

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return ("comb005_policy_not_approved",)

    @property
    def score(self) -> None:
        return None

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
            "score": None,
        })


def evaluate_road_parking_composite(
    components: tuple[RoadParkingComponentArtifact, ...] = (),
) -> RoadParkingCompositeResult:
    """Canonical V1 production gate.

    No caller policy, weights, approval flag, state, score or AVAILABLE component
    can be supplied as production authority. Until an empirically approved policy
    and component-normalization authorities are separately frozen, the only
    canonical result is POLICY_NOT_APPROVED with score=None.
    """
    return RoadParkingCompositeResult(COMB005_V1_POLICY, components)


__all__ = [
    "ROAD_PARKING_OUTPUT_FEATURE_KEY",
    "ROAD_PARKING_OUTPUT_UNIT",
    "RoadParkingComponentKind",
    "RoadParkingComponentState",
    "RoadParkingPolicyApprovalState",
    "RoadParkingCompositeState",
    "RoadParkingComponentArtifact",
    "RoadParkingCompositePolicy",
    "RoadParkingCompositeResult",
    "COMB005_V1_POLICY",
    "APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1",
    "evaluate_road_parking_composite",
]
