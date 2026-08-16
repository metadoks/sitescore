# SiteScore AI — FAZ 3.4-FINAL Integrated Architecture Audit + Freeze Readiness

## Control status

```text
PHASE: FAZ 3.4
CHECKPOINT: 3.4-FINAL
AUDIT_BASE_SHA: 8919edb9a2791047ff10f7d08bd3fc5ed251a6e0
AUDIT_BRANCH: faz3.4/final-audit-freeze
STATUS: READY_FOR_FINAL_REVIEW
FINAL_AUDIT_DECISION: FREEZE_CANDIDATE
FINAL_BLOCKERS: NONE
CONTRACT_CHANGE_REQUIRED: 0
LOCK_AUTHORITY: USER_ONLY
```

This document is a **pre-lock freeze-readiness record**. It does not declare FAZ 3.4 FROZEN, does not authorize merge, and does not advance to FAZ 3-FINAL or FAZ 4.

Phase claim:

> Mathematically validated scoring engine; empirical validation pending.

## 1. Audit scope and method

The final audit re-evaluates the integrated FAZ 3.4 chain rather than relying only on checkpoint-local acceptance records. The audited surface is the exact `main` baseline `8919edb9a2791047ff10f7d08bd3fc5ed251a6e0`, which includes all user-authorized locks through Checkpoint 3.4-8.

Audit methods used:

- direct inspection of all seven package `pyproject.toml` runtime dependency declarations;
- AST-based final guard over SiteScore package import direction;
- GitHub history comparisons from earlier locked merge baselines to the 3.4-8 merged main;
- source inspection of load-bearing spatial, metric, benchmark population/distribution, ECDF, normalization, COMB-005, readiness, and pipeline contracts;
- adversarial architecture guards for no reverse dependency, no core leakage, no product/category scoring leakage, no hidden empirical threshold/weight shortcut, exact age fallback, and unapproved COMB-005 state;
- full seven-package regression execution.

No production source change was required by this final audit.

## 2. Checkpoint lock register

Operational source of truth is the merged GitHub state plus Reviewer/Implementer handoff protocol. Historical checkpoint documents may preserve their pre-lock wording and are not retroactively rewritten merely to say `LOCKED`.

| Checkpoint | Current operational state | Relevant merged baseline / note |
|---|---|---|
| 3.4-0 | LOCKED | Phase foundation baseline |
| 3.4-1 | LOCKED | Spatial foundation |
| 3.4-2 | LOCKED | Commercial equal-area frame foundation |
| 3.4-3 | LOCKED | Shared derived-metrics foundation |
| 3.4-4 | LOCKED | merge/main `989b719d84a4fa01d40c0a2d342cdeff9197c3e7` |
| 3.4-5 | LOCKED | merge/main `530869a06fd5e1a64357701fff3f226d70ac6d1d` |
| 3.4-6 | LOCKED | merge/main `8bfe2eb92ea3d52f30d14a4333927f76f8630b0a` |
| 3.4-7 | LOCKED | merge/main `c8514401f1b9e2a671c00477219f6f930a594bc8` |
| 3.4-8 | LOCKED | merge/main `8919edb9a2791047ff10f7d08bd3fc5ed251a6e0` |

Historical-status note: some checkpoint-local markdown records still say `READY FOR REVIEW` or `not LOCKED` because those files were written before the later user-authorized lock transition. This is documentary history, not the current operational state.

## 3. Exact runtime dependency DAG

Current package metadata and source-import audit agree on the following DAG:

```text
sitescore-core
  -> no SiteScore runtime dependency

sitescore-data
  -> no SiteScore runtime dependency

sitescore-providers
  -> sitescore-data==0.1.0

sitescore-spatial
  -> shapely==2.1.2
  -> pyproj==3.7.2
  -> no SiteScore domain package

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

Final assertions:

- DAG is acyclic.
- `sitescore-core` remains isolated.
- `sitescore-data` remains neutral at the bottom of data contracts.
- `sitescore-spatial` has no SiteScore-domain dependency.
- no upstream package imports `sitescore-pipeline`.
- `sitescore-pipeline` does not depend on/import `sitescore-core`.
- no reverse dependency from data/providers/spatial/metrics/benchmarks into pipeline exists.

## 4. Frozen-source boundary / history audit

GitHub history comparisons were used to detect silent mutation after earlier locks.

### 4.1 Pre-3.4-4 baseline → 3.4-8 merged main

Comparison from `91608d7f70e2cdb28ba6aa9c287baea0af9f2275` to `8919edb9a2791047ff10f7d08bd3fc5ed251a6e0` shows later changes only in approved `sitescore-benchmarks` stages and the additive `sitescore-pipeline` package. No `sitescore-core`, `sitescore-data`, `sitescore-providers`, `sitescore-spatial`, or `sitescore-metrics` file changed across that interval.

### 4.2 3.4-4 lock → current baseline

Comparison from `989b719d84a4fa01d40c0a2d342cdeff9197c3e7` shows no later modification of the locked 3.4-4 measurement/distribution source (`measurement.py`, `population.py`, `distribution.py`).

### 4.3 3.4-5 lock → current baseline

Comparison from `530869a06fd5e1a64357701fff3f226d70ac6d1d` shows no later modification of locked `ecdf.py`.

### 4.4 3.4-6 lock → current baseline

Comparison from `8bfe2eb92ea3d52f30d14a4333927f76f8630b0a` shows no later modification of locked `normalization.py`; later benchmark work is the approved COMB-005 addition plus integration package work.

### 4.5 3.4-7 lock → 3.4-8 merged main

Comparison from `c8514401f1b9e2a671c00477219f6f930a594bc8` to `8919edb9a2791047ff10f7d08bd3fc5ed251a6e0` contains exactly the additive `sitescore-pipeline` package surface; benchmark source remained unchanged.

Audit conclusion: no silent frozen-source mutation was found.

## 5. End-to-end semantic chain

The integrated architectural chain is structurally coherent:

```text
provider evidence / frozen snapshots
→ spatial artifacts and provider-neutral real-unit measurements
→ commercial frame + complete eligible-cell attempt population
→ calibration/compatibility-gated numeric benchmark observations
→ BenchmarkDistributionArtifact
→ exact mid-ECDF percentile
→ feature-specific normalization
→ exact age fallback + COMB-005 gate
→ NormalizedLocationFeatures
→ ScoringReadinessResult
→ RealDataPipelineResult
```

The chain stops before category aggregation and Location Score computation.

### Boundary invariant

`metric != score` remains intact. Provider/metric layers emit real-unit evidence and measurements; percentile/0–100 transformation is owned by the benchmark normalization layer.

## 6. Missingness and readiness invariant

The full chain preserves:

```text
missing evidence != zero
unresolved policy != zero
uncalibrated != neutral
incompatible != bad score
NOT_SCORE_READY != PIPELINE_ERROR
```

Required direct feature normalization accepts a numeric site metric only when the authoritative metric is AVAILABLE, ELIGIBLE, CALIBRATED, and finite. Benchmark numeric observation inclusion uses the same structural conditions and additionally requires compatible measurement lineage.

The single frozen numeric-uncalibrated exception is exact age fallback authority:

```text
policy_id = age_neutral_fallback
policy_version = 1.0
feature = age_target_concentration_score
score = 50.0
availability = available
score_eligibility = eligible
calibration_state = uncalibrated
is_proxy = true
reason = age_affinity_not_calibrated
```

No generic missing/uncalibrated feature receives 0 or 50.

## 7. Spatial / precision audit

Locked spatial semantics remain consistent:

- Shapely `2.1.2`, pyproj `3.7.2`;
- PROJ network disabled for canonical transforms;
- ballpark transforms forbidden;
- `always_xy=True` explicit;
- best-available transformation required;
- CRS semantic identity is structured/content-bound, not a free-form label;
- Polygon/MultiPolygon only, strict 2D, finite coordinates, invalid/empty boundary rejection, no repair;
- `GeometryPrecisionPolicy = FULL_DOUBLE / 1.0`, no grid quantization;
- operation policy binds the actual precision-policy object;
- INTERSECT/PROJECT/AREA precision lineage is checked against actual canonicalization/execution inputs;
- geographic degree-area shortcut is rejected;
- projected metre CRS does not itself constitute equal-area attestation;
- no default production equal-area CRS is invented.

No spatial blocker was found.

## 8. Commercial frame audit

Locked frame semantics remain structural rather than empirically fabricated:

- canonical observation geometry is the full equal-area lattice cell;
- boundary clipping is diagnostic only;
- commercial population semantics are `commercially_evidenced_spatial_alternatives`;
- commercial eligibility is tri-state;
- lack of positive evidence is not exclusion evidence;
- equal-area selection/attestation, cell resolution, anchor, boundary-membership method, provider precedence/reconciliation and category calibration remain explicitly unresolved;
- public production construction cannot self-assert resolved equal-area or resolved commercial classification/applicability authority.

No production CRS/resolution/overlap threshold was introduced by later checkpoints.

## 9. Shared metric foundation audit

The canonical V1 metric registry remains ten metrics.

### Structural-unresolved / calibration-gated

- `walkable_population` — allocation/intersection policy unresolved;
- `target_population_density` — target-population definition unresolved;
- `household_income_ratio` — denominator/reference unresolved;
- `competition_pressure` — multi-scale scalar reduction unresolved;
- `road_reachable_area_km2` — multi-scale scalar reduction unresolved.

Canonical unresolved state remains nonnumeric:

```text
value = None
availability = UNKNOWN
data_quality = MISSING
score_eligibility = INELIGIBLE
calibration_state = UNCALIBRATED
is_estimate = False
is_proxy = False
```

### Provider-derived pass-through

- `household_income`;
- `walkable_reach_area_km2`;
- `transit_service_departure_equivalents_per_hour`;
- `parking_public_offstreet_capacity`;
- `parking_legal_curb_length_m`.

Pass-through outputs are constructor-bound to the actual frozen snapshot field rather than detached caller numeric values. Transit source-bundle, competition measurement-definition, and road routing-profile compatibility lineage remain explicit.

No unresolved metric was silently promoted to a production numeric metric.

## 10. Benchmark population / distribution audit

`BenchmarkMeasurementSet` still requires exactly one attempt per eligible frame cell. Missing, duplicate, foreign, and extra attempts are rejected. Attempt order is non-semantic only after completeness/uniqueness validation.

Numeric inclusion still requires:

```text
value != None
availability == AVAILABLE
score_eligibility == ELIGIBLE
calibration_state == CALIBRATED
finite(value)
```

Attempts excluded from numeric observation remain present in coverage. Compatibility conflicts yield `INCOMPATIBLE_MEASUREMENT_LINEAGE`; empty eligible populations and zero-numeric populations are explicit states. No minimum-N or coverage threshold is used to fabricate availability or rank.

## 11. Mid-ECDF audit

Locked V1 mathematics remain exactly:

```text
P(d) = (# observations < d + 0.5 * # observations == d) / N
```

Implementation properties verified:

- exact finite int/float comparison;
- bool rejected;
- float identity/order uses exact integer-ratio semantics;
- `1 == 1.0`, `-0.0 == 0.0` under canonical numeric representation;
- no epsilon/tolerance;
- no rounding/quantization;
- no interpolation;
- step-function behavior;
- input order non-semantic;
- multiplicity semantic;
- empty sample returns explicit `EMPTY_SAMPLE` with percentile `None`.

No later checkpoint altered `ecdf.py` after its lock.

## 12. Feature-specific normalization audit

Locked direct V1 mappings remain:

| Real-unit metric | Normalized feature | Direction |
|---|---|---|
| `walkable_population` | `walkable_population_score` | `100 * P` |
| `target_population_density` | `target_population_density_score` | `100 * P` |
| `competition_pressure` | `competition_opportunity_score` | `100 * (1-P)` |
| `walkable_reach_area_km2` | `walkable_reach_area_score` | `100 * P` |
| `transit_service_departure_equivalents_per_hour` | `transit_access_score` | `100 * P` |
| `household_income` | `household_income_score` | `100 * P` |

Policy construction enforces the exact metric→feature mapping and direction. Site/benchmark compatibility binds definition, derivation policy, precision, unit, method version, and metric-specific source/bundle lineage. Caller-selected direction or detached compatibility does not authorize production normalization.

No direct road/parking normalization policy exists.

## 13. COMB-005 audit

Current canonical production truth remains intentionally unavailable:

```text
COMB005_V1_POLICY.approval_state = NOT_APPROVED
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 = ()
weights = ()
composition_method = UNRESOLVED
missing_side_behavior = REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION
road_parking_access_score = None
```

Production constructors reject caller-created APPROVED policies, AVAILABLE component assertions, detached component scores, and executable weight vectors. There is no 50/50, road-only, parking-only, neutral fill, or missing-side renormalization.

COMB-005 is calibration-gated, not implemented empirically.

## 14. Readiness / pipeline authority audit

Production integration retains the 3.4-8 hardening:

- `NormalizedFeatureAssembly` direct construction disabled;
- `ReadinessEvaluation` direct construction disabled;
- canonical assembly/readiness authority stored in closure-owned registries;
- readiness accepts only the exact factory-produced assembly object;
- terminal result accepts only the exact factory-produced readiness object;
- readiness fingerprint is derived from semantic assembly content and validator semantics, not accepted as detached production authority;
- exactly six actual `FeatureNormalizationResult` objects are retained in canonical assembly;
- exact locked age fallback and actual COMB-005 result are required;
- benchmark bindings must match the actual normalization result/distribution/frame lineage;
- overlapping `DerivedLocationMetrics` terminal fields must exactly equal the actual site measurements used for normalization across value, unit, availability, quality, eligibility, calibration, estimate/proxy, source refs, method version, and reasons;
- readiness false derives `NOT_SCORE_READY`;
- explicit execution-stage failure derives `PIPELINE_ERROR`;
- `SCORE_READY` means scoring permission only and is not a scored Location Score.

No production self-assertion path found in final audit scope.

## 15. No category / core / product leakage

Final AST/source guards verify the real-data layers do not implement or invoke:

- CategoryScores;
- category weighting;
- base/final Location Score;
- dealbreaker penalty application;
- Decision Layer;
- `core.analyze()`;
- report/PDF generation;
- payment workflow.

Location Engine and Financial Engine separation remains outside this real-data layer and has not been collapsed by FAZ 3.4 integration.

## 16. Empirical / calibration gate register

The following remain deliberately unresolved, calibration-gated, or future-authority decisions. Their unresolved status is a correct architectural state, not a final-audit blocker:

1. approved equal-area CRS attestation/selection mechanism;
2. selected production equal-area CRS;
3. production benchmark-cell resolution;
4. production lattice anchor/origin;
5. boundary-membership method and any overlap/touch threshold;
6. commercial evidence classification ontology/category mapping;
7. exact evidence-to-cell applicability rule;
8. provider precedence and cross-provider reconciliation/deduplication;
9. population allocation/intersection policy for `walkable_population`;
10. target-population definition for `target_population_density`;
11. age-affinity empirical calibration replacing the V1 neutral fallback;
12. household-income-ratio denominator/reference policy;
13. competition multi-scale scalar reduction;
14. road multi-scale scalar reduction;
15. approved COMB-005 component normalization authorities;
16. approved COMB-005 formula/weights;
17. empirical benchmark sample-adequacy / minimum-N policy, if later required;
18. empirical benchmark coverage threshold policy, if later required;
19. production calibration datasets and calibration acceptance evidence;
20. production empirical validation across target business archetypes/geographies.

No value for any of these was invented during final audit.

## 17. Final architecture guard added by 3.4-FINAL

The final audit adds one test-only integrated guard under `sitescore-pipeline/tests/test_final_phase_architecture.py`. It does not change runtime behavior. It verifies:

- exact runtime dependency declarations for all seven packages;
- AST import direction and no reverse pipeline dependency;
- core isolation;
- no later scoring/product-layer leakage;
- no hidden empirical minimum-N/coverage/road-parking default-weight/neutralization shortcut in benchmarks or pipeline;
- canonical COMB-005 remains unapproved and weightless;
- exact locked age fallback remains the sole explicitly frozen numeric-uncalibrated exception represented by FAZ 3.4.

## 18. Regression evidence

Pre-document final-guard validation:

```text
workflow: cp34-final-validation
run: 31924843517
validated SHA: 3206695736ba4a205a8edd432adc01130cc8f71d
conclusion: SUCCESS

sitescore-pipeline:   33/33 PASS
sitescore-benchmarks: 191/191 PASS
sitescore-metrics:     67/67 PASS
sitescore-spatial:     PASS
sitescore-providers:   PASS
sitescore-data:        PASS
sitescore-core:        PASS
```

Only exact counts visibly present in the collected workflow log are asserted for pipeline, benchmarks, and metrics. The other four package steps completed successfully without relying on an unsupported reconstructed cardinality.

After this audit document is committed, the same seven-package workflow must be rerun on the documentation-inclusive HEAD. That final run is intentionally recorded in the PR/Implementer handoff rather than edited back into this file, because editing a validation SHA into the file would itself create a new unvalidated SHA.

## 19. Reproducibility / freeze-prep rule

Before Reviewer handoff:

1. run all seven package suites on the documentation-inclusive branch HEAD;
2. require SUCCESS;
3. remove the temporary final-validation workflow;
4. prove validated SHA → review HEAD differs only by temporary workflow removal;
5. prove audited base → review HEAD contains only this final audit document plus the final integrated test guard;
6. open one PR against `main`;
7. do not merge and do not declare FROZEN.

## 20. Final audit decision

No reproducible correctness blocker requiring production source changes or mutation of a frozen earlier contract was found.

```text
FINAL_AUDIT_DECISION: FREEZE_CANDIDATE
STATUS: READY_FOR_FINAL_REVIEW
FINAL_BLOCKERS: NONE
CONTRACT_CHANGE_REQUIRED: 0
```

This remains a pre-lock decision. FAZ 3.4 becomes frozen only after Reviewer SHA-specific acceptance followed by explicit user-authorized LOCK transition.