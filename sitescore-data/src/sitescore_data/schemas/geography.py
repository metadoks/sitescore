"""Immutable geography and resolved-location contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from sitescore_data.enums import GeographyType
from sitescore_data.validation import (
    require_aware_datetime,
    require_canonical_identifier,
    require_latitude,
    require_longitude,
)


_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")


def _require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    return value


def _require_optional_nonempty_text(
    value: str | None, *, field_name: str
) -> str | None:
    if value is None:
        return None
    return _require_nonempty_text(value, field_name=field_name)


def _require_country_code(value: str, *, field_name: str = "country_code") -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not _COUNTRY_CODE_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a two-letter uppercase country code")
    return value


def _require_unique_source_refs(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError("source_refs must be a tuple")
    for value in values:
        require_canonical_identifier(value, field_name="source_refs item")
    if len(set(values)) != len(values):
        raise ValueError("source_refs must not contain duplicates")
    return values


@dataclass(frozen=True, slots=True)
class GeographyRef:
    """Provider-neutral reference to a deterministic geographic unit."""

    geography_type: GeographyType
    geography_id: str
    name: str
    country_code: str
    source_ref: str
    source_version: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.geography_type, GeographyType):
            raise TypeError("geography_type must be a GeographyType")
        _require_nonempty_text(self.geography_id, field_name="geography_id")
        _require_nonempty_text(self.name, field_name="name")
        _require_country_code(self.country_code)
        require_canonical_identifier(self.source_ref, field_name="source_ref")
        _require_optional_nonempty_text(
            self.source_version, field_name="source_version"
        )


@dataclass(frozen=True, slots=True)
class ResolvedLocation:
    """Deterministically resolved site location with explicit provenance."""

    latitude: float
    longitude: float
    formatted_address: str
    country_code: str
    geography_refs: tuple[GeographyRef, ...]
    source_refs: tuple[str, ...]
    resolution_method_version: str
    generated_at: datetime

    def __post_init__(self) -> None:
        require_latitude(self.latitude, field_name="latitude")
        require_longitude(self.longitude, field_name="longitude")
        _require_nonempty_text(self.formatted_address, field_name="formatted_address")
        _require_country_code(self.country_code)
        if not isinstance(self.geography_refs, tuple):
            raise TypeError("geography_refs must be a tuple")
        if len(set(self.geography_refs)) != len(self.geography_refs):
            raise ValueError("geography_refs must not contain duplicates")
        for geography_ref in self.geography_refs:
            if not isinstance(geography_ref, GeographyRef):
                raise TypeError("geography_refs must contain GeographyRef values")
            if geography_ref.country_code != self.country_code:
                raise ValueError(
                    "all geography_refs must use the ResolvedLocation country_code"
                )
        _require_unique_source_refs(self.source_refs)
        if not self.source_refs:
            raise ValueError(
                "ResolvedLocation requires at least one source_ref"
            )
        missing_source_refs = {
            geography_ref.source_ref for geography_ref in self.geography_refs
        } - set(self.source_refs)
        if missing_source_refs:
            raise ValueError(
                "source_refs must include every GeographyRef.source_ref"
            )
        _require_nonempty_text(
            self.resolution_method_version,
            field_name="resolution_method_version",
        )
        require_aware_datetime(self.generated_at, field_name="generated_at")
