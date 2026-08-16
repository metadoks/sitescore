# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.1
CHECKPOINT_TITLE: Category Aggregation Authority

REVIEWER_STATE: CONTRACT_CHANGE_REQUIRED
IMPLEMENTER_ACTION: STOP_AWAIT_USER_AUTHORIZATION
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 16427d8bb74611a3de46652d55b708edc93b055b
CODE_BRANCH: NONE
REVIEWED_HEAD_SHA: NONE
PR: NONE

CONTRACT_CHANGE_REQUIRED: 1
FAZ_3_STATUS: FROZEN
FAZ_4_0_STATUS: LOCKED_BUT_INHERITED_AUTHORITY_DEFECT_FOUND
FAZ_4_1_IMPLEMENTATION_STATUS: NOT_STARTED

BLOCKERS:
- PIPE-AUTH-H001: frozen sitescore-pipeline canonical authority is identity-only and post-registration mutable
- APP-H002: sitescore-app 4.0 wrapper/scoring capability bindings are identity-only and post-registration mutable
```

---

# 1. TRANSITION VERIFICATION — FAZ 4.0 LOCK IS FACTUALLY MERGED

Reviewer independently re-fetched GitHub before acting.

Verified actual state:

```text
repo: metadoks/sitescore
main: 16427d8bb74611a3de46652d55b708edc93b055b
PR #8: closed / merged
PR #8 reviewed head: e89ec05f9c0e789670135f0c1ef46ef78707419f
PR #8 base at merge: b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
merge commit: 16427d8bb74611a3de46652d55b708edc93b055b
implementer.md: LOCKED / LOCK_TRANSITION_STATUS=SUCCESS
```

Therefore the historical transition record is factual:

```text
FAZ 4.0 was user-authorized and merged.
```

However, source inspection required for 4.1 exposed a previously unreviewed authority mutation path that invalidates the security/lineage assumption 4.1 would inherit. This is not a reason to silently erase the historical LOCK; it is a lock-integrity defect that must be escalated explicitly.

---

# 2. WHY 4.1 IS NOT BEING STARTED

The FAZ 4 master contract requires 4.1 to consume only a canonical factory-owned `ApplicationScoringInput` and preserve APP-H001's principle:

```text
shape equality is not execution authority
```

Actual current source does not provide a stable immutable execution authority under the project's own adversarial model because the canonical registries prove only object identity, while `frozen=True` dataclasses can still be mutated through `object.__setattr__`.

The existing tests themselves use `object.__new__` + `object.__setattr__` as an accepted adversarial technique. Therefore post-registration `object.__setattr__` mutation is in-scope and cannot be dismissed as a theoretical Python trick.

Starting category aggregation on top of this authority would allow caller-controlled normalized features/category inputs to obtain canonical downstream authority.

---

# 3. PIPE-AUTH-H001 — FROZEN `sitescore-pipeline` AUTHORITY BYPASS

## Affected frozen source

```text
sitescore-pipeline/src/sitescore_pipeline/integration.py
```

Affected factory-owned contracts:

```text
NormalizedFeatureAssembly
ReadinessEvaluation
assemble_normalized_location_features(...)
derive_scoring_readiness(...)
build_real_data_pipeline_result(...)
```

Current closure registries are effectively:

```text
canonical_assemblies[id(obj)] = obj
canonical_readiness[id(obj)] = obj
```

and canonical checks are effectively:

```text
canonical_assemblies.get(id(value)) is value
canonical_readiness.get(id(value)) is value
```

They do not bind the construction-time nested authority payload.

## Reproducible authority path

A caller can obtain a legitimate canonical `ReadinessEvaluation` and then mutate its registered fields with `object.__setattr__`.

Conceptually:

```text
canonical ReadinessEvaluation
    |
    | object.__setattr__(readiness, "assembly", forged_assembly)
    | object.__setattr__(readiness, "result", forged_score_ready_result)
    v
same registered object identity
    |
    v
is_canonical_readiness(...) == True
    |
    v
build_real_data_pipeline_result(...)
```

The terminal factory then reads the mutated public fields:

```text
readiness.assembly
readiness.result.is_score_ready
readiness.assembly.features
```

rather than a closure-bound construction-time snapshot.

A forged assembly can provide caller-controlled normalized features and an empty/altered `direct_results` tuple, weakening `_validate_derived_metrics_coherence(...)`. A forged/mutated readiness result can claim `is_score_ready=True`.

This creates a path to:

```text
caller-controlled normalized feature surface
-> canonical pipeline identity check passes
-> SCORE_READY terminal result
-> exact object returned by frozen pipeline factory
-> sitescore-app registers it as canonical ApplicationPipelineResult
-> canonical ApplicationScoringInput can be granted
```

This can in principle bypass the frozen current production truth that COMB-005 is not approved by inserting a numeric `road_parking_access_score` into the mutated assembly before terminal construction.

This is a true blocker because it can produce:

```text
false scoring authority
missing/unapproved evidence -> numeric scoring input
lineage detachment
wrong production result
```

## Why downstream-only FAZ 4 code cannot correctly fix PIPE-AUTH-H001

`sitescore-app` receives a `ReadinessEvaluation` and delegates to the exact frozen pipeline terminal factory.

If the frozen pipeline factory itself accepts a mutated registered readiness object and returns a terminal as canonical, downstream app code has no authoritative external fact that distinguishes that terminal from an uncompromised one.

A downstream reimplementation of pipeline fingerprints/assembly semantics would duplicate frozen upstream authority and is forbidden architecture.

Therefore correct repair requires changing the frozen `sitescore-pipeline` authority implementation.

```text
CONTRACT_CHANGE_REQUIRED: 1
```

---

# 4. APP-H002 — LOCAL FAZ 4.0 POST-REGISTRATION MUTATION GAP

Actual current source:

```text
sitescore-app/src/sitescore_app/gating.py
```

uses `WeakValueDictionary[id -> object]` identity registries for:

```text
ApplicationPipelineResult
ApplicationScoringInput
```

`require_canonical_application_pipeline_result(...)` verifies that the wrapper object is registered, but does not verify that its current `pipeline_result` is the exact construction-time terminal.

Likewise `require_canonical_application_scoring_input(...)` verifies the scoring-capability object and that its current nested app result is *a* canonical app result, not necessarily the exact construction-time one.

Therefore a registered canonical wrapper can be altered using `object.__setattr__` after registration.

At minimum, the corrective design must bind construction-time authority in closure-private state and fail closed if public object fields no longer match that binding. Later stages must consume closure-resolved canonical material, not mutable current object attributes as authority.

APP-H002 is additive FAZ 4 hardening, but fixing APP-H002 alone is insufficient while PIPE-AUTH-H001 remains in the frozen upstream pipeline.

---

# 5. REQUIRED FROZEN-CONTRACT ESCALATION

No product implementation is authorized by this reviewer record yet.

The user/master authority must explicitly decide whether to reopen the frozen pipeline authority contract for a narrow corrective hardening.

Required correction scope should be minimal and authority-only:

```text
sitescore-pipeline canonical assembly/readiness authority binding
```

No scoring math, normalization math, benchmarks, providers, spatial logic, or new feature work is authorized.

The correction must ensure that factory registration binds the exact construction-time semantic payload, not just object identity.

Acceptable architectural patterns include one of:

1. closure-private immutable construction-time snapshots used by all later canonical factories; or
2. closure-private origin bindings plus exact semantic attestation that detects any post-registration mutation before readiness/terminal execution.

The repair must not rely only on:

```text
frozen dataclass
object id
caller-visible boolean
caller-visible hash with no trusted origin binding
re-running __post_init__ on caller-mutated objects
```

## Version / migration implication

Public signatures may be preservable, but the package is currently a frozen FAZ 3 package at `0.1.0`. Any source change therefore constitutes an explicit frozen-contract reopen even if API shape is unchanged.

Reviewer will not silently choose whether this remains a corrective `0.1.0` freeze replacement or requires a version increment. That governance/version decision belongs to the user/master phase authority as part of the reopen authorization.

---

# 6. MANDATORY ADVERSARIAL REGRESSION TESTS FOR THE CORRECTION

A corrective implementation must prove at least:

```text
A. canonical NormalizedFeatureAssembly mutated after registration -> rejected
B. canonical ReadinessEvaluation.result replaced after registration -> rejected
C. canonical ReadinessEvaluation.assembly replaced after registration -> rejected
D. canonical assembly features replaced with forged SCORE_READY-like surface -> rejected
E. canonical assembly direct_results replaced/emptied after registration -> rejected
F. COMB-005 unavailable cannot become SCORE_READY through post-registration mutation
G. canonical ApplicationPipelineResult.pipeline_result replaced after registration -> rejected
H. canonical ApplicationScoringInput.application_pipeline_result replaced after registration -> rejected
I. copied/reconstructed objects remain rejected
J. normal unmodified canonical paths retain existing behavior
K. current real production COMB-005 truth remains NOT_SCORE_READY
L. no frozen scoring/config math changes
```

Tests must exercise `object.__setattr__` directly because that is the reproduced bypass mechanism.

---

# 7. 4.1 SOURCE INSPECTION FINDINGS RETAINED FOR AFTER CORRECTION

Reviewer completed enough 4.1 source inspection to establish the future implementation direction, but implementation is deliberately not requested yet.

Actual frozen sources establish:

```text
NormalizedLocationFeatures = exactly eight V1 score slots
SectorKey = opaque data/app identifier, does not enforce core vocabulary
core Sector = coffee / restaurant / gym / beauty
core CategoryScores = public DTO, therefore not app execution authority
ReadyCategoryScorePayload = public DTO/local invariant gate, therefore not app execution authority
```

Frozen category-subfeature configuration authority is currently in:

```text
sitescore-core/src/sitescore/config/subfeature_weights.py
```

with:

```text
DEMAND_SUBFEATURE_WEIGHTS
ACCESSIBILITY_SUBFEATURE_WEIGHTS
```

Therefore, after the authority correction is locked, 4.1 is expected to use the actual frozen core configuration rather than duplicate numeric weights. A downstream dependency:

```text
sitescore-app -> sitescore-core==0.1.0
```

is likely required at 4.1 because the category aggregation config authority physically lives in core. This is additive DAG direction and does not by itself require an upstream contract change.

No 4.1 branch has been authorized or requested in this record because the inherited scoring permission is currently unsafe.

---

# 8. STOP CONDITION

```text
FAZ 4.1 IMPLEMENTATION: NOT STARTED
FAZ 4.2: NOT STARTED
FAZ 5: FORBIDDEN
```

Implementer must not create a 4.1 feature branch or category aggregation code from this record.

Wait for explicit user/master decision on the frozen-contract reopen required by `PIPE-AUTH-H001`.
