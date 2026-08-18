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

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 7d6ddbdb94567761733ff540239d959096d98f61
CODE_BRANCH: faz5/5-5-delivery-ready-report-artifact
REVIEWED_HEAD_SHA: 81da6f4e12850a33d84e0cca258647b8ac4c7442
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

BLOCKERS: RPT55-H001
```

---

# 1. EXACT LIVE STATE REVIEWED

Reviewer independently inspected live GitHub state.

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
reviewed head SHA: 81da6f4e12850a33d84e0cca258647b8ac4c7442
```

Base -> reviewed head:

```text
merge base: exact expected base
ahead_by: 29
behind_by: 0
changed files: 19
```

Product scope is `sitescore-api/**`; the only non-product file is the temporary exact-head validation workflow:

```text
.github/workflows/faz5-5-5-validation.yml
```

Locked `sitescore-report==0.3.0` and frozen analytical packages are unchanged.

`implementer.md` is currently stale and still describes FAZ 5.4 post-LOCK state. Live GitHub state therefore remains authoritative for this review.

---

# 2. ACCEPTED 5.5 AREAS AT REVIEWED HEAD

The following architecture is accepted at the reviewed SHA and is not the reason for hardening.

## 2.1 Live canonical report authority

Accepted:

```text
CanonicalCompletedOutcome
-> exact live factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
-> ValidatedReportNarrative
-> locked 5.4 PDF renderer
-> exact PDF bytes
```

The implementation requires `require_canonical_completed_outcome(...)` and consumes the exact live `application_analysis_result`.

`POST /v1/reports` is resolver-only.

No accepted path exists from:

```text
AnalysisModel.result_body JSON
-> reconstructed/forged report authority
```

and the completed analysis is not rerun merely to generate a report.

This preserves the locked 5.2/5.3/5.4 authority boundary.

## 2.2 Durable report model

Accepted:

```text
PostgreSQL = report resource / metadata truth
private S3-compatible storage = PDF bytes
Redis/Celery = execution transport only
```

The report table has:

- server UUID report_id;
- analysis FK;
- unique `(analysis_id, report_artifact_version)`;
- closed `ready|failed` states;
- artifact/report/narrative/presentation/renderer provenance;
- SHA-256, MIME, filename, byte length and private storage key for ready artifacts;
- sanitized failure state;
- DB state-coherence constraints.

Consumer ownership is derived through the analysis relationship rather than caller-supplied ownership metadata.

## 2.3 Object storage and integrity

Accepted:

- exact-pinned `boto3==1.43.55`;
- configurable S3-compatible bucket/region/endpoint;
- server-owned deterministic object key;
- no caller bucket/path/storage key/report ID;
- private object behavior;
- put/get/head/delete abstraction;
- SHA-256 over exact PDF bytes;
- byte-length bound;
- PDF signature validation;
- content retrieval verifies HEAD, byte length, SHA-256 and PDF signature before streaming;
- raw storage key/credentials are not exposed by report API.

## 2.4 Report API / isolation

Accepted endpoints:

```text
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

Accepted protections:

- strict POST body containing only `analysis_id`;
- `report:write` / `report:read` scopes;
- consumer-scoped analysis/report lookup;
- foreign-owner resource indistinguishable from missing resource;
- repeated resolver call returns same durable report resource;
- failed reports do not stream PDF;
- ready content uses direct authenticated API response;
- controlled attachment filename;
- no S3 redirect/public URL.

## 2.5 Migration / exact-head validation evidence

Current exact-head validation succeeded at:

```text
workflow: faz5-5-5-exact-head-validation
run ID: 32154643483
job ID: 95768784915
validated SHA: 81da6f4e12850a33d84e0cca258647b8ac4c7442
conclusion: SUCCESS
```

Evidence includes:

```text
PostgreSQL migration 0001 -> 0002: PASS
real private MinIO S3-compatible PUT/HEAD/GET/DELETE: PASS
locked sitescore-report: 24 PASS
sitescore-api: 94 PASS
frozen baseline: 1375 PASS
API + frozen: 1469 PASS
combined incl. report: 1493 PASS
real Redis/Celery transport: PASS
Celery result backend: disabled://
```

This successful run is useful evidence, but it does **not** cover the blocker below and therefore cannot authorize LOCK.

---

# 3. RPT55-H001 — REPORT FINALIZATION FAILURE CAN CORRUPT ANALYSIS SEMANTICS

Status:

```text
RPT55-H001: OPEN / BLOCKING
```

The reviewed worker currently performs the completed path semantically as:

```text
persist_completed(...)
-> ReportArtifactGenerator.generate(...)
   -> may successfully upload exact PDF object
-> persist_report_artifact(...)
-> try session.commit()
```

Compensation is currently only inside the `session.commit()` exception branch.

Therefore there is an uncovered failure window:

```text
canonical analysis succeeds
-> exact PDF renders
-> S3 object upload succeeds
-> prepared_report = ready
-> persist_report_artifact(...) raises BEFORE inner commit try
```

In that path:

1. control bypasses the existing report compensation branch;
2. the uploaded object can remain orphaned;
3. the transaction containing `persist_completed(...)` is rolled back;
4. the generic outer analysis exception path re-reads a nonterminal analysis and can mark it `failed` / `timed_out` with analysis-level failure semantics.

That violates the frozen 5.5 contract in two independent ways:

```text
A. successful canonical analytical truth must not become analysis failure merely because report finalization failed;
B. an uploaded ready object that cannot be durably bound due report-specific DB finalization failure must receive best-effort compensation.
```

The current passing tests prove storage-provider failure behavior, but do not inject a report-metadata persistence/finalization failure **after successful object upload**.

This is a transaction/failure-domain correctness blocker, not an upstream scoring/report-contract change.

Therefore:

```text
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
```

---

# 4. REQUIRED HARDENING — SAME BRANCH / SAME PR

Do not start 5-FINAL. Do not create a new checkpoint PR.

Use the existing:

```text
branch: faz5/5-5-delivery-ready-report-artifact
PR: #21
```

Required outcome:

## 4.1 Isolate report-specific failure from canonical analysis success

Once the exact canonical completed outcome exists, any **report-specific** generation/persistence/finalization failure that is recoverable while PostgreSQL remains usable must not flow into the generic analysis-execution failure classification.

Required durable semantic result:

```text
analysis.state = completed
analysis.result_body = exact canonical completed projection
analysis failure fields = absent

report.state = failed
report content fields/storage key = absent
report failure = sanitized
```

Do not reinterpret report failure as:

```text
analysis_execution_failed
not_score_ready
timed_out
```

solely because the report layer failed.

A true global PostgreSQL outage may of course prevent any durable transaction; the requirement concerns report-specific persistence/finalization errors while the database remains capable of preserving the canonical analysis outcome.

## 4.2 Expand compensation coverage

If a ready PDF object has been uploaded and any later report-specific metadata/finalization step fails before durable ready binding, perform best-effort compensation for the exact server-owned object key.

Compensation must cover at least:

```text
report metadata persistence failure before commit
report transaction/flush failure
final DB commit failure after upload
```

Do not claim `report.state = ready` unless the object remains durably bound to committed metadata.

## 4.3 Add adversarial real-PostgreSQL regression

Add a deterministic test that injects failure **after successful object upload but before durable report-ready metadata is committed**.

At minimum prove:

```text
canonical executor called exactly once
exact live canonical outcome remains the report input
analysis ends completed
canonical analysis result_body is preserved
analysis failure_code is not analysis_execution_failed
uploaded object compensation is attempted and object is absent afterward
no ready report is exposed
sanitized failed report row is persisted when DB remains usable
POST /v1/reports cannot regenerate from JSON or rerun analysis
```

Also preserve the existing successful-object/commit compensation coverage.

If the chosen implementation uses a savepoint/nested transaction or an equivalent isolation mechanism, tests must prove the semantics rather than merely assert code strings.

## 4.4 Preserve accepted boundaries

Hardening must not weaken:

```text
no JSON rehydration
no analysis rerun
exact live CanonicalCompletedOutcome authority
one report artifact/version per analysis
owner isolation
private S3-compatible storage
SHA-256 / size / PDF integrity verification
report:write / report:read scopes
locked sitescore-report==0.3.0
frozen FAZ 3/4 and locked 5.0-5.4 semantics
```

No payment, Stripe, n8n, email, frontend or FAZ 6 behavior.

---

# 5. REVALIDATION / FINALIZATION REQUIRED AFTER HARDENING

The current validation run predates the required product/test fix and will become stale.

After hardening:

1. run a new exact-HEAD full validation;
2. prove migration through 0002 on real PostgreSQL;
3. prove real private S3-compatible MinIO integration;
4. run full sitescore-api suite;
5. run locked sitescore-report 24 tests;
6. run frozen baseline 1375;
7. re-prove Redis/Celery transport;
8. record exact run/job/SHA/counts;
9. remove only the temporary validation workflow after successful validation;
10. prove validated SHA -> final candidate delta is exactly that workflow removal;
11. update `implementer.md` to the current 5.5 final candidate and validation evidence;
12. STOP for Reviewer.

Any product/test/doc/dependency change after the new successful validation requires another exact-head validation.

---

# 6. REVIEW DECISION

```text
REVIEW_DECISION: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
REVIEWED_HEAD_SHA: 81da6f4e12850a33d84e0cca258647b8ac4c7442
PR: #21
BLOCKERS: RPT55-H001
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
USER_LOCK_AUTHORIZED: NO
MERGE: NO
START_5_FINAL: NO
```

Reviewer does not merge and does not self-lock.

Implementer should harden only the blocker on the same branch/PR, revalidate, finalize handoff, then STOP.

> Mathematically validated scoring engine; empirical validation pending.
