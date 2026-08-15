"""GTFS calendar/service-supply and frozen TransitSnapshot builders."""
from __future__ import annotations
from collections import defaultdict
from datetime import date,timedelta,datetime
from statistics import median
import math

from sitescore_data import AvailabilityState,CalibrationState,DataQualityState,ScoreEligibility,ValidityState
from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.transit import TransitObservation,TransitServiceWindow,TransitSnapshot,TransitStopRef
from ..hashing import CANONICALIZATION_VERSION,hash_canonical
from ..errors import ProviderInvariantError
from .models import *


def service_active(feed:ParsedGTFSFeed,service_id:str,d:date)->bool:
    base=False
    cmap={c.service_id:c for c in feed.calendars}
    c=cmap.get(service_id)
    if c and c.start_date<=d<=c.end_date: base=c.weekdays[d.weekday()]
    for ex in feed.calendar_dates:
        if ex.service_id==service_id and ex.date==d: base=ex.exception_type==1
    return base


def evaluate_validity(feed:ParsedGTFSFeed,reference_dates:tuple[date,...])->GTFSFeedValidityState:
    if feed.validity_start is None or feed.validity_end is None: return GTFSFeedValidityState.UNKNOWN
    if any(d<feed.validity_start or d>feed.validity_end for d in reference_dates): return GTFSFeedValidityState.OUT_OF_VALIDITY
    return feed.validity_state


def _canonical_station(stop:GTFSStop,byid:dict[str,GTFSStop])->str:
    if stop.location_type==1:return stop.stop_id
    if stop.location_type in {0,2,3}:return stop.parent_station or stop.stop_id
    if stop.location_type==4:
        p=byid[stop.parent_station]; return p.parent_station or p.stop_id
    raise ProviderInvariantError("unsupported location_type")


def build_reachable_stop_refs(feed:ParsedGTFSFeed,reach:ReachableTransitStopSet)->tuple[TransitStopRef,...]:
    if reach.source_bundle_fingerprint!=feed.bundle.fingerprint: raise ProviderInvariantError("reachability belongs to another GTFS bundle")
    byid={s.stop_id:s for s in feed.stops}
    unknown=set(reach.reachable_stop_ids)-set(byid)
    if unknown: raise ProviderInvariantError("reachability contains foreign/unknown GTFS stop IDs")
    # station/entrance reachability expands to child platforms; platform direct membership remains itself; generic/boarding resolve hierarchy.
    platform_ids=set()
    for sid in reach.reachable_stop_ids:
      s=byid[sid]
      if s.location_type==0: platform_ids.add(sid)
      elif s.location_type in {1,2,3}:
        station=s.stop_id if s.location_type==1 else s.parent_station
        platform_ids.update(x.stop_id for x in feed.stops if x.location_type==0 and x.parent_station==station)
      elif s.location_type==4: platform_ids.add(s.parent_station)
    out=[]
    for sid in sorted(platform_ids):
      s=byid[sid]
      if s.lat is None or s.lon is None: raise ProviderInvariantError("reachable platform lacks coordinates")
      out.append(TransitStopRef(feed_id=feed.bundle.feed_manifest.feed_id,stop_id=s.stop_id,location_type=s.location_type,parent_station_id=s.parent_station,
        canonical_station_id=_canonical_station(s,byid),latitude=s.lat,longitude=s.lon,access_geometry_quality=reach.access_geometry_quality,
        reachable_by_walk=True,walk_catchment_ref=reach.walk_catchment_ref,source_ref=feed.source_metadata.source_id))
    return tuple(sorted(out,key=lambda x:(x.feed_id,x.canonical_station_id,x.stop_id)))


def _trip_boarding_departure(feed:ParsedGTFSFeed,trip_id:str,reachable:set[str])->tuple[int,int]|None:
    boarding=[x for x in feed.stop_times if x.trip_id==trip_id and x.stop_id in reachable and x.pickup_type in feed.bundle.boarding_policy.allowed_pickup_types]
    if not boarding:return None
    if any(x.departure_seconds is None for x in boarding):
        raise ProviderInvariantError("reachable boarding-capable stop_time lacks departure_time; V1 will not infer/interpolate it")
    vals=boarding
    chosen=min(vals,key=lambda x:(x.departure_seconds,x.stop_sequence,x.stop_id))
    first=min((x for x in feed.stop_times if x.trip_id==trip_id and x.departure_seconds is not None),key=lambda x:(x.stop_sequence,x.departure_seconds),default=None)
    if first is None:return None
    return chosen.departure_seconds, chosen.departure_seconds-first.departure_seconds


def _hour_of_week(service_date:date,seconds:int)->int:
    actual=service_date+timedelta(days=seconds//86400); clock=seconds%86400
    return actual.weekday()*24+clock//3600


def _add_frequency_equivalents(arr:list[float],service_date:date,start:int,end:int,headway:int):
    # Integrate headway rate over the shifted window, split at service-clock hour boundaries.
    cur=start
    while cur<end:
      next_hour=((cur//3600)+1)*3600; stop=min(end,next_hour)
      arr[_hour_of_week(service_date,cur)] += (stop-cur)/headway
      cur=stop


def build_weekly_service_profile(*,feed:ParsedGTFSFeed,reachability:ReachableTransitStopSet,profile_policy:TransitWeeklyProfilePolicy)->TransitWeeklyServiceProfile:
    if reachability.source_bundle_fingerprint!=feed.bundle.fingerprint: raise ProviderInvariantError("foreign reachability bundle")
    validity=evaluate_validity(feed,profile_policy.reference_dates)
    if validity==GTFSFeedValidityState.OUT_OF_VALIDITY: raise ProviderInvariantError("GTFS feed is out of validity for requested profile dates")
    if validity==GTFSFeedValidityState.UNKNOWN: raise ProviderInvariantError("GTFS feed validity is unknown")
    stops=build_reachable_stop_refs(feed,reachability); reachable={s.stop_id for s in stops}
    freq_by=defaultdict(list)
    for f in feed.frequencies: freq_by[f.trip_id].append(f)

    # GTFS service-day times may exceed 24:00. Build into actual feed-local clock dates,
    # while activation remains tied to the originating service date/service_id.
    target_dates=set(profile_policy.reference_dates)
    max_seconds=0
    for x in feed.stop_times:
        if x.departure_seconds is not None: max_seconds=max(max_seconds,x.departure_seconds)
    for x in feed.frequencies: max_seconds=max(max_seconds,x.end_seconds)
    max_offset=max_seconds//86400 + 1
    first=min(profile_policy.reference_dates); last=max(profile_policy.reference_dates)
    service_dates=tuple(first-timedelta(days=i) for i in range(max_offset,0,-1))+profile_policy.reference_dates
    daily_exact={d:[0]*24 for d in profile_policy.reference_dates}
    daily_freq={d:[0.0]*24 for d in profile_policy.reference_dates}

    def add_exact(service_date:date, seconds:int):
        actual=service_date+timedelta(days=seconds//86400)
        if actual in target_dates: daily_exact[actual][(seconds%86400)//3600]+=1

    def add_freq(service_date:date,start:int,end:int,headway:int):
        cur=start
        while cur<end:
            actual=service_date+timedelta(days=cur//86400)
            next_hour=((cur//3600)+1)*3600; stop=min(end,next_hour)
            if actual in target_dates: daily_freq[actual][(cur%86400)//3600]+=(stop-cur)/headway
            cur=stop

    for d in service_dates:
      for trip in feed.trips:
        if not service_active(feed,trip.service_id,d): continue
        boarding=_trip_boarding_departure(feed,trip.trip_id,reachable)
        if boarding is None: continue
        dep,offset=boarding
        windows=freq_by.get(trip.trip_id,[])
        if not windows:
          add_exact(d,dep); continue
        for w in windows:
          if w.exact_times==1:
            t=w.start_seconds
            while t<w.end_seconds:
              add_exact(d,t+offset); t+=w.headway_secs
          else:
            add_freq(d,w.start_seconds+offset,w.end_seconds+offset,w.headway_secs)

    exact_out=[]; freq_out=[]
    for weekday in range(7):
      dates=[d for d in profile_policy.reference_dates if d.weekday()==weekday]
      if not dates: raise ProviderInvariantError("reference_dates must include every weekday")
      for hour in range(24):
        me=median(daily_exact[d][hour] for d in dates); mf=median(daily_freq[d][hour] for d in dates)
        if int(me)!=me: raise ProviderInvariantError("median exact departure count is fractional; choose an odd/consistent reference-date policy")
        exact_out.append(int(me)); freq_out.append(float(mf))
    total=tuple(e+f for e,f in zip(exact_out,freq_out))
    deriv=hash_canonical({"grammar":GTFS_DERIVATION_GRAMMAR,"canonicalization_version":CANONICALIZATION_VERSION,
      "source_bundle_fingerprint":feed.bundle.fingerprint,"reachability_identity":str(reachability.identity),"profile_policy_identity":str(profile_policy.identity)})
    return TransitWeeklyServiceProfile(tuple(exact_out),tuple(freq_out),total,feed.bundle.fingerprint,deriv)

def build_transit_snapshot(*,feed:ParsedGTFSFeed,reachability:ReachableTransitStopSet,profile_policy:TransitWeeklyProfilePolicy,generated_at:datetime)->TransitSnapshot:
    validity=evaluate_validity(feed,profile_policy.reference_dates)
    source_refs=tuple(sorted(set((feed.source_metadata.source_id,)+reachability.source_refs)))
    validity_map={GTFSFeedValidityState.VALID:ValidityState.VALID,GTFSFeedValidityState.DERIVED_VALIDITY:ValidityState.DERIVED_VALIDITY,GTFSFeedValidityState.OUT_OF_VALIDITY:ValidityState.OUT_OF_VALIDITY,GTFSFeedValidityState.UNKNOWN:ValidityState.UNKNOWN}
    window=TransitServiceWindow(timezone=feed.agency_timezone,validity_state=validity_map[validity],validity_start=feed.validity_start,validity_end=feed.validity_end,
      reference_dates=(() if validity==GTFSFeedValidityState.OUT_OF_VALIDITY else profile_policy.reference_dates),
      temporal_policy_version=f"{profile_policy.policy_id}.{profile_policy.policy_version}.{profile_policy.identity.digest}",
      service_calendar_version=f"{feed.bundle.calendar_policy.policy_id}.{feed.bundle.calendar_policy.policy_version}.{feed.bundle.calendar_policy.identity.digest}")
    stops=build_reachable_stop_refs(feed,reachability)
    if validity in {GTFSFeedValidityState.OUT_OF_VALIDITY,GTFSFeedValidityState.UNKNOWN}:
      availability=AvailabilityState.UNKNOWN; quality=DataQualityState.MISSING if validity==GTFSFeedValidityState.OUT_OF_VALIDITY else DataQualityState.DEGRADED
      metric=MetricValue(value=None,unit="departure_equivalents_per_hour",availability=availability,data_quality=quality,score_eligibility=ScoreEligibility.INELIGIBLE,
        calibration_state=CalibrationState.UNCALIBRATED,is_estimate=False,is_proxy=False,source_refs=source_refs,method_version=None,
        reason_codes=("gtfs_out_of_validity",) if validity==GTFSFeedValidityState.OUT_OF_VALIDITY else ("gtfs_validity_unknown",))
      sid=hash_canonical({"bundle":feed.bundle.fingerprint,"reachability":str(reachability.identity),"profile_policy":str(profile_policy.identity),"availability":availability.value})
      return TransitSnapshot(snapshot_id=f"transit.{sid.algorithm.value}_{sid.digest}",stops=stops,service_window=window,observations=(),service_departure_equivalents_per_hour=metric,
        benchmark_ref=None,source_bundle_fingerprint=feed.bundle.fingerprint,source_refs=source_refs,availability=availability,data_quality=quality,generated_at=generated_at)
    profile=build_weekly_service_profile(feed=feed,reachability=reachability,profile_policy=profile_policy)
    obs=tuple(TransitObservation(i,profile.exact_departures[i],profile.frequency_equivalents[i],profile.total_equivalents[i]) for i in range(168))
    mean=sum(profile.total_equivalents)/168
    metric=MetricValue(value=mean,unit="departure_equivalents_per_hour",availability=AvailabilityState.AVAILABLE,data_quality=DataQualityState.FULL,
      score_eligibility=ScoreEligibility.DIAGNOSTIC_ONLY,calibration_state=CalibrationState.UNCALIBRATED,is_estimate=False,is_proxy=False,source_refs=source_refs,
      method_version=f"transit_derivation.{profile.derivation_identity.algorithm.value}_{profile.derivation_identity.digest}")
    sid=hash_canonical({"derivation_identity":str(profile.derivation_identity),"source_refs":source_refs})
    return TransitSnapshot(snapshot_id=f"transit.{sid.algorithm.value}_{sid.digest}",stops=stops,service_window=window,observations=obs,service_departure_equivalents_per_hour=metric,
      benchmark_ref=None,source_bundle_fingerprint=feed.bundle.fingerprint,source_refs=source_refs,availability=AvailabilityState.AVAILABLE,data_quality=DataQualityState.FULL,generated_at=generated_at)
