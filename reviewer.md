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
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
CODE_BRANCH: faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
REVIEWED_HEAD_SHA: 4e2d44178141e2715b18283917288bfc829dd42e
PR: #2
CONTRACT_CHANGE_REQUIRED: 0
```

---

# 1. REVIEW DECISION

```text
FAZ 3.4 — CHECKPOINT 3.4-5
Decision: READY TO LOCK
Repository: metadoks/sitescore
PR: #2
Base: 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
Reviewed HEAD: 4e2d44178141e2715b18283917288bfc829dd42e
```

This acceptance applies only to the exact reviewed HEAD above.

`READY_TO_LOCK` is not `LOCKED`.

Do not merge unless the user explicitly sends `LOCK` to the Implementer chat.

Do not start checkpoint 3.4-6 during the LOCK transition.

---

# 2. INDEPENDENT REVIEW SCOPE

The Reviewer independently inspected:

- latest `implementer.md`;
- PR #2 metadata/base/head;
- base-to-head changed-file set;
- full `sitescore-benchmarks/src/sitescore_benchmarks/ecdf.py` implementation;
- full `test_mid_ecdf.py` adversarial/mathematical regression surface;
- updated architecture guard tests;
- current `main` baseline;
- validation commit → final review HEAD comparison;
- GitHub Actions validation run/job state;
- locked 3.4-4 distribution semantics consumed by this checkpoint.

No reviewer decision is based solely on the Implementer summary.

---

# 3. VERIFIED MATHEMATICAL SEMANTICS

The implementation directly preserves the frozen mid-ECDF rule:

```text
P(d) = (# below d + 0.5 × # equal d) / N
```

Operationally it evaluates the algebraically equivalent exact count form:

```text
(2 * below_count + equal_count) / (2 * N)
```

Verified behavior includes:

- unique middle observation;
- tied middle observations;
- all-equal sample → 0.5;
- below minimum → 0;
- above maximum → 1;
- observed minimum/maximum use formula midpoint semantics rather than endpoint clamping;
- no interpolation;
- duplicate multiplicity is preserved;
- input permutation is non-semantic.

No alternative percentile convention was introduced.

---

# 4. NUMERIC / TIE POLICY — VERIFIED

`NumericComparisonPolicy` / `EXACT_NUMERIC_COMPARISON_V1` is separate from geometry and measurement precision.

V1 semantics are explicitly:

```text
EXACT_CANONICAL_NUMERIC_VALUE
EXACT_CANONICAL_NUMERIC_ORDER
NO_TOLERANCE_NO_ROUNDING_NO_QUANTIZATION
```

Implementation canonicalizes accepted int/float values to reduced exact rational pairs.

Verified consequences:

```text
1 == 1.0 for ECDF tie/identity semantics
-0.0 == 0.0 for ECDF tie/identity semantics
close-but-unequal finite values remain distinct
```

Rejected inputs:

```text
bool
None
NaN
+Inf
-Inf
```

No arbitrary epsilon, rounding, quantization or ULP threshold exists.

The comparison-policy identity is distinct from `FULL_BINARY64` measurement precision semantics.

---

# 5. SAMPLE / LINEAGE SEMANTICS — VERIFIED

`CanonicalNumericSample` is a deliberately pure numeric helper:

- identity binds comparison-policy identity, canonical sorted values and multiplicity;
- order is non-semantic;
- multiplicity is semantic;
- invalid numeric values cannot enter the canonical sample.

`BenchmarkNumericSample` is the domain-bound wrapper:

- consumes an actual `BenchmarkDistributionArtifact`;
- requires distribution state `AVAILABLE`;
- consumes only actual 3.4-4 `BenchmarkObservation` values;
- binds actual distribution identity and observation identities;
- does not reconstruct excluded/missing/unresolved/uncalibrated attempts as numerics.

Thus unrelated benchmark distributions with coincidentally identical numeric values do not collapse to the same domain sample identity.

The pure helper is not itself site/benchmark compatibility authority. Feature/site compatibility remains explicitly deferred to checkpoint 3.4-6.

---

# 6. EMPTY / INCOMPATIBLE BEHAVIOR — VERIFIED

Pure empty numeric sample evaluation produces:

```text
state = EMPTY_SAMPLE
percentile = None
reason = empty_numeric_sample
```

No 0 / 0.5 / 1 fallback is fabricated.

Domain-bound benchmark ECDF rejects 3.4-4 distributions that are not `AVAILABLE`, including:

```text
EMPTY_ELIGIBLE_POPULATION
NO_NUMERIC_OBSERVATIONS
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

Therefore unavailable benchmark evidence cannot silently become an available percentile.

---

# 7. IDENTITY / SELF-ASSERTION REVIEW — VERIFIED

`MidEcdfEvaluation` accepts only:

```text
sample
query
policy
```

and derives:

```text
N
below_count
equal_count
percentile
state
reason_codes
```

No caller-supplied count or percentile path exists.

Evaluation identity binds canonical query value, sample identity, policy/comparison identity, state/reasons, N, counts and percentile.

`BenchmarkMidEcdfEvaluation` additionally binds benchmark sample/distribution lineage.

No reproducible public path was found that can self-assert a false canonical percentile while bypassing the actual sample.

---

# 8. SCOPE / ARCHITECTURE REVIEW — VERIFIED

Checkpoint 3.4-5 does not implement:

```text
0–100 feature normalization
feature-specific directionality
100 * P
100 * (1-P)
competition opportunity inversion
feature-specific site/benchmark compatibility orchestration
age fallback
COMB-005
road_parking_access_score
ScoringReadiness
RealDataPipelineResult
CategoryScores
Location Score
core.analyze()
```

No empirical adequacy constant was introduced for:

```text
minimum N
coverage ratio
minimum unique values
variance
sample adequacy
```

No dependency metadata changed.

No new third-party runtime dependency was added.

Approved package boundaries remain intact; no core/pipeline/provider/data leakage was introduced into `sitescore-benchmarks`.

---

# 9. TEST / VALIDATION STATUS

GitHub Actions validation independently verified:

```text
workflow: cp345-validation
run id: 31896517539
validated commit: cc32f3abdb080ecee97f812b65b1c7a076645e42
conclusion: SUCCESS
```

The visible job confirms successful execution of all six package test steps:

```text
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Reported checkpoint suite result:

```text
sitescore-benchmarks: 142/142 PASS
sitescore-metrics:      67/67 PASS
```

Reviewer independently compared the validated commit to final review HEAD and verified the only delta is removal of:

```text
.github/workflows/cp345-validation.yml
```

Therefore source/tests/checkpoint documentation at the validated commit are unchanged in the final reviewed HEAD.

---

# 10. REVIEW CONCLUSION

No reproducible production correctness blocker remains within checkpoint 3.4-5 scope at reviewed HEAD.

Acceptance criterion satisfied:

```text
No reproducible production correctness blocker remains within current checkpoint scope and all frozen invariants are preserved.
```

Final reviewer state:

```text
FAZ 3.4-5: READY TO LOCK
REVIEWED_HEAD_SHA: 4e2d44178141e2715b18283917288bfc829dd42e
PR: #2
CONTRACT_CHANGE_REQUIRED: 0
```

---

# 11. USER-AUTHORIZED LOCK INSTRUCTION

Only if the user explicitly sends:

```text
LOCK
```

the Implementer may perform the checkpoint transition.

Immediately before merge, re-fetch PR #2 and verify:

```text
current PR HEAD == 4e2d44178141e2715b18283917288bfc829dd42e
PR base == main
PR is open
main remains compatible with expected base
CONTRACT_CHANGE_REQUIRED == 0
```

If the PR HEAD differs from the reviewed SHA, do not merge. Record:

```text
IMPLEMENTER_STATE: LOCK_BLOCKED_REVIEW_STALE
```

in `implementer.md` and return for Reviewer re-review.

If the exact reviewed SHA is still current and the user explicitly authorized `LOCK`, merge PR #2 using expected-head-SHA protection when available and then record at minimum:

```text
IMPLEMENTER_STATE: LOCKED
CHECKPOINT: FAZ 3.4-5
REVIEWED_HEAD_SHA: 4e2d44178141e2715b18283917288bfc829dd42e
PR: #2
MERGED_MAIN_SHA: <actual merge/main SHA>
LOCK_TRANSITION_STATUS: SUCCESS
TAG: <actual tag / PENDING / NOT REQUIRED>
```

Do not implement checkpoint 3.4-6 during the LOCK transition.

After successful LOCK, stop and wait for the user to send `devam` to Reviewer.
