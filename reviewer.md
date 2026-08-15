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
REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
CODE_BRANCH: faz3.4/cp3.4-4-benchmark-distribution
EXPECTED_BASE_SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
REVIEWED_HEAD_SHA: 09657fb6a35e79725fac372f7dc1d9a40ebb938c
PR: #1
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
```

---

# 1. REVIEW DECISION

```text
FAZ 3.4 — CHECKPOINT 3.4-4
Decision: HARDENING REQUIRED
Reviewed repository: metadoks/sitescore
Reviewed PR: #1
Reviewed base: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
Reviewed head: 09657fb6a35e79725fac372f7dc1d9a40ebb938c
```

Do **not** start checkpoint 3.4-5.

Do **not** merge PR #1.

Do **not** create a new branch or PR.

Apply all hardening on the existing branch and PR:

```text
faz3.4/cp3.4-4-benchmark-distribution
PR #1
```

Return a new full HEAD SHA in `implementer.md` when complete.

---

# 2. VERIFIED CLEAN SURFACES

The reviewer independently inspected the actual GitHub PR/diff and load-bearing source at the exact reviewed HEAD.

The following checkpoint domains are structurally sound at this revision and should **not** be redesigned during hardening unless a fix directly requires a minimal sibling change:

- `CommercialFrame.eligible_cell_ids` is used as the canonical attempt population.
- Missing eligible attempts are rejected.
- Duplicate cell attempts are rejected rather than silently deduplicated.
- Extra/foreign attempt cells are rejected.
- Frame/cell subject adaptation binds actual frame ID, frame-cell ID, lattice-cell ID and evidence-derived scope.
- A measurement subject detached from the actual frame/cell/evidence is rejected.
- Canonical metric definition and derivation-policy identities are checked against the locked `sitescore-metrics` registry.
- Measurement precision-policy identity and unit are bound at the measurement-set boundary.
- Attempts remain distinct from numeric observations; unresolved/missing attempts remain represented in coverage.
- Observation value and unit are derived from the authoritative `DerivedMetricMeasurement.metric_value`; there is no independent caller numeric payload.
- Coverage counts are derived from the actual measurement set and reconcile to the full eligible population.
- Transit `transit_source_bundle_fingerprint` conflicts are surfaced and cannot silently blend numeric observations.
- Competition preserves `competition_measurement_definition_id` and remains non-numeric while reduction is unresolved.
- Road preserves routing profile ID/version and remains non-numeric while reduction is unresolved.
- Parking capacity and curb-length distributions remain separate.
- Empty eligible populations and all-non-numeric populations are explicit rather than fabricated as zero.
- Input-order canonicalization occurs after duplicate/completeness validation.
- No ECDF, percentile, 0–100 normalization, competition inversion, COMB-005, readiness, CategoryScores or core scoring leaked into 3.4-4.
- Only `sitescore-benchmarks` changed in PR #1; frozen upstream source trees are unchanged.
- `sitescore-benchmarks` now explicitly pins `sitescore-metrics==0.1.0`; the package DAG remains acyclic.

These findings are not permission to LOCK; the blockers below are production-semantic blockers.

---

# 3. TEST / CI EVIDENCE VERIFIED

GitHub Actions contains a successful `cp344-validation` run for commit:

```text
a4c53f935f2b3cf6e889eb4c0cf57cd9fee5d03c
```

The reviewer verified by commit comparison that the only change from that validation commit to reviewed HEAD `09657fb6...` is removal of the temporary validation workflow file:

```text
.github/workflows/cp344-validation.yml
```

Therefore the code/test/doc content at the reviewed HEAD is the same as the latest successful validation commit, apart from removal of the workflow itself.

GitHub also shows a prior successful validation run at `2510ad3d6b55732dd738e0f5cdedd87b44dd4c09`; the later commit `a4c53f...` changed checkpoint documentation only before the workflow removal.

Reported suite baseline in PR/docs:

```text
sitescore-benchmarks   99/99 PASS
sitescore-metrics      67/67 PASS
sitescore-spatial     180/180 PASS
sitescore-providers   418/418 PASS
sitescore-data        361/361 PASS
sitescore-core         86/86 PASS
aggregate            1211/1211 PASS
```

The visible Actions job and each package test step completed successfully. These green tests do not cover the two public-path gaps below.

---

# 4. BLOCKER BENCH-H001 — UNCALIBRATED NUMERIC MEASUREMENTS CAN ENTER THE DISTRIBUTION

## Problem

The current numeric-inclusion implementation in:

```text
sitescore-benchmarks/src/sitescore_benchmarks/distribution.py
_numeric_exclusion_reason(...)
```

checks:

```text
value is not None
availability == available
score_eligibility == eligible
finite(value)
```

but it does **not** check:

```text
calibration_state
```

The current policy string also freezes the incomplete rule as:

```text
AVAILABLE_SCORE_ELIGIBLE_FINITE_VALUE
```

## Why this is a real blocker

The frozen `MetricValue` contract deliberately keeps:

```text
availability
score_eligibility
calibration_state
```

as independent axes.

`MetricValue` permits a finite numeric metric to be:

```text
availability = AVAILABLE
score_eligibility = ELIGIBLE
calibration_state = UNCALIBRATED
```

because there is no contract invariant forcing `ELIGIBLE` to imply `CALIBRATED`.

The locked `DerivedMetricMeasurement` pass-through path also accepts the authoritative provider `MetricValue` as-is when definition/policy/evidence coherence is valid. It does not add a calibration requirement for resolved pass-through metrics.

Therefore a real public construction path exists where an AVAILABLE + ELIGIBLE + UNCALIBRATED numeric provider metric becomes:

```text
numeric_candidate_attempt
→ numeric_included_attempt
→ BenchmarkObservation
→ BenchmarkDistributionArtifact state AVAILABLE
```

This directly violates the authoritative 3.4-4 rule that an `UNCALIBRATED` attempt must not become a numeric observation unless the canonical metric contract explicitly allows that exception. No such exception exists for these benchmark metrics.

This is not a theoretical strengthening; it is a currently reachable false numeric-inclusion path.

## Required correction

1. Make numeric inclusion explicitly calibration-aware.
2. For the current canonical V1 benchmark-distribution rule, only permit the approved calibration state for numeric inclusion. Under the current architecture this is expected to be:

```text
CalibrationState.CALIBRATED
```

unless an already-frozen metric-specific exception can be demonstrated from actual contracts. Do not invent one.
3. Preserve the attempt in coverage when numeric inclusion is rejected for calibration.
4. Derive a deterministic exclusion reason for calibration mismatch, e.g. a canonical reason equivalent to:

```text
calibration_state_uncalibrated
```

Use existing enum values/canonical style; do not invent score fallback behavior.
5. Update `BenchmarkMeasurementDistributionPolicy.numeric_inclusion_rule` so its semantic identity accurately reflects the real rule. Do not keep a policy identity/string that claims a weaker rule while runtime enforces a stronger one.
6. Update checkpoint documentation and PR summary accordingly.

## Required regression tests

Add at minimum:

### H001-A
Construct an actual canonical pass-through measurement whose authoritative `MetricValue` is:

```text
AVAILABLE
FULL or DEGRADED
ELIGIBLE
UNCALIBRATED
finite numeric value
```

and prove:

```text
attempt remains present
attempt_count remains complete
numeric_candidate/included does not include it
no BenchmarkObservation is emitted for it
coverage exclusion reason records calibration mismatch
```

### H001-B
Mixed complete population:

```text
2 CALIBRATED numeric attempts
1 UNCALIBRATED numeric attempt
```

must produce:

```text
3 attempts
2 numeric observations
1 excluded attempt
```

with no missing→zero or silent omission.

### H001-C
Confirm a valid CALIBRATED numeric pass-through measurement remains included.

---

# 5. BLOCKER BENCH-H002 — COMPATIBILITY IDENTITY OMITS MEASUREMENT METHOD SEMANTICS

## Problem

`BenchmarkMetricCompatibility.identity_id` currently binds:

```text
metric_definition_id
metric_derivation_policy_id
measurement_precision_policy_id
unit
source_bundle_compatibility
```

but it omits:

```text
DerivedMetricMeasurement.method_version
```

The authoritative 3.4-4 compatibility contract explicitly requires compatibility to consider:

```text
metric definition
derivation policy
measurement precision
unit
method/source semantics
```

The special compatibility payload correctly preserves transit bundle, competition measurement-definition and road routing-profile semantics, but generic measurement method semantics are not included.

## Why this is a real blocker

The locked provider-derived pass-through path intentionally accepts the authoritative evidence `MetricValue.method_version` and carries it into `DerivedMetricMeasurement.method_version`.

For pass-through metrics such as `household_income`, `walkable_reach_area_km2` or parking metrics, `source_bundle_compatibility` may be empty.

Therefore two valid canonical measurements can have:

```text
same MetricDefinition
same MetricDerivationPolicy
same MeasurementPrecisionPolicy
same unit
same source_bundle_compatibility = ()
DIFFERENT method_version
```

and the current benchmark layer gives them the same `BenchmarkMetricCompatibility.identity_id`.

A complete measurement set can consequently combine numeric observations produced under different measurement methods while reporting one compatible distribution.

The measurement IDs/distribution IDs may still differ because the full measurements are hashed elsewhere, but that does **not** fix the comparability error: the compatibility gate itself treats semantically different measurement methods as equal and allows them to coexist as directly comparable observations.

This violates the frozen method/source compatibility requirement.

## Required correction

1. Bind actual canonical method semantics into `BenchmarkMetricCompatibility`.
2. At minimum include the actual:

```text
measurement.method_version
```

in the compatibility semantic record / identity.
3. Continue preserving the existing metric-specific `source_bundle_compatibility` tuple.
4. Do **not** require equality of per-cell `source_refs` merely to satisfy this blocker; source references are provenance and can legitimately differ by benchmark cell. The required fix is semantic method compatibility plus the already-approved metric-specific source/bundle compatibility dimensions.
5. Ensure mixed `method_version` values create a compatibility conflict rather than one blended numeric distribution.
6. Ensure the compatibility property/artifact exposes enough information for later site-vs-benchmark comparison to know the method semantics, not merely hide it inside a hash.
7. Update checkpoint documentation and PR summary to state that method semantics are compatibility-bearing.

## Required regression tests

Add at minimum:

### H002-A
Create a complete numeric pass-through population with identical metric definition/policy/precision/unit but two different actual `method_version` values.

Required result:

```text
has_compatibility_conflict = True
numeric observations are not silently blended
state = INCOMPATIBLE_MEASUREMENT_LINEAGE
```

### H002-B
Same method version across the complete population remains compatible.

### H002-C
Changing only `method_version` changes `BenchmarkMetricCompatibility.identity_id`.

### H002-D
Existing transit source-bundle compatibility behavior must continue to pass after adding method semantics.

---

# 6. SIBLING AUDIT REQUIREMENTS DURING FIX

While fixing H001/H002, perform a focused sibling audit of the same surfaces. Specifically verify that the fix does not introduce:

- caller-supplied calibration or compatibility self-assertion;
- a detached method-version parameter that can disagree with the actual `DerivedMetricMeasurement`;
- equality based only on metric key;
- source-ref equality that incorrectly makes every benchmark cell incompatible;
- silent exclusion of attempts from coverage;
- numeric zero substitution;
- arbitrary epsilon/rounding/quantization;
- ECDF/percentile/normalization leakage;
- new empirical minimum-N or coverage thresholds;
- frozen package edits;
- dependency-cycle changes.

Method/calibration semantics must be derived from the actual nested measurement objects.

---

# 7. SCOPE / FROZEN BOUNDARIES

Hardening scope is **only** BENCH-H001 and BENCH-H002 plus direct regression/doc updates and a focused sibling audit.

Do not reopen locked 3.4-1, 3.4-2 or 3.4-3 architecture.

Do not modify:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
```

unless a newly demonstrated impossibility genuinely requires `CONTRACT_CHANGE_REQUIRED = 1`. The current review finds no such necessity; both blockers are solvable additively inside `sitescore-benchmarks`.

Expected:

```text
CONTRACT_CHANGE_REQUIRED = 0
```

Do not implement 3.4-5 behavior.

---

# 8. REQUIRED TEST EXECUTION AFTER HARDENING

Run at minimum:

```text
sitescore-benchmarks full suite
sitescore-metrics full suite
```

Prefer the complete six-package regression again:

```text
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

If using a temporary GitHub Actions workflow again, it must not remain in the final checkpoint diff unless intentionally approved as separate infrastructure scope.

Report exactly what was run and what was not run.

---

# 9. REQUIRED `implementer.md` RETURN

When hardening is complete, replace `implementer.md` on:

```text
ops/reviewer-implementer-handoff
```

with:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CHECKPOINT: FAZ 3.4-4
BASE_SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
CODE_BRANCH: faz3.4/cp3.4-4-benchmark-distribution
OLD_REVIEWED_HEAD_SHA: 09657fb6a35e79725fac372f7dc1d9a40ebb938c
CODE_HEAD_SHA: <new full SHA>
PR: #1
CONTRACT_CHANGE_REQUIRED: 0 or 1
```

Then report, blocker by blocker:

```text
BENCH-H001: RESOLVED / NOT RESOLVED
BENCH-H002: RESOLVED / NOT RESOLVED
```

For each resolved blocker, state:

- exact changed files;
- exact code behavior;
- exact new regression tests;
- test results;
- documentation update;
- any sibling-audit findings.

Also include:

- current PR HEAD SHA;
- changed-file summary for the hardening delta;
- dependency audit;
- scope audit;
- full test/CI evidence;
- confirmation that no next-checkpoint work began.

Do not claim `READY_TO_LOCK` or `LOCKED`.

---

# 10. IMPLEMENTER EXECUTION RULE

On the user's next `devam` command:

1. Read this latest `reviewer.md`.
2. Re-fetch PR #1 and current branch HEAD.
3. Confirm the reviewed old HEAD is `09657fb6a35e79725fac372f7dc1d9a40ebb938c` or identify any unexpected intervening code change before editing.
4. Fix BENCH-H001 and BENCH-H002 on the same code branch.
5. Add the required regressions.
6. Run tests/self-audit.
7. Update PR #1; do not merge it.
8. Update `implementer.md` on the coordination branch.
9. Stop in `READY_FOR_REVIEW` state.

# END — FAZ 3.4-4 CONSOLIDATED HARDENING REVIEW
