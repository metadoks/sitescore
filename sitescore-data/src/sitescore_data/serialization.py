"""Deterministic serialization helpers for SiteScore data contracts.

This module is intentionally independent from ``sitescore-core`` serialization and
fingerprint implementations.  It serializes only canonical data-contract values
and does not generate timestamps, hashes, UUIDs, or other nondeterministic data.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import StrEnum
import math
from typing import Any

from .validation import require_aware_datetime


def to_primitive(value: Any) -> Any:
    """Convert a canonical data-contract value to deterministic Python primitives.

    Supported values are dataclass instances, ``StrEnum`` members, tuples, dates,
    timezone-aware datetimes, strings, booleans, finite integers/floats, and
    ``None``.  Mutable collections are deliberately unsupported at this contract
    boundary.
    """

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_primitive(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, StrEnum):
        return value.value

    if isinstance(value, tuple):
        return [to_primitive(item) for item in value]

    if isinstance(value, datetime):
        require_aware_datetime(value, field_name="datetime")
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical numeric values must be finite")
        return value

    raise TypeError(
        f"unsupported canonical serialization type: {type(value).__name__}"
    )
