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
plain dictionaries / JSON
analysis fingerprint alone
analysis_id or report_id alone
stored request payload
analysis rerun from POST /v1/reports
caller score/financial/decision/confidence values
caller filename/hash/storage key/bucket/object path
```

The resolver API never generates or regenerates report truth.

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

## Analysis/report failure separation

Analytical truth remains owned by the locked analysis lifecycle.

- canonical analytical success may persist `analysis.state = completed`;
- render/storage failure does not rewrite that success;
- report failure persists independently as terminal `report.state = failed`;
- failed report rows expose no content path and V1 does not regenerate them.

If an object is uploaded but durable DB finalization fails, worker compensation performs a best-effort delete. An orphan object without a durable row is safer than a `ready` durable row pointing at a known missing object.

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
