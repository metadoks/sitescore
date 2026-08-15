# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-6
CHECKPOINT_TITLE: Feature-Specific Normalization + Compatibility
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 530869a06fd5e1a64357701fff3f226d70ac6d1d
CODE_BRANCH: faz3.4/cp3.4-6-feature-normalization-compatibility
REVIEWED_HEAD_SHA: NONE
PR: NONE
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
```

---

# 1. PREVIOUS CHECKPOINT LOCK VERIFICATION

FAZ 3.4-5 is now accepted, user-authorized and merged.

Reviewer independently verified:

```text
PR #2 state: closed
PR #2 merged: true
reviewed branch HEAD: 4e2d44178141e2715b18283917288bfc829dd42e
merge/main SHA: 530869a06fd5e1a64357701fff3f226d70ac6d1d
```

GitHub `main` currently points to:

```text
530869a06fd5e1a64357701fff3f226d70ac6d1d
```

This merge SHA is the authoritative baseline for checkpoint 3.4-6.

Current repository branch listing contains no existing 3.4-6 branch at publication time. Therefore create exactly one new checkpoint branch from current `main`:

```text
faz3.4/cp3.4-6-feature-normalization-compatibility
```

If repository state has legitimately advanced by the time this instruction is read, re-fetch first and report the discrepancy. Do not reset legitimate work and do not create a duplicate branch.

---

# 2. CHECKPOINT PURPOSE

Implement only:

```text
FAZ 3.4 — CHECKPOINT 3.4-6
Feature-Specific Normalization + Compatibility
```

Checkpoint 3.4-5 ended at a generic statistical result:

```text
actual BenchmarkDistributionArtifact
→ BenchmarkNumericSample
→ mid-ECDF percentile P in [0,1]
```

Checkpoint 3.4-6 adds the feature-semantic boundary:

```text
actual SITE DerivedMetricMeasurement
+
actual compatible BenchmarkDistributionArtifact
+
locked 3.4-5 mid-ECDF semantics
+
canonical feature-normalization policy
→
feature-normalization result in [0,100]
```

The key purpose is not merely multiplying a percentile by 100. The checkpoint must prove that the site measurement and benchmark distribution are semantically comparable before producing a normalized score and must bind the feature-specific direction/inversion policy explicitly.

This checkpoint does **not** create CategoryScores, does **not** call core scoring, does **not** implement COMB-005 road/parking composition, and does **not** run scoring readiness / terminal pipeline orchestration.

---

# 3. FROZEN NORMALIZATION PRINCIPLE

The generic mid-ECDF output is directionless.

Feature normalization is feature-specific.

For ordinary higher-is-better features:

```text
score = 100 * P(site_metric_value)
```

For competition pressure, where a higher real-unit pressure means worse opportunity:

```text
competition_opportunity_score = 100 * (1 - P(competition_pressure))
```

The competition inversion is frozen and intentional.

Do not implement arbitrary feature direction passed by callers.

Direction must come from a canonical, versioned feature-normalization policy/registry owned by this checkpoint.

Do not let a caller turn competition into `100 * P`, or turn household income into `100 * (1-P)`, by supplying a boolean or string such as `invert=True`.

---

# 4. NORMALIZED V1 FEATURE SURFACE — FROZEN TARGET SEMANTICS

The frozen `sitescore-data` contract ultimately exposes exactly eight normalized feature slots:

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

Treat these names and semantics as frozen downstream targets.

However, this checkpoint must **not** mutate frozen `sitescore-data` merely to make construction convenient, and should not prematurely instantiate the final whole `NormalizedLocationFeatures` aggregate if that would require orchestration/readiness responsibilities belonging to later checkpoints.

The 3.4-6 result family must preserve enough explicit feature key, score, normalization policy, benchmark lineage and compatibility evidence for later adaptation to the frozen `NormalizedLocationFeatures` contract.

---

# 5. PACKAGE OWNERSHIP / DEPENDENCY BOUNDARY

Primary implementation should remain additive in:

```text
sitescore-benchmarks
```

because 3.4-6 consumes locked benchmark distributions and 3.4-5 ECDF artifacts and applies feature-specific benchmark normalization semantics.

Current approved direct SiteScore dependencies of `sitescore-benchmarks` are:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

Do not add a direct `sitescore-data` dependency merely to construct `MetricValue` or `NormalizedLocationFeatures` if an additive benchmark-owned normalization artifact can preserve the required semantics.

Do not add `sitescore-core`, `sitescore-pipeline`, or application dependencies.

Do not create dependency cycles.

If correct implementation is genuinely impossible under the frozen DAG, stop before mutating frozen contracts and report `CONTRACT_CHANGE_REQUIRED = 1` with exact evidence. Do not silently expand the DAG.

---

# 6. SITE MEASUREMENT MUST BE AN ACTUAL CANONICAL MEASUREMENT

Normalization must not accept a detached raw numeric query as production/domain authority.

The domain normalization path must consume an actual:

```text
DerivedMetricMeasurement
```

whose subject is a valid SITE subject under the locked `sitescore-metrics` contract.

The site numeric query passed into the 3.4-5 mid-ECDF evaluator must be derived from:

```text
site_measurement.metric_value.value
```

not from a separate caller-supplied number.

No API such as the following may be the canonical domain path:

```text
normalize(metric_key="household_income", site_value=85000, benchmark=...)
```

without binding the actual site measurement/evidence.

A deliberately pure mathematical helper may exist only if clearly separated from the domain canonical normalization artifact and cannot self-assert domain compatibility.

---

# 7. SITE MEASUREMENT NUMERIC ELIGIBILITY

A site measurement must not become a normalized score merely because it has a finite number.

For the current canonical V1 direct benchmark-normalization path, the actual nested site `MetricValue` must satisfy, unless an explicitly frozen exception exists:

```text
value is not None
availability == AVAILABLE
score_eligibility == ELIGIBLE
calibration_state == CALIBRATED
finite(value)
```

This mirrors the structural numeric-inclusion integrity established at 3.4-4 for benchmark observations.

Do not convert:

```text
missing → 0
unknown → 50
uncalibrated → 50
ineligible → 0
```

The one frozen age exception is handled separately in this prompt and must not be generalized.

If the site measurement is not normalization-eligible, produce an explicit non-available/gated normalization state or deterministically reject canonical available construction following package style. Do not fabricate a score.

---

# 8. BENCHMARK DISTRIBUTION MUST BE ACTUAL AND AVAILABLE

The benchmark side must be an actual locked:

```text
BenchmarkDistributionArtifact
```

and must satisfy the existing 3.4-4/3.4-5 usable state requirements.

No normalized score may be produced from:

```text
EMPTY_ELIGIBLE_POPULATION
NO_NUMERIC_OBSERVATIONS
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

Likewise, do not reconstruct a benchmark numeric population from excluded attempts or caller-provided values.

Use the locked 3.4-5 domain-bound ECDF path rather than implementing a second percentile algorithm.

There must be exactly one authoritative mid-ECDF convention: the locked 3.4-5 `MID_ECDF_V1` semantics.

---

# 9. EXACT SITE ↔ BENCHMARK COMPATIBILITY — PRIMARY CHECKPOINT INVARIANT

A site metric and a benchmark distribution are comparable only when their canonical measurement semantics match.

Metric key equality is insufficient.

Before evaluation, compatibility must bind/check at minimum the actual canonical identities/dimensions already established by locked metrics/benchmark contracts:

```text
MetricDefinition identity
MetricDerivationPolicy identity
MeasurementPrecisionPolicy identity
unit
actual method_version
metric-specific source/bundle compatibility
```

The benchmark distribution already exposes compatibility derived from actual benchmark measurements.

The site side must derive equivalent compatibility from the actual site `DerivedMetricMeasurement`, not from detached caller strings.

No normalized score may be emitted when compatibility differs.

The compatibility decision/result must itself be explicit and deterministic enough for later audit/readiness.

---

# 10. TRANSIT COMPATIBILITY — EXACT SOURCE BUNDLE REQUIRED

For:

```text
transit_service_departure_equivalents_per_hour
→ transit_access_score
```

site and benchmark must preserve and exactly match:

```text
transit_source_bundle_fingerprint
```

A site transit metric from bundle A and benchmark distribution from bundle B must not produce a normalized transit score even when:

```text
metric key
unit
method version
numeric value
```

otherwise match.

No neutral substitution or fallback bundle is allowed.

---

# 11. COMPETITION COMPATIBILITY — MEASUREMENT DEFINITION REQUIRED

For:

```text
competition_pressure
→ competition_opportunity_score
```

compatibility must preserve and exactly match:

```text
competition_measurement_definition_id
```

in addition to the generic measurement compatibility dimensions.

Current canonical `competition_pressure` remains structurally unresolved because the approved multi-scale scalar reduction does not yet exist.

Therefore 3.4-6 must **not invent a competition reduction merely to demonstrate inversion**.

It is valid and expected for production/canonical competition normalization to remain unavailable until the upstream canonical metric can become numeric under an approved future/calibration decision.

Still implement the frozen directionality/compatibility policy structurally so that, once a valid canonical numeric competition measurement/distribution exists under approved semantics, the normalization rule is unambiguously:

```text
100 * (1 - P)
```

Synthetic/private tests may exercise inversion only through structurally valid controlled artifacts if the existing contracts permit it without weakening canonical unresolved semantics. Never change the locked 3.4-3 unresolved production contract to make a test easy.

---

# 12. ROAD SEMANTICS / COMB-005 BOUNDARY

Current canonical:

```text
road_reachable_area_km2
```

remains unresolved because road multi-scale scalar reduction is unresolved.

The frozen final normalized surface contains:

```text
road_parking_access_score
```

but that score is a calibrated composite governed by COMB-005.

COMB-005 belongs to checkpoint 3.4-7.

Therefore checkpoint 3.4-6 must **not**:

```text
normalize road alone into road_parking_access_score
normalize parking capacity alone into road_parking_access_score
normalize curb length alone into road_parking_access_score
average road + parking 50/50
substitute neutral parking
renormalize when one side is missing
invent composite weights
```

Preserve road and parking evidence/normalization prerequisites if useful, but do not emit the final `road_parking_access_score` as an available score in 3.4-6 without an approved COMB-005 policy.

No arbitrary road-only fallback is allowed.

---

# 13. CURRENT DIRECT FEATURE NORMALIZATION MAP

Implement a canonical versioned registry/policy mapping real-unit metric semantics to normalized feature semantics.

At minimum preserve the intended V1 relationships:

```text
walkable_population
→ walkable_population_score
→ HIGHER_PERCENTILE_IS_BETTER

target_population_density
→ target_population_density_score
→ HIGHER_PERCENTILE_IS_BETTER

competition_pressure
→ competition_opportunity_score
→ LOWER_PERCENTILE_IS_BETTER / INVERTED

walkable_reach_area_km2
→ walkable_reach_area_score
→ HIGHER_PERCENTILE_IS_BETTER

transit_service_departure_equivalents_per_hour
→ transit_access_score
→ HIGHER_PERCENTILE_IS_BETTER

household_income
→ household_income_score
→ HIGHER_PERCENTILE_IS_BETTER
```

The remaining normalized targets are special/not direct in this checkpoint:

```text
age_target_concentration_score
→ frozen fallback special case when affinity calibration absent

road_parking_access_score
→ COMB-005 / checkpoint 3.4-7
```

Do not silently create a normalized feature for raw parking metrics because the frozen downstream surface does not expose independent parking score slots.

Do not create a normalized `road_reachable_area_score` slot that is not part of the frozen V1 normalized surface.

---

# 14. CURRENT UPSTREAM RESOLUTION STATE MUST REMAIN HONEST

Several real-unit metrics remain unresolved in the locked metric foundation:

```text
walkable_population
target_population_density
household_income_ratio
competition_pressure
road_reachable_area_km2
```

Do not invent missing derivation/calibration policies merely so every feature-normalization policy can produce a score.

Feature policy existence does not imply current measurement availability.

For example:

```text
policy says walkable_population_score is 100*P
```

may be structurally defined while canonical real-data normalization remains unavailable because `walkable_population` is still unresolved upstream.

Similarly `competition_opportunity_score` direction may be structurally frozen while canonical competition pressure remains nonnumeric.

Distinguish clearly:

```text
normalization semantics defined
!=
current canonical measurement available
!=
production score ready
```

---

# 15. FROZEN AGE FALLBACK — UNIQUE EXCEPTION

The only approved neutral normalized fallback is:

```text
age_target_concentration_score = 50
```

with the frozen semantics:

```text
availability: AVAILABLE
score eligibility: ELIGIBLE
calibration state: UNCALIBRATED
is_proxy: true
reason: age_affinity_not_calibrated
fallback/method semantic: age_neutral_fallback / 1.0
unit/semantic target: score_0_100
```

The exact frozen downstream `sitescore-data` contract already enforces important parts of this exception: numeric uncalibrated age score must be exactly 50, proxy=true, and carry `age_affinity_not_calibrated`.

Checkpoint 3.4-6 should provide an explicit versioned age-fallback normalization artifact/policy or equivalent foundation sufficient for later adaptation.

Do not generalize the age exception to any other feature.

Forbidden:

```text
missing transit → 50
missing income → 50
unresolved competition → 50
missing road/parking → 50
```

---

# 16. SCORE RANGE / NUMERIC SEMANTICS

Available normalized scores must satisfy:

```text
0.0 <= score <= 100.0
```

Feature normalization must use the locked mid-ECDF result directly:

```text
ordinary: score = 100 * percentile
competition: score = 100 * (1 - percentile)
```

Do not add:

```text
clamping to hide invalid upstream values
round(...)
quantization
integer coercion
smoothing
epsilon
winsorization
logistic transforms
custom nonlinear curves
```

If mathematical floating representation produces the normal binary floating result of the frozen formula, preserve it consistently; do not invent display rounding as semantic normalization.

Do not confuse report formatting with model semantics.

---

# 17. NORMALIZATION POLICY IDENTITY

The canonical normalization policy/registry must make feature semantics auditable and versioned.

A load-bearing feature-normalization identity should bind, as applicable:

```text
normalization policy id/version
source metric key / canonical metric definition identity
normalized feature key
direction / transform rule
required ECDF policy identity
required numeric comparison policy identity
compatibility rule/version
age fallback rule/version where applicable
```

Do not use a detached version string as the only authority if actual nested policy objects are available.

The runtime behavior and the policy identity must agree.

Changing directionality, ECDF policy, metric mapping, or compatibility semantics must change the relevant identity.

Incidental timestamps, filesystem paths and worker ordering must not.

---

# 18. NORMALIZATION RESULT / ARTIFACT IDENTITY

A canonical available feature-normalization result should bind enough actual nested lineage to prove what was normalized.

As applicable, bind:

```text
actual site DerivedMetricMeasurement.measurement_id
actual benchmark distribution_id
actual benchmark compatibility identity
actual site compatibility identity
normalization policy identity
mid-ECDF evaluation identity
normalized feature key
normalized score
state/reason codes
```

Do not accept caller-supplied:

```text
percentile
score
compatibility=true
benchmark_id string
site measurement id string
```

as independent authority when actual objects are available.

No self-asserted compatibility state.

---

# 19. METHOD VERSION COMPATIBILITY — PRESERVE 3.4-4 HARDENING

Checkpoint 3.4-4 explicitly hardened benchmark compatibility so actual:

```text
DerivedMetricMeasurement.method_version
```

is compatibility-bearing.

3.4-6 must preserve that invariant on the site ↔ benchmark boundary.

A site measurement using method V2 must not normalize against a benchmark distribution built under method V1 merely because definition/policy/unit/source-bundle keys otherwise match.

Add an adversarial test for this exact path.

Do not regress BENCH-H002.

---

# 20. MEASUREMENT PRECISION COMPATIBILITY

Site and benchmark measurement precision semantics must match exactly by actual `MeasurementPrecisionPolicy.identity_id`.

Do not confuse this with the 3.4-5 ECDF comparison policy.

The compatibility chain contains both distinct dimensions:

```text
measurement representation precision
AND
ECDF numeric comparison/tie policy
```

Both matter, but they are not aliases.

Add tests that mismatched measurement precision prevents canonical normalization even though ECDF comparison policy is unchanged.

---

# 21. UNIT COMPATIBILITY

Site measurement unit must match the benchmark metric/distribution unit exactly under the canonical metric definition.

There must be no generic implicit conversion in this checkpoint.

Do not convert dollars, kilometres, metres, counts, or rates opportunistically.

The locked canonical metric definition is authority.

A wrong-unit path should already be difficult to construct through locked metrics; nevertheless ensure 3.4-6 introduces no detached caller unit field that can bypass that protection.

---

# 22. FEATURE-SPECIFIC BENCHMARK LINEAGE

The normalization artifact should preserve enough benchmark lineage to support the downstream frozen fields conceptually represented by `NormalizedLocationFeatures`, especially:

```text
competition benchmark reference / measurement_definition / normalization policy
transit benchmark reference / source_bundle_fingerprint / normalization policy
```

Do not fabricate legacy `BenchmarkReference` values from arbitrary strings if the current 3.4 benchmark artifacts do not provide an exact lossless mapping.

If an adapter to the frozen legacy/lightweight reference is not yet structurally justified, preserve the stronger actual 3.4 artifact lineage in the new normalization artifact and defer final DTO adaptation to the later integration/readiness checkpoint.

Stronger actual lineage > detached compatibility metadata.

---

# 23. DO NOT PREMATURELY BUILD THE WHOLE NORMALIZEDLOCATIONFEATURES OBJECT

`sitescore-data.NormalizedLocationFeatures` is a frozen terminal normalized-feature surface with eight slots and compatibility metadata.

Checkpoint 3.4-6 is not the final readiness/orchestration checkpoint.

Do not create a whole `NormalizedLocationFeatures` by:

```text
putting fake unavailable fields at 0
putting unresolved fields at 50
omitting required slots
renormalizing category weights
generating road_parking_access_score without COMB-005
claiming score readiness
```

It is acceptable and likely preferable for 3.4-6 to emit individual strongly lineage-bound normalization results/artifacts which 3.4-7/3.4-8 can later assemble/gate.

Do not modify the frozen data contract simply because not all eight scores are currently available.

---

# 24. COMPATIBILITY FAILURE MUST BE EXPLICIT

A normalization attempt with an incompatible site/benchmark pair must not return a numeric score.

Provide a typed state/result or deterministic construction rejection consistent with current package style.

Compatibility failures should be diagnosable through stable reason semantics such as conceptually:

```text
metric_definition_mismatch
metric_derivation_policy_mismatch
measurement_precision_mismatch
unit_mismatch
method_version_mismatch
transit_source_bundle_mismatch
competition_measurement_definition_mismatch
benchmark_not_available
site_metric_not_available
site_metric_not_calibrated
```

Do not require these exact strings if the package already has a stronger canonical style, but avoid one opaque catch-all if precise structural reason is available.

No false available score may survive an incompatibility.

---

# 25. DO NOT REQUIRE PER-CELL SOURCE REFS TO BE IDENTICAL

Do not over-constrain site/benchmark compatibility by requiring site evidence `source_refs` to equal every benchmark cell's source refs.

Compatibility is semantic, not “same exact observation provenance”.

For example separate geographic observations under the same approved dataset/method/bundle semantics may legitimately have different source references.

Preserve provenance lineage, but do not make per-observation source-ref equality a generic compatibility rule unless an existing frozen contract explicitly requires it.

---

# 26. NO EMPIRICAL ADEQUACY POLICY HERE

Do not introduce:

```text
minimum benchmark N
minimum coverage ratio
minimum unique values
variance threshold
confidence threshold
```

3.4-6 consumes a structurally AVAILABLE benchmark distribution/ECDF foundation.

Production empirical sample adequacy remains calibration-gated/unresolved.

Do not hide this by assigning arbitrary thresholds.

---

# 27. REQUIRED FEATURE-DIRECTION TESTS

Add tests proving at minimum:

## NORM-001 — higher-is-better mapping

For a compatible synthetic canonical feature where percentile is:

```text
P = 0.75
```

ordinary normalized score must be:

```text
75.0
```

using a real domain path, not caller-supplied percentile authority.

## NORM-002 — competition inversion semantics

Where a structurally valid controlled fixture can lawfully produce competition percentile:

```text
P = 0.75
```

the policy mapping must imply:

```text
competition opportunity = 25.0
```

Do not mutate production unresolved competition metric semantics just for the test. If direct canonical fixture construction is impossible under frozen contracts, test the frozen mapping policy/pure transform separately while keeping the production domain path correctly unavailable.

## NORM-003 — endpoints

Ordinary feature:

```text
P=0 → 0
P=1 → 100
```

Competition inversion:

```text
P=0 → 100
P=1 → 0
```

No special endpoint override beyond the transform.

---

# 28. REQUIRED SITE ↔ BENCHMARK COMPATIBILITY TESTS

Add adversarial tests at minimum for:

## COMP-001 — exact compatible site/benchmark success

Use an actually canonical SITE measurement and matching AVAILABLE benchmark distribution. Normalize successfully.

## COMP-002 — wrong metric

Household-income site measurement against walkable-reach benchmark distribution must not normalize.

## COMP-003 — method mismatch

Same metric definition/policy/unit but site `method_version != benchmark method_version` must fail compatibility.

## COMP-004 — measurement precision mismatch

Actual precision identities differ → no score.

## COMP-005 — transit bundle mismatch

Same transit metric but site and benchmark `transit_source_bundle_fingerprint` differ → no score.

## COMP-006 — transit same bundle

Exact compatible transit bundle → normalization allowed if all numeric eligibility requirements are satisfied.

## COMP-007 — benchmark incompatible/unavailable

Non-AVAILABLE distribution → no normalization.

## COMP-008 — site unavailable

SITE measurement unavailable/missing → no score and no zero substitution.

## COMP-009 — site uncalibrated numeric

AVAILABLE + ELIGIBLE + UNCALIBRATED numeric SITE measurement → no normalized score, except the separate age fallback which is not this metric path.

## COMP-010 — no caller compatibility assertion

Prove public domain result cannot be constructed by passing `compatible=True`, arbitrary compatibility identity strings, or arbitrary percentile/score.

---

# 29. REQUIRED LINEAGE / IDENTITY TESTS

Add tests proving:

```text
same actual semantic inputs → same normalization identity
input/runtime noise → does not change identity
site measurement semantic change → identity changes
benchmark distribution change → identity changes
normalization direction/policy change → identity changes or unsupported policy is rejected
ECDF policy change → identity changes or unsupported policy is rejected
method version change → incompatible / identity-sensitive
transit bundle change → incompatible / identity-sensitive
```

Do not add a future-policy constructor that callers can freely use to bypass V1 support merely for identity tests. Unsupported policy objects should be rejected at canonical boundaries.

---

# 30. REQUIRED AGE FALLBACK TESTS

Add explicit tests for the frozen unique exception:

```text
score == 50
proxy == true
calibration == UNCALIBRATED
reason contains exactly/appropriately age_affinity_not_calibrated
fallback/method semantic identifies age_neutral_fallback / 1.0
```

Also prove:

```text
age fallback is feature-specific
```

and cannot be reused by transit, income, walk reach, competition, population or road/parking normalization.

Do not create a generic `neutral_fallback(feature_key)` API that allows arbitrary features to get 50.

---

# 31. REQUIRED COMB-005 BOUNDARY TESTS

Prove checkpoint 3.4-6 does not create an available final road/parking composite through any of these paths:

```text
road only
parking capacity only
curb length only
50/50 road + parking
one-side-missing renormalization
missing-side neutral 50
```

The final `road_parking_access_score` remains gated for checkpoint 3.4-7.

No new empirical composite weight should exist in source.

---

# 32. REQUIRED SCOPE TESTS

Architecture/scope regressions must continue to prohibit:

```text
CategoryScores
Location Score
core.analyze()
ScoringReadiness
RealDataPipelineResult orchestration
COMB-005 implementation
road_parking_access_score available composite
arbitrary empirical thresholds
provider-specific normalization logic
```

3.4-6 may legitimately contain `100 * P` / `100 * (1-P)` because those are now in scope, unlike 3.4-5.

Update architecture guards carefully so they do not accidentally forbid the feature-normalization behavior this checkpoint is supposed to add while still blocking later checkpoint leakage.

---

# 33. FROZEN UPSTREAM PACKAGES

Do not change source semantics in:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
```

unless a genuine frozen-contract impossibility is demonstrated.

Do not weaken `DerivedMetricMeasurement` coherence to manufacture test fixtures.

Do not make unresolved competition/road metrics numeric.

Do not change the 3.4-4 distribution eligibility rules.

Do not change the 3.4-5 ECDF formula or comparison policy.

Checkpoint 3.4-6 should be an additive consumer of those locked layers.

---

# 34. REQUIRED SOURCE INSPECTION BEFORE IMPLEMENTING

Before design, inspect the actual current `main` implementations at the verified baseline, including at minimum:

```text
sitescore-benchmarks/src/sitescore_benchmarks/measurement.py
sitescore-benchmarks/src/sitescore_benchmarks/population.py
sitescore-benchmarks/src/sitescore_benchmarks/distribution.py
sitescore-benchmarks/src/sitescore_benchmarks/ecdf.py
sitescore-benchmarks/src/sitescore_benchmarks/__init__.py
sitescore-benchmarks/tests/

sitescore-metrics/src/sitescore_metrics/contracts.py
sitescore-metrics/src/sitescore_metrics/measurements.py
sitescore-metrics/src/sitescore_metrics/definitions.py

sitescore-data/src/sitescore_data/schemas/features.py
sitescore-data/src/sitescore_data/schemas/benchmarks.py
```

Use actual source contracts and public constructors. Do not implement from remembered summaries alone.

---

# 35. RECOMMENDED ADDITIVE CONTRACT FAMILY

Exact names are not frozen, but a reasonable minimal semantic family may include equivalents of:

```text
FeatureNormalizationDirection / transform rule
FeatureNormalizationPolicy
canonical V1 normalization registry
SiteBenchmarkCompatibility / compatibility evaluation
FeatureNormalizationState
FeatureNormalizationResult / Artifact
normalize_feature(site_measurement, benchmark_distribution, feature_policy)
AgeTargetConcentrationFallbackPolicy / result
```

Avoid a generic extensible normalization framework larger than SiteScore requires.

Prefer explicit V1 registry semantics over caller-configurable generic transformations.

---

# 36. NORMALIZATION RESULT MUST NOT CLAIM SCORE READINESS

An available individual normalized feature result means only:

```text
this feature was normalized under compatible evidence and canonical policy
```

It does not mean:

```text
all eight normalized features are available
CategoryScores can be computed
core.analyze() may be called
pipeline is SCORE_READY
```

Do not use readiness terminology for an individual feature normalization artifact.

Checkpoint 3.4-8 owns whole-feature-set scoring readiness and terminal pipeline state.

---

# 37. VALIDITY / CALIBRATION CLAIMS

Do not describe percentile normalization as empirical validation.

The project-wide validity claim remains:

```text
Mathematically validated scoring engine; empirical validation pending.
```

Do not claim that feature normalization thresholds/directions have been empirically proven beyond the frozen structural model.

Production equal-area configuration, unresolved metric reductions, COMB-005 calibration and benchmark adequacy remain calibration-gated as already recorded.

---

# 38. TEST / REGRESSION EXPECTATION

The latest accepted pre-3.4-6 checkpoint test evidence includes:

```text
sitescore-benchmarks: 142/142 PASS
sitescore-metrics:      67/67 PASS
```

and the remaining locked package suites were green in the same 3.4-5 validation run.

New tests should increase the benchmark suite count.

Run at minimum the full `sitescore-benchmarks` and `sitescore-metrics` suites, and preferably all six package-root suites before READY FOR REVIEW.

Report exact executed counts where available.

If a suite was not run, say `NOT RUN` with the reason. Never report remembered historical counts as a current executed PASS.

A temporary branch-only validation workflow may be used if needed, but remove it before final handoff if it is not intended as repository infrastructure, and prove validated commit → final HEAD is workflow-removal-only.

---

# 39. CHECKPOINT DOCUMENTATION

Add a durable checkpoint record, likely:

```text
sitescore-benchmarks/docs/CHECKPOINT_3_4_6_FEATURE_NORMALIZATION_COMPATIBILITY.md
```

Document at minimum:

```text
purpose/scope
locked 3.4-4 / 3.4-5 dependencies
feature normalization registry
feature directions
site numeric eligibility
site↔benchmark compatibility dimensions
transit bundle semantics
competition measurement-definition semantics
current unresolved production features
age fallback unique exception
road/parking COMB-005 boundary
normalization identity/lineage
failure states/reasons
no empirical adequacy threshold
no readiness claim
package DAG
tests
CONTRACT_CHANGE_REQUIRED state
```

Status before independent Reviewer acceptance must remain:

```text
READY FOR REVIEW
```

not LOCKED.

---

# 40. GIT / PR WORKFLOW

Create exactly one branch:

```text
faz3.4/cp3.4-6-feature-normalization-compatibility
```

from verified baseline:

```text
530869a06fd5e1a64357701fff3f226d70ac6d1d
```

Open exactly one PR targeting `main`.

All later reviewer hardening for 3.4-6 stays on the same branch and same PR.

Do not merge.

Do not self-LOCK.

Do not start 3.4-7.

Do not force-push or rewrite history by default.

---

# 41. SELF-AUDIT BEFORE READY FOR REVIEW

Before returning, explicitly audit:

## Domain authority

- Is the site query derived from actual SITE `DerivedMetricMeasurement`?
- Can a caller supply arbitrary percentile or normalized score?
- Can a caller assert compatibility?

## Compatibility

- definition identity?
- derivation policy identity?
- measurement precision identity?
- unit?
- method version?
- transit bundle?
- competition measurement definition?
- correct ECDF policy?

## Missingness/calibration

- missing site → no score?
- uncalibrated site → no score except age fallback?
- unavailable benchmark → no score?
- no neutral substitution?

## Directionality

- ordinary features use 100*P?
- competition uses 100*(1-P)?
- caller cannot override direction?

## Age

- only age gets frozen 50 fallback?
- exact proxy/uncalibrated/reason/method semantics preserved?

## COMB-005

- no final road_parking_access_score yet?
- no arbitrary weights or one-side fallback?

## Scope

- no readiness?
- no CategoryScores?
- no core analyze?
- no pipeline orchestration?

## DAG

- no new forbidden package dependencies/cycles?
- frozen upstream source unchanged?

---

# 42. ADVERSARIAL REVIEW TARGETS

Before handoff, actively attempt public-path bypasses such as:

```text
SITE household_income + transit benchmark
SITE household_income method v2 + benchmark method v1
SITE transit bundle A + benchmark bundle B
SITE metric precision v2 + benchmark FULL_BINARY64
SITE uncalibrated numeric + valid benchmark
valid SITE + NO_NUMERIC_OBSERVATIONS benchmark
caller-supplied fake compatibility=true
caller-supplied score=99
caller-supplied invert flag reversing canonical direction
competition unresolved forced numeric
road-only normalized into road_parking_access_score
parking-only normalized into road_parking_access_score
missing feature receives age fallback 50
```

Every path must reject or produce explicit non-available semantics. No false canonical normalized score.

---

# 43. CONTRACT_CHANGE_REQUIRED RULE

Expected:

```text
CONTRACT_CHANGE_REQUIRED = 0
```

If and only if a frozen upstream contract truly makes correct additive 3.4-6 implementation impossible, do not silently alter that contract.

Return:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with:

```text
exact frozen contract
exact missing capability
reproducible public-path reason additive design cannot solve it
minimal proposed contract change
package/version/migration effects
```

Aesthetic/API-preference improvements are not sufficient.

---

# 44. REQUIRED IMPLEMENTER.md HANDOFF FORMAT

On completion update only the Implementer-owned coordination file:

```text
ops/reviewer-implementer-handoff/implementer.md
```

At minimum include:

```text
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-6
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: 530869a06fd5e1a64357701fff3f226d70ac6d1d
CODE_BRANCH: faz3.4/cp3.4-6-feature-normalization-compatibility
CODE_HEAD_SHA: <full actual SHA>
PR: #<actual number>
CONTRACT_CHANGE_REQUIRED: 0 or 1
```

Then report in detail:

```text
changed files
public contracts
feature normalization registry/directions
site numeric eligibility
site↔benchmark compatibility
transit semantics
competition semantics/current unresolved state
age fallback
COMB-005 boundary
identity/lineage
failure states/reasons
dependency/DAG audit
adversarial tests
full test evidence
scope audit
documentation
known unresolved calibration items
self-audit
reviewer attention points
```

Do not write `READY_TO_LOCK`, `LOCKED`, or reviewer acceptance.

---

# 45. ACCEPTANCE TARGET

The checkpoint is ready for independent review when:

```text
1. Actual SITE measurement is the canonical query authority.
2. Actual benchmark distribution is the benchmark authority.
3. Site and benchmark exact semantic compatibility is proven before normalization.
4. Method version and measurement precision cannot be bypassed.
5. Transit source-bundle compatibility is exact.
6. Competition measurement-definition semantics are preserved and unresolved production reduction is not invented.
7. Ordinary feature direction is canonical 100*P.
8. Competition direction is canonical 100*(1-P).
9. Direction cannot be caller overridden.
10. Score stays in [0,100] without rounding/epsilon/clamping hacks.
11. Missing/unavailable/uncalibrated inputs do not become numeric scores.
12. Frozen age fallback is implemented as the unique 50-point uncalibrated proxy exception.
13. Age fallback cannot leak to other features.
14. road_parking_access_score remains COMB-005 gated for 3.4-7.
15. No readiness, CategoryScores, Location Score or core scoring is implemented.
16. Frozen upstream packages and locked 3.4-4/3.4-5 semantics are preserved.
17. Dependency DAG remains approved/acyclic.
18. Adversarial tests cover public bypass paths.
19. Documentation matches runtime semantics.
20. Branch/PR are open for review and unmerged.
```

---

# 46. FINAL EXECUTION INSTRUCTION

Begin checkpoint 3.4-6 now.

Do not return a speculative design-only response.

Inspect actual GitHub source first, create the single checkpoint branch from the exact verified baseline, implement only Feature-Specific Normalization + Compatibility, run the required regressions/self-audit, open the PR, write the detailed `implementer.md` handoff on the coordination branch, and stop at:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

Do not merge.
Do not self-LOCK.
Do not start 3.4-7.

# END — FAZ 3.4 / CHECKPOINT 3.4-6 IMPLEMENTATION REQUEST
