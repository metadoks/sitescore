"""Immutable benchmark frame metadata and lightweight references."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data.enums import BenchmarkPopulationType, SpatialRepresentation
from sitescore_data.schemas.geography import GeographyRef
from sitescore_data.validation import (
    require_aware_datetime,
    require_canonical_identifier,
    require_nonnegative_number,
    require_positive_number,
)


def _require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
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
class CommercialBenchmarkFrameMetadata:
    """Metadata for one frozen commercially-evidenced benchmark frame artifact."""

    frame_id: str
    frame_version: str
    population_type: BenchmarkPopulationType
    benchmark_geography_ref: GeographyRef
    spatial_representation: SpatialRepresentation
    tessellation_topology: str
    projection_method: str
    projection_reference: str
    selected_resolution: float
    selected_resolution_unit: str
    resolution_policy_version: str
    eligibility_policy_version: str
    source_refs: tuple[str, ...]
    eligible_count: int
    ineligible_count: int
    unknown_count: int
    generated_at: datetime

    def __post_init__(self) -> None:
        require_canonical_identifier(self.frame_id, field_name="frame_id")
        _require_nonempty_text(self.frame_version, field_name="frame_version")
        if (
            self.population_type
            is not BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES
        ):
            raise ValueError(
                "commercial benchmark frames must use "
                "COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES"
            )
        if not isinstance(self.benchmark_geography_ref, GeographyRef):
            raise TypeError("benchmark_geography_ref must be a GeographyRef")
        if self.spatial_representation is not SpatialRepresentation.EQUAL_AREA:
            raise ValueError("commercial benchmark frames require EQUAL_AREA spatial representation")
        _require_nonempty_text(
            self.tessellation_topology,
            field_name="tessellation_topology",
        )
        _require_nonempty_text(self.projection_method, field_name="projection_method")
        _require_nonempty_text(
            self.projection_reference,
            field_name="projection_reference",
        )
        require_positive_number(
            self.selected_resolution,
            field_name="selected_resolution",
        )
        _require_nonempty_text(
            self.selected_resolution_unit,
            field_name="selected_resolution_unit",
        )
        _require_nonempty_text(
            self.resolution_policy_version,
            field_name="resolution_policy_version",
        )
        _require_nonempty_text(
            self.eligibility_policy_version,
            field_name="eligibility_policy_version",
        )
        _require_unique_source_refs(self.source_refs)
        if not self.source_refs:
            raise ValueError(
                "CommercialBenchmarkFrameMetadata requires at least one source_ref"
            )
        if self.benchmark_geography_ref.source_ref not in self.source_refs:
            raise ValueError(
                "source_refs must include benchmark_geography_ref.source_ref"
            )
        for field_name in (
            "eligible_count",
            "ineligible_count",
            "unknown_count",
        ):
            value = getattr(self, field_name)
            require_nonnegative_number(value, field_name=field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an int")
        require_aware_datetime(self.generated_at, field_name="generated_at")


@dataclass(frozen=True, slots=True)
class BenchmarkReference:
    """Lightweight identity/reference to a persisted benchmark artifact."""

    benchmark_id: str
    artifact_ref: str
    frame_id: str
    frame_version: str
    population_type: BenchmarkPopulationType
    benchmark_geography_ref: GeographyRef
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        require_canonical_identifier(self.benchmark_id, field_name="benchmark_id")
        _require_nonempty_text(self.artifact_ref, field_name="artifact_ref")
        require_canonical_identifier(self.frame_id, field_name="frame_id")
        _require_nonempty_text(self.frame_version, field_name="frame_version")
        if (
            self.population_type
            is not BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES
        ):
            raise ValueError(
                "benchmark references must use "
                "COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES"
            )
        if not isinstance(self.benchmark_geography_ref, GeographyRef):
            raise TypeError("benchmark_geography_ref must be a GeographyRef")
        _require_unique_source_refs(self.source_refs)
        if not self.source_refs:
            raise ValueError("BenchmarkReference requires at least one source_ref")
        if self.benchmark_geography_ref.source_ref not in self.source_refs:
            raise ValueError(
                "source_refs must include benchmark_geography_ref.source_ref"
            )
