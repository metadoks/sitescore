# FAZ 3 FINAL — Integrated Audit / Freeze Candidate

## Status

```text
CURRENT_PHASE: FAZ 3
CURRENT_CHECKPOINT: FAZ 3-FINAL
STATUS: FREEZE_CANDIDATE / READY_FOR_FINAL_REVIEW
AUDITED_BASE_MAIN_SHA: 3519b118c9f5d04a16096003657a0058cef4af42
CONTRACT_CHANGE_REQUIRED: 0
FINAL_BLOCKERS: NONE FOUND BY IMPLEMENTER AUDIT
```

This record does **not** declare FAZ 3 frozen. Only Reviewer acceptance followed by explicit user `LOCK` may create the operational frozen state.

Allowed phase claim remains exactly:

> Mathematically validated scoring engine; empirical validation pending.

## 1. Audit scope

This audit reconciles the actual repository state for the full FAZ 3 real-data architecture:

- FAZ 3.1 — structural real-data/scoring architecture decisions;
- FAZ 3.2 — frozen core/data contract boundary;
- FAZ 3.3 — frozen provider acquisition/provenance layer;
- FAZ 3.4 — frozen spatial, metric, benchmark, normalization, readiness and terminal pipeline layer.

No FAZ 4 application/API/UI/payment/report feature is introduced here. No empirical parameter is invented to force `SCORE_READY`.

## 2. Operational subsection register

### FAZ 3.1

Repository evidence does not provide a standalone canonical `FAZ 3.1 FROZEN` Git record. It is therefore **not independently relabelled as frozen** in this pre-lock audit. Its architectural decisions are, however, materially embodied by the frozen downstream package contracts and guards audited below. The whole-phase FAZ 3 freeze, if Reviewer/user authorized, will freeze those embodied structural decisions as part of the integrated baseline.

Material embodied decisions re-attested:

- metric != score;
- missing evidence != bad != neutral != zero;
- provider evidence is distinct from provider-neutral derived real-unit metrics;
- site and benchmark measurement semantics/lineage must be compatible;
- normalization occurs only after real-unit measurement + benchmark distribution;
- unresolved/incompatible/uncalibrated required evidence blocks readiness;
- `SCORE_READY != SCORED`;
- Location Engine and Financial Engine remain separate in the frozen core;
- benchmark semantics, transit service-supply semantics, road/parking separation, COMB-005 gating and age fallback rules are carried into later frozen implementation.

### FAZ 3.2

Operational evidence: `sitescore-data/docs/FAZ3_2_FREEZE_RECORD.md` records **FAZ 3.2 CONTRACT ARCHITECTURE — FROZEN**, checkpoints 1–7 LOCKED, `sitescore-data==0.1.0`, 361/361 freeze baseline, runtime dependencies `[]`, and no core/provider imports.

The same record identifies frozen core ownership separately. Current core package remains `0.1.0`, runtime dependencies `[]`; current `sitescore-core/docs/V1_BASELINE.md` continues to state strict Location/Financial separation and that empirical business validity is pending.

### FAZ 3.3

Operational evidence: `sitescore-providers/docs/FAZ3_3_PROVIDER_FREEZE_RECORD.md` records **FAZ 3.3 PROVIDER ARCHITECTURE — FROZEN**, checkpoints 3.3-1 through 3.3-8 LOCKED, package `0.1.0`, runtime dependency exactly `sitescore-data==0.1.0`, no core imports, and 418/418 freeze baseline.

Frozen provider families present in current source:

- foundation / request-response identity / hashing / temporal semantics;
- Census geography;
- ACS statistical evidence;
- Overture competition evidence;
- pedestrian/Valhalla execution evidence;
- transit/GTFS service-supply evidence;
- road evidence;
- parking evidence.

### FAZ 3.4

Operational evidence: PR #6 was user-authorized and merged at current base/main `3519b118c9f5d04a16096003657a0058cef4af42`. Coordination state records FAZ 3.4-FINAL LOCKED / FAZ 3.4 FROZEN. The merged final audit document intentionally retains historically correct pre-lock `FREEZE_CANDIDATE` wording.

No post-freeze production mutation was introduced before opening this FAZ 3-FINAL branch.

## 3. Current package set and exact runtime DAG

All current FAZ 3 packages are version `0.1.0`.

```text
sitescore-core
  runtime deps: []

sitescore-data
  runtime deps: []

sitescore-providers
  -> sitescore-data==0.1.0

sitescore-spatial
  -> shapely==2.1.2
  -> pyproj==3.7.2

sitescore-metrics
  -> sitescore-data==0.1.0
  -> sitescore-providers==0.1.0
  -> sitescore-spatial==0.1.0

sitescore-benchmarks
  -> sitescore-spatial==0.1.0
  -> sitescore-metrics==0.1.0

sitescore-pipeline
  -> sitescore-data==0.1.0
  -> sitescore-benchmarks==0.1.0
```

AST/source guard conclusions:

- DAG is acyclic;
- core is isolated;
- data is neutral;
- no upstream package imports pipeline;
- pipeline does not import core;
- providers import only data from SiteScore packages;
- no reverse dependency was introduced.

## 4. Frozen-source history re-attestation

GitHub compare from pre-3.4-4 baseline `91608d7f70e2cdb28ba6aa9c287baea0af9f2275` to audited base `3519b118c9f5d04a16096003657a0058cef4af42` shows no changes under:

```text
sitescore-core/
sitescore-data/
sitescore-providers/
sitescore-spatial/
sitescore-metrics/
```

Later approved changes are limited to downstream `sitescore-benchmarks`, additive `sitescore-pipeline`, and the 3.4 final audit/guard.

Therefore later 3.4 work did not silently mutate the frozen core/data/provider/spatial/metric source baseline.

## 5. FAZ 3.2 core/data contract audit

Current `MetricValue` keeps value state separate from:

- availability;
- data quality;
- score eligibility;
- calibration state;
- estimate/proxy flags;
- source refs;
- method version;
- reason codes.

`None` is not treated as an implicit state; missing numeric values require typed state explanation.

Current `DerivedLocationMetrics` still contains exactly ten V1 real-unit metric slots:

1. `walkable_population`
2. `target_population_density`
3. `household_income`
4. `household_income_ratio`
5. `competition_pressure`
6. `walkable_reach_area_km2`
7. `transit_service_departure_equivalents_per_hour`
8. `road_reachable_area_km2`
9. `parking_public_offstreet_capacity`
10. `parking_legal_curb_length_m`

Current `NormalizedLocationFeatures` still contains exactly eight V1 score slots:

1. `walkable_population_score`
2. `target_population_density_score`
3. `age_target_concentration_score`
4. `competition_opportunity_score`
5. `walkable_reach_area_score`
6. `transit_access_score`
7. `road_parking_access_score`
8. `household_income_score`

Load-bearing frozen contracts remain present:

- `MetricValue`;
- `DerivedLocationMetrics`;
- `NormalizedLocationFeatures`;
- `FeatureReadinessPolicy`;
- `ReadinessCompatibilityInput`;
- `ApprovedFallbackPolicyRef`;
- `ScoringReadinessResult`;
- `RealDataPipelineResult`;
- `PipelineStatus`.

## 6. FAZ 3.3 provider audit

Current provider architecture tests and phase guard re-attest:

- runtime dependency only on frozen `sitescore-data==0.1.0`;
- no provider import of core, benchmarks or pipeline;
- provider layer emits evidence/snapshots rather than normalized/category scores;
- all frozen provider family directories remain present;
- semantic request fingerprint/content/source identity remains represented;
- provider failure/missing/out-of-validity is not numeric site evidence;
- no hidden provider substitution is introduced by later layers.

Frozen provider semantics retained from source/records include:

- request fingerprint represents semantic provider request;
- raw content hash / parsed identity / source metadata remain provenance-bound;
- semantic identity is distinct from storage/download/execution noise;
- Census/ACS evidence is release/vintage/variable bound;
- competition evidence binds pinned release/taxonomy/measurement definition;
- pedestrian and road execution bind graph/network/execution policy identity;
- transit represents 168-hour scheduled/headway service supply and source-bundle identity rather than stop count;
- parking remains evidence with separate capacity/curb semantics;
- provider-side normalization/scoring is absent.

## 7. FAZ 3.4 integrated chain re-attestation

Frozen chain remains:

```text
provider evidence / frozen snapshots
-> spatial artifacts + provider-neutral real-unit measurements
-> complete eligible benchmark attempt population
-> compatibility/calibration-gated numeric observations
-> BenchmarkDistributionArtifact
-> exact mid-ECDF
-> feature-specific normalization
-> exact age fallback + COMB-005 gate
-> NormalizedLocationFeatures
-> derived ScoringReadinessResult
-> RealDataPipelineResult
```

Re-attested invariants:

- numeric benchmark observation requires AVAILABLE + ELIGIBLE + CALIBRATED + finite + compatible lineage;
- mid-ECDF remains `(#below + 0.5 * #equal) / N`;
- no interpolation, epsilon, tolerance, rounding or quantization;
- higher-better direct features use `100 * P`;
- competition opportunity uses `100 * (1-P)`;
- competition site/benchmark compatibility binds measurement definition;
- transit compatibility binds exact source bundle;
- road and parking remain separate before COMB-005;
- current COMB-005 production policy remains NOT_APPROVED, approved registry empty, weights empty, composition method unresolved, output nonnumeric;
- age fallback remains the unique explicit numeric uncalibrated exception: exact score 50, proxy, `age_affinity_not_calibrated`, policy `age_neutral_fallback/1.0`;
- pipeline assembly/readiness authority remains factory-owned;
- terminal overlapping real-unit metrics remain coherent with the actual normalization site measurements;
- readiness false -> `NOT_SCORE_READY`;
- explicit execution-stage failure -> `PIPELINE_ERROR`;
- `SCORE_READY` grants permission to later scoring but is not itself a score.

## 8. Cross-package lineage / authority audit

The phase-wide audit found no new public bypass requiring frozen-contract mutation.

Authority remains represented through actual evidence/artifact objects and semantic identities across boundaries, including as applicable:

- request fingerprint;
- content hash;
- source/manifest/source-bundle identity;
- method/policy/version identity;
- spatial precision/CRS operation policy identity;
- benchmark frame/distribution identity;
- site↔benchmark compatibility;
- normalization policy identity;
- age fallback authority;
- COMB-005 policy/gating;
- pipeline factory-owned assembly/readiness authority;
- terminal real-unit metric coherence.

Detached IDs are not treated as sufficient authority where hardened downstream contracts require nested/coherent objects.

## 9. Global missingness / no-hidden-default audit

No production shortcut was found that silently converts:

```text
missing -> zero
missing -> neutral
uncalibrated -> calibrated
incompatible -> compatible
unknown -> negative evidence
```

Phase guard searches production source for forbidden hidden-default patterns, including missing-to-zero fills, missing-input renormalization, default road/parking weights, implicit 50/50 road-parking composition, default equal-area CRS/cell resolution, and invented minimum-N/coverage authority.

No general neutral `50` is authorized. The exact age fallback is the sole frozen exception.

## 10. Structural freeze vs empirical/calibration gate register

### A. Structurally frozen / implemented

- typed availability/quality/eligibility/calibration axes;
- provider evidence/provenance foundation;
- frozen provider family contracts;
- deterministic spatial precision/CRS operation framework;
- full-cell equal-area benchmark model contract;
- commercial eligibility state model;
- provider-neutral real-unit metric layer;
- benchmark measurement/distribution artifacts;
- exact mid-ECDF;
- feature-specific normalization direction/compatibility;
- unique age fallback policy;
- COMB-005 approval gate with no approved production policy;
- eight normalized V1 slots;
- scoring readiness boundary;
- terminal real-data pipeline result and lineage authority;
- exact package DAG/boundaries.

### B. Empirically unresolved / calibration-gated

No value is invented for any item below:

1. production equal-area CRS selection/attestation;
2. benchmark-cell resolution;
3. lattice anchor/origin;
4. boundary-membership calibration/policy;
5. commercial ontology/category mapping;
6. commercial evidence-to-cell applicability;
7. provider precedence / cross-provider reconciliation;
8. population allocation/intersection policy;
9. target-population definition;
10. age-affinity empirical calibration;
11. household-income-ratio denominator/reference;
12. competition multi-scale scalar reduction;
13. road multi-scale scalar reduction;
14. approved COMB-005 component normalization authorities;
15. approved COMB-005 formula/weights;
16. benchmark sample-adequacy/minimum-N policy if later required;
17. benchmark coverage threshold policy if later required;
18. production provider/release/source configuration choices where deployment-specific;
19. production calibration datasets / acceptance evidence;
20. empirical validation across target archetypes/geographies.

These unresolved items remain explicit gates, not zero/default/neutral substitutes.

## 11. FAZ 4 / product-layer leakage audit

No new FAZ 4 executable layer is introduced by this phase-final work. Real-data packages do not add:

- web application/API framework;
- user/account/auth flow;
- payment orchestration;
- report/PDF generation;
- UI/frontend;
- product-delivery job orchestration;
- real-data category aggregation;
- Location Score orchestration;
- Decision Layer execution from the real-data pipeline;
- `sitescore-core analyze()` invocation from pipeline.

The frozen core itself legitimately contains its pre-existing deterministic scoring/financial engine. Historical DTO definitions in data/core are not treated as FAZ 4 leakage.

## 12. Regression / reproducibility evidence

A temporary branch-only GitHub Actions workflow runs the complete current package set:

```text
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

The phase-final architecture guard additionally verifies exact runtime DAG/version pins, source import direction, frozen V1 data surfaces, provider evidence-only boundary, no hidden defaults, exact age/COMB authority, no FAZ 4 dependencies, and presence of subsection freeze/final guards.

Final documentation-inclusive run and exact visible counts will be recorded before review. The temporary workflow will then be removed and validated SHA -> final review HEAD will be proven workflow-removal-only.

## 13. Contract-change decision

No reproducible correctness blocker requiring mutation of a previously frozen contract was found.

```text
CONTRACT_CHANGE_REQUIRED: 0
FINAL_BLOCKERS: NONE
FINAL_AUDIT_DECISION: FREEZE_CANDIDATE
```

This remains a pre-lock decision. Do not interpret this document as `FAZ 3: FROZEN` until Reviewer acceptance and explicit user LOCK are completed and verified.
