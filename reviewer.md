# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.5
CHECKPOINT_TITLE: Delivery-Ready Report Artifact Contract

REVIEWER_STATE: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 7d6ddbdb94567761733ff540239d959096d98f61
CODE_BRANCH: faz5/5-5-delivery-ready-report-artifact
REVIEWED_HEAD_SHA: ca96ee6e3fefde47e834f420afdaf05a4e141004
PR: #21

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED
FAZ_5_1_STATUS: LOCKED
FAZ_5_2_STATUS: LOCKED
FAZ_5_3_STATUS: LOCKED
FAZ_5_4_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

RPT55_H001_STATUS: RESOLVED
RPT55_H002_STATUS: RESOLVED
RPT55_H003_STATUS: RESOLVED
RPT55_H004_STATUS: RESOLVED
RPT55_H005_STATUS: RESOLVED
RPT55_H006_STATUS: OPEN
BLOCKERS: RPT55-H006
```

---

# 1. EXACT LIVE STATE REVIEWED

Reviewer independently re-read current handoff state, PR #21, live `main`, exact H005 delta, production lifecycle/worker code, migration, adversarial tests, frozen 5.1 lifecycle documentation, and fresh CI evidence.

```text
main: 7d6ddbdb94567761733ff540239d959096d98f61
main vs expected base: IDENTICAL

PR: #21
state: OPEN
merged: FALSE
mergeable: TRUE
draft: FALSE
base SHA: 7d6ddbdb94567761733ff540239d959096d98f61
head SHA: ca96ee6e3fefde47e834f420afdaf05a4e141004
```

Prior reviewed head -> current H005 candidate:

```text
4f93275050c9d8ff392d53ac41acec0824ff4405
->
ca96ee6e3fefde47e834f420afdaf05a4e141004
```

H005 product/test delta is confined to:

```text
sitescore-api/alembic/versions/0003_faz5_5_canonical_success_boundary.py
sitescore-api/docs/CHECKPOINT_5_5_DELIVERY_READY_REPORT_ARTIFACT.md
sitescore-api/src/sitescore_api/db_models.py
sitescore-api/src/sitescore_api/lifecycle.py
sitescore-api/src/sitescore_api/worker.py
sitescore-api/tests/test_migrations.py
sitescore-api/tests/test_report_timeout_coordination.py
```

No locked `sitescore-report==0.3.0` source or frozen analytical package changed. No 5-FINAL / FAZ 6 scope is present.

---

# 2. RPT55-H005 — RESOLVED

Reviewer accepts the core H005 timeout/report-finalization coordination fix.

The implementation adds nullable, server-owned:

```text
analyses.canonical_success_at
```

through additive migration `0003_faz5_5`.

Database constraints require:

```text
canonical_success_at IS NULL OR canonical_success_at < deadline_at
canonical_success_at IS NULL OR state IN ('running','completed')
```

The marker is written only after the worker has obtained a genuine `CanonicalCompletedOutcome`, and only for a success timestamp strictly before the durable analysis deadline. It is coordination evidence only: it is not exposed as caller authority, cannot reconstruct `ApplicationAnalysisResult`, and does not authorize report generation from stored JSON.

Once the marker is durable:

- owner-scoped lifecycle polling no longer rewrites the protected `running` row to `timed_out`;
- periodic `reconcile_expired()` excludes the protected row;
- worker redelivery may cross the original analytical deadline to rerun canonical execution and recover a live factory-owned canonical object;
- post-success report/finalization failures remain retryable instead of becoming analytical failure/timeout;
- `POST /v1/reports` remains resolver-only.

Before the marker exists, the original 5.1 timeout semantics remain present for ordinary expired analyses.

The real-PostgreSQL H005 regression exercises:

1. pre-deadline canonical success + blocked report generation + real timeout reconciler after deadline;
2. pre-deadline canonical success + blocked report generation + real lifecycle retrieval after deadline;
3. H002 `unknown` + retry/redelivery after original deadline;
4. no-marker regression for retrieve/reconciler/worker-entry timeout paths.

Therefore the original H005 blocker — report latency/retry converting an already-durably-marked canonical success into `timed_out` — is resolved.

```text
RPT55-H005: RESOLVED
```

---

# 3. FRESH H005 VALIDATION — GENUINE, BUT NOT SUFFICIENT FOR LOCK

Reviewer independently verified the new authoritative validation:

```text
validated SHA: 9818fc76a26a623ed9e53681617aee4956d863b0
workflow: faz5-5-5-exact-head-validation
run: 32180822082
job: 95853159137
conclusion: SUCCESS
```

Evidence includes:

```text
exact SHA checkout: PASS
PostgreSQL 16.15 migration 0001 -> 0002 -> 0003: PASS
private pinned MinIO PUT/HEAD/GET/DELETE: PASS
no public ACL: PASS
sitescore-report: 24 PASS
sitescore-api: 99 PASS
frozen baseline: 1375 PASS
API + frozen: 1474 PASS
combined: 1498 PASS
real Redis/Celery 5.6.3 worker: PASS
task_acks_late=true: PASS
task_reject_on_worker_lost=true: PASS
Celery result backend disabled://: PASS
```

Validated SHA -> final candidate is exactly:

```text
9818fc76a26a623ed9e53681617aee4956d863b0
->
ca96ee6e3fefde47e834f420afdaf05a4e141004

ahead_by: 1
changed file: .github/workflows/faz5-5-5-validation.yml
status: REMOVED
```

No product/test/dependency/migration/docs change exists after the validated SHA.

However the H005 implementation introduces the new H006 lifecycle regression below, which the 99-test API suite does not exercise.

---

# 4. RPT55-H006 — LOCK-RACE REPAIR CAN RESURRECT PUBLIC TERMINAL `timed_out`

Status:

```text
RPT55-H006: OPEN / BLOCKING
```

## 4.1 Frozen 5.1 contract is explicit

The locked FAZ 5.1 lifecycle document states:

```text
Terminal states are immutable.
```

and describes GET polling semantics as:

```text
timed_out: stable deadline terminal metadata
```

This is an externally meaningful V1 contract. n8n V1 is polling-only and may legitimately stop polling after receiving a terminal state.

## 4.2 Current H005 repair violates that contract

`AnalysisWorkerService._record_canonical_success_boundary(...)` contains a narrow-race repair branch for an already-durable row:

```text
if row.state == "timed_out":
    if failure_code == "analysis_deadline_exceeded"
       and result_body is NULL
       and readiness_body is NULL:
        row.state = "running"
        row.finished_at = NULL
        row.failure_code = NULL
        row.failure_message = NULL
        ...
        row.canonical_success_at = pre_deadline_success_at
        COMMIT
```

The intention is understandable: canonical execution may have actually completed before deadline while a timeout writer wins the row lock before the success marker can commit.

But the timeout writer can commit and expose that terminal state to an authenticated caller before the worker performs the repair.

Concrete race:

```text
T0  canonical executor returns genuine completed outcome before deadline
T1  worker records in-memory outcome_at < deadline, but has not committed marker yet
T2  deadline passes
T3  GET /v1/analyses/{id} OR reconcile_expired() wins row lock
T4  PostgreSQL COMMIT: state = timed_out
T5  GET may return timed_out to the consumer
T6  worker later locks the row
T7  H005 repair changes timed_out -> running and commits canonical_success_at
T8  report finalization succeeds
T9  state becomes completed
```

Externally visible sequence can therefore be:

```text
running
-> timed_out   (terminal; consumer may stop polling)
-> running     (resurrection)
-> completed
```

This is forbidden by the locked 5.1 terminal-state contract even if the final analytical truth would otherwise be more accurate.

The new database constraints do not prevent this because each intermediate row is individually constraint-valid: the marker is NULL while `timed_out`, then state and marker are changed together when resurrected.

## 4.3 Why this is blocking

This is not cosmetic state churn.

A polling consumer/n8n workflow is allowed to treat `timed_out` as final and stop. It may never observe the later `completed` report. Any downstream workflow that records terminal timeout is also left inconsistent with PostgreSQL's later state.

A durable public terminal result must never be retroactively revoked.

Therefore H005 cannot be accepted for LOCK while its narrow race is solved by terminal-state resurrection.

---

# 5. REQUIRED H006 RESOLUTION

Preserve all of H001-H005, but enforce the frozen 5.1 rule:

```text
Once any public TERMINAL_STATES value is durably committed,
it MUST remain immutable.

In particular:
timed_out -> running/completed is forbidden.
```

The fix must prevent the **false timeout from becoming durable/public in the first place** when a worker has already achieved genuine canonical success before deadline but has not yet committed the marker.

Do not solve H006 by changing the 5.1 contract, redefining `timed_out` as provisional, or teaching n8n to resume after terminal timeout.

A valid design may coordinate timeout writers with the already-held server-owned analysis advisory lock, a server-owned execution lease/coordination primitive, or another equivalent race-safe mechanism. Reviewer is not prescribing a specific implementation.

Required semantics:

### A. Pre-success deadline behavior remains locked

If canonical success has NOT been achieved before deadline, the system must still eventually produce stable `timed_out` through the existing timeout authorities.

### B. Pre-deadline success in flight must not expose false terminal timeout

If a worker already obtained a genuine canonical completed outcome before deadline but marker persistence is still in flight, polling/reconciliation must not durably publish `timed_out` and then rely on resurrection.

### C. Durable terminal state is final

If `timed_out`, `failed`, `not_score_ready`, or `completed` is already durably committed, worker code must not move it back to `queued`/`running` or replace it with another terminal outcome.

### D. H005 marker remains coordination-only

No stored JSON/fingerprint/marker may become scoring/report authority. Worker recovery needing report authority must still use a genuine live canonical execution path.

---

# 6. REQUIRED H006 ADVERSARIAL TESTS

Keep H001-H005 regressions.

Add deterministic real-PostgreSQL tests for the actual race, not only the post-marker state.

## 6.1 Pre-marker timeout race with owner polling

Create a controlled seam after canonical executor returns a genuine completed outcome with `success_at < deadline_at`, but before `canonical_success_at` becomes durable.

Cross the deadline and concurrently exercise the real `PostgresAnalysisLifecycleBackend.retrieve()` path.

Prove:

```text
caller never receives a durable terminal timed_out that is later revoked
no timed_out -> running/completed transition occurs
worker can finish completed + terminal report
```

## 6.2 Pre-marker timeout race with periodic reconciler

Exercise the same pre-marker interval with real `AnalysisWorkerService.reconcile_expired()`.

Prove no false timeout is durably committed and later resurrected.

## 6.3 Terminal immutability regression

Seed/produce genuine stable terminal rows and prove worker retry cannot resurrect them:

```text
timed_out remains timed_out
failed remains failed
not_score_ready remains not_score_ready
completed remains completed
```

At minimum `timed_out` must be tested through the production worker entry/coordination path implicated by H006.

## 6.4 No-success control

Prove that if a worker has NOT achieved a genuine pre-deadline canonical success, any temporary race avoidance/lock coordination does not suppress timeout forever. Once the active execution claim is released/lost without a success marker, normal retrieve/reconciler/worker-entry semantics must converge to stable `timed_out`.

---

# 7. PRESERVE ACCEPTED 5.5 BOUNDARIES

Do not weaken:

```text
RPT55-H001 analytical-success/report-failure separation
RPT55-H002 ambiguous-COMMIT reconciliation
RPT55-H003 paired completed + terminal report durability
RPT55-H004 actual-resource conflict fail-close
RPT55-H005 pre-deadline canonical-success timeout protection
exact live CanonicalCompletedOutcome / ApplicationAnalysisResult authority
no AnalysisModel.result_body report-authority rehydration
no POST /v1/reports analysis rerun
one report artifact version per analysis
consumer ownership isolation
private S3-compatible storage
server-owned object key
SHA-256 / length / MIME / PDF integrity checks
report:write / report:read scopes
resolver-only report API
locked sitescore-report==0.3.0
frozen FAZ 3/4 and locked 5.0-5.4
locked 5.1 terminal-state immutability
```

No payment, Stripe, n8n implementation, email, frontend, callback/webhook, 5-FINAL or FAZ 6 scope.

---

# 8. REVALIDATION / FINALIZATION REQUIRED

Current 1498-test validation becomes stale after H006 product/test changes.

After hardening:

1. fresh exact-HEAD validation;
2. PostgreSQL migration chain 0001 -> 0002 -> 0003 (plus only a legitimate additive 5.5 migration if strictly necessary);
3. private MinIO integration;
4. full sitescore-api suite including H001-H006 adversarial tests;
5. locked sitescore-report 24 tests;
6. frozen baseline 1375;
7. real Redis/Celery worker proof;
8. verify late-ack / reject-on-worker-lost / disabled result backend;
9. exact SHA/run/job/test counts recorded;
10. remove only temporary validation workflow after success;
11. prove validated SHA -> final candidate delta exactly workflow removal;
12. update `implementer.md`;
13. STOP for Reviewer.

Any product/test/doc/dependency/migration change after validation requires another exact-head validation.

---

# 9. REVIEW DECISION

```text
REVIEW_DECISION: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
REVIEWED_HEAD_SHA: ca96ee6e3fefde47e834f420afdaf05a4e141004
PR: #21

RPT55-H001: RESOLVED
RPT55-H002: RESOLVED
RPT55-H003: RESOLVED
RPT55-H004: RESOLVED
RPT55-H005: RESOLVED
RPT55-H006: OPEN / BLOCKING

BLOCKERS: RPT55-H006
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
USER_LOCK_AUTHORIZED: NO
MERGE: NO
START_5_FINAL: NO
```

Reviewer does not merge and does not self-lock.

Implementer must harden only Checkpoint 5.5 on the same branch/PR, preserve the frozen terminal-state contract, revalidate exact head, finalize handoff, and STOP.

> Mathematically validated scoring engine; empirical validation pending.
