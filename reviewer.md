# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.1
CHECKPOINT_TITLE: API Consumer Reliability + Execution Lifecycle

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
CODE_BRANCH: faz5/5-1-api-consumer-lifecycle
REVIEWED_HEAD_SHA: NONE
PR: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: NONE
RESOLVED_REVIEW_FINDING: F51-CANONICAL-SCORED-PATH-H001
REVIEWER_CONTRACT_CORRECTION_APPLIED: YES
```

---

# 1. REVIEWER DECISION ON IMPLEMENTER BLOCK

Implementer correctly stopped before writing product code and reported:

```text
F51-CANONICAL-SCORED-PATH-H001
CONTRACT_CHANGE_REQUIRED: 1
```

Reviewer independently inspected the exact frozen source at current `main` and confirms the source finding.

The frozen road/parking composite is intentionally not empirically approved:

```text
RoadParkingComponentArtifact
- production AVAILABLE is forbidden
- production numeric score is forbidden

RoadParkingCompositePolicy
- caller-created APPROVED is forbidden
- unapproved policy cannot carry weights
- composition_method must remain UNRESOLVED

COMB005_V1_POLICY.approval_state = NOT_APPROVED
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 = ()

evaluate_road_parking_composite(...)
-> RoadParkingCompositeResult.state = POLICY_NOT_APPROVED
-> score = None
```

The frozen pipeline maps that result to:

```text
road_parking_access_score.value = None
availability = UNKNOWN
score_eligibility = INELIGIBLE
calibration_state = UNCALIBRATED
road_parking_composite_policy_version = None
```

The frozen V1 readiness validator requires every normalized feature and explicitly adds:

```text
ROAD_PARKING_COMPOSITE_UNAVAILABLE
```

when the road/parking feature is not AVAILABLE + ELIGIBLE + CALIBRATED with a resolved composite policy version.

Therefore the current canonical V1 production chain truthfully produces:

```text
is_score_ready = False
PipelineStatus.NOT_SCORE_READY
ApplicationScoringGateState.NOT_SCORE_READY
```

and cannot legitimately reach the scored application/core path while COMB-005 remains unapproved.

This is not a newly discovered product defect. It is a deliberate frozen product-validity boundary consistent with:

> Mathematically validated scoring engine; empirical validation pending.

Reviewer therefore does NOT authorize reopening or modifying frozen COMB-005/benchmark/readiness semantics merely to make a 5.1 scored integration test green.

---

# 2. CONTRACT CORRECTION

The original 5.1 Reviewer contract incorrectly required both:

```text
A. use only the real frozen public authority chain
B. prove at least one real scored/completed integration path now
```

Those requirements are mutually incompatible with the current frozen source.

The authoritative correction is:

```text
CURRENT REAL PRODUCTION CANONICAL EXECUTION TARGET:
NOT_SCORE_READY

CURRENT REAL PRODUCTION COMPLETED/SCORED TARGET:
NOT CLAIMED / NOT REACHABLE UNDER THE LOCKED COMB-005 BASELINE
```

`completed` remains a required V1 lifecycle state because it is part of the durable API/resource contract for a future legitimately score-ready canonical execution. However 5.1 MUST NOT fabricate a canonical scored result, fake an approved COMB-005 result, bypass readiness, monkeypatch internal authority, or reopen frozen semantics to demonstrate that state today.

Accordingly:

```text
CONTRACT_CHANGE_REQUIRED: 0
```

for implementation under this corrected Reviewer contract.

The prior Implementer `CONTRACT_CHANGE_REQUIRED: 1` is accepted as the correct escalation signal for the superseded acceptance clause; it does not require a frozen product-contract change now that Reviewer has corrected the 5.1 acceptance requirement.

---

# 3. ALL OTHER 5.1 ARCHITECTURE REMAINS REQUIRED

The previous 5.1 contract remains authoritative except where explicitly replaced by this correction.

Implement only FAZ 5.1 in:

```text
sitescore-api/**
```

Branch remains:

```text
faz5/5-1-api-consumer-lifecycle
```

Base remains exactly:

```text
92d00cda34d337ce5c4e172d5184c9e3f1f55b11
```

Do not start 5.2.
Do not modify frozen FAZ 3 / FAZ 4 runtime semantics.
Do not merge.
Do not self-LOCK.

Required stack remains:

```text
FastAPI 0.140.0
Pydantic 2.13.4
SQLAlchemy 2.0.51
Alembic 1.18.5
psycopg[binary] 3.3.4
Celery 5.6.3
redis 7.4.1
httpx 0.28.1
pytest 8.4.2
```

If the actual resolver/runtime proves those selected dependency decisions incompatible in a way that requires architecture substitution:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

and STOP.

---

# 4. DURABLE LIFECYCLE AUTHORITY — UNCHANGED

Non-negotiable ownership remains:

```text
PostgreSQL = durable lifecycle / analysis / idempotency / auth metadata truth
Redis = broker transport only
Celery = execution infrastructure only
Celery AsyncResult = NOT public lifecycle truth
```

Required durable concepts remain:

```text
consumers
service API keys
analyses
dispatch outbox
```

The initial analysis row and dispatch-outbox intent must be committed atomically.

DB commit followed by untracked fire-and-forget broker publish is forbidden.

Pending dispatch must survive broker failure/process restart and must be safely redispatchable using the same persisted internal task ID.

Celery delivery is at-least-once. PostgreSQL execution claim/locking plus durable state transitions must prevent concurrent duplicate execution from creating two logical results or regressing terminal state.

---

# 5. AUTH / CONSUMER ISOLATION / IDEMPOTENCY — UNCHANGED

Use scoped Bearer service API keys.

```text
POST /v1/analyses -> analysis:write
GET  /v1/analyses/{analysis_id} -> analysis:read
```

Raw secrets must not be stored. Use a one-way server-owned verification scheme, revocation/active checks and constant-time comparison.

Every analysis belongs to one consumer.

Foreign analysis UUID and missing analysis UUID must both project:

```text
404 analysis_not_found
```

without cross-consumer existence leakage.

`Idempotency-Key` remains mandatory for POST.

Required semantics:

```text
same consumer + same key + same canonical validated payload
-> same analysis_id
-> no second analysis row
-> no second logical outbox intent

same consumer + same key + different canonical payload
-> 409 idempotency_conflict

same key across different consumers
-> independent resources
```

A PostgreSQL UNIQUE constraint remains mandatory; Python pre-check alone is insufficient.

Canonical request hash remains SHA-256 over deterministic validated request JSON only and must exclude operational/auth identities.

---

# 6. PUBLIC LIFECYCLE STATE MACHINE — CLARIFIED

V1 public states remain exactly:

```text
queued
running
completed
not_score_ready
failed
timed_out
```

Terminal:

```text
completed
not_score_ready
failed
timed_out
```

Nonterminal:

```text
queued
running
```

Cancellation remains:

```text
NOT_SUPPORTED
```

`completed` is a legitimate lifecycle state in the API/domain model, but current frozen production execution must not claim it unless a genuinely canonical score-ready authority object is produced by the frozen chain.

Under the current locked COMB-005 baseline, the real production integration expectation is:

```text
queued -> running -> not_score_ready
```

A generic persistence/state-machine unit test may verify that the transition graph structurally contains:

```text
running -> completed
```

but that test is NOT evidence that the current canonical production executor can reach `completed`, and it must not rely on a forged `CanonicalAnalysisResult` to validate production execution.

Production code must not expose a route/repository shortcut such as:

```text
complete(analysis_id, arbitrary_dict)
```

that lets plain JSON bypass canonical execution authority.

Any production completed-result write path must require a server-owned canonical execution outcome produced only from exact frozen application/core authority. If current source cannot instantiate that outcome legitimately, the path may remain structurally dormant/unreached in 5.1; do not weaken its guard for test convenience.

---

# 7. CORRECTED CANONICAL EXECUTION REQUIREMENT

5.1 still MUST implement a real production execution-service boundary. It may not be lifecycle infrastructure driven only by a fake test executor.

Required high-level chain remains:

```text
durable validated request intent
-> server-owned provider/deployment configuration
-> frozen provider acquisition / evidence
-> frozen metrics / benchmark normalization
-> frozen canonical normalized-feature assembly
-> frozen canonical readiness
-> frozen pipeline terminal factory
-> frozen application pipeline factory
-> frozen application gate
```

For the current baseline the required real canonical terminal behavior is:

```text
ApplicationScoringGateState.NOT_SCORE_READY
-> public lifecycle state not_score_ready
-> persist canonical readiness/gate reason projection
-> DO NOT invoke core analyze
```

The execution service must not stop before reaching the real frozen pipeline/application gate.

Provider/HTTP/network responses may use deterministic test fakes only at external transport/provider boundaries. Internal canonical benchmark/pipeline/application authority may not be replaced by fabricated DTOs.

The test must prove, through the real frozen public factories, that current COMB-005 truth propagates to `not_score_ready`.

Required assertions include at least:

```text
canonical RoadParkingCompositeResult = POLICY_NOT_APPROVED
canonical road_parking_access_score has no numeric value
canonical readiness is_score_ready = False
ROAD_PARKING_COMPOSITE_UNAVAILABLE present
canonical RealDataPipelineResult.status = NOT_SCORE_READY
canonical ApplicationScoringGateState = NOT_SCORE_READY
core analyze invocation count = 0
public durable terminal state = not_score_ready
no fake zero/category scores/decision/confidence/result persisted
```

If actual public APIs prevent even this canonical NOT_SCORE_READY path from being composed without frozen semantic mutation/private unsupported authority:

```text
CONTRACT_CHANGE_REQUIRED: 1
IMPLEMENTER_STATE: BLOCKED_FOR_REVIEW
```

and STOP.

---

# 8. COMPLETED STATE AUTHORITY GUARD

Because current production scoring is intentionally unavailable, 5.1 must explicitly harden against false completion.

Add architecture/security tests proving at minimum:

```text
worker cannot mark completed from stored request JSON alone
worker cannot mark completed from caller-supplied result JSON
worker cannot mark completed from a fabricated analysis_fingerprint
worker cannot mark completed from a fabricated CategoryScores / AnalysisInput substitute
worker cannot bypass application gate
plain lifecycle repository/service callers cannot attach arbitrary successful result payload as canonical authority
not_score_ready can never be persisted together with a scored result body
```

If production completed persistence needs a typed internal capability/outcome, its construction must be closed/server-owned and bound to exact canonical application analysis authority.

Do not create a test-only backdoor in production code.

---

# 9. PIPELINE ERROR / FAILURE / TIMEOUT SEMANTICS — UNCHANGED

Canonical pipeline failure must map to:

```text
failed
```

and never to `not_score_ready` or empty success.

Unexpected execution exceptions must persist only safe machine error metadata.

Timeout remains a durable PostgreSQL deadline concept:

```text
queued/running + now >= deadline_at
-> timed_out
```

GET/repository retrieval must be able to reconcile expiry atomically even if Celery/Redis is unavailable.

Late worker success/not-score-ready must not overwrite a terminal `timed_out`, `failed`, `completed` or prior `not_score_ready` record.

---

# 10. CORRECTED REQUIRED TEST MATRIX

All original auth, isolation, idempotency, PostgreSQL race, outbox, broker, migration, OpenAPI, timeout and full-regression tests remain required.

The worker/state-machine section is corrected to require:

```text
[ ] queued -> running state transition
[ ] real canonical queued -> running -> not_score_ready integration
[ ] canonical NOT_SCORE_READY proves core analyze not invoked
[ ] pipeline error -> failed
[ ] unexpected safe execution failure -> failed
[ ] deadline expiration -> timed_out
[ ] terminal state cannot regress
[ ] late worker cannot overwrite timed_out
[ ] duplicate worker delivery is concurrency-safe
[ ] worker broker payload contains analysis_id only/minimal locator
[ ] durable request intent is reconstructed server-side
[ ] PostgreSQL execution claim prevents simultaneous canonical execution
[ ] completed exists in lifecycle enum/transition model
[ ] completed persistence has a canonical-authority guard
[ ] arbitrary JSON cannot drive completed
```

Removed/superseded acceptance requirement:

```text
[REMOVED] at least one current real scored/completed integration path
```

It is replaced by:

```text
[REQUIRED] at least one current real canonical NOT_SCORE_READY integration path
           through frozen benchmark/pipeline/application gate semantics
```

Infrastructure-only tests may use narrow fakes for broker faults, clock/time, repository races, external HTTP/provider transport and dispatch behavior. Such fakes must not be presented as proof of current canonical scored execution.

---

# 11. API / N8N CONSUMER CONTRACT — UNCHANGED

POST success still means durable resource acceptance, not scoring completion:

```text
POST /v1/analyses
Authorization: Bearer ...
Idempotency-Key: ...
-> 202
-> fresh request_id
-> durable analysis_id
-> current lifecycle state
```

GET remains owner-scoped polling truth from PostgreSQL.

For the current frozen product baseline, a successfully executed real analysis is expected to terminate as:

```text
not_score_ready
```

with canonical reason information, not as `completed`.

Document prominently for future n8n consumers:

```text
not_score_ready is a terminal business/data-readiness outcome
not an infrastructure failure
not a zero score
not a completed scored result
```

V1 callback/webhook remains NONE.
V1 integration model remains polling.

---

# 12. MIGRATIONS / CLEAN VALIDATION — UNCHANGED

Use real PostgreSQL for migration/schema/race tests; SQLite substitution is insufficient.

Use Redis/Celery integration evidence for broker/worker behavior.

Run fresh:

```text
sitescore-api full unit/integration suite
sitescore-app
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Historical frozen reference remains 1375 tests but must not be copied as fresh evidence.

Temporary validation workflow is allowed only for validation and must be removed from final product candidate unless Reviewer explicitly accepts permanent CI scope.

---

# 13. DOCUMENTATION CORRECTION REQUIREMENT

`sitescore-api/docs/CHECKPOINT_5_1_API_CONSUMER_LIFECYCLE.md` must explicitly record:

```text
current COMB-005 policy is NOT_APPROVED
current canonical production scoring readiness is NOT_SCORE_READY
current real production lifecycle terminal is expected to be not_score_ready
completed remains a modeled future-capable terminal state
5.1 does not claim current empirical road/parking approval
5.1 does not forge a scored result to exercise completed
empirical validation remains pending
```

Do not describe `completed` as currently reachable through the locked real production chain unless source truth changes under a separately authorized future contract.

---

# 14. GIT / HANDOFF PROTOCOL

Continue on the already-created branch:

```text
faz5/5-1-api-consumer-lifecycle
```

It is independently verified to still point exactly at:

```text
92d00cda34d337ce5c4e172d5184c9e3f1f55b11
```

No product delta currently exists.

Implement the corrected 5.1 contract, then:

1. push the same branch,
2. open one PR to `main`,
3. update `implementer.md`,
4. record exact base/head/PR,
5. record migrations/schema/DB/Redis/Celery/auth/idempotency/outbox/canonical-NOT_SCORE_READY evidence,
6. record fresh test counts and validation run IDs if used,
7. set `CONTRACT_CHANGE_REQUIRED: 0` unless a new genuine frozen-semantic blocker is discovered,
8. set `DESIGN_DECISION_REVIEW_REQUIRED: 0` unless a selected-stack incompatibility is discovered,
9. set `IMPLEMENTER_STATE: READY_FOR_REVIEW`,
10. STOP.

Do not merge.
Do not LOCK.
Do not start 5.2.

---

# 15. CURRENT REVIEW DECISION

```text
REVIEW_DECISION: CONTRACT_CORRECTED_IMPLEMENTATION_REAUTHORIZED
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.1
EXPECTED_BASE_SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
CODE_BRANCH: faz5/5-1-api-consumer-lifecycle
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: NONE
RESOLVED_REVIEW_FINDING: F51-CANONICAL-SCORED-PATH-H001
```

Reviewer STOP.
