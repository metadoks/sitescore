# FAZ 3.3 — Provider Layer Authoritative Handoff

**Status:** FAZ 3.3 provider implementation checkpoints 3.3-1 through 3.3-8 are LOCKED.  
**Scope of this record:** final/frozen provider state only. Superseded intermediate designs are intentionally omitted.  
**Do not infer from this record that FAZ 3.4 has started.** Benchmark acquisition, normalization, pipeline assembly, category aggregation, and core integration remain future work.

---

## 0. Authoritative baselines

```text
sitescore-providers current locked baseline = 418/418 PASS
sitescore-data v0.1.0                  = 361/361 PASS
sitescore-core v0.1.0                  = 86/86 PASS

sitescore-providers runtime dependency:
    sitescore-data==0.1.0

sitescore-core imports from providers = 0
CONTRACT_CHANGE_REQUIRED              = 0
```

Frozen dependency identities:

```text
sitescore-data v0.1.0
ZIP SHA-256: 386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b
freeze commit: f03cbb71bd93c5a3afd78b43991e456595a7f75d
freeze tag: sitescore-data-v0.1.0

sitescore-core v0.1.0
ZIP SHA-256: aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192
freeze commit: 019b40beadb66c533f1de41e99efc7084663956f
freeze tag: v0.1.0
```

`sitescore-providers` currently declares package version `0.1.0`, but the **final provider repository freeze commit/tag has not yet been performed**. The current locked source is the Checkpoint 3.3-8 Hardened ZIP listed below.

---

# 1. FINAL FROZEN PROVIDER STATE

## 1.1 Checkpoint 3.3-1 — Provider Foundation

**Status:** LOCKED  
**Purpose:** provider-independent acquisition, identity, provenance, persistence, error/result, and deterministic hashing foundation.

### Production files

```text
src/sitescore_providers/
├── __init__.py
├── _validation.py
├── artifacts.py
├── baseline.py
├── errors.py
├── hashing.py
├── identity.py
├── lineage.py
├── parsing.py
├── policy.py
└── results.py
```

`http.py` was introduced at 3.3-2 as the generic stdlib HTTP boundary, not in the locked 3.3-1 production set.

### Main contracts

- `ArtifactRef`
- `ArtifactStore`
- `RawAcquisitionArtifact`
- `ParsedArtifact`
- `HashAlgorithm`, `ContentHash`
- canonical JSON/hash helpers
- `ProviderIdentity`
- `RequestFingerprint`, `build_request_fingerprint()`
- `PersistenceDecision`
- `ProviderPolicyDecision`, `ProviderPolicyRegistry`
- provider error taxonomy
- `AcquisitionResult`
- `build_parsed_artifact()`
- `build_source_metadata()`
- frozen `sitescore-data==0.1.0` runtime compatibility guard

### Frozen invariants

- Provider package may import `sitescore_data`; it must never import `sitescore-core` / `sitescore`.
- Canonicalization version is explicit (`v1`).
- Canonicalization rejects non-finite numbers, unsupported objects, and non-string mapping keys; semantic type distinctions such as bool vs int are preserved.
- `ParsedArtifact.parsed_content_hash` identifies canonical parsed content only.
- Parsed derivation identity additionally binds raw content, parser id/version, canonicalization version, and parsed content hash.
- Request fingerprint has independent grammar and canonicalization version axes.
- Semantic fingerprinting excludes secrets and execution/storage noise.
- `SourceMetadata.source_id` commits to provider/dataset/release/vintage/schema/raw-content semantics, not retrieval time or storage path.
- `source_ref` / `source_refs` remain opaque provenance identities; they are not globally guaranteed to equal `SourceMetadata.source_id`.
- Provider failure is not negative site evidence.

### Final hardening incorporated

- Parsed semantic-content identity separated from raw-to-parser derivation identity.
- Canonicalization grammar/version frozen.
- Persistence states hardened (`PERSIST`, `TRANSIENT`, `SOURCE_POLICY`, `DO_NOT_PERSIST`).
- Request-fingerprint grammar + canonicalization version binding.
- `SourceMetadata.source_id` semantic preimage hardened.
- Secret/reference guard added as defense-in-depth.

### Lock baseline

```text
69/69 PASS
ZIP SHA-256:
8dd6c61fb32950acd458b7e738f68d40cf683dcc8c617eda9be4dbf7d604ee50
```

---

## 1.2 Checkpoint 3.3-2 — US Geocoding + Census Geography Resolution

**Status:** LOCKED  
**Purpose:** address → Census geocode evidence → coordinate geography lookup → frozen `GeographyRef[]` / `ResolvedLocation`.

### Production package

```text
src/sitescore_providers/
├── http.py
└── census/
    ├── __init__.py
    ├── builders.py
    ├── client.py
    ├── models.py
    ├── parser.py
    └── policy.py
```

### Main contracts

- generic `HTTPRequest`, `HTTPResponse`, `HTTPTransport`, `UrllibHTTPTransport`
- `CensusCoordinates`
- `CensusGeographyLayerSpec`
- `CensusBenchmarkVintageCompatibility`
- `CensusGeographyManifest`
- `CensusAddressRequest`
- `CensusGeocodeEvidence`, `CensusGeographyEvidence`
- `GeocodeAcceptancePolicy`
- `CensusGeocoderClient`
- `build_geography_refs()` / `build_resolved_location()`

### Frozen invariants

- Census benchmark identity and geography vintage are pinned; `Current` is not canonical.
- Benchmark/vintage pair is supplied through trusted immutable `CensusBenchmarkVintageCompatibility`, not independently self-asserted manifest strings.
- Geography manifest commits to exact requested Census numeric layer IDs, accepted response aliases, and requiredness.
- Requiredness is manifest/config policy, not hard-coded by `GeographyType`.
- Parser maps only aliases authorized by the active manifest; unknown aliases are never guessed.
- `/locations/address` fingerprint contains address + benchmark semantics only; geography vintage/layers do not leak into geocode request identity.
- Geography lookup fingerprint binds coordinates, benchmark, vintage, exact requested layer IDs; response aliases/requiredness remain manifest semantics, not HTTP request semantics.
- `x=longitude`, `y=latitude` preserved.
- `NO_MATCH` / `AMBIGUOUS` are not frozen missing/zero site evidence.
- US V1 is explicitly 50 states + DC; territories are not silently coerced to `country_code="US"`.

### Final hardening incorporated

- Vintage-specific numeric layer identity.
- Manifest-bound response aliases.
- Trusted benchmark/vintage compatibility object.
- Required vs optional layers.
- Operation-specific request fingerprints.

### Lock baseline

```text
127/127 PASS
ZIP SHA-256:
f79c3c409997055c87172236b7606a2ccdbb96a50753db4bbac79944bf406bc0
```

---

## 1.3 Checkpoint 3.3-3 — ACS Acquisition + Statistical Evidence + Demographic Builder

**Status:** LOCKED  
**Purpose:** pinned ACS Detailed Tables acquisition → immutable statistical evidence sidecar → neutral age aggregation → frozen `DemographicSnapshot`.

### Production package

```text
src/sitescore_providers/acs/
├── __init__.py
├── builders.py
├── client.py
├── models.py
├── parser.py
└── request.py
```

### Main contracts

- `ACSVariableSpec`, `ACSVariableManifest`
- `ACSGeographyCompatibility`
- `ACSDatasetManifest`
- `ACSAgeCohortSpec`, `AgeCohortAggregationPolicy`
- `ACSRequest`, `ACSQueryPlan`
- `ACSStatisticalEvidence`
- `ACSEvidenceBundle`
- `ParsedACSResponse`
- `ACSClient`
- `build_evidence_bundle()`
- `build_demographic_snapshot()`
- `DemographicSnapshotLineage`

### Frozen invariants

- Exact ACS release/config is trusted deployment input; no live `latest/current` discovery in canonical identity.
- E/M/EA/MA column IDs are exact and versioned through `ACSVariableManifest`.
- A semantic `ACSVariableSpec` is an atomic query-planning unit; E/M/EA/MA constituents are not split across requests.
- Requests are deterministic and <=50 variables per Census request.
- Statistical estimate and MOE are separate semantic axes.
- MOE is retained in provider-side immutable evidence; it is never converted to arbitrary confidence/data-quality thresholds.
- Derived age-cohort MOE is intentionally deferred; source-cell MOEs remain available in lineage.
- Census special values/annotations are not ordinary numeric evidence.
- `ACSStatisticalEvidence` enforces VALUE/non-VALUE/ANNOTATED cross-field consistency and finite numeric values.
- Raw request fingerprint, raw provider identity, raw content, parsed raw-content hash, parser id/version, and active ACS manifest are structurally bound.
- Cross-chunk evidence bundle must use the same manifest/release/vintage/geography/query plan and exact E/M/EA/MA mappings.
- Demographic builder revalidates canonical evidence bundle and SourceMetadata semantics; factory bypass cannot inject foreign request/column provenance.
- No sector-specific age affinity logic exists in provider layer.

### Final hardening incorporated

- Atomic variable-spec query planning.
- Exact E/M/EA/MA evidence identity.
- Cross-chunk merge coherence.
- Annotation/special-value precedence.
- Raw→parsed→request→manifest lineage binding.
- `ACSStatisticalEvidence` state/value invariants.
- Direct `ACSEvidenceBundle` canonical-validation bypass closed.
- SourceMetadata semantic provenance binding.

### Lock baseline

```text
205/205 PASS
ZIP SHA-256:
b68aaebaaf0d87fc87de88e4be2c111592294fb3657fb61d16d9e63cc500626b
```

---

## 1.4 Checkpoint 3.3-4 — Competition / Overture Places

**Status:** LOCKED  
**Purpose:** pinned Overture Places release artifacts → release/taxonomy evidence → qualifying deduplicated alternatives → multi-scale frozen competition curve/snapshot. No normalization.

### Production package

```text
src/sitescore_providers/overture/
├── __init__.py
├── builders.py
├── models.py
├── parser.py
└── reader.py
```

### Main contracts

- `OverturePlacesReleaseManifest`
- `TaxonomyResolutionPolicy`
- `OvertureCompetitionTaxonomyMapping`, `OvertureTaxonomyRule`
- `PlaceLifecyclePolicy`
- `EntityDedupPolicy`
- `OverturePlaceEvidence`
- `OvertureAttributionManifest`
- `OverturePartitionEvidence`
- `CompetitionCatchmentPolicy` / scales
- `CoverageState`
- `build_measurement_definition_id()`
- `build_competition_snapshot()`

### Frozen invariants

- Overture is an INITIAL PRIOR, not a structural provider requirement.
- Exact release/schema/taxonomy identity is pinned; no mutable latest/current identity.
- Commercial benchmark semantic population remains **commercially evidenced spatial alternatives**.
- Exact Overture taxonomy mapping is release-specific deterministic configuration.
- Canonical taxonomy resolution is hierarchy-first → primary → basic-category fallback/QA; alternates are supporting-only and cannot independently promote/veto.
- Unknown taxonomy does not silently include or exclude.
- Permanently closed places do not count as active competition evidence.
- No arbitrary confidence threshold.
- Exact source-local place ID dedup only; no proximity/name/geometry fuzzy collapse.
- Duplicate exact IDs collapse only when full measurement-relevant evidence is identical; conflicting hierarchy/alternates/status/confidence/coordinates/attribution reject.
- Catchment generation is outside this package; builder consumes explicit multi-scale precomputed membership and spatial-policy identity.
- Missing/unknown coverage is not zero. AVAILABLE zero requires sufficient evidence.
- `measurement_definition_id` excludes site coordinates, processing order, retrieval time, and storage paths, but commits to release/schema/taxonomy/mapping/lifecycle/dedup/catchment/boundary/count/density method semantics.
- Canonical replay requires persisted pinned release partitions.
- Every supplied partition is validated against the active manifest before any coverage-state branch.

### Final hardening incorporated

- Frozen taxonomy field precedence semantics.
- Full exact-ID duplicate evidence comparison.
- Strict taxonomy collection parsing before canonicalization.
- Lifecycle/dedup policy grammar + canonicalization-version binding.
- Correct final release record in docs.
- Coverage-branch partition/manifest/PERSIST validation moved ahead of UNKNOWN/INSUFFICIENT early return.

### Lock baseline

```text
244/244 PASS
ZIP SHA-256:
91ba1fcf73674c311ea82366803ec280025ab85598fbb8c6d2c31438eaff0208
```

---

## 1.5 Checkpoint 3.3-5 — Pedestrian / Walking Network

**Status:** LOCKED  
**Purpose:** pinned walking network + graph/engine/profile identity + origin + walking budgets → Valhalla network isochrone evidence → frozen pedestrian catchment/area snapshot.

### Production package

```text
src/sitescore_providers/pedestrian/
├── __init__.py
├── builders.py
├── client.py
├── models.py
└── parser.py
```

### Main contracts

- `PedestrianNetworkManifest`
- `PedestrianRoutingEngineManifest`
- `PedestrianGraphCompatibility`
- `ValhallaIsochroneExecutionPolicy`
- `ValhallaExecutionBinding`
- `WalkingBudgetPolicy`, `WalkingBudgetScale`
- `PedestrianRoutingOrigin`, `RoutedOriginEvidence`
- `PedestrianGeometryPolicy`, `CanonicalPedestrianGeometry`
- `PedestrianIsochroneEvidence`
- `PedestrianAreaPolicy`, `PedestrianAreaEvidence`
- `PedestrianDerivationEvidence`
- `PedestrianIsochroneClient`
- frozen builders for `PedestrianCatchmentArtifact` / `IsochroneSnapshot`

### Frozen invariants

- OSM-derived network and Valhalla are INITIAL PRIORS, not structural requirements.
- Network source identity and routing-engine/profile identity are distinct.
- Exact graph ↔ network ↔ engine trusted compatibility is explicit.
- Execution binding ties a deployment to expected graph/engine/service-config semantics; endpoint URL itself is not semantic identity.
- Valhalla execution limits (`max_contours`, `max_time_contour`) are explicit and enforced before network calls; no automatic request chunking.
- Request identity binds exact origin, budgets, graph content, profile/options, engine, execution policy/binding; secrets/endpoints/storage locators are excluded.
- `graph_artifact_ref` remains replay/provenance but is excluded from graph compatibility/execution/request semantic hashes.
- `show_locations` exact input vs snapped location is role-resolved without positional assumptions; ambiguous/partial evidence becomes UNKNOWN.
- Warnings are preserved; V1 any warning blocks canonical AVAILABLE evidence rather than silently accepting clamp/deprecation/unknown semantics.
- Missing snap/engine failure/missing contour are not zero reach.
- No straight-line radius fallback.
- Geometry canonicalization normalizes serialization noise only; no topology/GIS engine.
- Area is explicit precomputed evidence bound to geometry + versioned area policy; no WGS84 degrees² calculation.

### Final hardening incorporated

- Valhalla execution limits.
- Deployment execution binding.
- Warning preservation/conservative rejection.
- `show_locations` role ambiguity handling.
- Network raw-content binding and explicit trusted graph attestation boundary.
- Storage `graph_artifact_ref` removed from semantic execution/request identity.

### Lock baseline

```text
292/292 PASS
ZIP SHA-256:
c9f3556af4c05f97ba7ed1545e3540318358d06bab3df43ab1d123f1bb283f4c
```

---

## 1.6 Checkpoint 3.3-6 — GTFS Static Transit

**Status:** LOCKED  
**Purpose:** pinned one-feed GTFS Static bundle + pedestrian reachable stops + service-calendar/frequency policies → 168-hour scheduled/headway service-supply profile → frozen `TransitSnapshot`.

### Production package

```text
src/sitescore_providers/transit/
├── __init__.py
├── builders.py
├── client.py
├── models.py
└── parser.py
```

### Main contracts

- `GTFSFeedManifest`
- `TransitSourceBundle`
- `GTFSServiceCalendarPolicy`
- `GTFSStopHierarchyPolicy`
- `TransitBoardingPolicy`
- `GTFSFrequencyPolicy`
- `TransitWeeklyProfilePolicy`
- `ParsedGTFSFeed`
- `ReachableTransitStopSet`
- `TransitWeeklyServiceProfile`
- acquisition/parser/builders for frozen `TransitSnapshot`

### Frozen invariants

- Transit access is not stop count; canonical unit is unique reachable service-trip instance / departure equivalent.
- V1 source bundle is explicitly one GTFS feed. No silent multi-feed merge.
- Source bundle fingerprint contains transit-source semantics only; site pedestrian reachability does not change it.
- Reachability is precomputed walking-network evidence and must bind to the same GTFS source bundle.
- Calendar = `calendar.txt` weekly service + `calendar_dates.txt` overrides; calendar_dates-only service is valid only when at least one explicit type=1 activation establishes service.
- Removal-only service ID absent from base calendar is unresolvable/malformed and cannot fabricate AVAILABLE zero.
- >24:00 stop times preserve service-day origin and contribute to following-day clock bins.
- Boarding excludes `pickup_type=1` no-pickup stops.
- Same trip at multiple reachable stops counts once per service instance.
- `exact_times=1` expands exact scheduled frequency instances.
- `exact_times=0` or blank yields headway departure equivalents, not a fake timetable.
- Frequency windows for a trip cannot overlap; positive headway and valid intervals required.
- Canonical profile is exactly 168 feed-local service-clock bins, Monday 00 through Sunday 23.
- Weekly profile policy is versioned; V1 uses median same-weekday/hour across explicit reference dates.
- Static schedule supply is not observed/realtime service.
- OUT_OF_VALIDITY / UNKNOWN / missing feed / unresolved reachability are not zero.
- Valid, complete, reachable feed with no scheduled supply can produce AVAILABLE true zero.
- `ReachableTransitStopSet.identity` includes emitted `walk_catchment_ref` and `access_geometry_quality` semantics.

### Final hardening incorporated

- Reachability identity includes catchment-ref and geometry-quality semantics emitted into frozen stops.
- Calendar-dates-only removal cannot establish a resolvable service.

### Lock baseline

```text
344/344 PASS
ZIP SHA-256:
665475158b50aaa3f1cd5a0533e66d5305f9f08edec95bbe2c89d944ad15fcea
```

---

## 1.7 Checkpoint 3.3-7 — Vehicle Road Network

**Status:** LOCKED  
**Purpose:** pinned vehicle network + graph/engine/auto profile + road origin + drive budgets → reproducible road-network reachability → frozen `RoadAccessSnapshot`.

### Production package

```text
src/sitescore_providers/road/
├── __init__.py
├── builders.py
├── client.py
├── models.py
└── parser.py
```

### Main contracts

- `RoadNetworkManifest`
- `RoadTrafficPolicy`
- `RoadRoutingEngineManifest`
- `RoadGraphCompatibility`
- `RoadIsochroneExecutionPolicy`
- `RoadRoutingExecutionBinding`
- `RoadDriveBudgetPolicy`, `RoadDriveBudgetScale`
- `RoadRoutingOrigin`, `RoutedOriginEvidence`
- `RoadGeometryPolicy`, `CanonicalRoadGeometry`
- `RoadIsochroneEvidence`
- `RoadAreaPolicy`, `RoadAreaEvidence`
- `RoadScaleMeasurementEvidence`
- `RoadDerivationEvidence`
- `build_measurement_policy_identity()`
- `RoadIsochroneClient`
- frozen `RoadAccessSnapshot` builder

### Frozen invariants

- Road accessibility is neither traffic score nor parking nor demand.
- OSM/Valhalla are INITIAL PRIORS only.
- V1 routing profile is automobile/`auto`, with explicit version/options identity.
- Canonical V1 traffic policy is static pinned graph/no runtime datetime traffic influence.
- Network, graph, engine/profile, and execution binding are distinct identities.
- `graph_artifact_ref` is provenance/replay only, not semantic request identity.
- Drive budgets are time-based and explicit; no universal radius.
- Valhalla execution limits enforced before network call; no chunking.
- Warnings preserved; unresolved warning blocks AVAILABLE canonical result.
- Road snap unresolved is not zero.
- Frozen observation requires area, reachable network length, connector count, and origin-to-network cost; these are explicit precomputed measurement evidence, not inferred from polygon alone.
- Per-scale measurement-method identity is canonicalized in drive-budget scale order and binds `scale_id`, area-policy identity, network measurement method id/version.
- Caller measurement tuple order cannot change method identity/snapshot.
- Road network `media_type` is manifest-bound; OSM-PBF is not globally hard-coded.
- Raw persisted network bytes are re-read and checked against `RoadNetworkManifest.network_content_hash`.
- No parking/composite logic.

### Final hardening incorporated

- Canonical per-scale measurement-method identity (`ROAD-001`).
- Manifest-bound road-network media type (`ROAD-002`).

### Lock baseline

```text
375/375 PASS
ZIP SHA-256:
5bc6148349a667e61de941e2a48a5f96ada8bd68b4406adf239d8aba5c6713ef
```

---

## 1.8 Checkpoint 3.3-8 — Parking Evidence

**Status:** LOCKED  
**Purpose:** pinned parking inventory + optional explicitly compatible dynamic sidecar + eligibility + road/pedestrian usability compatibility → frozen parking observations/snapshot. No composite/normalization.

### Production package

```text
src/sitescore_providers/parking/
├── __init__.py
├── builders.py
├── models.py
├── parser.py
└── reader.py
```

### Main contracts

- `ParkingSourceManifest`
- `ParkingSourceBundle`
- `ParkingDynamicLinkPolicy`, `ParkingDynamicLinkageMode`
- `ParkingMappingPolicy`
- `ParkingCoverageEvidence`
- `ParkingFacilityEvidence`
- `ParkingDynamicEvidence`
- `ParkingEligibilityPolicy`
- `ParkingMotorReachabilityEvidence`
- `ParkingPedestrianReachabilityEvidence`
- `ParkingAccessibilityCompatibility`
- `ParkingDerivationEvidence`
- source parser/reader/frozen builder

### Frozen invariants

- Parking is separate from road accessibility.
- Generic OSM no mapped parking is UNKNOWN real-world supply, not zero.
- True zero requires affirmative authoritative/exhaustive coverage.
- Capacity comes only from explicit source evidence; missing capacity is not zero; polygon area is never converted to spaces.
- Legal curb length remains meters and is never converted to spaces using magic vehicle length.
- Unknown/private/customer/permit/restricted access is not silently generic public supply.
- Canonical usable facility requires `ELIGIBLE` + resolved motor reachability + resolved pedestrian accessibility.
- Unknown required usability axis is not converted to false/zero.
- Parking code consumes precomputed road/pedestrian compatibility; it does not run hidden routers or straight-line fallbacks.
- `ParkingAccessibilityCompatibility` binds exact active road derivation/graph/drive-policy and pedestrian derivation/walking-policy identities; foreign upstream evidence rejects.
- V1 source bundle is one canonical inventory source + optional dynamic sidecar.
- Dynamic sidecar requires explicit `ParkingDynamicLinkPolicy`.
- V1 supported dynamic linkage is `SHARED_CANONICAL_PARKING_ID`: dynamic native `source_entity_id` must equal the static canonical `parking_id`; arbitrary reassignment/fuzzy matching is rejected.
- Dynamic AVAILABLE occupancy/available-spaces requires source observation timestamp; timestamp is semantic evidence, while retrieval time is not.
- Freshness policy remains deferred; current-looking dynamic state is not invented.
- Exact source-local parking ID dedup only; conflicting canonical evidence rejects.
- Input facility order is canonicalized and cannot alter semantic identity/snapshot.
- No COMB-005, benchmark, ECDF, or normalization logic.

### Final hardening incorporated

- Active road/pedestrian compatibility binding (`PARK-001`).
- Dynamic-sidecar canonical linkage policy (`PARK-002`).

### Lock baseline

```text
418/418 PASS
ZIP SHA-256:
41e3fa4f7b65beca334d75046c89b179309c963c783dad7576dd72a4490e5c74
```

---

# 2. EXACT PROVIDER PACKAGE ARCHITECTURE

Current production tree from the final locked 3.3-8 source:

```text
src/sitescore_providers/
├── __init__.py
├── _validation.py
├── artifacts.py
├── baseline.py
├── errors.py
├── hashing.py
├── http.py
├── identity.py
├── lineage.py
├── parsing.py
├── policy.py
├── results.py
├── census/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   ├── parser.py
│   └── policy.py
├── acs/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   ├── parser.py
│   └── request.py
├── overture/
│   ├── __init__.py
│   ├── builders.py
│   ├── models.py
│   ├── parser.py
│   └── reader.py
├── pedestrian/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   └── parser.py
├── transit/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   └── parser.py
├── road/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   └── parser.py
└── parking/
    ├── __init__.py
    ├── builders.py
    ├── models.py
    ├── parser.py
    └── reader.py
```

### Meaningful tests retained for handoff

```text
tests/test_architecture.py
tests/test_artifacts_and_parsing.py
tests/test_hashing.py
tests/test_policy.py
tests/test_request_fingerprint.py
tests/test_results.py
tests/test_source_metadata.py

tests/test_checkpoint_3_3_2_architecture.py
tests/test_census_*.py

tests/test_acs_checkpoint_3_3_3.py

tests/test_checkpoint_3_3_4_architecture.py
tests/test_overture_checkpoint_3_3_4.py

tests/test_checkpoint_3_3_5_architecture.py
tests/test_pedestrian_checkpoint_3_3_5.py

tests/test_checkpoint_3_3_6_architecture.py
tests/test_transit_checkpoint_3_3_6.py

tests/test_road_checkpoint_3_3_7.py

tests/test_checkpoint_3_3_8_architecture.py
tests/test_parking_checkpoint_3_3_8.py
```

### Meaningful provider records

The final ZIP retains checkpoint records and hardening records under `docs/`, including:

```text
CHECKPOINT_3_3_1_RECORD.md
CHECKPOINT_3_3_2_RECORD.md
CHECKPOINT_3_3_2_IDENTITY_HARDENING_AUDIT.md
CHECKPOINT_3_3_2_FINAL_MANIFEST_HARDENING.md
CHECKPOINT_3_3_3_RECORD.md
CHECKPOINT_3_3_3_STATISTICAL_HARDENING_AUDIT.md
CHECKPOINT_3_3_3_FINAL_LINEAGE_HARDENING.md
CHECKPOINT_3_3_3_FREEZE_HARDENING.md
CHECKPOINT_3_3_4_RECORD.md
CHECKPOINT_3_3_4_COMPETITION_SEMANTIC_HARDENING.md
CHECKPOINT_3_3_4_FREEZE_HARDENING.md
CHECKPOINT_3_3_5_RECORD.md
CHECKPOINT_3_3_5_EXECUTION_LINEAGE_HARDENING.md
CHECKPOINT_3_3_5_FREEZE_HARDENING.md
CHECKPOINT_3_3_6_RECORD.md
CHECKPOINT_3_3_6_TRANSIT_HARDENING.md
CHECKPOINT_3_3_7_RECORD.md
CHECKPOINT_3_3_7_ROAD_HARDENING.md
CHECKPOINT_3_3_8_RECORD.md
CHECKPOINT_3_3_8_PARKING_HARDENING.md
FROZEN_BASELINE.md
```

---

# 3. CROSS-PACKAGE ARCHITECTURAL INVARIANTS

## 3.1 Dependency / ownership

1. `sitescore-providers -> sitescore-data==0.1.0` only.
2. `sitescore-providers` must not import `sitescore-core`.
3. Provider-specific choices remain outside frozen data contracts unless the semantic is genuinely provider-neutral.
4. Rich provider evidence belongs in immutable provider-side sidecars whenever frozen data contracts can represent the downstream result without information loss.
5. A missing provider-side detail is **not** itself justification for modifying `sitescore-data`.

## 3.2 Missing / failure / zero

1. Provider execution failure != bad site evidence.
2. Missing != zero.
3. Unknown != false.
4. Unsupported != zero.
5. Out-of-validity != zero.
6. No mapped record != proven real-world absence unless source coverage is explicitly sufficient/authoritative/exhaustive for that claim.
7. True zero must be affirmative evidence under the active source/method policy.
8. No silent fallback/substitution:
   - no BG→tract ACS fallback;
   - no routing failure→circle fallback;
   - no provider A→provider B substitution;
   - no road-only parking substitution;
   - no missing parking→neutral value.

## 3.3 Release/content pinning

1. Canonical identities must use exact immutable release/content/config identities.
2. Mutable names such as `latest`, `current`, `live`, `today`, `now` are not canonical reproducibility identities.
3. Exact source bytes/content hash are distinct from release labels, parser identity, request identity, and storage locator.
4. Publicly expiring remote releases require persistent/content-addressed replay evidence when canonical reproduction depends on them.

## 3.4 Semantic identity vs locator

1. `ArtifactRef`, URL, file path, cache path, endpoint URL, server hostname, worker ID, retry metadata, and similar locators/execution details do **not** alter semantic identity unless the value is itself part of provider semantics.
2. Content hash, exact release, graph build, parser version, policy version, method version, and source semantic identity **do** alter semantic identity when they change behavior/evidence.
3. `graph_artifact_ref` is explicitly replay/provenance for pedestrian/road; it is excluded from graph/execution/request semantic hashes.

## 3.5 Request identity

1. `RequestFingerprint = actual semantic provider request`, not pipeline-object identity.
2. Provider request fingerprints bind only fields that affect provider execution semantics.
3. Pipeline/manifest/policy identities may be separate from HTTP/request identity when they do not change actual request parameters.
4. Secrets/auth tokens never enter request fingerprints, raw identity, source references, or logs/reference strings.

## 3.6 Raw / parsed / manifest provenance

Canonical lineage pattern:

```text
trusted manifest/config
  -> semantic RequestFingerprint
  -> RawAcquisitionArtifact
  -> exact content hash
  -> ParsedArtifact
  -> provider evidence
  -> frozen sitescore-data snapshot
```

Required coherence where applicable:

- raw request fingerprint == expected request fingerprint;
- raw provider identity == active manifest/provider semantics;
- raw content hash == pinned source content identity when source bytes are canonical;
- parsed raw-content hash == raw content hash;
- parsed parser id/version == active parser identity;
- SourceMetadata provider/dataset/release/vintage/schema/content == source semantics used by the evidence;
- same bytes + unrelated provider/dataset metadata must reject.

## 3.7 Canonicalization / determinism

1. Canonical JSON/versioned hashing from foundation is the shared primitive for provider semantic identities.
2. Semantically unordered input must be normalized before hashing.
3. Processing/input tuple order must not leak into identities or frozen outputs.
4. Per-scale methods must be associated with scale identity, not merely tuple position.
5. Same evidence + same policies/manifests + same explicit `generated_at` must yield the same frozen primitive.
6. Semantic/artifact derivation identity may intentionally exclude `generated_at`; primitive equality and derivation identity are distinct concepts.
7. `retrieved_at` is provenance/execution time, not source observation time and not normally a semantic measurement identity.
8. Source observation timestamps such as parking `availability_timestamp` **are** semantic evidence.

## 3.8 Persistence

1. Persistence policy stays provider/config-specific and does not leak into generic foundation as `if provider == X` rules.
2. Canonical source replay may require `PERSIST` where upstream releases are mutable/short-lived.
3. A `SOURCE_POLICY` decision is unresolved until caller/provider policy resolves it to a concrete persistence behavior.
4. Storage location is never substituted for content identity.

## 3.9 Measurement-definition compatibility

1. Site and benchmark must use the same measurement semantics for a normalized comparison.
2. Competition explicitly exposes `measurement_definition_id`.
3. Transit explicitly exposes `source_bundle_fingerprint`; site reachability is derivation identity, not feed-source identity.
4. Road currently exposes detailed method/version identities through observations/provider sidecars; future benchmark normalization must compare the same road measurement semantics before constructing a scalar normalized feature.
5. Parking benchmark/comparison must preserve identical eligibility, coverage, capacity, curb, motor/pedestrian compatibility semantics.

---

# 4. EXACT FROZEN DATA CONTRACTS USED BY PROVIDERS / FAZ 3.4

The authoritative source is `sitescore-data v0.1.0`. This section lists only the contracts relevant to provider outputs and the next-phase assembly/readiness boundary.

## 4.1 `SourceMetadata`

**File:** `src/sitescore_data/schemas/common.py`  
**Purpose:** metadata registry entry for one source identity known to a pipeline result.

Important fields:

```text
source_id
provider
dataset
dataset_release
vintage
schema_version
retrieved_at
content_hash
persistence_class
data_quality
license_class
attribution_required
source_reference
```

Downstream invariant: `source_ref/source_refs` across contracts are opaque identities and are not universally required to equal a `SourceMetadata.source_id`.

## 4.2 `MetricValue`

**File:** `schemas/common.py`

Fields:

```text
value
unit
availability
data_quality
score_eligibility
calibration_state
is_estimate
is_proxy
source_refs
method_version
reason_codes
```

The four state axes are independent and must not be collapsed:

```text
AvailabilityState
DataQualityState
ScoreEligibility
CalibrationState
```

## 4.3 `ResolvedLocation`

**File:** `schemas/geography.py`

Fields:

```text
latitude
longitude
formatted_address
country_code
geography_refs
source_refs
resolution_method_version
generated_at
```

Purpose: canonical geocoded site location + resolved census/geographic references. Source refs must cover nested geography references.

## 4.4 `DemographicSnapshot` / `AgeCohortPopulation`

**File:** `schemas/demographics.py`

`AgeCohortPopulation`:

```text
cohort_id
age_min_inclusive
age_max_exclusive
population
population_share
```

`DemographicSnapshot`:

```text
geography_ref
total_population
age_cohorts
household_income
source_refs
availability
data_quality
generated_at
```

Important: numeric ACS MOE is not stored here; immutable ACS statistical sidecar retains estimate/MOE/annotation lineage.

## 4.5 `PedestrianCatchmentArtifact` / `IsochroneSnapshot`

**File:** `schemas/pedestrian.py`

`PedestrianCatchmentArtifact`:

```text
catchment_id
origin_location_ref
origin_latitude
origin_longitude
travel_mode
travel_cost_budget_seconds
geometry_ref
source_refs
policy_version
generated_at
```

Frozen `travel_mode` is walk; catchment stores a geometry reference, not geometry bytes.

`IsochroneSnapshot`:

```text
snapshot_id
catchment_ref
area_km2
source_refs
availability
data_quality
method_version
generated_at
```

`area_km2` is a `MetricValue`; provider geometry/graph/snap sidecars remain external.

## 4.6 `CompetitionObservation` / `CompetitionCurve` / `CompetitionSnapshot`

**File:** `schemas/competition.py`

`CompetitionObservation`:

```text
scale_id
travel_mode
catchment_semantics
travel_cost
travel_cost_unit
competitor_count
catchment_area_km2
competitor_density_per_km2
source_refs
method_version
```

Density must equal count/area according to the frozen constructor.

`CompetitionCurve` is an ordered tuple of observations; canonical provider builder emits drive/catchment policy order deterministically.

`CompetitionSnapshot`:

```text
snapshot_id
measurement_definition_id
curve
benchmark_ref
source_refs
availability
data_quality
generated_at
```

`measurement_definition_id` is the key future benchmark compatibility identity.

## 4.7 `TransitStopRef`

**File:** `schemas/transit.py`

```text
feed_id
stop_id
location_type
parent_station_id
canonical_station_id
latitude
longitude
access_geometry_quality
reachable_by_walk
walk_catchment_ref
source_ref
```

This is reachable service infrastructure evidence, not the transit accessibility metric itself.

## 4.8 `TransitServiceWindow`

```text
timezone
validity_state
validity_start
validity_end
reference_dates
temporal_policy_version
service_calendar_version
profile_type = typical_published_week
hour_bins = 168
calendar_exceptions_applied = True
service_day_over_24h_semantics = True
```

Canonical 168 profile semantics are frozen here.

## 4.9 `TransitObservation`

```text
hour_of_week
scheduled_exact_departures
frequency_departure_equivalents
total_departure_equivalents
```

Invariant:

```text
total = scheduled_exact + frequency_equivalents
```

## 4.10 `TransitSnapshot`

```text
snapshot_id
stops
service_window
observations
service_departure_equivalents_per_hour
benchmark_ref
source_bundle_fingerprint
source_refs
availability
data_quality
generated_at
```

AVAILABLE requires exactly 168 ordered observations. The primary metric is the mean of their total departure equivalents.

## 4.11 `RoadObservation`

**File:** `schemas/road.py`

```text
travel_cost_seconds
reachable_area_km2
reachable_network_length_km
reachable_connector_count
origin_to_network_cost_seconds
benchmark_percentile
source_refs
method_version
```

Provider checkpoint leaves `benchmark_percentile=None`.

## 4.12 `RoadAccessSnapshot`

```text
snapshot_id
road_origin_ref
road_origin_quality
routing_profile_id
routing_profile_version
observations
benchmark_ref
source_refs
availability
data_quality
generated_at
```

`RoadOriginQuality` frozen values:

```text
VEHICLE_ENTRANCE
DRIVEWAY
ROAD_SEGMENT_FALLBACK
UNRESOLVED
```

No parking/composite metric is part of this snapshot.

## 4.13 `ParkingObservation`

**File:** `schemas/parking.py`

```text
parking_id
parking_mode
access_class
generic_public_supply_eligible
capacity
motor_vehicle_reachable
walk_time_to_site_seconds
curb_length_m
occupancy
available_spaces
availability_timestamp
source_ref
```

Important frozen invariants:

- public/permissive generic-supply flag must be coherent with access class;
- capacity unit = spaces;
- walk time unit = seconds;
- curb length unit = meters;
- occupancy unit = ratio;
- available spaces unit = spaces;
- occupancy AVAILABLE or available_spaces AVAILABLE => aware `availability_timestamp` required;
- if neither dynamic metric is AVAILABLE => timestamp must be `None`;
- known available spaces cannot exceed known capacity.

## 4.14 `ParkingSnapshot`

```text
snapshot_id
observations
mapped_public_facility_count
known_public_offstreet_capacity
unknown_capacity_facility_count
mapped_legal_curb_length_m
known_onstreet_capacity
dynamic_availability_present
source_refs
availability
data_quality
score_eligibility
generated_at
```

Capacity and legal curb length are intentionally separate dimensions/units.

## 4.15 `DerivedLocationMetrics`

**File:** `schemas/features.py`

```text
walkable_population
target_population_density
household_income
household_income_ratio
competition_pressure
walkable_reach_area_km2
transit_service_departure_equivalents_per_hour
road_reachable_area_km2
parking_public_offstreet_capacity
parking_legal_curb_length_m

demographic_snapshot_ref
competition_snapshot_ref
road_snapshot_ref
parking_snapshot_ref
source_refs
feature_contract_version
generated_at
```

Critical frozen rule:

```text
competition_pressure numeric
or road_reachable_area_km2 numeric
=> MetricValue.calibration_state must be CALIBRATED
```

Therefore multi-scale provider curves/road observations cannot be silently reduced to these scalars before an approved calibrated reduction policy exists.

## 4.16 `NormalizedLocationFeatures`

Exact frozen eight scores:

```text
walkable_population_score
target_population_density_score
age_target_concentration_score
competition_opportunity_score
walkable_reach_area_score
transit_access_score
road_parking_access_score
household_income_score
```

Each is a `MetricValue` with unit `score_0_100` when numeric.

Compatibility metadata:

```text
competition_benchmark_ref
competition_measurement_definition_id
competition_normalization_policy_version

transit_benchmark_ref
transit_source_bundle_fingerprint
transit_normalization_policy_version

road_parking_composite_policy_version
```

## 4.17 `ScoringReadinessResult`

**Files:** `schemas/readiness.py`, `validators/readiness.py`

Purpose: terminal data-layer permission boundary for later category aggregation.

Key fields:

```text
is_score_ready
missing_required_features
uncalibrated_features
insufficient_quality_features
incompatible_features
reason_codes
required_policy_versions
resolved_policy_versions
feature_states
validator_version
evaluated_at
readiness_fingerprint
```

Canonical V1 requirements:

- exactly the eight frozen normalized features in frozen order;
- every feature is required;
- unavailable required metric blocks readiness;
- quality other than FULL/DEGRADED blocks readiness;
- DIAGNOSTIC_ONLY or otherwise non-ELIGIBLE blocks readiness;
- UNCALIBRATED blocks readiness except exact approved age fallback;
- competition measurement definition must match benchmark measurement definition;
- transit source-bundle fingerprint must match benchmark source-bundle fingerprint;
- road+parking requires AVAILABLE + ELIGIBLE + CALIBRATED + non-null composite policy version.

Exact age fallback:

```text
feature = age_target_concentration_score
policy id = age_neutral_fallback
policy version = 1.0
value = 50
availability = AVAILABLE
calibration_state = UNCALIBRATED
score_eligibility = ELIGIBLE
is_proxy = True
reason code contains age_affinity_not_calibrated
explicit ApprovedFallbackPolicyRef required
```

## 4.18 `RealDataPipelineResult`

**File:** `schemas/pipeline.py`

Carries optional provider/domain snapshots plus derived metrics, normalized features, readiness, deterministic sorted `SourceMetadata`, data-contract versions, and terminal pipeline status.

Important monotonicity:

```text
normalized_features -> derived_metrics required
scoring_readiness   -> normalized_features required
```

Terminal states:

```text
SCORE_READY:
  resolved_location required
  normalized_features required
  scoring_readiness required and is_score_ready=True
  reason_codes = ()

NOT_SCORE_READY:
  scoring_readiness required and is_score_ready=False
  reason_codes = (SCORING_NOT_READY,)

PIPELINE_ERROR:
  scoring_readiness must be None
  reason_codes = (PIPELINE_STAGE_ERROR,)
```

The data layer stops at SCORE_READY. It does not construct core category scores or invoke `sitescore-core analyze()`.

## 4.19 Benchmark contracts

**File:** `schemas/benchmarks.py`

### `CommercialBenchmarkFrameMetadata`

Key fields:

```text
frame_id / frame_version
population_type
benchmark_geography_ref
spatial_representation
tessellation_topology
projection_method / projection_reference
selected_resolution / unit
resolution_policy_version
eligibility_policy_version
source_refs
eligible_count / ineligible_count / unknown_count
generated_at
```

Frozen structural markers:

```text
population_type = COMMERCIALLY_EVIDENCED_SPATIAL_ALTERNATIVES
spatial_representation = EQUAL_AREA
```

### `BenchmarkReference`

```text
benchmark_id
artifact_ref
frame_id / frame_version
population_type
benchmark_geography_ref
source_refs
```

This is a lightweight persisted benchmark reference; benchmark construction is not implemented in FAZ 3.3.

---

# 5. PROVIDER OUTPUT → DOWNSTREAM METRIC MAP

| Provider | Frozen/provider output now available | `DerivedLocationMetrics` target | Assembly status |
|---|---|---|---|
| Census Geography | `ResolvedLocation`, `GeographyRef[]` | pipeline location/context, refs for demographics/benchmarks | AVAILABLE |
| ACS | `DemographicSnapshot.total_population`, `age_cohorts`, `household_income`; ACS MOE sidecar | `household_income` | MAPPING NOT YET ASSEMBLED |
| ACS + Pedestrian geometry | demographics + walking catchment | `walkable_population` | **NOT YET ASSEMBLED** — requires demographic/catchment spatial overlay |
| ACS + Pedestrian geometry | demographic cells/cohorts + catchment area | `target_population_density` | **NOT YET ASSEMBLED** — requires target-age policy + spatial overlay/area |
| ACS / economic benchmark | household income | `household_income_ratio` | **NOT YET ASSEMBLED** — requires reference/benchmark ratio policy |
| Competition | `CompetitionSnapshot.curve`: count/area/density per scale + `measurement_definition_id` | `competition_pressure` | **NOT YET ASSEMBLED** — numeric scalar must be CALIBRATED |
| Pedestrian | `PedestrianCatchmentArtifact` + `IsochroneSnapshot.area_km2` | `walkable_reach_area_km2` | **NOT YET ASSEMBLED** — scale-selection/reduction policy not implemented |
| Transit | `TransitSnapshot.service_departure_equivalents_per_hour` + 168 profile | `transit_service_departure_equivalents_per_hour` | MAPPING NOT YET ASSEMBLED; source metric exists directly |
| Road | multi-scale `RoadObservation` area/network/connectors/cost | `road_reachable_area_km2` | **NOT YET ASSEMBLED** — numeric scalar reduction must be CALIBRATED |
| Parking | `known_public_offstreet_capacity` | `parking_public_offstreet_capacity` | MAPPING NOT YET ASSEMBLED; source metric exists directly |
| Parking | `mapped_legal_curb_length_m` | `parking_legal_curb_length_m` | MAPPING NOT YET ASSEMBLED; source metric exists directly |

### Normalized feature inputs still to be built

```text
walkable_population_score              <- DerivedLocationMetrics.walkable_population

target_population_density_score        <- DerivedLocationMetrics.target_population_density

age_target_concentration_score         <- age-cohort calibration OR exact approved neutral fallback

competition_opportunity_score          <- calibrated benchmark ECDF using compatible competition measurement definition

walkable_reach_area_score              <- normalized pedestrian reach-area metric

transit_access_score                    <- normalized scheduled/headway service-supply metric under same TransitSourceBundle benchmark semantics

road_parking_access_score              <- calibrated COMB-005 composite only

household_income_score                  <- normalized household-income/economic reference metric
```

No provider package currently constructs `DerivedLocationMetrics` or `NormalizedLocationFeatures` end-to-end.

---

# 6. BENCHMARK / NORMALIZATION HANDOFF

## 6.1 STRUCTURAL LOCK

### General benchmark frame

- Benchmark population semantics: **commercially evidenced spatial alternatives**.
- Commercial frame spatial representation: **equal area**.
- Eligibility is tri-state: eligible / ineligible / unknown; unknown is not silently eligible or ineligible.
- Full-frame-first semantics: construct/qualify the frame before sampling/normalizing.
- Equal eligible-cell weighting: each eligible equal-area cell receives equal benchmark weight.
- No arbitrary benchmark threshold may replace the versioned eligibility/measurement definition.
- Site and benchmark must use the same measurement semantics before a normalized comparison is legal.

### Competition

- Semantic ontology policy is structural.
- Frozen semantic classes:
  - INCLUDE: retail, food/drink, personal services, customer-facing recreation/fitness, lodging, malls/marketplaces.
  - CONDITIONAL: healthcare, professional services, automotive, paid attractions.
  - EXCLUDE: standalone education, religious, government, industrial, office-only, transit, natural/public attractions.
- Exact Overture taxonomy mapping is release-specific deterministic artifact/config, not a global unversioned category map.
- Site `CompetitionSnapshot.measurement_definition_id` must equal benchmark measurement-definition identity later supplied to readiness.
- Competition density/count semantics are **commercially evidenced spatial alternatives**, not inferred real-world completeness.

### Mid-ECDF normalization shape

Frozen structural ECDF rule:

```text
mid_ecdf(x) = ( count(v < x) + 0.5 * count(v == x) ) / N
```

Properties:

- exact ties receive the same mid-rank probability;
- endpoints are determined by the half-mass tie treatment rather than forced 0/1 interpolation;
- no interpolation between empirical observations;
- benchmark artifact/policy must record exact measurement identity and population/frame identity used.

Feature polarity (e.g. whether a raw pressure ECDF is inverted into an opportunity score) belongs to the explicit normalization policy; provider code does not decide it.

### Transit

- Primary transit evidence is scheduled/headway service supply, not stop count.
- 168 feed-local service-clock bins remain the canonical profile representation.
- Site and benchmark must use the **same `TransitSourceBundle` fingerprint**.
- Source bundle identity deliberately excludes site pedestrian catchment; transit derivation identity includes site reachability.

### Road

- Road benchmark is separate from parking benchmark/composite.
- Road accessibility is pinned vehicle-network reachability, not congestion/commute score.
- Any future road scalar/benchmark must use the same network/profile/drive-budget/measurement-method semantics as the site evidence.

### Parking

- No mapped parking != zero.
- Capacity and legal curb length are separate dimensions.
- Benchmark comparability requires the same coverage, eligibility, motor/pedestrian compatibility, capacity, curb-legality, and dynamic/static semantics.

### Age fallback

The exact neutral fallback mechanism is structurally frozen:

```text
value = 50
is_proxy = True
calibration_state = UNCALIBRATED
score_eligibility = ELIGIBLE
availability = AVAILABLE
reason = age_affinity_not_calibrated
fallback policy = age_neutral_fallback / 1.0
explicit approval required
```

This is not an empirical age calibration.

## 6.2 INITIAL PRIOR

- Overture Places for persistent competition source.
- OSM-derived routable graph + Valhalla for walking/road.
- Census Geocoder for US address/geography.
- ACS 5-Year Detailed Tables for demographics.
- GTFS Static for transit scheduled supply.
- OSM parking as supplementary/community-mapped inventory.

Provider priors may be replaced if the structural identities/semantics remain satisfied.

## 6.3 CALIBRATION REQUIRED

- Benchmark spatial resolution tolerance / final selected resolution policy. Once selected, exact resolution must be frozen in `CommercialBenchmarkFrameMetadata`.
- Competition scalar reduction and normalized `competition_opportunity_score` policy/artifact.
- Transit normalized `transit_access_score` policy/artifact.
- Pedestrian reach-area normalization.
- Household-income normalization/reference ratio.
- Road multi-scale scalar reduction/benchmark normalization.
- COMB-005 road+parking composite.
- Empirical age-target calibration if replacing/augmenting neutral fallback.
- Any feature calibration required to produce `MetricValue.calibration_state=CALIBRATED` before SCORE_READY.

## 6.4 DEFERRED

- Benchmark-frame builders/artifact acquisition.
- ECDF artifact implementation/persistence.
- Normalization code.
- Pipeline assembly into `DerivedLocationMetrics` / `NormalizedLocationFeatures`.
- App-layer category aggregation and core adapter.

---

# 7. SCORING READINESS HANDOFF

## Exact frozen normalized feature surface

Canonical order:

```text
1. walkable_population_score
2. target_population_density_score
3. age_target_concentration_score
4. competition_opportunity_score
5. walkable_reach_area_score
6. transit_access_score
7. road_parking_access_score
8. household_income_score
```

All eight are structurally required in canonical V1 readiness. `required=False` is not a valid canonical V1 policy.

## Per-feature readiness blockers

For any required feature:

```text
availability != AVAILABLE
-> missing_required_feature

quality not FULL/DEGRADED
-> insufficient_data_quality

score_eligibility == DIAGNOSTIC_ONLY
-> feature_diagnostic_only

score_eligibility != ELIGIBLE
-> feature_ineligible

calibration_state == UNCALIBRATED
-> feature_uncalibrated
   except exact approved age fallback
```

Policy-version requirements must also be configured and match.

## Age fallback exact triple/mechanism

Only `age_target_concentration_score` may use a V1 approved fallback. Required exact values are listed in §6.1. Any variation or missing explicit approval produces uncalibrated/invalid-fallback readiness reasons.

## Competition compatibility

Readiness requires:

```text
NormalizedLocationFeatures.competition_benchmark_ref != None
NormalizedLocationFeatures.competition_measurement_definition_id != None
ReadinessCompatibilityInput.competition_benchmark_measurement_definition_id != None

site normalized measurement_definition_id
== benchmark measurement_definition_id
```

Mismatch => `COMPETITION_MEASUREMENT_MISMATCH`.

The pipeline envelope additionally checks normalized competition measurement identity against the attached site `CompetitionSnapshot` when both are present.

## Transit compatibility

Readiness requires:

```text
transit_benchmark_ref != None
transit_source_bundle_fingerprint != None
benchmark source_bundle_fingerprint != None

site source_bundle_fingerprint
== benchmark source_bundle_fingerprint
```

Mismatch => `TRANSIT_SOURCE_BUNDLE_MISMATCH`.

The pipeline envelope additionally checks normalized transit source-bundle fingerprint against attached site `TransitSnapshot` when both are present.

## COMB-005 gate

`road_parking_access_score` must be:

```text
AVAILABLE
ELIGIBLE
CALIBRATED
road_parking_composite_policy_version != None
```

Otherwise reason = `ROAD_PARKING_COMPOSITE_UNAVAILABLE` and the feature is incompatible.

## SCORE_READY / NOT_SCORE_READY / PIPELINE_ERROR

`ScoringReadinessResult.is_score_ready` is true only when there are no blocking global reasons.

Data-layer terminal contract:

```text
SCORE_READY
-> normalized features exist
-> readiness is true
-> app-layer category aggregation is permitted

NOT_SCORE_READY
-> readiness is false
-> pipeline reason is SCORING_NOT_READY
-> do NOT create ReadyCategoryScorePayload
-> CategoryScores must remain null/not constructed at app integration
-> sitescore-core analyze() MUST NOT be called

PIPELINE_ERROR
-> scoring_readiness is absent
-> pipeline reason is PIPELINE_STAGE_ERROR
-> this is execution/data-pipeline failure, not readiness failure
```

`sitescore-data` does not perform category aggregation. Future flow is:

```text
RealDataPipelineResult(SCORE_READY)
-> sitescore-app category aggregation
-> readiness-gated ReadyCategoryScorePayload
-> core CategoryScores adapter
-> sitescore-core analyze()
```

---

# 8. ROAD + PARKING COMB-005 HANDOFF

## Frozen

- Independent road evidence exists: `RoadAccessSnapshot` + provider road derivation sidecars.
- Independent parking evidence exists: `ParkingSnapshot` + provider parking derivation sidecars.
- Frozen normalized feature surface contains exactly one composite slot: `road_parking_access_score`.
- `NormalizedLocationFeatures` contains `road_parking_composite_policy_version`.
- Readiness requires the composite feature to be AVAILABLE, ELIGIBLE, CALIBRATED, and version-bound.
- No substitution.
- No neutral fallback.
- No renormalization of remaining features when parking/road is unavailable.

## Not frozen / not implemented

- No road/parking weights.
- No combination formula.
- No calibration dataset/artifact.
- No benchmark composite distribution.
- No missing-axis fallback.

## Forbidden future shortcuts

```text
50/50 road+parking without calibrated policy
road-only fallback when parking missing
parking-only fallback when road missing
parking missing -> neutral 50
hidden weights
renormalize other accessibility features
```

## Exact prerequisite for score-readiness

Before `road_parking_access_score` may become score-ready, future FAZ 3.4+ must provide:

1. compatible usable road evidence;
2. compatible usable parking evidence;
3. explicit versioned COMB-005 combination policy;
4. empirically calibrated combination/reduction logic;
5. normalized `score_0_100` MetricValue marked AVAILABLE + ELIGIBLE + CALIBRATED;
6. `road_parking_composite_policy_version` matching the required readiness policy version;
7. deterministic source/method lineage.

Until then the feature remains NOT_SCORE_READY.

---

# 9. ALL DEFERRED WORK

Legend:

- **REQUIRED BEFORE SCORE_READY** — required to produce the frozen eight-feature score-ready surface.
- **OPTIONAL / DEPLOYMENT** — exact production provider/environment choice; does not change structural architecture.
- **FUTURE / V2** — accepted limitation or extension not required for V1 if a valid production configuration exists.

## 9.1 Provider deployment/config

| Item | Classification |
|---|---|
| Exact production Census benchmark/vintage compatibility config | OPTIONAL / DEPLOYMENT |
| Exact ACS release + variable manifest | OPTIONAL / DEPLOYMENT |
| Exact Overture production release/schema/taxonomy mapping artifact | OPTIONAL / DEPLOYMENT, but required for production competition evidence |
| Exact production OSM/network extracts | OPTIONAL / DEPLOYMENT, but required for production routing evidence |
| Exact Valhalla engine version, graph build/content, deployment binding | OPTIONAL / DEPLOYMENT, but required for production routing evidence |
| Walking budget scales | OPTIONAL / DEPLOYMENT / calibration policy |
| Drive budget scales | OPTIONAL / DEPLOYMENT / calibration policy |
| Exact GTFS feed/release | OPTIONAL / DEPLOYMENT, required for production transit evidence |
| Parking canonical inventory provider(s) | OPTIONAL / DEPLOYMENT |
| Municipal authoritative parking adapters | OPTIONAL / DEPLOYMENT |

## 9.2 Benchmark acquisition/frame

| Item | Classification |
|---|---|
| Commercial equal-area benchmark-frame construction | REQUIRED BEFORE SCORE_READY for benchmark-normalized features |
| Competition benchmark measurements using same measurement_definition_id | REQUIRED BEFORE SCORE_READY |
| Transit benchmark profiles using same TransitSourceBundle fingerprint | REQUIRED BEFORE SCORE_READY |
| Road benchmark under same measurement semantics | REQUIRED BEFORE SCORE_READY for road normalization/composite |
| Parking benchmark/reference evidence where composite calibration needs it | REQUIRED BEFORE SCORE_READY for COMB-005 calibration |
| Final benchmark spatial resolution after empirical tolerance calibration | REQUIRED BEFORE SCORE_READY for affected benchmark artifacts |

## 9.3 Normalization/calibration

| Item | Classification |
|---|---|
| Mid-ECDF artifact implementation | REQUIRED BEFORE SCORE_READY for ECDF-normalized features |
| Competition multi-scale reduction + opportunity normalization | REQUIRED BEFORE SCORE_READY |
| Transit access normalization | REQUIRED BEFORE SCORE_READY |
| Walkable reach normalization | REQUIRED BEFORE SCORE_READY |
| Household-income normalization/ratio reference | REQUIRED BEFORE SCORE_READY |
| Road multi-scale scalar reduction/normalization | REQUIRED BEFORE SCORE_READY |
| COMB-005 road+parking calibration | REQUIRED BEFORE SCORE_READY |
| Age empirical calibration | OPTIONAL if exact neutral fallback is explicitly approved; otherwise REQUIRED BEFORE SCORE_READY |
| Full empirical model validation | REQUIRED before production confidence in scoring, although structural SCORE_READY can be tested earlier with approved calibrated artifacts |

## 9.4 Geospatial computation

| Item | Classification |
|---|---|
| Actual geodesic/equal-area polygon area engine | REQUIRED for production area evidence unless supplied by trusted external precomputation |
| Demographic × walking-catchment spatial overlay | REQUIRED BEFORE SCORE_READY (`walkable_population`, target density) |
| Road reachable network-length/connector measurement implementation | REQUIRED for production road snapshots unless externally precomputed |
| Benchmark equal-area tessellation/projection processing | REQUIRED BEFORE benchmark artifacts |

## 9.5 Source discovery

| Item | Classification |
|---|---|
| Production ACS release discovery/selection UI/config | OPTIONAL / DEPLOYMENT |
| Overture release discovery | OPTIONAL / DEPLOYMENT; must resolve to exact pinned release before canonical use |
| GTFS feed discovery | OPTIONAL / DEPLOYMENT |
| Routing extract discovery | OPTIONAL / DEPLOYMENT |

## 9.6 Cross-source reconciliation

| Item | Classification |
|---|---|
| Multi-feed GTFS merging/namespacing | FUTURE / V2 |
| Cross-source parking facility reconciliation | FUTURE / V2 |
| Fuzzy parking matching by distance/name/geometry | FUTURE / V2; explicitly not allowed in V1 |
| Exact dynamic parking mapping artifact mode beyond shared canonical IDs | FUTURE / V2 |
| Subject-property private/customer parking qualification | FUTURE / V2 or explicit future policy |

## 9.7 Dynamic/freshness

| Item | Classification |
|---|---|
| Parking dynamic freshness/staleness policy | FUTURE / V2 unless dynamic current-state feature later depends on it |
| GTFS Realtime cancellations/delays | FUTURE / V2 |
| Traffic-aware road accessibility | FUTURE / V2; current V1 is static graph/no datetime |

## 9.8 App/backend

| Item | Classification |
|---|---|
| DerivedLocationMetrics assembler | REQUIRED BEFORE SCORE_READY |
| NormalizedLocationFeatures builder | REQUIRED BEFORE SCORE_READY |
| Benchmark artifact persistence/registry | REQUIRED BEFORE SCORE_READY for benchmark features |
| ScoringReadinessValidator orchestration | REQUIRED BEFORE SCORE_READY |
| RealDataPipelineResult assembly | REQUIRED BEFORE app/core integration |
| sitescore-app category aggregation | REQUIRED after SCORE_READY to call core |
| ReadyCategoryScorePayload → core CategoryScores adapter | REQUIRED after SCORE_READY |
| sitescore-core analyze() integration | REQUIRED only after readiness/category payload gate |

## 9.9 Empirical validation

| Item | Classification |
|---|---|
| Benchmark resolution tolerance validation | REQUIRED before final benchmark resolution freeze |
| Normalization calibration datasets and stability analysis | REQUIRED BEFORE SCORE_READY for calibrated features |
| COMB-005 empirical validation | REQUIRED BEFORE SCORE_READY |
| Sector-specific age calibration | Optional while exact neutral fallback is valid; eventually empirical |
| End-to-end field validation against real locations | REQUIRED before production launch |

---

# 10. KNOWN NON-BLOCKING LIMITATIONS ACCEPTED AT FREEZE

These are accepted boundaries, not bugs:

1. ACS MOE remains provider-side statistical evidence; frozen `DemographicSnapshot` has no numeric MOE field.
2. Derived age-cohort MOE is not generated; raw source-cell MOEs are retained.
3. ACS exact production variable manifest/release is deployment configuration.
4. Overture exact production taxonomy mapping must be populated/reviewed per pinned release.
5. Pedestrian/road graph content is trusted deployment attestation at runtime; `/status` is not falsely treated as cryptographic graph proof.
6. Pedestrian/road actual area calculation can be externally/precomputed evidence; provider code intentionally has no GIS area engine.
7. Pedestrian no-snap remains UNKNOWN/unresolved, never zero.
8. GTFS V1 is one-feed only.
9. GTFS V1 does not interpolate missing stop-time departure timestamps.
10. GTFS Static represents published scheduled/headway supply, not observed operation.
11. Transit weekly profile is feed-local service clock; it does not attempt elapsed-hour DST traffic simulation.
12. Road V1 uses static pinned graph/no datetime traffic semantics.
13. Road vehicle-entrance/driveway refinement is not implemented; normal network snap maps to road-segment fallback quality.
14. Road network length/connectors/area can be supplied by trusted versioned measurement evidence rather than derived from Valhalla polygon alone.
15. Parking V1 is one canonical inventory source + optional dynamic sidecar.
16. Parking dynamic sidecar V1 requires shared canonical parking ID namespace.
17. No fuzzy cross-source parking matching.
18. No dynamic parking freshness threshold.
19. Subject-property private/customer parking is not automatically eligible.
20. Generic OSM parking incompleteness means empty mapping remains UNKNOWN, not zero.
21. No road+parking composite exists yet.
22. No benchmark/normalization implementation exists yet.

---

# 11. PROVIDER SOURCE / DEPLOYMENT PRIORS

| Provider / source | Status | Meaning |
|---|---|---|
| Census Geocoder | INITIAL PRIOR / DEPLOYMENT CHOICE | Current implemented US geocoding/geography provider. Exact pinned compatibility config required. Not a universal structural requirement. |
| ACS 5-Year Detailed Tables | INITIAL PRIOR / DEPLOYMENT CHOICE | Implemented demographic statistical source. Neutral evidence semantics are structural; exact ACS provider/release is not. |
| Overture Places | INITIAL PRIOR | Implemented competition source candidate. Structural requirements are release/taxonomy/measurement identity and deterministic commercial-alternative semantics, not Overture itself. |
| OSM-derived routable network | INITIAL PRIOR | Implemented network-source pattern for pedestrian/road; exact source/provider may change if pinned content semantics remain. |
| Valhalla | INITIAL PRIOR | Implemented routing engine pattern; engine/profile/graph/execution identity is structural, Valhalla brand is not. |
| GTFS Static | STRUCTURAL FORMAT PRIOR for current transit implementation / industry-standard source | Transit structural metric is scheduled/headway service supply with explicit source-bundle identity; specific feed/operator is deployment choice. |
| OSM parking | INITIAL PRIOR supplementary/community-mapped source | Not authoritative completeness; empty OSM result is not zero. |
| Municipal parking inventory | EXTERNAL VERIFICATION / DEPLOYMENT CHOICE | Preferred authoritative source where available; each city/provider requires explicit adapter/schema/policy. Not a structural single provider. |

Cross-cutting **STRUCTURAL** concepts regardless of provider:

```text
exact content/release identity
versioned parser/mapping/method identity
explicit compatibility with active upstream semantics
no silent fallback/substitution
missing/unknown != zero
semantic identity excludes storage locator noise
source lineage and deterministic replay
```

---

# 12. FINAL HASH / VERSION / TEST RECORD

## sitescore-core

```text
package: sitescore-core
version: 0.1.0
tests: 86/86 PASS
ZIP SHA-256: aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192
commit: 019b40beadb66c533f1de41e99efc7084663956f
tag: v0.1.0
```

## sitescore-data

```text
package: sitescore-data
version: 0.1.0
tests: 361/361 PASS
runtime dependencies: []
ZIP SHA-256: 386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b
commit: f03cbb71bd93c5a3afd78b43991e456595a7f75d
tag: sitescore-data-v0.1.0
```

## sitescore-providers

```text
current package version in pyproject.toml: 0.1.0
current locked tests: 418/418 PASS
runtime dependency: sitescore-data==0.1.0
sitescore-core imports: 0
final repository freeze commit: UNKNOWN / NOT YET FROZEN
final repository freeze tag: UNKNOWN / NOT YET FROZEN
```

### Checkpoint ZIP hashes

```text
3.3-1 Foundation
8dd6c61fb32950acd458b7e738f68d40cf683dcc8c617eda9be4dbf7d604ee50

3.3-2 Geography
f79c3c409997055c87172236b7606a2ccdbb96a50753db4bbac79944bf406bc0

3.3-3 ACS
b68aaebaaf0d87fc87de88e4be2c111592294fb3657fb61d16d9e63cc500626b

3.3-4 Competition
91ba1fcf73674c311ea82366803ec280025ab85598fbb8c6d2c31438eaff0208

3.3-5 Pedestrian
c9f3556af4c05f97ba7ed1545e3540318358d06bab3df43ab1d123f1bb283f4c

3.3-6 Transit
665475158b50aaa3f1cd5a0533e66d5305f9f08edec95bbe2c89d944ad15fcea

3.3-7 Road
5bc6148349a667e61de941e2a48a5f96ada8bd68b4406adf239d8aba5c6713ef

3.3-8 Parking
41e3fa4f7b65beca334d75046c89b179309c963c783dad7576dd72a4490e5c74
```

The final current provider source is represented by the 3.3-8 hardened ZIP above; a repository-wide provider freeze tag has not yet been established.

---

# 13. FINAL PROVIDER REPO FREEZE CHECKLIST

**Do not execute this checklist unless explicitly requested.**

Proposed freeze record filename:

```text
docs/FAZ3_3_PROVIDER_FREEZE_RECORD.md
```

Exact freeze checklist:

1. **Authoritative source selection**
   - Start only from final 3.3-8 hardened source.
   - Verify expected ZIP SHA-256 `41e3fa4f...e5c74`.

2. **Full provider tests**
   - Run complete `sitescore-providers` suite with authoritative `sitescore-data v0.1.0` on `PYTHONPATH`/installed dependency.
   - Expected frozen baseline: `418/418 PASS` before any freeze-only metadata change.

3. **Frozen dependency tests**
   - `sitescore-data`: `361/361 PASS`.
   - `sitescore-core`: `86/86 PASS` independently.

4. **Dependency audit**
   - `pyproject.toml` runtime dependencies exactly `sitescore-data==0.1.0` unless an explicitly approved freeze change says otherwise.
   - No accidental third-party HTTP/GIS/data dependencies.

5. **Import audit**
   - `sitescore-core` / `sitescore` imports in provider production source = `0`.
   - No circular package dependency introduced.

6. **Production tree audit**
   - Confirm only expected foundation + census + acs + overture + pedestrian + transit + road + parking production files.
   - No benchmark/normalization/app/core implementation present.

7. **Locked checkpoint checksum/diff audit**
   - Verify final production sources representing earlier locked checkpoints have not changed unexpectedly.
   - Diff against checkpoint final ZIPs/hashes listed in §12.

8. **Source-level invariant audit**
   - semantic identity excludes locators/storage noise;
   - request fingerprint contains actual request semantics only;
   - raw/parsed/SourceMetadata coherence;
   - mutable release labels rejected;
   - missing/unknown/failure != zero;
   - no silent provider/fallback substitution;
   - deterministic canonical ordering;
   - no provider-specific scoring/calibration logic;
   - no COMB-005 / ECDF / normalization implementation.

9. **Version decision**
   - Explicitly decide whether provider freeze remains package `0.1.0` or requires a version change.
   - Do not infer a new version automatically.

10. **Freeze record**
    - Create `docs/FAZ3_3_PROVIDER_FREEZE_RECORD.md` containing:
      - frozen status;
      - package version;
      - dependency boundary;
      - checkpoint lock state 3.3-1–3.3-8;
      - final test baselines;
      - frozen data/core identities;
      - architecture invariant summary;
      - deferred FAZ 3.4 work;
      - final audit decision.

11. **Final clean ZIP**
    - Exclude caches/pyc/build noise.
    - Produce deterministic project ZIP.
    - Compute and record SHA-256.

12. **Git freeze commit**
    - Commit only the approved provider freeze source/record.
    - Record exact commit SHA.

13. **Git tag**
    - Create explicit provider freeze tag after version decision.
    - Record exact tag name.

14. **Clean working tree**
    - Verify no uncommitted tracked/untracked implementation changes remain.

15. **Final freeze verification**
    - Re-run provider + frozen dependency tests from clean tagged tree.
    - Re-run import/dependency/tree/hash audits.
    - Record the final results in the freeze record.

---

# 14. NEW CHAT BOOTSTRAP CONTEXT

See the separate concise copy-ready file:

```text
docs/FAZ3_4_NEW_CHAT_BOOTSTRAP.md
```

The authoritative concise bootstrap is duplicated below for completeness.

```text
PROJECT: SiteScore AI

PURPOSE
SiteScore is a typed real-data location-analysis system. The frozen scoring/financial core is isolated from provider acquisition. Provider evidence is converted into frozen sitescore-data contracts, then future normalization/readiness/app layers may feed sitescore-core only after SCORE_READY.

FROZEN BASELINES
- sitescore-core v0.1.0: 86/86 PASS; ZIP SHA-256 aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192; commit 019b40beadb66c533f1de41e99efc7084663956f; tag v0.1.0.
- sitescore-data v0.1.0: 361/361 PASS; ZIP SHA-256 386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b; commit f03cbb71bd93c5a3afd78b43991e456595a7f75d; tag sitescore-data-v0.1.0.
- sitescore-providers: checkpoints 3.3-1 through 3.3-8 LOCKED; current final source baseline 418/418 PASS; runtime dependency only sitescore-data==0.1.0; sitescore-core imports=0; CONTRACT_CHANGE_REQUIRED=0. Final provider repository freeze commit/tag has NOT yet been created.

LOCKED PROVIDER CHECKPOINTS
3.3-1 Foundation: canonical hashing/request fingerprints/raw-parsed artifacts/SourceMetadata/persistence/errors.
3.3-2 Geography: Census geocoder + exact benchmark/vintage/layer manifest -> ResolvedLocation.
3.3-3 ACS: exact release/variables, statistical estimate+MOE sidecar, neutral age aggregation -> DemographicSnapshot.
3.3-4 Competition: pinned Overture release/taxonomy mapping/dedup/catchments -> CompetitionSnapshot + measurement_definition_id.
3.3-5 Pedestrian: pinned network/graph/Valhalla walking execution/budgets -> PedestrianCatchmentArtifact + IsochroneSnapshot.
3.3-6 Transit: pinned one-feed GTFS Static + walking-reachable stops -> 168-hour service-supply TransitSnapshot + source_bundle_fingerprint.
3.3-7 Road: pinned vehicle network/graph/auto profile/static-traffic semantics -> RoadAccessSnapshot.
3.3-8 Parking: pinned inventory + eligibility + road/walk compatibility + optional explicit dynamic sidecar -> ParkingSnapshot.

CROSS-CUTTING INVARIANTS
- providers depend only on sitescore-data; never import core.
- provider failure != negative site evidence; missing/unknown/out-of-validity != zero.
- no silent fallback or provider substitution.
- exact release/content/config pinning; latest/current/live are not canonical identities.
- semantic identity excludes storage locators, URLs, paths, endpoints, workers, retries, retrieved_at unless intrinsically semantic.
- source observation timestamps (e.g. parking availability_timestamp) are semantic.
- request fingerprint = actual semantic provider request.
- raw request/provider/content, parsed raw hash/parser identity, active manifest, and SourceMetadata must be coherent.
- canonical serialization/order must make processing order irrelevant.
- provider-specific rich evidence stays in immutable sidecars when frozen sitescore-data can represent downstream output.
- do not modify sitescore-data unless a true contract gap is proven from actual frozen source.

AVAILABLE PROVIDER OUTPUTS
- Geography: ResolvedLocation / GeographyRef.
- ACS: DemographicSnapshot + provider-side MOE/statistical evidence.
- Competition: per-scale count/area/density curve + measurement_definition_id.
- Pedestrian: walking catchment geometry ref + reachable area snapshots.
- Transit: 168-hour scheduled/headway service-supply profile + service_departure_equivalents_per_hour + TransitSourceBundle fingerprint.
- Road: per-scale reachable area/network length/connector count/origin-to-network cost + road origin/profile identity.
- Parking: usable public facility evidence, explicit off-street capacity, legal curb length, optional dynamic occupancy/available-space evidence.

NOT YET ASSEMBLED
No end-to-end DerivedLocationMetrics builder or NormalizedLocationFeatures builder exists. In particular:
- walkable_population and target_population_density require demographic × pedestrian spatial overlay.
- competition_pressure scalar requires calibrated multi-scale reduction.
- road_reachable_area_km2 scalar requires calibrated multi-scale reduction.
- household_income_ratio requires explicit reference semantics.
- road_parking_access_score does not exist yet.

BENCHMARK/NORMALIZATION STRUCTURAL RULES
- benchmark population = commercially evidenced spatial alternatives.
- commercial benchmark frame = equal-area, tri-state eligibility, full-frame-first, equal eligible-cell weighting.
- competition site/benchmark must share measurement_definition_id.
- transit site/benchmark must share TransitSourceBundle fingerprint.
- mid-ECDF = (count(v<x)+0.5*count(v=x))/N; ties share rank; no interpolation.
- exact Overture category mapping is release-specific; semantic commercial ontology is structural.
- road benchmark stays separate from parking.
- parking missing/mapped-empty semantics must preserve coverage; capacity and curb are separate.

READINESS
Exact required normalized features:
1 walkable_population_score
2 target_population_density_score
3 age_target_concentration_score
4 competition_opportunity_score
5 walkable_reach_area_score
6 transit_access_score
7 road_parking_access_score
8 household_income_score
All eight required. AVAILABLE + sufficient quality + ELIGIBLE + CALIBRATED normally required.
Age exception only: value=50, AVAILABLE, ELIGIBLE, UNCALIBRATED, is_proxy=True, reason age_affinity_not_calibrated, fallback age_neutral_fallback/1.0, explicitly approved.
Competition benchmark measurement identity and transit benchmark source-bundle identity must match site values.
road_parking_access_score additionally requires a non-null calibrated/versioned COMB-005 composite policy.
NOT_SCORE_READY means no ReadyCategoryScorePayload, no CategoryScores construction, and sitescore-core analyze() must not be called. PIPELINE_ERROR is separate from readiness failure.

COMB-005
Road and parking evidence are frozen separately. The normalized slot road_parking_access_score exists, but no formula/weights/fallback exists. Forbidden: arbitrary 50/50, road-only fallback, parking-missing neutral 50, hidden weights, renormalization. A calibrated versioned composite policy is required before score-ready.

MAJOR DEFERRED BLOCKERS
- final production source/release configs (ACS/Overture/OSM/Valhalla/GTFS/parking providers).
- equal-area benchmark frame acquisition/builders and selected resolution calibration.
- demographic×walking overlay / actual geospatial area operations.
- competition, transit, pedestrian, road, income normalization artifacts.
- road scalar reduction and road benchmark.
- parking benchmark/municipal adapters and optional dynamic freshness policy.
- COMB-005 calibration.
- age empirical calibration (neutral fallback may be used only under exact frozen policy).
- DerivedLocationMetrics and NormalizedLocationFeatures assembly.
- readiness orchestration, RealDataPipelineResult assembly, sitescore-app category aggregation, core adapter.
- empirical end-to-end validation.

ACCEPTED NON-BLOCKING LIMITATIONS
ACS MOE stays sidecar; no derived cohort MOE. GTFS V1 one-feed only, no stop-time interpolation, static scheduled service only. Pedestrian/road graph runtime identity is trusted deployment attestation; no GIS area engine in providers. Road V1 static graph/no datetime traffic and no driveway/vehicle-entrance refinement. Parking V1 one canonical inventory + optional dynamic sidecar, shared canonical ID linkage only, no fuzzy cross-source matching, no freshness threshold.

NEXT PHASE BOUNDARY
Do not change locked provider checkpoints. Before FAZ 3.4 implementation, first perform the explicitly requested final sitescore-providers repository freeze audit if not already done. FAZ 3.4 should then address benchmark acquisition/frame + derived-metric/normalization/readiness pipeline work only under the frozen contracts/invariants above. Do not call sitescore-core until the data layer produces SCORE_READY and app-layer category aggregation has passed the readiness gate.
```

---

**Handoff extraction decision:** the provider implementation phase is technically complete and checkpoint-locked, but the provider repository itself still requires the explicit final freeze audit/commit/tag procedure in §13 before it is called a repository freeze.
