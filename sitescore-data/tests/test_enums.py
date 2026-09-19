from enum import StrEnum
import importlib
import pkgutil

from sitescore_data.enums import (
    AvailabilityState,
    BenchmarkPopulationType,
    CalibrationState,
    DataQualityState,
    EligibilityState,
    GeographyType,
    PersistenceClass,
    PipelineStatus,
    ScoreEligibility,
    SpatialRepresentation,
    ValidityState,
)
from sitescore_data.schemas.parking import ParkingAccessClass, ParkingMode
from sitescore_data.schemas.pipeline import PipelineReason
from sitescore_data.schemas.readiness import ScoringReadinessReason
from sitescore_data.schemas.road import RoadOriginQuality


EXPECTED_ENUM_VALUES = {
    AvailabilityState: {
        "AVAILABLE": "available",
        "MISSING": "missing",
        "UNAVAILABLE": "unavailable",
        "UNKNOWN": "unknown",
        "NOT_APPLICABLE": "not_applicable",
    },
    DataQualityState: {
        "FULL": "full",
        "DEGRADED": "degraded",
        "MISSING": "missing",
        "NOT_APPLICABLE": "not_applicable",
    },
    ScoreEligibility: {
        "ELIGIBLE": "eligible",
        "DIAGNOSTIC_ONLY": "diagnostic_only",
        "INELIGIBLE": "ineligible",
        "NOT_APPLICABLE": "not_applicable",
    },
    CalibrationState: {
        "CALIBRATED": "calibrated",
        "UNCALIBRATED": "uncalibrated",
        "NOT_APPLICABLE": "not_applicable",
    },
    PipelineStatus: {
        "SCORE_READY": "score_ready",
        "NOT_SCORE_READY": "not_score_ready",
        "PIPELINE_ERROR": "pipeline_error",
    },
    GeographyType: {
        "COUNTRY": "country",
        "STATE": "state",
        "COUNTY": "county",
        "CBSA": "cbsa",
        "METROPOLITAN_DIVISION": "metropolitan_division",
        "CSA": "csa",
        "TRACT": "tract",
        "BLOCK_GROUP": "block_group",
        "ZCTA": "zcta",
        "CUSTOM": "custom",
        "UNKNOWN": "unknown",
    },
    EligibilityState: {
        "ELIGIBLE": "eligible",
        "INELIGIBLE": "ineligible",
        "UNKNOWN": "unknown",
    },
    ValidityState: {
        "VALID": "valid",
        "DERIVED_VALIDITY": "derived_validity",
        "OUT_OF_VALIDITY": "out_of_validity",
        "UNKNOWN": "unknown",
        "NOT_APPLICABLE": "not_applicable",
    },
    PersistenceClass: {
        "PERSIST": "persist",
        "TRANSIENT": "transient",
        "SOURCE_POLICY": "source_policy",
        "DO_NOT_PERSIST": "do_not_persist",
    },
    BenchmarkPopulationType: {
        "COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES": (
            "commercially_evidenced_spatial_alternatives"
        ),
    },
    SpatialRepresentation: {
        "EQUAL_AREA": "equal_area",
    },
    ParkingMode: {
        "OFF_STREET": "off_street",
        "ON_STREET": "on_street",
    },
    ParkingAccessClass: {
        "PUBLIC": "public",
        "PERMISSIVE": "permissive",
        "PRIVATE": "private",
        "CUSTOMERS": "customers",
        "UNKNOWN": "unknown",
    },
    RoadOriginQuality: {
        "VEHICLE_ENTRANCE": "vehicle_entrance",
        "DRIVEWAY": "driveway",
        "ROAD_SEGMENT_FALLBACK": "road_segment_fallback",
        "UNRESOLVED": "unresolved",
    },
    ScoringReadinessReason: {
        "MISSING_REQUIRED_FEATURE": "missing_required_feature",
        "FEATURE_UNCALIBRATED": "feature_uncalibrated",
        "FEATURE_DIAGNOSTIC_ONLY": "feature_diagnostic_only",
        "FEATURE_INELIGIBLE": "feature_ineligible",
        "INSUFFICIENT_DATA_QUALITY": "insufficient_data_quality",
        "POLICY_NOT_CONFIGURED": "policy_not_configured",
        "POLICY_VERSION_MISMATCH": "policy_version_mismatch",
        "COMPETITION_MEASUREMENT_MISMATCH": "competition_measurement_mismatch",
        "TRANSIT_SOURCE_BUNDLE_MISMATCH": "transit_source_bundle_mismatch",
        "ROAD_PARKING_COMPOSITE_UNAVAILABLE": "road_parking_composite_unavailable",
        "AGE_FALLBACK_POLICY_INVALID": "age_fallback_policy_invalid",
    },
    PipelineReason: {
        "SCORING_NOT_READY": "scoring_not_ready",
        "PIPELINE_STAGE_ERROR": "pipeline_stage_error",
    },
}


def test_all_production_enum_values_are_exhaustively_stable() -> None:
    for enum_type, expected in EXPECTED_ENUM_VALUES.items():
        actual = {member.name: member.value for member in enum_type}
        assert actual == expected
        for member in enum_type:
            assert str(member) == expected[member.name]


def test_exhaustive_mapping_covers_every_production_strenum_class() -> None:
    import sitescore_data

    discovered: set[type[StrEnum]] = set()
    for module_info in pkgutil.walk_packages(
        sitescore_data.__path__,
        prefix="sitescore_data.",
    ):
        module = importlib.import_module(module_info.name)
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, StrEnum)
                and value is not StrEnum
                and value.__module__ == module.__name__
            ):
                discovered.add(value)

    assert discovered == set(EXPECTED_ENUM_VALUES)
