from sitescore.analyze import analyze
from sitescore.schemas.metadata import current_model_versions
from sitescore.version import (
    CANONICAL_SCHEMA_VERSION,
    CONFIDENCE_MODEL_VERSION,
    DECISION_MODEL_VERSION,
    FEATURE_SCHEMA_VERSION,
    FINANCIAL_MODEL_VERSION,
    PACKAGE_VERSION,
    SCORING_MODEL_VERSION,
)

from tests.unit.test_analyze import make_input


def test_current_model_versions():
    versions = current_model_versions()

    assert versions.package_version == PACKAGE_VERSION

    assert (
        versions.canonical_schema_version
        == CANONICAL_SCHEMA_VERSION
    )

    assert (
        versions.feature_schema_version
        == FEATURE_SCHEMA_VERSION
    )

    assert (
        versions.scoring_model_version
        == SCORING_MODEL_VERSION
    )

    assert (
        versions.financial_model_version
        == FINANCIAL_MODEL_VERSION
    )

    assert (
        versions.decision_model_version
        == DECISION_MODEL_VERSION
    )

    assert (
        versions.confidence_model_version
        == CONFIDENCE_MODEL_VERSION
    )


def test_fingerprint_is_deterministic():
    data = make_input()

    first = analyze(data)
    second = analyze(data)

    assert (
        first.analysis_fingerprint
        == second.analysis_fingerprint
    )


def test_fingerprint_is_sha256():
    result = analyze(make_input())

    assert len(result.analysis_fingerprint) == 64

    int(
        result.analysis_fingerprint,
        16,
    )


def test_canonical_result_serializes():
    result = analyze(make_input())

    payload = result.to_dict()

    assert isinstance(payload, dict)

    assert "analysis_fingerprint" in payload
    assert "model_versions" in payload
    assert "location" in payload
    assert "financial" in payload
    assert "decision" in payload
    assert "confidence" in payload