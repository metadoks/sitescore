# SiteScore AI — Automation Consumer Handoff

## Status and version context

This document is the durable FAZ 5 automation-consumer contract for future orchestration consumers such as n8n.

- FAZ 5 locked base entering 5-FINAL: `main@8f757b81c0cb69e5e6be62f45e94ff9a57432cca`
- 5-FINAL branch: `faz5/5-final-integrated-product-audit`
- API package: `sitescore-api==0.3.0`
- Report package: `sitescore-report==0.3.0`
- API version: `/v1`
- Report artifact version: `sitescore-report-artifact-v1`
- Exact 5-FINAL validated/final SHA is recorded in the authoritative 5-FINAL Implementer/Reviewer handoff because a Git commit cannot self-embed its own SHA.

> Mathematically validated scoring engine; empirical validation pending.

## Authority boundary

**n8n is an orchestration consumer, not scoring/report truth authority.**

**FAZ 5 does not contain the production n8n workflow itself.**

Automation may submit inputs, retry uncertain transport operations, poll durable resources, branch on public states, and retrieve verified PDF bytes. It must never calculate or override SiteScore scoring, benchmark, financial, confidence, decision, narrative, presentation, provenance, artifact hash, storage identity, or canonical analysis truth.

The SiteScore server remains authoritative for:

```text
external request
-> authenticated /v1 API
-> durable PostgreSQL analysis lifecycle
-> Celery worker execution
-> frozen canonical acquisition + analysis
-> canonical terminal outcome
-> canonical report facts/domain/narrative/presentation
-> PDF rendering
-> private object storage
-> durable PostgreSQL report resource
-> authenticated verified report content
```

## API base contract

The versioned API path prefix is:

```text
/v1
```

The deployment origin/hostname is environment-specific and must be supplied by deployment configuration. Consumers must not hard-code an internal storage endpoint as an API base URL.

### Analysis endpoints

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
```

### Report endpoints

```text
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

V1 is polling-only. There is no callback/webhook delivery contract and cancellation is not supported.

## Bearer authentication and scopes

All V1 resources use a scoped service API key carried as:

```http
Authorization: Bearer <service-api-key>
```

Supported scopes are exactly:

```text
analysis:write
analysis:read
report:write
report:read
```

Typical automation permissions:

- submit analysis: `analysis:write`
- poll analysis: `analysis:read`
- resolve report resource: `report:write`
- inspect/download report: `report:read`

A consumer must not treat possession of an ID as authorization. Ownership is derived from the authenticated consumer bound to the service API key.

## Request, analysis, and report IDs

`request_id`, `analysis_id`, and `report_id` are different identities.

- `request_id`: server request/correlation UUID generated for an API request.
- `analysis_id`: server-generated UUIDv4 identifying the durable analysis resource.
- `report_id`: server-generated UUIDv4 identifying the durable report resource.

A caller does not choose analysis/report identity as a truth-authority mechanism. IDs, fingerprints and hashes never substitute for canonical object authority.

## Submit analysis

Request:

```http
POST /v1/analyses
Authorization: Bearer <key with analysis:write>
Idempotency-Key: <opaque retry key>
Content-Type: application/json
```

Body is the strict SiteScore `AnalysisRequest` contract exposed by OpenAPI. Caller data is intent/input data only; it does not carry trusted internal provider snapshots, scoring outputs, report values, provenance, storage paths or canonical authority.

Successful durable acceptance returns HTTP `202` with a resource containing:

```json
{
  "api_version": "v1",
  "request_id": "<uuid>",
  "analysis_id": "<uuid>",
  "state": "queued|running|completed|not_score_ready|failed|timed_out"
}
```

When the returned state is `queued` or `running`, the server may include `Retry-After`; consumers should respect it when polling.

## Idempotency-Key semantics

Analysis creation is protected by the combination of:

```text
consumer identity
+ Idempotency-Key
+ canonical request hash
+ PostgreSQL uniqueness
```

Rules:

- same authenticated consumer + same key + same canonical payload resolves to the same durable analysis;
- same authenticated consumer + same key + different canonical payload is an idempotency conflict;
- concurrent same-key/same-payload submissions must converge on one durable resource;
- automation must retain the same `Idempotency-Key` when retrying an uncertain POST whose HTTP outcome is unknown.

### Uncertain POST transport retry

If the client loses the HTTP response after sending `POST /v1/analyses`, it must **not** invent a new analysis by changing the retry key. Retry the same request with the same authenticated consumer, exact logical payload and exact `Idempotency-Key`. PostgreSQL-backed idempotency determines whether the first attempt was already durably accepted.

## Analysis lifecycle and polling

Public states are closed:

```text
queued
running
completed
not_score_ready
failed
timed_out
```

`queued` and `running` are nonterminal and may be polled.

Terminal states are immutable:

```text
completed
not_score_ready
failed
timed_out
```

A consumer may stop analysis polling once a terminal state is observed.

Poll with:

```http
GET /v1/analyses/{analysis_id}
Authorization: Bearer <key with analysis:read>
```

Respect `Retry-After` when present for `queued`/`running` resources. Do not create a parallel analysis merely because work remains nonterminal.

### Terminal meaning

- `completed`: canonical scored analysis completed; in the FAZ 5.5 durable contract, the current report artifact resource is also terminal (`ready` or `failed`).
- `not_score_ready`: canonical readiness gate did not authorize a scored result. It is not an error converted to zero and must not be treated as scored success.
- `failed`: analysis execution failed safely.
- `timed_out`: server-owned analytical deadline became terminal before protected canonical success.

Missing, unavailable and uncalibrated data must not be rewritten by automation into zero, bad, or calibrated values.

## Current COMB-005 limitation

The current frozen COMB-005 road/parking authority remains `NOT_APPROVED`. Therefore the real locked production acquisition path can legitimately end as:

```text
queued -> running -> not_score_ready
```

Automation must accept this as authoritative SiteScore output. It must not manufacture `completed`, a score, a decision, financial values, or a report when SiteScore returns `not_score_ready`.

## Resolve the durable report resource

Only a completed canonical analysis can have a delivery-ready report resource.

Request:

```http
POST /v1/reports
Authorization: Bearer <key with report:write>
Content-Type: application/json

{"analysis_id":"<uuid>"}
```

This endpoint is a **resolver**, not a generator.

It does not:

- rerun analysis;
- reconstruct report authority from stored JSON;
- accept caller score/confidence/decision/financial values;
- accept caller hash, filename, storage key or provenance;
- create a report for `not_score_ready`, `failed`, or `timed_out` analysis.

Repeated resolution of the same current analysis/artifact version resolves the same durable report identity.

## Report states

Report states are closed:

```text
ready
failed
```

### `ready`

A ready report has a durable server-owned content contract including SHA-256, byte length, MIME type, safe filename, artifact/report/narrative/presentation provenance and a consumer-facing content path.

### `failed`

A failed report means canonical analytical success remains valid but report generation/storage finalization failed closed. It has no downloadable content contract. V1 does not regenerate a failed report through `POST /v1/reports`.

Automation must not reinterpret report failure as analytical failure.

## Report metadata and content retrieval

Metadata:

```http
GET /v1/reports/{report_id}
Authorization: Bearer <key with report:read>
```

Verified PDF bytes:

```http
GET /v1/reports/{report_id}/content
Authorization: Bearer <key with report:read>
```

Only `ready` reports can return content.

The SiteScore API verifies private object content before streaming, including:

- object existence;
- maximum/bounded size;
- exact byte length;
- exact SHA-256;
- MIME type expectations;
- `%PDF-` signature.

A consumer may additionally compare response/report metadata such as `Content-SHA256`, but must not replace the server's integrity decision with its own guessed hash or object-store ETag semantics.

## Ownership and non-disclosure

Analysis and report resources are consumer-owned through authenticated server-side bindings.

Automation must expect missing and foreign resources to share non-disclosing not-found behavior where defined by the API. It must not use response differences as an ownership enumeration mechanism.

The API does not expose private storage keys, bucket names, object-store credentials or internal provider secrets. Consumers must never construct direct private-object URLs from guessed paths.

## Safe error handling

Automation should branch on documented HTTP status and machine error codes, not traceback text.

Do not persist or forward credentials/provider secrets in business logs. Server errors are intentionally sanitized and must not be treated as a source of internal analytical truth.

## Recommended orchestration sequence

```text
1. POST /v1/analyses with stable Idempotency-Key
2. retain returned analysis_id
3. poll GET /v1/analyses/{analysis_id}, honoring Retry-After
4. if completed:
      POST /v1/reports {analysis_id}
   if not_score_ready / failed / timed_out:
      stop and preserve authoritative terminal result
5. inspect report resource
6. if report=ready:
      GET /v1/reports/{report_id}/content
   if report=failed:
      stop; do not reinterpret analysis truth
7. deliver/store the verified PDF according to future orchestration policy
```

Future automation may add scheduling, notifications, payment/order coordination or delivery behavior only in its own authorized phase. Those orchestration decisions must remain downstream of SiteScore truth.

## Explicit non-authority rules for future n8n

A future n8n workflow must never:

- calculate or alter scoring math;
- decide readiness independently of SiteScore;
- substitute missing/unavailable values with zero;
- reconstruct `ApplicationAnalysisResult` from JSON;
- regenerate report truth from `result_body`;
- author final narrative facts outside the typed SiteScore narrative contract;
- choose or override report hash/storage key/filename/provenance;
- revive a terminal analysis state;
- treat Redis/Celery task state as public lifecycle truth;
- treat payment/order state as evidence that analysis/report truth exists.

SiteScore PostgreSQL-backed API resources remain the durable consumer truth boundary.