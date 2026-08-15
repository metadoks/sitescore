from dataclasses import FrozenInstanceError, MISSING, fields
from datetime import datetime, timezone
import math
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    PersistenceClass,
    ScoreEligibility,
)
from sitescore_data.schemas.common import (
    DataContractVersions,
    MetricValue,
    SourceMetadata,
)


def make_source_metadata() -> SourceMetadata:
    return SourceMetadata(
        source_id="census_acs_2024",
        provider="U.S. Census Bureau",
        dataset="ACS 5-Year",
        dataset_release="2024",
        vintage="2024",
        schema_version="api-v1",
        retrieved_at=datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
        content_hash="sha256:0123456789abcdef",
        persistence_class=PersistenceClass.PERSIST,
        data_quality=DataQualityState.FULL,
        license_class="public-domain",
        attribution_required=False,
        source_reference="https://api.census.gov/data/2024/acs/acs5",
    )


def make_metric(**overrides: object) -> MetricValue:
    values: dict[str, object] = {
        "value": 10.0,
        "unit": "count",
        "availability": AvailabilityState.AVAILABLE,
        "data_quality": DataQualityState.FULL,
        "score_eligibility": ScoreEligibility.ELIGIBLE,
        "calibration_state": CalibrationState.CALIBRATED,
        "is_estimate": False,
        "is_proxy": False,
        "source_refs": ("census_acs_2024",),
        "method_version": "metric-v1",
        "reason_codes": (),
    }
    values.update(overrides)
    return MetricValue(**values)  # type: ignore[arg-type]


def test_available_none_rejected() -> None:
    with pytest.raises(ValueError):
        make_metric(value=None)


@pytest.mark.parametrize(
    "availability,quality",
    [
        (AvailabilityState.MISSING, DataQualityState.MISSING),
        (AvailabilityState.UNAVAILABLE, DataQualityState.MISSING),
        (AvailabilityState.UNKNOWN, DataQualityState.DEGRADED),
        (AvailabilityState.NOT_APPLICABLE, DataQualityState.NOT_APPLICABLE),
    ],
)
def test_nonavailable_numeric_rejected(
    availability: AvailabilityState,
    quality: DataQualityState,
) -> None:
    with pytest.raises(ValueError):
        make_metric(
            value=5,
            availability=availability,
            data_quality=quality,
        )


def test_available_zero_is_valid() -> None:
    metric = make_metric(value=0)
    assert metric.value == 0
    assert metric.availability is AvailabilityState.AVAILABLE


@pytest.mark.parametrize(
    "quality",
    [DataQualityState.FULL, DataQualityState.DEGRADED],
)
def test_available_full_or_degraded_is_valid(quality: DataQualityState) -> None:
    metric = make_metric(data_quality=quality)
    assert metric.data_quality is quality


def test_missing_full_rejected() -> None:
    with pytest.raises(ValueError):
        make_metric(
            value=None,
            availability=AvailabilityState.MISSING,
            data_quality=DataQualityState.FULL,
        )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_metric_value_rejects_nonfinite_numbers(value: float) -> None:
    with pytest.raises(ValueError):
        make_metric(value=value)


def test_metric_value_rejects_bool_as_numeric_value() -> None:
    with pytest.raises(TypeError):
        make_metric(value=True)


def test_unknown_none_with_degraded_or_missing_quality_is_valid() -> None:
    for quality in (DataQualityState.DEGRADED, DataQualityState.MISSING):
        metric = make_metric(
            value=None,
            availability=AvailabilityState.UNKNOWN,
            data_quality=quality,
            score_eligibility=ScoreEligibility.DIAGNOSTIC_ONLY,
            calibration_state=CalibrationState.UNCALIBRATED,
        )
        assert metric.value is None


def test_source_metadata_requires_aware_datetime() -> None:
    source = make_source_metadata()
    values = {
        field.name: getattr(source, field.name)
        for field in fields(SourceMetadata)
    }
    values["retrieved_at"] = datetime(2026, 8, 12, 12, 0)
    with pytest.raises(ValueError):
        SourceMetadata(**values)


def test_source_metadata_has_explicit_provenance_fields() -> None:
    field_names = {field.name for field in fields(SourceMetadata)}
    assert {
        "source_id",
        "provider",
        "dataset",
        "dataset_release",
        "vintage",
        "schema_version",
        "retrieved_at",
        "content_hash",
        "persistence_class",
        "data_quality",
        "license_class",
        "attribution_required",
        "source_reference",
    } <= field_names


def test_data_contract_versions_current_matches_foundation_constants() -> None:
    current = DataContractVersions.current()
    assert current.package_version == "0.1.0"
    assert current.data_schema_version == "1.0"
    assert current.benchmark_schema_version == "1.0"
    assert current.data_feature_contract_version == "1.0"
    assert current.readiness_contract_version == "1.0"
    assert current.data_serialization_version == "1.0"


def test_common_schemas_are_immutable() -> None:
    source = make_source_metadata()
    metric = make_metric()
    versions = DataContractVersions.current()

    with pytest.raises(FrozenInstanceError):
        source.provider = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        metric.value = 11  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        versions.package_version = "changed"  # type: ignore[misc]


def test_common_schemas_have_no_mutable_collection_field_types() -> None:
    mutable_origins = {list, dict, set}

    def contains_mutable(annotation: object) -> bool:
        origin = get_origin(annotation)
        if origin in mutable_origins:
            return True
        return any(contains_mutable(arg) for arg in get_args(annotation))

    for schema in (SourceMetadata, DataContractVersions, MetricValue):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not contains_mutable(hints[field.name])


def test_common_timestamp_fields_have_no_implicit_defaults() -> None:
    source_retrieved = next(
        field for field in fields(SourceMetadata) if field.name == "retrieved_at"
    )
    assert source_retrieved.default is MISSING
    assert source_retrieved.default_factory is MISSING


def test_not_applicable_requires_all_not_applicable_axes() -> None:
    metric = make_metric(
        value=None,
        availability=AvailabilityState.NOT_APPLICABLE,
        data_quality=DataQualityState.NOT_APPLICABLE,
        score_eligibility=ScoreEligibility.NOT_APPLICABLE,
        calibration_state=CalibrationState.NOT_APPLICABLE,
        source_refs=(),
    )
    assert metric.value is None

    with pytest.raises(ValueError):
        make_metric(
            value=None,
            availability=AvailabilityState.NOT_APPLICABLE,
            data_quality=DataQualityState.NOT_APPLICABLE,
            score_eligibility=ScoreEligibility.ELIGIBLE,
            calibration_state=CalibrationState.NOT_APPLICABLE,
            source_refs=(),
        )

    with pytest.raises(ValueError):
        make_metric(
            value=None,
            availability=AvailabilityState.NOT_APPLICABLE,
            data_quality=DataQualityState.NOT_APPLICABLE,
            score_eligibility=ScoreEligibility.NOT_APPLICABLE,
            calibration_state=CalibrationState.CALIBRATED,
            source_refs=(),
        )


@pytest.mark.parametrize(
    "availability,quality",
    [
        (AvailabilityState.MISSING, DataQualityState.MISSING),
        (AvailabilityState.UNAVAILABLE, DataQualityState.MISSING),
        (AvailabilityState.UNKNOWN, DataQualityState.DEGRADED),
    ],
)
def test_nonavailable_metric_cannot_be_score_eligible(
    availability: AvailabilityState,
    quality: DataQualityState,
) -> None:
    with pytest.raises(ValueError):
        make_metric(
            value=None,
            availability=availability,
            data_quality=quality,
            score_eligibility=ScoreEligibility.ELIGIBLE,
        )


def test_missing_or_unavailable_calibration_state_remains_policy_independent() -> None:
    for availability in (
        AvailabilityState.MISSING,
        AvailabilityState.UNAVAILABLE,
    ):
        metric = make_metric(
            value=None,
            availability=availability,
            data_quality=DataQualityState.MISSING,
            score_eligibility=ScoreEligibility.INELIGIBLE,
            calibration_state=CalibrationState.CALIBRATED,
            source_refs=(),
        )
        assert metric.calibration_state is CalibrationState.CALIBRATED


def test_available_metric_requires_provenance() -> None:
    with pytest.raises(ValueError):
        make_metric(source_refs=())


def test_not_applicable_metric_does_not_require_fake_provenance() -> None:
    metric = make_metric(
        value=None,
        availability=AvailabilityState.NOT_APPLICABLE,
        data_quality=DataQualityState.NOT_APPLICABLE,
        score_eligibility=ScoreEligibility.NOT_APPLICABLE,
        calibration_state=CalibrationState.NOT_APPLICABLE,
        source_refs=(),
    )
    assert metric.source_refs == ()
