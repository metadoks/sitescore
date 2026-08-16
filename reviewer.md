# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3
CURRENT_CHECKPOINT: FAZ 3-FINAL
CHECKPOINT_TITLE: Full Phase Integrated Audit + Freeze Readiness
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: AUDIT_AND_PREPARE_PHASE_FREEZE
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 3519b118c9f5d04a16096003657a0058cef4af42
CODE_BRANCH: faz3/final-audit-freeze
REVIEWED_HEAD_SHA: NONE
PR: NONE
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
```

---

# 1. PREVIOUS PHASE-SUBSECTION FREEZE VERIFICATION

FAZ 3.4-FINAL is accepted, user-authorized and merged.

Reviewer independently verified:

```text
PR #6 state: closed
PR #6 merged: true
reviewed branch HEAD: b66b0030760281a2b05391237007cdfabf69fb7b
merge/main SHA: 3519b118c9f5d04a16096003657a0058cef4af42
```

The merge commit has the exact reviewed HEAD as its second parent and current `main` points exactly to:

```text
3519b118c9f5d04a16096003657a0058cef4af42
```

Therefore the operational state is now:

```text
FAZ 3.4-FINAL: LOCKED
FAZ 3.4: FROZEN
```

The merged 3.4 audit document intentionally retains its historically correct pre-lock `FREEZE_CANDIDATE` wording. Do not create a post-lock rewrite merely to change historical wording.

Do not modify the frozen FAZ 3.4 baseline as part of opening FAZ 3-FINAL.

---

# 2. PURPOSE

Perform the final integrated audit for the **entire FAZ 3 real-data architecture**, not merely FAZ 3.4.

The audit must reconcile actual GitHub state across:

```text
FAZ 3.1 — real-data architecture / structural contract decisions
FAZ 3.2 — core + data contract architecture/freeze
FAZ 3.3 — provider layer
FAZ 3.4 — spatial/frame/metric/benchmark/normalization/readiness/pipeline architecture
```

Target outcome:

```text
one coherent, dependency-safe, replayable, provenance-bound FAZ 3 baseline
ready to be frozen before FAZ 4 backend/application work begins
```

This is **not** a new feature checkpoint.

Do not start FAZ 4.
Do not add application/backend/API/UI/payment/report behavior.
Do not perform empirical calibration merely to make current architecture SCORE_READY.

---

# 3. AUTHORITATIVE BASELINE

Audit actual `main` at exact SHA:

```text
3519b118c9f5d04a16096003657a0058cef4af42
```

Create/use exactly one audit branch:

```text
faz3/final-audit-freeze
```

from that baseline.

If the branch already legitimately exists, re-fetch and continue it rather than resetting or duplicating work.

Historical ZIPs and old markdown are provenance only. Actual GitHub source, commit history, merged PR state, dependency metadata, and coordination handoffs are authoritative.

---

# 4. MODE — AUDIT FIRST, FREEZE PREPARATION ONLY

Allowed persistent changes are limited to:

- one FAZ 3 final audit/freeze-candidate document;
- architecture/regression guards proving already-intended invariants;
- narrowly scoped corrections only if an actual reproducible final blocker is found;
- minimal documentation/metadata consistency needed for reproducible freeze evidence.

Do not introduce new product semantics, providers, scoring formulas, weights, thresholds, calibration constants, benchmark policies, or application behavior.

If a reproducible blocker requires mutation of a previously frozen contract rather than an additive safe correction, stop and report:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with exact GitHub evidence before changing frozen source.

Expected result remains `0`.

---

# 5. RECONSTRUCT THE ACTUAL FAZ 3 FREEZE / LOCK REGISTER

Do not rely on memory alone.

From GitHub history, merged PRs, package docs, and coordination state, reconstruct the actual operational register for:

```text
FAZ 3.1
FAZ 3.2
FAZ 3.3
FAZ 3.4
```

For each subsection record:

- relevant baseline/final SHA(s);
- lock/freeze state actually supported by GitHub;
- package(s) owned by that subsection;
- material architectural decisions;
- test evidence where retrievable;
- whether later work legitimately added downstream packages without mutating its frozen source.

Important distinction:

- historical docs may preserve pre-lock wording;
- current operational state must be derived from merged GitHub state and explicit user-authorized lock transitions.

If any prior subsection cannot honestly be called frozen from actual evidence, do **not** silently mark it frozen. Record the discrepancy as a final blocker or explicit state gap.

---

# 6. PACKAGE SET / FINAL DAG

Audit all current FAZ 3 runtime packages:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
sitescore-benchmarks
sitescore-pipeline
```

Expected final dependency direction remains:

```text
core: isolated

data: neutral contracts

providers -> data

spatial -> Shapely + pyproj only

metrics -> data + providers + spatial

benchmarks -> spatial + metrics

pipeline -> data + benchmarks
```

Required conclusions:

- exact direct runtime dependency table from current `pyproject.toml` files;
- actual source import graph from AST/source inspection;
- DAG acyclic;
- no reverse dependencies;
- no upstream -> pipeline dependency;
- no pipeline -> core dependency;
- core isolated;
- data neutral;
- package versions/pins internally coherent with frozen architecture.

Do not infer this from README text alone.

---

# 7. FAZ 3.1 ARCHITECTURAL DECISION AUDIT

Reconstruct and verify the structural decisions that FAZ 3 implementation is supposed to embody.

At minimum audit actual source/contracts against these frozen architectural truths:

```text
metric != score
missing evidence != bad != neutral != zero
provider evidence remains distinct from derived metrics
site metric semantics must match benchmark metric semantics
normalization occurs only after real-unit metric + compatible benchmark distribution
required unresolved/incompatible/uncalibrated feature -> NOT_SCORE_READY
SCORE_READY != SCORED
Location Engine and Financial Engine remain separated at this layer
```

Also verify the specific structural decisions that entered implementation:

- competition benchmark semantics = commercially evidenced spatial alternatives;
- full equal-area cells / no clipped-boundary equal weighting shortcut;
- tri-state commercial eligibility;
- mid-ECDF ties/endpoints/no interpolation;
- competition opportunity direction inversion;
- transit service-frequency semantics rather than stop count;
- road and parking remain semantically separate before COMB-005;
- COMB-005 remains calibration-gated;
- exact age fallback remains the sole explicit uncalibrated numeric exception.

If actual source diverges from an intended structural decision, report the exact divergence rather than rewriting history.

---

# 8. FAZ 3.2 CORE / DATA FROZEN BOUNDARY AUDIT

Re-audit actual current `sitescore-core` and `sitescore-data` against their frozen architecture.

At minimum verify:

```text
sitescore-core runtime dependencies = []
sitescore-core has no external SiteScore imports
sitescore-data has no SiteScore runtime dependency
no circular dependency
frozen DTO/state semantics still present
```

Re-check load-bearing data contracts used downstream, including at minimum:

```text
MetricValue
DerivedLocationMetrics
NormalizedLocationFeatures
FeatureReadinessPolicy
ReadinessCompatibilityInput
ApprovedFallbackPolicyRef
ScoringReadinessResult
RealDataPipelineResult
PipelineStatus
```

Confirm availability, eligibility and calibration remain separate dimensions.

Confirm the frozen normalized surface still has exactly eight V1 feature slots and the derived metric surface ten V1 metric slots.

Confirm later provider/spatial/benchmark/pipeline work has not silently altered core/data source after their accepted freeze baseline.

Do not mutate core/data merely to improve final documentation.

---

# 9. FAZ 3.3 PROVIDER LAYER FINAL AUDIT

Audit the actual current `sitescore-providers` package as a complete provider layer, including the previously hardened provider families and cross-cutting foundation.

At minimum inspect/reconcile actual source for:

- provider foundation / request-response identity and temporal semantics;
- geocoding + Census geography binding;
- ACS statistical evidence semantics;
- competition evidence/taxonomy/manifest lineage;
- pedestrian / routing / Valhalla execution binding and warning semantics;
- transit / GTFS semantics and source-bundle identity where implemented;
- road / parking provider evidence contracts where implemented;
- content hashes, manifest identities, execution-policy identities and compatibility attestations;
- provider evidence persistence/licensing boundaries where encoded.

Final provider audit must prove:

```text
provider layer emits evidence/snapshots, not normalized scores
no missing provider evidence becomes numeric zero by default
source/bundle/content identity is preserved into downstream metric compatibility
no provider imports benchmark/pipeline/core scoring logic
```

Use actual current GitHub state; do not assume checkpoint reports are sufficient.

If old provider documents conflict with current source, source + merged SHA wins and discrepancy must be recorded.

---

# 10. FAZ 3.4 FROZEN BASELINE RE-ATTESTATION

Treat merged FAZ 3.4 at:

```text
3519b118c9f5d04a16096003657a0058cef4af42
```

as frozen input to this phase audit.

Do not re-implement it.

Re-attest the load-bearing chain only to ensure it remains coherent with FAZ 3.1–3.3:

```text
provider evidence
-> spatial / real-unit measurement
-> benchmark population / distribution
-> exact mid-ECDF
-> feature-specific normalization
-> age fallback + COMB-005 gate
-> NormalizedLocationFeatures
-> ScoringReadinessResult
-> RealDataPipelineResult
```

Confirm the 3.4 final audit/guard merged via PR #6 is present and no post-freeze mutation has occurred after merge.

---

# 11. CROSS-PACKAGE LINEAGE / AUTHORITY AUDIT

The central FAZ 3-FINAL question is whether evidence authority survives package boundaries without caller self-assertion.

Audit end-to-end for:

- actual nested evidence/artifact objects rather than detached IDs alone;
- request/content/manifest/source bundle identity;
- method/policy/version lineage;
- precision and CRS identity where spatial operations are involved;
- benchmark frame/distribution identity;
- site↔benchmark compatibility;
- normalization policy identity;
- age fallback authority;
- COMB-005 authority/gating;
- pipeline assembly/readiness factory authority;
- terminal real-unit metric coherence.

Search for public/module-level bypasses or constructors that could fabricate canonical AVAILABLE/CALIBRATED/APPROVED/SCORE_READY state without actual evidence.

Do not treat underscore naming as an authority boundary by itself.

---

# 12. GLOBAL MISSINGNESS / NO-HIDDEN-DEFAULT AUDIT

Search actual FAZ 3 source for production shortcuts that could violate:

```text
missing != zero
missing != neutral
uncalibrated != calibrated
incompatible != compatible
unknown != negative evidence
```

Specifically audit for hidden or default:

- zero fill;
- neutral 50 fill outside exact age fallback;
- feature-weight renormalization over available inputs;
- minimum-N that silently changes structural availability;
- coverage threshold invented as production authority;
- road/parking 50/50;
- one-sided road/parking substitution;
- default empirical CRS/resolution/overlap threshold;
- caller-selected competition direction;
- provider-missing treated as no competition/no transit/no parking.

Any such production behavior is a final blocker unless explicitly frozen and evidenced.

---

# 13. EMPIRICAL / CALIBRATION GATE REGISTER — WHOLE FAZ 3

Produce one phase-wide register separating:

## A. structurally frozen / implemented

from

## B. empirically unresolved / calibration-gated

At minimum preserve unresolved status for applicable items such as:

```text
production equal-area CRS selection/attestation
benchmark cell resolution
lattice anchor/origin
boundary-membership calibration
commercial ontology/category mapping
commercial evidence-to-cell applicability
provider precedence / cross-provider reconciliation
population allocation/intersection policy
target population definition
age affinity calibration
household income ratio denominator/reference
competition multi-scale scalar reduction
road multi-scale scalar reduction
COMB-005 component normalization authorities
COMB-005 formula/weights
sample adequacy/minimum-N policy if later required
benchmark coverage threshold if later required
production calibration datasets/acceptance evidence
empirical validation across target archetypes/geographies
```

Add any other unresolved item actually found in current source/docs.

Do not invent a value to close any gate.

The final phase claim remains exactly:

```text
Mathematically validated scoring engine; empirical validation pending.
```

Do not upgrade this claim to empirically validated, production-calibrated, or production-ready scoring.

---

# 14. NO FAZ 4 / PRODUCT-LAYER LEAKAGE

FAZ 3 final source must remain a real-data architecture baseline, not an application implementation.

Audit for absence of newly implemented:

```text
HTTP/API application layer
user/account/auth flows
payment orchestration
report/PDF generation
UI/frontend
job orchestration for commercial product delivery
category aggregation from real-data pipeline
Location Score orchestration
Decision Layer execution
core.analyze() invocation from pipeline
```

Historical/frozen DTO definitions alone are not leakage; executable orchestration is.

FAZ 4 begins only after FAZ 3-FINAL is reviewed, user-LOCKED and independently verified.

---

# 15. FULL REGRESSION / REPRODUCIBILITY VALIDATION

Run the complete current package regression set:

```text
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Record exact pytest counts only where directly visible.

Add/retain phase-final architecture guards sufficient to prove at minimum:

- exact runtime dependency DAG;
- forbidden import directions;
- core/data frozen boundaries;
- provider no-score boundary;
- no upstream -> pipeline reverse dependency;
- no FAZ 4/product-layer leakage;
- no hidden empirical/default scoring shortcuts;
- COMB-005 remains unapproved;
- exact age exception remains unique;
- phase claim/gate register remains honest.

If using a temporary GitHub Actions workflow, remove it before final review and prove successful validated SHA -> final review HEAD is workflow-removal-only, or document any exact tree-neutral delta.

---

# 16. PHASE FINAL AUDIT / FREEZE-CANDIDATE RECORD

Create a phase-level audit document, preferably:

```text
docs/FAZ3_FINAL_AUDIT_FREEZE_CANDIDATE.md
```

unless an existing authoritative phase-final location is already present.

Record at minimum:

```text
FAZ 3 status
exact audited base/main SHA
3.1 / 3.2 / 3.3 / 3.4 operational state register
package/version/dependency DAG
frozen-source history evidence
end-to-end lineage/authority audit
missingness/no-hidden-default audit
full test evidence
structural vs empirical/calibration gate register
known unresolved empirical items
contract-change status
final blockers
final audit decision
```

Before user LOCK, allowed wording is only:

```text
FREEZE_CANDIDATE
READY_FOR_FINAL_REVIEW
```

Do not write `FAZ 3: FROZEN` before Reviewer acceptance and explicit user LOCK.

---

# 17. BRANCH / PR / RETURN PROTOCOL

Use exactly one branch:

```text
faz3/final-audit-freeze
```

Open/update exactly one PR against `main`.

Do not merge it.
Do not self-LOCK.
Do not start FAZ 4.

Replace `implementer.md` with detailed evidence containing at minimum:

```text
CURRENT_PHASE: FAZ 3
CURRENT_CHECKPOINT: FAZ 3-FINAL
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: 3519b118c9f5d04a16096003657a0058cef4af42
CODE_BRANCH: faz3/final-audit-freeze
CODE_HEAD_SHA: <exact SHA>
PR: <number>
CONTRACT_CHANGE_REQUIRED: 0/1
FINAL_AUDIT_DECISION: FREEZE_CANDIDATE / BLOCKED
FINAL_BLOCKERS: NONE or stable IDs
```

Also report:

- exact changed files;
- production-source changed yes/no;
- reconstructed 3.1–3.4 state register;
- exact package dependency/import audit;
- cross-package lineage findings;
- frozen-source history comparisons;
- regression run IDs/SHAs/counts where directly visible;
- complete empirical/calibration gate register;
- any discrepancy between historical docs and actual GitHub state.

Stop after PR + handoff. No merge, tag, FAZ 4, or post-review rewrite.

---

# 18. REVIEWER ACCEPTANCE STANDARD

The Reviewer will independently re-fetch and review the phase-final candidate.

Acceptance requires:

> No reproducible production correctness blocker remains across FAZ 3.1–3.4; the current package DAG and frozen-source boundaries are coherent; provider evidence through terminal pipeline lineage remains authority-bound; no hidden default turns missing or uncalibrated evidence into a score; all unresolved empirical/calibration items remain explicitly gated; full regression evidence is green; and no FAZ 4/product behavior has leaked into the frozen real-data architecture.

Only after that may Reviewer issue exact-SHA:

```text
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
FINAL_AUDIT_DECISION: FREEZE_READY
```

User remains sole LOCK authority.
