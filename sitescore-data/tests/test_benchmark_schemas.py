from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
import math
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import BenchmarkPopulationType, GeographyType, SpatialRepresentation
from sitescore_data.schemas.benchmarks import BenchmarkReference, CommercialBenchmarkFrameMetadata
from sitescore_data.schemas.geography import GeographyRef


def geography() -> GeographyRef:
    return GeographyRef(
        geography_type=GeographyType.CBSA,
        geography_id="35620",
        name="New York-Newark-Jersey City",
        country_code="US",
        source_ref="census_cbsa",
        source_version="2025",
    )


def frame(**overrides: object) -> CommercialBenchmarkFrameMetadata:
    values: dict[str, object] = {
        "frame_id": "commercial_frame_nyc_v1",
        "frame_version": "1.0",
        "population_type": BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES,
        "benchmark_geography_ref": geography(),
        "spatial_representation": SpatialRepresentation.EQUAL_AREA,
        "tessellation_topology": "regular_hex",
        "projection_method": "local_equal_area",
        "projection_reference": "EPSG:custom-equal-area",
        "selected_resolution": 500.0,
        "selected_resolution_unit": "m",
        "resolution_policy_version": "resolution-policy-v1",
        "eligibility_policy_version": "eligibility-policy-v1",
        "source_refs": ("overture_release", "census_cbsa"),
        "eligible_count": 1000,
        "ineligible_count": 200,
        "unknown_count": 50,
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return CommercialBenchmarkFrameMetadata(**values)  # type: ignore[arg-type]


def reference(**overrides: object) -> BenchmarkReference:
    values: dict[str, object] = {
        "benchmark_id": "competition_benchmark_nyc_v1",
        "artifact_ref": "artifact://competition/nyc/v1",
        "frame_id": "commercial_frame_nyc_v1",
        "frame_version": "1.0",
        "population_type": BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES,
        "benchmark_geography_ref": geography(),
        "source_refs": ("overture_release", "census_cbsa"),
    }
    values.update(overrides)
    return BenchmarkReference(**values)  # type: ignore[arg-type]


def test_benchmark_population_semantics_are_fixed() -> None:
    value = frame()
    assert (
        value.population_type
        is BenchmarkPopulationType.COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES
    )


@pytest.mark.parametrize("field_name", ["eligible_count", "ineligible_count", "unknown_count"])
def test_benchmark_counts_must_be_nonnegative(field_name: str) -> None:
    with pytest.raises(ValueError):
        frame(**{field_name: -1})


@pytest.mark.parametrize("resolution", [0, -1, math.nan, math.inf, -math.inf])
def test_selected_resolution_must_be_positive_and_finite(resolution: float) -> None:
    with pytest.raises(ValueError):
        frame(selected_resolution=resolution)


def test_benchmark_requires_explicit_provenance() -> None:
    with pytest.raises(ValueError):
        frame(source_refs=())
    with pytest.raises(ValueError):
        reference(source_refs=())


def test_benchmark_requires_one_typed_geography() -> None:
    with pytest.raises(TypeError):
        frame(benchmark_geography_ref=None)
    with pytest.raises(TypeError):
        reference(benchmark_geography_ref=None)


def test_frame_records_resolution_and_projection_metadata() -> None:
    value = frame()
    assert value.selected_resolution == 500.0
    assert value.selected_resolution_unit == "m"
    assert value.tessellation_topology == "regular_hex"
    assert value.projection_method == "local_equal_area"
    assert value.projection_reference
    assert value.resolution_policy_version == "resolution-policy-v1"


def test_generated_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        frame(generated_at=datetime(2026, 8, 12, 12, 0))


def test_benchmark_schemas_are_immutable() -> None:
    metadata = frame()
    ref = reference()
    with pytest.raises(FrozenInstanceError):
        metadata.selected_resolution = 1000.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ref.frame_version = "2.0"  # type: ignore[misc]


def _contains_mutable(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin in {list, dict, set}:
        return True
    return any(_contains_mutable(arg) for arg in get_args(annotation))


def test_benchmark_schemas_have_no_mutable_annotations() -> None:
    for schema in (CommercialBenchmarkFrameMetadata, BenchmarkReference):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not _contains_mutable(hints[field.name])


def test_benchmark_geography_source_must_be_in_frame_lineage() -> None:
    with pytest.raises(ValueError):
        frame(source_refs=("overture_release",))


def test_benchmark_geography_source_must_be_in_reference_lineage() -> None:
    with pytest.raises(ValueError):
        reference(source_refs=("overture_release",))


def test_empty_benchmark_frame_metadata_is_structurally_allowed() -> None:
    value = frame(
        eligible_count=0,
        ineligible_count=0,
        unknown_count=0,
    )
    assert value.eligible_count == 0
    assert value.ineligible_count == 0
    assert value.unknown_count == 0


def test_benchmark_spatial_representation_is_explicitly_equal_area() -> None:
    value = frame()
    assert value.spatial_representation is SpatialRepresentation.EQUAL_AREA

    with pytest.raises((TypeError, ValueError)):
        frame(spatial_representation="unequal_area")
