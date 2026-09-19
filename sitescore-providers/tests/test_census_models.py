from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from sitescore_data import GeographyType

from sitescore_providers.census import (
    CensusAddressRequest,
    CensusBenchmarkVintageCompatibility,
    CensusCoordinates,
    CensusGeographyLayerSpec,
    CensusGeographyManifest,
    GeocodeAcceptancePolicy,
)


def core_layer_specs():
    # Fixture IDs are manifest-bound fake Census layer IDs; production IDs must come from approved config.
    return (
        CensusGeographyLayerSpec(GeographyType.STATE, 101, ("States",), True),
        CensusGeographyLayerSpec(GeographyType.COUNTY, 102, ("Counties",), True),
        CensusGeographyLayerSpec(GeographyType.TRACT, 103, ("Census Tracts",), True),
        CensusGeographyLayerSpec(GeographyType.BLOCK_GROUP, 104, ("Census Block Groups",), True),
    )


def optional_layer_specs():
    return (
        CensusGeographyLayerSpec(GeographyType.CBSA, 201, ("Metropolitan Statistical Areas", "Micropolitan Statistical Areas"), False),
        CensusGeographyLayerSpec(GeographyType.METROPOLITAN_DIVISION, 202, ("Metropolitan Divisions",), False),
        CensusGeographyLayerSpec(GeographyType.CSA, 203, ("Combined Statistical Areas",), False),
        CensusGeographyLayerSpec(GeographyType.ZCTA, 204, ("ZIP Code Tabulation Areas", "2020 Census ZIP Code Tabulation Areas"), False),
    )


def compatibility(
    *,
    compatibility_id: str = "acs2024_pair",
    compatibility_version: str = "v1",
    geocoder_benchmark: str = "Public_AR_ACS2024",
    geography_vintage: str = "ACS2024_ACS2024",
) -> CensusBenchmarkVintageCompatibility:
    return CensusBenchmarkVintageCompatibility(
        compatibility_id=compatibility_id,
        compatibility_version=compatibility_version,
        geocoder_benchmark=geocoder_benchmark,
        geography_vintage=geography_vintage,
    )


def manifest() -> CensusGeographyManifest:
    return CensusGeographyManifest(
        manifest_version="v1",
        compatibility=compatibility(compatibility_id="acs2024_pair", compatibility_version="v1", geocoder_benchmark="Public_AR_ACS2024", geography_vintage="ACS2024_ACS2024"),
        supported_layers=core_layer_specs(),
    )


def test_manifest_rejects_mutable_current_identity():
    with pytest.raises(ValueError, match="Current"):
        CensusGeographyManifest(
            manifest_version="v1",
            compatibility=compatibility(compatibility_id="mutable_pair", compatibility_version="v1", geocoder_benchmark="Public_AR_Current", geography_vintage="ACS2024_Current"),
            supported_layers=core_layer_specs(),
        )


def test_manifest_identity_is_deterministic_and_version_bound():
    first = manifest()
    second = manifest()
    changed = CensusGeographyManifest(
        manifest_version="v2",
        compatibility=compatibility(compatibility_id=first.compatibility_id, compatibility_version=first.compatibility_version, geocoder_benchmark=first.geocoder_benchmark, geography_vintage=first.geography_vintage),
        supported_layers=first.supported_layers,
    )
    assert first.identity == second.identity
    assert first.identity != changed.identity


def test_manifest_identity_commits_to_compatibility_and_exact_layer_spec():
    first = manifest()
    changed_compatibility = CensusGeographyManifest(
        manifest_version=first.manifest_version,
        compatibility=compatibility(compatibility_id="acs2024_pair_reviewed", compatibility_version=first.compatibility_version, geocoder_benchmark=first.geocoder_benchmark, geography_vintage=first.geography_vintage),
        supported_layers=first.supported_layers,
    )
    changed_layer_id = CensusGeographyManifest(
        manifest_version=first.manifest_version,
        compatibility=compatibility(compatibility_id=first.compatibility_id, compatibility_version=first.compatibility_version, geocoder_benchmark=first.geocoder_benchmark, geography_vintage=first.geography_vintage),
        supported_layers=(
            CensusGeographyLayerSpec(GeographyType.STATE, 999, ("States",), True),
            *first.supported_layers[1:],
        ),
    )
    changed_alias = CensusGeographyManifest(
        manifest_version=first.manifest_version,
        compatibility=compatibility(compatibility_id=first.compatibility_id, compatibility_version=first.compatibility_version, geocoder_benchmark=first.geocoder_benchmark, geography_vintage=first.geography_vintage),
        supported_layers=(
            CensusGeographyLayerSpec(GeographyType.STATE, 101, ("States", "State Areas"), True),
            *first.supported_layers[1:],
        ),
    )
    assert first.identity != changed_compatibility.identity
    assert first.identity != changed_layer_id.identity
    assert first.identity != changed_alias.identity


def test_manifest_rejects_duplicate_geography_types_and_response_keys():
    duplicate_type = (
        CensusGeographyLayerSpec(GeographyType.STATE, 301, ("States",), True),
        CensusGeographyLayerSpec(GeographyType.STATE, 302, ("Other States",), True),
    )
    with pytest.raises(ValueError, match="repeat geography types"):
        CensusGeographyManifest("v1", compatibility(), duplicate_type)
    duplicate_key = (
        CensusGeographyLayerSpec(GeographyType.STATE, 301, ("States",), True),
        CensusGeographyLayerSpec(GeographyType.COUNTY, 303, ("States",), True),
    )
    with pytest.raises(ValueError, match="repeat response keys"):
        CensusGeographyManifest("v1", compatibility(), duplicate_key)


@pytest.mark.parametrize(
    "latitude,longitude,error",
    [
        (90.1, 0.0, ValueError),
        (-90.1, 0.0, ValueError),
        (0.0, 180.1, ValueError),
        (0.0, -180.1, ValueError),
        (float("nan"), 0.0, ValueError),
        (0.0, float("inf"), ValueError),
        (True, 0.0, TypeError),
        (0.0, False, TypeError),
    ],
)
def test_coordinate_validation(latitude, longitude, error):
    with pytest.raises(error):
        CensusCoordinates(latitude=latitude, longitude=longitude)


def test_address_request_requires_census_supported_address_components():
    m = manifest()
    CensusAddressRequest(street="4600 Silver Hill Rd", city="Washington", state="DC", zip_code=None, manifest=m)
    CensusAddressRequest(street="4600 Silver Hill Rd", city=None, state=None, zip_code="20233", manifest=m)
    with pytest.raises(ValueError):
        CensusAddressRequest(street="4600 Silver Hill Rd", city="Washington", state=None, zip_code=None, manifest=m)


def test_provider_records_are_immutable():
    coordinates = CensusCoordinates(38.0, -76.0)
    with pytest.raises(FrozenInstanceError):
        coordinates.latitude = 39.0


def test_acceptance_policy_has_no_empirical_thresholds():
    policy = GeocodeAcceptancePolicy(policy_id="census_acceptance", policy_version="v1")
    assert policy.accepted_match_types == ()
    assert not hasattr(policy, "confidence_threshold")
    assert not hasattr(policy, "precision_score")


def test_manifest_cannot_independently_override_compatibility_pair():
    pair = compatibility()
    m = CensusGeographyManifest("v1", pair, core_layer_specs())
    assert m.geocoder_benchmark == pair.geocoder_benchmark
    assert m.geography_vintage == pair.geography_vintage
    with pytest.raises(TypeError):
        CensusGeographyManifest(
            manifest_version="v1",
            compatibility=pair,
            geocoder_benchmark="arbitrary",
            supported_layers=core_layer_specs(),
        )
    with pytest.raises(TypeError):
        CensusGeographyManifest(
            manifest_version="v1",
            compatibility=pair,
            geography_vintage="arbitrary",
            supported_layers=core_layer_specs(),
        )


def test_compatibility_pair_and_identity_changes_manifest_identity():
    first = manifest()
    changed_pair = CensusGeographyManifest(
        first.manifest_version,
        compatibility(geography_vintage="ACS2023_ACS2023"),
        first.supported_layers,
    )
    changed_identity = CensusGeographyManifest(
        first.manifest_version,
        compatibility(compatibility_id="acs2024_pair_reviewed", compatibility_version="v2"),
        first.supported_layers,
    )
    assert first.identity != changed_pair.identity
    assert first.identity != changed_identity.identity


def test_layer_required_must_be_strict_bool_and_changes_manifest_identity():
    with pytest.raises(TypeError, match="required must be a bool"):
        CensusGeographyLayerSpec(GeographyType.STATE, 101, ("States",), 1)
    first = manifest()
    changed = CensusGeographyManifest(
        first.manifest_version,
        first.compatibility,
        (
            CensusGeographyLayerSpec(GeographyType.STATE, 101, ("States",), False),
            *first.supported_layers[1:],
        ),
    )
    assert first.identity != changed.identity
