from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
from typing import Mapping, Any

import pytest

from sitescore_data import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    PersistenceClass,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.parking import ParkingAccessClass, ParkingMode, ParkingObservation
from sitescore_providers import (
    ArtifactRef,
    CommercialUseState,
    PersistenceDecision,
    ProviderPolicyDecision,
    RedistributionState,
    sha256_bytes,
)
from sitescore_providers.hashing import ContentHash
from sitescore_providers.parking import (
    CurbLegalityState,
    PARKING_DYNAMIC_MAPPING_PROFILE_ID,
    PARKING_DYNAMIC_PARSER_ID,
    PARKING_NORMALIZED_MAPPING_PROFILE_ID,
    PARKING_OSM_MAPPING_PROFILE_ID,
    PARKING_STATIC_PARSER_ID,
    ParkingAccessibilityCompatibility,
    ParkingCoverageEvidence,
    ParkingCoverageState,
    ParkingDynamicLinkPolicy,
    ParkingEligibilityPolicy,
    ParkingGeometryType,
    ParkingMappingPolicy,
    ParkingMotorReachabilityEvidence,
    ParkingMotorReachabilityRecord,
    ParkingPedestrianReachabilityEvidence,
    ParkingPedestrianReachabilityRecord,
    ParkingProviderAccessState,
    ParkingReachabilityState,
    ParkingSourceAuthority,
    ParkingSourceBundle,
    ParkingSourceCompleteness,
    ParkingSourceManifest,
    ParkingSourceRole,
    build_parking_snapshot,
    build_parking_source_evidence,
    build_parking_source_request_fingerprint,
    classify_parking_eligibility,
    parse_parking_dynamic,
    parse_parking_inventory,
)

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


class MemoryStore:
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


class FixedReader:
    def __init__(self, rows: tuple[Mapping[str, Any], ...]):
        self.rows = rows

    def read_records(self, *, content: bytes, manifest):
        return self.rows


def provider_policy(pid: str = "parking_source_policy", persistence_class=PersistenceClass.PERSIST):
    kwargs = {}
    if persistence_class is PersistenceClass.TRANSIENT:
        kwargs["max_retention_seconds"] = 3600
    persistence = PersistenceDecision(pid, "v1", persistence_class, **kwargs)
    return ProviderPolicyDecision(
        pid, "v1", persistence, True,
        RedistributionState.ALLOWED, CommercialUseState.ALLOWED,
        "ODbL-1.0" if pid.startswith("osm") else "provider-license",
    )


def source_manifest(*, content: bytes, provider="openstreetmap", role=ParkingSourceRole.STATIC_INVENTORY,
                    authority=None, completeness=None, media_type="application/vnd.openstreetmap.data+pbf",
                    release="2026-08-01", parser_id=None):
    if authority is None:
        authority = ParkingSourceAuthority.COMMUNITY_MAPPED if provider == "openstreetmap" else ParkingSourceAuthority.AUTHORITATIVE
    if completeness is None:
        completeness = ParkingSourceCompleteness.NON_EXHAUSTIVE if provider == "openstreetmap" else ParkingSourceCompleteness.EXHAUSTIVE
    if parser_id is None:
        parser_id = PARKING_STATIC_PARSER_ID if role is ParkingSourceRole.STATIC_INVENTORY else PARKING_DYNAMIC_PARSER_ID
    return ParkingSourceManifest(
        manifest_version="v1", source_role=role, source_provider=provider,
        dataset="parking_inventory" if role is ParkingSourceRole.STATIC_INVENTORY else "parking_dynamic",
        dataset_release=release, vintage=release, schema_id="parking_source",
        schema_version="v1", media_type=media_type, content_hash=sha256_bytes(content),
        parser_id=parser_id, parser_version="v1", acquisition_id="parking_acquisition",
        acquisition_version="v1", authority=authority, completeness=completeness,
    )


def osm_mapping():
    return ParkingMappingPolicy(
        policy_id="osm_parking_mapping", policy_version="v1",
        mapping_profile_id=PARKING_OSM_MAPPING_PROFILE_ID, mapping_profile_version="v1",
    )


def normalized_mapping():
    return ParkingMappingPolicy(
        policy_id="normalized_parking_mapping", policy_version="v1",
        mapping_profile_id=PARKING_NORMALIZED_MAPPING_PROFILE_ID, mapping_profile_version="v1",
    )


def static_row(entity="way/1", *, access="yes", capacity="10", parking="surface"):
    tags = {"amenity": "parking", "parking": parking, "access": access}
    if capacity is not None:
        tags["capacity"] = capacity
    return {
        "kind": "facility", "entity_id": entity, "geometry_identity": f"geom.{entity.replace('/', '.')}",
        "geometry_type": "way", "tags": tags,
    }


def curb_row(entity="way/2", *, access="yes", restriction=None, capacity="3", length=40.0):
    return {
        "kind": "curb_segment", "entity_id": entity, "side": "right",
        "geometry_identity": f"geom.{entity.replace('/', '.')}.right", "geometry_type": "way",
        "parking_position": "lane", "access": access, "restriction": restriction,
        "conditional_restrictions_present": False, "capacity": capacity,
        "curb_length_m": length, "curb_measurement_method_id": "geodesic_line_length",
        "curb_measurement_method_version": "v1",
        "source_tags": {"parking:right": "lane", "parking:right:access": access},
    }


def parsed_inventory(rows, *, manifest=None, mapping=None, retrieved_at=NOW):
    content = b"parking-source-content"
    manifest = manifest or source_manifest(content=content)
    mapping = mapping or osm_mapping()
    store = MemoryStore()
    ref = store.put(content_hash=manifest.content_hash, content=content)
    raw = build_parking_source_evidence(
        manifest=manifest, artifact_ref=ref, artifact_store=store, retrieved_at=retrieved_at,
        policy=provider_policy("osm_parking_policy" if manifest.source_provider == "openstreetmap" else "municipal_parking_policy"),
    )
    parsed_ref = ArtifactRef("artifact:parsed/parking")
    inv = parse_parking_inventory(source_evidence=raw, artifact_store=store, reader=FixedReader(tuple(rows)),
                                  mapping_policy=mapping, parsed_artifact_ref=parsed_ref)
    return manifest, mapping, store, raw, inv


def reachability(manifest, facility_ids, *, motor_states=None, ped_states=None):
    motor_states = motor_states or {x: ParkingReachabilityState.REACHABLE for x in facility_ids}
    ped_states = ped_states or {x: ParkingReachabilityState.REACHABLE for x in facility_ids}
    road_id = sha256_bytes(b"road-derivation")
    graph_id = sha256_bytes(b"road-graph")
    drive_id = sha256_bytes(b"drive-policy")
    ped_id = sha256_bytes(b"ped-derivation")
    walk_id = sha256_bytes(b"walk-policy")
    motor = ParkingMotorReachabilityEvidence(
        source_manifest_identity=manifest.identity,
        road_derivation_identity=road_id, graph_compatibility_identity=graph_id,
        drive_budget_policy_identity=drive_id, method_id="road_parking_membership", method_version="v1",
        source_refs=("road_source",), records=tuple(
            ParkingMotorReachabilityRecord(x, motor_states[x]) for x in sorted(facility_ids)
        ),
    )
    ped = ParkingPedestrianReachabilityEvidence(
        source_manifest_identity=manifest.identity,
        pedestrian_derivation_identity=ped_id, walking_budget_policy_identity=walk_id,
        method_id="walk_parking_membership", method_version="v1", source_refs=("pedestrian_source",),
        records=tuple(
            ParkingPedestrianReachabilityRecord(
                x, ped_states[x], 120.0 if ped_states[x] is ParkingReachabilityState.REACHABLE else None
            ) for x in sorted(facility_ids)
        ),
    )
    return motor, ped




def accessibility_compatibility(motor, ped, *, cid="parking_accessibility_compat"):
    return ParkingAccessibilityCompatibility(
        compatibility_id=cid, compatibility_version="v1",
        expected_road_derivation_identity=motor.road_derivation_identity,
        expected_graph_compatibility_identity=motor.graph_compatibility_identity,
        expected_drive_budget_policy_identity=motor.drive_budget_policy_identity,
        expected_pedestrian_derivation_identity=ped.pedestrian_derivation_identity,
        expected_walking_budget_policy_identity=ped.walking_budget_policy_identity,
    )


def dynamic_link_policy(inventory_manifest, dynamic_manifest, *, pid="parking_dynamic_shared_id_link", version="v1"):
    return ParkingDynamicLinkPolicy(
        policy_id=pid, policy_version=version,
        inventory_manifest_identity=inventory_manifest.identity,
        dynamic_manifest_identity=dynamic_manifest.identity,
    )


def snapshot_from(rows, *, authoritative=False, coverage_state=ParkingCoverageState.SUFFICIENT,
                  motor_states=None, ped_states=None, dynamic=None, generated_at=NOW):
    content = b"parking-source-content"
    if authoritative:
        manifest = source_manifest(content=content, provider="municipal_parking", media_type="application/json")
        mapping = normalized_mapping()
        normalized_rows = tuple(rows)
    else:
        manifest = source_manifest(content=content)
        mapping = osm_mapping()
        normalized_rows = tuple(rows)
    _, _, store, raw, inv = parsed_inventory(normalized_rows, manifest=manifest, mapping=mapping)
    coverage = ParkingCoverageEvidence(manifest.identity, "site_parking_scope", coverage_state, len(inv.facilities))
    ids = tuple(f.parking_id for f in inv.facilities)
    motor, ped = reachability(manifest, ids, motor_states=motor_states, ped_states=ped_states)
    bundle = ParkingSourceBundle("site_parking_bundle", "v1", manifest)
    return build_parking_snapshot(
        source_bundle=bundle, inventory_source=raw, inventory=inv, coverage=coverage,
        mapping_policy=mapping, eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
        accessibility_compatibility=accessibility_compatibility(motor, ped),
        motor_reachability=motor, pedestrian_reachability=ped, generated_at=generated_at,
    )


def test_source_manifest_deterministic_content_sensitive_and_mutable_rejected():
    a = source_manifest(content=b"abc")
    b = source_manifest(content=b"abc")
    c = source_manifest(content=b"abd")
    assert a.identity == b.identity
    assert a.identity != c.identity
    with pytest.raises(ValueError):
        source_manifest(content=b"abc", release="current")


def test_media_type_is_manifest_bound_and_locator_excluded():
    content = b"abc"
    manifest = source_manifest(content=content)
    store = MemoryStore()
    ref1 = ArtifactRef("artifact:path/a")
    ref2 = ArtifactRef("artifact:path/b")
    store.values[str(ref1)] = content
    store.values[str(ref2)] = content
    one = build_parking_source_evidence(manifest=manifest, artifact_ref=ref1, artifact_store=store,
                                        retrieved_at=NOW, policy=provider_policy("osm_source_policy"))
    two = build_parking_source_evidence(manifest=manifest, artifact_ref=ref2, artifact_store=store,
                                        retrieved_at=NOW + timedelta(hours=1), policy=provider_policy("osm_source_policy"))
    assert one.raw_artifact.media_type == manifest.media_type
    assert two.raw_artifact.request_fingerprint == one.raw_artifact.request_fingerprint
    assert one.source_metadata.source_id == two.source_metadata.source_id
    wrong_media = replace(manifest, media_type="application/json")
    assert wrong_media.identity != manifest.identity


def test_osm_cannot_self_assert_authoritative_exhaustive_zero_semantics():
    with pytest.raises(ValueError):
        source_manifest(content=b"abc", authority=ParkingSourceAuthority.AUTHORITATIVE)
    with pytest.raises(ValueError):
        source_manifest(content=b"abc", completeness=ParkingSourceCompleteness.EXHAUSTIVE)


def test_static_dynamic_source_roles_are_distinct():
    static = source_manifest(content=b"s")
    dynamic = source_manifest(content=b"d", provider="parking_api", role=ParkingSourceRole.DYNAMIC_AVAILABILITY,
                              authority=ParkingSourceAuthority.OTHER, completeness=ParkingSourceCompleteness.UNKNOWN,
                              media_type="application/json")
    assert static.provider_identity.domain == "parking_inventory"
    assert dynamic.provider_identity.domain == "parking_dynamic"
    assert static.identity != dynamic.identity


def test_osm_public_permissive_private_customer_and_unknown_access_policy():
    rows = (
        static_row("way/1", access="yes"),
        static_row("way/2", access="permissive"),
        static_row("way/3", access="private"),
        static_row("way/4", access="customers"),
        static_row("way/5", access="permit"),
        static_row("way/6", access=None),
    )
    # remove None access key from final row
    rows = tuple({**r, "tags": {k: v for k, v in r["tags"].items() if v is not None}} for r in rows)
    manifest, mapping, _, _, inv = parsed_inventory(rows)
    policy = ParkingEligibilityPolicy("generic_parking", "v1")
    decisions = {f.source_entity_id: classify_parking_eligibility(facility=f, policy=policy) for f in inv.facilities}
    assert decisions["way/1"].value == "eligible"
    assert decisions["way/2"].value == "eligible"
    assert decisions["way/3"].value == "ineligible"
    assert decisions["way/4"].value == "ineligible"
    assert decisions["way/5"].value == "ineligible"
    assert decisions["way/6"].value == "unknown"
    assert manifest.authority is ParkingSourceAuthority.COMMUNITY_MAPPED


def test_capacity_explicit_missing_and_no_polygon_area_inference():
    _, _, _, _, inv = parsed_inventory((static_row("way/1", capacity="12"), static_row("way/2", capacity=None)))
    by_id = {f.source_entity_id: f for f in inv.facilities}
    assert by_id["way/1"].capacity == 12
    assert by_id["way/1"].capacity_state.value == "value"
    assert by_id["way/2"].capacity is None
    assert by_id["way/2"].capacity_state.value == "missing"
    with pytest.raises(Exception):
        parsed_inventory((static_row("way/3", capacity="12.5"),))


def test_bool_nan_negative_capacity_rejected():
    base = static_row()
    for bad in (True, -1, float("nan"), float("inf")):
        row = {**base, "tags": {**base["tags"], "capacity": bad}}
        with pytest.raises(Exception):
            parsed_inventory((row,))


def test_curb_length_separate_from_capacity_and_restrictions():
    _, _, _, _, inv = parsed_inventory((curb_row(capacity="4", length=55.0),))
    f = inv.facilities[0]
    assert f.parking_mode is ParkingMode.ON_STREET
    assert f.capacity == 4
    assert f.curb_length_m == 55.0
    assert f.curb_legality_state is CurbLegalityState.LEGAL
    _, _, _, _, blocked = parsed_inventory((curb_row(restriction="no_parking"),))
    assert blocked.facilities[0].curb_legality_state is CurbLegalityState.RESTRICTED


def test_deprecated_osm_parking_lane_condition_input_rejected():
    row = curb_row()
    row = {**row, "source_tags": {"parking:lane:right": "parallel"}}
    with pytest.raises(Exception):
        parsed_inventory((row,))


def test_generic_osm_empty_is_unknown_not_zero():
    result = snapshot_from((), authoritative=False, coverage_state=ParkingCoverageState.UNKNOWN)
    assert result.snapshot.availability is AvailabilityState.UNKNOWN
    assert result.snapshot.mapped_public_facility_count.value is None


def test_authoritative_complete_empty_is_true_zero():
    result = snapshot_from((), authoritative=True, coverage_state=ParkingCoverageState.SUFFICIENT)
    assert result.snapshot.availability is AvailabilityState.AVAILABLE
    assert result.snapshot.mapped_public_facility_count.value == 0
    assert result.snapshot.known_public_offstreet_capacity.value == 0
    assert result.snapshot.mapped_legal_curb_length_m.value == 0


def test_unknown_reachability_never_becomes_zero():
    manifest, mapping, _, raw, inv = parsed_inventory((static_row(),))
    pid = inv.facilities[0].parking_id
    motor, ped = reachability(manifest, (pid,), motor_states={pid: ParkingReachabilityState.UNKNOWN})
    result = build_parking_snapshot(
        source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest),
        inventory_source=raw, inventory=inv,
        coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
        mapping_policy=mapping, eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
        accessibility_compatibility=accessibility_compatibility(motor, ped),
        motor_reachability=motor, pedestrian_reachability=ped, generated_at=NOW,
    )
    assert result.snapshot.availability is AvailabilityState.UNKNOWN
    assert result.snapshot.mapped_public_facility_count.value is None


def test_foreign_motor_and_pedestrian_parking_bundle_rejected():
    manifest, mapping, _, raw, inv = parsed_inventory((static_row(),))
    pid = inv.facilities[0].parking_id
    motor, ped = reachability(manifest, (pid,))
    foreign = source_manifest(content=b"foreign")
    bad_motor = replace(motor, source_manifest_identity=foreign.identity)
    with pytest.raises(ValueError):
        build_parking_snapshot(
            source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest), inventory_source=raw,
            inventory=inv, coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
            mapping_policy=mapping, eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
            accessibility_compatibility=accessibility_compatibility(motor, ped),
            motor_reachability=bad_motor, pedestrian_reachability=ped, generated_at=NOW,
        )
    bad_ped = replace(ped, source_manifest_identity=foreign.identity)
    with pytest.raises(ValueError):
        build_parking_snapshot(
            source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest), inventory_source=raw,
            inventory=inv, coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
            mapping_policy=mapping, eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
            accessibility_compatibility=accessibility_compatibility(motor, ped),
            motor_reachability=motor, pedestrian_reachability=bad_ped, generated_at=NOW,
        )


def build_dynamic_for(manifest_static, parking_id, *, available=5, occupancy=0.5, timestamp=NOW, retrieved_at=NOW):
    content = b"dynamic-content"
    manifest = source_manifest(content=content, provider="parking_api", role=ParkingSourceRole.DYNAMIC_AVAILABILITY,
                               authority=ParkingSourceAuthority.OTHER, completeness=ParkingSourceCompleteness.UNKNOWN,
                               media_type="application/json")
    store = MemoryStore(); ref = store.put(content_hash=manifest.content_hash, content=content)
    raw = build_parking_source_evidence(manifest=manifest, artifact_ref=ref, artifact_store=store,
                                        retrieved_at=retrieved_at, policy=provider_policy("parking_dynamic_policy"))
    row = {"parking_id": parking_id, "source_entity_id": parking_id, "available_spaces": available,
           "occupancy": occupancy, "availability_timestamp": timestamp.isoformat() if timestamp else None}
    parsed = parse_parking_dynamic(source_evidence=raw, artifact_store=store, reader=FixedReader((row,)),
                                   parsed_artifact_ref=ArtifactRef("artifact:parsed/dynamic"))
    return manifest, raw, parsed


def test_dynamic_timestamp_required_and_semantic_identity_changes():
    manifest, _, _, _, inv = parsed_inventory((static_row(capacity="10"),))
    pid = inv.facilities[0].parking_id
    dyn_manifest, dyn_raw, dyn1 = build_dynamic_for(manifest, pid, timestamp=NOW)
    _, _, dyn2 = build_dynamic_for(manifest, pid, timestamp=NOW + timedelta(minutes=1))
    assert dyn1.records[0].identity != dyn2.records[0].identity
    with pytest.raises(Exception):
        build_dynamic_for(manifest, pid, timestamp=None)


def test_retrieved_at_does_not_change_dynamic_semantic_evidence_identity():
    manifest, _, _, _, inv = parsed_inventory((static_row(),))
    pid = inv.facilities[0].parking_id
    _, _, one = build_dynamic_for(manifest, pid, retrieved_at=NOW)
    _, _, two = build_dynamic_for(manifest, pid, retrieved_at=NOW + timedelta(hours=4))
    assert one.records[0].identity == two.records[0].identity


def test_dynamic_snapshot_mapping_timestamp_and_available_spaces_capacity_rule():
    manifest, mapping, _, raw, inv = parsed_inventory((static_row(capacity="10"),))
    pid = inv.facilities[0].parking_id
    motor, ped = reachability(manifest, (pid,))
    dyn_manifest, dyn_raw, dyn = build_dynamic_for(manifest, pid, available=4, occupancy=0.6, timestamp=NOW)
    result = build_parking_snapshot(
        source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest, dyn_manifest, dynamic_link_policy(manifest, dyn_manifest)),
        inventory_source=raw, inventory=inv,
        coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
        mapping_policy=mapping, eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
        accessibility_compatibility=accessibility_compatibility(motor, ped),
        motor_reachability=motor, pedestrian_reachability=ped, dynamic_source=dyn_raw, dynamic_evidence=dyn,
        generated_at=NOW,
    )
    obs = result.snapshot.observations[0]
    assert obs.available_spaces.value == 4
    assert obs.occupancy.value == 0.6
    assert obs.availability_timestamp == NOW
    assert result.snapshot.dynamic_availability_present is True
    _, _, bad_dyn = build_dynamic_for(manifest, pid, available=11, occupancy=0.6, timestamp=NOW)
    with pytest.raises(ValueError):
        build_parking_snapshot(
            source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest, dyn_manifest, dynamic_link_policy(manifest, dyn_manifest)),
            inventory_source=raw, inventory=inv,
            coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
            mapping_policy=mapping, eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
            accessibility_compatibility=accessibility_compatibility(motor, ped),
            motor_reachability=motor, pedestrian_reachability=ped, dynamic_source=dyn_raw, dynamic_evidence=bad_dyn,
            generated_at=NOW,
        )


def test_no_dynamic_evidence_frozen_timestamp_none():
    result = snapshot_from((static_row(),), authoritative=False)
    obs = result.snapshot.observations[0]
    assert obs.occupancy.availability is AvailabilityState.MISSING
    assert obs.available_spaces.availability is AvailabilityState.MISSING
    assert obs.availability_timestamp is None


def test_frozen_observation_constructor_enforces_dynamic_timestamp():
    def metric(value, unit):
        return MetricValue(value=value, unit=unit, availability=AvailabilityState.AVAILABLE,
                           data_quality=DataQualityState.FULL, score_eligibility=ScoreEligibility.DIAGNOSTIC_ONLY,
                           calibration_state=CalibrationState.UNCALIBRATED, is_estimate=False, is_proxy=False,
                           source_refs=("parking_source",), method_version="test.v1")
    unknown = MetricValue(value=None, unit="spaces", availability=AvailabilityState.MISSING,
                          data_quality=DataQualityState.MISSING, score_eligibility=ScoreEligibility.INELIGIBLE,
                          calibration_state=CalibrationState.UNCALIBRATED, is_estimate=False, is_proxy=False,
                          source_refs=(), method_version="test.v1")
    with pytest.raises(ValueError):
        ParkingObservation(
            parking_id="parking_test", parking_mode=ParkingMode.OFF_STREET,
            access_class=ParkingAccessClass.PUBLIC, generic_public_supply_eligible=True,
            capacity=unknown, motor_vehicle_reachable=True,
            walk_time_to_site_seconds=metric(60, "seconds"),
            curb_length_m=MetricValue(value=None, unit="m", availability=AvailabilityState.NOT_APPLICABLE,
                                      data_quality=DataQualityState.NOT_APPLICABLE, score_eligibility=ScoreEligibility.NOT_APPLICABLE,
                                      calibration_state=CalibrationState.NOT_APPLICABLE, is_estimate=False, is_proxy=False,
                                      source_refs=(), method_version="test.v1"),
            occupancy=metric(0.5, "ratio"), available_spaces=unknown,
            availability_timestamp=None, source_ref="parking_source",
        )


def test_reversed_facility_input_order_same_snapshot_and_derivation():
    rows = (static_row("way/2", capacity="2"), static_row("way/1", capacity="3"))
    a = snapshot_from(rows)
    b = snapshot_from(tuple(reversed(rows)))
    assert a.snapshot.snapshot_id == b.snapshot.snapshot_id
    assert a.derivation.measurement_identity == b.derivation.measurement_identity
    assert tuple(o.parking_id for o in a.snapshot.observations) == tuple(sorted(o.parking_id for o in a.snapshot.observations))


def test_duplicate_exact_record_collapses_conflicting_duplicate_rejects():
    row = static_row("way/1")
    _, _, _, _, inv = parsed_inventory((row, row))
    assert len(inv.facilities) == 1
    conflict = static_row("way/1", capacity="99")
    with pytest.raises(Exception):
        parsed_inventory((row, conflict))


def test_no_curb_length_to_capacity_conversion_in_snapshot():
    result = snapshot_from((curb_row(capacity=None, length=50.0),))
    assert result.snapshot.mapped_legal_curb_length_m.value == 50.0
    assert result.snapshot.known_onstreet_capacity.value == 0
    assert result.snapshot.unknown_capacity_facility_count.value == 1


def test_provider_failure_coverage_cannot_become_zero_snapshot():
    manifest, mapping, _, raw, inv = parsed_inventory(())
    motor, ped = reachability(manifest, ())
    failed = ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.FAILED, None)
    with pytest.raises(ValueError):
        build_parking_snapshot(
            source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest), inventory_source=raw,
            inventory=inv, coverage=failed, mapping_policy=mapping,
            eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
            accessibility_compatibility=accessibility_compatibility(motor, ped),
            motor_reachability=motor, pedestrian_reachability=ped, generated_at=NOW,
        )


def test_source_metadata_wrong_semantics_rejected():
    content = b"abc"; manifest = source_manifest(content=content); store=MemoryStore(); ref=store.put(content_hash=manifest.content_hash, content=content)
    raw = build_parking_source_evidence(manifest=manifest, artifact_ref=ref, artifact_store=store,
                                        retrieved_at=NOW, policy=provider_policy("osm_source_policy"))
    from sitescore_providers.parking.builders import ParkingRawSourceEvidence
    with pytest.raises(ValueError):
        ParkingRawSourceEvidence(manifest, raw.raw_artifact, replace(raw.source_metadata, dataset="wrong"))


def test_wrong_media_type_direct_raw_source_rejected():
    content = b"abc"; manifest = source_manifest(content=content); store=MemoryStore(); ref=store.put(content_hash=manifest.content_hash, content=content)
    raw = build_parking_source_evidence(manifest=manifest, artifact_ref=ref, artifact_store=store,
                                        retrieved_at=NOW, policy=provider_policy("osm_source_policy"))
    from sitescore_providers.parking.builders import ParkingRawSourceEvidence
    with pytest.raises(ValueError):
        ParkingRawSourceEvidence(manifest, replace(raw.raw_artifact, media_type="application/json"), raw.source_metadata)


def test_storage_locator_not_in_measurement_identity():
    rows = (static_row(),)
    manifest, mapping, store, raw1, inv1 = parsed_inventory(rows)
    # same semantic raw content, different locator and retrieval timestamp
    ref2 = ArtifactRef("artifact:alternate/location")
    store.values[str(ref2)] = b"parking-source-content"
    raw2 = build_parking_source_evidence(manifest=manifest, artifact_ref=ref2, artifact_store=store,
                                         retrieved_at=NOW + timedelta(hours=3), policy=provider_policy("osm_parking_policy"))
    inv2 = parse_parking_inventory(source_evidence=raw2, artifact_store=store, reader=FixedReader(rows),
                                   mapping_policy=mapping, parsed_artifact_ref=ArtifactRef("artifact:parsed/other"))
    pid = inv1.facilities[0].parking_id
    motor, ped = reachability(manifest, (pid,))
    args=dict(source_bundle=ParkingSourceBundle("site_parking_bundle","v1",manifest),
              coverage=ParkingCoverageEvidence(manifest.identity,"site_parking_scope",ParkingCoverageState.SUFFICIENT,1),
              mapping_policy=mapping, eligibility_policy=ParkingEligibilityPolicy("generic_parking","v1"),
              accessibility_compatibility=accessibility_compatibility(motor, ped),
              motor_reachability=motor, pedestrian_reachability=ped, generated_at=NOW)
    a=build_parking_snapshot(inventory_source=raw1, inventory=inv1, **args)
    b=build_parking_snapshot(inventory_source=raw2, inventory=inv2, **args)
    assert a.derivation.measurement_identity == b.derivation.measurement_identity
    assert a.snapshot.snapshot_id == b.snapshot.snapshot_id


def test_same_explicit_generated_at_same_primitive():
    a=snapshot_from((static_row(),), generated_at=NOW)
    b=snapshot_from((static_row(),), generated_at=NOW)
    assert a.snapshot == b.snapshot


def test_no_composite_or_normalization_outputs_exist():
    result=snapshot_from((static_row(),))
    assert not hasattr(result.snapshot, "road_parking_access_score")
    assert not hasattr(result.snapshot, "percentile")

def test_parking_coordinate_bounds_and_order_are_strict_when_supplied():
    row = static_row()
    good = {**row, "latitude": 40.0, "longitude": -74.0}
    _, _, _, _, inv = parsed_inventory((good,))
    assert inv.facilities[0].latitude == 40.0
    assert inv.facilities[0].longitude == -74.0
    for bad in (
        {**row, "latitude": 91.0, "longitude": 0.0},
        {**row, "latitude": 0.0, "longitude": 181.0},
        {**row, "latitude": True, "longitude": 0.0},
        {**row, "latitude": float("nan"), "longitude": 0.0},
        {**row, "latitude": 40.0},
    ):
        with pytest.raises(Exception):
            parsed_inventory((bad,))


def _base_snapshot_inputs_with_compatibility():
    manifest, mapping, _, raw, inv = parsed_inventory((static_row(capacity="10"),))
    pid = inv.facilities[0].parking_id
    motor, ped = reachability(manifest, (pid,))
    compatibility = accessibility_compatibility(motor, ped)
    common = dict(
        source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest),
        inventory_source=raw,
        inventory=inv,
        coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
        mapping_policy=mapping,
        eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
        accessibility_compatibility=compatibility,
        motor_reachability=motor,
        pedestrian_reachability=ped,
        generated_at=NOW,
    )
    return manifest, motor, ped, compatibility, common


def test_accessibility_compatibility_accepts_matching_active_upstreams():
    _, _, _, compatibility, common = _base_snapshot_inputs_with_compatibility()
    result = build_parking_snapshot(**common)
    assert result.snapshot.availability is AvailabilityState.AVAILABLE
    assert result.derivation.accessibility_compatibility_identity == compatibility.identity


@pytest.mark.parametrize(
    ("axis", "field", "foreign"),
    (
        ("motor", "road_derivation_identity", b"foreign-road-derivation"),
        ("motor", "graph_compatibility_identity", b"foreign-road-graph"),
        ("motor", "drive_budget_policy_identity", b"foreign-drive-budget"),
        ("pedestrian", "pedestrian_derivation_identity", b"foreign-ped-derivation"),
        ("pedestrian", "walking_budget_policy_identity", b"foreign-walk-budget"),
    ),
)
def test_accessibility_compatibility_rejects_foreign_upstream_identity(axis, field, foreign):
    _, motor, ped, _, common = _base_snapshot_inputs_with_compatibility()
    if axis == "motor":
        common["motor_reachability"] = replace(motor, **{field: sha256_bytes(foreign)})
    else:
        common["pedestrian_reachability"] = replace(ped, **{field: sha256_bytes(foreign)})
    with pytest.raises(ValueError):
        build_parking_snapshot(**common)


def test_accessibility_compatibility_identity_changes_measurement_and_snapshot_identity():
    _, motor, ped, compatibility, common = _base_snapshot_inputs_with_compatibility()
    a = build_parking_snapshot(**common)
    changed = replace(compatibility, compatibility_version="v2")
    b = build_parking_snapshot(**{**common, "accessibility_compatibility": changed})
    assert a.derivation.measurement_identity != b.derivation.measurement_identity
    assert a.snapshot.snapshot_id != b.snapshot.snapshot_id
    assert a.derivation.motor_reachability_identity == b.derivation.motor_reachability_identity
    assert a.derivation.pedestrian_reachability_identity == b.derivation.pedestrian_reachability_identity


def test_dynamic_manifest_requires_explicit_link_compatibility():
    static_manifest = source_manifest(content=b"static")
    dynamic_manifest = source_manifest(
        content=b"dynamic", provider="parking_api", role=ParkingSourceRole.DYNAMIC_AVAILABILITY,
        authority=ParkingSourceAuthority.OTHER, completeness=ParkingSourceCompleteness.UNKNOWN,
        media_type="application/json",
    )
    with pytest.raises(ValueError):
        ParkingSourceBundle("site_parking_bundle", "v1", static_manifest, dynamic_manifest)


def test_dynamic_link_policy_rejects_foreign_inventory_or_dynamic_manifest():
    static_manifest = source_manifest(content=b"static")
    dynamic_manifest = source_manifest(
        content=b"dynamic", provider="parking_api", role=ParkingSourceRole.DYNAMIC_AVAILABILITY,
        authority=ParkingSourceAuthority.OTHER, completeness=ParkingSourceCompleteness.UNKNOWN,
        media_type="application/json",
    )
    good = dynamic_link_policy(static_manifest, dynamic_manifest)
    with pytest.raises(ValueError):
        ParkingSourceBundle(
            "site_parking_bundle", "v1", static_manifest, dynamic_manifest,
            replace(good, inventory_manifest_identity=sha256_bytes(b"foreign-inventory")),
        )
    with pytest.raises(ValueError):
        ParkingSourceBundle(
            "site_parking_bundle", "v1", static_manifest, dynamic_manifest,
            replace(good, dynamic_manifest_identity=sha256_bytes(b"foreign-dynamic")),
        )


def test_shared_canonical_dynamic_link_rejects_arbitrary_source_entity_reassignment():
    manifest, mapping, _, raw, inv = parsed_inventory((static_row(capacity="10"),))
    pid = inv.facilities[0].parking_id
    motor, ped = reachability(manifest, (pid,))
    dyn_manifest, dyn_raw, dyn = build_dynamic_for(manifest, pid, available=4, occupancy=0.6, timestamp=NOW)
    bad_record = replace(dyn.records[0], source_entity_id="api-1")
    bad_dyn = replace(dyn, records=(bad_record,))
    bundle = ParkingSourceBundle(
        "site_parking_bundle", "v1", manifest, dyn_manifest,
        dynamic_link_policy(manifest, dyn_manifest),
    )
    with pytest.raises(ValueError):
        build_parking_snapshot(
            source_bundle=bundle,
            inventory_source=raw,
            inventory=inv,
            coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
            mapping_policy=mapping,
            eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
            accessibility_compatibility=accessibility_compatibility(motor, ped),
            motor_reachability=motor,
            pedestrian_reachability=ped,
            dynamic_source=dyn_raw,
            dynamic_evidence=bad_dyn,
            generated_at=NOW,
        )


def test_dynamic_link_policy_change_changes_measurement_identity():
    manifest, mapping, _, raw, inv = parsed_inventory((static_row(capacity="10"),))
    pid = inv.facilities[0].parking_id
    motor, ped = reachability(manifest, (pid,))
    dyn_manifest, dyn_raw, dyn = build_dynamic_for(manifest, pid, available=4, occupancy=0.6, timestamp=NOW)
    link_v1 = dynamic_link_policy(manifest, dyn_manifest, version="v1")
    link_v2 = dynamic_link_policy(manifest, dyn_manifest, version="v2")
    common = dict(
        inventory_source=raw,
        inventory=inv,
        coverage=ParkingCoverageEvidence(manifest.identity, "site_parking_scope", ParkingCoverageState.SUFFICIENT, 1),
        mapping_policy=mapping,
        eligibility_policy=ParkingEligibilityPolicy("generic_parking", "v1"),
        accessibility_compatibility=accessibility_compatibility(motor, ped),
        motor_reachability=motor,
        pedestrian_reachability=ped,
        dynamic_source=dyn_raw,
        dynamic_evidence=dyn,
        generated_at=NOW,
    )
    a = build_parking_snapshot(
        source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest, dyn_manifest, link_v1),
        **common,
    )
    b = build_parking_snapshot(
        source_bundle=ParkingSourceBundle("site_parking_bundle", "v1", manifest, dyn_manifest, link_v2),
        **common,
    )
    assert link_v1.identity != link_v2.identity
    assert a.derivation.dynamic_link_policy_identity != b.derivation.dynamic_link_policy_identity
    assert a.derivation.measurement_identity != b.derivation.measurement_identity
    assert a.snapshot.snapshot_id != b.snapshot.snapshot_id
