from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sitescore_data import DataQualityState, GeographyType, PersistenceClass

from sitescore_providers import (
    ArtifactRef,
    CommercialUseState,
    PersistenceDecision,
    ProviderIdentity,
    ProviderPolicyDecision,
    RawAcquisitionArtifact,
    RedistributionState,
    build_parsed_artifact,
    build_request_fingerprint,
    build_source_metadata,
    sha256_bytes,
)
from sitescore_providers.census import (
    CensusAddressRequest,
    CensusBenchmarkVintageCompatibility,
    CensusCoordinates,
    CensusGeographyEvidence,
    CensusGeographyLayerSpec,
    CensusGeographyManifest,
    GeocodeAcceptancePolicy,
    build_geography_refs,
    build_resolved_location,
    parse_geocode_evidence,
    parse_geography_evidence,
)
from sitescore_providers.errors import ProviderInvariantError, ProviderMalformedResponseError

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


NOW = datetime(2026, 8, 12, 17, 0, tzinfo=timezone.utc)


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


def policy() -> ProviderPolicyDecision:
    persistence = PersistenceDecision(
        policy_id="census_test_policy",
        policy_version="v1",
        persistence_class=PersistenceClass.PERSIST,
    )
    return ProviderPolicyDecision(
        policy_id="census_test_policy",
        policy_version="v1",
        persistence=persistence,
        attribution_required=False,
        redistribution_state=RedistributionState.UNKNOWN,
        commercial_use_state=CommercialUseState.UNKNOWN,
        license_class="census-api-terms",
        policy_reference="https://www.census.gov/data/developers/about/terms-of-service.html",
    )


def raw_and_parsed(parsed_value, *, domain="geocoding", dataset="maf_tiger_address_ranges", vintage=None, ref="artifact:parsed/test"):
    m = manifest()
    identity = ProviderIdentity(
        provider_key="us_census_geocoder",
        domain=domain,
        dataset=dataset,
        dataset_release=m.geocoder_benchmark,
        vintage=vintage,
        schema_version=None,
        parser_version="v1",
        method_version="v1",
    )
    fingerprint = build_request_fingerprint(
        provider_key=identity.provider_key,
        operation="test_operation",
        semantic_parameters={"benchmark": m.geocoder_benchmark, "vintage": m.geography_vintage},
        dataset=dataset,
        dataset_release=m.geocoder_benchmark,
        policy_id="census_test_policy",
        policy_version="v1",
    )
    raw = RawAcquisitionArtifact(
        provider_identity=identity,
        request_fingerprint=fingerprint,
        media_type="application/json",
        content_hash=sha256_bytes(b"raw census fixture" + domain.encode()),
        artifact_ref=ArtifactRef(f"artifact:raw/{domain}"),
        retrieved_at=NOW,
        persistence=policy().persistence,
    )
    parsed = build_parsed_artifact(
        raw_artifact=raw,
        parser_id="fixture_parser",
        parser_version="v1",
        parsed_value=parsed_value,
        parsed_artifact_ref=ArtifactRef(ref),
    )
    return raw, parsed, fingerprint


def matched_json(*, x=-76.92748724230096, y=38.84601622386617):
    return {
        "result": {
            "input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}},
            "addressMatches": [
                {
                    "tigerLine": {"side": "L", "tigerLineId": "76355984"},
                    "coordinates": {"x": x, "y": y},
                    "matchedAddress": "4600 SILVER HILL RD, WASHINGTON, DC, 20233",
                }
            ],
        }
    }


def geography_json(include_metro=False):
    geographies = {
        "States": [{"GEOID": "24", "NAME": "Maryland"}],
        "Counties": [{"GEOID": "24033", "NAME": "Prince George's County"}],
        "Census Tracts": [{"GEOID": "24033802405", "NAME": "Census Tract 8024.05"}],
        "Census Block Groups": [{"GEOID": "240338024052", "NAME": "Block Group 2"}],
    }
    if include_metro:
        geographies["Metropolitan Statistical Areas"] = [{"GEOID": "47900", "NAME": "Washington-Arlington-Alexandria"}]
    return {
        "result": {
            "input": {
                "benchmark": {"benchmarkName": "Public_AR_ACS2024"},
                "vintage": {"vintageName": "ACS2024_ACS2024"},
            },
            "geographies": geographies,
        }
    }


def test_matched_address_parse_and_coordinate_ordering():
    value = matched_json()
    _, parsed, fp = raw_and_parsed(value)
    evidence = parse_geocode_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, manifest=manifest())
    assert evidence.match_state.value == "matched"
    candidate = evidence.candidates[0]
    assert candidate.coordinates.latitude == pytest.approx(38.84601622386617)
    assert candidate.coordinates.longitude == pytest.approx(-76.92748724230096)
    assert candidate.tiger_line_id == "76355984"
    assert evidence.precision.value == "address_range_interpolated"


def test_no_match_parse_is_provider_observation_not_real_world_absence():
    value = {"result": {"input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}}, "addressMatches": []}}
    _, parsed, fp = raw_and_parsed(value)
    evidence = parse_geocode_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, manifest=manifest())
    decision = GeocodeAcceptancePolicy("census_acceptance", "v1").evaluate(evidence)
    assert evidence.match_state.value == "no_match"
    assert not decision.accepted
    assert decision.fallback_eligible


def test_multiple_matches_parse_as_ambiguous_and_are_not_accepted():
    value = matched_json()
    value["result"]["addressMatches"].append({**value["result"]["addressMatches"][0], "matchedAddress": "4602 SILVER HILL RD, WASHINGTON, DC, 20233"})
    _, parsed, fp = raw_and_parsed(value)
    evidence = parse_geocode_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, manifest=manifest())
    decision = GeocodeAcceptancePolicy("census_acceptance", "v1").evaluate(evidence)
    assert evidence.match_state.value == "ambiguous"
    assert not decision.accepted
    assert decision.fallback_eligible


def test_malformed_census_response_rejected():
    value = {"result": {"input": {"benchmark": {"benchmarkName": "Public_AR_ACS2024"}}, "addressMatches": [{"coordinates": {"x": "west", "y": 38.0}, "matchedAddress": "X"}]}}
    _, parsed, fp = raw_and_parsed(value)
    with pytest.raises(ProviderMalformedResponseError):
        parse_geocode_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, manifest=manifest())


def test_response_benchmark_must_match_manifest():
    value = matched_json()
    value["result"]["input"]["benchmark"]["benchmarkName"] = "Public_AR_ACS2023"
    _, parsed, fp = raw_and_parsed(value)
    with pytest.raises(ProviderInvariantError):
        parse_geocode_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, manifest=manifest())


def test_geography_geoid_mapping_and_deterministic_order():
    value = geography_json()
    _, parsed, fp = raw_and_parsed(value, domain="geography", dataset="census_geocoder_geolookup", vintage="ACS2024_ACS2024", ref="artifact:parsed/geography")
    coordinates = CensusCoordinates(38.84601622386617, -76.92748724230096)
    evidence = parse_geography_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, coordinates=coordinates, manifest=manifest())
    assert [(r.geography_type, r.geoid) for r in evidence.records] == [
        (GeographyType.STATE, "24"),
        (GeographyType.COUNTY, "24033"),
        (GeographyType.TRACT, "24033802405"),
        (GeographyType.BLOCK_GROUP, "240338024052"),
    ]


def test_optional_metro_absence_is_not_fabricated():
    m = CensusGeographyManifest(
        "v1",
        compatibility(),
        core_layer_specs() + optional_layer_specs(),
    )
    value = geography_json(include_metro=False)
    _, parsed, fp = raw_and_parsed(value, domain="geography", dataset="census_geocoder_geolookup", vintage="ACS2024_ACS2024", ref="artifact:parsed/geography2")
    evidence = parse_geography_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, coordinates=CensusCoordinates(38.8, -76.9), manifest=m)
    assert GeographyType.CBSA not in {r.geography_type for r in evidence.records}
    assert GeographyType.ZCTA not in {r.geography_type for r in evidence.records}


def test_duplicate_layer_records_rejected():
    value = geography_json()
    value["result"]["geographies"]["States"].append({"GEOID": "11", "NAME": "District of Columbia"})
    _, parsed, fp = raw_and_parsed(value, domain="geography", dataset="census_geocoder_geolookup", vintage="ACS2024_ACS2024", ref="artifact:parsed/geography3")
    with pytest.raises(ProviderInvariantError, match="multiple records"):
        parse_geography_evidence(parsed_value=value, parsed_artifact=parsed, request_fingerprint=fp, coordinates=CensusCoordinates(38.8, -76.9), manifest=manifest())


def test_source_metadata_and_frozen_geography_builders():
    m = manifest()
    g_value = matched_json()
    raw_g, parsed_g, fp_g = raw_and_parsed(g_value)
    geocode = parse_geocode_evidence(parsed_value=g_value, parsed_artifact=parsed_g, request_fingerprint=fp_g, manifest=m)
    geo_value = geography_json()
    raw_geo, parsed_geo, fp_geo = raw_and_parsed(geo_value, domain="geography", dataset="census_geocoder_geolookup", vintage=m.geography_vintage, ref="artifact:parsed/geography4")
    geography = parse_geography_evidence(parsed_value=geo_value, parsed_artifact=parsed_geo, request_fingerprint=fp_geo, coordinates=geocode.candidates[0].coordinates, manifest=m)
    p = policy()
    geocode_source = build_source_metadata(raw_artifact=raw_g, data_quality=DataQualityState.FULL, policy=p, source_reference="https://geocoding.geo.census.gov/geocoder/locations/address")
    geography_source = build_source_metadata(raw_artifact=raw_geo, data_quality=DataQualityState.FULL, policy=p, source_reference="https://geocoding.geo.census.gov/geocoder/geographies/coordinates")
    refs = build_geography_refs(evidence=geography, source_metadata=geography_source)
    assert [ref.geography_type for ref in refs] == [
        GeographyType.COUNTRY,
        GeographyType.STATE,
        GeographyType.COUNTY,
        GeographyType.TRACT,
        GeographyType.BLOCK_GROUP,
    ]
    location = build_resolved_location(
        geocode_evidence=geocode,
        acceptance_policy=GeocodeAcceptancePolicy("census_acceptance", "v1"),
        geography_evidence=geography,
        manifest=m,
        geocode_source=geocode_source,
        geography_source=geography_source,
        generated_at=NOW,
    )
    assert location.latitude == geocode.candidates[0].coordinates.latitude
    assert location.longitude == geocode.candidates[0].coordinates.longitude
    assert location.formatted_address == "4600 SILVER HILL RD, WASHINGTON, DC, 20233"
    assert location.country_code == "US"
    assert location.source_refs == (geocode_source.source_id, geography_source.source_id)
    assert {r.source_ref for r in location.geography_refs} == {geography_source.source_id}


def test_unaccepted_geocode_cannot_build_resolved_location():
    m = manifest()
    no_match_value = {"result": {"input": {"benchmark": {"benchmarkName": m.geocoder_benchmark}}, "addressMatches": []}}
    raw_g, parsed_g, fp_g = raw_and_parsed(no_match_value)
    geocode = parse_geocode_evidence(parsed_value=no_match_value, parsed_artifact=parsed_g, request_fingerprint=fp_g, manifest=m)
    geo_value = geography_json()
    raw_geo, parsed_geo, fp_geo = raw_and_parsed(geo_value, domain="geography", dataset="census_geocoder_geolookup", vintage=m.geography_vintage, ref="artifact:parsed/geography5")
    geography = parse_geography_evidence(parsed_value=geo_value, parsed_artifact=parsed_geo, request_fingerprint=fp_geo, coordinates=CensusCoordinates(38.8, -76.9), manifest=m)
    p = policy()
    g_source = build_source_metadata(raw_artifact=raw_g, data_quality=DataQualityState.FULL, policy=p)
    geo_source = build_source_metadata(raw_artifact=raw_geo, data_quality=DataQualityState.FULL, policy=p)
    with pytest.raises(ValueError, match="accepted single"):
        build_resolved_location(
            geocode_evidence=geocode,
            acceptance_policy=GeocodeAcceptancePolicy("census_acceptance", "v1"),
            geography_evidence=geography,
            manifest=m,
            geocode_source=g_source,
            geography_source=geo_source,
            generated_at=NOW,
        )


def test_us_v1_does_not_silently_coerce_territory_to_country_us():
    m = manifest()
    value = geography_json()
    value["result"]["geographies"]["States"] = [{"GEOID": "72", "NAME": "Puerto Rico"}]
    raw_geo, parsed_geo, fp_geo = raw_and_parsed(
        value,
        domain="geography",
        dataset="census_geocoder_geolookup",
        vintage=m.geography_vintage,
        ref="artifact:parsed/pr",
    )
    evidence = parse_geography_evidence(
        parsed_value=value,
        parsed_artifact=parsed_geo,
        request_fingerprint=fp_geo,
        coordinates=CensusCoordinates(18.2, -66.5),
        manifest=m,
    )
    source = build_source_metadata(
        raw_artifact=raw_geo,
        data_quality=DataQualityState.FULL,
        policy=policy(),
    )
    with pytest.raises(ValueError, match="50-state"):
        build_geography_refs(evidence=evidence, source_metadata=source)


def test_cbsa_alias_supports_micropolitan_layer_without_fabrication():
    m = CensusGeographyManifest(
        "v1",
        compatibility(),
        core_layer_specs() + optional_layer_specs(),
    )
    value = geography_json()
    value["result"]["geographies"]["Micropolitan Statistical Areas"] = [
        {"GEOID": "12345", "NAME": "Example Micropolitan Statistical Area"}
    ]
    _, parsed, fp = raw_and_parsed(
        value,
        domain="geography",
        dataset="census_geocoder_geolookup",
        vintage=m.geography_vintage,
        ref="artifact:parsed/micro",
    )
    evidence = parse_geography_evidence(
        parsed_value=value,
        parsed_artifact=parsed,
        request_fingerprint=fp,
        coordinates=CensusCoordinates(38.8, -76.9),
        manifest=m,
    )
    cbsa = next(record for record in evidence.records if record.geography_type is GeographyType.CBSA)
    assert cbsa.geoid == "12345"
    assert cbsa.response_layer == "Micropolitan Statistical Areas"


def test_response_alias_interpretation_is_manifest_bound_and_unknown_alias_not_guessed():
    m = manifest()
    value = geography_json()
    value["result"]["geographies"]["State Areas"] = value["result"]["geographies"].pop("States")
    _, parsed, fp = raw_and_parsed(
        value,
        domain="geography",
        dataset="census_geocoder_geolookup",
        vintage=m.geography_vintage,
        ref="artifact:parsed/unknown-alias",
    )
    with pytest.raises(ProviderInvariantError, match="required Census geography layer missing for state"):
        parse_geography_evidence(
            parsed_value=value,
            parsed_artifact=parsed,
            request_fingerprint=fp,
            coordinates=CensusCoordinates(38.8, -76.9),
            manifest=m,
        )

    alias_manifest = CensusGeographyManifest(
        manifest_version=m.manifest_version,
        compatibility=compatibility(compatibility_id=m.compatibility_id, compatibility_version=m.compatibility_version, geocoder_benchmark=m.geocoder_benchmark, geography_vintage=m.geography_vintage),
        supported_layers=(
            CensusGeographyLayerSpec(GeographyType.STATE, 101, ("State Areas",), True),
            *m.supported_layers[1:],
        ),
    )
    alias_evidence = parse_geography_evidence(
        parsed_value=value,
        parsed_artifact=parsed,
        request_fingerprint=fp,
        coordinates=CensusCoordinates(38.8, -76.9),
        manifest=alias_manifest,
    )
    assert GeographyType.STATE in {record.geography_type for record in alias_evidence.records}


@pytest.mark.parametrize(
    "geography_type,response_key",
    [
        (GeographyType.STATE, "States"),
        (GeographyType.COUNTY, "Counties"),
        (GeographyType.TRACT, "Census Tracts"),
        (GeographyType.BLOCK_GROUP, "Census Block Groups"),
    ],
)
def test_missing_required_core_layer_rejected(geography_type, response_key):
    m = manifest()
    value = geography_json()
    value["result"]["geographies"].pop(response_key)
    _, parsed, fp = raw_and_parsed(
        value,
        domain="geography",
        dataset="census_geocoder_geolookup",
        vintage=m.geography_vintage,
        ref=f"artifact:parsed/missing-{geography_type.value}",
    )
    with pytest.raises(ProviderInvariantError, match=f"required Census geography layer missing for {geography_type.value}"):
        parse_geography_evidence(
            parsed_value=value,
            parsed_artifact=parsed,
            request_fingerprint=fp,
            coordinates=CensusCoordinates(38.8, -76.9),
            manifest=m,
        )


def test_missing_optional_zcta_is_omitted():
    m = CensusGeographyManifest("v1", compatibility(), core_layer_specs() + optional_layer_specs())
    value = geography_json(include_metro=False)
    _, parsed, fp = raw_and_parsed(
        value,
        domain="geography",
        dataset="census_geocoder_geolookup",
        vintage=m.geography_vintage,
        ref="artifact:parsed/missing-zcta",
    )
    evidence = parse_geography_evidence(
        parsed_value=value,
        parsed_artifact=parsed,
        request_fingerprint=fp,
        coordinates=CensusCoordinates(38.8, -76.9),
        manifest=m,
    )
    assert GeographyType.ZCTA not in {record.geography_type for record in evidence.records}


def test_unrecognized_alias_for_optional_layer_is_omitted():
    m = CensusGeographyManifest("v1", compatibility(), core_layer_specs() + optional_layer_specs())
    value = geography_json(include_metro=False)
    value["result"]["geographies"]["Unknown Metro Alias"] = [{"GEOID": "99999", "NAME": "Unknown"}]
    _, parsed, fp = raw_and_parsed(
        value,
        domain="geography",
        dataset="census_geocoder_geolookup",
        vintage=m.geography_vintage,
        ref="artifact:parsed/unknown-optional-alias",
    )
    evidence = parse_geography_evidence(
        parsed_value=value,
        parsed_artifact=parsed,
        request_fingerprint=fp,
        coordinates=CensusCoordinates(38.8, -76.9),
        manifest=m,
    )
    assert GeographyType.CBSA not in {record.geography_type for record in evidence.records}
