from dataclasses import FrozenInstanceError, MISSING, fields
from datetime import datetime, timezone
from typing import get_args, get_origin, get_type_hints

import pytest

from sitescore_data.enums import GeographyType
from sitescore_data.schemas.geography import GeographyRef, ResolvedLocation


def make_geography_ref(**overrides: object) -> GeographyRef:
    values: dict[str, object] = {
        "geography_type": GeographyType.BLOCK_GROUP,
        "geography_id": "360610001001",
        "name": "Block Group 1",
        "country_code": "US",
        "source_ref": "census_tiger_2025",
        "source_version": "2025",
    }
    values.update(overrides)
    return GeographyRef(**values)  # type: ignore[arg-type]


def make_resolved_location(**overrides: object) -> ResolvedLocation:
    values: dict[str, object] = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "formatted_address": "New York, NY, USA",
        "country_code": "US",
        "geography_refs": (make_geography_ref(),),
        "source_refs": ("geocoder_primary", "census_tiger_2025"),
        "resolution_method_version": "resolve-location-v1",
        "generated_at": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return ResolvedLocation(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("latitude", [-90.0001, 90.0001])
def test_resolved_location_rejects_invalid_latitude(latitude: float) -> None:
    with pytest.raises(ValueError):
        make_resolved_location(latitude=latitude)


@pytest.mark.parametrize("longitude", [-180.0001, 180.0001])
def test_resolved_location_rejects_invalid_longitude(longitude: float) -> None:
    with pytest.raises(ValueError):
        make_resolved_location(longitude=longitude)


def test_resolved_location_accepts_coordinate_boundaries() -> None:
    location = make_resolved_location(latitude=-90.0, longitude=180.0)
    assert location.latitude == -90.0
    assert location.longitude == 180.0


def test_resolved_location_rejects_naive_generated_at() -> None:
    with pytest.raises(ValueError):
        make_resolved_location(generated_at=datetime(2026, 8, 12, 12, 0))


def test_geography_id_is_generic_not_canonical_identifier_specific() -> None:
    geography = make_geography_ref(geography_id="06-075/custom geography")
    assert geography.geography_id == "06-075/custom geography"


def test_geography_ref_source_must_be_in_resolved_location_sources() -> None:
    with pytest.raises(ValueError):
        make_resolved_location(source_refs=("geocoder_primary",))


def test_geography_country_must_match_resolved_location_country() -> None:
    geography = make_geography_ref(country_code="CA")
    with pytest.raises(ValueError):
        make_resolved_location(geography_refs=(geography,))


def test_country_code_must_be_two_letter_uppercase() -> None:
    with pytest.raises(ValueError):
        make_geography_ref(country_code="us")


def test_geography_schemas_are_immutable() -> None:
    geography = make_geography_ref()
    location = make_resolved_location()

    with pytest.raises(FrozenInstanceError):
        geography.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        location.latitude = 0.0  # type: ignore[misc]


def test_geography_schemas_have_no_mutable_collection_field_types() -> None:
    mutable_origins = {list, dict, set}

    def contains_mutable(annotation: object) -> bool:
        origin = get_origin(annotation)
        if origin in mutable_origins:
            return True
        return any(contains_mutable(arg) for arg in get_args(annotation))

    for schema in (GeographyRef, ResolvedLocation):
        hints = get_type_hints(schema)
        for field in fields(schema):
            assert not contains_mutable(hints[field.name])


def test_generated_at_has_no_implicit_default() -> None:
    generated_at = next(
        field for field in fields(ResolvedLocation) if field.name == "generated_at"
    )
    assert generated_at.default is MISSING
    assert generated_at.default_factory is MISSING


def test_resolved_location_requires_provenance() -> None:
    with pytest.raises(ValueError):
        make_resolved_location(
            geography_refs=(),
            source_refs=(),
        )
