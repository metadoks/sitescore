"""Deterministic validation primitives for SiteScore data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import re
from typing import TypeVar


NumberT = TypeVar("NumberT", int, float)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*(?:[.-][a-z0-9_]+)*$")


def _reject_bool(value: object, *, field_name: str) -> None:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not bool")


def require_finite_number(value: NumberT, *, field_name: str = "value") -> NumberT:
    """Return ``value`` if it is a finite int/float; otherwise raise.

    Booleans are rejected even though ``bool`` subclasses ``int`` in Python.
    """

    _reject_bool(value, field_name=field_name)
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be an int or float")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite")
    return value


def require_nonnegative_number(
    value: NumberT, *, field_name: str = "value"
) -> NumberT:
    require_finite_number(value, field_name=field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def require_positive_number(
    value: NumberT, *, field_name: str = "value"
) -> NumberT:
    require_finite_number(value, field_name=field_name)
    if value <= 0:
        raise ValueError(f"{field_name} must be > 0")
    return value


def require_bounded_number(
    value: NumberT,
    *,
    low: float,
    high: float,
    field_name: str = "value",
) -> NumberT:
    require_finite_number(value, field_name=field_name)
    require_finite_number(low, field_name="low")
    require_finite_number(high, field_name="high")
    if low > high:
        raise ValueError("low must be <= high")
    if value < low or value > high:
        raise ValueError(f"{field_name} must be between {low} and {high} inclusive")
    return value


def require_latitude(value: NumberT, *, field_name: str = "latitude") -> NumberT:
    return require_bounded_number(value, low=-90.0, high=90.0, field_name=field_name)


def require_longitude(value: NumberT, *, field_name: str = "longitude") -> NumberT:
    return require_bounded_number(value, low=-180.0, high=180.0, field_name=field_name)


def require_aware_datetime(value: datetime, *, field_name: str = "datetime") -> datetime:
    """Require an explicitly timezone-aware ``datetime``.

    No current time is generated here.  The caller must provide the timestamp.
    """

    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def require_canonical_identifier(
    value: str, *, field_name: str = "identifier"
) -> str:
    """Validate a normalized opaque identifier without assigning domain meaning."""

    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{field_name} must not contain leading/trailing whitespace")
    if value != value.lower():
        raise ValueError(f"{field_name} must be lowercase")
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{field_name} must match canonical identifier syntax: "
            "lowercase ASCII letters/digits/underscore with optional '.' or '-' segments"
        )
    return value


@dataclass(frozen=True, slots=True)
class SectorKey:
    """Opaque, normalized sector identifier used at the data/app handoff boundary.

    This value object intentionally does not know or enforce the frozen core's
    sector vocabulary (coffee/restaurant/gym/beauty).  Semantic validation of
    that vocabulary belongs to the future ``sitescore-app`` adapter.
    """

    value: str

    def __post_init__(self) -> None:
        require_canonical_identifier(self.value, field_name="SectorKey.value")

    def __str__(self) -> str:
        return self.value
