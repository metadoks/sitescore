from dataclasses import dataclass

from sitescore.version import (
    CANONICAL_SCHEMA_VERSION,
    CONFIDENCE_MODEL_VERSION,
    DECISION_MODEL_VERSION,
    FEATURE_SCHEMA_VERSION,
    FINANCIAL_MODEL_VERSION,
    PACKAGE_VERSION,
    SCORING_MODEL_VERSION,
)


@dataclass(frozen=True, slots=True)
class ModelVersions:
    package_version: str
    canonical_schema_version: str
    feature_schema_version: str
    scoring_model_version: str
    financial_model_version: str
    decision_model_version: str
    confidence_model_version: str


def current_model_versions() -> ModelVersions:
    return ModelVersions(
        package_version=PACKAGE_VERSION,
        canonical_schema_version=CANONICAL_SCHEMA_VERSION,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        scoring_model_version=SCORING_MODEL_VERSION,
        financial_model_version=FINANCIAL_MODEL_VERSION,
        decision_model_version=DECISION_MODEL_VERSION,
        confidence_model_version=CONFIDENCE_MODEL_VERSION,
    )