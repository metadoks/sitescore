# SiteScore AI — Implementer → Reviewer Handoff

HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-6
IMPLEMENTER_STATE: READY_FOR_REVIEW

CHECKPOINT: FAZ 3.4-6
CHECKPOINT_TITLE: Feature-Specific Normalization + Compatibility
BASE_SHA: 530869a06fd5e1a64357701fff3f226d70ac6d1d
CODE_BRANCH: faz3.4/cp3.4-6-feature-normalization-compatibility
CODE_HEAD_SHA: 7b8e4594ba3e58b31ae5163960220832e28b4970
PR: #3
CONTRACT_CHANGE_REQUIRED: 0

---

## 1. Executive implementation summary

Implemented only FAZ 3.4-6: the additive feature-specific normalization and SITE↔benchmark compatibility layer after locked checkpoints 3.4-4 and 3.4-5.

Canonical domain chain now supported for individual direct features:

```text
actual SITE DerivedMetricMeasurement
+ actual BenchmarkDistributionArtifact
+ derived exact measurement compatibility
+ locked MID_ECDF_V1 evaluation
+ canonical feature-normalization policy
→ individual FeatureNormalizationResult
```

The checkpoint defines ordinary `100 * P` direction and competition opportunity `100 * (1 - P)` direction, without making unresolved upstream metrics numeric. It also defines the unique frozen age neutral fallback contract.

No whole `NormalizedLocationFeatures`, COMB-005, readiness, CategoryScores, Location Score, pipeline orchestration or `core.analyze()` was implemented.

## 2. Git state

```text
repository: metadoks/sitescore
base branch: main
base SHA: 530869a06fd5e1a64357701fff3f226d70ac6d1d
code branch: faz3.4/cp3.4-6-feature-normalization-compatibility
code HEAD: 7b8e4594ba3e58b31ae5163960220832e28b4970
PR: #3
PR base: main
PR head: faz3.4/cp3.4-6-feature-normalization-compatibility
PR state at creation: OPEN
```

The branch was created from the exact Reviewer-specified main SHA. No duplicate 3.4-6 branch existed at creation time.

## 3. Changed files

Final base-to-HEAD diff contains exactly seven files, all under `sitescore-benchmarks`:

```text
sitescore-benchmarks/README.md
sitescore-benchmarks/docs/CHECKPOINT_3_4_6_FEATURE_NORMALIZATION_COMPATIBILITY.md
sitescore-benchmarks/src/sitescore_benchmarks/__init__.py
sitescore-benchmarks/src/sitescore_benchmarks/normalization.py
sitescore-benchmarks/tests/test_architecture.py
sitescore-benchmarks/tests/test_feature_normalization.py
sitescore-benchmarks/tests/test_feature_normalization_lineage.py
```

No final `.github` validation workflow remains.

No `pyproject.toml`, requirements lockfile, upstream package source, or dependency declaration changed.

## 4. Public contracts added or changed

Added and exported from `sitescore_benchmarks`:

```text
FeatureNormalizationDirection
FeatureNormalizationState
SiteBenchmarkCompatibilityState
FeatureNormalizationPolicy
FEATURE_NORMALIZATION_POLICIES_V1
feature_normalization_policy
SiteBenchmarkCompatibility
FeatureNormalizationResult
normalize_feature
AgeTargetConcentrationFallbackPolicy
AGE_TARGET_CONCENTRATION_FALLBACK_V1
AgeTargetConcentrationFallback
build_age_target_concentration_fallback
```

Existing locked 3.4-4 and 3.4-5 public contracts were not modified.

## 5. Canonical feature registry / directions

The direct V1 registry contains exactly six metric→feature mappings:

```text
walkable_population
  -> walkable_population_score
  -> HIGHER_PERCENTILE_IS_BETTER

target_population_density
  -> target_population_density_score
  -> HIGHER_PERCENTILE_IS_BETTER

competition_pressure
  -> competition_opportunity_score
  -> LOWER_PERCENTILE_IS_BETTER

walkable_reach_area_km2
  -> walkable_reach_area_score
  -> HIGHER_PERCENTILE_IS_BETTER

transit_service_departure_equivalents_per_hour
  -> transit_access_score
  -> HIGHER_PERCENTILE_IS_BETTER

household_income
  -> household_income_score
  -> HIGHER_PERCENTILE_IS_BETTER
```

Transform semantics:

```text
ordinary direct feature: 100 * P
competition opportunity: 100 * (1 - P)
```

Direction is frozen in the canonical registry. The public domain normalizer has no `invert`, direction, percentile or score argument.

A noncanonical policy object with reversed direction is rejected.

## 6. SITE measurement eligibility / missingness

The canonical domain query authority is the actual nested value:

```text
site_measurement.metric_value.value
```

The subject must be actual `SubjectKind.SITE`.

A direct feature can normalize only when the SITE value is:

```text
not None
availability == AVAILABLE
score_eligibility == ELIGIBLE
calibration_state == CALIBRATED
finite numeric
```

Otherwise the result remains nonnumeric with explicit state/reason. No missing→0, unavailable→0, unknown→50, or uncalibrated→50 substitution exists for direct features.

Implemented states:

```text
AVAILABLE
SITE_METRIC_NOT_AVAILABLE
SITE_METRIC_NOT_ELIGIBLE
SITE_METRIC_NOT_CALIBRATED
BENCHMARK_NOT_AVAILABLE
INCOMPATIBLE
```

Only `AVAILABLE` yields a locked ECDF evaluation, percentile and 0–100 score.

## 7. Benchmark authority

The benchmark authority is an actual `BenchmarkDistributionArtifact`.

Numeric normalization requires benchmark distribution state:

```text
AVAILABLE
```

These remain blocked:

```text
EMPTY_ELIGIBLE_POPULATION
NO_NUMERIC_OBSERVATIONS
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

No excluded measurement attempt is reconstructed into a numeric observation.

3.4-6 delegates percentile computation to the locked 3.4-5 function:

```text
evaluate_benchmark_mid_ecdf(distribution, query, policy=MID_ECDF_V1)
```

No second percentile/ECDF implementation exists.

## 8. SITE ↔ benchmark compatibility semantics

Compatibility is derived from actual objects through the existing `BenchmarkMetricCompatibility` semantics.

Exact compared dimensions:

```text
MetricDefinition.identity_id
MetricDerivationPolicy.identity_id
MeasurementPrecisionPolicy.identity_id
unit
actual DerivedMetricMeasurement.method_version
source_bundle_compatibility
```

Implemented reason codes include:

```text
metric_definition_mismatch
metric_derivation_policy_mismatch
measurement_precision_mismatch
unit_mismatch
method_version_mismatch
source_bundle_compatibility_mismatch
transit_source_bundle_mismatch
competition_measurement_definition_mismatch
benchmark_compatibility_unavailable
```

Per-observation/source `source_refs` are lineage provenance and are deliberately not required to be identical between SITE and benchmark populations.

Callers cannot supply a `compatible=True`, compatibility ID, percentile or score to canonical `normalize_feature`.

## 9. Transit compatibility

Transit source coherence remains exact:

```text
site transit_source_bundle_fingerprint
== benchmark transit_source_bundle_fingerprint
```

Regression tests cover both exact same-bundle success and different-bundle rejection.

A cross-bundle SITE measurement never receives a transit normalized score.

## 10. Competition compatibility and unresolved production state

The feature policy structurally defines:

```text
competition_pressure
-> competition_opportunity_score
-> 100 * (1 - P)
```

Compatibility preserves exact:

```text
competition_measurement_definition_id
```

Additional actual-object tests verify:

```text
same competition_measurement_definition_id -> compatibility can be COMPATIBLE
mismatched definition id -> explicit competition_measurement_definition_mismatch
```

The canonical competition metric remains unresolved and nonnumeric (`value=None`) because the scalar reduction policy is not approved. The checkpoint does not fabricate competition pressure to demonstrate inversion.

Therefore the inversion policy is frozen structurally while the production competition measurement remains unavailable for numeric normalization.

## 11. Age fallback — unique frozen exception

Dedicated contract only:

```text
feature: age_target_concentration_score
score: 50
unit: score_0_100
availability: available
score eligibility: eligible
calibration: uncalibrated
is_proxy: true
reason: age_affinity_not_calibrated
method/fallback semantic: age_neutral_fallback/1.0
```

The builder accepts no feature argument. The policy constructor rejects retargeting the age fallback to another normalized feature.

Regression explicitly verifies that a missing non-age feature receives no age reason and no neutral score.

## 12. Road / parking / COMB-005 boundary

No direct V1 feature-normalization policy exists for:

```text
road_reachable_area_km2
parking_public_offstreet_capacity
parking_legal_curb_length_m
```

Therefore this checkpoint cannot emit final `road_parking_access_score` through road-only or parking-only paths.

Forbidden/not implemented:

```text
road-only substitution
parking-only substitution
50/50 road+parking
missing-side neutral 50
renormalize onto available side
road_weight
parking_weight
```

COMB-005 remains checkpoint 3.4-7 scope.

## 13. Identity / lineage design

`FeatureNormalizationPolicy.identity_id` binds:

```text
policy id/version
canonical MetricDefinition identity
canonical MetricDerivationPolicy identity
normalized feature key
feature direction
MID_ECDF_V1 identity
ECDF numeric comparison policy identity
compatibility rule version
```

`SiteBenchmarkCompatibility.identity_id` binds:

```text
actual site measurement_id
actual benchmark distribution_id
site compatibility identity
benchmark compatibility identity
derived state
reason codes
```

`FeatureNormalizationResult.identity_id` binds:

```text
actual site measurement_id
actual benchmark distribution_id
site compatibility identity
benchmark compatibility identity
compatibility decision identity
canonical normalization policy identity
locked ECDF evaluation identity
normalized feature key
state/reasons
percentile
score
```

No detached caller ID, caller-supplied score, percentile, inversion flag or compatibility assertion is authoritative.

Regression confirms result identity changes when actual SITE measurement semantics or actual benchmark distribution identity changes, and remains deterministic for identical semantic inputs.

## 14. Dependency changes / DAG audit

Dependency metadata changes:

```text
none
```

Existing direct runtime dependencies remain:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

New third-party runtime dependency:

```text
none
```

Architecture guards continue to enforce no direct `sitescore-core`, `sitescore-data`, `sitescore-providers`, or pipeline/application imports from the benchmark source package.

No metrics→benchmarks reverse dependency was introduced. No new cycle was observed.

## 15. Tests / validation

### Initial validation defect

The first full run at:

```text
SHA: f67ade129283283ee7ccf7dc61a2e8960e3ce6f3
run: 31904924819
```

reported:

```text
160 passed, 6 failed
```

All six failures were the same integration-call defect:

```text
TypeError: evaluate_benchmark_mid_ecdf() takes 2 positional arguments but 3 were given
```

The locked 3.4-5 `policy` parameter is keyword-only. The call was corrected to:

```text
evaluate_benchmark_mid_ecdf(..., policy=self.policy.ecdf_policy)
```

No locked ECDF semantics were changed.

### Successful source/test validation

Run:

```text
run id: 31905049465
validated SHA: 0cd01caaa70d8c434bcdf58b5221bf898c399694
conclusion: SUCCESS
```

### Final documentation-inclusive validation

Run:

```text
run id: 31905150049
validated SHA: d0fe64d5bf34bdbb4fb1acce53535b211e0cc0c3
conclusion: SUCCESS
```

Visible exact test summaries:

```text
sitescore-benchmarks: 169/169 PASS
sitescore-metrics:      67/67 PASS
```

The same GitHub Actions job executed and successfully completed all four additional unchanged frozen-package steps:

```text
sitescore-spatial:   PASS
sitescore-providers: PASS
sitescore-data:      PASS
sitescore-core:      PASS
```

Those four package source/test trees were not modified by 3.4-6; their existing locked suite cardinalities remain the project baselines (180, 418, 361, 86 respectively). The handoff distinguishes these established cardinalities from the exact summary lines visibly emitted for benchmarks/metrics in the captured run log.

The final review HEAD is:

```text
7b8e4594ba3e58b31ae5163960220832e28b4970
```

GitHub compare verifies the only delta from documentation-inclusive validated SHA `d0fe64d5...` to final review HEAD is deletion of:

```text
.github/workflows/cp346-validation.yml
```

Source, tests and documentation are unchanged between validated commit and review HEAD.

## 16. Adversarial regressions

Coverage includes:

```text
NORM-001 real SITE + benchmark ordinary normalization P=.75 -> 75
NORM-002 competition inversion transform P=.75 -> 25
NORM-003 endpoint transforms
COMP-001 exact compatible SITE/benchmark success
COMP-002 wrong metric
COMP-003 method-version mismatch
COMP-004 measurement-precision mismatch
COMP-005 transit bundle mismatch
COMP-006 transit same-bundle success
COMP-007 unavailable benchmark
COMP-008 unavailable/missing SITE
COMP-009 uncalibrated numeric SITE
COMP-010 no caller compatibility/score/percentile/invert path
```

Additional regressions cover:

```text
caller cannot reverse canonical direction
six direct registry entries only
road and parking direct-normalization rejection
parking-only cannot become final road/parking feature
age fallback exact frozen semantics
age fallback cannot be retargeted
non-age missing feature never receives age fallback
deterministic identity
actual SITE semantic change changes identity
actual benchmark distribution change changes identity
competition measurement-definition same/mismatch lineage
competition remains value=None while inversion policy exists
no whole-feature/readiness/core surface
```

## 17. Scope audit

Explicitly not implemented:

```text
whole NormalizedLocationFeatures assembly
road_parking_access_score
COMB-005 weights/calibration
ScoringReadiness
RealDataPipelineResult orchestration
CategoryScores
Location Score
core.analyze()
```

No checkpoint 3.4-7 implementation was started.

## 18. Documentation updates

Added:

```text
sitescore-benchmarks/docs/CHECKPOINT_3_4_6_FEATURE_NORMALIZATION_COMPATIBILITY.md
```

Updated:

```text
sitescore-benchmarks/README.md
```

The checkpoint document records canonical registry/directions, SITE gates, compatibility dimensions, transit and competition lineage, unique age fallback, COMB-005 boundary, identities, failure states, DAG, validation evidence, scope and unresolved decisions.

## 19. Known unresolved / calibration-gated decisions preserved

No new derivation or scalar reduction was invented for unresolved metrics, including:

```text
walkable_population
target_population_density
household_income_ratio
competition_pressure
road_reachable_area_km2
```

No empirical benchmark adequacy rule was introduced for:

```text
minimum N
minimum coverage ratio
minimum unique-value count
variance requirement
confidence threshold
sample adequacy
```

Production equal-area decisions, unresolved metric reductions, COMB-005 calibration, benchmark adequacy and empirical validation remain outside this checkpoint.

An individual `AVAILABLE` normalized feature does not imply whole-model scoring readiness.

## 20. Self-audit result

```text
actual SITE measurement is query authority                  VERIFIED
actual BenchmarkDistributionArtifact is benchmark authority VERIFIED
locked MID_ECDF_V1 reused, not reimplemented                VERIFIED
caller raw score/percentile/invert/compatible path          NONE
six-feature canonical direction registry                    VERIFIED
exact definition compatibility                              VERIFIED
exact derivation-policy compatibility                       VERIFIED
exact measurement-precision compatibility                   VERIFIED
exact unit compatibility                                    VERIFIED
exact actual method-version compatibility                   VERIFIED
metric-specific source/bundle compatibility                 VERIFIED
transit bundle exactness                                    VERIFIED
competition measurement-definition lineage                 VERIFIED
per-observation source-ref equality not required            VERIFIED
missing/unavailable/uncalibrated direct input -> no score    VERIFIED
ordinary direction = 100*P                                  VERIFIED
competition direction = 100*(1-P)                           VERIFIED
age fallback is unique 50-point exception                   VERIFIED
road/parking final composite absent                         VERIFIED
no readiness/category/core scoring                          VERIFIED
new runtime dependency                                      NONE
frozen upstream source mutation                             NONE
final diff outside sitescore-benchmarks                     NONE
CONTRACT_CHANGE_REQUIRED                                    0
```

## 21. Reviewer attention points

Please independently focus on:

1. actual SITE `DerivedMetricMeasurement` being the only query authority;
2. inability to caller-supply/invert score direction;
3. exact definition/policy/precision/unit/method compatibility;
4. metric-specific source bundle semantics, especially transit fingerprint equality;
5. competition measurement-definition compatibility while canonical competition remains nonnumeric;
6. age fallback being unique and impossible to retarget through public builder;
7. absence of any road/parking composite substitute before COMB-005;
8. result identity binding actual site + benchmark + compatibility + ECDF + policy;
9. absence of whole features/readiness/category/core scoring;
10. validated `d0fe64d5...` → final `7b8e4594...` delta being workflow-removal-only.

## 22. Final implementer state

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CHECKPOINT: FAZ 3.4-6
BASE_SHA: 530869a06fd5e1a64357701fff3f226d70ac6d1d
CODE_BRANCH: faz3.4/cp3.4-6-feature-normalization-compatibility
CODE_HEAD_SHA: 7b8e4594ba3e58b31ae5163960220832e28b4970
PR: #3
CONTRACT_CHANGE_REQUIRED: 0
```

No merge, user-controlled LOCK transition, tag, or checkpoint 3.4-7 work was performed. The Implementer stops here for independent Reviewer review.
