import inspect

import pytest

import sitescore_benchmarks.composite as composite_module
from sitescore_benchmarks import (
    APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1,
    COMB005_V1_POLICY,
    ROAD_PARKING_OUTPUT_FEATURE_KEY,
    RoadParkingComponentArtifact,
    RoadParkingComponentKind,
    RoadParkingComponentState,
    RoadParkingCompositePolicy,
    RoadParkingCompositeState,
    RoadParkingPolicyApprovalState,
    evaluate_road_parking_composite,
    feature_normalization_policy,
)


def _component(kind, score=50.0, *, state=RoadParkingComponentState.AVAILABLE, lineage="lineage-v1"):
    metric_key = {
        RoadParkingComponentKind.ROAD_REACHABLE_AREA: "road_reachable_area_km2",
        RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY: "parking_public_offstreet_capacity",
        RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH: "parking_legal_curb_length_m",
    }[kind]
    return RoadParkingComponentArtifact(
        component_kind=kind,
        metric_key=metric_key,
        normalization_lineage_id=f"{lineage}:{kind.value}",
        state=state,
        score=score if state is RoadParkingComponentState.AVAILABLE else None,
    )


def _all_components():
    return (
        _component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 20.0),
        _component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 60.0),
        _component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH, 80.0),
    )


def _controlled_policy(weights=(0.2, 0.3, 0.5), *, version="test-only-v1"):
    return RoadParkingCompositePolicy(
        policy_id="test-only-comb005",
        policy_version=version,
        approval_state=RoadParkingPolicyApprovalState.APPROVED,
        required_components=(
            RoadParkingComponentKind.ROAD_REACHABLE_AREA,
            RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY,
            RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH,
        ),
        weights=weights,
        composition_method="WEIGHTED_LINEAR_SUM_NO_SUBSTITUTION",
        missing_side_behavior="REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION",
    )


def test_comb001_canonical_no_approved_policy_cannot_emit_score():
    result = evaluate_road_parking_composite(_all_components())
    assert result.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert result.score is None
    assert result.output_feature_key == ROAD_PARKING_OUTPUT_FEATURE_KEY
    assert result.reason_codes == ("comb005_policy_not_approved",)


def test_comb002_no_implicit_50_50_or_any_approved_canonical_weight_set():
    assert COMB005_V1_POLICY.approval_state is RoadParkingPolicyApprovalState.NOT_APPROVED
    assert COMB005_V1_POLICY.weights == ()
    assert COMB005_V1_POLICY.composition_method == "UNRESOLVED"
    assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()
    assert (0.5, 0.5) not in tuple(policy.weights for policy in APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1)


def test_comb003_road_only_substitution_forbidden():
    result = evaluate_road_parking_composite((
        _component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 90.0),
    ))
    assert result.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert result.score is None

    controlled = composite_module._compose_with_policy(
        _controlled_policy(),
        (_component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 90.0),),
    )
    assert controlled.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert controlled.score is None


def test_comb004_parking_only_substitution_forbidden():
    components = (
        _component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 90.0),
        _component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH, 90.0),
    )
    controlled = composite_module._compose_with_policy(_controlled_policy(), components)
    assert controlled.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert controlled.score is None


def test_comb005_missing_side_never_becomes_neutral_50():
    components = (
        _component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 20.0),
        _component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 60.0),
    )
    result = composite_module._compose_with_policy(_controlled_policy(), components)
    assert result.score is None
    assert 50.0 != result.score


def test_comb006_missing_side_is_not_renormalized_to_remaining_weights():
    components = (
        _component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 100.0),
        _component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 100.0),
    )
    result = composite_module._compose_with_policy(_controlled_policy(), components)
    assert result.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert result.score is None


def test_comb007_unresolved_road_remains_unavailable_even_in_controlled_policy():
    components = (
        _component(
            RoadParkingComponentKind.ROAD_REACHABLE_AREA,
            state=RoadParkingComponentState.UNRESOLVED,
        ),
        _component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 60.0),
        _component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH, 80.0),
    )
    result = composite_module._compose_with_policy(_controlled_policy(), components)
    assert result.state is RoadParkingCompositeState.INPUT_NOT_AVAILABLE
    assert result.score is None
    assert any("ROAD_REACHABLE_AREA:UNRESOLVED" in reason for reason in result.reason_codes)


def test_comb008_parking_capacity_and_curb_length_are_distinct_and_not_interchangeable():
    offstreet = _component(RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY, 40.0)
    curb = _component(RoadParkingComponentKind.PARKING_LEGAL_CURB_LENGTH, 40.0)
    assert offstreet.metric_key != curb.metric_key
    assert offstreet.component_kind is not curb.component_kind
    assert offstreet.identity_id != curb.identity_id
    with pytest.raises(ValueError):
        RoadParkingComponentArtifact(
            component_kind=RoadParkingComponentKind.PARKING_PUBLIC_OFFSTREET_CAPACITY,
            metric_key="parking_legal_curb_length_m",
            normalization_lineage_id="wrong",
            state=RoadParkingComponentState.AVAILABLE,
            score=40.0,
        )


def test_comb009_no_downstream_feature_slot_invention():
    public_names = set(dir(__import__("sitescore_benchmarks")))
    assert "road_access_score" not in public_names
    assert "parking_access_score" not in public_names
    assert "curb_access_score" not in public_names
    assert ROAD_PARKING_OUTPUT_FEATURE_KEY == "road_parking_access_score"


def test_comb010_canonical_api_has_no_caller_self_authorization_arguments():
    parameters = inspect.signature(evaluate_road_parking_composite).parameters
    assert tuple(parameters) == ("components",)
    for forbidden in ("approved", "approval_state", "weights", "policy", "score"):
        assert forbidden not in parameters


def test_comb011_identity_changes_with_controlled_policy_weights():
    result_a = composite_module._compose_with_policy(_controlled_policy((0.2, 0.3, 0.5)), _all_components())
    result_b = composite_module._compose_with_policy(_controlled_policy((0.3, 0.2, 0.5)), _all_components())
    assert result_a.state is RoadParkingCompositeState.AVAILABLE
    assert result_b.state is RoadParkingCompositeState.AVAILABLE
    assert result_a.policy.identity_id != result_b.policy.identity_id
    assert result_a.identity_id != result_b.identity_id


def test_comb012_identity_changes_with_component_lineage():
    first = _all_components()
    second = (
        _component(RoadParkingComponentKind.ROAD_REACHABLE_AREA, 20.0, lineage="lineage-v2"),
        first[1],
        first[2],
    )
    result_a = composite_module._compose_with_policy(_controlled_policy(), first)
    result_b = composite_module._compose_with_policy(_controlled_policy(), second)
    assert result_a.score == result_b.score
    assert result_a.identity_id != result_b.identity_id


def test_comb013_controlled_available_result_is_bounded_without_clamping():
    result = composite_module._compose_with_policy(_controlled_policy(), _all_components())
    assert result.state is RoadParkingCompositeState.AVAILABLE
    assert result.score == pytest.approx(62.0)
    assert 0.0 <= result.score <= 100.0


def test_comb014_no_later_scope_surface_is_introduced():
    package = __import__("sitescore_benchmarks")
    for forbidden in (
        "ScoringReadiness",
        "RealDataPipelineResult",
        "CategoryScores",
        "LocationScore",
        "analyze",
    ):
        assert not hasattr(package, forbidden)


def test_comb015_canonical_production_state_remains_unavailable_after_generic_helpers():
    controlled = composite_module._compose_with_policy(_controlled_policy(), _all_components())
    assert controlled.state is RoadParkingCompositeState.AVAILABLE
    canonical = evaluate_road_parking_composite(_all_components())
    assert canonical.state is RoadParkingCompositeState.POLICY_NOT_APPROVED
    assert canonical.score is None
    assert APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 == ()


def test_locked_3_4_6_still_rejects_direct_road_and_parking_normalization():
    for metric_key in (
        "road_reachable_area_km2",
        "parking_public_offstreet_capacity",
        "parking_legal_curb_length_m",
    ):
        with pytest.raises(ValueError):
            feature_normalization_policy(metric_key)


def test_component_nonavailable_states_never_carry_scores():
    for state in (
        RoadParkingComponentState.UNAVAILABLE,
        RoadParkingComponentState.UNRESOLVED,
        RoadParkingComponentState.INCOMPATIBLE,
        RoadParkingComponentState.INELIGIBLE,
        RoadParkingComponentState.UNCALIBRATED,
    ):
        with pytest.raises(ValueError):
            RoadParkingComponentArtifact(
                component_kind=RoadParkingComponentKind.ROAD_REACHABLE_AREA,
                metric_key="road_reachable_area_km2",
                normalization_lineage_id="lineage",
                state=state,
                score=50.0,
            )


def test_component_order_does_not_change_result_identity():
    components = _all_components()
    policy = _controlled_policy()
    forward = composite_module._compose_with_policy(policy, components)
    reverse = composite_module._compose_with_policy(policy, tuple(reversed(components)))
    assert forward.score == reverse.score
    assert forward.identity_id == reverse.identity_id
