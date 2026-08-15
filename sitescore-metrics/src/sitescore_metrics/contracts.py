from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any
from sitescore_data.schemas.common import MetricValue
from sitescore_data.enums import AvailabilityState, DataQualityState, ScoreEligibility, CalibrationState
from sitescore_data.schemas.demographics import DemographicSnapshot
from sitescore_data.schemas.pedestrian import IsochroneSnapshot
from sitescore_data.schemas.transit import TransitSnapshot
from sitescore_data.schemas.parking import ParkingSnapshot
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.road import RoadAccessSnapshot
from .enums import SubjectKind, MeasurementPrecisionMode, MetricImplementationStatus, DerivationStrategy
from .hashing import semantic_hash

_ALLOWED_EVIDENCE = (DemographicSnapshot, IsochroneSnapshot, TransitSnapshot, ParkingSnapshot, CompetitionSnapshot, RoadAccessSnapshot)

def _text(v, name):
    if not isinstance(v, str): raise TypeError(f"{name} must be str")
    if not v or v != v.strip(): raise ValueError(f"{name} must be non-empty and trimmed")
    return v

@dataclass(frozen=True, slots=True)
class MeasurementPrecisionPolicy:
    policy_id: str
    policy_version: str
    mode: MeasurementPrecisionMode = MeasurementPrecisionMode.FULL_BINARY64
    quantization_parameter: None = None
    @property
    def identity_id(self): return semantic_hash(self.semantic_record())
    def semantic_record(self):
        _text(self.policy_id, "policy_id"); _text(self.policy_version, "policy_version")
        if not isinstance(self.mode, MeasurementPrecisionMode): raise TypeError("mode must be MeasurementPrecisionMode")
        if self.mode is not MeasurementPrecisionMode.FULL_BINARY64 or self.quantization_parameter is not None:
            raise ValueError("V1 permits only FULL_BINARY64 with no quantization")
        return {"policy_id":self.policy_id,"policy_version":self.policy_version,"mode":self.mode.value,"quantization_parameter":None}
    def __post_init__(self): self.semantic_record()

@dataclass(frozen=True, slots=True)
class MeasurementSubject:
    kind: SubjectKind
    subject_contract: str
    subject_contract_version: str
    semantic_payload: tuple[tuple[str, str], ...]
    scope_refs: tuple[str, ...]
    @property
    def identity_id(self): return semantic_hash(self.semantic_record())
    def semantic_record(self):
        if not isinstance(self.kind, SubjectKind): raise TypeError("kind must be SubjectKind")
        _text(self.subject_contract,"subject_contract"); _text(self.subject_contract_version,"subject_contract_version")
        if not isinstance(self.semantic_payload, tuple) or not self.semantic_payload: raise ValueError("semantic_payload must be a non-empty tuple")
        keys=[]
        for item in self.semantic_payload:
            if not isinstance(item, tuple) or len(item)!=2: raise TypeError("semantic_payload items must be (key,value) tuples")
            k,v=item; _text(k,"semantic payload key"); _text(v,"semantic payload value"); keys.append(k)
        if len(set(keys)) != len(keys) or tuple(keys)!=tuple(sorted(keys)): raise ValueError("semantic_payload must have unique canonical-sorted keys")
        if not isinstance(self.scope_refs, tuple) or not self.scope_refs: raise ValueError("scope_refs must be non-empty tuple")
        for r in self.scope_refs: _text(r,"scope_ref")
        if len(set(self.scope_refs))!=len(self.scope_refs) or self.scope_refs!=tuple(sorted(self.scope_refs)): raise ValueError("scope_refs must be unique and sorted")
        return {"kind":self.kind.value,"subject_contract":self.subject_contract,"subject_contract_version":self.subject_contract_version,"semantic_payload":self.semantic_payload,"scope_refs":self.scope_refs}
    def __post_init__(self): self.semantic_record()

@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_key: str
    definition_version: str
    unit: str
    implementation_status: MetricImplementationStatus
    @property
    def identity_id(self): return semantic_hash(self.semantic_record())
    def semantic_record(self):
        _text(self.metric_key,"metric_key"); _text(self.definition_version,"definition_version"); _text(self.unit,"unit")
        if not isinstance(self.implementation_status, MetricImplementationStatus): raise TypeError("implementation_status must be MetricImplementationStatus")
        return {"metric_key":self.metric_key,"definition_version":self.definition_version,"unit":self.unit,"implementation_status":self.implementation_status.value}
    def __post_init__(self): self.semantic_record()

@dataclass(frozen=True, slots=True)
class MetricDerivationPolicy:
    policy_id: str
    policy_version: str
    metric_key: str
    strategy: DerivationStrategy
    @property
    def identity_id(self): return semantic_hash(self.semantic_record())
    @property
    def is_resolved(self): return self.strategy is DerivationStrategy.PASS_THROUGH_PROVIDER_DERIVED
    def semantic_record(self):
        _text(self.policy_id,"policy_id"); _text(self.policy_version,"policy_version"); _text(self.metric_key,"metric_key")
        if not isinstance(self.strategy, DerivationStrategy): raise TypeError("strategy must be DerivationStrategy")
        return {"policy_id":self.policy_id,"policy_version":self.policy_version,"metric_key":self.metric_key,"strategy":self.strategy.value}
    def __post_init__(self): self.semantic_record()

@dataclass(frozen=True, slots=True)
class MetricEvidence:
    evidence: Any
    evidence_role: str
    @property
    def identity_id(self): return semantic_hash(self.semantic_record())
    def semantic_record(self):
        if not isinstance(self.evidence, _ALLOWED_EVIDENCE): raise TypeError("evidence must be an approved frozen snapshot contract")
        _text(self.evidence_role,"evidence_role")
        return {"evidence_role":self.evidence_role,"evidence":self.evidence}
    def __post_init__(self): self.semantic_record()


def _canonical_registry_pair(metric_key: str):
    # Lazy import avoids the definitions -> contracts construction cycle while
    # still making the public result contract registry-authoritative.
    from .definitions import DEFINITIONS, POLICIES
    if metric_key not in DEFINITIONS or metric_key not in POLICIES:
        raise ValueError("metric_key is not registered in the canonical V1 metric registry")
    return DEFINITIONS[metric_key], POLICIES[metric_key]


def _validate_registry_coherence(measurement):
    key = measurement.definition.metric_key
    canonical_definition, canonical_policy = _canonical_registry_pair(key)
    if measurement.definition.identity_id != canonical_definition.identity_id:
        raise ValueError("metric definition does not match the canonical V1 registry")
    if measurement.policy.identity_id != canonical_policy.identity_id:
        raise ValueError("metric derivation policy does not match the canonical V1 registry")
    if measurement.policy.metric_key != measurement.definition.metric_key:
        raise ValueError("policy metric_key mismatch")
    if canonical_definition.implementation_status is MetricImplementationStatus.PASS_THROUGH_PROVIDER_DERIVED:
        if canonical_policy.strategy is not DerivationStrategy.PASS_THROUGH_PROVIDER_DERIVED:
            raise ValueError("canonical pass-through metric requires PASS_THROUGH_PROVIDER_DERIVED strategy")
    elif canonical_definition.implementation_status is MetricImplementationStatus.STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED:
        if canonical_policy.strategy is DerivationStrategy.PASS_THROUGH_PROVIDER_DERIVED:
            raise ValueError("canonical unresolved metric cannot use pass-through derivation strategy")
    else:
        raise ValueError("V1 canonical metric registry contains unsupported implementation status")


def _canonical_source_refs(*snapshots):
    refs = []
    for snapshot in snapshots:
        refs.extend(snapshot.source_refs)
    return tuple(sorted(set(refs)))


def _canonical_unresolved_method(metric_key: str):
    return f"sitescore_metrics.{metric_key}.v1"


def _validate_exact_unresolved_metric_value(measurement, *, source_refs, reason):
    mv = measurement.metric_value
    expected_method = _canonical_unresolved_method(measurement.definition.metric_key)
    if mv.value is not None:
        raise ValueError("canonical unresolved measurement must not contain a numeric value")
    if mv.unit != measurement.definition.unit:
        raise ValueError("canonical unresolved measurement unit mismatch")
    if mv.availability is not AvailabilityState.UNKNOWN:
        raise ValueError("canonical unresolved availability must be UNKNOWN")
    if mv.data_quality is not DataQualityState.MISSING:
        raise ValueError("canonical unresolved data_quality must be MISSING")
    if mv.score_eligibility is not ScoreEligibility.INELIGIBLE:
        raise ValueError("canonical unresolved score_eligibility must be INELIGIBLE")
    if mv.calibration_state is not CalibrationState.UNCALIBRATED:
        raise ValueError("canonical unresolved calibration_state must be UNCALIBRATED")
    if mv.is_estimate or mv.is_proxy:
        raise ValueError("canonical unresolved measurement cannot be estimate/proxy")
    if mv.source_refs != source_refs:
        raise ValueError("canonical unresolved source_refs must be derived from actual evidence")
    if mv.method_version != expected_method or measurement.method_version != expected_method:
        raise ValueError("canonical unresolved method_version mismatch")
    if mv.reason_codes != (reason,) or measurement.reason_codes != (reason,):
        raise ValueError("canonical unresolved reason_codes mismatch")


def _require_exact_inputs(measurement, specs):
    if len(measurement.inputs) != len(specs):
        raise ValueError("measurement evidence cardinality does not match canonical V1 schema")
    # Inputs are identity-sorted, so compare role/type as a set of exact role/type pairs.
    expected = sorted((role, typ) for typ, role in specs)
    actual = sorted((ev.evidence_role, type(ev.evidence)) for ev in measurement.inputs)
    if len(actual) != len(expected):
        raise ValueError("measurement evidence cardinality mismatch")
    for (actual_role, actual_type), (expected_role, expected_type) in zip(actual, expected):
        if actual_role != expected_role or actual_type is not expected_type:
            raise TypeError("measurement evidence family/role does not match canonical V1 schema")
    by_role = {ev.evidence_role: ev.evidence for ev in measurement.inputs}
    return by_role


def _validate_measurement_evidence_coherence(measurement):
    key = measurement.definition.metric_key
    _validate_registry_coherence(measurement)

    # Canonical provider-derived pass-through metrics.
    if key == "household_income":
        by_role = _require_exact_inputs(measurement, ((DemographicSnapshot, "demographic_snapshot"),))
        evidence = by_role["demographic_snapshot"]
        expected = evidence.household_income
        required_scope = f"geography:{evidence.geography_ref.geography_id}"
        required_compat = {}
    elif key == "walkable_reach_area_km2":
        by_role = _require_exact_inputs(measurement, ((IsochroneSnapshot, "isochrone_snapshot"),))
        evidence = by_role["isochrone_snapshot"]
        expected = evidence.area_km2
        required_scope = f"catchment:{evidence.catchment_ref}"
        required_compat = {}
    elif key == "transit_service_departure_equivalents_per_hour":
        by_role = _require_exact_inputs(measurement, ((TransitSnapshot, "transit_snapshot"),))
        evidence = by_role["transit_snapshot"]
        expected = evidence.service_departure_equivalents_per_hour
        required_scope = f"transit:{evidence.snapshot_id}"
        required_compat = {"transit_source_bundle_fingerprint": evidence.source_bundle_fingerprint}
    elif key == "parking_public_offstreet_capacity":
        by_role = _require_exact_inputs(measurement, ((ParkingSnapshot, "parking_snapshot"),))
        evidence = by_role["parking_snapshot"]
        expected = evidence.known_public_offstreet_capacity
        required_scope = f"parking:{evidence.snapshot_id}"
        required_compat = {}
    elif key == "parking_legal_curb_length_m":
        by_role = _require_exact_inputs(measurement, ((ParkingSnapshot, "parking_snapshot"),))
        evidence = by_role["parking_snapshot"]
        expected = evidence.mapped_legal_curb_length_m
        required_scope = f"parking:{evidence.snapshot_id}"
        required_compat = {}
    else:
        expected = required_scope = None
        required_compat = None

    if measurement.policy.is_resolved:
        if expected is None:
            raise ValueError("V1 resolved derivation strategy is not implemented for this metric")
        if measurement.metric_value != expected:
            raise ValueError("pass-through output must equal the canonical MetricValue carried by actual evidence")
        if required_scope not in measurement.subject.scope_refs:
            raise ValueError("measurement subject is incompatible with actual evidence scope")
        if dict(measurement.source_bundle_compatibility) != required_compat:
            raise ValueError("source/bundle compatibility lineage does not match actual evidence")
        return

    # Canonical structural-unresolved metrics: exact evidence + exact result metadata.
    if key == "walkable_population":
        by_role = _require_exact_inputs(measurement, (
            (DemographicSnapshot, "demographic_snapshot"),
            (IsochroneSnapshot, "isochrone_snapshot"),
        ))
        source_refs = _canonical_source_refs(by_role["demographic_snapshot"], by_role["isochrone_snapshot"])
        if measurement.source_bundle_compatibility:
            raise ValueError("walkable_population has no approved compatibility lineage in V1")
        _validate_exact_unresolved_metric_value(measurement, source_refs=source_refs, reason="population_allocation_policy_unresolved")
    elif key == "target_population_density":
        by_role = _require_exact_inputs(measurement, ((DemographicSnapshot, "demographic_snapshot"),))
        source_refs = _canonical_source_refs(by_role["demographic_snapshot"])
        if measurement.source_bundle_compatibility:
            raise ValueError("target_population_density has no approved compatibility lineage in V1")
        _validate_exact_unresolved_metric_value(measurement, source_refs=source_refs, reason="target_population_definition_unresolved")
    elif key == "household_income_ratio":
        by_role = _require_exact_inputs(measurement, ((DemographicSnapshot, "demographic_snapshot"),))
        source_refs = _canonical_source_refs(by_role["demographic_snapshot"])
        if measurement.source_bundle_compatibility:
            raise ValueError("household_income_ratio has no approved compatibility lineage in V1")
        _validate_exact_unresolved_metric_value(measurement, source_refs=source_refs, reason="household_income_denominator_policy_unresolved")
    elif key == "competition_pressure":
        by_role = _require_exact_inputs(measurement, ((CompetitionSnapshot, "competition_snapshot"),))
        evidence = by_role["competition_snapshot"]
        expected_compat = {"competition_measurement_definition_id": evidence.measurement_definition_id}
        if dict(measurement.source_bundle_compatibility) != expected_compat:
            raise ValueError("competition measurement_definition lineage mismatch")
        _validate_exact_unresolved_metric_value(measurement, source_refs=_canonical_source_refs(evidence), reason="competition_reduction_policy_unresolved")
    elif key == "road_reachable_area_km2":
        by_role = _require_exact_inputs(measurement, ((RoadAccessSnapshot, "road_snapshot"),))
        evidence = by_role["road_snapshot"]
        expected_compat = {
            "routing_profile_id": evidence.routing_profile_id,
            "routing_profile_version": evidence.routing_profile_version,
        }
        if dict(measurement.source_bundle_compatibility) != expected_compat:
            raise ValueError("road routing-profile lineage mismatch")
        _validate_exact_unresolved_metric_value(measurement, source_refs=_canonical_source_refs(evidence), reason="road_reduction_policy_unresolved")
    else:
        raise ValueError("metric_key is not implemented in the canonical V1 measurement schema")

@dataclass(frozen=True, slots=True)
class DerivedMetricMeasurement:
    definition: MetricDefinition
    policy: MetricDerivationPolicy
    precision_policy: MeasurementPrecisionPolicy
    subject: MeasurementSubject
    inputs: tuple[MetricEvidence, ...]
    metric_value: MetricValue
    method_version: str
    reason_codes: tuple[str, ...]
    source_bundle_compatibility: tuple[tuple[str,str], ...] = ()
    @property
    def measurement_id(self): return semantic_hash(self.semantic_record())
    def semantic_record(self):
        if not isinstance(self.definition, MetricDefinition): raise TypeError("definition must be MetricDefinition")
        if not isinstance(self.policy, MetricDerivationPolicy): raise TypeError("policy must be MetricDerivationPolicy")
        if not isinstance(self.precision_policy, MeasurementPrecisionPolicy): raise TypeError("precision_policy must be MeasurementPrecisionPolicy")
        if not isinstance(self.subject, MeasurementSubject): raise TypeError("subject must be MeasurementSubject")
        if self.policy.metric_key != self.definition.metric_key: raise ValueError("policy metric_key mismatch")
        if not isinstance(self.inputs, tuple): raise TypeError("inputs must be tuple")
        if not self.inputs: raise ValueError("measurement requires actual input evidence")
        for x in self.inputs:
            if not isinstance(x, MetricEvidence): raise TypeError("inputs must contain MetricEvidence")
        ids=tuple(x.identity_id for x in self.inputs)
        if len(set(ids))!=len(ids) or ids!=tuple(sorted(ids)): raise ValueError("inputs must be unique and canonical-sorted by identity")
        if not isinstance(self.metric_value, MetricValue): raise TypeError("metric_value must be MetricValue")
        if self.metric_value.unit != self.definition.unit: raise ValueError("metric unit must equal definition unit")
        if self.metric_value.value is not None and not math.isfinite(float(self.metric_value.value)): raise ValueError("metric value must be finite")
        _text(self.method_version,"method_version")
        if self.metric_value.method_version != self.method_version: raise ValueError("MetricValue.method_version mismatch")
        if self.metric_value.reason_codes != self.reason_codes: raise ValueError("reason_codes must match MetricValue.reason_codes")
        if not isinstance(self.reason_codes, tuple) or len(set(self.reason_codes))!=len(self.reason_codes): raise ValueError("reason_codes must be unique tuple")
        if self.metric_value.availability.value == "available" and not self.policy.is_resolved: raise ValueError("AVAILABLE numeric measurement requires resolved derivation policy")
        if self.metric_value.availability.value == "available" and self.metric_value.value is None: raise ValueError("AVAILABLE measurement requires value")
        if not self.policy.is_resolved and self.metric_value.value is not None:
            raise ValueError("unresolved derivation policy must not produce a numeric value")
        if not isinstance(self.source_bundle_compatibility, tuple): raise TypeError("source_bundle_compatibility must be tuple")
        keys=[]
        for kv in self.source_bundle_compatibility:
            if not isinstance(kv,tuple) or len(kv)!=2: raise TypeError("compatibility items must be pairs")
            _text(kv[0],"compatibility key"); _text(kv[1],"compatibility value"); keys.append(kv[0])
        if tuple(keys)!=tuple(sorted(keys)) or len(set(keys))!=len(keys): raise ValueError("compatibility keys must be unique and sorted")
        _validate_measurement_evidence_coherence(self)
        return {"definition":self.definition,"policy":self.policy,"precision_policy":self.precision_policy,"subject":self.subject,"inputs":tuple(x.identity_id for x in self.inputs),"metric_value":self.metric_value,"method_version":self.method_version,"reason_codes":self.reason_codes,"source_bundle_compatibility":self.source_bundle_compatibility}
    def __post_init__(self): self.semantic_record()
