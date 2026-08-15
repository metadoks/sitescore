from __future__ import annotations
from sitescore_data.enums import AvailabilityState, DataQualityState, ScoreEligibility, CalibrationState
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.demographics import DemographicSnapshot
from sitescore_data.schemas.pedestrian import IsochroneSnapshot
from sitescore_data.schemas.transit import TransitSnapshot
from sitescore_data.schemas.parking import ParkingSnapshot
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.road import RoadAccessSnapshot
from .contracts import MeasurementSubject, MetricEvidence, DerivedMetricMeasurement, MetricDerivationPolicy, MeasurementPrecisionPolicy
from .definitions import DEFINITIONS, POLICIES, FULL_BINARY64


def _unknown(metric_key, subject, evidence, *, policy=None, reason, source_refs=(), compatibility=(), precision_policy=FULL_BINARY64):
    p = policy or POLICIES[metric_key]
    d = DEFINITIONS[metric_key]
    mv = MetricValue(None,d.unit,AvailabilityState.UNKNOWN,DataQualityState.MISSING,ScoreEligibility.INELIGIBLE,CalibrationState.UNCALIBRATED,False,False,tuple(sorted(set(source_refs))),f"sitescore_metrics.{metric_key}.v1",(reason,))
    return DerivedMetricMeasurement(d,p,precision_policy,subject,tuple(sorted(evidence,key=lambda e:e.identity_id)),mv,mv.method_version,mv.reason_codes,tuple(sorted(compatibility)))

def _pass(metric_key, subject, evidence_obj, metric_value, *, role, required_scope_ref=None, compatibility=(), precision_policy=FULL_BINARY64):
    if not isinstance(subject, MeasurementSubject): raise TypeError("subject must be MeasurementSubject")
    if required_scope_ref is not None and required_scope_ref not in subject.scope_refs: raise ValueError("foreign subject evidence")
    d=DEFINITIONS[metric_key]; p=POLICIES[metric_key]
    if metric_value.unit != d.unit: raise ValueError("provider metric unit mismatch")
    ev=MetricEvidence(evidence_obj,role)
    return DerivedMetricMeasurement(d,p,precision_policy,subject,(ev,),metric_value,metric_value.method_version or f"sitescore_metrics.{metric_key}.v1",metric_value.reason_codes,tuple(sorted(compatibility)))

def measure_household_income(subject: MeasurementSubject, snapshot: DemographicSnapshot, *, precision_policy=FULL_BINARY64):
    if not isinstance(snapshot,DemographicSnapshot): raise TypeError("snapshot must be DemographicSnapshot")
    geography_scope = f"geography:{snapshot.geography_ref.geography_id}"
    return _pass("household_income",subject,snapshot,snapshot.household_income,role="demographic_snapshot",required_scope_ref=geography_scope,precision_policy=precision_policy)

def measure_walkable_reach_area(subject: MeasurementSubject, snapshot: IsochroneSnapshot, *, precision_policy=FULL_BINARY64):
    if not isinstance(snapshot,IsochroneSnapshot): raise TypeError("snapshot must be IsochroneSnapshot")
    return _pass("walkable_reach_area_km2",subject,snapshot,snapshot.area_km2,role="isochrone_snapshot",required_scope_ref=f"catchment:{snapshot.catchment_ref}",precision_policy=precision_policy)

def measure_transit_service(subject: MeasurementSubject, snapshot: TransitSnapshot, *, expected_source_bundle_fingerprint: str, precision_policy=FULL_BINARY64):
    if not isinstance(snapshot,TransitSnapshot): raise TypeError("snapshot must be TransitSnapshot")
    if snapshot.source_bundle_fingerprint != expected_source_bundle_fingerprint: raise ValueError("foreign transit source bundle fingerprint")
    return _pass("transit_service_departure_equivalents_per_hour",subject,snapshot,snapshot.service_departure_equivalents_per_hour,role="transit_snapshot",required_scope_ref=f"transit:{snapshot.snapshot_id}",compatibility=(("transit_source_bundle_fingerprint",snapshot.source_bundle_fingerprint),),precision_policy=precision_policy)

def measure_parking_public_offstreet_capacity(subject: MeasurementSubject, snapshot: ParkingSnapshot, *, precision_policy=FULL_BINARY64):
    if not isinstance(snapshot,ParkingSnapshot): raise TypeError("snapshot must be ParkingSnapshot")
    return _pass("parking_public_offstreet_capacity",subject,snapshot,snapshot.known_public_offstreet_capacity,role="parking_snapshot",required_scope_ref=f"parking:{snapshot.snapshot_id}",precision_policy=precision_policy)

def measure_parking_legal_curb_length(subject: MeasurementSubject, snapshot: ParkingSnapshot, *, precision_policy=FULL_BINARY64):
    if not isinstance(snapshot,ParkingSnapshot): raise TypeError("snapshot must be ParkingSnapshot")
    return _pass("parking_legal_curb_length_m",subject,snapshot,snapshot.mapped_legal_curb_length_m,role="parking_snapshot",required_scope_ref=f"parking:{snapshot.snapshot_id}",precision_policy=precision_policy)

def unresolved_walkable_population(subject, demographic: DemographicSnapshot, isochrone: IsochroneSnapshot):
    return _unknown("walkable_population",subject,(MetricEvidence(demographic,"demographic_snapshot"),MetricEvidence(isochrone,"isochrone_snapshot")),reason="population_allocation_policy_unresolved",source_refs=tuple(sorted(set(demographic.source_refs+isochrone.source_refs))))

def unresolved_target_population_density(subject, demographic: DemographicSnapshot):
    return _unknown("target_population_density",subject,(MetricEvidence(demographic,"demographic_snapshot"),),reason="target_population_definition_unresolved",source_refs=demographic.source_refs)

def unresolved_household_income_ratio(subject, demographic: DemographicSnapshot):
    return _unknown("household_income_ratio",subject,(MetricEvidence(demographic,"demographic_snapshot"),),reason="household_income_denominator_policy_unresolved",source_refs=demographic.source_refs)

def unresolved_competition_pressure(subject, snapshot: CompetitionSnapshot, *, expected_measurement_definition_id: str):
    if not isinstance(snapshot,CompetitionSnapshot): raise TypeError("snapshot must be CompetitionSnapshot")
    if snapshot.measurement_definition_id != expected_measurement_definition_id: raise ValueError("foreign competition measurement_definition_id")
    return _unknown("competition_pressure",subject,(MetricEvidence(snapshot,"competition_snapshot"),),reason="competition_reduction_policy_unresolved",source_refs=snapshot.source_refs,compatibility=(("competition_measurement_definition_id",snapshot.measurement_definition_id),))

def unresolved_road_reachable_area(subject, snapshot: RoadAccessSnapshot):
    if not isinstance(snapshot,RoadAccessSnapshot): raise TypeError("snapshot must be RoadAccessSnapshot")
    return _unknown("road_reachable_area_km2",subject,(MetricEvidence(snapshot,"road_snapshot"),),reason="road_reduction_policy_unresolved",source_refs=snapshot.source_refs,compatibility=(("routing_profile_id",snapshot.routing_profile_id),("routing_profile_version",snapshot.routing_profile_version)))
