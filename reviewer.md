# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-FINAL
CHECKPOINT_TITLE: Integrated Architecture Audit + Freeze Readiness
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: AUDIT_AND_PREPARE_FREEZE
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 8919edb9a2791047ff10f7d08bd3fc5ed251a6e0
CODE_BRANCH: faz3.4/final-audit-freeze
REVIEWED_HEAD_SHA: NONE
PR: NONE
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
```

---

# 1. PREVIOUS CHECKPOINT LOCK VERIFICATION

FAZ 3.4-8 is accepted, user-authorized and merged.

Reviewer independently verified:

```text
PR #5 state: closed
PR #5 merged: true
reviewed branch HEAD: 6e27617674c7b7bfac539a38f98edf690b17477c
merge/main SHA: 8919edb9a2791047ff10f7d08bd3fc5ed251a6e0
```

The merge commit has the reviewed HEAD as its second parent, and current `main` points exactly to:

```text
8919edb9a2791047ff10f7d08bd3fc5ed251a6e0
```

Do not alter any completed checkpoint merely because this final audit exists. This is not a feature implementation checkpoint.

Create exactly one audit/freeze branch from the verified baseline:

```text
faz3.4/final-audit-freeze
```

If that branch already exists when work begins, re-fetch and continue legitimate existing work rather than duplicating/resetting it.

---

# 2. PURPOSE

Perform the integrated final audit for the entire FAZ 3.4 chain:

```text
3.4-0 package/DAG foundation
3.4-1 spatial foundation
3.4-2 commercial equal-area frame
3.4-3 shared derived metrics measurement foundation
3.4-4 benchmark measurement/distribution foundation
3.4-5 mid-ECDF numeric foundation
3.4-6 feature-specific normalization + compatibility
3.4-7 COMB-005 road/parking gating
3.4-8 scoring readiness + RealDataPipelineResult integration
```

Target outcome:

```text
one coherent, replayable, dependency-safe, provenance-bound FAZ 3.4 architecture
with no hidden scoring shortcuts and no unresolved item falsely represented as calibrated/available.
```

This checkpoint must answer whether FAZ 3.4 is ready to be frozen as a phase baseline.

Do not start FAZ 3-FINAL or FAZ 4.

---

# 3. MODE: AUDIT FIRST, MINIMAL FREEZE PREPARATION ONLY

Primary work is audit, not new implementation.

Allowed changes are limited to:

- final FAZ 3.4 audit/freeze documentation;
- architecture/test guards needed to prove already-frozen invariants;
- narrowly scoped corrections for reproducible blockers discovered by the integrated audit;
- package metadata/documentation consistency needed for freeze reproducibility.

Do not add new product features, scoring behavior, empirical constants, providers, reductions, category aggregation, or application behavior.

If a reproducible blocker is found, fix only that blocker and its siblings on this same final branch/PR, with stable IDs such as `FINAL-H001`.

If a correct fix requires mutation of a previously frozen contract rather than an additive correction, stop and report:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with exact evidence before making the mutation.

Expected result is `0`.

---

# 4. AUTHORITATIVE BASELINE / PACKAGE SET

Audit current `main` at exact SHA:

```text
8919edb9a2791047ff10f7d08bd3fc5ed251a6e0
```

Package set in scope:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
sitescore-benchmarks
sitescore-pipeline
```

Historical ZIPs/docs are provenance only. Actual GitHub source + commit SHA + current dependency metadata are authoritative.

---

# 5. DAG / DEPENDENCY FINAL AUDIT

Verify the final dependency graph still respects the frozen FAZ 3.4-0 architecture.

Required structural direction:

```text
core: isolated

data: neutral contracts, no sitescore package dependency

providers -> data

spatial -> external geometry/projection dependencies only as already frozen

metrics -> data + providers + spatial

benchmarks -> spatial + metrics

pipeline -> data + benchmarks
```

No reverse dependencies.
No cycles.
No pipeline import from upstream packages.
No benchmarks -> pipeline.
No data/providers/spatial/metrics -> benchmarks unless explicitly frozen already.
No pipeline -> core for this phase.

Inspect actual `pyproject.toml` files and imports; do not infer from docs alone.

Record a final DAG table with exact direct runtime dependencies for every package.

---

# 6. FROZEN SOURCE BOUNDARY AUDIT

Verify no later checkpoint silently mutated the intended frozen source surfaces of earlier packages outside its approved scope.

At minimum compare actual final main against known freeze/checkpoint baselines and PR histories for:

- `sitescore-core`;
- `sitescore-data`;
- `sitescore-providers`;
- `sitescore-spatial` after 3.4-1;
- `sitescore-metrics` after 3.4-3;
- previously locked benchmark semantics after each benchmark checkpoint.

Distinguish legitimate additive later-package work from mutations of frozen upstream code.

Do not treat documentation-only later additions as contract mutation unless they contradict source truth.

---

# 7. END-TO-END SEMANTIC CHAIN AUDIT

Prove the final architecture preserves this chain without detached/self-asserted shortcuts:

```text
provider evidence
→ spatial / metric evidence
→ DerivedMetricMeasurement
→ benchmark cell measurement attempts
→ BenchmarkDistributionArtifact
→ exact numeric sample / mid-ECDF
→ FeatureNormalizationResult
→ honest NormalizedLocationFeatures assembly
→ derived ScoringReadinessResult
→ RealDataPipelineResult
```

For every transition audit:

- actual nested artifact authority;
- identity/fingerprint content binding;
- source/method/policy/version lineage;
- missing/unavailable semantics;
- compatibility semantics;
- duplicate/completeness behavior;
- deterministic ordering;
- no caller boolean/string/score self-assertion authority.

Where factory-owned authority exists, verify public/module-level callers cannot reproduce it through importable tokens, detached hashes or arbitrary constructors.

---

# 8. MISSINGNESS / READINESS FINAL INVARIANT

The following invariant must hold globally:

```text
missing evidence != bad score != neutral score != zero
```

For every required normalized feature except the one explicit age fallback:

```text
unavailable / incompatible / ineligible / uncalibrated
→ not usable for scoring
→ readiness false
→ PipelineStatus.NOT_SCORE_READY
```

No hidden renormalization over available features.
No generic neutral 50.
No silent zero substitution.
No `core.analyze()` call from an unready real-data path.

The only frozen numeric UNCALIBRATED exception remains exactly:

```text
age_target_concentration_score = 50
policy = age_neutral_fallback/1.0
proxy = true
reason = age_affinity_not_calibrated
```

Verify the exception cannot leak to another feature.

---

# 9. BENCHMARK / ECDF / NORMALIZATION FINAL AUDIT

Verify the following locked semantics remain exact:

## Benchmark population / frame

```text
commercially evidenced spatial alternatives
full equal-area cells
all eligible cells retained
absence of POI evidence != INELIGIBLE by itself
```

No clipped-boundary equal weighting shortcut.

## Distribution attempts

Every eligible frame cell must have exactly one attempt.
Missing/unresolved attempts remain retained.
Numeric observations require the locked availability/eligibility/calibration/finite policy.
No min-N or coverage threshold has been invented as production authority.

## Mid-ECDF

```text
P(d) = (#below + 0.5 * #equal) / N
```

No interpolation.
All ties at midpoint.
No epsilon/tolerance/rounding/quantization.
Exact numeric comparison semantics remain frozen.

## Directionality

```text
ordinary higher-is-better feature -> 100 * P(d)
competition opportunity -> 100 * (1 - P(d))
```

Direction cannot be caller selected/inverted.

## Site/benchmark compatibility

Exact compatibility must still include actual measurement definition/policy/precision/unit/method/source-bundle semantics as applicable.

Transit exact source-bundle identity and competition measurement-definition identity must survive into readiness.

---

# 10. SPATIAL / PRECISION FINAL AUDIT

Re-verify load-bearing 3.4-1 / 3.4-2 invariants in final main:

- executable CRS identity;
- projected AREA semantics;
- actual `GeometryPrecisionPolicy` bound into operation policy identity;
- INTERSECT precision coherence;
- no silent geometry repair;
- equal-area frame identity/content binding;
- production resolution/CRS remain calibration/evidence gated where not frozen empirically.

Do not invent a production CRS/resolution in this final audit.

---

# 11. METRIC FINAL AUDIT

Re-verify the ten frozen `DerivedLocationMetrics` slots and actual measurement foundation.

Confirm numeric pass-through metrics still obey their frozen semantics and unresolved reductions remain unresolved rather than numerically fabricated.

Unresolved/calibration-gated items include as applicable:

```text
walkable_population reduction
target_population_density reduction
competition_pressure reduction
road_reachable_area reduction
population allocation
age affinity
road reduction
parking/composite policy
sample adequacy threshold
```

Do not confuse structural contract existence with empirical calibration completion.

---

# 12. COMB-005 FINAL AUDIT

Final canonical truth must still be:

```text
no approved empirical COMB-005 policy
no production weight vector
canonical production composite unavailable
road_parking_access_score nonnumeric/unready
```

Verify no alternate public constructor/helper/fixture has reintroduced:

- caller-created approval;
- arbitrary AVAILABLE components;
- arbitrary final score;
- 50/50 default;
- road-only/parking-only substitution;
- neutral fill;
- remaining-weight renormalization.

Test-only synthetic composition machinery must not be production authority.

---

# 13. PIPELINE / READINESS FINAL AUDIT

Verify final `sitescore-pipeline` retains:

- canonical assembly from actual six `FeatureNormalizationResult` artifacts;
- exact locked age fallback;
- actual 3.4-7 COMB result;
- benchmark binding/compatibility lineage;
- factory-owned assembly/readiness authority;
- deterministic readiness fingerprint;
- terminal `DerivedLocationMetrics` coherence against actual site measurements;
- status derived rather than caller supplied;
- ordinary unready -> `NOT_SCORE_READY`;
- explicit execution failure -> `PIPELINE_ERROR`;
- `SCORE_READY != SCORED`.

Current production architecture may legitimately remain NOT_SCORE_READY because unresolved/calibration-gated inputs remain. Do not force a canonical SCORE_READY example.

---

# 14. NO CATEGORY / CORE / PRODUCT LAYER LEAKAGE

FAZ 3.4 final source must not implement real-data category aggregation or product scoring orchestration.

Audit for absence of new pipeline/benchmark logic performing:

```text
Demand category aggregation
Competition category aggregation
Accessibility category aggregation
Economics category aggregation
category weights
base Location Score
dealbreaker penalties
final Location Score
Decision Layer
core.analyze()
report/PDF
payments/UI/application workflow
```

Frozen data DTOs such as `ReadyCategoryScorePayload` may exist historically, but FAZ 3.4 must not compute those outputs from the real-data pipeline.

---

# 15. EMPIRICAL / CALIBRATION GATE REGISTER

Create one explicit final register separating:

## structurally frozen / implemented

from

## empirically unresolved / calibration-gated

At minimum list:

```text
production equal-area CRS/resolution/membership calibration
population allocation
age affinity
competition reduction
road reduction
approved COMB-005 weights
sample adequacy threshold
empirical benchmark/calibration datasets
```

Also record any additional unresolved item found in actual source/docs.

The final phase claim must remain:

```text
Mathematically validated scoring engine; empirical validation pending.
```

Do not upgrade this claim.

---

# 16. TEST / VALIDATION REQUIREMENTS

Run the complete package regression set on the final audit branch:

```text
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Record exact counts only where actually visible from pytest/job output.

Add or retain architecture guards that prove at minimum:

- dependency DAG/import prohibitions;
- no later-layer leakage;
- no production empirical constants introduced in forbidden scopes;
- no public authority bypasses previously hardened;
- core/data/provider frozen boundaries remain intact.

If using a temporary GitHub Actions validation workflow, remove it before final review and prove successful validated SHA -> final review HEAD is workflow-removal-only (or explain any exact nonsemantic/tree-neutral delta with evidence).

---

# 17. FINAL AUDIT DOCUMENT / FREEZE RECORD PREPARATION

Create/update an appropriate final FAZ 3.4 audit document under a sensible package/root docs location.

It must record at minimum:

```text
FAZ 3.4 status
base/main SHA audited
checkpoint 3.4-0 through 3.4-8 lock state
package DAG and direct dependencies
full test evidence
key structural invariants
final calibration-gate register
known unresolved empirical items
contract-change status
final audit decision
```

Do not falsely label FAZ 3.4 `FROZEN` before Reviewer acceptance and user LOCK.

Allowed pre-lock wording:

```text
FREEZE_CANDIDATE
READY_FOR_FINAL_REVIEW
```

not `FROZEN`.

---

# 18. PR / BRANCH / RETURN PROTOCOL

Use exactly one branch:

```text
faz3.4/final-audit-freeze
```

Open/update exactly one PR against `main` for the final audit/freeze candidate.

Do not merge it.
Do not self-LOCK.
Do not create FAZ 3-FINAL work.

Replace `implementer.md` with a detailed report containing at minimum:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-FINAL
BASE_SHA: 8919edb9a2791047ff10f7d08bd3fc5ed251a6e0
CODE_BRANCH: faz3.4/final-audit-freeze
CODE_HEAD_SHA: <exact SHA>
PR: <number>
CONTRACT_CHANGE_REQUIRED: 0/1
FINAL_AUDIT_DECISION: FREEZE_CANDIDATE / BLOCKED
FINAL_BLOCKERS: NONE or stable IDs
```

Also report:

- changed file list;
- whether source code changed or audit/docs/tests only;
- exact dependency audit;
- frozen-boundary audit;
- exact validation run IDs/SHAs;
- test counts where visible;
- unresolved empirical/calibration register;
- any discrepancy between historical checkpoint claims and actual final GitHub state.

Stop after updating PR and `implementer.md`.

---

# 19. REVIEWER ACCEPTANCE STANDARD

The Reviewer will independently re-fetch and inspect the entire final candidate.

Acceptance standard:

> No reproducible production correctness blocker remains within FAZ 3.4 scope; all locked structural invariants are preserved; unresolved empirical/calibration items are explicitly gated rather than silently defaulted; package DAG and frozen boundaries are clean; final test evidence is green and reproducible.

Only then may Reviewer issue SHA-specific:

```text
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
```

User remains sole LOCK authority.
