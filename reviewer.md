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
REVIEWED_HEAD_SHA: d744150f618c84f652da0ae419facea1c59e5f87
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
RPT55_H002_STATUS: OPEN
BLOCKERS: RPT55-H002
```

---

# 1. EXACT LIVE STATE REVIEWED

Reviewer independently re-read coordination state and live GitHub state after the first 5.5 hardening cycle.

```text
main: 7d6ddbdb94567761733ff540239d959096d98f61
main vs expected base: IDENTICAL

PR: #21
state: OPEN
merged: FALSE
mergeable: TRUE
draft: FALSE
base branch: main
base SHA: 7d6ddbdb94567761733ff540239d959096d98f61
head branch: faz5/5-5-delivery-ready-report-artifact
head SHA: d744150f618c84f652da0ae419facea1c59e5f87
```

The final candidate is 33 commits ahead / 0 behind the exact locked base. The final PR diff contains 18 files and every changed file is under:

```text
sitescore-api/**
```

The temporary validation workflow is absent from the final candidate.

Locked `sitescore-report==0.3.0` and all frozen analytical packages remain unchanged.

---

# 2. PRIOR BLOCKER RPT55-H001 — RESOLVED

Reviewer independently inspected the hardening delta from prior reviewed head:

```text
81da6f4e12850a33d84e0cca258647b8ac4c7442
->
d744150f618c84f652da0ae419facea1c59e5f87
```

Product/test hardening is confined to:

```text
sitescore-api/src/sitescore_api/worker.py
sitescore-api/tests/test_report_live_authority.py
```

plus removal of the temporary validation workflow after successful validation.

The new worker semantics now commit canonical analytical truth before entering report finalization:

```text
exact CanonicalCompletedOutcome
-> persist_completed(...)
-> COMMIT analysis.state=completed + exact canonical result_body
-> generate report from the SAME live completed outcome object
-> separate report persistence/finalization domain
```

This closes the original H001 problem where a report metadata failure could roll back canonical completion and cause `analysis_execution_failed`.

Reviewer verified the new report-specific path:

```text
persist_report_artifact(...)
-> explicit session.flush()
-> session.commit()
```

is guarded separately, and ordinary pre-commit report metadata failure triggers rollback + best-effort object compensation + sanitized failed-report persistence without regressing the already committed analysis state.

The new real-PostgreSQL adversarial test injects failure after successful PDF upload but before report-ready metadata persistence. It proves:

```text
executor call count = 1
same live CanonicalCompletedOutcome identity reaches report generation
analysis remains completed
canonical result_body remains exact
analysis failure fields remain absent
uploaded object compensation occurs
failed report row is persisted
ready content bindings are absent
POST /v1/reports resolves existing failed resource only
no JSON authority rehydration
no analysis rerun
```

Therefore:

```text
RPT55-H001: RESOLVED
```

---

# 3. FRESH VALIDATION EVIDENCE — ACCEPTED BUT NOT SUFFICIENT FOR LOCK

Fresh exact-head hardening validation succeeded at:

```text
workflow: faz5-5-5-exact-head-validation
run: 32162211707
job: 95793488010
validated SHA: 9cc58d1765da6f52646116dbbf55e5a76ba0a03b
conclusion: SUCCESS
```

Reviewer independently verified the workflow run/job and logs.

Evidence includes:

```text
exact SHA checkout assertion: PASS
PostgreSQL 0001 -> 0002 migration: PASS
private MinIO S3-compatible PUT/HEAD/GET/DELETE: PASS
no public object ACL grant: PASS
locked sitescore-report: 24 PASS
sitescore-api: 95 PASS
frozen baseline: 1375 PASS
API + frozen: 1470 PASS
combined total: 1494 PASS
real Redis/Celery worker: PASS
Celery result backend: disabled://
```

Validated SHA -> final candidate is exactly:

```text
9cc58d1765da6f52646116dbbf55e5a76ba0a03b
->
d744150f618c84f652da0ae419facea1c59e5f87

ahead_by: 1
behind_by: 0
changed files: 1
```

Sole delta:

```text
.github/workflows/faz5-5-5-validation.yml -> REMOVED
```

No product/test/dependency/migration/docs semantics changed after the successful run.

However the successful suite does not exercise the new blocker below, so the validation cannot authorize LOCK.

---

# 4. RPT55-H002 — AMBIGUOUS DB COMMIT CAN CREATE FALSE `ready` REPORT

Status:

```text
RPT55-H002: OPEN / BLOCKING
```

## 4.1 Problem

The current `_persist_report_after_completed(...)` treats **every** exception from:

```text
session.commit()
```

as though PostgreSQL definitely did not commit the ready report row.

Its failure path is semantically:

```text
persist ready ReportModel
-> flush
-> session.commit() raises
-> rollback
-> compensate uploaded PDF object (DELETE)
-> derive failed artifact
-> persist failed artifact
```

That is correct only when the report-ready DB transaction is definitely uncommitted.

But a database commit has an unavoidable client-observation ambiguity window:

```text
client sends COMMIT
PostgreSQL commits transaction durably
connection/acknowledgement fails before client receives success
session.commit() raises to application
```

In that case the database may already contain the exact `ready` row even though Python observed an exception.

The current code then immediately compensates/deletes the exact PDF object.

After that it attempts to persist a sanitized failed artifact using the same `report_id`. `persist_report_artifact(...)` currently behaves as:

```text
existing row for (analysis_id, artifact_version) found
AND existing.report_id == artifact.report_id
-> return existing row unchanged
```

It does not require the existing row's state/content/provenance semantics to equal the requested failed artifact.

Therefore the ambiguous-commit sequence can become:

```text
1. PDF upload succeeds
2. ready report row actually commits
3. commit acknowledgement is lost -> application sees exception
4. application deletes PDF object
5. application builds failed artifact
6. DB lookup finds same report_id already `ready`
7. persist helper silently returns existing ready row
8. final DB state remains `ready`
9. object is now missing because compensation deleted it
```

Externally this produces:

```text
GET /v1/reports/{report_id}
-> state = ready

GET /v1/reports/{report_id}/content
-> artifact integrity failure / missing object
```

The content endpoint correctly refuses to stream missing/corrupt bytes, but that does **not** make the durable resource contract valid. A caller-visible `ready` resource whose exact server-owned object was deleted is a false-ready state.

This violates the 5.5 transaction/storage invariant:

```text
DB ready metadata must not knowingly point to a missing object.
```

It also violates the intended rule that a storage orphan with no DB resource is safer than a DB `ready` resource with a missing/wrong object.

## 4.2 Why current H001 test does not catch H002

The H001 adversarial test injects failure **before** the ready metadata is committed by making the first `persist_report_artifact(...)` call raise.

That proves the definite-precommit failure path.

It does not simulate:

```text
DB commit actually succeeds
BUT session.commit() raises to the caller afterward
```

Therefore all 95 API tests can pass while the false-ready window remains open.

---

# 5. REQUIRED H002 HARDENING — SAME BRANCH / SAME PR

Do not create a new PR. Do not start `5-FINAL`.

Continue only on:

```text
branch: faz5/5-5-delivery-ready-report-artifact
PR: #21
```

## 5.1 Treat commit exception as UNKNOWN until independently reconciled

A report-ready commit exception MUST NOT immediately authorize object deletion.

After a ready metadata commit exception, resolve the durable outcome using a **fresh independent PostgreSQL session/connection**, not merely the possibly failed transaction/session.

The reconciliation must query the authoritative report identity by server-owned keys, at minimum:

```text
analysis_id
report_artifact_version
report_id
```

and compare the persisted row against the exact prepared artifact.

## 5.2 Exact semantic match required

If a row already exists with the same `report_id`, equality of ID alone is insufficient.

For a committed ready artifact, verify all security/identity-relevant bindings that determine the exact resource, including at minimum:

```text
analysis_id
report_id
report_artifact_version
state
analysis_fingerprint
content_sha256
byte_length
mime_type
filename
storage_key
report/projection versions
narrative provenance/version fields
presentation/template/chart/renderer versions
```

Do not let an existing row with same report ID but different state/content semantics silently satisfy persistence.

`persist_report_artifact(...)` may remain an insert-oriented helper if reconciliation is handled elsewhere, but no production path may interpret a semantic mismatch as successful idempotent persistence.

## 5.3 Safe reconciliation outcomes

### Case A — fresh DB confirms exact committed ready row

If a fresh authoritative read proves the exact ready row was committed and the exact object still satisfies its expected storage binding:

```text
KEEP object
KEEP ready row
return success from report finalization
```

Do not compensate a proven committed ready artifact merely because the original client lost the commit acknowledgement.

### Case B — fresh DB proves ready row did NOT commit

If a fresh read proves no exact report row exists:

```text
best-effort compensate exact uploaded object
-> persist sanitized failed report in a fresh transaction when DB is usable
```

This is the existing H001-style failure outcome.

### Case C — fresh DB finds committed failed row

Compensate any unbound ready object and keep/validate the failed resource contract.

### Case D — fresh DB finds conflicting/mismatched row

Fail closed. Do not silently treat it as idempotent success. Do not expose a false ready artifact.

### Case E — commit outcome cannot be determined because DB remains unavailable

Do not make a destructive compensation decision that could turn a successfully committed ready row into `ready + missing object` merely from uncertainty.

A temporary orphan object with no durable report row is safer than deleting an object that may already be referenced by a committed ready row.

The implementation may use bounded reconciliation/retry or another equivalent deterministic mechanism, but the safety invariant above is mandatory.

## 5.4 Object verification after reconciled ready commit

When reconciliation concludes that ready metadata committed, verify the exact object binding before accepting the resource as ready. At minimum preserve existing checks around:

```text
server-owned storage key
object existence
byte length
MIME expectations
```

The existing content download path must continue to verify full SHA-256 + byte length + PDF signature before streaming.

If reconciliation proves a committed ready row but also proves the referenced object is missing/invalid, the system must not leave that row caller-visible as valid `ready`. Transition/fail closed in a way consistent with the closed `ready|failed` report contract.

---

# 6. REQUIRED ADVERSARIAL TESTS

Keep the existing H001 test.

Add a deterministic real-PostgreSQL test for **commit acknowledgement loss after actual commit**.

A valid test can, for example, instrument the report-ready commit so that it:

```text
1. invokes the real commit successfully;
2. then raises a synthetic client-side/connection acknowledgement error exactly once.
```

The test must target the **report-ready metadata transaction**, not the earlier canonical analysis completion commit.

Prove at minimum:

```text
canonical executor called exactly once
analysis remains completed
canonical result_body remains exact
analysis failure fields remain absent
exact live outcome remains the report authority
PDF upload succeeds
ready metadata is actually committed before the synthetic exception
application does NOT produce `ready + deleted/missing object`
```

Then prove one of the safe allowed final outcomes:

```text
A. exact ready row retained + exact object retained + content endpoint succeeds
```

or, if implementation intentionally converts the reconciled state to failed:

```text
B. failed row persisted + ready bindings cleared + object compensated + no caller-visible ready state
```

Also add/retain coverage showing an existing same `report_id` with state/content mismatch is not silently accepted as an equivalent artifact.

The test should exercise production worker/reconciliation behavior, not only a standalone helper.

---

# 7. PRESERVE ALL ACCEPTED 5.5 BOUNDARIES

H002 hardening must not weaken any already accepted checkpoint invariant:

```text
no JSON report-authority rehydration
no analysis rerun
exact live CanonicalCompletedOutcome authority
analysis completion isolated from report failure
one artifact/version per analysis
owner isolation through analysis consumer
private S3-compatible storage
server-owned object key
no public/raw storage URL
SHA-256 / size / PDF-signature integrity verification
report:write / report:read scopes
resolver-only POST /v1/reports
locked sitescore-report==0.3.0
frozen FAZ 3/4 and locked 5.0-5.4
```

Do not add payment, Stripe, n8n, email, frontend or FAZ 6 orchestration.

---

# 8. REVALIDATION / FINALIZATION REQUIRED

The current successful validation predates H002 and becomes stale after the required fix.

After hardening:

1. run a fresh exact-HEAD full validation;
2. prove real PostgreSQL migration through `0002_faz5_5`;
3. prove private MinIO S3-compatible integration;
4. run all sitescore-api tests including H001 + H002 adversarial cases;
5. run locked sitescore-report 24 tests;
6. run frozen baseline 1375;
7. re-prove real Redis/Celery worker with disabled result backend;
8. record exact validated SHA/run/job/counts;
9. remove only the temporary validation workflow after success;
10. prove validated SHA -> final candidate delta is exactly that workflow removal;
11. update `implementer.md` to the new exact final candidate;
12. STOP for Reviewer.

Any product/test/doc/dependency change after the fresh successful validation requires another exact-head validation.

---

# 9. REVIEW DECISION

```text
REVIEW_DECISION: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
REVIEWED_HEAD_SHA: d744150f618c84f652da0ae419facea1c59e5f87
PR: #21

RPT55-H001: RESOLVED
RPT55-H002: OPEN / BLOCKING

BLOCKERS: RPT55-H002
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
USER_LOCK_AUTHORIZED: NO
MERGE: NO
START_5_FINAL: NO
```

Reviewer does not merge and does not self-lock.

Implementer must harden only the current checkpoint on the same branch/PR, revalidate the exact head, finalize handoff, and STOP.

> Mathematically validated scoring engine; empirical validation pending.
