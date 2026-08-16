# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.0
CHECKPOINT_TITLE: Application / Backend Boundary Foundation
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
CODE_BRANCH: faz4/cp4.0-application-boundary-foundation
REVIEWED_HEAD_SHA: NONE
PR: NONE
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
FAZ_3_STATUS: FROZEN
```

---

# 1. PREVIOUS PHASE LOCK VERIFICATION

FAZ 3-FINAL is user-authorized, merged and operationally frozen.

Reviewer independently verified:

```text
PR #7 state: closed
PR #7 merged: true
reviewed branch HEAD: 905e1c8ad35363c9453ffad349fec448ee9bbc5d
merge/main SHA: b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
```

The merge commit has the exact reviewed HEAD as its second parent and current `main` points exactly to:

```text
b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
```

Therefore:

```text
FAZ 3-FINAL: LOCKED
FAZ 3: FROZEN
```

Frozen FAZ 3 phase claim remains:

```text
Mathematically validated scoring engine; empirical validation pending.
```

FAZ 4 MUST consume FAZ 3 as a frozen upstream baseline. Do not mutate frozen FAZ 3 source merely to simplify application integration.

---

# 2. PURPOSE OF CHECKPOINT 4.0

This is the first FAZ 4 checkpoint.

It is an **application/backend architecture foundation checkpoint**, not yet a full web/API/product implementation.

Target outcome:

```text
establish one additive application-layer package/boundary that can safely own
future readiness-gated category aggregation and core invocation
without contaminating frozen FAZ 3 packages or duplicating core semantics.
```

The intended future high-level chain is:

```text
RealDataPipelineResult
  -> application readiness gate
  -> application category aggregation
  -> frozen core adapter / CategoryScores
  -> sitescore-core analyze()
  -> application result envelope
```

Checkpoint 4.0 MUST establish the ownership/DAG/contracts for that chain, but MUST NOT yet implement production HTTP endpoints, auth, payments, report/PDF generation, UI, queues, or commercial delivery orchestration.

---

# 3. AUTHORITATIVE BASELINE / FROZEN INPUTS

Start exactly from:

```text
main @ b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
```

Frozen upstream packages that must remain unchanged unless a genuine contract-change blocker is proven:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
sitescore-benchmarks
sitescore-pipeline
```

Current package versions are `0.1.0`.

Do not edit any frozen upstream production source in this checkpoint.

If application integration is genuinely impossible without changing a frozen contract, STOP and report:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with exact source evidence before making any such change.

Expected outcome is `0`.

---

# 4. CHECKPOINT MODE — FOUNDATION FIRST

Prefer a new additive package:

```text
sitescore-app
```

or an equivalently clear application-layer package only if the current repository contains a stronger canonical naming convention.

Do not place FAZ 4 orchestration inside:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
sitescore-benchmarks
sitescore-pipeline
```

because those are frozen FAZ 3 ownership boundaries.

Checkpoint 4.0 should create only the minimum production surface required to establish the app-layer boundary and future adapter contract.

---

# 5. REQUIRED REPOSITORY / API DISCOVERY BEFORE IMPLEMENTATION

Before designing the new package, inspect actual frozen source for the exact existing interfaces that FAZ 4 will consume.

At minimum inspect and document:

## sitescore-data

```text
RealDataPipelineResult
PipelineStatus
ScoringReadinessResult
NormalizedLocationFeatures
ReadyCategoryScorePayload (if present)
SectorKey
```

## sitescore-core

Inspect actual public types/functions for:

```text
CategoryScores
analyze()
sector/business type configuration
category weights
thresholds / penalties
result schema
```

Do not assume names or signatures from chat memory; use actual current GitHub source.

## sitescore-pipeline

Inspect actual public terminal construction and status/readiness semantics.

The app boundary must consume frozen interfaces exactly as they exist.

---

# 6. FINAL FAZ 4 PACKAGE DAG TARGET

Checkpoint 4.0 must define and enforce the intended additive dependency direction.

Preferred direction:

```text
sitescore-app
  -> sitescore-pipeline
  -> sitescore-data
  -> sitescore-core
```

The app package may depend directly on frozen data/core only where the actual adapter boundary requires it.

It MUST NOT cause reverse dependencies such as:

```text
core -> app
data -> app
providers -> app
spatial -> app
metrics -> app
benchmarks -> app
pipeline -> app
```

No upstream package may import `sitescore_app`.

No cycle is permitted.

Do not add providers/benchmarks/etc. as direct app dependencies unless actual production code in this checkpoint genuinely needs them; prefer consuming the terminal pipeline result rather than reaching behind the pipeline boundary.

---

# 7. READINESS GATE — NON-NEGOTIABLE

The app layer must never make a scoring path available merely because normalized numbers exist.

The future core-call gate must be structurally based on the actual frozen terminal pipeline result.

Required semantic rule:

```text
RealDataPipelineResult.status == SCORE_READY
AND
scoring_readiness exists and is_score_ready == True
```

before any later app-layer category/core scoring may occur.

For:

```text
NOT_SCORE_READY
PIPELINE_ERROR
```

app-layer scoring must be forbidden/fail closed.

No caller-supplied boolean such as:

```text
ready=True
force=True
skip_readiness=True
```

may bypass this boundary.

Do not implement a fallback that scores whatever subset of features is available.

Do not map missing features to zero or generic 50.

---

# 8. SCORE-READY IS NOT SCORED

Preserve the frozen distinction:

```text
SCORE_READY != SCORED
```

Checkpoint 4.0 must not alter FAZ 3 terminal semantics.

`RealDataPipelineResult(SCORE_READY)` is only permission for the application layer to begin category/core scoring.

The application package owns the future transition from score-ready data to scored result.

Do not write scored output back into frozen pipeline/data objects.

---

# 9. CATEGORY AGGREGATION OWNERSHIP — DEFINE, DO NOT DUPLICATE SEMANTICS

Checkpoint 4.0 must establish where future category aggregation lives and how it will consume the exact eight frozen normalized feature slots.

The frozen feature surface is:

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

The app layer may later aggregate these into Demand / Competition / Accessibility / Economics, but this checkpoint MUST NOT invent new weights or duplicate business rules if frozen core configuration already owns them.

Required discovery/audit question:

> Which existing frozen core/config objects are the canonical authority for sector-specific category weights, dealbreakers, and final analysis semantics?

Checkpoint 4.0 should create a typed adapter plan/contracts around those existing authorities, not copy constants into a new package.

If an existing `ReadyCategoryScorePayload` DTO is intended as the app boundary, inspect its actual semantics and use it only if it is truly suitable. Do not mutate it just to fit a preferred design.

---

# 10. ANTI-SELF-ASSERTION / AUTHORITY BOUNDARY

Any new app-layer object representing a validated/ready scoring input must not allow callers to self-assert canonical readiness or arbitrary category scores as if derived from the pipeline.

Avoid public constructors/factories that accept detached inputs such as:

```text
is_ready=True
is_score_ready=True
category_scores=<arbitrary dict>
location_score=<arbitrary number>
readiness_fingerprint=<caller string>
```

and then treat them as canonical production authority.

At 4.0, if you introduce an application scoring-input envelope, it should bind to the actual `RealDataPipelineResult` object and derive its eligibility/state.

Synthetic test fixtures may exist, but must not become production authorization mechanisms.

---

# 11. APPLICATION FOUNDATION CONTRACTS

Implement the minimum typed contracts needed to make the FAZ 4 boundary explicit and testable.

A reasonable shape may include concepts equivalent to:

```text
ApplicationScoringGateState
ApplicationScoringInput
ApplicationScoringEligibility / evaluation
ApplicationStageFailure
```

but exact names are Implementer-owned after source discovery.

Required properties:

- immutable where practical;
- deterministic semantic identity for semantic artifacts if identity is introduced;
- caller cannot directly assert READY state;
- actual terminal pipeline result is retained/bound, not only copied IDs;
- error/not-ready reasons remain typed or canonical, not ambiguous free-form success booleans;
- timestamps must not enter semantic identity unless intrinsically semantic;
- deterministic ordering for any reason/state collections.

Do not overbuild a workflow engine in 4.0.

---

# 12. DO NOT CALL CORE `analyze()` YET UNLESS STRICTLY NEEDED FOR A BOUNDARY TEST

Default checkpoint boundary:

```text
4.0 establishes app package + readiness-gated scoring input boundary.
```

Production category aggregation and actual `sitescore-core analyze()` invocation should normally begin in a later FAZ 4 checkpoint after this boundary is reviewed and locked.

If you believe a minimal controlled adapter call is necessary to prove the boundary, keep it test-only and do not create production scoring orchestration without Reviewer re-scope.

No production Location Score result should be introduced in 4.0 unless reviewer.md is first updated through the protocol.

---

# 13. NO HTTP/API FRAMEWORK YET

Do not add FastAPI, Flask, Django, Starlette, Express-style server dependencies, or route/controller code in 4.0.

The backend HTTP transport boundary belongs to a later checkpoint after the application domain boundary is frozen.

Therefore:

```text
no endpoints
no request handlers
no web server
no OpenAPI surface
no auth middleware
no CORS
```

in this checkpoint.

---

# 14. NO PAYMENT / REPORT / UI / DELIVERY

Explicitly out of scope:

```text
Stripe/payment
checkout
webhooks
PDF/report rendering
email delivery
frontend/UI
customer accounts/authentication
job queues
n8n/commercial automation
billing limits
production deployment
```

These belong to later phases/checkpoints.

---

# 15. EMPIRICAL GATES REMAIN FROZEN-UPSTREAM TRUTH

FAZ 4 must not "fix" FAZ 3 unresolved empirical gates in order to produce a happy-path score.

In particular do not invent:

```text
COMB-005 weights
road/parking normalized substitutes
population allocation
competition reduction
road reduction
equal-area CRS/resolution
sample minimums
coverage thresholds
```

Current canonical production data may legitimately be `NOT_SCORE_READY`.

Use controlled test-local fixtures if a ready input shape must be exercised.

Never change production truth merely to make a FAZ 4 test green.

---

# 16. REQUIRED TESTS / ARCHITECTURE GUARDS

Add tests proving at minimum:

1. new app package is additive and upstream frozen package source remains unchanged;
2. app dependency/import graph follows the intended direction and no upstream package imports app;
3. `NOT_SCORE_READY` pipeline result cannot become an application scoring-ready input;
4. `PIPELINE_ERROR` cannot become application scoring-ready input;
5. actual `SCORE_READY + readiness true` is the only eligible status combination;
6. caller cannot bypass gate with a boolean/status argument;
7. no partial-feature scoring or missing-value neutralization occurs;
8. app retains/binds the actual pipeline result/provenance rather than only accepting detached scores;
9. no production `core.analyze()` invocation exists yet if the checkpoint stays at boundary-only scope;
10. no HTTP/API/payment/report/UI dependencies or source are introduced;
11. all frozen FAZ 3 regression suites continue to pass.

If controlled SCORE_READY fixtures are needed, clearly mark them test-local and construct them using frozen contract semantics without altering upstream production policy.

---

# 17. DOCUMENTATION

Create a checkpoint record in the new app package, for example:

```text
sitescore-app/docs/CHECKPOINT_4_0_APPLICATION_BOUNDARY_FOUNDATION.md
```

Document at minimum:

- exact FAZ 3 frozen input SHA;
- app package ownership;
- final dependency DAG;
- exact upstream interfaces consumed;
- readiness gating semantics;
- `SCORE_READY != SCORED` boundary;
- authority/anti-self-assertion design;
- explicit out-of-scope items;
- roadmap to the next FAZ 4 checkpoint;
- test/validation evidence.

Do not claim FAZ 4 complete or production-ready.

---

# 18. VALIDATION

Run at minimum:

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

Record exact counts only where directly visible.

If using a temporary GitHub Actions workflow, remove it before final review and prove successful validated SHA -> final review HEAD is workflow-removal-only, or precisely explain any tree-neutral delta.

---

# 19. BRANCH / PR / RETURN PROTOCOL

Use exactly one branch:

```text
faz4/cp4.0-application-boundary-foundation
```

against `main` at exact baseline:

```text
b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
```

Open/update exactly one PR.

Do not merge it.
Do not self-LOCK.
Do not start 4.1.

Replace `implementer.md` with detailed evidence containing at minimum:

```text
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.0
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
CODE_BRANCH: faz4/cp4.0-application-boundary-foundation
CODE_HEAD_SHA: <exact SHA>
PR: <number>
CONTRACT_CHANGE_REQUIRED: 0/1
```

Also report:

- changed file list;
- exact new package/dependency graph;
- actual frozen interfaces inspected;
- readiness-gate design;
- authority/constructor analysis;
- whether any production core scoring call exists (expected: NO);
- exact validation runs/SHAs;
- test counts where visible;
- proof that frozen FAZ 3 production source was not modified.

Stop after updating the PR and `implementer.md`.

---

# 20. REVIEWER ACCEPTANCE STANDARD

Reviewer will independently verify:

> FAZ 4 application ownership has been introduced additively on top of the exact frozen FAZ 3 baseline; readiness cannot be bypassed; no frozen upstream source or empirical gate was mutated; no category/core/product semantics were duplicated or prematurely implemented; the package DAG remains clean; the new application boundary is sufficient for a later scoring-adapter checkpoint.

Only after exact review may Reviewer issue SHA-specific:

```text
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
```

User remains sole LOCK authority.
