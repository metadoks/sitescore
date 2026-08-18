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
REVIEWED_HEAD_SHA: 4f93275050c9d8ff392d53ac41acec0824ff4405
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
RPT55_H005_STATUS: OPEN
BLOCKERS: RPT55-H005
```

---

# 1. EXACT LIVE STATE REVIEWED

Reviewer independently re-read coordination state, PR #21, exact hardening delta, production source, adversarial tests and fresh CI evidence.

```text
main: 7d6ddbdb94567761733ff540239d959096d98f61
main vs expected base: IDENTICAL

PR: #21
state: OPEN
merged: FALSE
mergeable: TRUE
draft: FALSE
base SHA: 7d6ddbdb94567761733ff540239d959096d98f61
head SHA: 4f93275050c9d8ff392d53ac41acec0824ff4405
```

Locked base -> final candidate is 43 commits ahead / 0 behind. Final PR diff is 22 files and every changed file remains under `sitescore-api/**`. Locked `sitescore-report==0.3.0` and frozen analytical packages remain unchanged.

H003/H004 hardening delta from prior reviewed head:

```text
169c067a79b13edd64d866ad9fe15a697fe887b9
->
4f93275050c9d8ff392d53ac41acec0824ff4405
```

Product/test changes are confined to:

```text
sitescore-api/src/sitescore_api/worker.py
sitescore-api/src/sitescore_api/tasks.py
sitescore-api/src/sitescore_api/celery_app.py
sitescore-api/tests/test_report_crash_recovery.py
```

No 5-FINAL / FAZ 6 scope is present.

---

# 2. RPT55-H003 — RESOLVED

Reviewer accepts the new paired terminal durability design.

Production completed path is now:

```text
analysis durable state = running
-> canonical executor returns genuine CanonicalCompletedOutcome
-> exact live outcome generates/uploads terminal PreparedReportArtifact
-> analysis row re-lock
-> persist_completed(...)
-> persist report terminal metadata ready|failed
-> ONE PostgreSQL commit exposes both terminal resources
```

Therefore a normal durable `analysis=completed` can no longer be committed before the current report artifact resource exists.

The new process-loss seam proves a `BaseException` after report preparation but before pair commit leaves:

```text
analysis = running
result_body = NULL
report row = absent
```

A fresh worker redelivery reruns canonical execution through worker authority and reaches a terminal pair. The report API remains resolver-only and no stored JSON is promoted to report authority.

Unexpected generator exceptions now raise `RetryableReportFinalization` rather than returning successful `completed + missing report`. H002 `unknown` also becomes retryable rather than silently stranded.

Celery is explicitly configured with:

```text
task_acks_late = true
task_reject_on_worker_lost = true
```

and the bound execute-analysis task retries `RetryableReportFinalization`.

Therefore the original permanent `completed + missing report` blocker is resolved.

```text
RPT55-H003: RESOLVED
```

---

# 3. RPT55-H004 — RESOLVED

Reviewer accepts the different-report-id conflict fix.

Conflict fail-close now targets the actual durable unique resource by:

```text
analysis_id + report_artifact_version
```

instead of requiring candidate `report_id` equality.

`_transition_resource_to_failed(...)` locks the actual row, preserves its durable report_id, clears ready content bindings, writes sanitized failure state, confirms durable failed state, and only then allows candidate object compensation.

The real-PostgreSQL H004 regression pre-creates a ready row for the same analysis/version with a different report_id and proves:

```text
actual durable report_id preserved
actual row -> failed
storage_key/hash/length/MIME/filename cleared
sanitized failure fields present
analysis -> completed with exact canonical result
candidate deterministic object deleted only after DB row is failed
no false-ready metadata remains
```

Therefore:

```text
RPT55-H004: RESOLVED
```

---

# 4. FRESH H003/H004 VALIDATION — ACCEPTED BUT NOT SUFFICIENT FOR LOCK

Fresh exact-head validation succeeded at:

```text
validated SHA: dd608bf395e2a240c3512c67218f63cb5151b8b4
workflow: faz5-5-5-exact-head-validation
run: 32172352608
job: 95826241399
conclusion: SUCCESS
```

Reviewer independently verified:

```text
exact SHA checkout: PASS
PostgreSQL 0001 -> 0002 migration: PASS
private pinned MinIO PUT/HEAD/GET/DELETE: PASS
no public ACL: PASS
sitescore-report: 24 PASS
sitescore-api: 98 PASS
frozen baseline: 1375 PASS
API + frozen: 1473 PASS
combined: 1497 PASS
real Redis/Celery worker: PASS
task_reject_on_worker_lost=true: PASS
Celery result backend disabled://: PASS
```

Validated SHA -> final candidate is exactly:

```text
dd608bf395e2a240c3512c67218f63cb5151b8b4
->
4f93275050c9d8ff392d53ac41acec0824ff4405

ahead_by: 1
changed file: .github/workflows/faz5-5-5-validation.yml
status: REMOVED
```

No product/test/dependency/migration/docs semantics changed after validation.

However this suite does not exercise H005 below, so it cannot authorize LOCK.

---

# 5. RPT55-H005 — REPORT FINALIZATION WINDOW CAN CONVERT A GENUINE CANONICAL SUCCESS INTO `timed_out`

Status:

```text
RPT55-H005: OPEN / BLOCKING
```

## 5.1 Problem

H003 correctly keeps analysis durable state nonterminal until analysis completion + terminal report metadata can be committed as a pair.

But the implementation deliberately releases the analysis row transaction/lock before report generation:

```text
canonical executor returns completed outcome
-> row is still durable `running`
-> session.rollback() releases row lock
-> report_artifacts.generate(...) / render / storage
-> later re-lock analysis row
-> pair commit
```

During that report-generation/finalization window the authoritative 5.1 timeout machinery still sees an ordinary `running` analysis.

Both existing production paths can independently terminalize it:

```text
PostgresAnalysisLifecycleBackend.retrieve(...)
if nonterminal and now >= deadline_at:
    row.state = timed_out
```

and:

```text
AnalysisWorkerService.reconcile_expired(...)
WHERE state IN (queued, running) AND deadline_at <= now
-> state = timed_out
```

The timeout reconciler runs periodically through Celery beat.

Therefore this deterministic sequence is possible:

```text
1. canonical executor succeeds before deadline
2. exact CanonicalCompletedOutcome exists in worker
3. report rendering/upload is still running
4. deadline_at passes during report work
5. polling GET or reconcile_timeouts locks the durable `running` row
6. row becomes terminal `timed_out`
7. report generation finishes
8. worker re-locks row
9. persist_completed(...) sees TERMINAL_STATES and returns False
10. candidate report is compensated
11. worker returns `timed_out`
```

Final durable state:

```text
canonical analytical computation genuinely succeeded
BUT analysis.state = timed_out
report resource = absent
```

The only reason canonical success could not become `completed` is time spent in / interaction with the FAZ 5.5 report finalization layer.

This violates the already accepted H001 semantic boundary:

```text
report failure / report latency / report finalization uncertainty
must not convert genuine canonical analytical success into
analysis_execution_failed / not_score_ready / timed_out.
```

It also makes the new H003 paired-durability solution race with the locked 5.1 timeout semantics.

## 5.2 Retry window has the same problem

The issue is not limited to a long synchronous render.

`RetryableReportFinalization` intentionally leaves the analysis nonterminal and schedules a later Celery retry. Between attempts, existing lifecycle polling or `reconcile_expired()` can mark the row timed_out once `deadline_at` passes.

Thus H002 `unknown`, generator-boundary retry, or process-loss recovery can still end as analytical timeout solely because report finalization required retry.

`task_reject_on_worker_lost=True` does not prevent PostgreSQL timeout state from becoming terminal.

## 5.3 Required invariant

Preserve both H001 and H003 simultaneously:

```text
A. before canonical analytical success is reached:
   locked 5.1 deadline/timeout semantics remain authoritative.

B. once a genuine canonical completed outcome has been reached before the
   analytical deadline and the system enters report finalization/recovery:
   report work MUST NOT cause that analytical success to become timed_out.

C. externally durable analysis=completed still requires one durable terminal
   report resource ready|failed for the current artifact version.

D. no stored JSON becomes report authority.
```

The solution must coordinate the timeout machinery with the new pre-terminal report-finalization state without weakening analysis deadline protection before canonical success.

Do not simply disable timeouts globally or extend arbitrary caller-visible deadlines.

A valid implementation may use an internal server-owned durable marker/state/column proving that canonical execution crossed the success boundary before `deadline_at`, or another equivalent mechanism. Such a marker is coordination evidence only and MUST NOT become report/scoring authority; any worker recovery that needs the live canonical object may still rerun canonical execution through worker authority.

Equivalent solutions are acceptable if the invariants are proven.

## 5.4 Both timeout writers must be covered

Hardening must account for BOTH:

```text
PostgresAnalysisLifecycleBackend.retrieve(...)
```

and:

```text
AnalysisWorkerService.reconcile_expired(...)
```

plus the execute-analysis entry deadline check on redelivery/retry.

A fix that protects only one writer is insufficient.

---

# 6. REQUIRED H005 ADVERSARIAL TESTS

Keep H001/H002/H003/H004 tests.

Add real-PostgreSQL production-path tests proving at minimum:

## 6.1 Reconciler race after canonical success

Force canonical execution to succeed before `deadline_at`, enter report-generation/finalization, then advance time beyond the analysis deadline and invoke the real timeout reconciler while report finalization is still pending.

Prove final outcome cannot become `timed_out` due to report work and eventually reaches:

```text
analysis = completed
report = ready OR failed
analysis failure fields = NULL
```

## 6.2 Polling retrieval race after canonical success

Exercise the real lifecycle retrieval/poll path after deadline while report finalization/recovery is pending.

It must not convert an already-achieved canonical success boundary into timed_out.

Before canonical success, ordinary expired queued/running analyses must still time out exactly as locked 5.1 requires.

## 6.3 Retry across deadline

Force a H002-unknown or generator-finalization retry after genuine canonical success occurred before the original deadline. Let retry/redelivery happen after `deadline_at`.

Prove report recovery remains possible and analytical success is not rewritten to timed_out merely because report finalization crossed the deadline.

No report API rerun and no JSON authority rehydration.

## 6.4 Regression guard

Prove analyses that have NOT reached canonical success before deadline still become timed_out through:

```text
retrieve polling
reconcile_expired
execute_analysis entry check
```

so H005 does not silently disable the locked lifecycle deadline.

---

# 7. DOCUMENTATION COHERENCE

The checkpoint documentation must be updated to describe the final paired terminal durability + retry/timeout coordination semantics. Current 5.5 docs predate H003/H004 and do not fully describe the new paired commit/retry behavior.

This documentation update is part of H005 hardening/finalization, not a separate architecture change.

---

# 8. PRESERVE ALL ACCEPTED 5.5 BOUNDARIES

Do not weaken:

```text
RPT55-H001 analytical-success/report-failure separation
RPT55-H002 ambiguous-COMMIT reconciliation
RPT55-H003 paired completed + terminal report durability
RPT55-H004 actual-resource conflict fail-close
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
```

No payment, Stripe, n8n, email, frontend, callback/webhook, 5-FINAL or FAZ 6 scope.

---

# 9. REVALIDATION / FINALIZATION REQUIRED

The successful 1497-test validation predates H005 and becomes stale after required changes.

After hardening:

1. fresh exact-HEAD validation;
2. real PostgreSQL migration through `0002_faz5_5` (plus any additive 5.5 migration if H005 legitimately requires one);
3. private MinIO integration;
4. full sitescore-api suite including H001-H005 adversarial cases;
5. locked sitescore-report 24 tests;
6. frozen baseline 1375;
7. real Redis/Celery worker proof;
8. verify late-ack / reject-on-worker-lost / disabled result backend;
9. exact validated SHA/run/job/counts recorded;
10. remove only temporary validation workflow after success;
11. prove validated SHA -> final candidate delta is exactly workflow removal;
12. update `implementer.md`;
13. STOP for Reviewer.

Any product/test/doc/dependency/migration change after validation requires another exact-head validation.

---

# 10. REVIEW DECISION

```text
REVIEW_DECISION: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
REVIEWED_HEAD_SHA: 4f93275050c9d8ff392d53ac41acec0824ff4405
PR: #21

RPT55-H001: RESOLVED
RPT55-H002: RESOLVED
RPT55-H003: RESOLVED
RPT55-H004: RESOLVED
RPT55-H005: OPEN / BLOCKING

BLOCKERS: RPT55-H005
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
USER_LOCK_AUTHORIZED: NO
MERGE: NO
START_5_FINAL: NO
```

Reviewer does not merge and does not self-lock.

Implementer must harden only Checkpoint 5.5 on the same branch/PR, revalidate exact head, finalize handoff, and STOP.

> Mathematically validated scoring engine; empirical validation pending.
