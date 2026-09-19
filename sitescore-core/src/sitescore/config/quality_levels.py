from enum import StrEnum


class CoverageLevel(StrEnum):
    FULL = "full"
    DEGRADED = "degraded"
    MISSING = "missing"


class InputQuality(StrEnum):
    USER = "user"
    DEFAULT = "default"
    MISSING = "missing"


class GeographicLevel(StrEnum):
    BLOCK_GROUP = "block_group"
    TRACT = "tract"
    ZIP = "zip"
    COUNTY = "county"
    UNKNOWN = "unknown"