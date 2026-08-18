# FAZ 5.5 — Delivery-Ready Report Artifact Contract

## Status and scope

- Package: `sitescore-api==0.3.0`
- API version: `/v1` unchanged
- Exact locked base: `main@7d6ddbdb94567761733ff540239d959096d98f61`
- Report renderer consumed: locked `sitescore-report==0.3.0`
- Durable metadata truth: PostgreSQL
- PDF byte storage: private S3-compatible object storage
- Redis/Celery: execution transport only
- Artifact version: `sitescore-report-artifact-v1`
- Report schema migration: `0002_faz5_5`
- Canonical-success/report-finalization coordination migration: `0003_faz5_5`

> Mathematically validated scoring engine; empirical validation pending.

## Authority boundary

Report artifact generation occurs only inside the canonical analysis worker while live factory-owned authority exists:

```text
CanonicalAnalysisExecutor
-> CanonicalCompletedOutcome
-> exact CanonicalCompletedOutcome.application_analysis_result identity
-> build_canonical_report_facts(...)
-> build_report_domain_model(...)
-> build_validated_report_narrative(...)
-> render_report_pdf(...)
-> exact PDF bytes
-> SHA-256 / private object / durable metadata
```

Forbidden report authority paths:

```text
AnalysisModel.result_body JSON
canonical_success_at coordination marker
plain dictionaries / JSON
analysis fingerprint alone
analysis_id or report_id alone
stored request payload
analysis rerun from POST /v1/reports
caller score/financial/decision/confidence values
caller filename/hash/storage key/bucket/object path
```

The resolver API never generates or regenerates report truth. `canonical_success_at` is coordination evidence only; it never reconstructs a report or scored analytical object.

## Durable report identity

`report_id` is server-issued UUIDv4. The current artifact contract is uniquely bound by:

```text
(analysis_id, report_artifact_version)
```

Current artifact version:

```text
sitescore-report-artifact-v1
```

The server-owned object key is deterministic by consumer, analysis and artifact version. The safe download filename is based on `report_id` and cannot be caller-controlled.

## PostgreSQL report metadata

The `reports` table persists:

- `report_id`
- `analysis_id`
- artifact version/state
- exact source analysis fingerprint
- report schema/projection provenance
- narrative prompt/schema/provider/model/generation/fallback provenance
- presentation schema/policy provenance
- template/stylesheet/chart/renderer versions
- `generated_at`
- exact lowercase SHA-256
- MIME type
- safe filename
- byte length
- private storage key
- sanitized failure code/message
- created/updated timestamps

Closed states:

```text
ready
failed
```

Ready rows require coherent downloadable metadata and no failure fields. Failed rows require no downloadable object contract and a failure code.

## Paired terminal durability

A genuine canonical completed outcome is not exposed as durable `analysis.state=completed` before the current report artifact has a terminal resource.

Production ordering with report generation enabled:

```text
analysis durable state = running
-> canonical executor returns genuine CanonicalCompletedOutcome
-> record server-owned canonical_success_at before deadline
-> COMMIT running + canonical_success_at coordination marker
-> generate/upload PreparedReportArtifact from the SAME live canonical outcome
-> re-lock analysis
-> persist analysis completed + exact canonical result_body
-> persist report ready OR failed metadata
-> ONE PostgreSQL commit exposes the terminal pair
```

Externally durable completion invariant:

```text
analysis.state = completed
=> exactly one current report_artifact_version resource exists
=> report.state = ready OR failed
```

A process loss before the paired terminal commit leaves the analysis nonterminal and therefore redeliverable. Worker recovery may rerun canonical execution to recover live factory-owned authority. That worker retry is not API authority and does not promote stored JSON or the coordination marker into report authority.

Celery execution uses late acknowledgement and worker-loss redelivery semantics:

```text
task_acks_late = true
task_reject_on_worker_lost = true
result backend = disabled://
```

Report-finalization indeterminacy raises an explicit retry condition rather than returning successful `completed + missing report` or converting genuine analytical success into an analysis execution failure.

## Canonical success / timeout coordination

Locked FAZ 5.1 analytical deadline semantics remain authoritative until genuine canonical completed success is achieved.

`0003_faz5_5` adds nullable server-owned:

```text
analyses.canonical_success_at
```

The marker may be written only when canonical completed success was achieved strictly before `deadline_at`. Database checks require:

```text
canonical_success_at IS NULL
OR canonical_success_at < deadline_at

canonical_success_at IS NULL
OR state IN ('running','completed')
```

Before this marker exists, all locked timeout writers remain authoritative:

```text
GET/retrieve polling after deadline -> timed_out
periodic reconcile_expired after deadline -> timed_out
execute_analysis entry after deadline -> timed_out
```

After a genuine pre-deadline canonical success marker exists, report rendering, storage, ambiguous-commit reconciliation, process-loss recovery and worker retry may cross the original analysis deadline without rewriting that already-achieved analytical success to `timed_out`.

The timeout writers therefore exclude rows with `canonical_success_at IS NOT NULL`. Execute-analysis redelivery after deadline is allowed only for such a protected row and still reruns canonical execution through worker authority to recover a live canonical object.

If a timeout writer wins the row lock in the narrow interval after a genuine canonical completed result was reached before deadline but before the marker transaction commits, the worker may repair only the exact `analysis_deadline_exceeded` timeout using the live pre-deadline success timestamp. A success reached at or after the analytical deadline is never protected and remains timed out.

This coordination does **not** extend caller-controlled deadlines, disable deadlines globally, or grant a report API retry path.

## Analysis/report failure separation

Analytical truth remains owned by the locked analysis lifecycle.

- before canonical success, deadline/failure semantics are unchanged;
- genuine pre-deadline canonical success is durably protected while report finalization is pending;
- render/storage failure does not rewrite that success into `failed`, `not_score_ready`, or `timed_out`;
- report failure persists independently as terminal `report.state = failed` paired with `analysis.state = completed`;
- failed report rows expose no content path and V1 does not regenerate them;
- ambiguous report commit outcome is reconciled from a fresh PostgreSQL session before destructive object compensation;
- a conflicting durable resource is failed closed by the actual `(analysis_id, report_artifact_version)` identity, even when its durable `report_id` differs from the candidate.

If an object is uploaded but durable DB finalization is definitely absent, worker compensation performs a best-effort delete. If DB commit outcome is unknown, candidate storage is retained until fresh durable-state reconciliation makes cleanup safe.

## S3-compatible private storage

Runtime dependency:

```text
boto3==1.43.55
```

Server-owned configuration:

```text
SITESCORE_REPORT_STORAGE_BUCKET
SITESCORE_REPORT_STORAGE_REGION
SITESCORE_REPORT_STORAGE_ENDPOINT_URL  # optional S3-compatible endpoint
SITESCORE_REPORT_MAX_BYTES
```

Credentials remain AWS/boto credential-provider concerns and are not copied into SiteScore settings metadata, API responses, report metadata, PDFs, narrative context, or logs.

The adapter exposes only:

```text
put
head
get
delete
```

No public-read ACL is requested. Content retrieval does not redirect to storage and does not expose a storage key.

## Content integrity

The durable content contract is:

```text
mime_type = application/pdf
content_sha256 = SHA-256(exact persisted PDF bytes)
byte_length = exact persisted PDF length
```

Before API streaming, the backend verifies:

1. owner-scoped ready report row exists;
2. required durable content metadata is coherent;
3. object exists and reported size matches PostgreSQL;
4. bounded object read does not exceed configured maximum;
5. exact byte length matches;
6. SHA-256 of returned bytes matches PostgreSQL;
7. bytes begin with `%PDF-`.

ETag is not used as SHA-256 authority. Missing/tampered/corrupted objects fail closed and no PDF bytes are returned.

## V1 API contract

### `POST /v1/reports`

Requires `report:write`.

Strict request:

```json
{"analysis_id": "<uuid>"}
```

Semantics:

- missing/foreign analysis -> 404-equivalent `report_not_found`;
- `queued` / `running` -> 409 `report_not_yet_reportable`;
- a protected report-finalization/retry analysis remains public `running` until paired terminal durability;
- `not_score_ready` / `failed` / `timed_out` -> 409 `analysis_not_reportable`;
- `completed` + durable report row -> returns that exact row;
- `completed` + missing report row -> internal invariant failure;
- repeat resolve -> same `report_id`;
- no generation, no JSON rehydration, no rerun.

### `GET /v1/reports/{report_id}`

Requires `report:read`. Ownership is derived through the linked `AnalysisModel.consumer_id`. Foreign and missing resources share the same 404 boundary.

### `GET /v1/reports/{report_id}/content`

Requires `report:read`. Only `ready` resources with verified private object bytes are returned as `application/pdf`. Failed artifacts and integrity failures never return stored bytes.

Caller responses do not expose bucket, endpoint, private storage key, provider credentials, or internal object path.

## Locked upstream preservation

FAZ 5.5 does not modify `sitescore-report==0.3.0` or any frozen FAZ 3/4 analytical package. The dependency direction is:

```text
sitescore-api==0.3.0
-> sitescore-report==0.3.0
-> locked app/core authority
```

There is no reverse `sitescore-report -> sitescore-api` dependency.

Frozen COMB-005 remains NOT_APPROVED. The current real production provider path may still end `queued -> running -> not_score_ready`; 5.5 does not fabricate a completed analysis or report artifact from that state.

## Explicit exclusions

Not implemented in this checkpoint:

```text
payment / Stripe
n8n
email delivery
commercial order state
frontend behavior
webhooks / callbacks
public object URLs
caller-controlled storage paths
FAZ 6 orchestration
empirical validation
```
