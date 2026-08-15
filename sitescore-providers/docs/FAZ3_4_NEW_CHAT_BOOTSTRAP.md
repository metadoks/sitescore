# NEW CHAT BOOTSTRAP CONTEXT

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
