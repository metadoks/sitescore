# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-5
CHECKPOINT_TITLE: Mid-ECDF + Numeric / Normalization Foundation
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
CODE_BRANCH: faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
REVIEWED_HEAD_SHA: NONE
PR: NONE
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
```

---

# 1. PREVIOUS CHECKPOINT LOCK VERIFICATION

FAZ 3.4-4 is now accepted and merged.

Reviewer independently verified:

```text
PR #1 state: closed
PR #1 merged: true
reviewed branch HEAD: 9fa9aff25d64de6176d051438828e55e7ba7a99a
merge/main SHA: 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
```

GitHub `main` currently points to:

```text
989b719d84a4fa01d40c0a2d342cdeff9197c3e7
```

This merge SHA is the authoritative baseline for checkpoint 3.4-5.

Current repository branch listing contains no existing 3.4-5 branch at publication time. Therefore create exactly one new checkpoint branch from current `main`:

```text
faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
```

If GitHub state has changed by the time this instruction is read, re-fetch first. Do not reset legitimate concurrent work and do not create a duplicate checkpoint branch.

---

# 2. CHECKPOINT PURPOSE

Implement only:

```text
FAZ 3.4 — CHECKPOINT 3.4-5
Mid-ECDF + Numeric / Normalization Foundation
```

The checkpoint establishes the generic, deterministic numeric/statistical foundation immediately after the locked raw benchmark distribution artifact.

Canonical chain after this checkpoint:

```text
BenchmarkDistributionArtifact
→ canonical finite numeric sample semantics
→ explicit tie-equality policy
→ generic mid-ECDF evaluation
→ percentile in [0,1]
```

This checkpoint does **not** yet convert percentile to a feature-specific 0–100 score.

This checkpoint does **not** yet implement metric/site compatibility orchestration, competition-opportunity inversion, feature directionality, age fallback, COMB-005, readiness, CategoryScores, Location Score, or `core.analyze()`.

Those belong to later checkpoints.

---

# 3. FROZEN STRUCTURAL MATHEMATICS

The generic mid-ECDF definition is frozen:

```text
P(d) = (# observations strictly below d + 0.5 × # observations equal to d) / N
```

where:

```text
N = number of canonical numeric benchmark observations
```

Required properties:

```text
all observations tied at d → P(d) = 0.5
no interpolation
step-function semantics
exact tie counting under one explicit V1 tie policy
permutation/input order is non-semantic
```

Do not replace this formula with:

```text
rank / N
(rank - 1) / (N - 1)
linear interpolation
quantile interpolation
percentile-of-score variants from scipy/pandas
average of arbitrary percentile conventions
```

No library convention may silently redefine the frozen formula.

---

# 4. ENDPOINT SEMANTICS — EXPLICIT

The mathematical endpoint behavior follows directly from the frozen formula.

For non-empty sample `S`:

```text
d < min(S)  → P(d) = 0
d > max(S)  → P(d) = 1
```

For a query equal to an observed endpoint, do **not** forcibly clamp it to 0 or 1.

Example with one minimum observation and N observations total:

```text
d == min(S)
P(d) = 0.5 / N
```

For one maximum observation:

```text
d == max(S)
P(d) = (N - 1 + 0.5) / N
```

Tied endpoint observations use the same general formula.

Do not add special endpoint overrides.

---

# 5. NO INTERPOLATION

Mid-ECDF is a step function.

Example:

```text
sample = [1, 3]
query = 2
#below = 1
#equal = 0
N = 2
P(2) = 0.5
```

There is no numerical interpolation between 1 and 3.

Do not use percentile/quantile interpolation modes.

---

# 6. TIE-EQUALITY POLICY — MUST BE EXPLICIT AND SEPARATE

Tie equality is a distinct numeric/statistical policy.

It must **not** be conflated with:

```text
GeometryPrecisionPolicy
MeasurementPrecisionPolicy / FULL_BINARY64
future feature-normalization policies
```

Create an explicit versioned V1 tie/comparison policy or equivalent structural contract.

There is currently no approved empirical epsilon or rounding precision.

Therefore V1 must not invent:

```text
1e-6
1e-9
round(x, n)
Decimal quantization scale
ULP distance threshold
relative/absolute tolerance
```

Unless an already-frozen repository contract explicitly supplies one, use exact canonical numeric equality semantics for V1.

Important: exact equality is a structural no-tolerance rule, not permission to confuse representation identity with numeric equality.

The canonical numeric layer must make equality/order semantics deterministic for valid Python numeric inputs and must explicitly consider at least:

```text
1 and 1.0
-0.0 and 0.0
finite int/float values
```

Values that are numerically equal under the approved V1 comparison semantics must count as ties and must not receive divergent identity merely because of incidental Python representation differences.

Very close but non-equal finite values must remain distinct; do not merge them with an epsilon.

---

# 7. NUMERIC DOMAIN / CANONICALIZATION

The ECDF foundation must accept only legitimate finite real numeric values.

Required behavior:

```text
finite int/float → supported
bool → reject
NaN → reject
+Inf / -Inf → reject
None → reject as numeric value
```

Do not silently coerce invalid values to zero.

Do not silently drop invalid values from a sample and continue as though coverage were complete.

If building from a locked `BenchmarkDistributionArtifact`, consume only its already-authoritative `BenchmarkObservation` population; do not reconstruct numbers from excluded attempts.

Do not deduplicate equal numeric observations. Duplicate equal values are legitimate observations and are exactly what tie counting needs.

---

# 8. EMPTY SAMPLE / UNAVAILABLE ECDF

The formula is undefined for `N = 0`.

Do not fabricate:

```text
P = 0
P = 0.5
P = 1
```

for an empty sample.

Represent empty/unavailable evaluation explicitly through a typed state/result or deterministically reject evaluation before division, following existing package style.

The design must preserve the distinction:

```text
no numeric benchmark observations
!=
percentile 0
!=
percentile 0.5
!=
percentile 1
```

A 3.4-4 artifact in `EMPTY_ELIGIBLE_POPULATION`, `NO_NUMERIC_OBSERVATIONS`, or incompatible lineage with no usable observations must not magically yield a percentile.

---

# 9. GENERIC PERCENTILE OUTPUT

When evaluation is available, output must be a generic percentile/probability:

```text
0.0 <= P(d) <= 1.0
```

Do not multiply by 100 in this checkpoint.

Do not call the result:

```text
score
opportunity_score
access_score
competition_score
```

Prefer terminology such as:

```text
mid_ecdf
percentile
probability
rank_fraction
```

consistent with actual semantics.

The generic result has no directionality.

---

# 10. FEATURE DIRECTIONALITY IS OUT OF SCOPE

Do not implement:

```text
100 * P
100 * (1 - P)
competition opportunity inversion
higher-is-better mapping
lower-is-better mapping
feature-specific normalization
```

Checkpoint 3.4-6 owns feature-specific normalization + compatibility.

In particular, although future competition opportunity uses:

```text
100 * (1 - P)
```

that formula must **not** appear as operational 3.4-5 logic.

3.4-5 returns generic statistical position only.

---

# 11. PACKAGE OWNERSHIP

Primary implementation should remain additive within:

```text
sitescore-benchmarks
```

because this checkpoint operates immediately on the locked benchmark distribution/statistical layer.

Do not create `sitescore-pipeline`, `sitescore-app`, or a new generic statistics package for this checkpoint.

Do not modify frozen upstream package semantics merely for convenience.

Expected package dependency DAG must remain acyclic.

No `sitescore-core` dependency is allowed.

No later package ownership should be invented prematurely.

---

# 12. LOCKED 3.4-4 INPUT CONTRACT

Treat the merged 3.4-4 implementation at main SHA:

```text
989b719d84a4fa01d40c0a2d342cdeff9197c3e7
```

as locked input.

Important 3.4-4 semantics that must remain preserved:

- exact eligible-cell measurement-attempt completeness;
- numeric observation inclusion requires AVAILABLE + ELIGIBLE + CALIBRATED + finite;
- uncalibrated/missing/unresolved attempts remain coverage facts but not observations;
- benchmark observations carry authoritative real-unit values;
- incompatible method/source-bundle populations do not emit one falsely comparable numeric observation set;
- metric definition/policy/precision/unit/method/source-bundle lineage remains available;
- no ECDF existed in 3.4-4.

Do not weaken those contracts.

---

# 13. RECOMMENDED CONTRACT SURFACE

Use the actual repository style and inspect source before deciding names.

A reasonable semantic family may include equivalents of:

```text
NumericComparisonPolicy / EcdfTiePolicy
MidEcdfPolicy
CanonicalNumericSample or adapter from BenchmarkDistributionArtifact
MidEcdfEvaluation / MidEcdfResult
build/evaluate helpers
```

Exact names are not frozen by this prompt.

What **is** frozen is behavior.

Avoid unnecessary framework abstraction.

Do not build a generic statistics platform.

---

# 14. STATISTICAL SAMPLE IDENTITY

If introducing a canonical sample artifact, its identity must bind the semantic observation population and numeric policy.

Requirements:

- order of a logically set/multiset population must be non-semantic;
- multiplicity **is** semantic: `[1,1,2]` is not equivalent to `[1,2]`;
- values equal under V1 tie semantics must canonicalize consistently;
- invalid numerics cannot enter identity;
- generated timestamps, worker order, filesystem paths and temporary execution data are non-semantic;
- if the sample is derived from `BenchmarkDistributionArtifact`, preserve enough actual artifact lineage to prevent unrelated distributions with coincidentally identical numeric values from collapsing to the same domain artifact identity, unless the object is deliberately a pure numeric helper and clearly separated from domain artifact identity.

Do not accidentally deduplicate ties by converting the observation collection to a `set`.

---

# 15. MID-ECDF RESULT IDENTITY

A canonical domain ECDF result, if persisted/identified, should bind as applicable:

```text
sample/distribution identity
ECDF policy identity
tie/comparison policy identity
canonical query numeric value
N
below count
equal count
result P(d)
state/reason when unavailable
```

Do not trust caller-supplied `below_count`, `equal_count`, `N`, or percentile.

Derive them from actual canonical sample contents.

---

# 16. DETERMINISM

The following must not affect semantics:

```text
input order
worker order
dictionary ordering
timestamps
filesystem paths
```

The following must affect semantics:

```text
numeric multiplicity
actual numeric values
query value
ECDF/tie policy identity
underlying benchmark distribution identity where domain-bound
```

Repeated evaluation of equivalent inputs must produce the same result/identity.

---

# 17. REQUIRED ADVERSARIAL / MATHEMATICAL TEST MATRIX

Add focused tests at minimum for the following.

## ECDF-001 — basic unique sample

```text
sample = [1,2,3]
query = 2
below = 1
equal = 1
N = 3
P = 0.5
```

## ECDF-002 — tied middle value

```text
sample = [1,2,2,2,3]
query = 2
below = 1
equal = 3
N = 5
P = 0.5
```

## ECDF-003 — all equal

For any N > 0 where every observation equals query:

```text
P = 0.5
```

## ECDF-004 — below minimum

```text
P = 0
```

## ECDF-005 — above maximum

```text
P = 1
```

## ECDF-006 — observed minimum

Prove formula-derived midpoint behavior; do not clamp to zero.

## ECDF-007 — observed maximum

Prove formula-derived midpoint behavior; do not clamp to one.

## ECDF-008 — no interpolation

```text
sample = [1,3]
query = 2
P = 0.5
```

and prove no interpolation-specific logic exists.

## ECDF-009 — duplicate multiplicity preserved

Prove `[1,1,2]` is not treated as `[1,2]`.

## ECDF-010 — input permutation determinism

Different input order → same canonical result/identity.

## ECDF-011 — exact equality, no epsilon

Use two close but unequal finite values and prove they are not ties.

## ECDF-012 — numeric-equivalent representations

Prove V1 handles representation-equivalent numeric values consistently, including as applicable:

```text
1 vs 1.0
-0.0 vs 0.0
```

## ECDF-013 — bool rejected

No `True == 1` leakage into numeric observations.

## ECDF-014 — NaN/Inf rejected

No non-finite sample/query values.

## ECDF-015 — empty sample

No fabricated percentile.

## ECDF-016 — 3.4-4 no-observation artifact

A `NO_NUMERIC_OBSERVATIONS` / empty artifact cannot yield an available ECDF result.

## ECDF-017 — incompatible 3.4-4 distribution

No compatibility-conflicted distribution may be silently treated as a usable numeric benchmark sample.

## ECDF-018 — percentile bounds

Available output always satisfies:

```text
0 <= P <= 1
```

## ECDF-019 — counts are derived

No caller-supplied counts/percentile path.

## ECDF-020 — no feature-score leakage

No 0–100 normalization, directionality, competition inversion, readiness or core scoring APIs appear.

---

# 18. NUMERIC PRECISION AUDIT

Explicitly document the difference among:

```text
GeometryPrecisionPolicy
MeasurementPrecisionPolicy
ECDF tie/comparison policy
```

They are not aliases.

Do not reuse `FULL_BINARY64.identity_id` as if it automatically defines tie equality unless the implementation explicitly and correctly derives a separate ECDF comparison policy from approved semantics.

There must be no arbitrary epsilon.

---

# 19. NO EMPIRICAL ADEQUACY THRESHOLD

3.4-5 must not invent:

```text
minimum N
minimum coverage ratio
minimum unique values
variance requirement
sample adequacy threshold
```

A non-empty structurally valid numeric sample can be mathematically evaluated by mid-ECDF even if empirical adequacy for production scoring remains unresolved.

Structural evaluability != empirical adequacy.

Keep that distinction explicit in docs.

---

# 20. NO SILENT RENORMALIZATION / DROPPING

Do not silently remove numeric observations because:

```text
value is duplicated
value is extreme
variance is zero
sample is small
```

All canonical 3.4-4 observations in the usable distribution participate exactly according to multiplicity.

Do not trim/winsorize/outlier-filter.

No production clipping.

---

# 21. TEST / REGRESSION EXPECTATION

Last verified locked aggregate after 3.4-4 hardening:

```text
sitescore-benchmarks  108/108 PASS
sitescore-metrics       67/67 PASS
sitescore-spatial      180/180 PASS
sitescore-providers    418/418 PASS
sitescore-data         361/361 PASS
sitescore-core           86/86 PASS
aggregate             1220/1220 PASS
```

New 3.4-5 tests should increase the benchmark test count.

Run at minimum:

```text
sitescore-benchmarks full suite
```

Prefer full six-package regression before READY FOR REVIEW.

Report exact executed counts. Do not claim PASS for unexecuted suites.

If temporary GitHub Actions workflow is used for validation, remove it from the final checkpoint diff and prove by commit comparison that final source/tests/docs are unchanged from the validated commit except for workflow removal.

---

# 22. DEPENDENCY / DAG AUDIT

Before handoff verify:

```text
benchmarks → core imports = 0
metrics → benchmarks imports = 0
data → core imports = 0
providers → core imports = 0
circular dependencies = 0
```

Do not add third-party statistics/numeric dependencies merely to compute this simple frozen formula unless demonstrably necessary.

The expected implementation should be possible with the standard library and current package surface.

---

# 23. DOCUMENTATION

Add a durable checkpoint record, preferably following existing package style, e.g.:

```text
sitescore-benchmarks/docs/CHECKPOINT_3_4_5_MID_ECDF_NUMERIC_FOUNDATION.md
```

Document at minimum:

- frozen formula;
- exact endpoint behavior;
- all-equal behavior;
- no interpolation;
- numeric domain;
- explicit ECDF tie/comparison policy;
- separation from measurement and geometry precision;
- empty-sample semantics;
- determinism/multiplicity;
- no empirical minimum N;
- no feature directionality/0–100 normalization;
- tests and exact test evidence;
- unresolved/calibration-gated items carried forward;
- `CONTRACT_CHANGE_REQUIRED`.

Do not mark the checkpoint LOCKED.

---

# 24. FORBIDDEN SCOPE EXPANSION

Do not implement checkpoint 3.4-6 work early.

Specifically forbidden in this checkpoint:

```text
NormalizedLocationFeatures production
feature-specific 0–100 mapping
competition opportunity = 100*(1-P)
walk/transit/income direction policies
site-vs-benchmark metric compatibility orchestration
age neutral fallback integration
road/parking composite
COMB-005
ScoringReadinessValidator
RealDataPipelineResult orchestration
CategoryScores
Location Score
core.analyze()
```

Do not start 3.4-7 or 3.4-8.

---

# 25. FROZEN PACKAGE MUTATION RULE

Primary changes belong to `sitescore-benchmarks`.

Do not modify frozen `sitescore-core`, `sitescore-data`, `sitescore-providers`, `sitescore-spatial`, or `sitescore-metrics` semantics merely to simplify 3.4-5.

If a true additive implementation is impossible, stop and report:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

with exact proof.

Do not silently mutate a frozen contract.

---

# 26. GIT WORKFLOW

Before working, re-fetch `main` and branch state.

Expected starting baseline:

```text
main = 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
```

If no 3.4-5 branch exists, create exactly:

```text
faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
```

from that current `main` baseline.

Then:

```text
implement
→ tests
→ docs
→ self-audit
→ commit
→ open one PR targeting main
→ update implementer.md
→ READY FOR REVIEW
```

Do not merge.

One checkpoint = one branch = one PR.

Any future reviewer hardening remains on that same branch/PR.

---

# 27. REQUIRED IMPLEMENTER SELF-AUDIT

Before handoff explicitly answer:

### Mathematics
- Is the exact frozen formula implemented directly?
- Are all-equal ties exactly 0.5?
- Are endpoint observations not forcibly clamped?
- Is there zero interpolation?

### Numeric semantics
- Are bool/NaN/Inf rejected?
- Is multiplicity preserved?
- Are 1 and 1.0 handled consistently?
- Are -0.0 and 0.0 handled consistently?
- Are close-but-unequal values kept distinct?
- Is there any hidden epsilon/rounding?

### Missingness
- Can an empty sample become 0/0.5/1?
- Can a no-observation 3.4-4 artifact become an available percentile?

### Identity
- Does permutation leave set/multiset semantics stable?
- Does multiplicity change identity/result when it should?
- Are caller-supplied counts impossible or validated away?

### Scope
- Any 0–100 score?
- Any feature directionality?
- Any competition inversion?
- Any 3.4-6 compatibility orchestration?
- Any empirical minimum N?

### Architecture
- Any new cycle?
- Any core dependency?
- Any frozen upstream mutation?

---

# 28. REQUIRED `implementer.md` RETURN FORMAT

When complete, replace/update only `implementer.md` on:

```text
ops/reviewer-implementer-handoff
```

Use at least:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-5
BASE_SHA: <full actual base SHA>
CODE_BRANCH: faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
CODE_HEAD_SHA: <full current head SHA>
PR: #<number>
CONTRACT_CHANGE_REQUIRED: 0 or 1
```

Then detail:

1. Git state.
2. Changed files and purpose.
3. Public contracts.
4. Exact numeric canonicalization semantics.
5. Exact tie policy.
6. Mid-ECDF formula implementation.
7. Endpoint/all-equal/no-interpolation behavior.
8. Empty/unavailable behavior.
9. Identity/determinism design.
10. Full adversarial tests.
11. Exact test counts and CI evidence.
12. Dependency/DAG audit.
13. Scope audit.
14. Known unresolved/calibration-gated decisions preserved.
15. Self-audit result.
16. Reviewer attention points.

Do not write `READY_TO_LOCK` or `LOCKED`.

---

# 29. ACCEPTANCE TARGET

Checkpoint 3.4-5 is ready for independent review only if:

```text
1. Mid-ECDF formula is exact and explicit.
2. Tie equality is governed by a separate versioned no-epsilon V1 policy.
3. Numeric values are finite and canonical; bool/NaN/Inf cannot leak in.
4. Tied observations preserve multiplicity.
5. all-equal => 0.5.
6. below-min => 0 and above-max => 1.
7. observed min/max follow midpoint formula, not forced endpoints.
8. no interpolation exists.
9. empty sample yields no fabricated percentile.
10. input ordering is non-semantic.
11. numeric representation equivalence is deterministic.
12. no empirical minimum-N/coverage rule is invented.
13. no 0–100 normalization/directionality/competition inversion exists.
14. locked 3.4-4 semantics remain unchanged.
15. package DAG remains valid.
16. regression tests are green and adversarial coverage is present.
17. docs match runtime behavior.
18. PR is open/unmerged and exact HEAD is reported.
```

---

# 30. FINAL EXECUTION INSTRUCTION

On the next user `devam` in the Implementer chat:

1. Read this latest `reviewer.md` from GitHub.
2. Re-fetch current repository state.
3. Create/reuse the single 3.4-5 checkpoint branch as instructed.
4. Implement the full checkpoint scope above.
5. Run tests and self-audit.
6. Open one PR to `main`.
7. Write the complete result into `implementer.md` on the coordination branch.
8. Stop at `READY_FOR_REVIEW`.

Do not merge and do not start 3.4-6.
