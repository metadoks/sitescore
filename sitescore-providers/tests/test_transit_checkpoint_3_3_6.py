from __future__ import annotations
import io, zipfile
from datetime import datetime, timezone, date
from pathlib import Path
import pytest

from sitescore_data import PersistenceClass, AvailabilityState
from sitescore_providers import ArtifactRef, PersistenceDecision, ProviderPolicyDecision, RedistributionState, CommercialUseState, sha256_bytes
from sitescore_providers.transit import *
from sitescore_providers.hashing import sha256_bytes as hbytes
from sitescore_providers.errors import ProviderInvariantError, ProviderMalformedResponseError


class Store:
    def __init__(self): self.data={}
    def put(self,*,content_hash,content):
        r=ArtifactRef(f"artifact:{content_hash.algorithm.value}/{content_hash.digest}"); self.data[str(r)]=content; return r
    def get(self,artifact_ref): return self.data[str(artifact_ref)]
    def exists(self,artifact_ref): return str(artifact_ref) in self.data


def zip_bytes(files:dict[str,str])->bytes:
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_STORED) as z:
        for n in sorted(files): z.writestr(n,files[n])
    return b.getvalue()


def base_files(*,freq:str|None=None, calendar=True, caldates:str|None=None, stop_times:str|None=None, stops:str|None=None, feed_info=True):
    f={
      'agency.txt':'agency_id,agency_name,agency_url,agency_timezone\nA,Agency,https://example.com,America/New_York\n',
      'stops.txt': stops or 'stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\nST,Station,40,-73,1,\nP1,Platform 1,40.001,-73.001,0,ST\nP2,Platform 2,40.002,-73.002,0,ST\nE1,Entrance,40,-73,2,ST\n',
      'routes.txt':'route_id,route_short_name,route_type\nR,1,3\n',
      'trips.txt':'route_id,service_id,trip_id\nR,S,T\n',
      'stop_times.txt': stop_times or 'trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nT,08:00:00,08:00:00,P1,1,0\nT,08:10:00,08:10:00,P2,2,0\n',
    }
    if calendar:
      f['calendar.txt']='service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nS,1,1,1,1,1,1,1,20260101,20261231\n'
    if caldates is not None: f['calendar_dates.txt']=caldates
    if freq is not None: f['frequencies.txt']=freq
    if feed_info: f['feed_info.txt']='feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,feed_end_date,feed_version\nX,https://x.test,en,20260101,20261231,v1\n'
    return f


def policies():
    cal=GTFSServiceCalendarPolicy('gtfs_calendar','v1')
    hier=GTFSStopHierarchyPolicy('gtfs_hierarchy','v1')
    board=TransitBoardingPolicy('gtfs_boarding','v1')
    freq=GTFSFrequencyPolicy('gtfs_frequency','v1')
    return cal,hier,board,freq


def make_bundle(files, *, release='2026-08-01', content=None):
    content=content or zip_bytes(files)
    manifest=GTFSFeedManifest('v1','feed_a','Example Transit',release,'gtfs_schedule_reference_2026','v1',hbytes(content),'static_feed','v1')
    cal,hier,board,freq=policies()
    comps=tuple(sorted((n,hbytes(v.encode())) for n,v in files.items() if n.endswith('.txt')))
    return TransitSourceBundle('bundle_a','v1',manifest,cal,hier,board,freq,comps),content


def policy():
    p=PersistenceDecision('gtfs_persist','v1',PersistenceClass.PERSIST,reason_codes=('static_feed_replay',))
    return ProviderPolicyDecision('gtfs_persist','v1',p,False,RedistributionState.UNKNOWN,CommercialUseState.UNKNOWN)


def parsed(files=None, **kwargs):
    files=files or base_files(); bundle,content=make_bundle(files); store=Store(); pol=policy()
    raw=acquire_gtfs_zip_bytes(content=content,manifest=bundle.feed_manifest,artifact_store=store,retrieved_at=datetime(2026,8,13,tzinfo=timezone.utc),persistence=pol.persistence)
    feed=parse_gtfs_zip(raw_artifact=raw,bundle=bundle,artifact_store=store,policy=pol)
    return feed,store


def reach(feed, ids=('E1',)):
    return ReachableTransitStopSet(feed.bundle.fingerprint,'pedestrian.derivation.a','walking_budget.a','network_membership','v1',tuple(sorted(ids)),'catchment.a','network_walk',('source.pedestrian',))


def week_policy(start=date(2026,8,10)):
    return TransitWeeklyProfilePolicy('weekly_profile','v1','median_same_weekday_hour',tuple(start.fromordinal(start.toordinal()+i) for i in range(7)))


def test_source_bundle_determinism_and_locator_independence():
    files=base_files(); b,c=make_bundle(files); b2,_=make_bundle(dict(reversed(list(files.items()))),content=c)
    assert b.fingerprint==b2.fingerprint
    # acquisition has no locator input at all; exact content semantics drive raw identity
    assert b.feed_manifest.identity==b2.feed_manifest.identity


def test_feed_content_change_changes_fingerprint():
    f=base_files(); b,_=make_bundle(f); f2=dict(f); f2['agency.txt']=f2['agency.txt'].replace('Agency','Agency2'); b2,_=make_bundle(f2)
    assert b.fingerprint!=b2.fingerprint


def test_mutable_release_rejected():
    files=base_files(); c=zip_bytes(files)
    with pytest.raises(ValueError): GTFSFeedManifest('v1','feed_a','X','latest','schema','v1',hbytes(c),'static','v1')


def test_calendar_weekly_and_exception_add_remove():
    cd='service_id,date,exception_type\nS,20260810,2\nS,20260816,1\n'
    feed,_=parsed(base_files(caldates=cd))
    assert not service_active(feed,'S',date(2026,8,10))
    assert service_active(feed,'S',date(2026,8,16))


def test_calendar_dates_only_supported():
    cd='service_id,date,exception_type\nS,20260810,1\n'
    feed,_=parsed(base_files(calendar=False,caldates=cd,feed_info=False))
    assert service_active(feed,'S',date(2026,8,10)); assert not service_active(feed,'S',date(2026,8,11))


def test_gtfs_over_24_time_preserved_and_binned_next_clock_day():
    st='trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nT,25:30:00,25:30:00,P1,1,0\n'
    feed,_=parsed(base_files(stop_times=st)); prof=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())
    # Monday service 25:30 lands Tuesday 01:xx => hour_of_week 25
    assert prof.exact_departures[25]==1


def test_parent_station_entrance_expands_to_platforms():
    feed,_=parsed(); refs=build_reachable_stop_refs(feed,reach(feed,('E1',)))
    assert [x.stop_id for x in refs]==['P1','P2']; assert all(x.canonical_station_id=='ST' for x in refs)


def test_malformed_parent_reference_rejected():
    stops='stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\nP1,P,40,-73,0,NOPE\n'
    with pytest.raises(ProviderMalformedResponseError): parsed(base_files(stops=stops))


def test_reachability_foreign_bundle_rejected():
    feed,_=parsed(); r=ReachableTransitStopSet('gtfs_bundle.other','ped','walk','m','v1',('P1',),'c','q',())
    with pytest.raises(ProviderInvariantError): build_reachable_stop_refs(feed,r)


def test_unknown_reachable_stop_rejected():
    feed,_=parsed()
    with pytest.raises(ProviderInvariantError): build_reachable_stop_refs(feed,reach(feed,('NOPE',)))


def test_same_trip_multiple_reachable_stops_counted_once_earliest():
    feed,_=parsed(); prof=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1','P2')),profile_policy=week_policy())
    assert prof.exact_departures[8]==1


def test_no_pickup_stop_does_not_create_supply():
    st='trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nT,08:00:00,08:00:00,P1,1,1\n'
    feed,_=parsed(base_files(stop_times=st)); prof=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())
    assert sum(prof.total_equivalents)==0


def test_frequency_exact_times_one_expands_exact_instances():
    fr='trip_id,start_time,end_time,headway_secs,exact_times\nT,08:00:00,09:00:00,1200,1\n'
    feed,_=parsed(base_files(freq=fr)); p=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())
    assert p.exact_departures[8]==3 and p.frequency_equivalents[8]==0


def test_frequency_exact_times_zero_headway_equivalents():
    fr='trip_id,start_time,end_time,headway_secs,exact_times\nT,08:00:00,09:00:00,900,0\n'
    feed,_=parsed(base_files(freq=fr)); p=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())
    assert p.exact_departures[8]==0 and p.frequency_equivalents[8]==pytest.approx(4.0)


def test_frequency_blank_exact_times_is_inexact():
    fr='trip_id,start_time,end_time,headway_secs,exact_times\nT,08:00:00,08:30:00,600,\n'
    feed,_=parsed(base_files(freq=fr)); p=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())
    assert p.frequency_equivalents[8]==pytest.approx(3.0)


def test_frequency_overlap_rejected():
    fr='trip_id,start_time,end_time,headway_secs,exact_times\nT,08:00:00,09:00:00,600,0\nT,08:30:00,10:00:00,600,0\n'
    with pytest.raises(ProviderMalformedResponseError): parsed(base_files(freq=fr))


def test_frequency_invalid_headway_rejected():
    fr='trip_id,start_time,end_time,headway_secs,exact_times\nT,08:00:00,09:00:00,0,0\n'
    with pytest.raises(ProviderMalformedResponseError): parsed(base_files(freq=fr))


def test_168_bin_ordering_and_median_policy():
    feed,_=parsed(); p=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())
    assert len(p.total_equivalents)==168
    snap=build_transit_snapshot(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy(),generated_at=datetime(2026,8,13,tzinfo=timezone.utc))
    assert tuple(o.hour_of_week for o in snap.observations)==tuple(range(168))


def test_profile_date_window_changes_derivation_identity():
    feed,_=parsed(); r=reach(feed,('P1',)); p1=build_weekly_service_profile(feed=feed,reachability=r,profile_policy=week_policy(date(2026,8,10)))
    p2=build_weekly_service_profile(feed=feed,reachability=r,profile_policy=week_policy(date(2026,8,17)))
    assert p1.derivation_identity!=p2.derivation_identity


def test_reachability_changes_derivation_not_source_bundle():
    feed,_=parsed(); p=week_policy(); r1=reach(feed,('P1',)); r2=reach(feed,('P2',))
    assert r1.source_bundle_fingerprint==r2.source_bundle_fingerprint==feed.bundle.fingerprint
    assert build_weekly_service_profile(feed=feed,reachability=r1,profile_policy=p).derivation_identity != build_weekly_service_profile(feed=feed,reachability=r2,profile_policy=p).derivation_identity


def test_valid_no_service_is_available_true_zero():
    st='trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nT,08:00:00,08:00:00,P1,1,1\n'
    feed,_=parsed(base_files(stop_times=st)); snap=build_transit_snapshot(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy(),generated_at=datetime(2026,8,13,tzinfo=timezone.utc))
    assert snap.availability is AvailabilityState.AVAILABLE
    assert snap.service_departure_equivalents_per_hour.value==0


def test_out_of_validity_not_zero():
    feed,_=parsed(); pol=TransitWeeklyProfilePolicy('weekly_profile','v1','median_same_weekday_hour',tuple(date(2027,1,4).fromordinal(date(2027,1,4).toordinal()+i) for i in range(7)))
    snap=build_transit_snapshot(feed=feed,reachability=reach(feed,('P1',)),profile_policy=pol,generated_at=datetime(2026,8,13,tzinfo=timezone.utc))
    assert snap.availability is AvailabilityState.UNKNOWN and snap.observations==() and snap.service_departure_equivalents_per_hour.value is None


def test_machine_timezone_not_used(monkeypatch):
    feed,_=parsed(); r=reach(feed,('P1',)); p=week_policy()
    a=build_weekly_service_profile(feed=feed,reachability=r,profile_policy=p)
    monkeypatch.setenv('TZ','Pacific/Honolulu')
    b=build_weekly_service_profile(feed=feed,reachability=r,profile_policy=p)
    assert a==b


def test_raw_zip_hash_must_match_manifest():
    files=base_files(); b,c=make_bundle(files); store=Store()
    with pytest.raises(ProviderInvariantError): acquire_gtfs_zip_bytes(content=c+b'x',manifest=b.feed_manifest,artifact_store=store,retrieved_at=datetime.now(timezone.utc),persistence=policy().persistence)


def test_parser_rejects_same_bytes_wrong_manifest_release():
    files=base_files(); b,c=make_bundle(files); store=Store(); pol=policy(); raw=acquire_gtfs_zip_bytes(content=c,manifest=b.feed_manifest,artifact_store=store,retrieved_at=datetime.now(timezone.utc),persistence=pol.persistence)
    wrong=GTFSFeedManifest('v1','feed_a','Example Transit','2026-09-01',b.feed_manifest.schema_version,'v1',b.feed_manifest.feed_content_hash,'static_feed','v1')
    wb=TransitSourceBundle('bundle_a','v1',wrong,*policies(),b.component_file_hashes)
    with pytest.raises(ProviderInvariantError): parse_gtfs_zip(raw_artifact=raw,bundle=wb,artifact_store=store,policy=pol)


def test_frozen_transit_snapshot_fields_and_metric_mapping():
    feed,_=parsed(); snap=build_transit_snapshot(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy(),generated_at=datetime(2026,8,13,tzinfo=timezone.utc))
    assert len(snap.observations)==168 and snap.benchmark_ref is None
    assert snap.source_bundle_fingerprint==feed.bundle.fingerprint
    assert snap.service_departure_equivalents_per_hour.unit=='departure_equivalents_per_hour'
    assert snap.service_departure_equivalents_per_hour.score_eligibility.value=='diagnostic_only'


def test_one_feed_only_namespace_explicit():
    feed,_=parsed(); assert feed.bundle.feed_manifest.feed_id=='feed_a'
    # There is one feed_manifest field, not an implicit tuple/merge surface.
    assert not hasattr(feed.bundle,'feeds')

def test_policy_change_changes_source_bundle_fingerprint_not_feed_manifest_identity():
    files=base_files(); b,c=make_bundle(files)
    alt=TransitBoardingPolicy('gtfs_boarding','v2',(0,))
    b2=TransitSourceBundle(b.bundle_id,b.bundle_version,b.feed_manifest,b.calendar_policy,b.hierarchy_policy,alt,b.frequency_policy,b.component_file_hashes)
    assert b.feed_manifest.identity==b2.feed_manifest.identity
    assert b.fingerprint!=b2.fingerprint


def test_component_file_hash_mismatch_rejected_at_parse():
    files=base_files(); b,c=make_bundle(files); bad_components=list(b.component_file_hashes); n,h=bad_components[0]; bad_components[0]=(n,hbytes(b'wrong'))
    bad=TransitSourceBundle(b.bundle_id,b.bundle_version,b.feed_manifest,b.calendar_policy,b.hierarchy_policy,b.boarding_policy,b.frequency_policy,tuple(sorted(bad_components)))
    store=Store(); pol=policy(); raw=acquire_gtfs_zip_bytes(content=c,manifest=b.feed_manifest,artifact_store=store,retrieved_at=datetime.now(timezone.utc),persistence=pol.persistence)
    with pytest.raises(ProviderInvariantError): parse_gtfs_zip(raw_artifact=raw,bundle=bad,artifact_store=store,policy=pol)


def test_trip_missing_route_reference_rejected():
    f=base_files(); f['trips.txt']='route_id,service_id,trip_id\nNOPE,S,T\n'
    with pytest.raises(ProviderMalformedResponseError): parsed(f)


def test_trip_unresolvable_service_id_rejected():
    f=base_files(); f['trips.txt']='route_id,service_id,trip_id\nR,UNKNOWN,T\n'
    with pytest.raises(ProviderMalformedResponseError): parsed(f)


def test_stop_time_missing_stop_reference_rejected():
    f=base_files(stop_times='trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nT,08:00:00,08:00:00,NOPE,1,0\n')
    with pytest.raises(ProviderMalformedResponseError): parsed(f)


def test_duplicate_stop_sequence_rejected():
    f=base_files(stop_times='trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nT,08:00:00,08:00:00,P1,1,0\nT,08:10:00,08:10:00,P2,1,0\n')
    with pytest.raises(ProviderMalformedResponseError): parsed(f)


def test_agency_timezones_must_be_single_shared_timezone():
    f=base_files(); f['agency.txt']='agency_id,agency_name,agency_url,agency_timezone\nA,A,https://a,America/New_York\nB,B,https://b,America/Chicago\n'
    with pytest.raises(ProviderMalformedResponseError): parsed(f)


def test_feed_info_validity_is_authoritative_for_zero_service_days():
    # feed_info explicitly covers date, even if service is removed that day: valid zero, not missing.
    cd='service_id,date,exception_type\nS,20260810,2\n'
    feed,_=parsed(base_files(caldates=cd)); snap=build_transit_snapshot(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy(),generated_at=datetime(2026,8,13,tzinfo=timezone.utc))
    assert snap.availability is AvailabilityState.AVAILABLE


def test_reference_dates_must_cover_all_weekdays_for_168_profile():
    feed,_=parsed(); p=TransitWeeklyProfilePolicy('weekly_profile','v1','median_same_weekday_hour',(date(2026,8,10),))
    with pytest.raises(ProviderInvariantError): build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=p)


def test_frequency_policy_does_not_turn_inexact_into_exact_departures():
    fr='trip_id,start_time,end_time,headway_secs,exact_times\nT,08:00:00,09:00:00,900,0\n'
    feed,_=parsed(base_files(freq=fr)); p=build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())
    assert sum(p.exact_departures)==0 and sum(p.frequency_equivalents)>0

def test_parser_rejects_wrong_raw_request_fingerprint():
    from dataclasses import replace
    from sitescore_providers import build_request_fingerprint
    files=base_files(); b,c=make_bundle(files); store=Store(); pol=policy(); raw=acquire_gtfs_zip_bytes(content=c,manifest=b.feed_manifest,artifact_store=store,retrieved_at=datetime.now(timezone.utc),persistence=pol.persistence)
    wrong=build_request_fingerprint(provider_key='gtfs_static',operation='other',semantic_parameters={'x':1},dataset='gtfs_schedule:feed_a',dataset_release=b.feed_manifest.dataset_release,policy_id=pol.policy_id,policy_version=pol.policy_version)
    with pytest.raises(ProviderInvariantError): parse_gtfs_zip(raw_artifact=replace(raw,request_fingerprint=wrong),bundle=b,artifact_store=store,policy=pol)


def test_parsed_feed_rejects_same_hash_wrong_source_metadata_semantics():
    from dataclasses import replace
    feed,_=parsed()
    bad=replace(feed.source_metadata,provider='other_provider')
    with pytest.raises(ValueError): replace(feed,source_metadata=bad)

def test_reachable_boarding_stop_missing_departure_is_not_silent_zero():
    st='trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type\nT,,,P1,1,0\nT,08:10:00,08:10:00,P2,2,0\n'
    feed,_=parsed(base_files(stop_times=st))
    with pytest.raises(ProviderInvariantError): build_weekly_service_profile(feed=feed,reachability=reach(feed,('P1',)),profile_policy=week_policy())


def test_reachability_identity_commits_walk_catchment_and_access_quality():
    feed,_=parsed()
    base=reach(feed,('P1',))
    other_catchment=ReachableTransitStopSet(base.source_bundle_fingerprint,base.pedestrian_derivation_identity,base.walking_budget_policy_identity,
        base.membership_method_id,base.membership_method_version,base.reachable_stop_ids,'catchment.b',base.access_geometry_quality,base.source_refs)
    other_quality=ReachableTransitStopSet(base.source_bundle_fingerprint,base.pedestrian_derivation_identity,base.walking_budget_policy_identity,
        base.membership_method_id,base.membership_method_version,base.reachable_stop_ids,base.walk_catchment_ref,'network_walk_degraded',base.source_refs)
    same=ReachableTransitStopSet(base.source_bundle_fingerprint,base.pedestrian_derivation_identity,base.walking_budget_policy_identity,
        base.membership_method_id,base.membership_method_version,base.reachable_stop_ids,base.walk_catchment_ref,base.access_geometry_quality,base.source_refs)
    assert base.identity != other_catchment.identity
    assert base.identity != other_quality.identity
    assert base.identity == same.identity
    assert base.source_bundle_fingerprint == other_catchment.source_bundle_fingerprint == other_quality.source_bundle_fingerprint


def test_reachability_identity_change_propagates_to_transit_derivation_and_snapshot():
    feed,_=parsed(); p=week_policy(); generated=datetime(2026,8,13,tzinfo=timezone.utc)
    r1=reach(feed,('P1',))
    r2=ReachableTransitStopSet(r1.source_bundle_fingerprint,r1.pedestrian_derivation_identity,r1.walking_budget_policy_identity,
        r1.membership_method_id,r1.membership_method_version,r1.reachable_stop_ids,'catchment.b',r1.access_geometry_quality,r1.source_refs)
    prof1=build_weekly_service_profile(feed=feed,reachability=r1,profile_policy=p)
    prof2=build_weekly_service_profile(feed=feed,reachability=r2,profile_policy=p)
    snap1=build_transit_snapshot(feed=feed,reachability=r1,profile_policy=p,generated_at=generated)
    snap2=build_transit_snapshot(feed=feed,reachability=r2,profile_policy=p,generated_at=generated)
    assert prof1.derivation_identity != prof2.derivation_identity
    assert snap1.snapshot_id != snap2.snapshot_id
    assert snap1.source_bundle_fingerprint == snap2.source_bundle_fingerprint == feed.bundle.fingerprint


def test_calendar_dates_only_addition_service_accepted():
    cd='service_id,date,exception_type\nS,20260810,1\n'
    feed,_=parsed(base_files(calendar=False,caldates=cd,feed_info=False))
    assert service_active(feed,'S',date(2026,8,10))


def test_calendar_dates_only_additions_and_removals_with_activation_accepted():
    cd='service_id,date,exception_type\nS,20260810,1\nS,20260811,2\n'
    feed,_=parsed(base_files(calendar=False,caldates=cd,feed_info=False))
    assert service_active(feed,'S',date(2026,8,10))
    assert not service_active(feed,'S',date(2026,8,11))


def test_calendar_dates_only_removal_service_referenced_by_trip_rejected():
    cd='service_id,date,exception_type\nS,20260810,2\nS,20260811,2\n'
    with pytest.raises(ProviderMalformedResponseError):
        parsed(base_files(calendar=False,caldates=cd,feed_info=False))


def test_base_calendar_service_with_removal_override_still_accepted():
    cd='service_id,date,exception_type\nS,20260810,2\n'
    feed,_=parsed(base_files(calendar=True,caldates=cd,feed_info=False))
    assert not service_active(feed,'S',date(2026,8,10))
    assert service_active(feed,'S',date(2026,8,11))


def test_removal_only_calendar_dates_feed_cannot_produce_available_zero():
    cd='service_id,date,exception_type\nS,20260810,2\nS,20260811,2\nS,20260812,2\nS,20260813,2\nS,20260814,2\nS,20260815,2\nS,20260816,2\n'
    with pytest.raises(ProviderMalformedResponseError):
        parsed(base_files(calendar=False,caldates=cd,feed_info=False))
