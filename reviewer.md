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
REVIEWED_HEAD_SHA: 169c067a79b13edd64d866ad9fe15a697fe887b9
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
RPT55_H003_STATUS: OPEN
RPT55_H004_STATUS: OPEN
BLOCKERS: RPT55-H003, RPT55-H004
```

---

# 1. EXACT LIVE STATE REVIEWED

Reviewer independently re-read coordination state and live GitHub after the H002 hardening cycle.

```text
main: 7d6ddbdb94567761733ff540239d959096d98f61
main vs expected base: IDENTICAL

PR: #21
state: OPEN
merged: FALSE
mergeable: TRUE
draft: FALSE
base SHA: 7d6ddbdb94567761733ff540239d959096d98f61
head SHA: 169c067a79b13edd64d866ad9fe15a697fe887b9
```

Locked base -> final candidate is 37 commits ahead / 0 behind. Final PR diff is 19 files, all under `sitescore-api/**`. Locked `sitescore-report==0.3.0` and frozen analytical packages remain unchanged.

---

# 2. RPT55-H002 — RESOLVED

Reviewer independently inspected the H002 delta:

```text
d744150f618c84f652da0ae419facea1c59e5f87
->
169c067a79b13edd64d866ad9fe15a697fe887b9
```

Product/test change is confined to:

```text
sitescore-api/src/sitescore_api/worker.py
sitescore-api/tests/test_report_commit_reconciliation.py
```

The implementation now treats report metadata COMMIT exception as UNKNOWN until a fresh `Database.session()` reconciles durable state. Exact equivalence is bound across report/analysis/artifact identity, state, fingerprint, report/projection provenance, narrative provenance, presentation/template/stylesheet/chart/renderer versions, generated time, hash/MIME/filename/size/storage key, and failure fields.

The real-PostgreSQL adversarial test genuinely performs:

```text
real report-ready PostgreSQL COMMIT
-> COMMIT succeeds
-> synthetic acknowledgement-loss exception
```

and proves exact committed ready metadata + exact object remain intact and downloadable. Same-`report_id` content-semantic corruption is no longer accepted as idempotent success and transitions to sanitized failed before object compensation.

Therefore:

```text
RPT55-H002: RESOLVED
```

Fresh exact-head H002 validation is also accepted as genuine evidence:

```text
validated SHA: 3952df60bddf86e7ba36b06283d3468daad6edbd
workflow: faz5-5-5-exact-head-validation
run: 32166096019
job: 95805923610
conclusion: SUCCESS

sitescore-report: 24 PASS
sitescore-api: 96 PASS
frozen baseline: 1375 PASS
API + frozen: 1471 PASS
combined: 1495 PASS
PostgreSQL migration through 0002: PASS
private MinIO S3 integration: PASS
Redis/Celery worker: PASS
result backend: disabled://
```

Validated -> final candidate is exactly one commit removing only `.github/workflows/faz5-5-5-validation.yml`.

This validation does not exercise H003/H004 below, so it cannot authorize LOCK.

---

# 3. RPT55-H003 — TERMINAL ANALYSIS CAN BECOME PERMANENTLY `completed + no report resource`

Status:

```text
RPT55-H003: OPEN / BLOCKING
```

## 3.1 Current ordering creates a crash/restart durability gap

Current completed path is semantically:

```text
canonical executor succeeds
-> persist_completed(...)
-> COMMIT analysis.state=completed + result_body
-> generate PDF/report artifact from live outcome
-> persist/finalize report metadata
```

But `execute_analysis()` treats every `TERMINAL_STATES` analysis as an immediate return before any report generation/reconciliation logic.

Therefore, after the analysis completion COMMIT and before a terminal report row becomes durable, any process death / worker loss / hard time limit / host failure can produce:

```text
analysis.state = completed
report row = absent
```

A subsequent Celery redelivery/retry does not repair it because it sees terminal `completed` and returns without re-entering the report path.

The current task topology has only:

```text
execute_analysis
drain_outbox
reconcile_timeouts
```

There is no report outbox, report-finalization task, or report reconciler that can close this gap after restart.

## 3.2 Resolver-only API makes the gap permanent

The locked 5.5 authority rule correctly forbids:

```text
AnalysisModel.result_body JSON -> report authority
POST /v1/reports -> analysis rerun
```

The current report resolver explicitly treats:

```text
completed analysis + missing report row
```

as `report_invariant_violation` / HTTP 500.

Therefore a worker crash after analysis completion but before report finalization is not merely a transient delay: after live `ApplicationAnalysisResult` authority disappears with the worker process, no accepted V1 path can reconstruct the report.

## 3.3 A normal Exception path can create the same invalid state

The current worker also contains:

```text
try:
    prepared_report = report_artifacts.generate(...)
except Exception:
    return completed_state
```

An unexpected generator-level exception therefore returns successful `completed` while persisting no failed report resource. This produces the same durable invariant violation without requiring process death.

`ReportArtifactGenerator` catches many expected render/storage failures internally, but an outer unexpected failure must still not make `completed + missing report row` a legitimate terminal state.

## 3.4 H002 `unknown` can also strand an absent row permanently

H002 correctly avoids destructive object deletion when commit outcome cannot be reconciled because PostgreSQL is unavailable.

However current `reconciliation == "unknown"` simply returns. If the original report-ready COMMIT actually did **not** commit and PostgreSQL later recovers, final durable state can be:

```text
analysis = completed
report row = absent
object = orphaned or indeterminate
```

There is no scheduled/follow-up report reconciliation, and terminal analysis retry skips report processing. Thus the deliberately safe temporary uncertainty can become permanent resource loss.

## 3.5 Required invariant

Before 5.5 LOCK, production semantics must ensure:

```text
if analysis is durably/external-state `completed`,
then the current report_artifact_version has exactly one durable terminal report resource:
    ready
    OR failed
```

A normal worker return/acknowledgement must never leave `completed + missing report row`.

A catastrophic interruption before this paired durable invariant is reached must leave enough durable state for deterministic retry/reconciliation without using stored JSON as report authority and without POST-triggered analysis rerun.

H001 remains semantic, not ordering-specific:

```text
report failure must not turn genuine analytical success into durable analysis_execution_failed / not_score_ready / timed_out.
```

Implementer may restructure transaction ordering inside 5.5 if needed. H001 does **not** require preserving the current commit-analysis-first ordering if that ordering makes crash-safe delivery impossible.

A valid approach may, for example, build the terminal `PreparedReportArtifact` while the live canonical outcome exists and while analysis is still nonterminal, then make canonical completion + terminal report metadata a paired durable PostgreSQL decision, with H002-style reconciliation around ambiguous commit and safe object compensation on definite non-commit. Equivalent designs are acceptable if they prove the invariant.

Do not introduce serialized JSON rehydration as authority merely to solve restart recovery.

---

# 4. RPT55-H004 — DIFFERENT-`report_id` CONFLICT BRANCH DOES NOT ACTUALLY FAIL CLOSED

Status:

```text
RPT55-H004: OPEN / BLOCKING
```

Current `_reconcile_report_commit(artifact)` queries the unique report resource by:

```text
analysis_id + report_artifact_version
```

and correctly returns `conflict` if the durable row's `report_id != artifact.report_id`.

But the subsequent conflict handler calls:

```text
_transition_same_identity_to_failed(artifact)
```

and that method queries using:

```text
analysis_id
report_artifact_version
artifact.report_id
```

If the conflict is specifically a different durable `report_id`, that query returns no row and the transition returns `False`. The `conflict` branch then returns without changing the actual conflicting row and without proving a safe object state.

This contradicts the claimed H002 state-machine contract that a durable conflicting/mismatched identity fails closed.

The risk is amplified by the server-owned object key being deterministic by:

```text
consumer_id + analysis_id + report_artifact_version
```

and **not** by `report_id`. A candidate generation can therefore write the same deterministic key while a contradictory ready row for the same analysis/version already exists. If conflict handling no-ops, caller-visible metadata can remain `ready` while its stored hash/content binding no longer matches the object.

The existing H002 test covers same-`report_id` semantic mismatch but not different-`report_id` conflict.

Required outcome:

- a row found by the unique `(analysis_id, report_artifact_version)` resource identity must never be ignored merely because its `report_id` differs from the candidate;
- conflict resolution must operate on the actual durable conflicting row/resource identity;
- no path may finish with caller-visible `ready` metadata whose exact object binding is known/likely to have been overwritten, deleted, or contradicted;
- destructive compensation must still obey H002's commit-ambiguity safety rules.

---

# 5. REQUIRED ADVERSARIAL TESTS — SAME PR

Keep all existing H001 and H002 regressions.

Add deterministic production-path tests for H003/H004.

## 5.1 Crash/restart between analysis success and report durable terminal state

Inject a process-loss-equivalent seam after canonical success but before the paired durable report invariant. Use a `BaseException`/explicit crash seam or equivalent that is not converted into an ordinary successful worker return.

Then instantiate a fresh worker and simulate redelivery/retry.

Prove:

```text
no externally durable completed + missing report terminal resource remains
retry/reconciliation can finish deterministically
no POST JSON rehydration
no POST-triggered analysis rerun
final analysis = completed
final report = ready OR failed
analysis failure fields absent
```

If the chosen design intentionally reruns canonical execution after a pre-terminal crash, prove it is a worker retry consequence, not report API authority, and preserve all existing analytical authority gates.

## 5.2 Unexpected generator exception

Force the report generator boundary itself to raise unexpectedly.

Prove a normal worker return cannot leave:

```text
analysis=completed
report row absent
```

Either persist `completed + failed report` safely or leave a clearly retryable nonterminal state until a terminal paired result can be made durable.

## 5.3 H002 unknown -> later DB recovery

Simulate a report commit failure where reconciliation is temporarily unavailable and the ready row was not actually committed. After DB access is restored, prove the system has a deterministic recovery path and does not strand `completed + no report row` forever.

## 5.4 Different-report-id conflict

Pre-create a durable row for the same:

```text
analysis_id + report_artifact_version
```

with a different `report_id`, exercise the production finalization/reconciliation path, and prove:

```text
conflict is not accepted as idempotent success
actual conflicting row is handled fail-closed
no false-ready metadata survives
candidate object is not destructively handled until DB state is safely resolved
```

---

# 6. PRESERVE ACCEPTED BOUNDARIES

Do not weaken:

```text
exact live CanonicalCompletedOutcome / ApplicationAnalysisResult authority
no AnalysisModel.result_body report-authority rehydration
no POST /v1/reports analysis rerun
H001 analytical-success/report-failure separation
H002 ambiguous-COMMIT reconciliation
owner isolation through analysis consumer
one artifact version per analysis
private S3-compatible storage
server-owned object key
SHA-256 / byte-length / MIME / PDF integrity checks
report:write / report:read
resolver-only report API
locked sitescore-report==0.3.0
frozen FAZ 3/4 and locked 5.0-5.4
```

No payment, Stripe, n8n, email, frontend, callback/webhook, or FAZ 6 / 5-FINAL scope.

---

# 7. REVALIDATION / FINALIZATION

The current successful validation predates H003/H004 and becomes stale after required changes.

After hardening:

1. fresh exact-HEAD validation;
2. real PostgreSQL migration through `0002_faz5_5`;
3. private MinIO S3 integration;
4. full sitescore-api suite including H001/H002/H003/H004 adversarial tests;
5. locked sitescore-report 24 tests;
6. frozen baseline 1375;
7. real Redis/Celery worker proof with disabled result backend;
8. exact SHA/run/job/test counts recorded;
9. remove only temporary validation workflow after success;
10. prove validated SHA -> final candidate delta is exactly workflow removal;
11. update `implementer.md`;
12. STOP for Reviewer.

Any product/test/dependency/migration/docs change after validation requires another exact-head validation.

---

# 8. REVIEW DECISION

```text
REVIEW_DECISION: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
REVIEWED_HEAD_SHA: 169c067a79b13edd64d866ad9fe15a697fe887b9
PR: #21

RPT55-H001: RESOLVED
RPT55-H002: RESOLVED
RPT55-H003: OPEN / BLOCKING
RPT55-H004: OPEN / BLOCKING

BLOCKERS: RPT55-H003, RPT55-H004
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
