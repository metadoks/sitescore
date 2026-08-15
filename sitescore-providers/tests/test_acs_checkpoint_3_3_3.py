from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import json

import pytest

from sitescore_data import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    GeographyType,
    PersistenceClass,
    ScoreEligibility,
)
from sitescore_data.schemas.geography import GeographyRef
from sitescore_providers import (
    ArtifactRef,
    CommercialUseState,
    PersistenceDecision,
    ProviderPolicyDecision,
    RedistributionState,
    build_source_metadata,
    sha256_bytes,
)
from sitescore_providers.acs import (
    ACSAgeCohortSpec,
    ACSClient,
    ACSDatasetManifest,
    ACSGeographyCompatibility,
    ACSProduct,
    ACSRowState,
    ACSStatisticalValueState,
    ACSUnsupportedGeography,
    ACSVariableManifest,
    ACSVariableRole,
    ACSVariableSpec,
    AgeCohortAggregationPolicy,
    build_acs_geography_request,
    build_acs_query_plan,
    build_demographic_snapshot,
    build_evidence_bundle,
    parse_acs_statistical_evidence,
)
from sitescore_providers.acs.builders import ACSDemographicEvidenceError
from sitescore_providers.errors import ProviderInvariantError, ProviderMalformedResponseError
from sitescore_providers.http import HTTPResponse


class MemoryArtifactStore:
    def __init__(self):
        self.values: dict[str, bytes] = {}

    def put(self, *, content_hash, content: bytes):
        ref = ArtifactRef(f"artifact:sha256/{content_hash.digest}")
        self.values[str(ref)] = content
        return ref

    def get(self, artifact_ref):
        return self.values[str(artifact_ref)]

    def exists(self, artifact_ref):
        return str(artifact_ref) in self.values


class FakeTransport:
    def __init__(self, response: HTTPResponse):
        self.response = response
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return self.response


@pytest.fixture
def geography_ref():
    return GeographyRef(
        geography_type=GeographyType.BLOCK_GROUP,
        geography_id="060750101001",
        name="Block Group 1; Census Tract 101; San Francisco County; California",
        country_code="US",
        source_ref="source.census_geo",
        source_version="census2020_v1",
    )


@pytest.fixture
def tract_ref():
    return GeographyRef(
        geography_type=GeographyType.TRACT,
        geography_id="06075010100",
        name="Census Tract 101; San Francisco County; California",
        country_code="US",
        source_ref="source.census_geo",
        source_version="census2020_v1",
    )


def variable_specs():
    return (
        ACSVariableSpec("total_population", ACSVariableRole.TOTAL_POPULATION, "B01003_001E", "B01003_001M", "B01003_001EA", "B01003_001MA", "people"),
        ACSVariableSpec("age_0_24_a", ACSVariableRole.AGE_COMPONENT, "B01001_003E", "B01001_003M", "B01001_003EA", "B01001_003MA", "people", "age"),
        ACSVariableSpec("age_0_24_b", ACSVariableRole.AGE_COMPONENT, "B01001_027E", "B01001_027M", "B01001_027EA", "B01001_027MA", "people", "age"),
        ACSVariableSpec("age_25_plus_a", ACSVariableRole.AGE_COMPONENT, "B01001_011E", "B01001_011M", "B01001_011EA", "B01001_011MA", "people", "age"),
        ACSVariableSpec("age_25_plus_b", ACSVariableRole.AGE_COMPONENT, "B01001_035E", "B01001_035M", "B01001_035EA", "B01001_035MA", "people", "age"),
        ACSVariableSpec("household_income", ACSVariableRole.HOUSEHOLD_INCOME, "B19013_001E", "B19013_001M", "B19013_001EA", "B19013_001MA", "usd_2024"),
    )


@pytest.fixture
def variable_manifest():
    return ACSVariableManifest("site_demographics", "v1", variable_specs())


@pytest.fixture
def geo_compat():
    return ACSGeographyCompatibility(
        compatibility_id="acs_2024_census2020",
        compatibility_version="v1",
        accepted_source_versions=("census2020_v1",),
        supported_geography_types=(GeographyType.TRACT, GeographyType.BLOCK_GROUP),
    )


@pytest.fixture
def manifest(variable_manifest, geo_compat):
    return ACSDatasetManifest(
        manifest_version="v1",
        dataset_release="2024",
        vintage="2020-2024",
        product=ACSProduct.DETAILED_TABLES,
        dataset_identifier="acs/acs5",
        variable_manifest=variable_manifest,
        geography_compatibility=geo_compat,
        parser_version="v1",
    )


@pytest.fixture
def age_policy():
    return AgeCohortAggregationPolicy(
        policy_id="standard_age_v1",
        policy_version="v1",
        cohorts=(
            ACSAgeCohortSpec("under_25", 0, 25, ("age_0_24_a", "age_0_24_b")),
            ACSAgeCohortSpec("age_25_plus", 25, None, ("age_25_plus_a", "age_25_plus_b")),
        ),
    )


@pytest.fixture
def persistence_policy():
    persistence = PersistenceDecision(
        policy_id="census_public_api",
        policy_version="v1",
        persistence_class=PersistenceClass.PERSIST,
        reason_codes=("public_statistical_data",),
    )
    return ProviderPolicyDecision(
        policy_id="census_public_api",
        policy_version="v1",
        persistence=persistence,
        attribution_required=True,
        redistribution_state=RedistributionState.RESTRICTED,
        commercial_use_state=CommercialUseState.ALLOWED,
        license_class="census_api_terms",
        policy_reference="policy:census-api-terms/2026-04-14",
    )


def test_manifest_identity_deterministic(manifest):
    assert manifest.identity == manifest.identity


def test_variable_manifest_change_changes_identity(variable_manifest):
    changed = list(variable_specs())
    old = changed[-1]
    changed[-1] = ACSVariableSpec(old.semantic_key, old.role, "B19013_999E", "B19013_999M", "B19013_999EA", "B19013_999MA", old.unit)
    other = ACSVariableManifest("site_demographics", "v1", tuple(changed))
    assert other.identity != variable_manifest.identity


def test_release_change_changes_dataset_manifest_identity(manifest):
    other = ACSDatasetManifest("v1", "2023", "2019-2023", ACSProduct.DETAILED_TABLES, "acs/acs5", manifest.variable_manifest, manifest.geography_compatibility, "v1")
    assert other.identity != manifest.identity


def test_variable_order_normalized_in_manifest_identity(variable_manifest):
    reverse = ACSVariableManifest("site_demographics", "v1", tuple(reversed(variable_manifest.variables)))
    assert reverse.identity == variable_manifest.identity


def test_current_and_latest_release_rejected(manifest):
    with pytest.raises(ValueError):
        ACSDatasetManifest("v1", "latest", "2020-2024", ACSProduct.DETAILED_TABLES, "acs/acs5", manifest.variable_manifest, manifest.geography_compatibility, "v1")


def test_block_group_request_construction(geography_ref, manifest):
    result = build_acs_geography_request(geography_ref=geography_ref, manifest=manifest)
    assert result.query.for_clause == "block group:1"
    assert result.query.in_clause == "state:06 county:075 tract:010100"


def test_tract_request_construction(tract_ref, manifest):
    result = build_acs_geography_request(geography_ref=tract_ref, manifest=manifest)
    assert result.query.for_clause == "tract:010100"
    assert result.query.in_clause == "state:06 county:075"


def test_unsupported_geography_is_typed_not_execution_failure(manifest):
    county = GeographyRef(GeographyType.COUNTY, "06075", "San Francisco County", "US", "source.census_geo", "census2020_v1")
    result = build_acs_geography_request(geography_ref=county, manifest=manifest)
    assert result.unsupported.reason_code == "geography_type_not_supported"


def test_no_silent_bg_to_tract_fallback(geography_ref, manifest):
    incompatible = GeographyRef(GeographyType.BLOCK_GROUP, geography_ref.geography_id, geography_ref.name, "US", geography_ref.source_ref, "other_vintage")
    result = build_acs_query_plan(geography_ref=incompatible, manifest=manifest)
    assert isinstance(result, ACSUnsupportedGeography)
    assert result.geography_type is GeographyType.BLOCK_GROUP


def test_request_plan_is_deterministic_and_variables_sorted(geography_ref, manifest):
    plan1 = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    plan2 = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    assert plan1 == plan2
    for request in plan1.requests:
        assert request.variable_ids == tuple(sorted(request.variable_ids))
        assert len(request.variable_ids) <= 50


def test_large_manifest_chunks_without_splitting_variable_spec(geography_ref, geo_compat):
    specs = [ACSVariableSpec("total_population", ACSVariableRole.TOTAL_POPULATION, "T_001E", "T_001M", "T_001EA", "T_001MA", "people")]
    for i in range(13):
        specs.append(ACSVariableSpec(f"age_{i}", ACSVariableRole.AGE_COMPONENT, f"A{i}_001E", f"A{i}_001M", f"A{i}_001EA", f"A{i}_001MA", "people", "age"))
    specs.append(ACSVariableSpec("household_income", ACSVariableRole.HOUSEHOLD_INCOME, "I_001E", "I_001M", "I_001EA", "I_001MA", "usd"))
    vm = ACSVariableManifest("chunked", "v1", tuple(specs))
    m = ACSDatasetManifest("v1", "2024", "2020-2024", ACSProduct.DETAILED_TABLES, "acs/acs5", vm, geo_compat, "v1")
    plan = build_acs_query_plan(geography_ref=geography_ref, manifest=m)
    assert len(plan.requests) == 2
    assert all(len(r.variable_ids) <= 50 for r in plan.requests)
    assert all(len(set(r.semantic_keys)) == len(r.semantic_keys) for r in plan.requests)


def _payload(request, spec_by_key, *, overrides=None):
    overrides = overrides or {}
    header = list(request.variable_ids) + ["state", "county", "tract", "block group"]
    values = {}
    defaults = {
        "total_population": ("100", "5", None, None),
        "age_0_24_a": ("20", "2", None, None),
        "age_0_24_b": ("20", "2", None, None),
        "age_25_plus_a": ("30", "3", None, None),
        "age_25_plus_b": ("30", "3", None, None),
        "household_income": ("80000", "5000", None, None),
    }
    defaults.update(overrides)
    for key in request.semantic_keys:
        spec = spec_by_key[key]
        e, m, ea, ma = defaults[key]
        values[spec.estimate_variable_id] = e
        values[spec.margin_of_error_variable_id] = m
        if spec.estimate_annotation_variable_id:
            values[spec.estimate_annotation_variable_id] = ea
        if spec.margin_of_error_annotation_variable_id:
            values[spec.margin_of_error_annotation_variable_id] = ma
    row = [values[col] for col in request.variable_ids] + ["06", "075", "010100", "1"]
    return [header, row]


def _acquire_parse(*, request, manifest, persistence_policy, payload, api_key="secret-key"):
    store = MemoryArtifactStore()
    response = HTTPResponse(200, (), json.dumps(payload, separators=(",", ":")).encode())
    transport = FakeTransport(response)
    client = ACSClient(transport=transport, artifact_store=store, api_key=api_key)
    acquired = client.acquire(request=request, manifest=manifest, persistence_policy=persistence_policy, retrieved_at=datetime(2026, 8, 12, tzinfo=timezone.utc))
    parsed = client.parse_success(acquisition=acquired, manifest=manifest)
    return client, transport, acquired, parsed


def test_api_key_excluded_from_request_fingerprint(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    _, t1, a1, _ = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload, api_key="key-one")
    _, t2, a2, _ = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload, api_key="key-two")
    assert a1.artifact.request_fingerprint == a2.artifact.request_fingerprint
    assert dict(t1.requests[0].query)["key"] == "key-one"
    assert "key-one" not in str(a1.artifact.request_fingerprint)


def test_valid_estimate_and_moe_parse(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
    assert result.row_state is ACSRowState.FOUND
    assert all(item.estimate_state is ACSStatisticalValueState.VALUE for item in result.evidence)
    assert all(item.margin_of_error_state is ACSStatisticalValueState.VALUE for item in result.evidence)


@pytest.mark.parametrize(
    "raw,annotation,expected",
    [
        ("-666666666", "-", ACSStatisticalValueState.MISSING),
        ("-999999999", "N", ACSStatisticalValueState.SUPPRESSED),
        ("-888888888", "(X)", ACSStatisticalValueState.NOT_APPLICABLE),
    ],
)
def test_official_estimate_special_values_not_numeric(geography_ref, manifest, persistence_policy, raw, annotation, expected):
    request = next(r for r in build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests if "household_income" in r.semantic_keys)
    payload = _payload(request, manifest.variable_manifest.by_semantic_key, overrides={"household_income": (raw, "5000", annotation, None)})
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
    item = next(e for e in result.evidence if e.semantic_key == "household_income")
    assert item.estimate is None
    assert item.estimate_state is expected
    assert item.estimate_raw_value == raw
    assert item.estimate_annotation == annotation


def test_controlled_moe_preserved_as_special_not_zero(geography_ref, manifest, persistence_policy):
    request = next(r for r in build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests if "household_income" in r.semantic_keys)
    payload = _payload(request, manifest.variable_manifest.by_semantic_key, overrides={"household_income": ("80000", "-555555555", None, "*****")})
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
    item = next(e for e in result.evidence if e.semantic_key == "household_income")
    assert item.margin_of_error is None
    assert item.margin_of_error_state is ACSStatisticalValueState.CONTROLLED
    assert item.margin_of_error_raw_value == "-555555555"


def test_annotated_numeric_value_is_not_plain_value(geography_ref, manifest, persistence_policy):
    request = next(r for r in build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests if "household_income" in r.semantic_keys)
    payload = _payload(request, manifest.variable_manifest.by_semantic_key, overrides={"household_income": ("250000", "5000", "median+", None)})
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
    item = next(e for e in result.evidence if e.semantic_key == "household_income")
    assert item.estimate is None
    assert item.estimate_state is ACSStatisticalValueState.ANNOTATED


def test_malformed_header_duplicate_rejected(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    payload[0][1] = payload[0][0]
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    with pytest.raises(ProviderInvariantError):
        parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)


def test_missing_requested_column_rejected(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    payload[0].pop(0); payload[1].pop(0)
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    with pytest.raises(ProviderMalformedResponseError):
        parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)


def test_geography_mismatch_rejected(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    payload[1][-1] = "2"
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    with pytest.raises(ProviderInvariantError):
        parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)


def test_no_data_row_is_typed_not_zero(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    payload = [payload[0]]
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
    assert result.row_state is ACSRowState.NO_DATA
    assert result.evidence == ()


def test_raw_parsed_statistical_lineage(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    _, _, acquired, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
    assert all(item.raw_content_hash == acquired.artifact.content_hash for item in result.evidence)
    assert all(item.parsed_artifact_identity == parsed.parsed_artifact.identity for item in result.evidence)
    assert all(item.margin_of_error is not None for item in result.evidence)


def test_evidence_is_immutable(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    item = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest).evidence[0]
    with pytest.raises(FrozenInstanceError):
        item.estimate = 1


def test_overlapping_cohort_policy_rejected():
    with pytest.raises(ValueError):
        AgeCohortAggregationPolicy("bad", "v1", (ACSAgeCohortSpec("a", 0, 30, ("age_0_24_a",)), ACSAgeCohortSpec("b", 25, None, ("age_25_plus_a",))))


def test_gap_policy_rejected_by_default():
    with pytest.raises(ValueError):
        AgeCohortAggregationPolicy("bad", "v1", (ACSAgeCohortSpec("a", 0, 20, ("age_0_24_a",)), ACSAgeCohortSpec("b", 25, None, ("age_25_plus_a",))))


def test_incomplete_age_variable_mapping_rejected(variable_manifest):
    policy = AgeCohortAggregationPolicy("bad", "v1", (ACSAgeCohortSpec("all", 0, None, ("age_0_24_a", "age_25_plus_a")),), require_contiguous_intervals=True, require_all_age_components=True)
    with pytest.raises(ValueError):
        policy.validate_against(variable_manifest)


def _full_bundle_and_sources(geography_ref, manifest, persistence_policy):
    plan = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    evidence = []
    sources = []
    for request in plan.requests:
        payload = _payload(request, manifest.variable_manifest.by_semantic_key)
        _, _, acquired, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
        result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
        evidence.extend(result.evidence)
        sources.append(build_source_metadata(raw_artifact=acquired.artifact, data_quality=DataQualityState.FULL, policy=persistence_policy, source_reference="https://api.census.gov/data/2024/acs/acs5"))
    return build_evidence_bundle(geography_ref=geography_ref, manifest=manifest, evidence=tuple(evidence)), tuple(sources)


def test_demographic_snapshot_construction(geography_ref, manifest, persistence_policy, age_policy):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    snapshot, lineage = build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=sources, generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc))
    assert snapshot.total_population.value == 100
    assert tuple(c.population for c in snapshot.age_cohorts) == (40, 60)
    assert tuple(c.population_share for c in snapshot.age_cohorts) == (0.4, 0.6)
    assert snapshot.household_income.value == 80000
    assert snapshot.total_population.score_eligibility is ScoreEligibility.DIAGNOSTIC_ONLY
    assert snapshot.total_population.calibration_state is CalibrationState.UNCALIBRATED
    assert snapshot.data_quality is DataQualityState.FULL
    assert lineage.total_population_evidence_identity == bundle.by_semantic_key["total_population"].identity
    assert len(lineage.cohort_evidence_identities) == 2


def test_source_lineage_preserves_all_raw_sources(geography_ref, manifest, persistence_policy, age_policy):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    snapshot, lineage = build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=sources, generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc))
    assert set(snapshot.source_refs) == {source.source_id for source in sources}
    assert set(lineage.source_ids) == set(snapshot.source_refs)
    assert all(item.margin_of_error is not None for item in bundle.evidence)


def test_missing_age_evidence_never_becomes_zero(geography_ref, manifest, persistence_policy, age_policy):
    plan = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    evidence = []
    sources = []
    for request in plan.requests:
        overrides = {"age_0_24_a": ("-666666666", "2", "-", None)} if "age_0_24_a" in request.semantic_keys else {}
        payload = _payload(request, manifest.variable_manifest.by_semantic_key, overrides=overrides)
        _, _, acquired, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
        result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
        evidence.extend(result.evidence)
        sources.append(build_source_metadata(raw_artifact=acquired.artifact, data_quality=DataQualityState.FULL, policy=persistence_policy))
    bundle = build_evidence_bundle(geography_ref=geography_ref, manifest=manifest, evidence=tuple(evidence))
    with pytest.raises(ACSDemographicEvidenceError):
        build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=tuple(sources), generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc))


def test_household_income_special_maps_to_non_numeric_metric(geography_ref, manifest, persistence_policy, age_policy):
    plan = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    evidence = []
    sources = []
    for request in plan.requests:
        overrides = {"household_income": ("-999999999", "-999999999", "N", "N")} if "household_income" in request.semantic_keys else {}
        payload = _payload(request, manifest.variable_manifest.by_semantic_key, overrides=overrides)
        _, _, acquired, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
        result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
        evidence.extend(result.evidence)
        sources.append(build_source_metadata(raw_artifact=acquired.artifact, data_quality=DataQualityState.FULL, policy=persistence_policy))
    bundle = build_evidence_bundle(geography_ref=geography_ref, manifest=manifest, evidence=tuple(evidence))
    snapshot, _ = build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=tuple(sources), generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc))
    assert snapshot.household_income.value is None
    assert snapshot.household_income.availability is AvailabilityState.MISSING
    assert snapshot.data_quality is DataQualityState.DEGRADED


def test_cohort_moe_is_not_silently_aggregated(geography_ref, manifest, persistence_policy, age_policy):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    snapshot, lineage = build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=sources, generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc))
    assert not hasattr(snapshot.age_cohorts[0], "margin_of_error")
    source_ids = lineage.cohort_evidence_identities[0][1]
    assert len(source_ids) == 2
    assert all(bundle.by_semantic_key[key].margin_of_error is not None for key in ("age_0_24_a", "age_0_24_b"))


def test_variable_suffix_semantics_are_explicitly_validated():
    with pytest.raises(ValueError):
        ACSVariableSpec("bad", ACSVariableRole.AGE_COMPONENT, "B01001_003M", "B01001_003E", None, None, "people", "age")
    with pytest.raises(ValueError):
        ACSVariableSpec("bad", ACSVariableRole.AGE_COMPONENT, "B01001_003E", "B01001_004M", None, None, "people", "age")


def test_variable_spec_is_atomic_at_every_chunk_boundary(geography_ref, geo_compat):
    specs = [ACSVariableSpec("total_population", ACSVariableRole.TOTAL_POPULATION, "T_001E", "T_001M", "T_001EA", "T_001MA", "people")]
    for i in range(13):
        specs.append(ACSVariableSpec(f"age_{i}", ACSVariableRole.AGE_COMPONENT, f"A{i}_001E", f"A{i}_001M", f"A{i}_001EA", f"A{i}_001MA", "people", "age"))
    specs.append(ACSVariableSpec("household_income", ACSVariableRole.HOUSEHOLD_INCOME, "I_001E", "I_001M", "I_001EA", "I_001MA", "usd"))
    vm = ACSVariableManifest("atomic", "v1", tuple(specs))
    manifest = ACSDatasetManifest("v1", "2024", "2020-2024", ACSProduct.DETAILED_TABLES, "acs/acs5", vm, geo_compat, "v1")
    plan = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    request_by_key = {key: request for request in plan.requests for key in request.semantic_keys}
    for spec in vm.variables:
        request = request_by_key[spec.semantic_key]
        assert set(spec.request_variable_ids).issubset(request.variable_ids)
        assert len(request.variable_ids) <= 50


def test_query_plan_stable_under_manifest_input_order(geography_ref, manifest):
    reversed_vm = ACSVariableManifest(
        manifest.variable_manifest.manifest_id,
        manifest.variable_manifest.manifest_version,
        tuple(reversed(manifest.variable_manifest.variables)),
    )
    reversed_manifest = ACSDatasetManifest(
        manifest.manifest_version, manifest.dataset_release, manifest.vintage, manifest.product,
        manifest.dataset_identifier, reversed_vm, manifest.geography_compatibility, manifest.parser_version,
    )
    plan1 = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    plan2 = build_acs_query_plan(geography_ref=geography_ref, manifest=reversed_manifest)
    assert tuple((r.semantic_keys, r.variable_ids, r.request_fingerprint) for r in plan1.requests) == tuple(
        (r.semantic_keys, r.variable_ids, r.request_fingerprint) for r in plan2.requests
    )


def test_evidence_preserves_exact_originating_column_ids(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    item = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest).evidence[0]
    spec = manifest.variable_manifest.by_semantic_key[item.semantic_key]
    assert item.estimate_variable_id == spec.estimate_variable_id
    assert item.margin_of_error_variable_id == spec.margin_of_error_variable_id
    assert item.estimate_annotation_variable_id == spec.estimate_annotation_variable_id
    assert item.margin_of_error_annotation_variable_id == spec.margin_of_error_annotation_variable_id
    assert item.request_fingerprint == request.request_fingerprint


def test_cross_chunk_bundle_rejects_dataset_release_mismatch(geography_ref, manifest, persistence_policy):
    bundle, _ = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    tampered = replace(bundle.evidence[0], dataset_release="2023")
    with pytest.raises(ValueError):
        build_evidence_bundle(geography_ref=geography_ref, manifest=manifest, evidence=(tampered,) + bundle.evidence[1:])


def test_cross_chunk_bundle_rejects_geography_mismatch(geography_ref, manifest, persistence_policy):
    bundle, _ = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    tampered = replace(bundle.evidence[0], geography_id="060750101002")
    with pytest.raises(ValueError):
        build_evidence_bundle(geography_ref=geography_ref, manifest=manifest, evidence=(tampered,) + bundle.evidence[1:])


def test_cross_chunk_bundle_rejects_wrong_query_plan_fingerprint(geography_ref, manifest, persistence_policy):
    bundle, _ = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    first = bundle.evidence[0]
    wrong_fingerprint = replace(first.request_fingerprint, grammar_version="v999")
    tampered = replace(first, request_fingerprint=wrong_fingerprint)
    with pytest.raises(ValueError):
        build_evidence_bundle(geography_ref=geography_ref, manifest=manifest, evidence=(tampered,) + bundle.evidence[1:])


def test_cross_chunk_bundle_rejects_originating_column_mismatch(geography_ref, manifest, persistence_policy):
    bundle, _ = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    first = bundle.evidence[0]
    tampered = replace(first, estimate_variable_id=bundle.evidence[1].estimate_variable_id)
    with pytest.raises(ValueError):
        build_evidence_bundle(geography_ref=geography_ref, manifest=manifest, evidence=(tampered,) + bundle.evidence[1:])


def test_nonempty_annotation_never_exposes_numeric_value(geography_ref, manifest, persistence_policy):
    request = next(r for r in build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests if "household_income" in r.semantic_keys)
    payload = _payload(request, manifest.variable_manifest.by_semantic_key, overrides={"household_income": ("250000", "5000", "unknown-annotation", "unknown-moe-annotation")})
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    item = next(e for e in parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest).evidence if e.semantic_key == "household_income")
    assert item.estimate is None
    assert item.margin_of_error is None
    assert item.estimate_state is ACSStatisticalValueState.ANNOTATED
    assert item.margin_of_error_state is ACSStatisticalValueState.ANNOTATED


def test_special_sentinel_precedes_annotation_without_becoming_numeric(geography_ref, manifest, persistence_policy):
    request = next(r for r in build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests if "household_income" in r.semantic_keys)
    payload = _payload(request, manifest.variable_manifest.by_semantic_key, overrides={"household_income": ("-666666666", "-555555555", "some-annotation", "some-annotation")})
    _, _, _, parsed = _acquire_parse(request=request, manifest=manifest, persistence_policy=persistence_policy, payload=payload)
    item = next(e for e in parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest).evidence if e.semantic_key == "household_income")
    assert item.estimate is None and item.estimate_state is ACSStatisticalValueState.MISSING
    assert item.margin_of_error is None and item.margin_of_error_state is ACSStatisticalValueState.CONTROLLED


def test_snapshot_primitive_determinism_requires_same_generated_at(geography_ref, manifest, persistence_policy, age_policy):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    t1 = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 12, 12, 1, tzinfo=timezone.utc)
    snapshot1, lineage1 = build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=sources, generated_at=t1)
    snapshot1b, lineage1b = build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=sources, generated_at=t1)
    snapshot2, lineage2 = build_demographic_snapshot(bundle=bundle, manifest=manifest, age_policy=age_policy, source_metadata=sources, generated_at=t2)
    assert snapshot1 == snapshot1b
    assert lineage1.snapshot_identity == lineage1b.snapshot_identity
    assert snapshot1 != snapshot2
    # Provider lineage identity deliberately excludes generated_at; it identifies
    # the same demographic derivation, not the full serialized snapshot primitive.
    assert lineage1.snapshot_identity == lineage2.snapshot_identity

# Final 3.3-3 lineage/state hardening regressions.
def _parsed_item(geography_ref, manifest, persistence_policy):
    request = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests[0]
    payload = _payload(request, manifest.variable_manifest.by_semantic_key)
    _, _, acquired, parsed = _acquire_parse(
        request=request,
        manifest=manifest,
        persistence_policy=persistence_policy,
        payload=payload,
    )
    result = parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest)
    return request, acquired, parsed, result.evidence[0]


def test_parser_rejects_raw_request_fingerprint_mismatch(geography_ref, manifest, persistence_policy):
    request, _, parsed, _ = _parsed_item(geography_ref, manifest, persistence_policy)
    wrong_request = replace(
        request,
        request_fingerprint=replace(request.request_fingerprint, grammar_version="v999"),
    )
    with pytest.raises(ProviderInvariantError):
        parse_acs_statistical_evidence(response=parsed, request=wrong_request, manifest=manifest)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dataset_release", "2023"),
        ("vintage", "2019-2023"),
        ("dataset_identifier", "acs/acs5/other"),
    ],
)
def test_parser_rejects_raw_provider_identity_manifest_mismatch(
    geography_ref, manifest, persistence_policy, field, value
):
    request, _, parsed, _ = _parsed_item(geography_ref, manifest, persistence_policy)
    kwargs = {
        "manifest_version": manifest.manifest_version,
        "dataset_release": manifest.dataset_release,
        "vintage": manifest.vintage,
        "product": manifest.product,
        "dataset_identifier": manifest.dataset_identifier,
        "variable_manifest": manifest.variable_manifest,
        "geography_compatibility": manifest.geography_compatibility,
        "parser_version": manifest.parser_version,
    }
    kwargs[field] = value
    other_manifest = ACSDatasetManifest(**kwargs)
    with pytest.raises(ProviderInvariantError):
        parse_acs_statistical_evidence(response=parsed, request=request, manifest=other_manifest)


def test_parsed_response_rejects_unrelated_raw_content_hash(geography_ref, manifest, persistence_policy):
    _, _, parsed, _ = _parsed_item(geography_ref, manifest, persistence_policy)
    bad_parsed_artifact = replace(parsed.parsed_artifact, raw_content_hash=sha256_bytes(b"unrelated raw"))
    with pytest.raises(ValueError):
        replace(parsed, parsed_artifact=bad_parsed_artifact)


@pytest.mark.parametrize("field,value", [("parser_id", "wrong_parser"), ("parser_version", "v999")])
def test_parser_rejects_wrong_parsed_parser_identity(
    geography_ref, manifest, persistence_policy, field, value
):
    request, _, parsed, _ = _parsed_item(geography_ref, manifest, persistence_policy)
    bad_parsed = replace(parsed, parsed_artifact=replace(parsed.parsed_artifact, **{field: value}))
    with pytest.raises(ProviderInvariantError):
        parse_acs_statistical_evidence(response=bad_parsed, request=request, manifest=manifest)


def test_canonical_acquire_parse_evidence_lineage_path_remains_valid(geography_ref, manifest, persistence_policy):
    request, acquired, parsed, item = _parsed_item(geography_ref, manifest, persistence_policy)
    assert acquired.artifact.request_fingerprint == request.request_fingerprint
    assert parsed.parsed_artifact.raw_content_hash == acquired.artifact.content_hash
    assert item.request_fingerprint == request.request_fingerprint
    assert item.raw_content_hash == acquired.artifact.content_hash


@pytest.mark.parametrize("axis", ["estimate", "margin_of_error"])
def test_statistical_evidence_value_state_requires_numeric_value(
    geography_ref, manifest, persistence_policy, axis
):
    _, _, _, item = _parsed_item(geography_ref, manifest, persistence_policy)
    with pytest.raises(ValueError):
        replace(item, **{axis: None})


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), True])
@pytest.mark.parametrize("axis", ["estimate", "margin_of_error"])
def test_statistical_evidence_value_state_rejects_nonfinite_and_bool(
    geography_ref, manifest, persistence_policy, axis, bad
):
    _, _, _, item = _parsed_item(geography_ref, manifest, persistence_policy)
    with pytest.raises(ValueError):
        replace(item, **{axis: bad})


@pytest.mark.parametrize(
    "axis,state_field",
    [("estimate", "estimate_state"), ("margin_of_error", "margin_of_error_state")],
)
def test_statistical_evidence_non_value_state_rejects_numeric_value(
    geography_ref, manifest, persistence_policy, axis, state_field
):
    _, _, _, item = _parsed_item(geography_ref, manifest, persistence_policy)
    with pytest.raises(ValueError):
        replace(item, **{state_field: ACSStatisticalValueState.MISSING, axis: 1})


@pytest.mark.parametrize(
    "axis,state_field,annotation_field",
    [
        ("estimate", "estimate_state", "estimate_annotation"),
        ("margin_of_error", "margin_of_error_state", "margin_of_error_annotation"),
    ],
)
def test_statistical_evidence_annotated_state_requires_annotation(
    geography_ref, manifest, persistence_policy, axis, state_field, annotation_field
):
    _, _, _, item = _parsed_item(geography_ref, manifest, persistence_policy)
    with pytest.raises(ValueError):
        replace(
            item,
            **{state_field: ACSStatisticalValueState.ANNOTATED, axis: None, annotation_field: None},
        )


@pytest.mark.parametrize(
    "annotation_field",
    ["estimate_annotation", "margin_of_error_annotation"],
)
def test_statistical_evidence_value_state_rejects_nonempty_annotation(
    geography_ref, manifest, persistence_policy, annotation_field
):
    _, _, _, item = _parsed_item(geography_ref, manifest, persistence_policy)
    with pytest.raises(ValueError):
        replace(item, **{annotation_field: "not-empty"})


def test_statistical_evidence_valid_value_axes_accept(geography_ref, manifest, persistence_policy):
    _, _, _, item = _parsed_item(geography_ref, manifest, persistence_policy)
    assert item.estimate_state is ACSStatisticalValueState.VALUE
    assert item.margin_of_error_state is ACSStatisticalValueState.VALUE
    assert item.estimate is not None
    assert item.margin_of_error is not None


def test_estimate_value_and_controlled_moe_axes_are_independent(geography_ref, manifest, persistence_policy):
    request = next(
        r for r in build_acs_query_plan(geography_ref=geography_ref, manifest=manifest).requests
        if "household_income" in r.semantic_keys
    )
    payload = _payload(
        request,
        manifest.variable_manifest.by_semantic_key,
        overrides={"household_income": ("80000", "-555555555", None, "*****")},
    )
    _, _, _, parsed = _acquire_parse(
        request=request,
        manifest=manifest,
        persistence_policy=persistence_policy,
        payload=payload,
    )
    item = next(
        e for e in parse_acs_statistical_evidence(response=parsed, request=request, manifest=manifest).evidence
        if e.semantic_key == "household_income"
    )
    assert item.estimate_state is ACSStatisticalValueState.VALUE
    assert item.estimate == 80000
    assert item.margin_of_error_state is ACSStatisticalValueState.CONTROLLED
    assert item.margin_of_error is None

# Freeze-boundary hardening regressions FINAL-003 / FINAL-004.
def test_demographic_builder_revalidates_direct_bundle_request_fingerprint(
    geography_ref, manifest, persistence_policy, age_policy
):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    first = bundle.evidence[0]
    bad = replace(
        first,
        request_fingerprint=replace(first.request_fingerprint, grammar_version="v999"),
    )
    fabricated = type(bundle)(
        geography_ref=bundle.geography_ref,
        manifest_identity=bundle.manifest_identity,
        evidence=(bad,) + bundle.evidence[1:],
    )
    with pytest.raises(ValueError, match="request fingerprint"):
        build_demographic_snapshot(
            bundle=fabricated,
            manifest=manifest,
            age_policy=age_policy,
            source_metadata=sources,
            generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        )


def test_demographic_builder_revalidates_direct_bundle_originating_columns(
    geography_ref, manifest, persistence_policy, age_policy
):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    first = bundle.evidence[0]
    bad = replace(
        first,
        estimate_variable_id="X999_001E",
        margin_of_error_variable_id="X999_001M",
        estimate_annotation_variable_id="X999_001EA",
        margin_of_error_annotation_variable_id="X999_001MA",
    )
    fabricated = type(bundle)(
        geography_ref=bundle.geography_ref,
        manifest_identity=bundle.manifest_identity,
        evidence=(bad,) + bundle.evidence[1:],
    )
    with pytest.raises(ValueError, match="originating ACS columns"):
        build_demographic_snapshot(
            bundle=fabricated,
            manifest=manifest,
            age_policy=age_policy,
            source_metadata=sources,
            generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        )


def test_demographic_builder_accepts_canonical_bundle_after_revalidation(
    geography_ref, manifest, persistence_policy, age_policy
):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    snapshot, _ = build_demographic_snapshot(
        bundle=bundle,
        manifest=manifest,
        age_policy=age_policy,
        source_metadata=sources,
        generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    assert snapshot.total_population.value == 100


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "unrelated_provider"),
        ("dataset", "unrelated/dataset"),
        ("dataset_release", "2023"),
        ("vintage", "2019-2023"),
        ("schema_version", "other_schema"),
    ],
)
def test_demographic_builder_rejects_source_metadata_semantic_identity_mismatch(
    geography_ref, manifest, persistence_policy, age_policy, field, value
):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    # Preserve the exact raw content hash: only semantic source identity is wrong.
    bad_sources = (replace(sources[0], **{field: value}),) + sources[1:]
    with pytest.raises(ValueError, match="active dataset manifest"):
        build_demographic_snapshot(
            bundle=bundle,
            manifest=manifest,
            age_policy=age_policy,
            source_metadata=bad_sources,
            generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        )


def test_demographic_builder_accepts_correct_acs_source_metadata(
    geography_ref, manifest, persistence_policy, age_policy
):
    bundle, sources = _full_bundle_and_sources(geography_ref, manifest, persistence_policy)
    snapshot, lineage = build_demographic_snapshot(
        bundle=bundle,
        manifest=manifest,
        age_policy=age_policy,
        source_metadata=sources,
        generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    assert set(snapshot.source_refs) == {source.source_id for source in sources}
    assert set(lineage.source_ids) == set(snapshot.source_refs)
