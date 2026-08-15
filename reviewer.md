# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-4
CHECKPOINT_TITLE: Benchmark Measurement + Distribution Artifacts
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
CODE_BRANCH: faz3.4/cp3.4-4-benchmark-distribution
EXPECTED_BASE_SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
REVIEWED_HEAD_SHA: NONE
PR: NONE
```

---

# 1. COORDINATION PROTOCOL

This file is the canonical Reviewer → Implementer instruction channel for the SiteScore project.

The paired Implementer → Reviewer channel is:

```text
implementer.md
```

Both files live on the dedicated coordination branch:

```text
ops/reviewer-implementer-handoff
```

The coordination branch is intentionally separate from checkpoint code branches. Updating `reviewer.md` or `implementer.md` must therefore **not alter the checkpoint code HEAD SHA** being reviewed.

## File ownership

`reviewer.md`:
- written/updated only by the Reviewer chat under normal workflow;
- contains the current checkpoint implementation instruction, hardening instruction, READY_TO_LOCK decision, or post-lock next-step instruction.

`implementer.md`:
- written/updated only by the Implementer chat under normal workflow;
- contains the exact work performed, code branch HEAD SHA, PR, tests, self-audit, hardening resolutions, or LOCK transition result.

Neither chat should overwrite the other chat's file under normal workflow.

## User command model

The user intends to use only simple commands such as:

```text
devam
LOCK
```

### When Implementer receives `devam`

1. Fetch the latest `reviewer.md` from `ops/reviewer-implementer-handoff`.
2. Fetch the latest `implementer.md` for context.
3. Re-fetch the actual GitHub code branch/PR state.
4. Execute the action declared in `IMPLEMENTER_ACTION`.
5. Perform the work completely in the current turn.
6. Commit/push code changes to the checkpoint code branch when required.
7. Open/update the same checkpoint PR.
8. Replace `implementer.md` with a detailed current handoff report.
9. Do not self-LOCK unless the user explicitly sent `LOCK` and the lock preconditions below are satisfied.

### When Reviewer receives `devam`

1. Fetch the latest `implementer.md` from the coordination branch.
2. Fetch the latest `reviewer.md` to confirm current state.
3. Independently inspect the actual GitHub PR, changed files, full load-bearing source, dependencies, tests/CI where available, and exact code HEAD SHA.
4. Do not trust `implementer.md` as proof; it is a handoff report only.
5. Perform one comprehensive checkpoint-wide review.
6. Replace `reviewer.md` with either:
   - `HARDENING_REQUIRED` + one consolidated blocker set, or
   - `READY_TO_LOCK` + exact reviewed repository/PR/branch/full HEAD SHA.
7. Do not merge, tag, self-LOCK, or start the next checkpoint before explicit user LOCK.

### When Implementer receives `LOCK`

The `LOCK` command is valid only when the latest `reviewer.md` says:

```text
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
```

Before any merge/LOCK transition, the Implementer must:

1. Read both `reviewer.md` and `implementer.md`.
2. Fetch current PR metadata and current code branch HEAD.
3. Verify `REVIEWED_HEAD_SHA` in `reviewer.md` exactly equals the current PR HEAD SHA.
4. Verify the PR/base/checkpoint match the reviewer decision.
5. Verify no unresolved reviewer blocker is recorded.
6. Verify `CONTRACT_CHANGE_REQUIRED` is compatible with the reviewer decision.
7. Merge only the exact reviewed code HEAD, using expected-head-SHA protection when tooling supports it.
8. Do not start the next checkpoint.
9. Update `implementer.md` with a detailed `LOCKED` transition report including reviewed head, PR, merge SHA/main SHA, tests known at transition, and any pending tag/record state.

If the current code HEAD differs from `REVIEWED_HEAD_SHA`, **do not LOCK**. Report `LOCK_BLOCKED_REVIEW_STALE` in `implementer.md` and wait for Reviewer re-review.

### After a successful LOCK

On the next Reviewer `devam`:
- verify the merge/main state;
- update `reviewer.md` with the next checkpoint implementation prompt;
- record the new accepted main SHA as the next checkpoint baseline.

Then the next Implementer `devam` starts from that prompt.

---

# 2. CURRENT VERIFIED START STATE

At issuance of this instruction, GitHub was independently checked.

```text
Repository: metadoks/sitescore
Default branch: main
main SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
Working branch: faz3.4/cp3.4-4-benchmark-distribution
Working branch SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
Open 3.4-4 PR: none
```

This is a snapshot. Before implementation, re-fetch the branch. If legitimate work has appeared meanwhile, do not reset or force-push it; inspect and continue from actual current state.

Do not create a second 3.4-4 branch.

---

# 3. CURRENT TASK

Implement only:

```text
FAZ 3.4 — CHECKPOINT 3.4-4
Benchmark Measurement + Distribution Artifacts
```

The checkpoint must implement the structural bridge:

```text
CommercialFrame
        ↓
complete eligible benchmark-cell population
        ↓
exactly one measurement attempt per eligible cell
        ↓
explicit coverage accounting
        ↓
canonical compatibility / numeric-inclusion decision
        ↓
real-unit numeric benchmark observations
        ↓
BenchmarkDistributionArtifact
```

The checkpoint ends at **raw real-unit benchmark distributions**.

It must NOT implement ECDF, percentile rank, 0–100 normalization, competition opportunity inversion, feature scores, COMB-005, readiness, CategoryScores, core scoring, pipeline orchestration, or later checkpoint behavior.

---

# 4. FROZEN / LOCKED INPUTS

Preserve these existing states:

```text
sitescore-core        0.1.0 — FROZEN — historical 86/86 PASS
sitescore-data        0.1.0 — FROZEN — historical 361/361 PASS
sitescore-providers   0.1.0 — FAZ 3.3 FROZEN — historical 418/418 PASS
sitescore-spatial     FAZ 3.4-1 LOCKED — historical 180/180 PASS
sitescore-benchmarks  FAZ 3.4-2 LOCKED — historical 63/63 PASS
sitescore-metrics     FAZ 3.4-3 LOCKED — historical 67/67 PASS
```

Historical aggregate before 3.4-4:

```text
1175 PASS
```

The exact future aggregate may increase. Zero regressions matter; preserving exactly 1175 does not.

Primary implementation belongs in `sitescore-benchmarks` as an additive extension of the locked 3.4-2 frame semantics.

Do not change frozen/locked packages merely for convenience.

If correct implementation is impossible without changing a frozen/locked contract, return:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with the exact contract, missing capability, why an additive benchmark-side solution cannot work, affected paths, version/migration consequences, and minimal proposed change. Do not silently mutate frozen semantics.

---

# 5. PACKAGE OWNERSHIP / DAG

`sitescore-benchmarks` owns in 3.4-4:

```text
benchmark-cell measurement population
benchmark subject adaptation / frame-cell binding
measurement-attempt set completeness
coverage accounting
benchmark observation inclusion semantics
raw real-unit benchmark distribution artifacts
benchmark-level compatibility lineage
```

It does not own:

```text
provider-specific parsing/acquisition
shared metric formulas
core scoring
ECDF
feature normalization
COMB-005
readiness
application orchestration
```

`sitescore-metrics` remains authoritative for:

```text
MetricDefinition
MetricDerivationPolicy
MeasurementPrecisionPolicy
MeasurementSubject
MetricEvidence
DerivedMetricMeasurement
canonical metric registry
provider-neutral real-unit derivation semantics
```

Current `sitescore-benchmarks` baseline directly depends only on:

```text
sitescore-spatial==0.1.0
```

If 3.4-4 directly imports the locked metric package, explicitly add the exact internal dependency:

```text
sitescore-metrics==0.1.0
```

to benchmark package metadata/lock files as appropriate. Do not copy metric contracts to avoid declaring the dependency. Add no unrelated third-party dependency.

Required DAG must remain acyclic. In particular:

```text
sitescore-benchmarks -> sitescore-core       FORBIDDEN
sitescore-metrics -> sitescore-benchmarks    FORBIDDEN
sitescore-data -> sitescore-core             FORBIDDEN
sitescore-providers -> sitescore-core        FORBIDDEN
```

---

# 6. SOURCE TO INSPECT BEFORE IMPLEMENTING

Read actual repository source first, at minimum:

```text
sitescore-benchmarks/src/sitescore_benchmarks/contracts.py
sitescore-benchmarks/src/sitescore_benchmarks/builders.py
sitescore-benchmarks/src/sitescore_benchmarks/evaluation.py
sitescore-benchmarks/src/sitescore_benchmarks/hashing.py
sitescore-benchmarks/src/sitescore_benchmarks/validation.py
sitescore-benchmarks/src/sitescore_benchmarks/enums.py
sitescore-benchmarks/src/sitescore_benchmarks/__init__.py
sitescore-benchmarks/tests/
sitescore-benchmarks/docs/CHECKPOINT_3_4_2_COMMERCIAL_EQUAL_AREA_FRAME_FOUNDATION.md
sitescore-benchmarks/pyproject.toml
sitescore-benchmarks/requirements.lock

sitescore-metrics/src/sitescore_metrics/contracts.py
sitescore-metrics/src/sitescore_metrics/definitions.py
sitescore-metrics/src/sitescore_metrics/measurements.py
sitescore-metrics/src/sitescore_metrics/enums.py
sitescore-metrics/src/sitescore_metrics/__init__.py
sitescore-metrics/tests/
```

Inspect the actual public shape of:

```text
CommercialFrame
CommercialFrameCell
CommercialEligibilityResult
LatticeCellArtifact
MeasurementSubject
SubjectKind
MetricDefinition
MetricDerivationPolicy
MeasurementPrecisionPolicy
DerivedMetricMeasurement
MetricValue
DEFINITIONS
POLICIES
FULL_BINARY64
```

Use actual source names and constructor semantics; do not implement from remembered pseudocode alone.

---

# 7. PRIMARY COMPLETENESS INVARIANT

For one exact `CommercialFrame`, derive the canonical ELIGIBLE frame-cell population.

If eligible cells are:

```text
A, B, C
```

measurement attempts must represent exactly:

```text
A, B, C
```

once each.

Reject:

```text
A, B          # missing eligible C
A, B, C, C    # duplicate attempt
A, B, C, D    # foreign extra cell
```

Do not silently deduplicate.
Do not silently ignore foreign attempts.
Do not shrink the population to successful numeric measurements.

`frame eligibility` and `metric availability` are different axes.

An ELIGIBLE benchmark cell may have an UNKNOWN/MISSING/INELIGIBLE/UNCALIBRATED/UNRESOLVED/non-numeric metric measurement. The attempt must remain represented in coverage accounting.

Never convert unresolved/missing/unknown to zero.

---

# 8. REQUIRED SEMANTIC CONTRACT FAMILY

Implement a clear public semantic family equivalent to these responsibilities. Exact class/file names may follow existing package style.

## 8.1 Benchmark measurement policy

Versioned structural policy for behavior owned by 3.4-4.

Do not smuggle empirical constants such as minimum N, minimum coverage, cell size, CRS, road reduction, competition reduction, or scoring thresholds.

## 8.2 Benchmark-cell subject adaptation

Provide an explicit deterministic versioned mechanism mapping an actual `CommercialFrameCell` in an actual `CommercialFrame` to:

```text
MeasurementSubject(kind=BENCHMARK_CELL)
```

The subject must be derived from actual frame/cell semantics, not a detached caller-supplied string.

The representation must distinguish frame context where necessary. A lattice cell appearing in two different frames must not become falsely interchangeable if frame context is part of benchmark meaning.

Any additional metric evidence scope refs must remain coherent with actual attached evidence and cannot become detached assertions.

## 8.3 Benchmark cell measurement attempt

A canonical attempt must bind actual hardened objects, conceptually:

```text
actual frame context
actual CommercialFrameCell
actual DerivedMetricMeasurement
actual benchmark policy / subject-adapter semantics
```

Reject foreign frame/cell, subject mismatch, wrong metric family, wrong derivation policy, wrong precision, wrong unit, or detached lineage.

## 8.4 BenchmarkMeasurementSet semantic equivalent

Bind:

```text
actual CommercialFrame
one exact canonical metric semantic family
exactly one attempt for every eligible cell
benchmark policy
```

Reject missing, duplicate, foreign, cross-frame and metric-incompatible attempts.

## 8.5 Coverage accounting

Derive counts from actual contents, never caller-supplied arbitrary counts.

At minimum preserve:

```text
eligible_cell_count
attempt_count
numeric_included_count
non_numeric_or_excluded_count
```

with internally reconcilable arithmetic.

`attempt_count` and `numeric observation count` are not the same concept.

## 8.6 Numeric observation

Every numeric observation must preserve exact lineage to:

```text
exact benchmark cell
exact DerivedMetricMeasurement
exact canonical metric semantics
```

The numeric value must be derived from `DerivedMetricMeasurement.metric_value.value` and must not be separately caller-supplied as semantic truth.

No NaN/+Inf/-Inf path.

## 8.7 BenchmarkDistributionArtifact semantic equivalent

Represent:

```text
raw real-unit observations
complete coverage lineage
frame identity
metric definition/policy/precision/unit semantics
metric-specific compatibility lineage
```

No ECDF, rank, percentile, interpolation, inversion, or normalized score.

---

# 9. ACTUAL OBJECTS / ANTI-SELF-ASSERTION

Do not build canonical semantics from detached strings such as:

```text
frame_id = caller text
cell_id = caller text
measurement_id = caller text
COMPATIBLE = caller enum
INCLUDED = caller enum
```

when this package owns verification and actual objects are available.

Adversarial combinations must fail, including:

```text
cell A + subject B
frame A + cell from frame B
frame A + measurement whose benchmark subject is foreign
metric X distribution + metric Y measurement
matching-looking ID attached to foreign evidence
caller-supplied count/value inconsistent with actual objects
```

Strong states owned by this layer must be derived or strictly validated from actual evidence/policy.

---

# 10. CANONICAL METRIC BINDING

Metric key alone is insufficient.

Bind/verify the actual canonical identities of:

```text
MetricDefinition
MetricDerivationPolicy
MeasurementPrecisionPolicy
unit
```

The locked `sitescore-metrics` registry is authoritative.

A custom definition with `metric_key="household_income"` must not masquerade as canonical V1 household income if semantic definition/policy identity differs.

Current V1 measurement precision is:

```text
FULL_BINARY64
```

with no quantization.

Do not add arbitrary epsilon/rounding (`1e-6`, `round`, quantize) as benchmark semantics. ECDF tie precision is a different later concern.

---

# 11. CURRENT TEN-METRIC STATUS

Currently numeric pass-through candidates:

```text
household_income
walkable_reach_area_km2
transit_service_departure_equivalents_per_hour
parking_public_offstreet_capacity
parking_legal_curb_length_m
```

Currently structurally supported but unresolved:

```text
walkable_population
  population_allocation_policy_unresolved

target_population_density
  target_population_definition_unresolved

household_income_ratio
  household_income_denominator_policy_unresolved

competition_pressure
  competition_reduction_policy_unresolved

road_reachable_area_km2
  road_reduction_policy_unresolved
```

Unresolved metrics may have complete benchmark attempts while contributing zero numeric observations. This is valid.

Do not invent reductions merely to populate distributions.

---

# 12. NUMERIC INCLUSION

Attempt existence is independent from numeric inclusion.

A measurement must not become a numeric observation when it is, as applicable:

```text
value=None
non-finite
UNKNOWN
MISSING
INELIGIBLE
UNCALIBRATED where calibration is required
semantically incompatible
wrong canonical metric
wrong unit
wrong precision
```

Use the actual frozen MetricValue/metric-contract semantics rather than creating a conflicting parallel truth system.

---

# 13. METRIC-SPECIFIC COMPATIBILITY

## Transit

Preserve exact:

```text
transit_source_bundle_fingerprint
```

Do not allow incompatible transit source bundles to silently form one canonical comparable distribution.

The compatibility value must come from actual `DerivedMetricMeasurement` lineage; callers must not overwrite it in benchmark metadata.

Add adversarial cross-bundle regression coverage.

## Competition

Preserve:

```text
competition_measurement_definition_id
```

but keep `competition_pressure` non-numeric while scalar reduction is unresolved.

No competition opportunity inversion here.

## Road

Preserve:

```text
routing_profile_id
routing_profile_version
```

but keep road metric non-numeric while scalar reduction is unresolved.

Do not invent mean/median/max/nearest-scale/weighted-average semantics.

## Parking

Keep:

```text
parking_public_offstreet_capacity
parking_legal_curb_length_m
```

as separate metrics.

Preserve:

```text
unknown capacity != zero
NoMappedParking != NoParking
```

Do not combine road and parking. COMB-005 belongs later.

---

# 14. UNRESOLVED FRAME POLICIES

Current production frame foundation intentionally leaves some policies unresolved, including production equal-area CRS selection, cell resolution, boundary membership, commercial classification, and evidence applicability.

Do not manufacture production frame cells so 3.4-4 can have data.

Synthetic/private resolved test fixtures may exercise structural downstream behavior only when clearly isolated from production semantics.

No approved minimum N or coverage threshold exists. Do not invent one.

If the eligible population is empty, or all complete attempts are non-numeric, represent that state explicitly and deterministically without fake observations.

---

# 15. DETERMINISM / IDENTITY

For set-like collections:
- reject duplicates before canonical ordering;
- canonical input order/worker order must not affect identity;
- semantic changes must affect identity;
- timestamps, temp paths, worker indices, extraction directories, or other runtime noise must not affect semantic identity unless an existing frozen contract explicitly says otherwise.

Audit identity preimages for all new canonical artifacts.

Load-bearing identity fields include, as applicable:

```text
CommercialFrame identity
CommercialFrameCell identity
subject-adapter policy/version
MetricDefinition identity
MetricDerivationPolicy identity
MeasurementPrecisionPolicy identity
unit
DerivedMetricMeasurement.measurement_id
compatibility lineage
canonical attempt/observation membership
benchmark policy identity
```

Do not hash irrelevant metadata just because it exists.

---

# 16. STRICT SCOPE EXCLUSIONS

Do not implement in 3.4-4:

```text
mid-ECDF
P(d) formula
future tie equality policy
percentile lookup
interpolation
0–100 normalization
100*(1-P)
feature directionality
age fallback integration
road_parking_access_score
COMB-005
ScoringReadinessValidator
RealDataPipelineResult orchestration
CategoryScores
core.analyze()
```

Do not hide later behavior behind convenience APIs.

Do not invent new production constants such as sample thresholds, benchmark adequacy thresholds, cell size, CRS, overlap threshold, classification mapping, road/competition reduction weights, road/parking weights, or fallback scores.

---

# 17. REQUIRED ADVERSARIAL TEST COVERAGE

Add comprehensive benchmark-package regressions covering at least:

```text
eligible A/B/C + attempts A/B/C -> accepted
eligible A/B/C + attempts A/B -> reject
eligible A/B/C + attempts A/B/C/C -> reject
eligible A/B/C + attempts A/B/C/D -> reject
foreign frame attempt -> reject
cell A + benchmark subject B -> reject
correct deterministic subject adaptation -> pass
household-income set + walk-reach measurement -> reject
custom/altered metric definition with same key -> cannot masquerade as canonical
precision mismatch -> reject/non-comparable
wrong-unit bypass -> impossible/reject
unresolved eligible attempt retained in coverage but excluded from numeric observations
missing/None never becomes zero
observation value equals authoritative measurement value
no arbitrary observation-value path
no NaN/Inf path
transit same-bundle -> compatible
transit cross-bundle -> reject/non-comparable
competition unresolved remains non-numeric with canonical reason
road unresolved remains non-numeric with routing-profile lineage
parking capacity and curb length remain independent metric distributions
empty eligible population -> deterministic, no fabricated observations
all attempts non-numeric -> complete coverage, zero fabricated numeric values
attempt input order permutation -> same set/distribution identity
semantic identity sensitivity -> real semantic change changes identity
runtime noise does not change semantic identity
no ECDF/percentile/normalization public result
no core import / no dependency cycle
all existing 3.4-2 benchmark tests still pass
```

Do not rely on test count alone; exercise actual bypass attempts.

---

# 18. REGRESSION / IMPORT AUDIT

Run at minimum:

```text
sitescore-benchmarks full suite
sitescore-metrics full suite
```

Prefer all six package suites where environment supports them.

Report each suite independently. If not run, say why; never report an unexecuted suite as PASS.

Explicitly audit:

```text
sitescore-benchmarks imports sitescore-core = 0
sitescore-metrics imports sitescore-benchmarks = 0
sitescore-data imports sitescore-core = 0
sitescore-providers imports sitescore-core = 0
no circular dependency introduced
```

---

# 19. DOCUMENTATION / EXPORTS / HYGIENE

Create/update a durable checkpoint record, recommended:

```text
sitescore-benchmarks/docs/CHECKPOINT_3_4_4_BENCHMARK_MEASUREMENT_DISTRIBUTION.md
```

Document:

```text
scope
new public contracts
identity semantics
eligible-cell completeness
attempt vs observation distinction
coverage accounting
metric compatibility
numeric inclusion
transit compatibility
competition/road unresolved preservation
empty/zero-observation behavior
unresolved empirical decisions
strict no-ECDF boundary
dependency changes
tests
CONTRACT_CHANGE_REQUIRED
```

Do not call the checkpoint LOCKED before user-authorized lock transition.

Update README/public exports only as required by actual public API changes.

Do not commit `.pytest_cache`, `__pycache__`, `*.pyc`, build/dist/temp/editor artifacts, credentials or secrets.

---

# 20. REQUIRED SELF-AUDIT BEFORE HANDOFF

Before writing `implementer.md`, answer through code/tests/source inspection:

```text
Can a foreign cell enter the measurement set?
Can a subject be detached from the actual frame cell?
Can a custom same-key metric masquerade as canonical?
Can arbitrary observation values/counts be asserted?
Can an eligible cell disappear?
Can duplicates be silently deduplicated?
Can foreign extras be ignored?
Can None/unresolved become zero/numeric?
Are definition/policy/precision/unit bound?
Is transit bundle compatibility preserved?
Are competition/road compatibility semantics preserved while reductions remain unresolved?
Does input order alter set-like identity?
Does runtime noise alter semantic identity?
Did any ECDF/normalization leak in?
Did any empirical constant leak in?
Did any frozen package semantics change?
Is the dependency graph still acyclic?
```

Try to break the public API yourself before declaring completion.

---

# 21. GIT / PR WORKFLOW

Use the existing code branch only:

```text
faz3.4/cp3.4-4-benchmark-distribution
```

Rules:

```text
no second 3.4-4 branch
no feature work directly on main
no force-push by default
no main history rewrite
no auto-merge
same branch for hardening
same PR for hardening
```

Commit intentionally and open one PR targeting `main`.

Do not merge it during normal `devam` implementation work.

---

# 22. IMPLEMENTER.MD REQUIRED RETURN FORMAT

At completion, replace `implementer.md` on the coordination branch with a detailed report containing at least:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
REPOSITORY: metadoks/sitescore
CHECKPOINT: FAZ 3.4-4
BASE_SHA: <full SHA>
CODE_BRANCH: faz3.4/cp3.4-4-benchmark-distribution
CODE_HEAD_SHA: <full SHA>
PR: #<number>
CONTRACT_CHANGE_REQUIRED: 0 or 1
```

Then include sections:

```text
Changed files
Implemented contracts
Detailed behavior
Completeness guarantees
Subject/frame lineage
Metric compatibility
Coverage accounting
Transit handling
Competition/road unresolved handling
Dependency changes
Tests by package
Import/DAG audit
Known unresolved/calibration-gated items preserved
Self-audit
Any reviewer attention points
```

The report must be detailed enough for reviewer orientation but must not claim reviewer verification or LOCK.

If implementation is blocked by a genuine frozen-contract deficiency, set:

```text
IMPLEMENTER_STATE: CONTRACT_CHANGE_REQUIRED
CONTRACT_CHANGE_REQUIRED: 1
```

and describe the exact blocker instead of silently changing the frozen contract.

---

# 23. SUCCESS CONDITION

Implementation is ready for independent review only when:

```text
1. Every eligible frame cell has exactly one attempt.
2. Missing/unresolved attempts remain visible in coverage.
3. Numeric observations derive only from valid compatible canonical measurements.
4. Observation values derive from authoritative metric values.
5. Frame/cell/subject lineage cannot be detached through public construction.
6. Definition/policy/precision/unit semantics are bound, not merely metric key.
7. Transit source-bundle compatibility cannot be bypassed.
8. Competition and road unresolved reductions remain unresolved.
9. No empirical threshold/reduction is invented.
10. No ECDF/percentile/normalization is implemented.
11. Locked 3.4-2 behavior remains passing.
12. No dependency cycle/core leakage is introduced.
13. Documentation matches source.
14. Adversarial bypass tests exist.
15. Code is committed and one PR is open, not merged.
16. `implementer.md` accurately records the exact current code HEAD and PR.
```

---

# 24. EXECUTE ON NEXT `devam`

When the user sends `devam` to the Implementer chat, do not ask for this prompt to be pasted or uploaded.

Read this file directly from:

```text
Repository: metadoks/sitescore
Branch: ops/reviewer-implementer-handoff
Path: reviewer.md
```

Then execute `IMPLEMENTER_ACTION: IMPLEMENT` completely, write the code to the existing checkpoint branch, open/update the PR, and write the final detailed handoff to `implementer.md` on the coordination branch.

Do not start 3.4-5.
Do not self-LOCK.
