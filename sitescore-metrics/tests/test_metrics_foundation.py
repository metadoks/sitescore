from dataclasses import replace
from datetime import date, datetime, timezone
import inspect, math
import pytest

from sitescore_data.enums import AvailabilityState, CalibrationState, DataQualityState, GeographyType, ScoreEligibility, ValidityState
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.geography import GeographyRef
from sitescore_data.schemas.demographics import AgeCohortPopulation, DemographicSnapshot
from sitescore_data.schemas.pedestrian import IsochroneSnapshot
from sitescore_data.schemas.transit import TransitObservation, TransitServiceWindow, TransitSnapshot
from sitescore_data.schemas.parking import ParkingSnapshot
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.road import RoadAccessSnapshot, RoadOriginQuality

from sitescore_metrics import *

NOW=datetime(2026,8,14,12,0,tzinfo=timezone.utc)

def mv(value,unit,ref="src",method="m-v1", *, availability=AvailabilityState.AVAILABLE, quality=DataQualityState.FULL, calibration=CalibrationState.CALIBRATED):
    if availability is AvailabilityState.AVAILABLE:
        refs=(ref,); eligibility=ScoreEligibility.ELIGIBLE
    else:
        refs=(); eligibility=ScoreEligibility.INELIGIBLE
    return MetricValue(value,unit,availability,quality,eligibility,calibration,False,False,refs,method,())

def subject(kind=SubjectKind.SITE, *refs):
    return MeasurementSubject(kind,"sitescore.measurement.subject","1.0",(("semantic_key","subject-a"),),tuple(sorted(refs or ("scope:a",))))

def demo():
    g=GeographyRef(GeographyType.BLOCK_GROUP,"360610001001","BG1","US","geo_src","2025")
    return DemographicSnapshot(g,mv(400,"people","acs"),(AgeCohortPopulation("age_18_24",18,25,100,.25),),mv(80000,"usd_per_household","acs","acs-income-v1"),("acs",),AvailabilityState.AVAILABLE,DataQualityState.FULL,NOW)

def iso():
    return IsochroneSnapshot("iso_1","walk_1",mv(1.5,"km2","routing","iso-area-v1"),("routing",),AvailabilityState.AVAILABLE,DataQualityState.FULL,"iso-v1",NOW)

def transit():
    win=TransitServiceWindow("America/New_York",ValidityState.VALID,date(2026,1,1),date(2026,12,31),tuple(date(2026,8,d) for d in range(3,10)),"typical-week-v1","gtfs-calendar-v1")
    obs=tuple(TransitObservation(h,2,.5,2.5) for h in range(168))
    return TransitSnapshot("transit_1",(),win,obs,mv(2.5,"departure_equivalents_per_hour","gtfs","transit-v1"),None,"bundle:abc",("gtfs",),AvailabilityState.AVAILABLE,DataQualityState.FULL,NOW)

def parking():
    return ParkingSnapshot("parking_1",(),mv(1,"count","park"),mv(42,"spaces","park","parking-v1"),mv(0,"count","park"),mv(120.0,"m","park","curb-v1"),mv(0,"spaces","park"),False,("park",),AvailabilityState.AVAILABLE,DataQualityState.FULL,ScoreEligibility.ELIGIBLE,NOW)

def competition():
    return CompetitionSnapshot("comp_1","measurement_def_1",None,None,(),AvailabilityState.UNKNOWN,DataQualityState.MISSING,NOW)

def road():
    return RoadAccessSnapshot("road_1","origin_1",RoadOriginQuality.UNRESOLVED,"drive","1.0",(),None,(),AvailabilityState.UNKNOWN,DataQualityState.MISSING,NOW)


def test_precision_policy_full_float_only():
    assert FULL_BINARY64.mode is MeasurementPrecisionMode.FULL_BINARY64
    with pytest.raises(ValueError): MeasurementPrecisionPolicy("p","1",MeasurementPrecisionMode.FULL_BINARY64,0.01)

def test_precision_policy_version_changes_identity():
    assert MeasurementPrecisionPolicy("p","1").identity_id != MeasurementPrecisionPolicy("p","2").identity_id

def test_subject_is_content_bound_and_kind_typed():
    s=subject(); assert len(s.identity_id)==64
    with pytest.raises(TypeError): MeasurementSubject("site","x","1",(("a","b"),),("r",))

def test_subject_payload_order_must_be_canonical():
    with pytest.raises(ValueError): MeasurementSubject(SubjectKind.SITE,"x","1",(("b","1"),("a","2")),("r",))

def test_household_income_passthrough():
    d=demo(); s=subject(SubjectKind.SITE,f"geography:{d.geography_ref.geography_id}")
    r=measure_household_income(s,d)
    assert r.metric_value is d.household_income and r.metric_value.value==80000 and r.definition.unit=="usd_per_household"

def test_walk_area_passthrough():
    i=iso(); r=measure_walkable_reach_area(subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"),i)
    assert r.metric_value is i.area_km2 and r.metric_value.value==1.5

def test_transit_passthrough_and_bundle_binding():
    t=transit(); s=subject(SubjectKind.SITE,f"transit:{t.snapshot_id}")
    r=measure_transit_service(s,t,expected_source_bundle_fingerprint="bundle:abc")
    assert r.metric_value is t.service_departure_equivalents_per_hour
    assert dict(r.source_bundle_compatibility)["transit_source_bundle_fingerprint"]=="bundle:abc"
    with pytest.raises(ValueError): measure_transit_service(s,t,expected_source_bundle_fingerprint="foreign")

def test_parking_passthroughs_stay_dimensionally_separate():
    p=parking(); s=subject(SubjectKind.SITE,f"parking:{p.snapshot_id}")
    cap=measure_parking_public_offstreet_capacity(s,p); curb=measure_parking_legal_curb_length(s,p)
    assert cap.metric_value.value==42 and cap.metric_value.unit=="spaces"
    assert curb.metric_value.value==120 and curb.metric_value.unit=="m"

def test_foreign_subject_evidence_rejected():
    with pytest.raises(ValueError): measure_walkable_reach_area(subject(),iso())

def test_generated_at_does_not_change_measurement_identity():
    i=iso(); s=subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}")
    a=measure_walkable_reach_area(s,i)
    b=measure_walkable_reach_area(s,replace(i,generated_at=datetime(2027,1,1,tzinfo=timezone.utc)))
    assert a.measurement_id==b.measurement_id

def test_subject_kind_changes_measurement_identity_but_not_algorithm_value():
    i=iso(); site=subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"); bench=subject(SubjectKind.BENCHMARK_CELL,f"catchment:{i.catchment_ref}")
    a=measure_walkable_reach_area(site,i); b=measure_walkable_reach_area(bench,i)
    assert a.metric_value.value==b.metric_value.value and a.definition.identity_id==b.definition.identity_id and a.policy.identity_id==b.policy.identity_id
    assert a.measurement_id != b.measurement_id

def test_foreign_policy_version_rejected_by_canonical_registry():
    i=iso(); s=subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"); r=measure_walkable_reach_area(s,i)
    p=MetricDerivationPolicy("isochrone_area_passthrough","2.0","walkable_reach_area_km2",DerivationStrategy.PASS_THROUGH_PROVIDER_DERIVED)
    with pytest.raises(ValueError):
        DerivedMetricMeasurement(r.definition,p,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_precision_change_changes_measurement_identity():
    i=iso(); s=subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"); a=measure_walkable_reach_area(s,i)
    b=measure_walkable_reach_area(s,i,precision_policy=MeasurementPrecisionPolicy("real_unit_full_binary64","2.0"))
    assert a.measurement_id != b.measurement_id

def test_unit_mismatch_rejected_at_result_contract():
    i=iso(); s=subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"); r=measure_walkable_reach_area(s,i)
    bad=replace(r.metric_value,unit="m2")
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,bad,bad.method_version,bad.reason_codes)

def test_fake_input_evidence_rejected():
    class Fake: pass
    with pytest.raises(TypeError): MetricEvidence(Fake(),"fake")

def test_detached_inputs_api_absent():
    assert "input_ids" not in inspect.signature(DerivedMetricMeasurement).parameters

def test_available_measurement_cannot_use_unresolved_policy():
    i=iso(); s=subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"); r=measure_walkable_reach_area(s,i)
    unresolved=MetricDerivationPolicy("u","1","walkable_reach_area_km2",DerivationStrategy.UNRESOLVED_REDUCTION)
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,unresolved,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes)

def test_walkable_population_policy_unresolved_not_zero():
    d,i=demo(),iso(); r=unresolved_walkable_population(subject(),d,i)
    assert r.metric_value.value is None and r.metric_value.availability is AvailabilityState.UNKNOWN

def test_target_population_density_policy_unresolved():
    r=unresolved_target_population_density(subject(),demo()); assert r.metric_value.value is None

def test_income_ratio_denominator_unresolved():
    r=unresolved_household_income_ratio(subject(),demo()); assert r.metric_value.value is None

def test_competition_reduction_unresolved_and_definition_bound():
    c=competition(); r=unresolved_competition_pressure(subject(),c,expected_measurement_definition_id="measurement_def_1")
    assert r.metric_value.value is None and dict(r.source_bundle_compatibility)["competition_measurement_definition_id"]=="measurement_def_1"
    with pytest.raises(ValueError): unresolved_competition_pressure(subject(),c,expected_measurement_definition_id="other")

def test_road_reduction_unresolved():
    r=unresolved_road_reachable_area(subject(),road()); assert r.metric_value.value is None and r.metric_value.unit=="km2"

def test_missing_is_not_zero_passthrough():
    i=iso(); missing=replace(i,area_km2=MetricValue(None,"km2",AvailabilityState.MISSING,DataQualityState.MISSING,ScoreEligibility.INELIGIBLE,CalibrationState.UNCALIBRATED,False,False,(),"iso-area-v1",("missing",)),source_refs=(),availability=AvailabilityState.MISSING,data_quality=DataQualityState.MISSING)
    r=measure_walkable_reach_area(subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"),missing)
    assert r.metric_value.value is None and r.metric_value.availability is AvailabilityState.MISSING

def test_input_order_is_canonical_and_duplicate_rejected():
    d,i=demo(),iso(); s=subject(); e1=MetricEvidence(d,"demographic_snapshot"); e2=MetricEvidence(i,"isochrone_snapshot")
    m=unresolved_walkable_population(s,d,i)
    assert tuple(x.identity_id for x in m.inputs)==tuple(sorted((e1.identity_id,e2.identity_id)))
    with pytest.raises(ValueError): DerivedMetricMeasurement(m.definition,m.policy,m.precision_policy,m.subject,(e1,e1),m.metric_value,m.method_version,m.reason_codes)

def test_nonfinite_metric_value_cannot_be_constructed():
    with pytest.raises(ValueError): mv(math.inf,"km2")

def test_no_normalized_metric_definitions():
    assert all(d.unit != "score_0_100" for d in DEFINITIONS.values())
    assert not any("ecdf" in d.metric_key.lower() or "percentile" in d.metric_key.lower() for d in DEFINITIONS.values())


def test_household_income_site_benchmark_parity():
    d=demo(); ref=f"geography:{d.geography_ref.geography_id}"
    a=measure_household_income(subject(SubjectKind.SITE,ref),d)
    b=measure_household_income(subject(SubjectKind.BENCHMARK_CELL,ref),d)
    assert (a.metric_value.value,a.metric_value.unit,a.definition.identity_id,a.policy.identity_id)==(b.metric_value.value,b.metric_value.unit,b.definition.identity_id,b.policy.identity_id)

def test_transit_site_benchmark_parity():
    t=transit(); ref=f"transit:{t.snapshot_id}"
    a=measure_transit_service(subject(SubjectKind.SITE,ref),t,expected_source_bundle_fingerprint=t.source_bundle_fingerprint)
    b=measure_transit_service(subject(SubjectKind.BENCHMARK_CELL,ref),t,expected_source_bundle_fingerprint=t.source_bundle_fingerprint)
    assert (a.metric_value.value,a.metric_value.unit,a.definition.identity_id,a.policy.identity_id)==(b.metric_value.value,b.metric_value.unit,b.definition.identity_id,b.policy.identity_id)

def test_parking_capacity_site_benchmark_parity():
    p=parking(); ref=f"parking:{p.snapshot_id}"
    a=measure_parking_public_offstreet_capacity(subject(SubjectKind.SITE,ref),p)
    b=measure_parking_public_offstreet_capacity(subject(SubjectKind.BENCHMARK_CELL,ref),p)
    assert (a.metric_value.value,a.metric_value.unit,a.definition.identity_id,a.policy.identity_id)==(b.metric_value.value,b.metric_value.unit,b.definition.identity_id,b.policy.identity_id)

def test_parking_curb_site_benchmark_parity():
    p=parking(); ref=f"parking:{p.snapshot_id}"
    a=measure_parking_legal_curb_length(subject(SubjectKind.SITE,ref),p)
    b=measure_parking_legal_curb_length(subject(SubjectKind.BENCHMARK_CELL,ref),p)
    assert (a.metric_value.value,a.metric_value.unit,a.definition.identity_id,a.policy.identity_id)==(b.metric_value.value,b.metric_value.unit,b.definition.identity_id,b.policy.identity_id)

def test_semantic_source_ref_order_does_not_change_evidence_identity():
    i=iso()
    # Use a metric/snapshot pair with two source refs while preserving frozen coverage semantics.
    m=replace(i.area_km2,source_refs=("routing","secondary"))
    a=replace(i,area_km2=m,source_refs=("routing","secondary"))
    b=replace(i,area_km2=replace(m,source_refs=("secondary","routing")),source_refs=("secondary","routing"))
    assert MetricEvidence(a,"isochrone_snapshot").identity_id == MetricEvidence(b,"isochrone_snapshot").identity_id

def test_metric_evidence_role_changes_identity():
    i=iso()
    assert MetricEvidence(i,"isochrone_snapshot").identity_id != MetricEvidence(i,"other_role").identity_id

def test_measurement_definition_unit_change_changes_identity():
    d=DEFINITIONS["walkable_reach_area_km2"]
    other=MetricDefinition(d.metric_key,d.definition_version,"m2",d.implementation_status)
    assert d.identity_id != other.identity_id

def test_public_measurement_has_no_caller_measurement_id_field():
    assert "measurement_id" not in inspect.signature(DerivedMetricMeasurement).parameters

def test_public_evidence_has_no_detached_evidence_id_field():
    assert "identity_id" not in inspect.signature(MetricEvidence).parameters


def test_direct_pass_through_cannot_replace_snapshot_metric_with_fake_numeric_value():
    i=iso(); s=subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"); legit=measure_walkable_reach_area(s,i)
    fake=replace(i.area_km2,value=999.0)
    with pytest.raises(ValueError):
        DerivedMetricMeasurement(legit.definition,legit.policy,legit.precision_policy,legit.subject,legit.inputs,fake,fake.method_version,fake.reason_codes)

def test_direct_transit_result_cannot_drop_bundle_lineage():
    t=transit(); s=subject(SubjectKind.SITE,f"transit:{t.snapshot_id}"); legit=measure_transit_service(s,t,expected_source_bundle_fingerprint=t.source_bundle_fingerprint)
    with pytest.raises(ValueError):
        DerivedMetricMeasurement(legit.definition,legit.policy,legit.precision_policy,legit.subject,legit.inputs,legit.metric_value,legit.method_version,legit.reason_codes,())

def test_direct_resolved_result_cannot_attach_foreign_subject():
    i=iso(); legit=measure_walkable_reach_area(subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"),i)
    with pytest.raises(ValueError):
        DerivedMetricMeasurement(legit.definition,legit.policy,legit.precision_policy,subject(),legit.inputs,legit.metric_value,legit.method_version,legit.reason_codes)

def test_direct_competition_unresolved_result_must_keep_measurement_definition_lineage():
    c=competition(); legit=unresolved_competition_pressure(subject(),c,expected_measurement_definition_id=c.measurement_definition_id)
    with pytest.raises(ValueError):
        DerivedMetricMeasurement(legit.definition,legit.policy,legit.precision_policy,legit.subject,legit.inputs,legit.metric_value,legit.method_version,legit.reason_codes,())

def test_unresolved_policy_cannot_emit_numeric_even_if_availability_not_available():
    r=unresolved_road_reachable_area(subject(),road())
    bad=MetricValue(1.0,"km2",AvailabilityState.AVAILABLE,DataQualityState.FULL,ScoreEligibility.ELIGIBLE,CalibrationState.CALIBRATED,False,False,("x",),r.method_version,())
    with pytest.raises(ValueError):
        DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,bad,bad.method_version,bad.reason_codes,r.source_bundle_compatibility)


# --- Final contract-integrity hardening: METRIC-H001 / METRIC-H002 ---

def _rebuild_definition(d):
    return MetricDefinition(d.metric_key,d.definition_version,d.unit,d.implementation_status)

def _rebuild_policy(p):
    return MetricDerivationPolicy(p.policy_id,p.policy_version,p.metric_key,p.strategy)

def test_h001_altered_definition_version_rejected():
    r=measure_walkable_reach_area(subject(SubjectKind.SITE,"catchment:walk_1"),iso())
    bad=MetricDefinition(r.definition.metric_key,"bogus",r.definition.unit,r.definition.implementation_status)
    with pytest.raises(ValueError): DerivedMetricMeasurement(bad,r.policy,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h001_altered_implementation_status_rejected():
    r=measure_walkable_reach_area(subject(SubjectKind.SITE,"catchment:walk_1"),iso())
    bad=MetricDefinition(r.definition.metric_key,r.definition.definition_version,r.definition.unit,MetricImplementationStatus.DEFERRED)
    with pytest.raises(ValueError): DerivedMetricMeasurement(bad,r.policy,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h001_foreign_policy_id_rejected():
    r=measure_walkable_reach_area(subject(SubjectKind.SITE,"catchment:walk_1"),iso())
    bad=MetricDerivationPolicy("foreign",r.policy.policy_version,r.policy.metric_key,r.policy.strategy)
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,bad,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h001_known_passthrough_with_unresolved_strategy_rejected():
    r=measure_walkable_reach_area(subject(SubjectKind.SITE,"catchment:walk_1"),iso())
    bad=MetricDerivationPolicy(r.policy.policy_id,r.policy.policy_version,r.policy.metric_key,DerivationStrategy.UNRESOLVED_REDUCTION)
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,bad,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h001_known_unresolved_with_passthrough_strategy_rejected():
    r=unresolved_road_reachable_area(subject(),road())
    bad=MetricDerivationPolicy(r.policy.policy_id,r.policy.policy_version,r.policy.metric_key,DerivationStrategy.PASS_THROUGH_PROVIDER_DERIVED)
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,bad,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h001_unregistered_metric_key_rejected():
    d=MetricDefinition("custom_metric","1.0","ratio",MetricImplementationStatus.STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED)
    p=MetricDerivationPolicy("custom","1.0","custom_metric",DerivationStrategy.UNRESOLVED_REDUCTION)
    e=MetricEvidence(demo(),"demographic_snapshot")
    m=MetricValue(None,"ratio",AvailabilityState.UNKNOWN,DataQualityState.MISSING,ScoreEligibility.INELIGIBLE,CalibrationState.UNCALIBRATED,False,False,("acs",),"sitescore_metrics.custom_metric.v1",("unresolved",))
    with pytest.raises(ValueError): DerivedMetricMeasurement(d,p,FULL_BINARY64,subject(),(e,),m,m.method_version,m.reason_codes)

def test_h001_semantically_reconstructed_canonical_definition_policy_accepted():
    r=measure_walkable_reach_area(subject(SubjectKind.SITE,"catchment:walk_1"),iso())
    rebuilt=DerivedMetricMeasurement(_rebuild_definition(r.definition),_rebuild_policy(r.policy),r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)
    assert rebuilt.measurement_id == r.measurement_id

@pytest.mark.parametrize("builder, wrong_evidence, wrong_role",[
    (lambda: unresolved_walkable_population(subject(),demo(),iso()), lambda: parking(), "parking_snapshot"),
    (lambda: unresolved_target_population_density(subject(),demo()), lambda: parking(), "parking_snapshot"),
    (lambda: unresolved_household_income_ratio(subject(),demo()), lambda: transit(), "transit_snapshot"),
])
def test_h002_unresolved_metrics_reject_wrong_evidence_family(builder,wrong_evidence,wrong_role):
    r=builder(); bad=(MetricEvidence(wrong_evidence(),wrong_role),)
    with pytest.raises((TypeError,ValueError)): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,bad,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h002_walkable_population_requires_exact_two_evidence_artifacts_and_roles():
    r=unresolved_walkable_population(subject(),demo(),iso())
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,(r.inputs[0],),r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)
    extra=MetricEvidence(parking(),"parking_snapshot")
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,tuple(sorted(r.inputs+(extra,),key=lambda e:e.identity_id)),r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)
    d=demo(); i=iso(); wrong=(MetricEvidence(d,"wrong_role"),MetricEvidence(i,"isochrone_snapshot"))
    wrong=tuple(sorted(wrong,key=lambda e:e.identity_id))
    with pytest.raises((TypeError,ValueError)): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,wrong,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h002_unresolved_source_refs_are_exactly_derived_from_evidence():
    r=unresolved_walkable_population(subject(),demo(),iso())
    bad=replace(r.metric_value,source_refs=("invented",))
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,bad,bad.method_version,bad.reason_codes,r.source_bundle_compatibility)

def test_h002_unresolved_reason_is_canonical_and_not_caller_invented():
    r=unresolved_target_population_density(subject(),demo())
    bad=replace(r.metric_value,reason_codes=("caller_reason",))
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,bad,bad.method_version,bad.reason_codes,r.source_bundle_compatibility)

def test_h002_unresolved_method_version_is_canonical():
    r=unresolved_household_income_ratio(subject(),demo())
    bad=replace(r.metric_value,method_version="caller-method")
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,bad,bad.method_version,bad.reason_codes,r.source_bundle_compatibility)

@pytest.mark.parametrize("field,value",[
    ("availability",AvailabilityState.MISSING),
    ("data_quality",DataQualityState.FULL),
    ("score_eligibility",ScoreEligibility.ELIGIBLE),
    ("calibration_state",CalibrationState.CALIBRATED),
    ("is_estimate",True),
    ("is_proxy",True),
])
def test_h002_unresolved_metricvalue_state_is_exact(field,value):
    r=unresolved_road_reachable_area(subject(),road())
    with pytest.raises((ValueError,TypeError)):
        bad=replace(r.metric_value,**{field:value})
        DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,bad,bad.method_version,bad.reason_codes,r.source_bundle_compatibility)

def test_h002_unresolved_metrics_reject_arbitrary_compatibility_entries():
    a=unresolved_target_population_density(subject(),demo())
    with pytest.raises(ValueError): DerivedMetricMeasurement(a.definition,a.policy,a.precision_policy,a.subject,a.inputs,a.metric_value,a.method_version,a.reason_codes,(("x","y"),))
    b=unresolved_household_income_ratio(subject(),demo())
    with pytest.raises(ValueError): DerivedMetricMeasurement(b.definition,b.policy,b.precision_policy,b.subject,b.inputs,b.metric_value,b.method_version,b.reason_codes,(("x","y"),))

def test_h002_competition_requires_exact_evidence_cardinality_role_and_metadata():
    c=competition(); r=unresolved_competition_pressure(subject(),c,expected_measurement_definition_id=c.measurement_definition_id)
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs+(MetricEvidence(demo(),"demographic_snapshot"),),r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)
    bad=replace(r.metric_value,reason_codes=("other",))
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,bad,bad.method_version,bad.reason_codes,r.source_bundle_compatibility)

def test_h002_road_requires_exact_evidence_cardinality_and_routing_compatibility():
    r=unresolved_road_reachable_area(subject(),road())
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,r.inputs,r.metric_value,r.method_version,r.reason_codes,(("routing_profile_id","drive"),))
    extra=MetricEvidence(demo(),"demographic_snapshot")
    inputs=tuple(sorted(r.inputs+(extra,),key=lambda e:e.identity_id))
    with pytest.raises(ValueError): DerivedMetricMeasurement(r.definition,r.policy,r.precision_policy,r.subject,inputs,r.metric_value,r.method_version,r.reason_codes,r.source_bundle_compatibility)

def test_h002_all_ten_metrics_have_exact_canonical_evidence_cardinality():
    d,i,t,p,c,rd=demo(),iso(),transit(),parking(),competition(),road()
    measurements=(
        unresolved_walkable_population(subject(),d,i),
        unresolved_target_population_density(subject(),d),
        measure_household_income(subject(SubjectKind.SITE,f"geography:{d.geography_ref.geography_id}"),d),
        unresolved_household_income_ratio(subject(),d),
        unresolved_competition_pressure(subject(),c,expected_measurement_definition_id=c.measurement_definition_id),
        measure_walkable_reach_area(subject(SubjectKind.SITE,f"catchment:{i.catchment_ref}"),i),
        measure_transit_service(subject(SubjectKind.SITE,f"transit:{t.snapshot_id}"),t,expected_source_bundle_fingerprint=t.source_bundle_fingerprint),
        unresolved_road_reachable_area(subject(),rd),
        measure_parking_public_offstreet_capacity(subject(SubjectKind.SITE,f"parking:{p.snapshot_id}"),p),
        measure_parking_legal_curb_length(subject(SubjectKind.SITE,f"parking:{p.snapshot_id}"),p),
    )
    expected={
        "walkable_population":2,
        "target_population_density":1,
        "household_income":1,
        "household_income_ratio":1,
        "competition_pressure":1,
        "walkable_reach_area_km2":1,
        "transit_service_departure_equivalents_per_hour":1,
        "road_reachable_area_km2":1,
        "parking_public_offstreet_capacity":1,
        "parking_legal_curb_length_m":1,
    }
    assert {m.definition.metric_key:len(m.inputs) for m in measurements} == expected
