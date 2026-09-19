# FAZ 3.4 — Checkpoint 3.4-6: Feature-Specific Normalization + Compatibility

Status: **READY FOR REVIEW** after implementation validation. This document is not a LOCK record.

## 1. Purpose and locked inputs

Checkpoint 3.4-6 is an additive consumer of the locked 3.4-4 benchmark distribution and 3.4-5 mid-ECDF layers. The canonical domain chain is:

```text
actual SITE DerivedMetricMeasurement
+ actual BenchmarkDistributionArtifact
+ exact site↔benchmark measurement compatibility
+ locked MID_ECDF_V1
+ canonical feature normalization policy
→ individual FeatureNormalizationResult in [0,100]
```

No frozen upstream source contract was changed. `CONTRACT_CHANGE_REQUIRED = 0`.

## 2. Canonical direct-feature registry

V1 direct mappings are exactly:

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

There is no direct V1 normalization policy for road or raw parking metrics. The downstream `road_parking_access_score` remains COMB-005 gated for checkpoint 3.4-7.

## 3. Direction / transform semantics

The locked 3.4-5 percentile remains directionless. 3.4-6 applies feature semantics:

```text
ordinary higher-is-better: score = 100 * P
competition opportunity:    score = 100 * (1 - P)
```

No caller `invert`, direction string, score, or percentile is accepted by the canonical domain entry point. Direction comes only from the canonical V1 registry.

No rounding, quantization, smoothing, epsilon, winsorization, logistic transform, or semantic display formatting is applied. Available scores must naturally satisfy `[0,100]`.

## 4. SITE measurement authority and numeric eligibility

The canonical domain function consumes an actual `DerivedMetricMeasurement` whose subject kind is `SITE`. The ECDF query value is derived only from:

```text
site_measurement.metric_value.value
```

For direct normalization, the nested site `MetricValue` must satisfy:

```text
value is not None
availability == AVAILABLE
score_eligibility == ELIGIBLE
calibration_state == CALIBRATED
finite numeric value
```

Missing, unavailable, ineligible, or uncalibrated direct measurements do not receive a numeric normalized score. There is no zero or neutral substitution.

## 5. Benchmark authority

The benchmark input is an actual `BenchmarkDistributionArtifact`. A numeric feature score is emitted only when its state is `AVAILABLE`.

These states remain non-normalizable:

```text
EMPTY_ELIGIBLE_POPULATION
NO_NUMERIC_OBSERVATIONS
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

Excluded benchmark attempts are never reconstructed as observations. Percentile evaluation delegates to the locked `evaluate_benchmark_mid_ecdf(..., policy=MID_ECDF_V1)` path; there is no second ECDF implementation.

## 6. Exact site ↔ benchmark compatibility

`SiteBenchmarkCompatibility` derives both sides from actual objects. It compares:

```text
MetricDefinition.identity_id
MetricDerivationPolicy.identity_id
MeasurementPrecisionPolicy.identity_id
unit
actual DerivedMetricMeasurement.method_version
source_bundle_compatibility
```

`source_refs` are provenance and are deliberately not required to be identical across site and benchmark observations.

Diagnosable incompatibility reasons include:

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

Compatibility state is derived; callers cannot provide `compatible=True` or arbitrary compatibility identities.

## 7. Transit compatibility

Transit requires exact equality of:

```text
transit_source_bundle_fingerprint
```

A SITE measurement from bundle A cannot normalize against a benchmark distribution from bundle B even when metric definition, unit, method and numeric value otherwise match. Same-bundle canonical transit measurements normalize normally when all other gates pass.

## 8. Competition semantics

The V1 policy structurally freezes:

```text
competition_pressure
-> competition_opportunity_score
-> 100 * (1 - P)
```

Compatibility also preserves exact:

```text
competition_measurement_definition_id
```

The locked canonical `competition_pressure` metric remains unresolved and nonnumeric because its approved scalar reduction does not yet exist. 3.4-6 does not make it numeric. Controlled tests verify the inversion transform separately and verify same/mismatched measurement-definition lineage using actual unresolved canonical measurements.

Thus:

```text
normalization direction defined
!= canonical competition metric currently numeric
!= production score ready
```

## 9. Other upstream unresolved metrics

The checkpoint does not invent derivation/calibration policies for current unresolved metrics, including:

```text
walkable_population
target_population_density
household_income_ratio
competition_pressure
road_reachable_area_km2
```

A registry entry defines future normalization semantics; it does not assert present measurement availability or production readiness.

## 10. Frozen age fallback — unique exception

Age uses a dedicated, non-generic policy and builder:

```text
normalized feature: age_target_concentration_score
score: 50
unit: score_0_100
availability: available
score eligibility: eligible
calibration: uncalibrated
is_proxy: true
reason: age_affinity_not_calibrated
method/fallback semantic: age_neutral_fallback/1.0
```

The builder accepts no feature argument. The policy rejects attempts to retarget this fallback to transit, income, walk reach, competition, population, road, or parking. No other missing/uncalibrated feature receives 50.

## 11. COMB-005 boundary

Checkpoint 3.4-6 does not emit an available final `road_parking_access_score` from:

```text
road only
parking capacity only
curb length only
50/50 road+parking
missing-side neutral 50
one-side renormalization
```

No road/parking composite weights exist here. COMB-005 remains checkpoint 3.4-7 scope.

## 12. Public contract family

Added in `sitescore_benchmarks.normalization`:

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

These are exported by `sitescore_benchmarks`.

## 13. Identity / lineage

A feature-normalization policy identity binds:

```text
policy id/version
actual canonical metric definition identity
actual canonical derivation-policy identity
normalized feature key
direction
MID_ECDF_V1 identity
ECDF comparison-policy identity
compatibility-rule version
```

A compatibility identity binds actual site measurement, actual benchmark distribution, both compatibility identities, derived state and reasons.

A normalization result identity binds as applicable:

```text
actual site measurement_id
actual benchmark distribution_id
site compatibility identity
benchmark compatibility identity
compatibility decision identity
normalization policy identity
locked ECDF evaluation identity
normalized feature key
state/reasons
percentile
score
```

No detached caller-supplied benchmark ID, measurement ID, score, percentile, or compatibility assertion is authoritative.

## 14. Explicit result gating states

Direct normalization may be:

```text
AVAILABLE
SITE_METRIC_NOT_AVAILABLE
SITE_METRIC_NOT_ELIGIBLE
SITE_METRIC_NOT_CALIBRATED
BENCHMARK_NOT_AVAILABLE
INCOMPATIBLE
```

Only `AVAILABLE` produces an ECDF evaluation and score.

## 15. Dependency / DAG audit

No dependency metadata changed.

Direct runtime dependencies remain:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

No new third-party dependency was added. `sitescore-benchmarks` still has no direct runtime import of `sitescore-core`, `sitescore-data`, `sitescore-providers`, or pipeline/application packages. No metrics→benchmarks reverse edge was introduced.

## 16. Adversarial regression coverage

Tests cover at minimum:

```text
NORM-001 real-domain higher-is-better P=.75 -> 75
NORM-002 competition P=.75 -> 25 policy transform
NORM-003 ordinary/inverted endpoints
COMP-001 exact compatible SITE+benchmark success
COMP-002 wrong metric
COMP-003 method-version mismatch
COMP-004 measurement-precision mismatch
COMP-005 transit bundle mismatch
COMP-006 transit same-bundle success
COMP-007 unavailable benchmark
COMP-008 unavailable/missing SITE measurement
COMP-009 uncalibrated numeric SITE measurement
COMP-010 no caller compatible/percentile/score/invert authority
```

Additional tests cover canonical direction immutability, exact six-feature registry membership, raw parking/road rejection, age fallback exactness and non-leakage, deterministic result identities, site/benchmark lineage sensitivity, competition measurement-definition compatibility, and absence of later-checkpoint surfaces.

## 17. Validation evidence

First full workflow run found one integration-call defect shared by six tests: the locked ECDF policy parameter is keyword-only. That call was corrected without changing locked ECDF semantics.

Subsequent full validation at source/test commit `0cd01caaa70d8c434bcdf58b5221bf898c399694` succeeded in GitHub Actions run `31905049465`:

```text
sitescore-benchmarks: 169 passed
sitescore-metrics:     67 passed
sitescore-spatial:     PASS
sitescore-providers:   PASS
sitescore-data:        PASS
sitescore-core:        PASS
```

A final documentation-inclusive validation is required after this document/README update before handoff. The temporary branch-only workflow will then be removed from the final PR diff.

## 18. Explicit non-scope / readiness boundary

Not implemented:

```text
whole NormalizedLocationFeatures assembly
road_parking_access_score composite
COMB-005 weights/calibration
ScoringReadiness
RealDataPipelineResult orchestration
CategoryScores
Location Score
core.analyze()
```

An available individual feature-normalization result means only that one feature was normalized under compatible evidence and canonical policy. It does not imply whole-model score readiness.

## 19. Empirical adequacy / calibration decisions preserved

No minimum benchmark N, coverage ratio, unique-value count, variance requirement, confidence threshold, or sample-adequacy threshold was introduced. Production equal-area choices, unresolved metric reductions, COMB-005 calibration, benchmark adequacy, and empirical validation remain outside this checkpoint.

Project validity language remains: mathematically validated scoring engine; empirical validation pending.

## 20. Self-audit state

```text
actual SITE measurement is query authority                 VERIFIED
actual BenchmarkDistributionArtifact is benchmark authority VERIFIED
caller raw score/percentile/invert/compatible path          NONE
exact definition/policy/precision/unit/method compatibility VERIFIED
transit bundle exactness                                    VERIFIED
competition measurement-definition lineage                 VERIFIED
per-observation source-ref equality not required            VERIFIED
missing/unavailable/uncalibrated direct input -> no score    VERIFIED
ordinary direction = 100*P                                 VERIFIED
competition direction = 100*(1-P)                          VERIFIED
age fallback is unique 50-point exception                  VERIFIED
road/parking final composite absent                         VERIFIED
no readiness/category/core scoring                         VERIFIED
new dependency/cycle                                       NONE OBSERVED
frozen upstream source mutation                            NONE
CONTRACT_CHANGE_REQUIRED                                   0
```

Final implementation handoff state remains `READY_FOR_REVIEW`; reviewer/user acceptance is separate.
