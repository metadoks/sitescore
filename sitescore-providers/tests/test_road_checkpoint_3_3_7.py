from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
import json
import pytest

from sitescore_data import PersistenceClass
from sitescore_data.schemas.geography import ResolvedLocation
from sitescore_data.schemas.road import RoadOriginQuality
from sitescore_providers.artifacts import ArtifactRef
from sitescore_providers.hashing import sha256_bytes
from sitescore_providers.policy import CommercialUseState, PersistenceDecision, ProviderPolicyDecision, RedistributionState
from sitescore_providers.results import AcquisitionState
from sitescore_providers.road.models import *
from sitescore_providers.road.client import *
from sitescore_providers.road.parser import parse_valhalla_isochrone_evidence, canonicalize_geometry
from sitescore_providers.road.builders import *

NOW=datetime(2026,8,13,tzinfo=timezone.utc)

class Store:
    def __init__(self): self.d={}
    def put(self,*,content_hash,content):
        r=ArtifactRef(f"artifact://sha256/{content_hash.digest}"); self.d[str(r)]=content; return r
    def get(self,r): return self.d[str(r)]
    def exists(self,r): return str(r) in self.d
class Transport:
    def __init__(self,body,status=200): self.res=ValhallaJSONResponse(status,json.dumps(body).encode()); self.requests=[]
    def send(self,r): self.requests.append(r); return self.res

def policy(pid="road_policy", persist=PersistenceClass.PERSIST):
    kw={} if persist is not PersistenceClass.TRANSIENT else {"max_retention_seconds":3600}
    pd=PersistenceDecision(pid,"v1",persist,**kw)
    return ProviderPolicyDecision(pid,"v1",pd,True,RedistributionState.ALLOWED,CommercialUseState.ALLOWED,"ODbL-1.0")
def loc(lat=40.74,lon=-73.99):
    return ResolvedLocation(lat,lon,"1 Test St","US",(),("source.geo",),"geo.v1",NOW)
def net(content=b"road-net",release="2026-08-10"):
    return RoadNetworkManifest("v1","openstreetmap","osm_vehicle_extract","ny_metro",sha256_bytes(content),release,"osm_pbf","pbf_v1","application/vnd.openstreetmap.data+pbf","build_v1","trusted_extract","v1")
def traffic(ver="v1"):
    return RoadTrafficPolicy("static_traffic",ver,"static_graph_no_datetime")
def engine(ver="3.8.3", opts=(), traffic_policy=None):
    return RoadRoutingEngineManifest("v1","valhalla",ver,"mjolnir_tiles","v1","auto","auto_v1",opts,traffic_policy or traffic(),"v1")
def compat(n=None,e=None,graph=b"graph",ref="artifact://graph/a"):
    return RoadGraphCompatibility("ny_graph","v1",n or net(),e or engine(),sha256_bytes(graph),ArtifactRef(ref))
def limit(mc=4,mt=60.0): return RoadIsochroneExecutionPolicy("iso_limits","v1",mc,mt)
def binding(c=None,l=None): return RoadRoutingExecutionBinding("ny_deploy","v1",c or compat(),l or limit())
def budget(costs=(300.,600.)):
    return RoadDriveBudgetPolicy("drive_budget","v1",tuple(RoadDriveBudgetScale(f"drive_{int(x)}s",x) for x in costs))
def geo(): return RoadGeometryPolicy("geojson","v1","epsg_4326","geojson",True,1.0,None,"v1")
def req(c=None,b=None,o=None,bd=None):
    c=c or compat(); bd=bd or binding(c)
    return RoadIsochroneRequest(RoadRoutingOrigin.from_resolved_location(o or loc()), b or budget(), c, bd, geo())
def poly(off=0):
    return {"type":"Polygon","coordinates":[[[-74+off,40.73],[-73.98+off,40.73],[-73.98+off,40.75],[-74+off,40.75],[-74+off,40.73]]]}
def payload(r, warnings=None, missing=None, duplicate=None, locs=True):
    fs=[]
    for i,s in enumerate(r.budget_policy.scales):
        if s.scale_id==missing: continue
        f={"type":"Feature","properties":{"metric":"time","contour":s.travel_cost_seconds/60},"geometry":poly(i*.001)}; fs.append(f)
        if s.scale_id==duplicate: fs.append(f)
    if locs:
        fs += [{"type":"Feature","properties":{},"geometry":{"type":"MultiPoint","coordinates":[[r.origin.longitude,r.origin.latitude]]}},
               {"type":"Feature","properties":{},"geometry":{"type":"MultiPoint","coordinates":[[r.origin.longitude+.0001,r.origin.latitude+.0001]]}}]
    d={"type":"FeatureCollection","features":fs}
    if warnings is not None:d["warnings"]=warnings
    return d
def acquire_parse(r=None,p=None):
    r=r or req(); st=Store(); tr=Transport(p or payload(r)); cl=RoadIsochroneClient(transport=tr,artifact_store=st,endpoint_url="https://x/isochrone",execution_binding=r.execution_binding)
    ac=cl.acquire(request=r,persistence_policy=policy("route_policy",PersistenceClass.TRANSIENT),retrieved_at=NOW); assert ac.state is AcquisitionState.SUCCESS
    parsed=cl.parse_success(acquisition=ac,request=r); ev=parse_valhalla_isochrone_evidence(response=parsed,request=r); return st,tr,cl,ev

def test_network_manifest_deterministic_and_mutable_rejected():
    assert net().identity==net().identity
    for x in ("latest","current","live"):
        with pytest.raises(ValueError): net(release=x)
def test_network_content_sensitive(): assert net(b"a").identity!=net(b"b").identity
def test_engine_profile_and_options_sensitive():
    assert engine()!=engine(opts=(("use_tolls",0.2),))
    assert engine().identity!=engine(opts=(("use_tolls",0.2),)).identity
def test_traffic_policy_sensitive(): assert engine(traffic_policy=traffic("v1")).identity!=engine(traffic_policy=traffic("v2")).identity
def test_graph_artifact_locator_excluded():
    a=compat(ref="artifact://graph/a"); b=compat(ref="artifact://graph/b")
    assert a.identity==b.identity
    assert binding(a).identity==binding(b).identity
    assert build_isochrone_request_fingerprint(req(c=a,bd=binding(a)))==build_isochrone_request_fingerprint(req(c=b,bd=binding(b)))
def test_graph_content_sensitive(): assert compat(graph=b"a").identity!=compat(graph=b"b").identity
def test_execution_limit_before_network():
    c=compat(); bd=binding(c,limit(1,5)); req(c=c,b=budget((300.,)),bd=bd)
    with pytest.raises(ValueError): req(c=c,b=budget((301.,)),bd=bd)
    with pytest.raises(ValueError): req(c=c,b=budget((300.,600.)),bd=bd)
def test_request_body_auto_and_no_datetime():
    body=json.loads(build_valhalla_isochrone_body(req()))
    assert body["costing"]=="auto" and "date_time" not in body
def test_request_fingerprint_origin_budget_profile_sensitive():
    x=req(); assert build_isochrone_request_fingerprint(x)!=build_isochrone_request_fingerprint(req(o=loc(40.75,-73.99)))
    assert build_isochrone_request_fingerprint(x)!=build_isochrone_request_fingerprint(req(b=budget((300.,900.))))
    c=compat(e=engine(opts=(("use_tolls",0.2),))); assert build_isochrone_request_fingerprint(x)!=build_isochrone_request_fingerprint(req(c=c,bd=binding(c)))
def test_execution_binding_mismatch_rejects_before_network():
    r=req(); other=compat(graph=b"other"); tr=Transport(payload(r)); cl=RoadIsochroneClient(transport=tr,artifact_store=Store(),endpoint_url="https://x/isochrone",execution_binding=binding(other))
    with pytest.raises(ValueError): cl.acquire(request=r,persistence_policy=policy("route_policy",PersistenceClass.TRANSIENT),retrieved_at=NOW)
    assert not tr.requests
def test_parse_resolved_snap_and_quality():
    *_,ev=acquire_parse(); assert ev.routed_origin.snap_state is OriginSnapState.RESOLVED; assert ev.routed_origin.road_origin_quality is RoadOriginQuality.ROAD_SEGMENT_FALLBACK
def test_unresolved_snap_not_zero():
    r=req(); *_,ev=acquire_parse(r,payload(r,locs=False)); assert ev.routed_origin.snap_state is OriginSnapState.UNKNOWN
    assert ev.routed_origin.road_origin_quality is RoadOriginQuality.UNRESOLVED
def test_warning_preserved():
    r=req(); *_,ev=acquire_parse(r,payload(r,warnings=[{"code":1,"text":"clamped"}])); assert len(ev.warnings)==1
def test_missing_duplicate_contour_reject():
    r=req()
    with pytest.raises(Exception): acquire_parse(r,payload(r,missing=r.budget_policy.scales[0].scale_id))
    with pytest.raises(Exception): acquire_parse(r,payload(r,duplicate=r.budget_policy.scales[0].scale_id))
def test_geometry_canonical_order():
    r=req(); g1=poly(); g2={"type":"Polygon","coordinates":[list(reversed(g1["coordinates"][0]))]}
    assert canonicalize_geometry(geometry=g1,request=r).identity==canonicalize_geometry(geometry=g2,request=r).identity
def test_network_raw_actual_hash_verified():
    st=Store(); ref=st.put(content_hash=sha256_bytes(b"wrong"),content=b"wrong")
    with pytest.raises(ValueError): build_network_source_evidence(manifest=net(b"expected"),artifact_ref=ref,artifact_store=st,retrieved_at=NOW,policy=policy("osm_policy"))
def test_frozen_snapshot_mapping_and_zero():
    r=req(); st,tr,cl,ev=acquire_parse(r)
    nbytes=b"road-net"; nref=st.put(content_hash=sha256_bytes(nbytes),content=nbytes)
    ns=build_network_source_evidence(manifest=r.graph_compatibility.network_manifest,artifact_ref=nref,artifact_store=st,retrieved_at=NOW,policy=policy("osm_policy"))
    rm=build_routing_source_metadata(evidence=ev,policy=policy("route_policy",PersistenceClass.TRANSIENT))
    ap=RoadAreaPolicy("area","v1","geodesic_area","v1")
    ms=tuple(RoadScaleMeasurementEvidence(c.scale_id,c.geometry.identity,0.0 if i==0 else 10.0,20.0,5,3.0,ap,"expansion_metrics","v1") for i,c in enumerate(ev.contours))
    out=build_road_access_snapshot(evidence=ev,measurements=ms,network_source=ns,routing_source_metadata=rm,generated_at=NOW)
    assert out.snapshot.observations[0].reachable_area_km2==0
    assert out.snapshot.road_origin_quality is RoadOriginQuality.ROAD_SEGMENT_FALLBACK
    assert out.snapshot.routing_profile_id=="auto"
    assert out.snapshot.routing_profile_version=="auto_v1"
def test_warning_prevents_available_snapshot():
    r=req(); st,_,_,ev=acquire_parse(r,payload(r,warnings=[{"text":"x"}]))
    nbytes=b"road-net"; nref=st.put(content_hash=sha256_bytes(nbytes),content=nbytes)
    ns=build_network_source_evidence(manifest=r.graph_compatibility.network_manifest,artifact_ref=nref,artifact_store=st,retrieved_at=NOW,policy=policy("osm_policy")); rm=build_routing_source_metadata(evidence=ev,policy=policy("route_policy",PersistenceClass.TRANSIENT)); ap=RoadAreaPolicy("area","v1","geodesic_area","v1")
    ms=tuple(RoadScaleMeasurementEvidence(c.scale_id,c.geometry.identity,1,1,1,1,ap,"m","v1") for c in ev.contours)
    with pytest.raises(ValueError): build_road_access_snapshot(evidence=ev,measurements=ms,network_source=ns,routing_source_metadata=rm,generated_at=NOW)
def test_area_method_changes_measurement_identity():
    g=sha256_bytes(b"g"); a=RoadScaleMeasurementEvidence("s",g,1,1,1,1,RoadAreaPolicy("a","v1","geodesic","v1"),"m","v1"); b=replace(a,area_policy=RoadAreaPolicy("a","v1","equal_area","v1")); assert a.identity!=b.identity
def test_no_parking_or_traffic_scoring_symbols():
    from pathlib import Path
    root=Path(__file__).parents[1]/"src/sitescore_providers/road"
    txt="\n".join(p.read_text() for p in root.glob("*.py"))
    assert "road_parking_access_score" not in txt and "benchmark_percentile=" in (Path(root/"builders.py").read_text())

def test_drive_budget_unit_explicit_seconds_only():
    assert RoadDriveBudgetScale("s", 60).travel_cost_unit == "seconds"
    with pytest.raises(ValueError): RoadDriveBudgetScale("s", 60, "minutes")

def test_execution_config_changes_request_identity():
    c=compat(); a=req(c=c,bd=binding(c,limit(4,60))); b=req(c=c,bd=binding(c,limit(3,60)))
    assert build_isochrone_request_fingerprint(a) != build_isochrone_request_fingerprint(b)

def test_execution_headers_secret_do_not_change_request_fingerprint():
    r=req(); fp=build_isochrone_request_fingerprint(r)
    c1=RoadIsochroneClient(transport=Transport(payload(r)),artifact_store=Store(),endpoint_url="https://a/isochrone",execution_binding=r.execution_binding,execution_headers=(("Authorization","Bearer secret-a"),))
    c2=RoadIsochroneClient(transport=Transport(payload(r)),artifact_store=Store(),endpoint_url="https://b/isochrone",execution_binding=r.execution_binding,execution_headers=(("Authorization","Bearer secret-b"),))
    assert build_isochrone_request_fingerprint(r) == fp

def test_same_bytes_wrong_network_source_metadata_semantics_rejected():
    from dataclasses import replace as dc_replace
    st=Store(); content=b"road-net"; ref=st.put(content_hash=sha256_bytes(content),content=content)
    source=build_network_source_evidence(manifest=net(content),artifact_ref=ref,artifact_store=st,retrieved_at=NOW,policy=policy("osm_policy"))
    with pytest.raises(ValueError): RoadNetworkSourceEvidence(source.manifest,source.raw_artifact,dc_replace(source.source_metadata,provider="wrong_provider"))

def _snapshot_fixture_outputs(measurements_order="canonical"):
    r=req(); st,_,_,ev=acquire_parse(r)
    nbytes=b"road-net"; nref=st.put(content_hash=sha256_bytes(nbytes),content=nbytes)
    ns=build_network_source_evidence(manifest=r.graph_compatibility.network_manifest,artifact_ref=nref,artifact_store=st,retrieved_at=NOW,policy=policy("osm_policy"))
    rm=build_routing_source_metadata(evidence=ev,policy=policy("route_policy",PersistenceClass.TRANSIENT))
    a0=RoadAreaPolicy("area_a","v1","geodesic_area","v1")
    a1=RoadAreaPolicy("area_b","v1","equal_area","v1")
    ms=(
        RoadScaleMeasurementEvidence(ev.contours[0].scale_id,ev.contours[0].geometry.identity,1,2,3,4,a0,"network_a","v1"),
        RoadScaleMeasurementEvidence(ev.contours[1].scale_id,ev.contours[1].geometry.identity,5,6,7,8,a1,"network_b","v2"),
    )
    if measurements_order == "reversed":
        ms=tuple(reversed(ms))
    out=build_road_access_snapshot(evidence=ev,measurements=ms,network_source=ns,routing_source_metadata=rm,generated_at=NOW)
    return r,ev,ns,rm,ms,out


def test_measurement_policy_identity_input_order_independent():
    _,_,_,_,_,a=_snapshot_fixture_outputs("canonical")
    _,_,_,_,_,b=_snapshot_fixture_outputs("reversed")
    assert a.derivation.measurement_policy_identity == b.derivation.measurement_policy_identity
    assert tuple(o.method_version for o in a.snapshot.observations) == tuple(o.method_version for o in b.snapshot.observations)
    assert a.snapshot.snapshot_id == b.snapshot.snapshot_id


def test_measurement_policy_identity_scale_assignment_sensitive():
    r,ev,ns,rm,ms,a=_snapshot_fixture_outputs("canonical")
    swapped=(
        replace(ms[0], area_policy=ms[1].area_policy, network_measurement_method_id=ms[1].network_measurement_method_id, network_measurement_method_version=ms[1].network_measurement_method_version),
        replace(ms[1], area_policy=ms[0].area_policy, network_measurement_method_id=ms[0].network_measurement_method_id, network_measurement_method_version=ms[0].network_measurement_method_version),
    )
    b=build_road_access_snapshot(evidence=ev,measurements=swapped,network_source=ns,routing_source_metadata=rm,generated_at=NOW)
    assert a.derivation.measurement_policy_identity != b.derivation.measurement_policy_identity


def test_measurement_policy_identity_area_policy_sensitive():
    r,ev,ns,rm,ms,a=_snapshot_fixture_outputs("canonical")
    changed=(replace(ms[0], area_policy=RoadAreaPolicy("area_a","v2","geodesic_area","v2")), ms[1])
    b=build_road_access_snapshot(evidence=ev,measurements=changed,network_source=ns,routing_source_metadata=rm,generated_at=NOW)
    assert a.derivation.measurement_policy_identity != b.derivation.measurement_policy_identity


def test_measurement_policy_identity_network_method_sensitive():
    r,ev,ns,rm,ms,a=_snapshot_fixture_outputs("canonical")
    changed=(replace(ms[0], network_measurement_method_version="v9"), ms[1])
    b=build_road_access_snapshot(evidence=ev,measurements=changed,network_source=ns,routing_source_metadata=rm,generated_at=NOW)
    assert a.derivation.measurement_policy_identity != b.derivation.measurement_policy_identity


def test_network_manifest_media_type_identity_and_raw_binding():
    a=net()
    b=replace(a,media_type="application/x-road-network-test")
    assert a.identity != b.identity
    st=Store(); content=b"road-net"; ref=st.put(content_hash=sha256_bytes(content),content=content)
    src=build_network_source_evidence(manifest=b,artifact_ref=ref,artifact_store=st,retrieved_at=NOW,policy=policy("alt_policy"))
    assert src.raw_artifact.media_type == b.media_type == "application/x-road-network-test"


def test_network_manifest_media_type_validation():
    with pytest.raises((TypeError,ValueError)):
        replace(net(),media_type="")
    with pytest.raises(ValueError):
        replace(net(),media_type=" application/test ")


def test_network_source_evidence_rejects_raw_media_type_mismatch():
    from dataclasses import replace as dc_replace
    st=Store(); content=b"road-net"; ref=st.put(content_hash=sha256_bytes(content),content=content)
    source=build_network_source_evidence(manifest=net(content),artifact_ref=ref,artifact_store=st,retrieved_at=NOW,policy=policy("osm_policy"))
    with pytest.raises(ValueError):
        RoadNetworkSourceEvidence(source.manifest, dc_replace(source.raw_artifact, media_type="application/x-wrong"), source.source_metadata)
