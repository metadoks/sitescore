from __future__ import annotations

import pytest

from sitescore_providers import (
    AcquisitionResult,
    AcquisitionState,
    PolicyRejection,
    ProviderFailure,
    ProviderFailureKind,
)


def test_success_result(raw_artifact):
    result = AcquisitionResult.success(raw_artifact)
    assert result.state is AcquisitionState.SUCCESS
    assert result.artifact is raw_artifact


def test_provider_failure_result():
    failure = ProviderFailure(
        provider_key="example.provider.v1",
        operation="fetch",
        kind=ProviderFailureKind.RATE_LIMIT,
        reason_code="rate_limited",
        retryable=True,
        status_code=429,
    )
    result = AcquisitionResult.provider_failure(failure)
    assert result.failure is failure


def test_policy_rejection_result():
    rejection = PolicyRejection(policy_id="p", policy_version="v1", reason_code="not_allowed")
    result = AcquisitionResult.policy_rejected(rejection)
    assert result.policy_rejection is rejection


def test_invalid_mixed_acquisition_states_rejected(raw_artifact):
    failure = ProviderFailure(
        provider_key="example.provider.v1",
        operation="fetch",
        kind=ProviderFailureKind.UNAVAILABLE,
        reason_code="down",
        retryable=True,
    )
    with pytest.raises(ValueError):
        AcquisitionResult(
            state=AcquisitionState.SUCCESS,
            artifact=raw_artifact,
            failure=failure,
        )


def test_empty_result_rejected():
    with pytest.raises(ValueError):
        AcquisitionResult(state=AcquisitionState.SUCCESS)
