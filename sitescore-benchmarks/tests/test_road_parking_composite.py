from dataclasses import dataclass
import inspect
import math

import pytest

import sitescore_benchmarks as public_api
from sitescore_benchmarks import (
    APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1,
    COMB005_V1_POLICY,
    ROAD_PARKING_OUTPUT_FEATURE_KEY,
    RoadParkingComponentArtifact,
    RoadParkingComponentKind,
    RoadParkingComponentState,
    RoadParkingCompositePolicy,
    RoadParkingCompositeResult,
    RoadParkingCompositeState,
    RoadParkingPolicyApprovalState,
    evaluate_road_parking_composite,
    feature_normalization_policy,
    semantic_hash,
)


_METRIC_KEYS = {
    RoadParkingComponentKind.ROAD_REACHABLE_AREA: "road_reachable_area_km2",
    RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY: "parking_public_offstreet_capacity",
    RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH: "parking_legal_curb_length_m",
}

_REQUIRED_KINDS = tuple(_METRIC_KEYS)


def _production_component(kind, *, state=RoadParkingComponentState.UNRESOLVED, lineage="lineage-v1"):
    return RoadParkingComponentArtifact(
        component_kind=kind,
        metric_key=_METRIC_KEYS[kind],
        normalization_lineage_id=f"{lineage}:{kind.value}",
        state=state,
        score=None,
    )


@dataclass(frozen=True)
class _SyntheticComponent:
    kind: RoadParkingComponentKind
    score: float | None
    state: RoadParkingComponentState
    lineage: str

    @property
    def identity_id(self):
        return semantic_hash({
            "test_only": True,
            "kind": self.kind.value,
            "metric_key": _METRIC_KEYS[self.kind],
            "score": self.score,
            "state": self.state.value,
            "lineage": self.lineage,
        })


@dataclass(frozen=True)
class _SyntheticPolicy:
    weights: tuple[float, float, float]
    version: str = "test-only-v1"

    def __post_init__(self):
        if any(not math.isfinite(weight) or weight < 0.0 for weight in self.weights):
            raise ValueError("synthetic weights must be finite and nonnegative")
        if sum(self.weights) != 1.0:
            raise ValueError("synthetic weights must sum exactly to 1")

    @property
    def identity_id(self):
        return semantic_hash({
            "test_only": True,
            "version": self.version,
            "weights": self.weights,
            "required_kinds": tuple(kind.value for kind in _REQUIRED_KINDS),
            "missing_behavior": "REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION",
        })


@dataclass(frozen=True)
class _SyntheticResult:
    policy: _SyntheticPolicy
    components: tuple[_SyntheticComponent, ...]
    state: RoadParkingCompositeState
    reasons: tuple[str, ...]
    score: float | None

    @property
    def identity_id(self):
        return semantic_hash({
            "test_only": True,
            "policy": self.policy.identity_id,
            "components": tuple(sorted(
                ((component.kind.value, component.identity_id) for component in self.components),
                key=lambda item: item[0],
            )),
            "state": self.state.value,
            "reasons": self.reasons,
            "score": self.score,
        })


def _synthetic_component(kind, score=50.0, *, state=RoadParkingComponentState.AVAILABLE, lineage="lineage-v1"):
    return _SyntheticComponent(
        kind=kind,
        score=score if state is RoadParkingComponentState.AVAILABLE else None,
        state=state,
        lineage=f"{lineage}:{kind.value}",
    )


def _synthetic_components():
    return (
        _synthetic_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 20.0),
        _synthetic_component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 60.0),
        _synthetic_component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH, 80.0),
    )


def _synthetic_compose(policy, components):
    by_kind = {component.kind: component for component in components}
    if len(by_kind) != len(components):
        return _SyntheticResult(policy, components, RoadParkingCompositeState.INPUT_INCOMPATIBLE, ("duplicate_component_kind",), None)
    missing = [kind for kind in _REQUIRED_KINDS if kind not in by_kind]
    if missing:
        return _SyntheticResult(
            policy,
            components,
            RoadParkingCompositeState.INPUT_NOT_AVAILABLE,
            tuple(f"missing_component:{kind.value}" for kind in missing),
            None,
        )
    for kind in _REQUIRED_KINDS:
        component = by_kind[kind]
        if component.state in (RoadParkingComponentState.UNAVAILABLE, RoadParkingComponentState.UNRESOLVED):
            return _SyntheticResult(policy, components, RoadParkingCompositeState.INPUT_NOT_AVAILABLE, (f"component_not_available:{kind.value}:{component.state.value}",), None)
        if component.state is RoadParkingComponentState.INELIGIBLE:
            return _SyntheticResult(policy, components, RoadParkingCompositeState.INPUT_NOT_ELIGIBLE, (f"component_not_eligible:{kind.value}",), None)
        if component.state is RoadParkingComponentState.UNCALIBRATED:
            return _SyntheticResult(policy, components, RoadParkingCompositeState.INPUT_NOT_CALIBRATED, (f"component_not_calibrated:{kind.value}",), None)
        if component.state is RoadParkingComponentState.INCOMPATIBLE:
            return _SyntheticResult(policy, components, RoadParkingCompositeState.INPUT_INCOMPATIBLE, (f"component_incompatible:{kind.value}",), None)
    values = tuple(float(by_kind[kind].score) for kind in _REQUIRED_KINDS)
    score = sum(weight * value for weight, value in zip(policy.weights, values, strict=True))
    if not math.isfinite(score) or not 0.0 <= score <= 100.0:
        raise ValueError("synthetic COMB-005 score out of bounds")
    return _SyntheticResult(policy, components, RoadParkingCompositeState.AVAILABLE, (), score)


def test_comb001_canonical_no_approved_policy_cannot_emit_score():
    result = evaluate_road_parking_composite()
    assert result.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert result.score is None
    assert result.output_feature_key == ROAD_PARKING_OUTPUT_FEATURE_KEY
    assert result.reason_codes == ("comb005_policy_not_approved",)


def test_comb002_no_implicit_50_50_or_any_approved_canonical_weight_set():
    assert COMB005_V1_POLICY.approval_state is RoadParkingPolicyApprovalState.NOT_APPROVED
    assert COMB005_V1_POLICY.weights == ()
    assert COMB005_V1_POLICY.composition_method == "UNRESOLVED"
    assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()


def test_comb003_road_only_substitution_forbidden():
    canonical = evaluate_road_parking_composite((
        _production_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA),
    ))
    assert canonical.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert canonical.score is None

    synthetic = _synthetic_compose(
        _SyntheticPolicy((0.2, 0.3, 0.5)),
        (_synthetic_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 90.0),),
    )
    assert synthetic.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert synthetic.score is None


def test_comb004_parking_only_substitution_forbidden():
    synthetic = _synthetic_compose(
        _SyntheticPolicy((0.2, 0.3, 0.5)),
        (
            _synthetic_component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 90.0),
            _synthetic_component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH, 90.0),
        ),
    )
    assert synthetic.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert synthetic.score is None


def test_comb005_missing_side_never_becomes_neutral_50():
    synthetic = _synthetic_compose(
        _SyntheticPolicy((0.2, 0.3, 0.5)),
        (
            _synthetic_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 20.0),
            _synthetic_component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 60.0),
        ),
    )
    assert synthetic.score is None
    assert synthetic.score != 50.0


def test_comb006_missing_side_is_not_renormalized_to_remaining_weights():
    synthetic = _synthetic_compose(
        _SyntheticPolicy((0.2, 0.3, 0.5)),
        (
            _synthetic_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 100.0),
            _synthetic_component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 100.0),
        ),
    )
    assert synthetic.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert synthetic.score is None


def test_comb007_unresolved_road_remains_unresolved():
    production = _production_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA)
    assert production.state is RoadParkingComponentState.UNRESOLVED
    assert production.score is None
    synthetic = _synthetic_compose(
        _SyntheticPolicy((0.2, 0.3, 0.5)),
        (
            _synthetic_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, state=RoadParkingComponentState.UNRESOLVED),
            _synthetic_component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 60.0),
            _synthetic_component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH, 80.0),
        ),
    )
    assert synthetic.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert synthetic.score is None


def test_comb008_parking_capacity_and_curb_length_remain_distinct():
    offstreet = _production_component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY)
    curb = _production_component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH)
    assert offstreet.metric_key != curb.metric_key
    assert offstreet.component_kind is not curb.component_kind
    assert offstreet.identity_id != curb.identity_id
    with pytest.raises(ValueError):
        RoadParkingComponentArtifact(
            component_kind=RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY,
            metric_key="parking_legal_curb_length_m",
            normalization_lineage_id="wrong",
            state=RoadParkingComponentState.UNRESOLVED,
        )


def test_comb009_no_downstream_feature_slot_invention():
    public_names = set(dir(public_api))
    assert "road_access_score" not in public_names
    assert "parking_access_score" not in public_names
    assert "curb_access_score" not in public_names
    assert ROAD_PARKING_OUTPUT_FEATURE_KEY == "road_parking_access_score"


def test_comb010_canonical_api_has_no_caller_self_authorization_arguments():
    parameters = inspect.signature(evaluate_road_parking_composite).parameters
    assert tuple(parameters) == ("components",)
    for forbidden in ("approved", "approval_state", "weights", "policy", "score", "state"):
        assert forbidden not in parameters


def test_comb011_synthetic_identity_changes_with_test_only_weights():
    first = _synthetic_compose(_SyntheticPolicy((0.2, 0.3, 0.5)), _synthetic_components())
    second = _synthetic_compose(_SyntheticPolicy((0.3, 0.2, 0.5)), _synthetic_components())
    assert first.state is RoadParkingCompositeState.AVAILABLE
    assert second.state is RoadParkingCompositeState.AVAILABLE
    assert first.identity_id != second.identity_id


def test_comb012_synthetic_identity_changes_with_component_lineage():
    first_components = _synthetic_components()
    second_components = (
        _synthetic_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 20.0, lineage="lineage-v2"),
        first_components[1],
        first_components[2],
    )
    policy = _SyntheticPolicy((0.2, 0.3, 0.5))
    first = _synthetic_compose(policy, first_components)
    second = _synthetic_compose(policy, second_components)
    assert first.score == second.score
    assert first.identity_id != second.identity_id


def test_comb013_synthetic_available_result_is_bounded_without_clamping():
    result = _synthetic_compose(_SyntheticPolicy((0.2, 0.3, 0.5)), _synthetic_components())
    assert result.state is RoadParkingCompositeState.AVAILABLE
    assert result.score == pytest.approx(62.0)
    assert 0.0 <= result.score <= 100.0


def test_comb014_no_later_scope_surface_is_introduced():
    for forbidden in (
        "ScoringReadiness",
        "RealDataPipelineResult",
        "CategoryScores",
        "LocationScore",
        "analyze",
    ):
        assert not hasattr(public_api, forbidden)


def test_comb015_canonical_production_state_remains_unavailable_after_test_helpers_exist():
    assert _synthetic_compose(
        _SyntheticPolicy((0.2, 0.3, 0.5)), _synthetic_components()
    ).state is RoadParkingCompositeState.AVAILABLE
    canonical = evaluate_road_parking_composite()
    assert canonical.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert canonical.score is None
    assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()


def test_comb_h001_public_policy_constructor_rejects_caller_approved_weights():
    assert hasattr(public_api, "RoadParkingCompositePolicy")
    with pytest.raises(ValueError, match="caller-created APPROVED policies are forbidden"):
        public_api.RoadParkingCompositePolicy(
            policy_id="caller-spoof",
            policy_version="1.0",
            approval_state=public_api.RoadParkingPolicyApprovalState.APPROVED,
            required_components=_REQUIRED_KINDS,
            weights=(0.2, 0.3, 0.5),
            composition_method="WEIGHTED_LINEAR_SUM_NO_SUBSTITUTION",
            missing_side_behavior="REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION",
        )
    assert public_api.APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()


def test_comb_h002_public_component_constructor_rejects_detached_available_score():
    with pytest.raises(ValueError, match="cannot self-assert AVAILABLE components"):
        public_api.RoadParkingComponentArtifact(
            component_kind=RoadParkingComponentKind.ROAD_REACHABLE_AREA,
            metric_key="road_reachable_area_km2",
            normalization_lineage_id="caller-lineage",
            state=RoadParkingComponentState.AVAILABLE,
            score=99.0,
        )


def test_comb_h002_public_result_constructor_has_no_state_or_score_assertion_fields():
    parameters = inspect.signature(public_api.RoadParkingCompositeResult).parameters
    assert tuple(parameters) == ("policy", "components")
    assert "state" not in parameters
    assert "reason_codes" not in parameters
    assert "score" not in parameters

    result = public_api.RoadParkingCompositeResult(COMB005_V1_POLICY, ())
    assert result.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert result.reason_codes == ("comb005_policy_not_approved",)
    assert result.score is None

    with pytest.raises(TypeError):
        public_api.RoadParkingCompositeResult(
            COMB005_V1_POLICY,
            (),
            state=RoadParkingCompositeState.AVAILABLE,
            score=99.0,
        )


def test_comb_h002_public_api_cannot_make_available_result_with_missing_duplicate_or_nonavailable_inputs():
    unresolved_road = _production_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA)
    duplicate = (unresolved_road, unresolved_road)
    for components in ((), (unresolved_road,), duplicate):
        result = evaluate_road_parking_composite(components)
        assert result.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
        assert result.score is None
        assert result.state is not RoadParkingCompositeState.AVAILABLE


def test_locked_3_4_6_still_rejects_direct_road_and_parking_normalization():
    for metric_key in _METRIC_KEYS.values():
        with pytest.raises(ValueError):
            feature_normalization_policy(metric_key)


def test_production_component_nonavailable_states_never_carry_scores():
    for state in (
        RoadParkingComponentState.UNAVAILABLE,
        RoadParkingComponentState.UNRESOLVED,
        RoadParkingComponentState.INCOMPATIBLE,
        RoadParkingComponentState.INELIGIBLE,
        RoadParkingComponentState.UNCALIBRATED,
    ):
        component = RoadParkingComponentArtifact(
            component_kind=RoadParkingComponentKind.ROAD_REACHABLE_AREA,
            metric_key="road_reachable_area_km2",
            normalization_lineage_id="lineage",
            state=state,
        )
        assert component.score is None
        with pytest.raises(ValueError):
            RoadParkingComponentArtifact(
                component_kind=RoadParkingComponentKind.ROAD_REACHABLE_AREA,
                metric_key="road_reachable_area_km2",
                normalization_lineage_id="lineage",
                state=state,
                score=50.0,
            )


def test_production_component_order_does_not_change_result_identity():
    components = (
        _production_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA),
        _production_component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY),
        _production_component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH),
    )
    forward = evaluate_road_parking_composite(components)
    reverse = evaluate_road_parking_composite(tuple(reversed(components)))
    assert forward.score is None
    assert reverse.score is None
    assert forward.identity_id == reverse.identity_id
