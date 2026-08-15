"""Typed state enums for SiteScore's real-data layer.

These enums deliberately do not redefine similarly named concepts from
``sitescore-core``.  They model data availability, evidence quality, scoring
eligibility, calibration, persistence, benchmark population semantics, and
pipeline state at the data-contract boundary.
"""

from enum import StrEnum


class AvailabilityState(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class DataQualityState(StrEnum):
    FULL = "full"
    DEGRADED = "degraded"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class ScoreEligibility(StrEnum):
    ELIGIBLE = "eligible"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    INELIGIBLE = "ineligible"
    NOT_APPLICABLE = "not_applicable"


class CalibrationState(StrEnum):
    CALIBRATED = "calibrated"
    UNCALIBRATED = "uncalibrated"
    NOT_APPLICABLE = "not_applicable"


class PipelineStatus(StrEnum):
    SCORE_READY = "score_ready"
    NOT_SCORE_READY = "not_score_ready"
    PIPELINE_ERROR = "pipeline_error"


class GeographyType(StrEnum):
    COUNTRY = "country"
    STATE = "state"
    COUNTY = "county"
    CBSA = "cbsa"
    METROPOLITAN_DIVISION = "metropolitan_division"
    CSA = "csa"
    TRACT = "tract"
    BLOCK_GROUP = "block_group"
    ZCTA = "zcta"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class EligibilityState(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"


class ValidityState(StrEnum):
    VALID = "valid"
    DERIVED_VALIDITY = "derived_validity"
    OUT_OF_VALIDITY = "out_of_validity"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class PersistenceClass(StrEnum):
    PERSIST = "persist"
    TRANSIENT = "transient"
    SOURCE_POLICY = "source_policy"
    DO_NOT_PERSIST = "do_not_persist"


class BenchmarkPopulationType(StrEnum):
    COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES = (
        "commercially_evidenced_spatial_alternatives"
    )


class SpatialRepresentation(StrEnum):
    EQUAL_AREA = "equal_area"
