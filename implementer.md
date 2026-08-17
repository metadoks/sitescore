# SiteScore AI — Implementer → Reviewer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.1
CHECKPOINT_TITLE: API Consumer Reliability + Execution Lifecycle

IMPLEMENTER_STATE: READY_FOR_REVIEW
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
CODE_BRANCH: faz5/5-1-api-consumer-lifecycle
CODE_HEAD_SHA: 7e2399cdb4bbc7d43f24625427bf7eb88534a922
PR: #17
PR_STATE: OPEN
PR_MERGEABLE: TRUE
PR_MERGED: FALSE

REVIEWER_STATE_SEEN: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION_SEEN: IMPLEMENT
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS_REPORTED_BY_IMPLEMENTER: NONE
RESOLVED_BLOCKERS: F51-CANONICAL-SCORED-PATH-H001_BY_REVIEWER_EXPECTATION_CORRECTION

VALIDATED_SHA: c34fd71648141a66b83b1ac275b6ea4fdb606090
VALIDATION_WORKFLOW: faz5-5-1-exact-integration-validation
VALIDATION_RUN_ID: 32032263495
VALIDATION_JOB_ID: 95394699756
VALIDATION_CONCLUSION: SUCCESS
TEMP_VALIDATION_WORKFLOW_REMOVED: YES
VALIDATED_TO_FINAL_DELTA: ONLY .github/workflows/faz5-5-1-validation.yml REMOVAL
VALIDATED_TO_FINAL_COMMITS: 1

SITESCORE_API_TESTS: 86 PASS
FROZEN_REGRESSION_TESTS: 1375 PASS
COMBINED_TESTS: 1461 PASS
```

## 1. Reviewer expectation correction resolved prior blocker

Implementer initially reported `F51-CANONICAL-SCORED-PATH-H001` after source review proved the frozen production COMB-005 authority cannot currently create a score-ready road/parking feature:

```text
COMB005_V1_POLICY.approval_state = NOT_APPROVED
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 = ()
canonical RoadParkingCompositeResult.state = POLICY_NOT_APPROVED
canonical RoadParkingCompositeResult.score = None
```

The frozen pipeline regression itself proves current canonical production readiness includes:

```text
ScoringReadinessReason.ROAD_PARKING_COMPOSITE_UNAVAILABLE
is_score_ready = False
```

Reviewer subsequently corrected the 5.1 expectation instead of reopening frozen semantics. Current authoritative target is therefore the real canonical production path:

```text
queued
-> running
-> not_score_ready
```

`completed` remains a modeled V1 lifecycle state but is NOT claimed currently reachable under the locked model. It may be persisted only from a genuine canonical frozen application analysis authority if a future frozen state becomes ELIGIBLE.

Therefore the prior contract blocker is resolved without frozen mutation:

```text
F51-CANONICAL-SCORED-PATH-H001: RESOLVED BY REVIEWER EXPECTATION CORRECTION
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
```

No zero score, neutral fill, fabricated SCORE_READY terminal, forged readiness, or manufactured canonical result was introduced.

---

## 2. Exact branch / base / PR

```text
base branch: main
expected/live base SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
code branch: faz5/5-1-api-consumer-lifecycle
final head: 7e2399cdb4bbc7d43f24625427bf7eb88534a922
PR: #17
PR state: OPEN
PR mergeable: TRUE
PR merged: FALSE
changed files: 37
```

Final base-to-head diff contains only:

```text
sitescore-api/**
```

No final `.github/workflows/**` file remains.
No frozen FAZ 3 / FAZ 4 package file is modified.
No FAZ 5.2/report/payment/n8n/FAZ 6 product file is present.

---

## 3. Package / dependency contract

Package:

```text
sitescore-api==0.2.0
API version: /v1
```

Exact direct runtime dependencies:

```text
fastapi==0.140.0
pydantic==2.13.4
SQLAlchemy==2.0.51
alembic==1.18.5
psycopg[binary]==3.3.4
celery==5.6.3
redis==7.4.1
sitescore-core==0.1.0
sitescore-data==0.1.0
sitescore-metrics==0.1.0
sitescore-benchmarks==0.1.0
sitescore-pipeline==0.1.0
sitescore-app==0.1.0
```

Exact dev/test dependencies:

```text
httpx==0.28.1
pytest==8.4.2
```

No 5.2+ report/OpenAI/PDF/S3/payment dependencies were introduced.

---

## 4. Scoped Bearer service authentication

Implemented machine-consumer key format:

```text
ssk1_<public-key-id>.<high-entropy-secret>
```

Security properties:

```text
public lookup key id != secret
raw secret never stored in PostgreSQL
HMAC-SHA256 verifier stored using server-owned pepper
constant-time hmac.compare_digest verification
key active/revoked checks
consumer active check
raw Authorization token not persisted in analysis/outbox/task payloads
```

Supported scope vocabulary:

```text
analysis:write
analysis:read
report:write
report:read
```

5.1 route enforcement:

```text
POST /v1/analyses -> analysis:write
GET /v1/analyses/{analysis_id} -> analysis:read
```

Stable auth errors and `WWW-Authenticate: Bearer` behavior are covered by tests.

---

## 5. Consumer isolation

Every durable analysis row is owned by one `consumer_id`.

GET uses an owner-scoped query. These cases intentionally share one public concept:

```text
missing analysis
foreign consumer analysis
-> 404 analysis_not_found
```

Idempotency uniqueness is also consumer-scoped.

---

## 6. Durable PostgreSQL idempotency

`Idempotency-Key` is mandatory and limited to exactly 200 UTF-8 bytes maximum. Blank, control-character and oversized keys are rejected.

Canonical request hash:

```text
validated Pydantic model
-> model_dump(mode="json", exclude_none=False)
-> deterministic JSON
   sort_keys=True
   separators=(",", ":")
   ensure_ascii=False
   allow_nan=False
-> UTF-8
-> SHA-256
```

Operational identities are excluded because only caller request intent is hashed.

PostgreSQL owns a UNIQUE constraint on:

```text
(consumer_id, idempotency_key)
```

Race semantics proven against real PostgreSQL:

```text
same consumer + same key + same payload
-> exactly one analyses row
-> exactly one logical analysis_id
-> exactly one durable outbox intent
-> replay gets fresh request_id

same consumer + same key + different payload
-> exactly one winner
-> other request deterministically resolves to 409 idempotency_conflict

same key across consumers
-> independent resources
```

No in-memory-only uniqueness authority exists.

---

## 7. Transactional outbox / broker recovery

Durable acceptance transaction atomically inserts:

```text
analysis(state=queued)
dispatch_outbox(analysis_id, persisted internal task_id)
COMMIT
```

Only after commit does best-effort Celery publication occur.

Proven behavior:

```text
broker unavailable after DB commit -> analysis remains durable
pending outbox survives
redispatch reuses persisted task_id
successful publication marks outbox dispatched
same-payload POST replay does not create second logical analysis
```

Celery task payload contains only:

```text
analysis_id
```

No raw API key, Authorization header or caller-authored canonical result enters broker messages.

---

## 8. PostgreSQL is public lifecycle truth

Durable model includes:

```text
consumers
service_api_keys
analyses
dispatch_outbox
```

Public states are exactly:

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

Redis is broker transport only.
Celery result backend is disabled as product truth.
`AsyncResult` is not used by GET.

Validated Celery configuration includes:

```text
task_ignore_result = true
results = disabled://
```

---

## 9. Duplicate-delivery execution guard

Worker uses:

```text
PostgreSQL session-level advisory lock derived from analysis_id
+ row-level FOR UPDATE state checks
+ terminal immutability
```

A real hardening issue was discovered by PostgreSQL concurrency CI:

```text
session-level advisory lock acquired
-> SQLAlchemy Session.commit()
-> physical connection could return to pool
-> second worker could check out same physical PostgreSQL connection
-> advisory lock is reentrant on the same PostgreSQL session
```

This could allow concurrent duplicate execution despite the intended lock.

Fix:

```text
with database.engine.connect() as connection:
    Session(bind=connection, ...)
```

The physical PostgreSQL connection is now pinned for the complete advisory-lock lifetime.

Real duplicate-delivery concurrency test after the fix proves:

```text
first worker owns execution claim
second simultaneous worker -> busy/no concurrent execution
executor invocation count = 1
```

Celery/Redis are correctly described as at-least-once infrastructure, not exactly-once execution.

---

## 10. Timeout / terminal state integrity

Server-owned configured deadline is persisted as `deadline_at`.

Defaults:

```text
analysis deadline = 900 seconds
Celery soft time limit = 840 seconds
Celery hard time limit = 900 seconds
poll Retry-After = 3 seconds
```

Timeout reconciliation occurs through:

```text
worker checks
periodic reconciliation task
GET owner-scoped retrieval
```

Therefore timeout truth does not depend on Redis availability or worker cleanup.

Late workers cannot overwrite a terminal `timed_out`, `failed`, `completed`, or `not_score_ready` state.

V1 cancellation remains:

```text
NOT_SUPPORTED
```

---

## 11. Canonical execution authority

`ExecutionEvidenceSource` is server/deployment-owned. Caller JSON cannot submit trusted provider manifests, benchmark authority, coordinates, policy identities or canonical result payloads.

Real execution chain implemented in `sitescore-api`:

```text
server-owned typed evidence + benchmark artifacts
-> frozen sitescore-metrics measurement functions
-> frozen benchmark normalize_feature
-> frozen COMB-005 evaluation
-> frozen normalized feature assembly
-> frozen scoring readiness
-> frozen build_application_pipeline_result
-> frozen application scoring gate
```

Current locked COMB-005 truth produces canonical NOT_SCORE_READY.

The authoritative integration test uses public frozen constructors/factories rather than fabricating internal terminal DTOs and verifies:

```text
canonical RoadParkingCompositeState = POLICY_NOT_APPROVED
canonical road_parking_access_score.value = None
canonical readiness is_score_ready = False
ROAD_PARKING_COMPOSITE_UNAVAILABLE present
ApplicationScoringGateState = NOT_SCORE_READY
core analyze invocation count = 0
worker persists state = not_score_ready
result_body = SQL NULL / no scored result
canonical readiness projection persisted
```

---

## 12. Guarded `completed` state

`completed` is modeled because it is part of the V1 lifecycle contract, but current frozen model reachability is NOT claimed.

`CanonicalCompletedOutcome` is server-factory owned. Persistence requires an exact canonical `ApplicationAnalysisResult` accepted by frozen application authority.

These cannot authorize `completed`:

```text
plain JSON
stored request payload
analysis_fingerprint
caller flag
manually allocated wrapper
detached CanonicalAnalysisResult-like object
```

If a future frozen upstream state becomes genuinely ELIGIBLE, execution continues only through:

```text
build_application_scoring_input
-> aggregate_application_category_scores
-> build_application_core_analysis_input
-> analyze_application_core_input
-> canonical ApplicationAnalysisResult
-> guarded completed persistence
```

---

## 13. JSONB SQL-NULL hardening found by integration CI

The canonical worker integration reached PostgreSQL persistence and exposed a real SQLAlchemy/PostgreSQL semantic issue:

```text
Python None on JSONB
-> default SQLAlchemy JSON encoding
-> JSON literal null
-> SQL column IS NOT NULL evaluates TRUE
```

That contradicted the DB CHECK requiring `not_score_ready` to have no scored `result_body`.

Fix:

```text
result_body JSONB(none_as_null=True)
readiness_body JSONB(none_as_null=True)
```

Python `None` now becomes SQL NULL where nullable terminal payload semantics require it.

The real canonical worker persistence test passes after this fix.

---

## 14. Alembic migration authority

Added package-owned Alembic environment and initial migration.

Production does not use SQLAlchemy `create_all()` as schema authority.

Real PostgreSQL validation proves:

```text
empty DB -> alembic upgrade head: PASS
schema tables/constraints/indexes present: PASS
downgrade base: PASS
fresh re-upgrade head: PASS
```

---

## 15. Public API / future n8n polling contract

POST success:

```text
HTTP 202
api_version
fresh request_id
stable durable analysis_id
current lifecycle state
```

GET owner success:

```text
HTTP 200
api_version
fresh request_id
analysis_id
state
created_at
updated_at
state-specific result/readiness/error
```

For queued/running responses:

```text
Retry-After: 3
```

Machine-consumer retry rules documented:

```text
POST transport/5xx uncertainty -> retry SAME payload + SAME Idempotency-Key
202 -> durable resource exists; poll GET
queued/running -> poll again
completed -> terminal scored result, only if canonical authority exists
not_score_ready -> terminal readiness/business-data outcome, not infrastructure failure
failed -> terminal execution failure
timed_out -> terminal deadline result
401/403/409/422 -> do not blindly retry without correcting condition
```

V1 callback/webhook support:

```text
NONE
```

n8n itself is not implemented in 5.1.

---

## 16. Runtime OpenAPI

Runtime-generated OpenAPI tests prove:

```text
exact /v1 analysis paths
Bearer security scheme
Idempotency-Key header documentation
exact lifecycle state enum
202 durable resource schema
401/403/404/409/422/500/503 declarations as applicable
internal task_id absent
raw API key secret schema absent
no report/payment/n8n endpoints
```

No handwritten schema divergence is introduced.

---

## 17. Authoritative exact integration validation

Temporary workflow:

```text
.github/workflows/faz5-5-1-validation.yml
workflow name: faz5-5-1-exact-integration-validation
```

Authoritative successful run:

```text
run ID: 32032263495
job ID: 95394699756
validated SHA: c34fd71648141a66b83b1ac275b6ea4fdb606090
status: completed
conclusion: SUCCESS
```

Exact imported/runtime versions proven:

```text
Python 3.11.15
PostgreSQL server 16.15
Redis server 7.4.10
FastAPI 0.140.0
Pydantic 2.13.4
SQLAlchemy 2.0.51
Alembic 1.18.5
psycopg 3.3.4
Celery 5.6.3
redis-py 7.4.1
HTTPX 0.28.1
pytest 8.4.2
Shapely 2.1.2
pyproj 3.7.2
```

Real Celery/Redis evidence:

```text
Celery worker started successfully
broker transport = redis://127.0.0.1:6379/0
results = disabled://
registered SiteScore tasks visible
celery inspect ping = pong / 1 node online
sitescore_api.reconcile_timeouts task received and succeeded
```

---

## 18. Fresh test evidence

Authoritative successful exact-SHA counts:

```text
sitescore-api:         86 PASS
sitescore-app:         19 PASS
sitescore-pipeline:    53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics:     67 PASS
sitescore-spatial:    180 PASS
sitescore-providers:  418 PASS
sitescore-data:       361 PASS
sitescore-core:        86 PASS
--------------------------------
frozen regression:  1375 PASS
combined total:     1461 PASS
```

One Starlette/TestClient deprecation warning occurred in the API suite. All 86 API tests passed.

Expected PostgreSQL duplicate-key ERROR log entries occurred during intentional UNIQUE race/idempotency tests and are not test failures; the application resolved them through authoritative conflict re-read and the run concluded SUCCESS.

Redis emitted a GitHub-runner `vm.overcommit_memory` host warning; the Redis service remained healthy and the real worker smoke/test passed.

---

## 19. Superseded hardening runs

Earlier validation attempts are not acceptance evidence:

```text
run 32031391489 / SHA 0d8cc072...
82 PASS / 4 failures
- exposed advisory-lock physical-connection pooling issue
- plus three fixture/methodology failures

run 32031700318 / SHA a5ec056...
84 PASS / 2 fixture failures
- duplicate-delivery concurrency already PASS after connection pin fix

run 32031827115 / SHA 409ed71...
84 PASS / 2 source-lineage fixture failures

run 32032024898 / SHA 78822feb...
85 PASS / 1 failure
- canonical path reached DB persistence
- exposed JSONB None -> JSON null / SQL NULL semantic issue
```

Only `32032263495` is authoritative acceptance evidence.

---

## 20. Validated SHA -> final head closure

After successful validation, temporary workflow was deleted.

Exact closure:

```text
c34fd71648141a66b83b1ac275b6ea4fdb606090
->
7e2399cdb4bbc7d43f24625427bf7eb88534a922
```

GitHub compare:

```text
status: ahead
ahead_by: 1
total commits: 1
changed files: 1
.github/workflows/faz5-5-1-validation.yml: REMOVED
```

Therefore no product source, test, migration, dependency, API contract or documentation semantic change occurred after the fully successful validation SHA.

Final PR diff contains no workflow file.

---

## 21. Frozen / scope audit

Final base-to-head comparison:

```text
92d00cda34d337ce5c4e172d5184c9e3f1f55b11
->
7e2399cdb4bbc7d43f24625427bf7eb88534a922
```

reports:

```text
37 changed files
all under sitescore-api/**
```

Frozen source mutation:

```text
sitescore-core/**: NONE
sitescore-data/**: NONE
sitescore-providers/**: NONE
sitescore-spatial/**: NONE
sitescore-metrics/**: NONE
sitescore-benchmarks/**: NONE
sitescore-pipeline/**: NONE
sitescore-app/**: NONE
```

Unauthorized later scope:

```text
Stripe/payment: NONE
n8n workflow: NONE
report endpoints/package: NONE
OpenAI narrative: NONE
Jinja2/WeasyPrint/Matplotlib: NONE
S3 report storage: NONE
FAZ 5.2+: NONE
FAZ 6+: NONE
```

---

## 22. Final self-audit

```text
Reviewer corrected 5.1 expectation honored: YES
Prior F51 blocker resolved without frozen mutation: YES
PostgreSQL sole durable lifecycle truth: YES
Alembic real PostgreSQL migration evidence: YES
Redis broker-only role: YES
Celery result backend non-authority: YES
scoped Bearer auth: YES
raw key secret non-persistence: YES
consumer isolation: YES
DB-backed idempotency uniqueness/races: YES
transactional outbox: YES
persisted task ID redispatch: YES
PostgreSQL duplicate-execution claim: YES
physical connection lock-lifetime hardening: YES
public lifecycle exact: YES
terminal immutability: YES
durable timeout reconciliation: YES
V1 cancellation unsupported documented: YES
real canonical NOT_SCORE_READY path: YES
core analyze calls on current NOT_SCORE_READY path: 0
arbitrary JSON/fingerprint completed authority: FORBIDDEN
current locked completed reachability claimed: NO
PostgreSQL JSONB SQL-NULL semantics hardened: YES
runtime OpenAPI matches behavior: YES
future n8n polling/retry contract documented: YES
callback/webhook claim: NONE
fresh exact integration validation: SUCCESS
sitescore-api tests: 86 PASS
frozen regression: 1375 PASS
combined: 1461 PASS
temporary validation workflow removed: YES
validated -> final semantic product delta: NONE
final scope only sitescore-api/**: YES
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: NONE
```

Canonical product validity statement remains:

> Mathematically validated scoring engine; empirical validation pending.

## 23. Next authority

Checkpoint 5.1 is returned to Reviewer for independent exact-head audit at:

```text
PR #17
7e2399cdb4bbc7d43f24625427bf7eb88534a922
```

`READY_FOR_REVIEW` does not authorize merge or LOCK.

Do not start FAZ 5.2.
Do not merge.
Do not self-LOCK.

STOP.
