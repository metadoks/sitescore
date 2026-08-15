"""Parking source provenance, eligibility, and frozen ParkingSnapshot builders."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    PersistenceClass,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue, SourceMetadata
from sitescore_data.schemas.parking import (
    ParkingAccessClass,
    ParkingObservation,
    ParkingSnapshot,
)

from ..artifacts import ArtifactRef, ArtifactStore, RawAcquisitionArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical, sha256_bytes
from ..identity import build_request_fingerprint
from ..lineage import build_source_metadata
from ..policy import ProviderPolicyDecision
from .models import (
    CurbLegalityState,
    ParkingAccessibilityCompatibility,
    ParkingCoverageEvidence,
    ParkingCoverageState,
    ParkingDerivationEvidence,
    ParkingDynamicBundleEvidence,
    ParkingEligibilityPolicy,
    ParkingEligibilityState,
    ParkingFacilityDecisionEvidence,
    ParkingFacilityEvidence,
    ParkingInventoryEvidence,
    ParkingMappingPolicy,
    ParkingMotorReachabilityEvidence,
    ParkingPedestrianReachabilityEvidence,
    ParkingProviderAccessState,
    ParkingReachabilityState,
    ParkingSourceAuthority,
    ParkingSourceBundle,
    ParkingSourceCompleteness,
    ParkingSourceManifest,
    ParkingSourceRole,
    ParkingValueState,
)

PARKING_SOURCE_ACQUISITION_GRAMMAR = "v1"
PARKING_SOURCE_ACQUISITION_OPERATION = "pinned_parking_source_artifact"
PARKING_MEASUREMENT_GRAMMAR = "v1"
PARKING_FROZEN_MAPPING_GRAMMAR = "v1"
PARKING_FROZEN_MAPPING_METHOD = "parking_snapshot_mapping.v1"


@dataclass(frozen=True, slots=True)
class ParkingRawSourceEvidence:
    manifest: ParkingSourceManifest
    raw_artifact: RawAcquisitionArtifact
    source_metadata: SourceMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, ParkingSourceManifest):
            raise TypeError("manifest must be ParkingSourceManifest")
        if not isinstance(self.raw_artifact, RawAcquisitionArtifact):
            raise TypeError("raw_artifact must be RawAcquisitionArtifact")
        if not isinstance(self.source_metadata, SourceMetadata):
            raise TypeError("source_metadata must be SourceMetadata")
        if self.raw_artifact.provider_identity != self.manifest.provider_identity:
            raise ValueError("parking raw provider identity must match active source manifest")
        if self.raw_artifact.content_hash != self.manifest.content_hash:
            raise ValueError("parking raw content hash must match active source manifest")
        if self.raw_artifact.media_type != self.manifest.media_type:
            raise ValueError("parking raw media_type must match active source manifest")
        if self.manifest.source_role is ParkingSourceRole.STATIC_INVENTORY:
            if self.raw_artifact.persistence.persistence_class is not PersistenceClass.PERSIST:
                raise ValueError("canonical pinned parking inventory source requires PERSIST for replay")
        elif self.raw_artifact.persistence.persistence_class in {PersistenceClass.SOURCE_POLICY, PersistenceClass.DO_NOT_PERSIST}:
            raise ValueError("dynamic parking source requires a concrete persisted/transient artifact")
        identity = self.manifest.provider_identity
        if (
            self.source_metadata.provider != identity.provider_key
            or self.source_metadata.dataset != identity.dataset
            or self.source_metadata.dataset_release != identity.dataset_release
            or self.source_metadata.vintage != identity.vintage
            or self.source_metadata.schema_version != identity.schema_version
            or self.source_metadata.content_hash != str(self.raw_artifact.content_hash)
            or self.source_metadata.persistence_class != self.raw_artifact.persistence.persistence_class
        ):
            raise ValueError("parking SourceMetadata must match raw source semantics")


@dataclass(frozen=True, slots=True)
class ParkingFrozenResult:
    snapshot: ParkingSnapshot
    derivation: ParkingDerivationEvidence


def build_parking_source_request_fingerprint(manifest: ParkingSourceManifest):
    if not isinstance(manifest, ParkingSourceManifest):
        raise TypeError("manifest must be ParkingSourceManifest")
    return build_request_fingerprint(
        provider_key=manifest.source_provider,
        operation=PARKING_SOURCE_ACQUISITION_OPERATION,
        semantic_parameters={
            "source_role": manifest.source_role.value,
            "dataset": manifest.dataset,
            "dataset_release": manifest.dataset_release,
            "vintage": manifest.vintage,
            "schema_id": manifest.schema_id,
            "schema_version": manifest.schema_version,
            "media_type": manifest.media_type,
            "content_hash": str(manifest.content_hash),
            "parser_id": manifest.parser_id,
            "parser_version": manifest.parser_version,
            "acquisition_id": manifest.acquisition_id,
            "acquisition_version": manifest.acquisition_version,
        },
        dataset=manifest.dataset,
        dataset_release=manifest.dataset_release,
        policy_id=manifest.acquisition_id,
        policy_version=manifest.acquisition_version,
        grammar_version=PARKING_SOURCE_ACQUISITION_GRAMMAR,
    )


def build_parking_source_evidence(*, manifest: ParkingSourceManifest, artifact_ref: ArtifactRef,
                                  artifact_store: ArtifactStore, retrieved_at: datetime,
                                  policy: ProviderPolicyDecision,
                                  source_reference: str | None = None) -> ParkingRawSourceEvidence:
    if manifest.source_role is ParkingSourceRole.STATIC_INVENTORY:
        if policy.persistence.persistence_class is not PersistenceClass.PERSIST:
            raise ValueError("canonical pinned parking inventory requires PERSIST policy")
    elif policy.persistence.persistence_class in {PersistenceClass.SOURCE_POLICY, PersistenceClass.DO_NOT_PERSIST}:
        raise ValueError("dynamic parking source requires concrete PERSIST or TRANSIENT policy")
    actual = artifact_store.get(artifact_ref)
    if sha256_bytes(actual) != manifest.content_hash:
        raise ValueError("stored parking source bytes do not match ParkingSourceManifest.content_hash")
    raw = RawAcquisitionArtifact(
        provider_identity=manifest.provider_identity,
        request_fingerprint=build_parking_source_request_fingerprint(manifest),
        media_type=manifest.media_type,
        content_hash=manifest.content_hash,
        artifact_ref=artifact_ref,
        retrieved_at=retrieved_at,
        persistence=policy.persistence,
    )
    metadata = build_source_metadata(
        raw_artifact=raw,
        data_quality=DataQualityState.FULL,
        policy=policy,
        source_reference=source_reference,
    )
    return ParkingRawSourceEvidence(manifest=manifest, raw_artifact=raw, source_metadata=metadata)


def classify_parking_eligibility(*, facility: ParkingFacilityEvidence,
                                 policy: ParkingEligibilityPolicy) -> ParkingEligibilityState:
    if not isinstance(facility, ParkingFacilityEvidence):
        raise TypeError("facility must be ParkingFacilityEvidence")
    if not isinstance(policy, ParkingEligibilityPolicy):
        raise TypeError("policy must be ParkingEligibilityPolicy")
    if facility.parking_mode.value == "on_street":
        if facility.curb_legality_state is CurbLegalityState.RESTRICTED:
            return ParkingEligibilityState.INELIGIBLE
        if facility.curb_legality_state is CurbLegalityState.UNKNOWN:
            return ParkingEligibilityState.UNKNOWN
        if facility.curb_legality_state is not CurbLegalityState.LEGAL:
            raise ValueError("on-street parking requires legal/restricted/unknown curb semantics")
    if facility.access_state in policy.eligible_access_states:
        return ParkingEligibilityState.ELIGIBLE
    if facility.access_state is ParkingProviderAccessState.UNKNOWN:
        return ParkingEligibilityState.UNKNOWN
    return ParkingEligibilityState.INELIGIBLE


def _validate_inputs(*, source_bundle: ParkingSourceBundle, inventory_source: ParkingRawSourceEvidence,
                     inventory: ParkingInventoryEvidence, coverage: ParkingCoverageEvidence,
                     mapping_policy: ParkingMappingPolicy, accessibility_compatibility: ParkingAccessibilityCompatibility,
                     motor: ParkingMotorReachabilityEvidence, pedestrian: ParkingPedestrianReachabilityEvidence,
                     dynamic_source: ParkingRawSourceEvidence | None,
                     dynamic: ParkingDynamicBundleEvidence | None) -> None:
    if inventory_source.manifest.identity != source_bundle.inventory_manifest.identity:
        raise ValueError("inventory source does not match ParkingSourceBundle")
    if inventory.source_manifest_identity != source_bundle.inventory_manifest.identity:
        raise ValueError("inventory evidence does not match active parking inventory manifest")
    if inventory.raw_artifact != inventory_source.raw_artifact or inventory.source_ref != inventory_source.source_metadata.source_id:
        raise ValueError("parsed parking inventory must bind supplied raw/source metadata lineage")
    if inventory.mapping_policy_identity != mapping_policy.identity:
        raise ValueError("parking inventory mapping policy does not match active mapping policy")
    if coverage.source_manifest_identity != source_bundle.inventory_manifest.identity:
        raise ValueError("parking coverage evidence does not match active inventory manifest")
    if coverage.state in {ParkingCoverageState.FAILED, ParkingCoverageState.UNSUPPORTED}:
        raise ValueError("provider failure/unsupported parking source cannot be converted into parking supply snapshot")
    assert coverage.observed_record_count is not None
    if coverage.observed_record_count != len(inventory.facilities):
        raise ValueError("parking coverage record count must match parsed inventory evidence")
    if motor.source_manifest_identity != source_bundle.inventory_manifest.identity:
        raise ValueError("motor reachability evidence is bound to a foreign parking inventory")
    if pedestrian.source_manifest_identity != source_bundle.inventory_manifest.identity:
        raise ValueError("pedestrian reachability evidence is bound to a foreign parking inventory")
    if not isinstance(accessibility_compatibility, ParkingAccessibilityCompatibility):
        raise TypeError("accessibility_compatibility must be ParkingAccessibilityCompatibility")
    if motor.road_derivation_identity != accessibility_compatibility.expected_road_derivation_identity:
        raise ValueError("motor reachability road derivation does not match active parking accessibility compatibility")
    if motor.graph_compatibility_identity != accessibility_compatibility.expected_graph_compatibility_identity:
        raise ValueError("motor reachability graph compatibility does not match active parking accessibility compatibility")
    if motor.drive_budget_policy_identity != accessibility_compatibility.expected_drive_budget_policy_identity:
        raise ValueError("motor reachability drive-budget policy does not match active parking accessibility compatibility")
    if pedestrian.pedestrian_derivation_identity != accessibility_compatibility.expected_pedestrian_derivation_identity:
        raise ValueError("pedestrian reachability derivation does not match active parking accessibility compatibility")
    if pedestrian.walking_budget_policy_identity != accessibility_compatibility.expected_walking_budget_policy_identity:
        raise ValueError("pedestrian reachability walking-budget policy does not match active parking accessibility compatibility")
    facility_ids = tuple(f.parking_id for f in inventory.facilities)
    if tuple(r.parking_id for r in motor.records) != facility_ids:
        raise ValueError("motor reachability must cover the exact parking facility set")
    if tuple(r.parking_id for r in pedestrian.records) != facility_ids:
        raise ValueError("pedestrian reachability must cover the exact parking facility set")
    if source_bundle.dynamic_manifest is None:
        if dynamic_source is not None or dynamic is not None:
            raise ValueError("dynamic parking evidence supplied without dynamic source manifest")
    else:
        if dynamic_source is None or dynamic is None:
            raise ValueError("dynamic source manifest requires matching dynamic source/evidence")
        if dynamic_source.manifest.identity != source_bundle.dynamic_manifest.identity:
            raise ValueError("dynamic source does not match ParkingSourceBundle")
        if dynamic.source_manifest_identity != source_bundle.dynamic_manifest.identity:
            raise ValueError("dynamic evidence does not match active dynamic source manifest")
        if dynamic.raw_artifact != dynamic_source.raw_artifact or dynamic.source_ref != dynamic_source.source_metadata.source_id:
            raise ValueError("dynamic parking evidence must bind supplied raw/source metadata lineage")
        link_policy = source_bundle.dynamic_link_policy
        if link_policy is None:
            raise ValueError("canonical dynamic parking evidence requires explicit dynamic link compatibility")
        if link_policy.inventory_manifest_identity != source_bundle.inventory_manifest.identity:
            raise ValueError("dynamic link policy inventory manifest mismatch")
        if link_policy.dynamic_manifest_identity != source_bundle.dynamic_manifest.identity:
            raise ValueError("dynamic link policy dynamic manifest mismatch")
        foreign = {r.parking_id for r in dynamic.records} - set(facility_ids)
        if foreign:
            raise ValueError("dynamic parking records cannot reference foreign inventory facility IDs")
        if any(r.source_entity_id != r.parking_id for r in dynamic.records):
            raise ValueError("SHARED_CANONICAL_PARKING_ID requires dynamic source_entity_id == canonical parking_id")
        facilities_by_id = {f.parking_id: f for f in inventory.facilities}
        for record in dynamic.records:
            facility = facilities_by_id[record.parking_id]
            if (record.available_spaces_state is ParkingValueState.VALUE
                    and facility.capacity_state is ParkingValueState.VALUE):
                assert record.available_spaces is not None and facility.capacity is not None
                if record.available_spaces > facility.capacity:
                    raise ValueError("dynamic available_spaces cannot exceed explicit static capacity")


def _decision_for(*, facility: ParkingFacilityEvidence, eligibility_policy: ParkingEligibilityPolicy,
                  motor_state: ParkingReachabilityState,
                  pedestrian_state: ParkingReachabilityState) -> ParkingFacilityDecisionEvidence:
    eligibility = classify_parking_eligibility(facility=facility, policy=eligibility_policy)
    if eligibility is ParkingEligibilityState.UNKNOWN:
        usable = None
    elif eligibility is ParkingEligibilityState.INELIGIBLE:
        usable = False
    elif motor_state is ParkingReachabilityState.UNKNOWN:
        usable = None
    elif motor_state is ParkingReachabilityState.UNREACHABLE:
        usable = False
    elif pedestrian_state is ParkingReachabilityState.UNKNOWN:
        usable = None
    elif pedestrian_state is ParkingReachabilityState.UNREACHABLE:
        usable = False
    else:
        usable = True
    return ParkingFacilityDecisionEvidence(
        parking_id=facility.parking_id,
        eligibility=eligibility,
        motor_reachability=motor_state,
        pedestrian_reachability=pedestrian_state,
        usable=usable,
    )


def build_parking_measurement_identity(*, source_bundle: ParkingSourceBundle,
                                       inventory: ParkingInventoryEvidence,
                                       coverage: ParkingCoverageEvidence,
                                       mapping_policy: ParkingMappingPolicy,
                                       eligibility_policy: ParkingEligibilityPolicy,
                                       accessibility_compatibility: ParkingAccessibilityCompatibility,
                                       motor: ParkingMotorReachabilityEvidence,
                                       pedestrian: ParkingPedestrianReachabilityEvidence,
                                       dynamic: ParkingDynamicBundleEvidence | None,
                                       decisions: tuple[ParkingFacilityDecisionEvidence, ...]) -> ContentHash:
    facilities = tuple(sorted(inventory.facilities, key=lambda f: f.parking_id))
    dynamic_records = () if dynamic is None else tuple(sorted(dynamic.records, key=lambda r: r.parking_id))
    return hash_canonical({
        "grammar_version": PARKING_MEASUREMENT_GRAMMAR,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "source_bundle_identity": str(source_bundle.identity),
        "inventory_manifest_identity": str(source_bundle.inventory_manifest.identity),
        "inventory_content_hash": str(source_bundle.inventory_manifest.content_hash),
        "coverage_identity": str(coverage.identity),
        "mapping_policy_identity": str(mapping_policy.identity),
        "eligibility_policy_identity": str(eligibility_policy.identity),
        "accessibility_compatibility_identity": str(accessibility_compatibility.identity),
        "motor_reachability_identity": str(motor.identity),
        "pedestrian_reachability_identity": str(pedestrian.identity),
        "facility_evidence": tuple({
            "parking_id": f.parking_id,
            "evidence_identity": str(f.identity),
            "capacity_method_id": f.capacity_method_id,
            "capacity_method_version": f.capacity_method_version,
            "curb_measurement_method_id": f.curb_measurement_method_id,
            "curb_measurement_method_version": f.curb_measurement_method_version,
        } for f in facilities),
        "dynamic_evidence": tuple({
            "parking_id": r.parking_id,
            "evidence_identity": str(r.identity),
            "availability_timestamp": r.availability_timestamp,
        } for r in dynamic_records),
        "decisions": tuple({
            "parking_id": d.parking_id,
            "eligibility": d.eligibility.value,
            "motor": d.motor_reachability.value,
            "pedestrian": d.pedestrian_reachability.value,
            "usable": d.usable,
        } for d in sorted(decisions, key=lambda d: d.parking_id)),
        "method": PARKING_FROZEN_MAPPING_METHOD,
    })


def _metric(*, value: int | float | None, unit: str, availability: AvailabilityState,
            quality: DataQualityState, source_refs: tuple[str, ...], method_version: str,
            reason_codes: tuple[str, ...] = ()) -> MetricValue:
    if availability is AvailabilityState.AVAILABLE:
        eligibility = ScoreEligibility.DIAGNOSTIC_ONLY
        calibration = CalibrationState.UNCALIBRATED
    elif availability is AvailabilityState.NOT_APPLICABLE:
        eligibility = ScoreEligibility.NOT_APPLICABLE
        calibration = CalibrationState.NOT_APPLICABLE
    else:
        eligibility = ScoreEligibility.INELIGIBLE
        calibration = CalibrationState.UNCALIBRATED
    return MetricValue(
        value=value,
        unit=unit,
        availability=availability,
        data_quality=quality,
        score_eligibility=eligibility,
        calibration_state=calibration,
        is_estimate=False,
        is_proxy=False,
        source_refs=source_refs,
        method_version=method_version,
        reason_codes=reason_codes,
    )


def _unknown_metric(unit: str, *, source_refs: tuple[str, ...], method_version: str,
                    reason: str) -> MetricValue:
    return _metric(
        value=None, unit=unit, availability=AvailabilityState.UNKNOWN,
        quality=DataQualityState.DEGRADED, source_refs=source_refs,
        method_version=method_version, reason_codes=(reason,),
    )


def _facility_capacity_metric(facility: ParkingFacilityEvidence, source_ref: str) -> MetricValue:
    version = f"{facility.capacity_method_id}.{facility.capacity_method_version}"
    if facility.capacity_state is ParkingValueState.VALUE:
        return _metric(value=facility.capacity, unit="spaces", availability=AvailabilityState.AVAILABLE,
                       quality=DataQualityState.FULL, source_refs=(source_ref,), method_version=version)
    if facility.capacity_state is ParkingValueState.NOT_APPLICABLE:
        return _metric(value=None, unit="spaces", availability=AvailabilityState.NOT_APPLICABLE,
                       quality=DataQualityState.NOT_APPLICABLE, source_refs=(), method_version=version)
    if facility.capacity_state is ParkingValueState.MISSING:
        return _metric(value=None, unit="spaces", availability=AvailabilityState.MISSING,
                       quality=DataQualityState.MISSING, source_refs=(source_ref,), method_version=version,
                       reason_codes=("capacity_not_published",))
    return _unknown_metric("spaces", source_refs=(source_ref,), method_version=version, reason="capacity_unknown")


def _facility_curb_metric(facility: ParkingFacilityEvidence, source_ref: str) -> MetricValue:
    if facility.curb_length_state is ParkingValueState.NOT_APPLICABLE:
        return _metric(value=None, unit="m", availability=AvailabilityState.NOT_APPLICABLE,
                       quality=DataQualityState.NOT_APPLICABLE, source_refs=(), method_version="curb.not_applicable.v1")
    if facility.curb_length_state is ParkingValueState.VALUE:
        assert facility.curb_measurement_method_id and facility.curb_measurement_method_version
        return _metric(value=facility.curb_length_m, unit="m", availability=AvailabilityState.AVAILABLE,
                       quality=DataQualityState.FULL, source_refs=(source_ref,),
                       method_version=f"{facility.curb_measurement_method_id}.{facility.curb_measurement_method_version}")
    if facility.curb_length_state is ParkingValueState.MISSING:
        return _metric(value=None, unit="m", availability=AvailabilityState.MISSING,
                       quality=DataQualityState.MISSING, source_refs=(source_ref,),
                       method_version="curb.explicit_length.v1", reason_codes=("curb_length_not_published",))
    return _unknown_metric("m", source_refs=(source_ref,), method_version="curb.explicit_length.v1", reason="curb_length_unknown")


def _dynamic_metric(*, state: ParkingValueState, value: int | float | None, unit: str,
                    source_ref: str | None) -> MetricValue:
    if state is ParkingValueState.VALUE:
        assert source_ref is not None
        return _metric(value=value, unit=unit, availability=AvailabilityState.AVAILABLE,
                       quality=DataQualityState.DEGRADED, source_refs=(source_ref,),
                       method_version="parking_dynamic_observation.v1",
                       reason_codes=("freshness_unassessed",))
    if state is ParkingValueState.MISSING:
        refs = (source_ref,) if source_ref else ()
        return _metric(value=None, unit=unit, availability=AvailabilityState.MISSING,
                       quality=DataQualityState.MISSING, source_refs=refs,
                       method_version="parking_dynamic_observation.v1",
                       reason_codes=("dynamic_value_not_available",))
    if state is ParkingValueState.NOT_APPLICABLE:
        return _metric(value=None, unit=unit, availability=AvailabilityState.NOT_APPLICABLE,
                       quality=DataQualityState.NOT_APPLICABLE, source_refs=(),
                       method_version="parking_dynamic_observation.v1")
    refs = (source_ref,) if source_ref else ()
    return _unknown_metric(unit, source_refs=refs, method_version="parking_dynamic_observation.v1", reason="dynamic_value_unknown")


def _frozen_access(access: ParkingProviderAccessState) -> ParkingAccessClass:
    if access is ParkingProviderAccessState.PUBLIC:
        return ParkingAccessClass.PUBLIC
    if access is ParkingProviderAccessState.PERMISSIVE:
        return ParkingAccessClass.PERMISSIVE
    raise ValueError("only PUBLIC/PERMISSIVE parking can become canonical usable frozen observations")


def build_parking_snapshot(*, source_bundle: ParkingSourceBundle,
                           inventory_source: ParkingRawSourceEvidence,
                           inventory: ParkingInventoryEvidence,
                           coverage: ParkingCoverageEvidence,
                           mapping_policy: ParkingMappingPolicy,
                           eligibility_policy: ParkingEligibilityPolicy,
                           accessibility_compatibility: ParkingAccessibilityCompatibility,
                           motor_reachability: ParkingMotorReachabilityEvidence,
                           pedestrian_reachability: ParkingPedestrianReachabilityEvidence,
                           generated_at: datetime,
                           dynamic_source: ParkingRawSourceEvidence | None = None,
                           dynamic_evidence: ParkingDynamicBundleEvidence | None = None) -> ParkingFrozenResult:
    _validate_inputs(
        source_bundle=source_bundle, inventory_source=inventory_source, inventory=inventory,
        coverage=coverage, mapping_policy=mapping_policy, accessibility_compatibility=accessibility_compatibility,
        motor=motor_reachability, pedestrian=pedestrian_reachability, dynamic_source=dynamic_source, dynamic=dynamic_evidence,
    )
    facilities = tuple(sorted(inventory.facilities, key=lambda f: f.parking_id))
    motor_by_id = {r.parking_id: r for r in motor_reachability.records}
    ped_by_id = {r.parking_id: r for r in pedestrian_reachability.records}
    dynamic_by_id = {} if dynamic_evidence is None else {r.parking_id: r for r in dynamic_evidence.records}
    decisions = tuple(
        _decision_for(
            facility=f,
            eligibility_policy=eligibility_policy,
            motor_state=motor_by_id[f.parking_id].state,
            pedestrian_state=ped_by_id[f.parking_id].state,
        )
        for f in facilities
    )
    measurement_identity = build_parking_measurement_identity(
        source_bundle=source_bundle, inventory=inventory, coverage=coverage,
        mapping_policy=mapping_policy, eligibility_policy=eligibility_policy,
        accessibility_compatibility=accessibility_compatibility, motor=motor_reachability, pedestrian=pedestrian_reachability,
        dynamic=dynamic_evidence, decisions=decisions,
    )
    method_version = f"parking.method.sha256_{measurement_identity.digest}"
    base_source_refs = {
        inventory_source.source_metadata.source_id,
        *motor_reachability.source_refs,
        *pedestrian_reachability.source_refs,
    }
    if dynamic_source is not None:
        base_source_refs.add(dynamic_source.source_metadata.source_id)
    all_source_refs = tuple(sorted(base_source_refs))

    unresolved = any(d.usable is None for d in decisions)
    usable_ids = {d.parking_id for d in decisions if d.usable is True}
    true_zero_authority = (
        coverage.state is ParkingCoverageState.SUFFICIENT
        and source_bundle.inventory_manifest.authority is ParkingSourceAuthority.AUTHORITATIVE
        and source_bundle.inventory_manifest.completeness is ParkingSourceCompleteness.EXHAUSTIVE
    )
    if unresolved or (not usable_ids and not true_zero_authority):
        reason = "parking_usability_unresolved" if unresolved else "parking_source_cannot_establish_true_zero"
        summary_specs = (
            ("count",), ("spaces",), ("count",), ("m",), ("spaces",),
        )
        summaries = tuple(
            _unknown_metric(unit[0], source_refs=all_source_refs, method_version=method_version, reason=reason)
            for unit in summary_specs
        )
        snapshot_hash = hash_canonical({
            "grammar_version": PARKING_FROZEN_MAPPING_GRAMMAR,
            "measurement_identity": str(measurement_identity),
            "availability": AvailabilityState.UNKNOWN.value,
            "source_refs": all_source_refs,
        })
        snapshot_id = f"parking.snapshot.sha256_{snapshot_hash.digest}"
        snapshot = ParkingSnapshot(
            snapshot_id=snapshot_id,
            observations=(),
            mapped_public_facility_count=summaries[0],
            known_public_offstreet_capacity=summaries[1],
            unknown_capacity_facility_count=summaries[2],
            mapped_legal_curb_length_m=summaries[3],
            known_onstreet_capacity=summaries[4],
            dynamic_availability_present=False,
            source_refs=all_source_refs,
            availability=AvailabilityState.UNKNOWN,
            data_quality=DataQualityState.DEGRADED,
            score_eligibility=ScoreEligibility.INELIGIBLE,
            generated_at=generated_at,
        )
    else:
        observations: list[ParkingObservation] = []
        offstreet_known = 0
        onstreet_known = 0
        unknown_capacity_count = 0
        legal_curb_length = 0.0
        degraded = coverage.state is not ParkingCoverageState.SUFFICIENT or not true_zero_authority
        dynamic_present = False
        for facility in facilities:
            if facility.parking_id not in usable_ids:
                continue
            ped = ped_by_id[facility.parking_id]
            assert ped.state is ParkingReachabilityState.REACHABLE
            assert ped.walk_time_to_site_seconds is not None
            dynamic = dynamic_by_id.get(facility.parking_id)
            capacity_metric = _facility_capacity_metric(facility, inventory_source.source_metadata.source_id)
            curb_metric = _facility_curb_metric(facility, inventory_source.source_metadata.source_id)
            if facility.capacity_state is ParkingValueState.VALUE:
                assert facility.capacity is not None
                if facility.parking_mode.value == "off_street":
                    offstreet_known += facility.capacity
                else:
                    onstreet_known += facility.capacity
            else:
                unknown_capacity_count += 1
                degraded = True
            if facility.parking_mode.value == "on_street":
                if facility.curb_legality_state is not CurbLegalityState.LEGAL:
                    raise ValueError("usable on-street facility must have LEGAL curb semantics")
                if facility.curb_length_state is ParkingValueState.VALUE:
                    assert facility.curb_length_m is not None
                    legal_curb_length += facility.curb_length_m
                else:
                    degraded = True
            walk_metric = _metric(
                value=float(ped.walk_time_to_site_seconds), unit="seconds",
                availability=AvailabilityState.AVAILABLE, quality=DataQualityState.FULL,
                source_refs=pedestrian_reachability.source_refs,
                method_version=f"{pedestrian_reachability.method_id}.{pedestrian_reachability.method_version}",
            )
            if dynamic is None:
                occupancy_metric = _dynamic_metric(state=ParkingValueState.MISSING, value=None, unit="ratio", source_ref=None)
                available_metric = _dynamic_metric(state=ParkingValueState.MISSING, value=None, unit="spaces", source_ref=None)
                availability_timestamp = None
            else:
                occupancy_metric = _dynamic_metric(
                    state=dynamic.occupancy_state, value=dynamic.occupancy, unit="ratio", source_ref=dynamic.source_ref,
                )
                available_metric = _dynamic_metric(
                    state=dynamic.available_spaces_state, value=dynamic.available_spaces, unit="spaces", source_ref=dynamic.source_ref,
                )
                dynamic_available = (
                    dynamic.occupancy_state is ParkingValueState.VALUE
                    or dynamic.available_spaces_state is ParkingValueState.VALUE
                )
                availability_timestamp = dynamic.availability_timestamp if dynamic_available else None
                dynamic_present = dynamic_present or dynamic_available
                if dynamic_available:
                    degraded = True  # no frozen/current freshness threshold in V1
            observations.append(ParkingObservation(
                parking_id=facility.parking_id,
                parking_mode=facility.parking_mode,
                access_class=_frozen_access(facility.access_state),
                generic_public_supply_eligible=True,
                capacity=capacity_metric,
                motor_vehicle_reachable=True,
                walk_time_to_site_seconds=walk_metric,
                curb_length_m=curb_metric,
                occupancy=occupancy_metric,
                available_spaces=available_metric,
                availability_timestamp=availability_timestamp,
                source_ref=inventory_source.source_metadata.source_id,
            ))
        quality = DataQualityState.DEGRADED if degraded else DataQualityState.FULL
        summary_refs = tuple(sorted({inventory_source.source_metadata.source_id, *motor_reachability.source_refs, *pedestrian_reachability.source_refs}))
        summaries = (
            _metric(value=len(observations), unit="count", availability=AvailabilityState.AVAILABLE,
                    quality=quality, source_refs=summary_refs, method_version=method_version),
            _metric(value=offstreet_known, unit="spaces", availability=AvailabilityState.AVAILABLE,
                    quality=quality, source_refs=summary_refs, method_version=method_version),
            _metric(value=unknown_capacity_count, unit="count", availability=AvailabilityState.AVAILABLE,
                    quality=quality, source_refs=summary_refs, method_version=method_version),
            _metric(value=legal_curb_length, unit="m", availability=AvailabilityState.AVAILABLE,
                    quality=quality, source_refs=summary_refs, method_version=method_version),
            _metric(value=onstreet_known, unit="spaces", availability=AvailabilityState.AVAILABLE,
                    quality=quality, source_refs=summary_refs, method_version=method_version),
        )
        observations_tuple = tuple(sorted(observations, key=lambda o: o.parking_id))
        snapshot_hash = hash_canonical({
            "grammar_version": PARKING_FROZEN_MAPPING_GRAMMAR,
            "measurement_identity": str(measurement_identity),
            "observation_ids": tuple(o.parking_id for o in observations_tuple),
            "summary_values": tuple(m.value for m in summaries),
            "dynamic_availability_present": dynamic_present,
            "source_refs": all_source_refs,
        })
        snapshot_id = f"parking.snapshot.sha256_{snapshot_hash.digest}"
        snapshot = ParkingSnapshot(
            snapshot_id=snapshot_id,
            observations=observations_tuple,
            mapped_public_facility_count=summaries[0],
            known_public_offstreet_capacity=summaries[1],
            unknown_capacity_facility_count=summaries[2],
            mapped_legal_curb_length_m=summaries[3],
            known_onstreet_capacity=summaries[4],
            dynamic_availability_present=dynamic_present,
            source_refs=all_source_refs,
            availability=AvailabilityState.AVAILABLE,
            data_quality=quality,
            score_eligibility=ScoreEligibility.DIAGNOSTIC_ONLY,
            generated_at=generated_at,
        )

    facility_evidence_ids = tuple(f"parking.facility.sha256_{f.identity.digest}" for f in facilities)
    dynamic_evidence_ids = () if dynamic_evidence is None else tuple(
        f"parking.dynamic.sha256_{r.identity.digest}" for r in sorted(dynamic_evidence.records, key=lambda r: r.parking_id)
    )
    derivation = ParkingDerivationEvidence(
        source_bundle_identity=source_bundle.identity,
        coverage_identity=coverage.identity,
        mapping_policy_identity=mapping_policy.identity,
        eligibility_policy_identity=eligibility_policy.identity,
        accessibility_compatibility_identity=accessibility_compatibility.identity,
        motor_reachability_identity=motor_reachability.identity,
        pedestrian_reachability_identity=pedestrian_reachability.identity,
        dynamic_link_policy_identity=None if source_bundle.dynamic_link_policy is None else source_bundle.dynamic_link_policy.identity,
        dynamic_bundle_identity=None if dynamic_evidence is None else hash_canonical({
            "source_manifest_identity": str(dynamic_evidence.source_manifest_identity),
            "raw_content_hash": str(dynamic_evidence.raw_artifact.content_hash),
            "parsed_artifact_identity": str(dynamic_evidence.parsed_artifact.identity),
            "records": tuple(str(r.identity) for r in dynamic_evidence.records),
        }),
        facility_evidence_ids=facility_evidence_ids,
        dynamic_evidence_ids=dynamic_evidence_ids,
        decisions=decisions,
        measurement_identity=measurement_identity,
        snapshot_id=snapshot.snapshot_id,
    )
    return ParkingFrozenResult(snapshot=snapshot, derivation=derivation)
