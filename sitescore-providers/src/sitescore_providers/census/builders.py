"""Pure mappings from accepted Census evidence into frozen SiteScore geography contracts."""

from __future__ import annotations

from datetime import datetime

from sitescore_data import GeographyType
from sitescore_data.schemas.common import SourceMetadata
from sitescore_data.schemas.geography import GeographyRef, ResolvedLocation

from .._validation import require_aware_datetime, require_nonempty_text
from .models import (
    CENSUS_COUNTRY_CODE,
    CensusGeocodeEvidence,
    CensusGeographyEvidence,
    CensusGeographyManifest,
    CensusMatchState,
    US_STATE_AND_DC_FIPS,
)
from .policy import GeocodeAcceptanceDecision, GeocodeAcceptancePolicy


def build_geography_refs(
    *,
    evidence: CensusGeographyEvidence,
    source_metadata: SourceMetadata,
) -> tuple[GeographyRef, ...]:
    if not isinstance(evidence, CensusGeographyEvidence):
        raise TypeError("evidence must be CensusGeographyEvidence")
    if not isinstance(source_metadata, SourceMetadata):
        raise TypeError("source_metadata must be SourceMetadata")
    refs: list[GeographyRef] = []
    state_records = tuple(record for record in evidence.records if record.geography_type is GeographyType.STATE)
    if not state_records:
        return ()
    if state_records[0].geoid not in US_STATE_AND_DC_FIPS:
        raise ValueError("Census geography is outside the 50-state + DC US V1 scope")
    refs.append(
        GeographyRef(
            geography_type=GeographyType.COUNTRY,
            geography_id="US",
            name="United States",
            country_code=CENSUS_COUNTRY_CODE,
            source_ref=source_metadata.source_id,
            source_version=evidence.geography_vintage,
        )
    )
    for record in evidence.records:
        refs.append(
            GeographyRef(
                geography_type=record.geography_type,
                geography_id=record.geoid,
                name=record.name,
                country_code=CENSUS_COUNTRY_CODE,
                source_ref=source_metadata.source_id,
                source_version=evidence.geography_vintage,
            )
        )
    return tuple(refs)


def build_resolved_location(
    *,
    geocode_evidence: CensusGeocodeEvidence,
    acceptance_policy: GeocodeAcceptancePolicy,
    geography_evidence: CensusGeographyEvidence,
    manifest: CensusGeographyManifest,
    geocode_source: SourceMetadata,
    geography_source: SourceMetadata,
    generated_at: datetime,
    resolution_method_version: str = "census_geography_resolution.v1",
) -> ResolvedLocation:
    if not isinstance(geocode_evidence, CensusGeocodeEvidence):
        raise TypeError("geocode_evidence must be CensusGeocodeEvidence")
    if not isinstance(acceptance_policy, GeocodeAcceptancePolicy):
        raise TypeError("acceptance_policy must be GeocodeAcceptancePolicy")
    if not isinstance(geography_evidence, CensusGeographyEvidence):
        raise TypeError("geography_evidence must be CensusGeographyEvidence")
    if not isinstance(manifest, CensusGeographyManifest):
        raise TypeError("manifest must be CensusGeographyManifest")
    if not isinstance(geocode_source, SourceMetadata) or not isinstance(geography_source, SourceMetadata):
        raise TypeError("geocode_source and geography_source must be SourceMetadata")
    require_aware_datetime(generated_at, field_name="generated_at")
    require_nonempty_text(resolution_method_version, field_name="resolution_method_version")
    decision: GeocodeAcceptanceDecision = acceptance_policy.evaluate(geocode_evidence)
    if not decision.accepted or geocode_evidence.match_state is not CensusMatchState.MATCHED:
        raise ValueError("ResolvedLocation requires an accepted single Census geocode")
    candidate = geocode_evidence.candidates[0]
    if geography_evidence.coordinates != candidate.coordinates:
        raise ValueError("geography evidence coordinates must equal the accepted geocode coordinates")
    if geocode_evidence.benchmark != manifest.geocoder_benchmark:
        raise ValueError("geocode evidence benchmark must match manifest")
    if geography_evidence.benchmark != manifest.geocoder_benchmark:
        raise ValueError("geography evidence benchmark must match manifest")
    if geography_evidence.geography_vintage != manifest.geography_vintage:
        raise ValueError("geography evidence vintage must match manifest")
    if geography_evidence.manifest_identity != manifest.identity:
        raise ValueError("geography evidence manifest identity must match manifest")
    geography_refs = build_geography_refs(
        evidence=geography_evidence,
        source_metadata=geography_source,
    )
    if not geography_refs:
        raise ValueError("ResolvedLocation requires at least one resolved Census geography")
    return ResolvedLocation(
        latitude=candidate.coordinates.latitude,
        longitude=candidate.coordinates.longitude,
        formatted_address=candidate.matched_address,
        country_code=CENSUS_COUNTRY_CODE,
        geography_refs=geography_refs,
        source_refs=(geocode_source.source_id, geography_source.source_id),
        resolution_method_version=f"{resolution_method_version}+{acceptance_policy.method_version}+manifest.{manifest.manifest_version}",
        generated_at=generated_at,
    )
