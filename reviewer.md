# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: AUTHORITY-CORRECTIVE-REOPEN
CHECKPOINT_TITLE: PIPE-AUTH-H001 + APP-H002 Authority Corrective Reopen

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 16427d8bb74611a3de46652d55b708edc93b055b
CODE_BRANCH: corrective/authority-reopen-pipe-app
REVIEWED_HEAD_SHA: NONE
PR: NONE

CONTRACT_CHANGE_REQUIRED: 1
USER_REOPEN_AUTHORIZED: YES
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

FAZ_3_STATUS: FROZEN_WITH_NARROW_USER_AUTHORIZED_CORRECTIVE_REOPEN
FAZ_4_0_STATUS: HISTORICALLY_LOCKED_MERGED
FAZ_4_1_IMPLEMENTATION_STATUS: NOT_STARTED

PIPE-AUTH-H001: OPEN
APP-H002: OPEN
```

---

# 1. USER AUTHORITY / HISTORICAL LOCK RULE

The user has explicitly authorized a narrow frozen-contract corrective reopen for exactly:

```text
PIPE-AUTH-H001
APP-H002
```

Do not rewrite history:

```text
FAZ 4.0 was historically LOCKED and merged.
An inherited authority defect was discovered after lock.
A narrow corrective reopen is now user-authorized.
```

This corrective work is NOT FAZ 4.1. Category aggregation remains NOT STARTED.

Current authoritative `main` independently verified by Reviewer before this request:

```text
16427d8bb74611a3de46652d55b708edc93b055b
```

No corrective PR existed when this implementation request was issued. Implement from exactly this base.

---

# 2. IMPLEMENTATION OBJECTIVE

Correct only the execution-authority defect class exposed by post-registration mutation.

Final authority standard:

```text
shape equality is not execution authority
object identity alone is not execution authority

factory origin
+
construction-time closure-private binding
+
post-registration integrity verification
=
execution authority
```

A caller must not be able to obtain a legitimate factory-owned object, mutate its public fields through `object.__setattr__`, and retain scoring/execution authority.

Public/reconstructable hashes, booleans, IDs, sentinels, underscore names, frozen dataclasses, or object identity alone are insufficient.

---

# 3. PIPE-AUTH-H001 — REQUIRED PIPELINE HARDENING

Primary production source allowed:

```text
sitescore-pipeline/src/sitescore_pipeline/integration.py
```

The canonical `NormalizedFeatureAssembly` construction-time authority must bind at least:

```text
features
direct_results
feature_policies
compatibility
approved_fallback_policies
artifact_identities
assembly_id
```

The canonical `ReadinessEvaluation` construction-time authority must bind at least:

```text
assembly
result
```

Canonical validation must establish BOTH:

```text
A. exact registered factory-owned object identity
B. current public object has not diverged from its construction-time trusted binding
```

Direct `object.__setattr__` mutation of any bound field must fail closed.

## Trusted execution requirement

Do NOT implement this pattern:

```text
validate registered object
-> then continue execution from caller-mutable public fields
```

For readiness and terminal execution, resolve the closure-private trusted construction-time binding and use the trusted bound values as execution authority.

`derive_scoring_readiness(...)` and `build_real_data_pipeline_result(...)` must not be redirectable to mutated public state after canonicality has been checked.

The terminal status, normalized features, readiness result, and real-unit coherence checks must derive from trusted construction-time material.

## Fake fixes forbidden

The following are not sufficient as sole authority mechanisms:

```text
dataclass(frozen=True)
object id
public assembly_id
public readiness_fingerprint
public hash
trusted=True
public/private-named sentinel
re-running __post_init__
field equality without factory-origin binding
```

A semantic hash may supplement integrity only if the expected value/origin is closure-private and factory-bound; it cannot replace trusted origin.

---

# 4. APP-H002 — REQUIRED APPLICATION HARDENING

Primary production source allowed:

```text
sitescore-app/src/sitescore_app/gating.py
```

`ApplicationPipelineResult` must be closure-bound to the exact terminal returned at its construction time.

`ApplicationScoringInput` must be closure-bound to the exact `ApplicationPipelineResult` accepted at its construction time.

`require_canonical_application_pipeline_result(...)` must reject a previously canonical wrapper whose public `.pipeline_result` was replaced after registration.

`require_canonical_application_scoring_input(...)` must reject a previously canonical scoring input whose public `.application_pipeline_result` was replaced after registration.

The nested wrapper must also remain canonical and match the construction-time trusted binding.

## Trusted app execution requirement

Authorization must consume closure-resolved trusted bindings, not mutable current public references after validation.

Do not leave a TOCTOU-style path where:

```text
canonicality check passes
-> public nested reference changes / has changed
-> later execution follows redirected object
```

No public token/hash/boolean may grant authority.

---

# 5. MANDATORY ADVERSARIAL TESTS — PIPE-AUTH-H001

Tests must directly use `object.__setattr__` and cover at minimum:

```text
1. canonical assembly.features replaced -> rejected
2. canonical assembly.direct_results replaced -> rejected
3. canonical assembly.feature_policies replaced -> rejected
4. canonical assembly.compatibility replaced -> rejected
5. canonical assembly.approved_fallback_policies replaced -> rejected
6. canonical assembly.artifact_identities replaced -> rejected
7. canonical assembly.assembly_id replaced -> rejected
8. canonical readiness.assembly replaced -> rejected
9. canonical readiness.result replaced -> rejected
10. forged SCORE_READY result cannot become trusted
11. forged numeric road_parking_access_score cannot become trusted
12. COMB-005 bypass attempt fails closed
13. copied/reconstructed assembly rejected
14. copied/reconstructed readiness rejected
15. unmodified canonical behavior remains valid
```

Tests should demonstrate that integrity checks are not merely descriptive: trusted downstream execution itself must refuse redirected/mutated state.

---

# 6. MANDATORY ADVERSARIAL TESTS — APP-H002

Tests must directly use `object.__setattr__` and cover at minimum:

```text
1. canonical ApplicationPipelineResult.pipeline_result replaced -> rejected
2. wrapper redirected to forged SCORE_READY terminal -> rejected
3. canonical ApplicationScoringInput.application_pipeline_result replaced -> rejected
4. scoring input redirected to another otherwise-canonical wrapper -> rejected
5. manual wrappers rejected
6. copied/reconstructed wrappers rejected
7. raw forged RealDataPipelineResult rejected
8. detached status/readiness_fingerprint/normalized_features remain non-authoritative
9. normal unmodified canonical app path preserved
```

---

# 7. COMB-005 / PRODUCTION TRUTH FIREWALL

Independently preserve the frozen state:

```text
COMB-005: NOT_APPROVED
approved registry: empty
weights: empty
road_parking_access_score: unavailable / nonnumeric in current production truth
```

This corrective reopen must NOT make the present empirical pipeline SCORE_READY by fabricating road/parking evidence, weights, fallback, neutral score, or approval.

No generic missingness fallback is permitted. The sole historical age fallback remains unchanged and out of corrective scope.

---

# 8. ALLOWED / FORBIDDEN CHANGE SCOPE

Expected production-source changes are primarily:

```text
sitescore-pipeline/src/sitescore_pipeline/integration.py
sitescore-app/src/sitescore_app/gating.py
```

Tests and narrowly scoped corrective docs may be added/updated.

Unrelated frozen production-package changes are forbidden unless explicitly escalated back to Reviewer/user before implementation.

Do not change:

```text
core scoring math
category weights
subfeature weights
dealbreakers
normalization formulas
mid-ECDF
benchmark semantics
provider semantics
spatial semantics
age fallback
COMB-005 approval or weights
empirical calibration
financial engine
```

Do not implement any FAZ 4.1+ feature.

Explicitly forbidden in this corrective branch:

```text
category aggregation
DEMAND_SUBFEATURE_WEIGHTS usage
ACCESSIBILITY_SUBFEATURE_WEIGHTS usage
sitescore-app -> core scoring adapter
CategoryScores production construction
core.analyze()
Location Score
Decision Layer
HTTP/API
auth
payment
report/PDF
UI
queue/deployment
n8n
```

---

# 9. VERSION / DEPENDENCY GOVERNANCE

This is an internal corrective authority hardening.

Required unless a genuinely unavoidable blocker is escalated first:

```text
public signatures: stable
sitescore-pipeline package version: unchanged at 0.1.0
sitescore-app package version: unchanged at 0.1.0
runtime dependency DAG: unchanged
new runtime dependencies: none
```

Do not add `sitescore-app -> sitescore-core` in this corrective reopen. That belongs, if authorized later, to FAZ 4.1.

If a public API or package version change is truly necessary, STOP and report:

```text
VERSION_CHANGE_REQUIRED: 1
```

Do not silently perform it.

---

# 10. FULL REGRESSION / ACTIONS REQUIREMENT

Before returning READY_FOR_REVIEW, validate all packages:

```text
sitescore-app
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Use GitHub Actions evidence that the Reviewer can independently inspect.

If a temporary validation workflow is used, remove it before final review HEAD and report:

```text
validated SHA
final PR HEAD
exact compare validated SHA -> final HEAD
```

Preferred/acceptable post-validation delta:

```text
temporary workflow removed only
```

Any source/tests/docs change after validation requires fresh validation or explicit exact evidence sufficient for re-review.

---

# 11. IMPLEMENTER RETURN CONTRACT

When implementation is complete, update `implementer.md` with at least:

```text
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: AUTHORITY-CORRECTIVE-REOPEN
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: 16427d8bb74611a3de46652d55b708edc93b055b
CODE_BRANCH: corrective/authority-reopen-pipe-app
CODE_HEAD_SHA: <exact>
PR: #N
CONTRACT_CHANGE_REQUIRED: 1
USER_REOPEN_AUTHORIZED: YES
VERSION_CHANGE_REQUIRED: 0
PIPE-AUTH-H001: IMPLEMENTED
APP-H002: IMPLEMENTED
FAZ_4_1_IMPLEMENTATION_STATUS: NOT_STARTED
```

Also report:

- exact changed filenames;
- exact production-source changes;
- public signature/version/dependency status;
- adversarial tests added;
- full package test results;
- Actions workflow/run/job IDs and conclusions;
- validated SHA and final-head comparison;
- COMB-005 registry/weights/current production truth verification;
- scope firewall verification.

Do NOT merge.
Do NOT self-LOCK.
Do NOT start FAZ 4.1.

---

# 12. REVIEWER ACCEPTANCE GATE

Reviewer will independently inspect actual PR metadata, base/head, changed files, full patches, full changed source, relevant unchanged frozen contracts, tests, Actions, dependency metadata, docs, and validated-SHA integrity.

READY_TO_LOCK is possible only if Reviewer can truthfully conclude:

> Factory-owned pipeline and application authority can no longer be redirected after registration through `object.__setattr__`; construction-time trusted origin is bound in closure-private state; downstream execution consumes trusted bindings; copied/forged/mutated objects cannot become scoring authority; COMB-005 and all scoring/calibration semantics remain unchanged; full regression is green; FAZ 4.1 remains not started.

Until then:

```text
PIPE-AUTH-H001: OPEN
APP-H002: OPEN
FAZ 4.1: NOT STARTED
```
