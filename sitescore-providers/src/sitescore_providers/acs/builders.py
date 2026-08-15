"""Pure ACS evidence aggregation and frozen demographic snapshot mapping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data import AvailabilityState, CalibrationState, DataQualityState, ScoreEligibility
from sitescore_data.schemas.common import MetricValue, SourceMetadata
from sitescore_data.schemas.demographics import AgeCohortPopulation, DemographicSnapshot
from sitescore_data.schemas.geography import GeographyRef

from .._validation import require_aware_datetime
from ..hashing import ContentHash, hash_canonical
from .client import _provider_identity
from .request import build_acs_query_plan
from .models import (
    ACSDatasetManifest,
    ACSEvidenceBundle,
    ACSStatisticalEvidence,
    ACSStatisticalValueState,
    ACSVariableRole,
    AgeCohortAggregationPolicy,
)

ACS_DEMOGRAPHIC_BUILDER_VERSION = "acs_demographic_builder.v1"


class ACSDemographicEvidenceError(ValueError):
    """Domain/data condition: required demographic evidence cannot form a snapshot."""


@dataclass(frozen=True, slots=True)
class DemographicSnapshotLineage:
    snapshot_identity: ContentHash
    total_population_evidence_identity: ContentHash
    household_income_evidence_identity: ContentHash
    cohort_evidence_identities: tuple[tuple[str, tuple[ContentHash, ...]], ...]
    age_policy_identity: ContentHash
    source_ids: tuple[str, ...]


def build_evidence_bundle(*, geography_ref: GeographyRef, manifest: ACSDatasetManifest, evidence: tuple[ACSStatisticalEvidence, ...]) -> ACSEvidenceBundle:
    """Merge one or more ACS response chunks under one coherent query plan."""
    expected = {item.semantic_key for item in manifest.variable_manifest.variables}
    actual = {item.semantic_key for item in evidence}
    if actual != expected:
        raise ValueError(f"complete ACS evidence bundle required; missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")

    plan = build_acs_query_plan(geography_ref=geography_ref, manifest=manifest)
    if not hasattr(plan, "requests"):
        raise ValueError("evidence geography is unsupported by the ACS dataset manifest")
    expected_request_by_key = {key: request.request_fingerprint for request in plan.requests for key in request.semantic_keys}
    spec_by_key = manifest.variable_manifest.by_semantic_key
    originating_ids: set[str] = set()
    for item in evidence:
        if item.dataset_manifest_identity != manifest.identity:
            raise ValueError("all evidence must bind to the requested ACS dataset manifest")
        if item.dataset_release != manifest.dataset_release or item.vintage != manifest.vintage:
            raise ValueError("all evidence must use the manifest dataset release and vintage")
        if item.geography_type is not geography_ref.geography_type or item.geography_id != geography_ref.geography_id:
            raise ValueError("all evidence must use the requested geography")
        spec = spec_by_key[item.semantic_key]
        exact_columns = (
            item.estimate_variable_id,
            item.margin_of_error_variable_id,
            item.estimate_annotation_variable_id,
            item.margin_of_error_annotation_variable_id,
        )
        if exact_columns != (
            spec.estimate_variable_id,
            spec.margin_of_error_variable_id,
            spec.estimate_annotation_variable_id,
            spec.margin_of_error_annotation_variable_id,
        ):
            raise ValueError("evidence originating ACS columns must match the immutable variable manifest")
        if item.request_fingerprint != expected_request_by_key[item.semantic_key]:
            raise ValueError("evidence request fingerprint is not compatible with the deterministic ACS query plan")
        for variable_id in (value for value in exact_columns if value is not None):
            if variable_id in originating_ids:
                raise ValueError("evidence bundle must not repeat originating ACS variable IDs")
            originating_ids.add(variable_id)

    return ACSEvidenceBundle(geography_ref=geography_ref, manifest_identity=manifest.identity, evidence=tuple(sorted(evidence, key=lambda item: item.semantic_key)))


def _source_map(
    source_metadata: tuple[SourceMetadata, ...],
    *,
    manifest: ACSDatasetManifest,
) -> dict[str, SourceMetadata]:
    if not isinstance(source_metadata, tuple) or not source_metadata:
        raise TypeError("source_metadata must be a non-empty tuple")
    expected_identity = _provider_identity(manifest)
    result: dict[str, SourceMetadata] = {}
    for source in source_metadata:
        if not isinstance(source, SourceMetadata):
            raise TypeError("source_metadata must contain SourceMetadata values")
        if source.provider != expected_identity.provider_key:
            raise ValueError("ACS SourceMetadata provider must match the active dataset manifest")
        if source.dataset != expected_identity.dataset:
            raise ValueError("ACS SourceMetadata dataset must match the active dataset manifest")
        if source.dataset_release != expected_identity.dataset_release:
            raise ValueError("ACS SourceMetadata dataset_release must match the active dataset manifest")
        if source.vintage != expected_identity.vintage:
            raise ValueError("ACS SourceMetadata vintage must match the active dataset manifest")
        if source.schema_version != expected_identity.schema_version:
            raise ValueError("ACS SourceMetadata schema_version must match the active dataset manifest")
        if source.content_hash in result:
            raise ValueError("source_metadata must not repeat raw content hashes")
        result[source.content_hash] = source
    return result


def _source_ids_for(evidence: tuple[ACSStatisticalEvidence, ...], source_by_hash: dict[str, SourceMetadata]) -> tuple[str, ...]:
    ids: list[str] = []
    for item in evidence:
        source = source_by_hash.get(str(item.raw_content_hash))
        if source is None:
            raise ValueError("every ACSStatisticalEvidence raw content hash requires SourceMetadata")
        if source.source_id not in ids:
            ids.append(source.source_id)
    return tuple(ids)


def _metric_from_evidence(*, item: ACSStatisticalEvidence, unit: str, source_ref: str) -> MetricValue:
    state = item.estimate_state
    reason_codes: tuple[str, ...] = ()
    if state is ACSStatisticalValueState.VALUE:
        availability = AvailabilityState.AVAILABLE
        quality = DataQualityState.FULL
        eligibility = ScoreEligibility.DIAGNOSTIC_ONLY
        value = item.estimate
    elif state in {ACSStatisticalValueState.MISSING, ACSStatisticalValueState.SUPPRESSED}:
        availability = AvailabilityState.MISSING
        quality = DataQualityState.MISSING
        eligibility = ScoreEligibility.INELIGIBLE
        value = None
        reason_codes = ("acs_suppressed" if state is ACSStatisticalValueState.SUPPRESSED else "acs_missing",)
    elif state is ACSStatisticalValueState.NOT_APPLICABLE:
        availability = AvailabilityState.NOT_APPLICABLE
        quality = DataQualityState.NOT_APPLICABLE
        eligibility = ScoreEligibility.NOT_APPLICABLE
        value = None
    else:
        availability = AvailabilityState.UNKNOWN
        quality = DataQualityState.DEGRADED
        eligibility = ScoreEligibility.INELIGIBLE
        value = None
        reason_codes = ("acs_annotated_or_special",)
    return MetricValue(
        value=value,
        unit=unit,
        availability=availability,
        data_quality=quality,
        score_eligibility=eligibility,
        calibration_state=CalibrationState.NOT_APPLICABLE if availability is AvailabilityState.NOT_APPLICABLE else CalibrationState.UNCALIBRATED,
        is_estimate=True,
        is_proxy=False,
        source_refs=(source_ref,) if availability is AvailabilityState.AVAILABLE else ((source_ref,) if source_ref else ()),
        method_version=ACS_DEMOGRAPHIC_BUILDER_VERSION,
        reason_codes=reason_codes,
    )


def build_demographic_snapshot(
    *,
    bundle: ACSEvidenceBundle,
    manifest: ACSDatasetManifest,
    age_policy: AgeCohortAggregationPolicy,
    source_metadata: tuple[SourceMetadata, ...],
    generated_at: datetime,
) -> tuple[DemographicSnapshot, DemographicSnapshotLineage]:
    if not isinstance(bundle, ACSEvidenceBundle):
        raise TypeError("bundle must be an ACSEvidenceBundle")
    if not isinstance(manifest, ACSDatasetManifest):
        raise TypeError("manifest must be an ACSDatasetManifest")
    if bundle.manifest_identity != manifest.identity:
        raise ValueError("evidence bundle must match dataset manifest")
    # Re-run the single canonical bundle validator so direct ACSEvidenceBundle
    # construction cannot bypass request-plan or originating-column coherence.
    bundle = build_evidence_bundle(
        geography_ref=bundle.geography_ref,
        manifest=manifest,
        evidence=bundle.evidence,
    )
    if not isinstance(age_policy, AgeCohortAggregationPolicy):
        raise TypeError("age_policy must be an AgeCohortAggregationPolicy")
    age_policy.validate_against(manifest.variable_manifest)
    require_aware_datetime(generated_at, field_name="generated_at")
    source_by_hash = _source_map(source_metadata, manifest=manifest)
    evidence_by_key = bundle.by_semantic_key
    spec_by_key = manifest.variable_manifest.by_semantic_key

    total_spec = next(item for item in manifest.variable_manifest.variables if item.role is ACSVariableRole.TOTAL_POPULATION)
    income_spec = next(item for item in manifest.variable_manifest.variables if item.role is ACSVariableRole.HOUSEHOLD_INCOME)
    total_evidence = evidence_by_key[total_spec.semantic_key]
    income_evidence = evidence_by_key[income_spec.semantic_key]
    if total_evidence.estimate_state is not ACSStatisticalValueState.VALUE:
        raise ACSDemographicEvidenceError("total population is not a usable ACS value; missing evidence is not zero")
    if not isinstance(total_evidence.estimate, int) or isinstance(total_evidence.estimate, bool) or total_evidence.estimate < 0:
        raise ACSDemographicEvidenceError("total population must be a nonnegative integer ACS estimate")
    total_source_id = _source_ids_for((total_evidence,), source_by_hash)[0]
    income_source_id = _source_ids_for((income_evidence,), source_by_hash)[0]

    cohorts: list[AgeCohortPopulation] = []
    cohort_lineage: list[tuple[str, tuple[ContentHash, ...]]] = []
    for cohort in age_policy.cohorts:
        source_evidence = tuple(evidence_by_key[key] for key in cohort.source_semantic_keys)
        for item in source_evidence:
            if item.estimate_state is not ACSStatisticalValueState.VALUE:
                raise ACSDemographicEvidenceError(f"age component {item.semantic_key} is not a usable value; missing is not zero")
            if not isinstance(item.estimate, int) or isinstance(item.estimate, bool) or item.estimate < 0:
                raise ACSDemographicEvidenceError("age component estimates must be nonnegative integers")
        population = sum(int(item.estimate) for item in source_evidence)
        total = total_evidence.estimate
        share = 0.0 if total == 0 else population / total
        cohorts.append(
            AgeCohortPopulation(
                cohort_id=cohort.cohort_id,
                age_min_inclusive=cohort.age_min_inclusive,
                age_max_exclusive=cohort.age_max_exclusive,
                population=population,
                population_share=share,
            )
        )
        cohort_lineage.append((cohort.cohort_id, tuple(item.identity for item in source_evidence)))

    total_metric = _metric_from_evidence(item=total_evidence, unit=total_spec.unit, source_ref=total_source_id)
    income_metric = _metric_from_evidence(item=income_evidence, unit=income_spec.unit, source_ref=income_source_id)
    all_source_ids = _source_ids_for(bundle.evidence, source_by_hash)
    degraded = income_metric.availability is not AvailabilityState.AVAILABLE or any(item.estimate_state is not ACSStatisticalValueState.VALUE for item in bundle.evidence)
    snapshot = DemographicSnapshot(
        geography_ref=bundle.geography_ref,
        total_population=total_metric,
        age_cohorts=tuple(cohorts),
        household_income=income_metric,
        source_refs=all_source_ids,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.DEGRADED if degraded else DataQualityState.FULL,
        generated_at=generated_at,
    )
    snapshot_identity = hash_canonical(
        {
            "geography_type": snapshot.geography_ref.geography_type.value,
            "geography_id": snapshot.geography_ref.geography_id,
            "total_population": snapshot.total_population.value,
            "age_cohorts": tuple((c.cohort_id, c.age_min_inclusive, c.age_max_exclusive, c.population, c.population_share) for c in snapshot.age_cohorts),
            "household_income": snapshot.household_income.value,
            "source_refs": snapshot.source_refs,
            "builder_version": ACS_DEMOGRAPHIC_BUILDER_VERSION,
            "age_policy_identity": str(age_policy.identity),
        }
    )
    lineage = DemographicSnapshotLineage(
        snapshot_identity=snapshot_identity,
        total_population_evidence_identity=total_evidence.identity,
        household_income_evidence_identity=income_evidence.identity,
        cohort_evidence_identities=tuple(cohort_lineage),
        age_policy_identity=age_policy.identity,
        source_ids=all_source_ids,
    )
    return snapshot, lineage
