"""Pure Overture taxonomy, deduplication, and frozen competition builders."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from sitescore_data import AvailabilityState, DataQualityState, PersistenceClass
from sitescore_data.schemas.competition import CompetitionCurve, CompetitionObservation, CompetitionSnapshot

from .._validation import require_aware_datetime, require_canonical_id, require_nonempty_text
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from .models import (
    CompetitionBuildEvidence, CompetitionCatchmentPolicy, CompetitionEligibilityState,
    CoverageState, EntityDedupPolicy, OvertureCompetitionTaxonomyMapping,
    OvertureOperatingStatus, OverturePartitionEvidence, OverturePlaceEvidence, PlaceLifecyclePolicy,
    OverturePlacesReleaseManifest, TaxonomyEligibilityEvidence, TaxonomyMatchField,
    OVERTURE_MEASUREMENT_GRAMMAR, OVERTURE_METHOD_VERSION,
)

@dataclass(frozen=True, slots=True)
class PlaceCompetitionDecision:
    place: OverturePlaceEvidence
    taxonomy: TaxonomyEligibilityEvidence
    active_state: CompetitionEligibilityState

    @property
    def qualifies(self) -> bool | None:
        if self.active_state is CompetitionEligibilityState.EXCLUDED:
            return False
        if self.active_state is CompetitionEligibilityState.UNKNOWN:
            return None
        return self.taxonomy.qualifies


def _rule_matches(place: OverturePlaceEvidence, rule) -> bool:
    if rule.match_field is TaxonomyMatchField.BASIC_CATEGORY:
        return place.basic_category == rule.category
    if rule.match_field is TaxonomyMatchField.PRIMARY:
        return place.taxonomy_primary == rule.category
    if rule.match_field is TaxonomyMatchField.HIERARCHY:
        return rule.category in place.taxonomy_hierarchy
    if rule.match_field is TaxonomyMatchField.ALTERNATE:
        return rule.category in place.taxonomy_alternates
    return False


def _resolve_taxonomy_matches(*, place: OverturePlaceEvidence, mapping: OvertureCompetitionTaxonomyMapping):
    # Canonical V1 precedence is committed by TaxonomyResolutionPolicy. Alternates are
    # supporting/QA evidence only and never independently qualify or veto a place.
    for field in mapping.resolution_policy.field_precedence:
        matches = tuple(sorted(
            (r for r in mapping.rules if r.match_field is field and _rule_matches(place, r)),
            key=lambda r: r.rule_id,
        ))
        if matches:
            return matches
    return ()


def classify_taxonomy(*, place: OverturePlaceEvidence, mapping: OvertureCompetitionTaxonomyMapping) -> TaxonomyEligibilityEvidence:
    if place.release_manifest_identity != mapping.release_manifest_identity:
        raise ValueError("place release identity does not match taxonomy mapping")
    matches = _resolve_taxonomy_matches(place=place, mapping=mapping)
    if not matches:
        # ALTERNATE-only matches intentionally cannot establish canonical qualification.
        return TaxonomyEligibilityEvidence(place.place_id, CompetitionEligibilityState.UNKNOWN, (), (), None, mapping.identity)
    states = {r.eligibility for r in matches}
    semantics = tuple(sorted({r.semantic_class for r in matches}, key=lambda x: x.value))
    if len(states) != 1:
        return TaxonomyEligibilityEvidence(place.place_id, CompetitionEligibilityState.UNKNOWN, tuple(r.rule_id for r in matches), semantics, None, mapping.identity)
    state = next(iter(states))
    conditional = None
    if state is CompetitionEligibilityState.CONDITIONAL:
        outcomes = {r.conditional_qualifies for r in matches}
        conditional = next(iter(outcomes)) if len(outcomes) == 1 else None
    return TaxonomyEligibilityEvidence(place.place_id, state, tuple(r.rule_id for r in matches), semantics, conditional, mapping.identity)


def classify_place(*, place: OverturePlaceEvidence, mapping: OvertureCompetitionTaxonomyMapping, lifecycle_policy: PlaceLifecyclePolicy) -> PlaceCompetitionDecision:
    taxonomy = classify_taxonomy(place=place, mapping=mapping)
    if place.operating_status in lifecycle_policy.excluded_statuses:
        active = CompetitionEligibilityState.EXCLUDED
    elif place.operating_status in lifecycle_policy.active_statuses:
        active = CompetitionEligibilityState.INCLUDED
    else:
        active = CompetitionEligibilityState.UNKNOWN
    return PlaceCompetitionDecision(place, taxonomy, active)


def validate_partitions_against_manifest(*, partitions: tuple[OverturePartitionEvidence, ...], manifest: OverturePlacesReleaseManifest) -> tuple[OverturePartitionEvidence, ...]:
    if not isinstance(partitions, tuple):
        raise TypeError("partitions must be a tuple")
    if not isinstance(manifest, OverturePlacesReleaseManifest):
        raise TypeError("manifest must be OverturePlacesReleaseManifest")
    ordered = tuple(sorted(partitions, key=lambda p: p.partition_id))
    for part in ordered:
        if not isinstance(part, OverturePartitionEvidence):
            raise TypeError("partitions must contain OverturePartitionEvidence")
        if part.raw_artifact.provider_identity != manifest.provider_identity:
            raise ValueError("partition provider identity does not match release manifest")
        if part.raw_artifact.persistence.persistence_class is not PersistenceClass.PERSIST:
            raise ValueError("canonical Overture competition evidence requires persistable pinned release artifacts")
        for place in part.places:
            if place.release_manifest_identity != manifest.identity:
                raise ValueError("place release identity does not match manifest")
    return ordered


def deduplicate_places(*, partitions: tuple[OverturePartitionEvidence, ...], manifest: OverturePlacesReleaseManifest, policy: EntityDedupPolicy) -> tuple[OverturePlaceEvidence, ...]:
    if not isinstance(partitions, tuple) or not partitions:
        raise ValueError("partitions must be a non-empty tuple")
    if not isinstance(policy, EntityDedupPolicy):
        raise TypeError("policy must be EntityDedupPolicy")
    ordered = validate_partitions_against_manifest(partitions=partitions, manifest=manifest)
    by_id: dict[str, OverturePlaceEvidence] = {}
    for part in ordered:
        for place in part.places:
            prior = by_id.get(place.place_id)
            if prior is None:
                by_id[place.place_id] = place
            else:
                prior_measurement = (
                    prior.longitude, prior.latitude, prior.basic_category, prior.taxonomy_primary,
                    prior.taxonomy_hierarchy, prior.taxonomy_alternates, prior.operating_status,
                    prior.confidence, prior.source_attributions, prior.release_manifest_identity,
                )
                current_measurement = (
                    place.longitude, place.latitude, place.basic_category, place.taxonomy_primary,
                    place.taxonomy_hierarchy, place.taxonomy_alternates, place.operating_status,
                    place.confidence, place.source_attributions, place.release_manifest_identity,
                )
                if prior_measurement != current_measurement:
                    raise ValueError("duplicate Overture place ID has conflicting canonical measurement evidence")
    return tuple(by_id[k] for k in sorted(by_id))


def build_measurement_definition_id(*, manifest: OverturePlacesReleaseManifest, mapping: OvertureCompetitionTaxonomyMapping, dedup_policy: EntityDedupPolicy, catchment_policy: CompetitionCatchmentPolicy, lifecycle_policy: PlaceLifecyclePolicy, count_method: str, density_method: str, method_version: str = OVERTURE_METHOD_VERSION) -> str:
    if not isinstance(lifecycle_policy, PlaceLifecyclePolicy):
        raise TypeError("lifecycle_policy must be PlaceLifecyclePolicy")
    require_canonical_id(count_method, field_name="count_method")
    require_canonical_id(density_method, field_name="density_method")
    require_nonempty_text(method_version, field_name="method_version")
    if mapping.release_manifest_identity != manifest.identity or mapping.taxonomy_id != manifest.taxonomy_id or mapping.taxonomy_version != manifest.taxonomy_version:
        raise ValueError("taxonomy mapping must bind to active release/taxonomy manifest")
    payload = {
        "grammar_version": OVERTURE_MEASUREMENT_GRAMMAR,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "provider": manifest.provider_identity.provider_key,
        "dataset": manifest.provider_identity.dataset,
        "data_release": manifest.data_release,
        "schema_version": manifest.schema_version,
        "taxonomy_id": manifest.taxonomy_id,
        "taxonomy_version": manifest.taxonomy_version,
        "taxonomy_mapping_identity": str(mapping.identity),
        "lifecycle_policy_identity": str(lifecycle_policy.identity),
        "entity_dedup_policy": str(dedup_policy.identity),
        "catchment_policy_identity": str(catchment_policy.identity),
        "travel_mode": catchment_policy.scales[0].travel_mode,
        "travel_cost_scales": tuple((s.scale_id, s.travel_cost, s.travel_cost_unit, s.catchment_semantics) for s in sorted(catchment_policy.scales, key=lambda s:(s.travel_cost,s.scale_id))),
        "spatial_boundary_predicate": (catchment_policy.spatial_predicate_id, catchment_policy.spatial_predicate_version),
        "projection_area_method": (catchment_policy.projection_area_policy_id, catchment_policy.projection_area_policy_version),
        "count_method": count_method,
        "density_method": density_method,
        "method_version": method_version,
    }
    h = hash_canonical(payload)
    return f"competition_measurement.{h.algorithm.value}_{h.digest}"


def build_competition_snapshot(*, manifest: OverturePlacesReleaseManifest, mapping: OvertureCompetitionTaxonomyMapping, dedup_policy: EntityDedupPolicy, catchment_policy: CompetitionCatchmentPolicy, lifecycle_policy: PlaceLifecyclePolicy, partitions: tuple[OverturePartitionEvidence, ...], coverage_state: CoverageState, generated_at: datetime, count_method: str = "qualifying_deduplicated_entity_count", density_method: str = "count_per_square_kilometre", method_version: str = OVERTURE_METHOD_VERSION) -> tuple[CompetitionSnapshot, CompetitionBuildEvidence]:
    require_aware_datetime(generated_at, field_name="generated_at")
    if not isinstance(coverage_state, CoverageState):
        raise TypeError("coverage_state must be CoverageState")
    measurement_id = build_measurement_definition_id(manifest=manifest, mapping=mapping, dedup_policy=dedup_policy, catchment_policy=catchment_policy, lifecycle_policy=lifecycle_policy, count_method=count_method, density_method=density_method, method_version=method_version)
    validated_partitions = validate_partitions_against_manifest(partitions=partitions, manifest=manifest)
    source_refs = tuple(sorted({p.source_metadata.source_id for p in validated_partitions}))
    if coverage_state is not CoverageState.SUFFICIENT:
        availability = AvailabilityState.UNKNOWN
        snapshot = CompetitionSnapshot(
            snapshot_id=_snapshot_id(measurement_id, (), source_refs), measurement_definition_id=measurement_id,
            curve=None, benchmark_ref=None, source_refs=source_refs, availability=availability,
            data_quality=DataQualityState.DEGRADED if source_refs else DataQualityState.MISSING, generated_at=generated_at,
        )
        return snapshot, CompetitionBuildEvidence(measurement_id, (), source_refs, coverage_state)

    places = deduplicate_places(partitions=validated_partitions, manifest=manifest, policy=dedup_policy)
    decisions = {p.place_id: classify_place(place=p, mapping=mapping, lifecycle_policy=lifecycle_policy) for p in places}
    observations = []
    qualifying_sets = []
    for scale in sorted(catchment_policy.scales, key=lambda s:(s.travel_cost,s.scale_id)):
        qualifying = []
        unresolved = []
        for pid in scale.member_place_ids:
            decision = decisions.get(pid)
            if decision is None:
                raise ValueError("catchment membership references a place absent from the pinned evidence set")
            q = decision.qualifies
            if q is True:
                qualifying.append(pid)
            elif q is None:
                unresolved.append(pid)
        if unresolved:
            # Unknown taxonomy/status inside a supposedly complete catchment cannot silently become zero/excluded.
            snapshot = CompetitionSnapshot(
                snapshot_id=_snapshot_id(measurement_id, (), source_refs), measurement_definition_id=measurement_id,
                curve=None, benchmark_ref=None, source_refs=source_refs, availability=AvailabilityState.UNKNOWN,
                data_quality=DataQualityState.DEGRADED, generated_at=generated_at,
            )
            return snapshot, CompetitionBuildEvidence(measurement_id, (), source_refs, CoverageState.UNKNOWN)
        qids = tuple(sorted(set(qualifying)))
        qualifying_sets.append((scale.scale_id, qids))
        count = len(qids)
        observations.append(CompetitionObservation(
            scale_id=scale.scale_id, travel_mode=scale.travel_mode,
            catchment_semantics=scale.catchment_semantics, travel_cost=scale.travel_cost,
            travel_cost_unit=scale.travel_cost_unit, competitor_count=count,
            catchment_area_km2=scale.area_km2, competitor_density_per_km2=count/scale.area_km2,
            source_refs=source_refs, method_version=method_version,
        ))
    curve = CompetitionCurve(tuple(observations))
    snapshot = CompetitionSnapshot(
        snapshot_id=_snapshot_id(measurement_id, tuple(qualifying_sets), source_refs), measurement_definition_id=measurement_id,
        curve=curve, benchmark_ref=None, source_refs=source_refs, availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL, generated_at=generated_at,
    )
    return snapshot, CompetitionBuildEvidence(measurement_id, tuple(qualifying_sets), source_refs, coverage_state)


def _snapshot_id(measurement_id: str, qualifying_sets, source_refs: tuple[str, ...]) -> str:
    h = hash_canonical({"measurement_definition_id": measurement_id, "qualifying_sets": qualifying_sets, "source_refs": source_refs})
    return f"competition_snapshot.{h.algorithm.value}_{h.digest}"
