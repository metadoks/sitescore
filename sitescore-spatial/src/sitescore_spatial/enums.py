from __future__ import annotations

from enum import Enum


class GeometryType(str, Enum):
    POLYGON = "POLYGON"
    MULTIPOLYGON = "MULTIPOLYGON"


class GeometryOperation(str, Enum):
    CANONICALIZE = "CANONICALIZE"
    PROJECT = "PROJECT"
    INTERSECT = "INTERSECT"
    AREA = "AREA"


class OperationState(str, Enum):
    SUCCESS = "SUCCESS"
    UNRESOLVED = "UNRESOLVED"
    INVALID_INPUT = "INVALID_INPUT"
    INCOMPATIBLE = "INCOMPATIBLE"
    ENGINE_ERROR = "ENGINE_ERROR"


class CompatibilityState(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNRESOLVED = "UNRESOLVED"


class AxisOrderPolicy(str, Enum):
    ALWAYS_XY = "ALWAYS_XY"


class InvalidGeometryBehavior(str, Enum):
    REJECT = "REJECT"


class EmptyGeometryBehavior(str, Enum):
    REJECT = "REJECT"
    ALLOW_OPERATION_OUTPUT = "ALLOW_OPERATION_OUTPUT"


class GeometryPrecisionMode(str, Enum):
    FULL_DOUBLE = "FULL_DOUBLE"
