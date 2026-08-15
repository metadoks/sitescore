from __future__ import annotations

import math
import re
from collections.abc import Iterable

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_MUTABLE_RELEASE_RE = re.compile(r"(^|[-_./\s])(latest|current|live|today|now)($|[-_./\s])", re.I)


def canonical_string(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be a non-empty canonical string")
    return value


def immutable_release(value: str, field: str = "release") -> str:
    value = canonical_string(value, field)
    if _MUTABLE_RELEASE_RE.search(value):
        raise ValueError(f"{field} must be immutable; mutable latest/current/live-style identity rejected")
    return value


def sha256_hex(value: str, field: str) -> str:
    if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
        raise ValueError(f"{field} must be lowercase SHA-256 hex")
    return value


def finite_number(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite numeric evidence")
    return float(value)


def canonical_string_tuple(values: Iterable[str], field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    out = tuple(canonical_string(v, field) for v in values)
    if not allow_empty and not out:
        raise ValueError(f"{field} must not be empty")
    if len(set(out)) != len(out):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(sorted(out))
