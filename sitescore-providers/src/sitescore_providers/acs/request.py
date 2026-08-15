"""Pure ACS geography decomposition and deterministic request planning."""

from __future__ import annotations

from sitescore_data import GeographyType
from sitescore_data.schemas.geography import GeographyRef

from ..identity import build_request_fingerprint
from .models import (
    ACS_PROVIDER_KEY,
    ACS_REQUEST_MAX_VARIABLES,
    ACSDatasetManifest,
    ACSGeographyQuery,
    ACSGeographyRequestResult,
    ACSGeographyRequestState,
    ACSQueryPlan,
    ACSRequest,
    ACSUnsupportedGeography,
)

ACS_OPERATION = "acs_detailed_table_query"
ACS_REQUEST_POLICY_ID = "census_acs_request"
ACS_REQUEST_POLICY_VERSION = "v1"


def build_acs_geography_request(*, geography_ref: GeographyRef, manifest: ACSDatasetManifest) -> ACSGeographyRequestResult:
    if not isinstance(geography_ref, GeographyRef):
        raise TypeError("geography_ref must be a GeographyRef")
    if not isinstance(manifest, ACSDatasetManifest):
        raise TypeError("manifest must be an ACSDatasetManifest")
    compat = manifest.geography_compatibility
    if geography_ref.country_code != "US":
        return ACSGeographyRequestResult(
            state=ACSGeographyRequestState.UNSUPPORTED,
            unsupported=ACSUnsupportedGeography(geography_ref.geography_type, geography_ref.geography_id, "country_not_supported"),
        )
    if geography_ref.geography_type not in compat.supported_geography_types:
        return ACSGeographyRequestResult(
            state=ACSGeographyRequestState.UNSUPPORTED,
            unsupported=ACSUnsupportedGeography(geography_ref.geography_type, geography_ref.geography_id, "geography_type_not_supported"),
        )
    if geography_ref.source_version not in compat.accepted_source_versions:
        return ACSGeographyRequestResult(
            state=ACSGeographyRequestState.UNSUPPORTED,
            unsupported=ACSUnsupportedGeography(geography_ref.geography_type, geography_ref.geography_id, "geography_version_not_compatible"),
        )
    geoid = geography_ref.geography_id
    if not geoid.isdigit():
        return ACSGeographyRequestResult(
            state=ACSGeographyRequestState.UNSUPPORTED,
            unsupported=ACSUnsupportedGeography(geography_ref.geography_type, geoid, "invalid_census_geoid"),
        )
    if geography_ref.geography_type is GeographyType.TRACT:
        if len(geoid) != 11:
            return ACSGeographyRequestResult(
                state=ACSGeographyRequestState.UNSUPPORTED,
                unsupported=ACSUnsupportedGeography(geography_ref.geography_type, geoid, "invalid_tract_geoid"),
            )
        state, county, tract = geoid[:2], geoid[2:5], geoid[5:11]
        query = ACSGeographyQuery(
            geography_type=GeographyType.TRACT,
            geography_id=geoid,
            for_clause=f"tract:{tract}",
            in_clause=f"state:{state} county:{county}",
        )
    else:
        if len(geoid) != 12:
            return ACSGeographyRequestResult(
                state=ACSGeographyRequestState.UNSUPPORTED,
                unsupported=ACSUnsupportedGeography(geography_ref.geography_type, geoid, "invalid_block_group_geoid"),
            )
        state, county, tract, block_group = geoid[:2], geoid[2:5], geoid[5:11], geoid[11:12]
        query = ACSGeographyQuery(
            geography_type=GeographyType.BLOCK_GROUP,
            geography_id=geoid,
            for_clause=f"block group:{block_group}",
            in_clause=f"state:{state} county:{county} tract:{tract}",
        )
    return ACSGeographyRequestResult(state=ACSGeographyRequestState.SUPPORTED, query=query)


def build_acs_query_plan(*, geography_ref: GeographyRef, manifest: ACSDatasetManifest) -> ACSQueryPlan | ACSUnsupportedGeography:
    geography_result = build_acs_geography_request(geography_ref=geography_ref, manifest=manifest)
    if geography_result.state is ACSGeographyRequestState.UNSUPPORTED:
        assert geography_result.unsupported is not None
        return geography_result.unsupported
    assert geography_result.query is not None
    geography = geography_result.query

    specs = tuple(sorted(manifest.variable_manifest.variables, key=lambda item: item.semantic_key))
    chunks: list[list[object]] = []
    current: list[object] = []
    current_width = 0
    for spec in specs:
        width = len(spec.request_variable_ids)
        if width > ACS_REQUEST_MAX_VARIABLES:
            raise ValueError(f"variable spec {spec.semantic_key} exceeds one ACS request limit")
        if current and current_width + width > ACS_REQUEST_MAX_VARIABLES:
            chunks.append(current)
            current = []
            current_width = 0
        current.append(spec)
        current_width += width
    if current:
        chunks.append(current)

    requests: list[ACSRequest] = []
    for chunk in chunks:
        semantic_keys = tuple(sorted(item.semantic_key for item in chunk))  # type: ignore[attr-defined]
        variable_ids = tuple(sorted(variable_id for item in chunk for variable_id in item.request_variable_ids))  # type: ignore[attr-defined]
        semantic = {
            "dataset_release": manifest.dataset_release,
            "dataset_identifier": manifest.dataset_identifier,
            "geography_type": geography.geography_type.value,
            "geography_id": geography.geography_id,
            "for": geography.for_clause,
            "in": geography.in_clause,
            "variable_ids": variable_ids,
        }
        fingerprint = build_request_fingerprint(
            provider_key=ACS_PROVIDER_KEY,
            operation=ACS_OPERATION,
            semantic_parameters=semantic,
            dataset=manifest.dataset_identifier,
            dataset_release=manifest.dataset_release,
            policy_id=ACS_REQUEST_POLICY_ID,
            policy_version=ACS_REQUEST_POLICY_VERSION,
        )
        requests.append(
            ACSRequest(
                geography=geography,
                semantic_keys=semantic_keys,
                variable_ids=variable_ids,
                request_fingerprint=fingerprint,
            )
        )
    return ACSQueryPlan(manifest_identity=manifest.identity, geography=geography, requests=tuple(requests))
