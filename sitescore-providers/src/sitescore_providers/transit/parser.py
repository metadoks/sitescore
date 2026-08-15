"""Strict stdlib GTFS Static ZIP parser."""
from __future__ import annotations
import csv, io, zipfile
from datetime import datetime, date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from collections import defaultdict

from sitescore_data import DataQualityState
from ..artifacts import ArtifactStore, RawAcquisitionArtifact
from ..errors import ProviderInvariantError, ProviderMalformedResponseError
from ..hashing import sha256_bytes, hash_canonical, canonical_json_bytes
from ..lineage import build_source_metadata
from ..parsing import build_parsed_artifact
from ..policy import ProviderPolicyDecision
from .models import *
from .client import build_gtfs_acquisition_fingerprint

_REQUIRED_FILES={"agency.txt","stops.txt","routes.txt","trips.txt","stop_times.txt"}

def _date(v:str,name:str)->date:
    try: return datetime.strptime(v,"%Y%m%d").date()
    except Exception as e: raise ProviderMalformedResponseError(f"invalid {name}") from e

def parse_gtfs_time(v:str)->int:
    parts=v.split(":")
    if len(parts)!=3: raise ProviderMalformedResponseError("invalid GTFS time")
    try: h,m,s=map(int,parts)
    except ValueError as e: raise ProviderMalformedResponseError("invalid GTFS time") from e
    if h<0 or m not in range(60) or s not in range(60): raise ProviderMalformedResponseError("invalid GTFS time")
    return h*3600+m*60+s

def _read_csv(z:zipfile.ZipFile,name:str)->list[dict[str,str]]:
    try: data=z.read(name)
    except KeyError: return []
    try: text=data.decode("utf-8-sig")
    except UnicodeDecodeError as e: raise ProviderMalformedResponseError(f"{name} must be UTF-8") from e
    reader=csv.DictReader(io.StringIO(text,newline=""))
    if reader.fieldnames is None or len(set(reader.fieldnames))!=len(reader.fieldnames): raise ProviderMalformedResponseError(f"malformed header in {name}")
    return [{k:(v or "").strip() for k,v in row.items()} for row in reader]

def _require_cols(rows,name,cols):
    if not rows: return
    missing=set(cols)-set(rows[0])
    if missing: raise ProviderMalformedResponseError(f"{name} missing required columns: {sorted(missing)}")

def parse_gtfs_zip(*, raw_artifact:RawAcquisitionArtifact, bundle:TransitSourceBundle, artifact_store:ArtifactStore,
                   policy:ProviderPolicyDecision, source_reference:str|None=None)->ParsedGTFSFeed:
    if raw_artifact.provider_identity != bundle.feed_manifest.provider_identity: raise ProviderInvariantError("GTFS raw provider identity/manifest mismatch")
    if raw_artifact.media_type != "application/zip": raise ProviderInvariantError("GTFS raw artifact must use application/zip media type")
    if raw_artifact.content_hash != bundle.feed_manifest.feed_content_hash: raise ProviderInvariantError("GTFS ZIP hash/manifest mismatch")
    if raw_artifact.request_fingerprint != build_gtfs_acquisition_fingerprint(manifest=bundle.feed_manifest,persistence=raw_artifact.persistence):
        raise ProviderInvariantError("GTFS raw request fingerprint/manifest mismatch")
    payload=artifact_store.get(raw_artifact.artifact_ref)
    if sha256_bytes(payload)!=raw_artifact.content_hash: raise ProviderInvariantError("stored GTFS ZIP bytes/hash mismatch")
    try: z=zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as e: raise ProviderMalformedResponseError("invalid GTFS ZIP") from e
    names=set(z.namelist())
    if any("/" in n.strip("/") for n in names): raise ProviderMalformedResponseError("GTFS files must be at ZIP root")
    if not _REQUIRED_FILES<=names: raise ProviderMalformedResponseError(f"missing required GTFS files: {sorted(_REQUIRED_FILES-names)}")
    if "calendar.txt" not in names and "calendar_dates.txt" not in names: raise ProviderMalformedResponseError("calendar.txt or calendar_dates.txt required")
    rows={n:_read_csv(z,n) for n in names if n.endswith('.txt')}
    for n,cols in {
      "agency.txt":{"agency_name","agency_url","agency_timezone"},"stops.txt":{"stop_id"},"routes.txt":{"route_id","route_type"},"trips.txt":{"route_id","service_id","trip_id"},
      "stop_times.txt":{"trip_id","stop_id","stop_sequence"},"calendar.txt":{"service_id","monday","tuesday","wednesday","thursday","friday","saturday","sunday","start_date","end_date"},
      "calendar_dates.txt":{"service_id","date","exception_type"},"frequencies.txt":{"trip_id","start_time","end_time","headway_secs"},
      "feed_info.txt":{"feed_publisher_name","feed_publisher_url","feed_lang"},
    }.items():
      if n in rows:_require_cols(rows[n],n,cols)
    tzs={r["agency_timezone"] for r in rows["agency.txt"] if r.get("agency_timezone")}
    if len(tzs)!=1: raise ProviderMalformedResponseError("all agencies must provide one shared agency_timezone")
    timezone=next(iter(tzs))
    try: ZoneInfo(timezone)
    except ZoneInfoNotFoundError as e: raise ProviderMalformedResponseError("invalid agency_timezone") from e
    # IDs
    stop_ids=[r["stop_id"] for r in rows["stops.txt"]]; route_ids=[r["route_id"] for r in rows["routes.txt"]]; trip_ids=[r["trip_id"] for r in rows["trips.txt"]]
    for label,ids in (("stop_id",stop_ids),("route_id",route_ids),("trip_id",trip_ids)):
      if any(not x for x in ids) or len(ids)!=len(set(ids)): raise ProviderMalformedResponseError(f"duplicate/empty {label}")
    stop_map={r["stop_id"]:r for r in rows["stops.txt"]}
    stops=[]
    for r in rows["stops.txt"]:
      try: lt=int(r.get("location_type") or 0)
      except ValueError as e: raise ProviderMalformedResponseError("invalid location_type") from e
      if lt not in {0,1,2,3,4}: raise ProviderMalformedResponseError("unsupported location_type")
      parent=r.get("parent_station") or None
      if lt==1 and parent is not None: raise ProviderMalformedResponseError("station cannot have parent_station")
      if lt in {2,3,4} and parent is None: raise ProviderMalformedResponseError("location_type requires parent_station")
      if parent is not None and parent not in stop_map: raise ProviderMalformedResponseError("parent_station reference missing")
      if parent is not None:
        plt=int(stop_map[parent].get("location_type") or 0)
        if lt in {0,2,3} and plt!=1: raise ProviderMalformedResponseError("parent_station must reference station")
        if lt==4 and plt!=0: raise ProviderMalformedResponseError("boarding area parent must be platform")
      lat=float(r["stop_lat"]) if r.get("stop_lat") else None; lon=float(r["stop_lon"]) if r.get("stop_lon") else None
      if lat is not None and not -90<=lat<=90: raise ProviderMalformedResponseError("invalid stop_lat")
      if lon is not None and not -180<=lon<=180: raise ProviderMalformedResponseError("invalid stop_lon")
      if lt in {0,1,2} and (lat is None or lon is None): raise ProviderMalformedResponseError("stop/station/entrance requires coordinates")
      if lt in {0,1,2} and not r.get("stop_name"): raise ProviderMalformedResponseError("stop/station/entrance requires stop_name")
      stops.append(GTFSStop(r["stop_id"],lt,parent,lat,lon))
    routes=tuple(GTFSRoute(x) for x in sorted(route_ids)); route_set=set(route_ids)
    trips=[]; service_ids=set()
    for r in rows["trips.txt"]:
      if r["route_id"] not in route_set: raise ProviderMalformedResponseError("trip references missing route")
      trips.append(GTFSTrip(r["trip_id"],r["route_id"],r["service_id"])); service_ids.add(r["service_id"])
    trip_set=set(trip_ids); stop_set=set(stop_ids)
    st=[]; seqs=defaultdict(set)
    for r in rows["stop_times.txt"]:
      if r["trip_id"] not in trip_set or r["stop_id"] not in stop_set: raise ProviderMalformedResponseError("stop_time missing trip/stop reference")
      if int(stop_map[r["stop_id"]].get("location_type") or 0)!=0: raise ProviderMalformedResponseError("stop_times stop_id must reference platform/stop")
      try: seq=int(r["stop_sequence"])
      except ValueError as e: raise ProviderMalformedResponseError("invalid stop_sequence") from e
      if seq<0 or seq in seqs[r["trip_id"]]: raise ProviderMalformedResponseError("duplicate/invalid stop_sequence")
      seqs[r["trip_id"]].add(seq)
      dep=parse_gtfs_time(r["departure_time"]) if r.get("departure_time") else None
      try: pickup=int(r.get("pickup_type") or 0)
      except ValueError as e: raise ProviderMalformedResponseError("invalid pickup_type") from e
      if pickup not in {0,1,2,3}: raise ProviderMalformedResponseError("invalid pickup_type")
      st.append(GTFSStopTime(r["trip_id"],r["stop_id"],seq,dep,pickup))
    calendars=[]; cal_ids=set()
    for r in rows.get("calendar.txt",[]):
      sid=r["service_id"]
      if sid in cal_ids: raise ProviderMalformedResponseError("duplicate calendar service_id")
      cal_ids.add(sid); start=_date(r["start_date"],"calendar.start_date"); end=_date(r["end_date"],"calendar.end_date")
      if end<start: raise ProviderMalformedResponseError("calendar end before start")
      try:
        flags=tuple(int(r[d]) for d in ("monday","tuesday","wednesday","thursday","friday","saturday","sunday"))
      except Exception as e: raise ProviderMalformedResponseError("invalid calendar weekday flags") from e
      if any(x not in {0,1} for x in flags): raise ProviderMalformedResponseError("calendar weekday flags must be 0 or 1")
      weekdays=tuple(bool(x) for x in flags)
      calendars.append(GTFSCalendar(sid,weekdays,start,end))
    cdates=[]; seen_cd=set(); date_only_addition_ids=set()
    for r in rows.get("calendar_dates.txt",[]):
      key=(r["service_id"],r["date"])
      if key in seen_cd: raise ProviderMalformedResponseError("duplicate calendar_dates service/date")
      seen_cd.add(key)
      try: ex=int(r["exception_type"])
      except ValueError as e: raise ProviderMalformedResponseError("invalid exception_type") from e
      if ex not in {1,2}: raise ProviderMalformedResponseError("invalid exception_type")
      sid=r["service_id"]
      cdates.append(GTFSCalendarDate(sid,_date(r["date"],"calendar_dates.date"),ex))
      if ex==1: date_only_addition_ids.add(sid)
    # A service_id absent from calendar.txt is established only by at least one explicit
    # calendar_dates addition. Removal-only exception rows cannot prove that service exists.
    resolvable=cal_ids|date_only_addition_ids
    if not service_ids<=resolvable: raise ProviderMalformedResponseError("trip service_id is not resolvable by base calendar or calendar_dates addition")
    freqs=[]; by_trip=defaultdict(list)
    for r in rows.get("frequencies.txt",[]):
      if r["trip_id"] not in trip_set: raise ProviderMalformedResponseError("frequency references missing trip")
      start=parse_gtfs_time(r["start_time"]); end=parse_gtfs_time(r["end_time"])
      try: head=int(r["headway_secs"]); exact=int(r.get("exact_times") or 0)
      except ValueError as e: raise ProviderMalformedResponseError("invalid frequency") from e
      if head<=0 or end<=start or exact not in {0,1}: raise ProviderMalformedResponseError("invalid frequency interval")
      for prev in by_trip[r["trip_id"]]:
        if max(start,prev.start_seconds)<min(end,prev.end_seconds): raise ProviderMalformedResponseError("overlapping frequency windows")
      f=GTFSFrequency(r["trip_id"],start,end,head,exact); by_trip[r["trip_id"]].append(f); freqs.append(f)
    feed_info=None
    if rows.get("feed_info.txt"):
      if len(rows["feed_info.txt"])!=1: raise ProviderMalformedResponseError("V1 requires one feed_info row")
      r=rows["feed_info.txt"][0]; fs=_date(r["feed_start_date"],"feed_start_date") if r.get("feed_start_date") else None; fe=_date(r["feed_end_date"],"feed_end_date") if r.get("feed_end_date") else None
      if fs and fe and fe<fs: raise ProviderMalformedResponseError("feed_end_date before feed_start_date")
      feed_info=GTFSFeedInfo(fs,fe,r.get("feed_version") or None)
    # Component identities from exact bytes.
    actual_components=tuple(sorted((n,sha256_bytes(z.read(n))) for n in names if n.endswith('.txt')))
    if bundle.component_file_hashes and bundle.component_file_hashes != actual_components: raise ProviderInvariantError("GTFS component file hash manifest mismatch")
    primitive={"files":{n:rows[n] for n in sorted(rows)}}
    parsed_bytes=canonical_json_bytes(primitive); pref=artifact_store.put(content_hash=hash_canonical(primitive),content=parsed_bytes)
    parsed=build_parsed_artifact(raw_artifact=raw_artifact,parser_id=GTFS_PARSER_ID,parser_version=bundle.feed_manifest.parser_version,parsed_value=primitive,parsed_artifact_ref=pref)
    sm=build_source_metadata(raw_artifact=raw_artifact,data_quality=DataQualityState.FULL,policy=policy,source_reference=source_reference)
    # Derived validity from feed_info if both provided, else service calendars/exceptions.
    dates=[]
    for c in calendars: dates.extend([c.start_date,c.end_date])
    dates.extend(cd.date for cd in cdates)
    derived_start=min(dates) if dates else None; derived_end=max(dates) if dates else None
    if feed_info and feed_info.feed_start_date and feed_info.feed_end_date:
      vs,ve=feed_info.feed_start_date,feed_info.feed_end_date; state=GTFSFeedValidityState.VALID
    elif (feed_info and (feed_info.feed_start_date or feed_info.feed_end_date)) or (derived_start and derived_end):
      vs=(feed_info.feed_start_date if feed_info and feed_info.feed_start_date else derived_start)
      ve=(feed_info.feed_end_date if feed_info and feed_info.feed_end_date else derived_end)
      state=GTFSFeedValidityState.DERIVED_VALIDITY if vs and ve else GTFSFeedValidityState.UNKNOWN
    else: vs=ve=None; state=GTFSFeedValidityState.UNKNOWN
    return ParsedGTFSFeed(bundle,raw_artifact,parsed,sm,timezone,tuple(sorted(stops,key=lambda x:x.stop_id)),routes,tuple(sorted(trips,key=lambda x:x.trip_id)),tuple(sorted(st,key=lambda x:(x.trip_id,x.stop_sequence))),tuple(sorted(calendars,key=lambda x:x.service_id)),tuple(sorted(cdates,key=lambda x:(x.service_id,x.date))),tuple(sorted(freqs,key=lambda x:(x.trip_id,x.start_seconds))),feed_info,vs,ve,state)
