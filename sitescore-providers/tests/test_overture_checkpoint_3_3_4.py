from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import pytest

from sitescore_data import DataQualityState, PersistenceClass, AvailabilityState
from sitescore_data.schemas.common import SourceMetadata
from sitescore_providers.artifacts import ArtifactRef
from sitescore_providers.hashing import CANONICALIZATION_VERSION, hash_canonical, sha256_bytes
from sitescore_providers.policy import (
    CommercialUseState, PersistenceDecision, ProviderPolicyDecision, RedistributionState,
)
from sitescore_providers.overture.models import (
    CommercialSemanticClass, CompetitionCatchmentPolicy, CompetitionCatchmentScale,
    CompetitionEligibilityState, CoverageState, EntityDedupPolicy,
    OvertureCompetitionTaxonomyMapping, OvertureOperatingStatus,
    OverturePlacesReleaseManifest, OvertureSourceAttribution, OvertureTaxonomyRule,
    PlaceLifecyclePolicy, TaxonomyMatchField, TaxonomyResolutionPolicy,
)
from sitescore_providers.overture.reader import (
    OverturePartitionDescriptor, build_partition_raw_artifact, build_partition_request_fingerprint,
)
from sitescore_providers.overture.parser import parse_overture_partition
from sitescore_providers.overture.builders import (
    build_competition_snapshot, build_measurement_definition_id, classify_place,
    classify_taxonomy, deduplicate_places,
)

NOW=datetime(2026,8,12,12,0,tzinfo=timezone.utc)


def manifest(**kw):
    args=dict(manifest_version="v1",data_release="2026-06-17.0",schema_version="v1.17.0",
              taxonomy_id="opc",taxonomy_version="2026.07",acquisition_id="overture_release_read",
              acquisition_version="v1",parser_version="v1")
    args.update(kw); return OverturePlacesReleaseManifest(**args)

def persistence(): return PersistenceDecision("overture_places_policy","v1",PersistenceClass.PERSIST)
def provider_policy():
    return ProviderPolicyDecision("overture_places_policy","v1",persistence(),True,RedistributionState.ALLOWED,CommercialUseState.ALLOWED,"multi_license","official_overture_attribution")

def descriptor(pid="part_a", content=b"partition-a"):
    return OverturePartitionDescriptor(pid,ArtifactRef(f"artifact://overture/{pid}"),sha256_bytes(content))

def row(pid="p1", category="cafe", status="open", confidence=.1, lon=-73.9, lat=40.7):
    return {"id":pid,"theme":"places","type":"place","geometry":{"type":"Point","coordinates":[lon,lat]},
            "basic_category":category,"taxonomy":{"primary":category,"hierarchy":["food_and_drink",category],"alternates":[]},
            "operating_status":status,"confidence":confidence,
            "sources":[{"dataset":"meta","license":"CDLA-Permissive-2.0","record_id":pid}]}

def partition(m=None,pid="part_a",rows=None,content=None):
    m=m or manifest(); d=descriptor(pid, content or pid.encode()); raw=build_partition_raw_artifact(manifest=m,descriptor=d,retrieved_at=NOW,persistence=persistence())
    return parse_overture_partition(raw_artifact=raw,records=tuple(rows or [row()]),manifest=m,policy=provider_policy(),
                                    parsed_artifact_ref=ArtifactRef(f"artifact://parsed/{pid}"),source_reference=f"s3://release/{m.data_release}/{pid}.parquet",partition_id=pid)

def resolution(version="v1"):
    return TaxonomyResolutionPolicy("hierarchy_first_v1", version)

def mapping(m=None, rules=None, version="v1", resolution_policy=None):
    m=m or manifest()
    if rules is None:
        rules=(OvertureTaxonomyRule("food_cafe",TaxonomyMatchField.PRIMARY,"cafe",CommercialSemanticClass.FOOD_DRINK,CompetitionEligibilityState.INCLUDED),)
    return OvertureCompetitionTaxonomyMapping("sector_competition",version,m.identity,m.taxonomy_id,m.taxonomy_version,resolution_policy or resolution(),tuple(rules))

def lifecycle(version="v1"):
    return PlaceLifecyclePolicy("active_place_status",version,(OvertureOperatingStatus.OPEN,),(OvertureOperatingStatus.PERMANENTLY_CLOSED,))
def dedup(version="v1"): return EntityDedupPolicy("exact_place_id",version)
def catches(members=("p1",), area1=2.0, area2=4.0, boundary="covers", version="v1"):
    return CompetitionCatchmentPolicy("trade_area",version,boundary,"v1","equal_area","v1",(
        CompetitionCatchmentScale("near","walking_network","precomputed_network_membership",5.0,"minutes",area1,tuple(members),"artifact://catchment/near"),
        CompetitionCatchmentScale("far","walking_network","precomputed_network_membership",10.0,"minutes",area2,tuple(members),"artifact://catchment/far"),
    ))


def test_release_manifest_deterministic_and_mutable_rejected():
    assert manifest().identity == manifest().identity
    with pytest.raises(ValueError): manifest(data_release="latest")
    with pytest.raises(ValueError): manifest(schema_version="current")

def test_release_and_schema_change_identity():
    assert manifest().identity != manifest(data_release="2026-05-20.0").identity
    assert manifest().identity != manifest(schema_version="v1.18.0").identity

def test_partition_request_identity_binds_release_file_content_not_path():
    m=manifest(); d=descriptor()
    fp=build_partition_request_fingerprint(manifest=m,descriptor=d)
    d2=replace(d,artifact_ref=ArtifactRef("artifact://different/store"))
    assert fp == build_partition_request_fingerprint(manifest=m,descriptor=d2)
    assert fp != build_partition_request_fingerprint(manifest=m,descriptor=replace(d,content_hash=sha256_bytes(b"other")))

def test_taxonomy_mapping_deterministic_and_change_changes_identity():
    m=manifest(); r1=OvertureTaxonomyRule("food_cafe",TaxonomyMatchField.PRIMARY,"cafe",CommercialSemanticClass.FOOD_DRINK,CompetitionEligibilityState.INCLUDED)
    r2=OvertureTaxonomyRule("retail_shop",TaxonomyMatchField.PRIMARY,"shop",CommercialSemanticClass.RETAIL,CompetitionEligibilityState.INCLUDED)
    a=mapping(m,(r1,r2)); b=mapping(m,(r2,r1))
    assert a.identity == b.identity
    assert a.identity != mapping(m,(replace(r1,eligibility=CompetitionEligibilityState.EXCLUDED),r2)).identity

def test_unknown_taxonomy_not_silently_included_or_excluded():
    p=partition(rows=[row(category="mystery")]).places[0]
    ev=classify_taxonomy(place=p,mapping=mapping())
    assert ev.state is CompetitionEligibilityState.UNKNOWN and ev.qualifies is None

def test_conditional_rule_explicit_and_unresolved_is_not_boolean_default():
    m=manifest(); rule=OvertureTaxonomyRule("healthcare_cond",TaxonomyMatchField.HIERARCHY,"health_care",CommercialSemanticClass.HEALTHCARE,CompetitionEligibilityState.CONDITIONAL,"sector_relevance",None)
    p=partition(m,rows=[{**row(category="clinic"),"taxonomy":{"primary":"clinic","hierarchy":["health_care","clinic"],"alternates":[]}}]).places[0]
    ev=classify_taxonomy(place=p,mapping=mapping(m,(rule,)))
    assert ev.state is CompetitionEligibilityState.CONDITIONAL and ev.qualifies is None

def test_permanently_closed_excluded_unknown_not_active_confidence_no_threshold():
    m=manifest(); mp=mapping(m); lp=lifecycle()
    open_low=partition(m,rows=[row(confidence=0.01)]).places[0]
    assert classify_place(place=open_low,mapping=mp,lifecycle_policy=lp).qualifies is True
    closed=partition(m,pid="part_b",rows=[row(status="permanently_closed",confidence=0.0)]).places[0]
    assert classify_place(place=closed,mapping=mp,lifecycle_policy=lp).qualifies is False
    unknown=partition(m,pid="part_c",rows=[row(status=None,confidence=None)]).places[0]
    assert classify_place(place=unknown,mapping=mp,lifecycle_policy=lp).qualifies is None

def test_parser_preserves_taxonomy_status_confidence_source_license():
    p=partition().places[0]
    assert p.taxonomy_primary=="cafe" and p.taxonomy_hierarchy==("food_and_drink","cafe")
    assert p.operating_status is OvertureOperatingStatus.OPEN and p.confidence==.1
    assert p.source_attributions==(OvertureSourceAttribution("meta","CDLA-Permissive-2.0","p1"),)

def test_exact_id_dedup_across_partitions_does_not_inflate_count():
    m=manifest(); a=partition(m,"part_a",[row("p1")]); b=partition(m,"part_b",[row("p1")])
    assert len(deduplicate_places(partitions=(b,a),manifest=m,policy=dedup()))==1
    snap,_=build_competition_snapshot(manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=catches(),lifecycle_policy=lifecycle(),partitions=(a,b),coverage_state=CoverageState.SUFFICIENT,generated_at=NOW)
    assert [o.competitor_count for o in snap.curve.observations]==[1,1]

def test_conflicting_duplicate_id_rejected_without_distance_heuristic():
    m=manifest(); a=partition(m,"part_a",[row("p1")]); b=partition(m,"part_b",[row("p1",lon=-74.5)])
    with pytest.raises(ValueError): deduplicate_places(partitions=(a,b),manifest=m,policy=dedup())

def test_multiscale_order_density_true_zero_and_source_lineage():
    m=manifest(); p=partition(m,rows=[row(category="church")])
    ex=OvertureTaxonomyRule("religious_church",TaxonomyMatchField.PRIMARY,"church",CommercialSemanticClass.RELIGIOUS,CompetitionEligibilityState.EXCLUDED)
    snap,evidence=build_competition_snapshot(manifest=m,mapping=mapping(m,(ex,)),dedup_policy=dedup(),catchment_policy=catches(),lifecycle_policy=lifecycle(),partitions=(p,),coverage_state=CoverageState.SUFFICIENT,generated_at=NOW)
    assert snap.availability is AvailabilityState.AVAILABLE
    assert tuple(o.scale_id for o in snap.curve.observations)==("near","far")
    assert tuple(o.competitor_count for o in snap.curve.observations)==(0,0)
    assert tuple(o.competitor_density_per_km2 for o in snap.curve.observations)==(0.0,0.0)
    assert snap.source_refs==(p.source_metadata.source_id,) and evidence.source_refs==snap.source_refs

def test_unknown_coverage_is_not_zero_curve():
    m=manifest(); p=partition(m)
    snap,_=build_competition_snapshot(manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=catches(),lifecycle_policy=lifecycle(),partitions=(p,),coverage_state=CoverageState.UNKNOWN,generated_at=NOW)
    assert snap.availability is AvailabilityState.UNKNOWN and snap.curve is None

def test_unknown_place_semantics_is_not_silent_exclusion():
    m=manifest(); p=partition(m,rows=[row(category="mystery")])
    snap,_=build_competition_snapshot(manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=catches(),lifecycle_policy=lifecycle(),partitions=(p,),coverage_state=CoverageState.SUFFICIENT,generated_at=NOW)
    assert snap.availability is AvailabilityState.UNKNOWN and snap.curve is None

def mid(m=None,mp=None,dp=None,cp=None,lp=None,count="qualifying_deduplicated_entity_count",density="count_per_square_kilometre"):
    m=m or manifest(); mp=mp or mapping(m); dp=dp or dedup(); cp=cp or catches(); lp=lp or lifecycle()
    return build_measurement_definition_id(manifest=m,mapping=mp,dedup_policy=dp,catchment_policy=cp,lifecycle_policy=lp,count_method=count,density_method=density)

def test_measurement_definition_changes_on_semantic_inputs():
    base=mid(); m2=manifest(data_release="2026-05-20.0"); mp2=mapping(m2)
    assert base != mid(m2,mp2)
    m3=manifest(schema_version="v1.18.0"); assert base != mid(m3,mapping(m3))
    assert base != mid(mp=mapping(rules=(OvertureTaxonomyRule("food_cafe",TaxonomyMatchField.PRIMARY,"cafe",CommercialSemanticClass.FOOD_DRINK,CompetitionEligibilityState.EXCLUDED),)))
    assert base != mid(dp=dedup("v2"))
    assert base != mid(cp=catches(boundary="contains"))
    assert base != mid(lp=lifecycle("v2"))
    assert base != mid(count="entity_count_v2")
    assert base != mid(density="density_v2")

def test_measurement_definition_ignores_site_specific_membership_area_artifact_and_retrieval_order():
    base=mid(cp=catches(("p1",),2,4))
    changed=catches(("p2","p3"),99,123)
    changed=replace(changed, scales=tuple(replace(s,catchment_artifact_ref=f"artifact://other/{s.scale_id}") for s in changed.scales))
    assert base==mid(cp=changed)

def test_multiple_partition_source_lineage_deterministic_processing_order():
    m=manifest(); a=partition(m,"part_a",[row("p1")]); b=partition(m,"part_b",[row("p2")])
    cp=catches(("p1","p2"))
    s1,_=build_competition_snapshot(manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=cp,lifecycle_policy=lifecycle(),partitions=(a,b),coverage_state=CoverageState.SUFFICIENT,generated_at=NOW)
    s2,_=build_competition_snapshot(manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=cp,lifecycle_policy=lifecycle(),partitions=(b,a),coverage_state=CoverageState.SUFFICIENT,generated_at=NOW)
    assert s1==s2 and len(s1.source_refs)==2

def test_same_bytes_wrong_source_metadata_semantics_rejected():
    p=partition(); sm=p.source_metadata
    wrong=SourceMetadata(source_id=sm.source_id,provider="other_provider",dataset=sm.dataset,dataset_release=sm.dataset_release,vintage=sm.vintage,schema_version=sm.schema_version,retrieved_at=sm.retrieved_at,content_hash=sm.content_hash,persistence_class=sm.persistence_class,data_quality=sm.data_quality,license_class=sm.license_class,attribution_required=sm.attribution_required,source_reference=sm.source_reference)
    with pytest.raises(ValueError): replace(p,source_metadata=wrong)

def test_no_fixed_universal_radius_or_confidence_threshold_in_production():
    root=Path(__file__).resolve().parents[1]/"src"/"sitescore_providers"/"overture"
    text="\n".join(p.read_text().lower() for p in root.glob("*.py"))
    assert "fixed_radius" not in text and "confidence <" not in text and "confidence >" not in text
    assert "ecdf" not in text and "percentile" not in text and "normalization" not in text

def test_canonical_competition_requires_persistable_release_artifacts():
    m=manifest(); p=partition(m)
    transient=PersistenceDecision("overture_places_policy","v1",PersistenceClass.TRANSIENT,max_retention_seconds=3600)
    raw=replace(p.raw_artifact,persistence=transient)
    sm=replace(p.source_metadata,persistence_class=PersistenceClass.TRANSIENT)
    pp=replace(p,raw_artifact=raw,source_metadata=sm)
    with pytest.raises(ValueError):
        deduplicate_places(partitions=(pp,),manifest=m,policy=dedup())

def test_partition_parser_rejects_wrong_partition_request_fingerprint():
    m=manifest(); d=descriptor("part_a"); raw=build_partition_raw_artifact(manifest=m,descriptor=d,retrieved_at=NOW,persistence=persistence())
    wrong=replace(raw, request_fingerprint=build_partition_request_fingerprint(manifest=m,descriptor=descriptor("part_b")))
    with pytest.raises(Exception):
        parse_overture_partition(raw_artifact=wrong,records=(row(),),manifest=m,policy=provider_policy(),parsed_artifact_ref=ArtifactRef("artifact://parsed/a"),partition_id="part_a")

def test_unordered_taxonomy_alternates_and_sources_canonicalize_same_parsed_content():
    m=manifest(); base=row(); base["taxonomy"]={"primary":"cafe","hierarchy":["food_and_drink","cafe"],"alternates":["bakery","shop"]}
    base["sources"]=[{"dataset":"zeta","license":"CC0","record_id":"2"},{"dataset":"alpha","license":"Apache-2.0","record_id":"1"}]
    rev={**base,"taxonomy":{**base["taxonomy"],"alternates":list(reversed(base["taxonomy"]["alternates"]))},"sources":list(reversed(base["sources"]))}
    a=partition(m,"part_a",[base],b"same")
    # same content hash and same partition semantics required for parsed identity comparison
    d=descriptor("part_a",b"same"); raw=build_partition_raw_artifact(manifest=m,descriptor=d,retrieved_at=NOW,persistence=persistence())
    b=parse_overture_partition(raw_artifact=raw,records=(rev,),manifest=m,policy=provider_policy(),parsed_artifact_ref=ArtifactRef("artifact://parsed/other"),partition_id="part_a")
    assert a.parsed_artifact.parsed_content_hash==b.parsed_artifact.parsed_content_hash
    assert a.places[0].taxonomy_alternates==b.places[0].taxonomy_alternates==("bakery","shop")

def test_catchment_membership_cannot_reference_unloaded_place_when_coverage_sufficient():
    m=manifest(); p=partition(m)
    with pytest.raises(ValueError):
        build_competition_snapshot(manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=catches(("p1","missing_place")),lifecycle_policy=lifecycle(),partitions=(p,),coverage_state=CoverageState.SUFFICIENT,generated_at=NOW)


def test_taxonomy_resolution_hierarchy_wins_over_alternate_conflict():
    m=manifest()
    rules=(
        OvertureTaxonomyRule("hier_food",TaxonomyMatchField.HIERARCHY,"food_and_drink",CommercialSemanticClass.FOOD_DRINK,CompetitionEligibilityState.INCLUDED),
        OvertureTaxonomyRule("alt_shop_ex",TaxonomyMatchField.ALTERNATE,"shop",CommercialSemanticClass.RETAIL,CompetitionEligibilityState.EXCLUDED),
    )
    r=row(); r["taxonomy"]={"primary":"cafe","hierarchy":["food_and_drink","cafe"],"alternates":["shop"]}
    ev=classify_taxonomy(place=partition(m,rows=[r]).places[0],mapping=mapping(m,rules))
    assert ev.state is CompetitionEligibilityState.INCLUDED
    assert ev.matched_rule_ids == ("hier_food",)

def test_taxonomy_resolution_alternate_cannot_promote_hierarchy_exclusion():
    m=manifest()
    rules=(
        OvertureTaxonomyRule("hier_food_ex",TaxonomyMatchField.HIERARCHY,"food_and_drink",CommercialSemanticClass.FOOD_DRINK,CompetitionEligibilityState.EXCLUDED),
        OvertureTaxonomyRule("alt_shop_in",TaxonomyMatchField.ALTERNATE,"shop",CommercialSemanticClass.RETAIL,CompetitionEligibilityState.INCLUDED),
    )
    r=row(); r["taxonomy"]={"primary":"cafe","hierarchy":["food_and_drink","cafe"],"alternates":["shop"]}
    ev=classify_taxonomy(place=partition(m,rows=[r]).places[0],mapping=mapping(m,rules))
    assert ev.state is CompetitionEligibilityState.EXCLUDED

def test_taxonomy_resolution_basic_category_is_explicit_fallback():
    m=manifest()
    rule=OvertureTaxonomyRule("basic_cafe",TaxonomyMatchField.BASIC_CATEGORY,"cafe",CommercialSemanticClass.FOOD_DRINK,CompetitionEligibilityState.INCLUDED)
    ev=classify_taxonomy(place=partition(m).places[0],mapping=mapping(m,(rule,)))
    assert ev.state is CompetitionEligibilityState.INCLUDED

def test_taxonomy_resolution_alternate_only_is_unknown():
    m=manifest()
    rule=OvertureTaxonomyRule("alt_shop",TaxonomyMatchField.ALTERNATE,"shop",CommercialSemanticClass.RETAIL,CompetitionEligibilityState.INCLUDED)
    r=row(); r["taxonomy"]={"primary":"cafe","hierarchy":["food_and_drink","cafe"],"alternates":["shop"]}
    ev=classify_taxonomy(place=partition(m,rows=[r]).places[0],mapping=mapping(m,(rule,)))
    assert ev.state is CompetitionEligibilityState.UNKNOWN and ev.qualifies is None

def test_taxonomy_resolution_policy_change_changes_mapping_and_measurement_identity():
    m=manifest()
    a=mapping(m,resolution_policy=resolution("v1")); b=mapping(m,resolution_policy=resolution("v2"))
    assert a.identity != b.identity
    assert mid(m=m,mp=a) != mid(m=m,mp=b)

def test_duplicate_id_full_measurement_evidence_conflicts_rejected():
    m=manifest(); base=row("p1")
    mutations=[]
    h={**base,"taxonomy":{**base["taxonomy"],"hierarchy":["food_and_drink","restaurant","cafe"]}}; h["taxonomy"]["primary"]="cafe"; mutations.append(h)
    a={**base,"taxonomy":{**base["taxonomy"],"alternates":["shop"]}}; mutations.append(a)
    mutations.append({**base,"operating_status":"temporarily_closed"})
    mutations.append({**base,"confidence":0.9})
    mutations.append({**base,"geometry":{"type":"Point","coordinates":[-74.5,40.7]}})
    mutations.append({**base,"sources":[{"dataset":"other","license":"CC0-1.0","record_id":"p1"}]})
    for i,changed in enumerate(mutations):
        pa=partition(m,"base"+str(i),[base]); pb=partition(m,"changed"+str(i),[changed])
        with pytest.raises(ValueError): deduplicate_places(partitions=(pa,pb),manifest=m,policy=dedup())

def test_identical_duplicate_id_collapses_to_one_entity():
    m=manifest(); a=partition(m,"x",[row("p1")]); b=partition(m,"y",[row("p1")])
    assert len(deduplicate_places(partitions=(a,b),manifest=m,policy=dedup())) == 1

def test_taxonomy_collection_raw_types_rejected_before_canonicalization():
    m=manifest()
    for bad in (
        {"primary":"cafe","hierarchy":"restaurant","alternates":[]},
        {"primary":"cafe","hierarchy":["food_and_drink","cafe"],"alternates":"grocery_store"},
    ):
        r=row(); r["taxonomy"]=bad
        with pytest.raises(Exception): partition(m,pid="bad_"+str(len(str(bad))),rows=[r])

def test_taxonomy_schema_primary_hierarchy_and_alternate_invariants():
    m=manifest()
    cases=(
        {"primary":"cafe","hierarchy":[],"alternates":[]},
        {"primary":"cafe","hierarchy":["food_and_drink","restaurant"],"alternates":[]},
        {"primary":"cafe","hierarchy":["food_and_drink","cafe"],"alternates":["cafe"]},
    )
    for i,tax in enumerate(cases):
        r=row(); r["taxonomy"]=tax
        with pytest.raises(Exception): partition(m,pid=f"schema_bad_{i}",rows=[r])

def test_lifecycle_and_dedup_identities_commit_grammar_and_canonicalization():
    from sitescore_providers.overture import models as om
    expected_lifecycle=hash_canonical({
        "grammar_version": om.OVERTURE_LIFECYCLE_POLICY_GRAMMAR,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "policy_id":"active_place_status","policy_version":"v1",
        "active_statuses":("open",),"excluded_statuses":("permanently_closed",),
    })
    expected_dedup=hash_canonical({
        "grammar_version": om.OVERTURE_DEDUP_POLICY_GRAMMAR,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "policy_id":"exact_place_id","policy_version":"v1","identity_field":"overture_place_id_exact",
    })
    assert lifecycle().identity == expected_lifecycle
    assert dedup().identity == expected_dedup

def test_snapshot_validates_partitions_before_all_coverage_branches():
    m=manifest(); p=partition(m)
    for coverage in (CoverageState.SUFFICIENT, CoverageState.UNKNOWN, CoverageState.INSUFFICIENT):
        snap,_=build_competition_snapshot(
            manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=catches(),
            lifecycle_policy=lifecycle(),partitions=(p,),coverage_state=coverage,generated_at=NOW,
        )
        if coverage is CoverageState.SUFFICIENT:
            assert snap.availability is AvailabilityState.AVAILABLE
        else:
            assert snap.availability is AvailabilityState.UNKNOWN and snap.curve is None


def test_snapshot_rejects_wrong_manifest_partition_for_unknown_and_insufficient_coverage():
    active=manifest(); foreign=manifest(data_release="2026-05-20.0")
    p=partition(foreign)
    for coverage in (CoverageState.UNKNOWN, CoverageState.INSUFFICIENT):
        with pytest.raises(ValueError, match="partition provider identity"):
            build_competition_snapshot(
                manifest=active,mapping=mapping(active),dedup_policy=dedup(),catchment_policy=catches(),
                lifecycle_policy=lifecycle(),partitions=(p,),coverage_state=coverage,generated_at=NOW,
            )


def test_snapshot_rejects_transient_partition_before_unknown_coverage_branch():
    m=manifest(); p=partition(m)
    transient=PersistenceDecision("overture_places_policy","v1",PersistenceClass.TRANSIENT,max_retention_seconds=3600)
    raw=replace(p.raw_artifact,persistence=transient)
    sm=replace(p.source_metadata,persistence_class=PersistenceClass.TRANSIENT)
    pp=replace(p,raw_artifact=raw,source_metadata=sm)
    with pytest.raises(ValueError, match="persistable pinned release artifacts"):
        build_competition_snapshot(
            manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=catches(),
            lifecycle_policy=lifecycle(),partitions=(pp,),coverage_state=CoverageState.UNKNOWN,generated_at=NOW,
        )


def test_empty_partitions_unknown_coverage_preserves_existing_behavior():
    m=manifest()
    snap,evidence=build_competition_snapshot(
        manifest=m,mapping=mapping(m),dedup_policy=dedup(),catchment_policy=catches(),
        lifecycle_policy=lifecycle(),partitions=(),coverage_state=CoverageState.UNKNOWN,generated_at=NOW,
    )
    assert snap.availability is AvailabilityState.UNKNOWN
    assert snap.curve is None
    assert snap.source_refs == ()
    assert evidence.source_refs == ()
