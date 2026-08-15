"""Private deterministic validation primitives for provider-layer contracts."""

from __future__ import annotations

from datetime import datetime
import math
import re

_CANONICAL_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(?:[.-][a-z0-9_]+)*$")


def require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    return value


def require_optional_nonempty_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return require_nonempty_text(value, field_name=field_name)


def require_canonical_id(value: str, *, field_name: str) -> str:
    require_nonempty_text(value, field_name=field_name)
    if value != value.lower() or not _CANONICAL_ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase canonical identifier")
    return value


def require_aware_datetime(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def require_optional_aware_datetime(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    return require_aware_datetime(value, field_name=field_name)


def require_positive_int(value: int | None, *, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be > 0")
    return value


def require_finite_number(value: int | float, *, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite int or float")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite")
    return value


_SECRET_REFERENCE_TOKENS = frozenset({
    "api_key=", "apikey=", "access_token=", "refresh_token=",
    "authorization=", "client_secret=", "password=", "token=",
})


def require_secret_free_reference(value: str | None, *, field_name: str) -> str | None:
    """Reject obvious credential-bearing references before they enter artifacts/metadata.

    This is a boundary guard, not a secret detector. Credentials must be carried
    out-of-band and references must be non-secret by construction.
    """
    if value is None:
        return None
    require_nonempty_text(value, field_name=field_name)
    lowered = value.lower()
    if any(token in lowered for token in _SECRET_REFERENCE_TOKENS):
        raise ValueError(f"{field_name} must not contain credential-like query material")
    scheme = lowered.find("://")
    if scheme >= 0:
        authority = value[scheme + 3 :].split("/", 1)[0]
        if "@" in authority:
            userinfo = authority.rsplit("@", 1)[0]
            if ":" in userinfo:
                raise ValueError(f"{field_name} must not contain URI userinfo credentials")
    return value
