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

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 7d6ddbdb94567761733ff540239d959096d98f61
CODE_BRANCH: faz5/5-5-delivery-ready-report-artifact
REVIEWED_HEAD_SHA: NONE
PR: NONE

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
BLOCKERS: NONE
```

---

# 1. POST-LOCK VERIFICATION — FAZ 5.4

Reviewer independently verified the user-authorized 5.4 LOCK against live GitHub state.

```text
PR: #20
state: CLOSED
merged: TRUE
base SHA: 30a12424cebfb6bcd53ad6fcd5d5db1b2315d9ae
reviewed/merged head: d725df4022170f32c0d225677994d43dd5628273
merge commit: 7d6ddbdb94567761733ff540239d959096d98f61
post-lock main: 7d6ddbdb94567761733ff540239d959096d98f61
```

Merge commit parents were independently verified as exactly:

```text
parent 1: 30a12424cebfb6bcd53ad6fcd5d5db1b2315d9ae
parent 2: d725df4022170f32c0d225677994d43dd5628273
```

Live `main` is identical to the merge commit.

Implementer coordination record states:

```text
USER_LOCK_AUTHORIZED: YES
REVIEWED_AND_MERGED_HEAD_SHA: d725df4022170f32c0d225677994d43dd5628273
MERGE_COMMIT_SHA: 7d6ddbdb94567761733ff540239d959096d98f61
POST_LOCK_MAIN_SHA: 7d6ddbdb94567761733ff540239d959096d98f61
```

Therefore:

```text
FAZ_5_4_STATUS: LOCKED
```

Locked 5.4 rendering truth is now upstream authority for 5.5.

---

# 2. 5.5 PURPOSE

Create a durable report artifact/resource that a future FAZ 6 automation consumer can safely retrieve and deliver without becoming report/scoring authority.

Target external resources:

```text
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

Target durable semantic record includes, at minimum:

```text
report_id
analysis_id
analysis_fingerprint
report artifact/version identity
report schema/projection version
template/presentation/renderer version
narrative prompt/schema/provider/model/generation provenance
generated_at
content SHA-256
MIME type
filename
byte length
generation state
storage key
failure state where applicable
```

Storage contract:

```text
PostgreSQL = durable report metadata/state truth
S3-compatible private object storage = PDF bytes
Redis = queue transport only; never artifact truth
```

No report PDF binary may be persisted in PostgreSQL merely for convenience.

---

# 3. CRITICAL AUTHORITY DECISION — NO POST-HOC REHYDRATION FROM JSON

This checkpoint must preserve locked 5.2/5.3/5.4 authority.

Current 5.1 durable analysis row stores:

```text
result_body: JSONB
```

But locked report authority explicitly does NOT accept a dict/JSON projection as canonical report authority.

Therefore 5.5 MUST NOT implement:

```text
AnalysisModel.result_body JSON
-> reconstruct/forge ApplicationAnalysisResult
-> reconstruct/forge ReportDomainModel
-> generate PDF
```

It also MUST NOT rerun a completed analysis merely to obtain new in-memory authority for a report. A rerun could consume changed external evidence and would not be provably the exact completed analysis.

Required generation point:

```text
CanonicalAnalysisExecutor
-> CanonicalCompletedOutcome
-> exact live factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
-> ValidatedReportNarrative
-> render_report_pdf(...)
-> exact PDF bytes
-> durable artifact
```

The artifact must be generated while the exact canonical application result from the original analysis execution is still live and factory-owned.

No serialized fingerprint/hash/ID can replace this authority chain.

---

# 4. PACKAGE / DEPENDENCY DIRECTION

Primary 5.5 product scope is expected to be:

```text
sitescore-api/**
```

`sitescore-report==0.3.0` is now a locked upstream view/report package and should remain unchanged unless a genuinely necessary narrow compatibility issue is discovered and Reviewer explicitly reopens it.

Expected dependency direction:

```text
sitescore-api
-> sitescore-report==0.3.0
-> sitescore-app / sitescore-core
```

This is allowed because `sitescore-report` does not depend on `sitescore-api`.

Do not create a reverse import from report into API.

Advance `sitescore-api` package version appropriately for 5.5 while keeping external API version `/v1` unchanged.

An S3-compatible adapter may add an exact-pinned S3 client dependency such as `boto3`; it must remain provider-neutral by supporting configurable S3 endpoint/bucket/region semantics rather than hard-coding AWS-specific product behavior.

Do not upgrade unrelated locked dependencies.

---

# 5. REPORT ARTIFACT IDENTITY

Use a server-generated UUIDv4:

```text
report_id
```

Keep identities distinct:

```text
request_id != analysis_id != task_id != report_id != analysis_fingerprint
```

Define a code-owned artifact contract/version, for example:

```text
REPORT_ARTIFACT_VERSION = sitescore-report-artifact-v1
```

The exact constant name is implementation-owned, but the semantic identity must be explicit and versioned.

V1 should have at most one artifact for:

```text
(analysis_id, report_artifact_version)
```

Enforce this with a durable DB uniqueness constraint.

`analysis_fingerprint` is persisted as provenance/binding metadata only. It never grants authority by itself.

---

# 6. POSTGRESQL REPORT MODEL

Add a new Alembic migration after current:

```text
0001_faz5_1_consumer_lifecycle
```

Create a durable reports table/model with a schema equivalent to the following semantics:

```text
report_id UUID PK
analysis_id UUID FK -> analyses.analysis_id
report_artifact_version
state
analysis_fingerprint
report_schema_version
report_projection_version
narrative_prompt_version
narrative_schema_version
narrative_provider
narrative_model_id nullable
narrative_generation_mode
narrative_fallback_version nullable
presentation_schema_version
presentation_policy_version
template_version
stylesheet_version
chart_version
renderer_version
generated_at
content_sha256 nullable by state
mime_type nullable by state
filename nullable by state
byte_length nullable by state
storage_key nullable by state
failure_code nullable by state
failure_message nullable by state
created_at
updated_at
```

Exact physical column grouping may vary if still fully auditable, but do not hide artifact binding behind an opaque caller-controlled blob.

Recommended V1 report states:

```text
ready
failed
```

There is no need to invent a second asynchronous report worker/state machine in this checkpoint because post-hoc JSON regeneration is forbidden.

Database constraints must enforce state coherence. At minimum:

```text
ready -> content_sha256, MIME, filename, byte_length, storage_key all present
ready -> failure fields absent
failed -> no downloadable storage contract may be claimed
state in closed allowed set
unique(analysis_id, report_artifact_version)
```

Consumer ownership should be derived from the authoritative analysis relationship rather than trusting a duplicated caller-supplied consumer ID. API lookups must join/filter through the analysis owner.

---

# 7. ANALYSIS COMPLETION + REPORT GENERATION SEMANTICS

Preserve locked analysis lifecycle meaning.

A successful canonical score may remain:

```text
analysis.state = completed
```

even if the separate report artifact generation fails. Do NOT reinterpret an analytically valid completed result as `not_score_ready` merely because rendering/storage failed.

Required worker behavior for a genuine canonical completed outcome:

```text
1. retain exact CanonicalCompletedOutcome / ApplicationAnalysisResult authority
2. attempt exact report facts/domain construction
3. build validated narrative
4. render exact PDF through locked 5.4 renderer
5. compute exact PDF metadata/hash
6. attempt S3-compatible storage
7. persist analysis completed result using existing canonical persist_completed path
8. atomically persist report metadata as ready OR failed
```

The analysis result and report metadata finalization must be coordinated so the system never exposes:

```text
report.state = ready
```

unless the referenced object was actually written under the exact server-owned storage key.

If report generation/rendering/storage fails while canonical analysis succeeded:

```text
analysis may still be completed
report.state = failed
content endpoint unavailable
failure is explicit and sanitized
```

Do not fabricate PDF bytes or a `ready` report.

Because canonical authority cannot be safely reconstructed later, V1 failed report generation is terminal for that analysis resource. `POST /v1/reports` MUST NOT silently rerun the analysis or rebuild report authority from JSON. Document this limitation truthfully.

---

# 8. OBJECT STORAGE CONTRACT

Implement a narrow object-storage abstraction plus a concrete S3-compatible adapter.

Required conceptual operations:

```text
put PDF bytes
get PDF bytes
head/metadata as needed for verification
delete for compensation/cleanup where required
```

Production storage configuration must be server-owned. A compatible configuration surface should cover:

```text
bucket
region where applicable
endpoint URL where applicable
credential provider/secret handling outside response/provenance/log output
```

Do not hard-code a public cloud vendor endpoint.

Storage credentials MUST NOT appear in:

```text
API responses
report metadata returned to callers
PDF
narrative context
logs
Git history
content hash/provenance
```

Bucket/object access is private application infrastructure. Do not create public-read objects.

---

# 9. STORAGE KEY POLICY

Storage keys are code-owned and server-generated.

Never accept from caller:

```text
storage_key
bucket
object path
filename path
content hash
report_id
```

Prefer a deterministic versioned object key derived only from server-owned identities, for example semantically:

```text
reports/{consumer-or-tenant-scope}/{analysis_id}/{report_artifact_version}.pdf
```

Do not use caller text/address/business name in storage paths.

A deterministic per-analysis/version key is preferred so a pre-commit retry overwrites the same intended object rather than creating unbounded orphan keys.

`storage_key` remains internal metadata and should not be exposed as a customer authority token.

---

# 10. CONTENT HASH / INTEGRITY

Compute:

```text
SHA-256(exact PDF bytes)
```

Persist lowercase canonical hex plus exact byte length.

Hash semantics:

```text
content hash = artifact integrity evidence
content hash != scoring authority
content hash != report-domain authority
content hash != analysis authority
```

Before serving report content, verify at minimum:

```text
object exists
byte length == persisted byte_length
SHA-256(bytes) == persisted content_sha256
bytes are consistent with expected PDF contract/signature
```

If integrity fails:

```text
DO NOT stream corrupted/mismatched bytes
return stable explicit artifact-integrity error
```

Do not trust S3 ETag as SHA-256 identity.

Bound the maximum report object size to a reasonable code/config-owned limit so content verification cannot become an unbounded-memory path.

---

# 11. FILENAME / MIME CONTRACT

For ready V1 PDF artifact:

```text
MIME type = application/pdf
```

Filename is server-owned and header-safe, preferably derived from `report_id` or another safe canonical identifier.

Do not derive a filesystem/header filename from raw caller business/address text.

Content response should set a controlled attachment filename.

---

# 12. REPORT API CONTRACT

## POST /v1/reports

Strict request body:

```text
analysis_id
```

No extra fields.

Requires:

```text
Bearer service API key
scope: report:write
```

This endpoint is NOT a post-hoc report recomputation endpoint.

Its V1 semantic purpose is to resolve the durable report resource already created by the canonical analysis execution path.

Required behavior:

```text
analysis belongs to authenticated consumer -> continue
analysis missing / other consumer -> 404-equivalent fail closed
queued/running -> stable not-yet-reportable conflict
not_score_ready/failed/timed_out -> stable not-reportable conflict
completed + report row exists -> return exact report resource
completed + report row missing -> internal invariant failure; do not regenerate from JSON
```

Repeated calls for the same consumer/analysis/version must return the same durable `report_id` and must not mint duplicate report resources.

Because this route resolves a unique server-created artifact rather than creating new analytical work, no caller idempotency key is required unless implementation introduces a genuine new side effect. If one is introduced, it must use durable race-safe DB semantics equivalent to locked 5.1, not memory-only state.

## GET /v1/reports/{report_id}

Requires:

```text
scope: report:read
```

Return consumer-owned report metadata/resource state.

Do not reveal whether another consumer owns the supplied ID; use the same not-found boundary as locked analysis ownership.

## GET /v1/reports/{report_id}/content

Requires:

```text
scope: report:read
```

V1 delivery mechanism selected for this checkpoint:

```text
authenticated direct API response of verified PDF bytes
```

Do not redirect callers to an arbitrary storage URL and do not expose a raw storage key.

Only `ready` reports return content.

`failed` reports must return an explicit non-success response and zero artifact bytes.

---

# 13. REPORT RESOURCE RESPONSE

External metadata response should expose only useful durable contract fields such as:

```text
api_version
request_id
report_id
analysis_id
state
generated_at
analysis_fingerprint
report/artifact version
content_sha256 if ready
mime_type if ready
filename if ready
byte_length if ready
content URL/path if ready
narrative/report/presentation provenance as appropriate
failure code/message if failed
```

Do NOT expose:

```text
storage credentials
bucket secret/config
raw internal storage key unless explicitly justified
serialized internal authority objects
caller-forgeable trusted flags
```

API projections remain views, not authority.

---

# 14. CROSS-CONSUMER / CROSS-ANALYSIS SECURITY

A report must be provably bound to the exact analysis that produced it.

Required protections:

```text
report.analysis_id is a durable DB FK
report resource lookup is owner-scoped through analysis.consumer_id
report generation receives analysis_id from the locked server-owned analysis row/command
storage key is generated server-side
analysis_fingerprint comes from exact report/application authority
content hash comes from exact rendered PDF bytes
```

Attacks that must fail:

```text
Consumer A requests Consumer B analysis report
Consumer A fetches Consumer B report_id
caller submits report_id
caller submits storage_key
caller submits analysis_fingerprint to attach artifact
caller swaps analysis_id after PDF generation
report metadata from analysis A points to object from analysis B
```

No cross-analysis artifact substitution.

---

# 15. TRANSACTION / FAILURE COHERENCE

PostgreSQL and S3 do not share a distributed transaction. Handle this explicitly rather than pretending atomicity.

Required safety outcome:

```text
DB ready row must never point to an object known not to have been written
object upload success followed by DB failure must not create caller-visible ready metadata
```

Use a safe ordering with compensation as appropriate, for example:

```text
render/hash
-> put deterministic object
-> verify storage acknowledgement/metadata
-> DB transaction persist completed analysis + report ready row
-> if DB finalization fails, best-effort delete/compensate object and fail closed
```

A storage orphan with no DB resource is undesirable but is safer than a DB `ready` row with missing/wrong bytes. Tests must prove no false ready state.

Do not use Redis as a transaction journal or durable artifact registry.

---

# 16. CURRENT PRODUCTION LIMITATION

Frozen truth remains:

```text
COMB-005 = NOT_APPROVED
current real production canonical lifecycle -> not_score_ready
```

Therefore current real production execution still does not produce a scored report artifact.

5.5 MUST NOT manufacture a report for `not_score_ready`.

Positive artifact integration tests may use the established test-only SCORE_READY substitution, but they must still obtain genuine factory-owned:

```text
ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
-> ValidatedReportNarrative
-> PDF
```

No forged top-level authority fixtures.

---

# 17. REQUIRED TESTS — DATABASE / MIGRATION

At minimum:

```text
clean PostgreSQL upgrade 0001 -> new 5.5 migration
report table constraints
UUID report identity
unique analysis/version artifact
ready-state completeness constraints
failed-state coherence constraints
analysis FK integrity
migration reproducibility
```

No SQLite substitute for authoritative migration validation.

---

# 18. REQUIRED TESTS — GENERATION AUTHORITY

Test:

```text
genuine canonical completed outcome -> report artifact generation succeeds
serialized AnalysisModel.result_body cannot create report authority
plain dict/JSON cannot be passed as report generation authority
cross-analysis source substitution rejected
mutated/copied report/narrative authority rejected by locked validators
not_score_ready creates no ready artifact
report builder does not rerun canonical analysis
report builder does not call scoring/finance decision logic independently
```

Add a regression proving artifact generation consumes the exact `CanonicalCompletedOutcome.application_analysis_result` identity from the same worker execution.

---

# 19. REQUIRED TESTS — REPORT STATE / FAILURE

Test at minimum:

```text
render failure -> report failed, never ready/fake PDF
storage put failure -> report failed, never ready
DB finalization failure after upload -> no caller-visible ready row; compensation attempted
ready row -> exact object exists
failed row -> content endpoint cannot deliver
completed analysis + missing report row -> invariant error, no JSON regeneration
same analysis/version -> same durable report resource, no duplicate
```

Preserve analytically completed state when only report generation fails, unless an existing locked lifecycle invariant makes that technically impossible; if so, STOP and escalate rather than silently redefining 5.1 semantics.

---

# 20. REQUIRED TESTS — AUTH / API

Using real PostgreSQL-backed service keys:

```text
POST report requires report:write
GET metadata requires report:read
GET content requires report:read
invalid/revoked key rejected
wrong scope rejected
cross-consumer analysis POST -> 404 boundary
cross-consumer report GET -> 404 boundary
cross-consumer content GET -> 404 boundary
queued/running analysis -> not-yet-reportable
not_score_ready -> not-reportable
failed/timed_out analysis -> not-reportable
completed ready -> metadata + content
completed report-failed -> metadata failure + no content
strict POST extra fields rejected
OpenAPI matches actual routes/security/status models
```

Existing `ALL_SCOPES` already includes `report:write` and `report:read`; preserve that contract.

---

# 21. REQUIRED TESTS — STORAGE / CONTENT INTEGRITY

Test with both a deterministic fake/unit adapter and real S3-compatible integration evidence.

Authoritative CI should use a real S3-compatible service such as a fixed MinIO image/release or equivalent.

Test:

```text
put/get exact bytes
private server-owned key
head/content-length verification
missing object
storage unavailable/error
wrong byte length
mutated object bytes
wrong SHA-256
PDF signature mismatch
forbidden oversized object
server-owned filename and Content-Disposition
storage key not accepted from API
storage key not leaked as authority
```

A tampered object must never be streamed successfully.

---

# 22. REQUIRED REGRESSION

Fresh validation must include:

```text
sitescore-api complete 5.5 suite
sitescore-report locked suite = 24 PASS
frozen FAZ 3/4 regression = 1375 PASS
real PostgreSQL migration
real Redis/Celery locked transport regression
real S3-compatible object-storage integration
```

If final API suite count is `A`, expected combined total is:

```text
1375 + 24 + A
```

unless an explicitly Reviewer-authorized baseline change is documented.

No live OpenAI call/key is required; use deterministic fallback or a fake provider boundary for validation.

---

# 23. VALIDATION EVIDENCE

Before handoff, Implementer must record:

```text
exact product/test/doc SHA
Python 3.11 exact version
all direct dependency exact versions
sitescore-api test count
sitescore-report 24 PASS
all frozen package counts
PostgreSQL version + migration success
Redis/Celery transport success
S3-compatible service/version + put/get/integrity success
OpenAPI endpoint/security evidence
```

If a temporary GitHub workflow is used:

```text
checkout exact PR branch HEAD explicitly
assert git rev-parse HEAD == expected SHA
validate that SHA
record workflow run/job IDs
remove temporary workflow only after success
prove validated SHA -> final HEAD delta is workflow removal only
```

Any product/test/dependency/migration/API change after validation requires fresh validation.

---

# 24. EXPLICIT OUT OF SCOPE — FAZ 5.5

Do NOT implement:

```text
Stripe Checkout
payment authorization
payment verification
payment webhook
n8n workflow JSON
n8n execution
customer email delivery
commercial order state
refund workflow
frontend
public customer account system
presigned public delivery flow unless Reviewer re-authorizes
full production deployment/autoscaling
empirical validation/calibration
FAZ 6+
```

FAZ 6 will orchestrate these frozen API/report resources later.

---

# 25. REVIEWER ACCEPTANCE GATE

Reviewer will independently inspect exact future 5.5 PR head for:

```text
exact base = 7d6ddbdb94567761733ff540239d959096d98f61
one branch / one PR
scope limited to 5.5
5.4 and earlier locked packages preserved except authorized API dependency wiring
no JSON authority rehydration
no analysis rerun for report generation
exact live completed-outcome authority consumed
report_id UUIDv4 / durable analysis binding
PostgreSQL metadata correctness
S3-compatible storage adapter correctness
server-owned object key
hash/length/PDF integrity verification
ready/failed state coherence
cross-consumer isolation
cross-analysis substitution resistance
direct authenticated content retrieval
no storage secret/key leakage
migration correctness
OpenAPI/runtime agreement
real PostgreSQL + Redis/Celery + S3-compatible validation
locked report/frozen regressions
no FAZ 6 leakage
```

Decision will be exactly one of:

```text
NEEDS_HARDENING / HARDEN
READY_TO_LOCK / LOCK_IF_USER_AUTHORIZED
```

No auto-lock. Reviewer never merges.

Current action:

```text
IMPLEMENTER_ACTION: IMPLEMENT
USER_LOCK_AUTHORIZED: NO
MERGE: NO
START_5_FINAL: NO
```

Implementer must create/use branch:

```text
faz5/5-5-delivery-ready-report-artifact
```

from exact base:

```text
7d6ddbdb94567761733ff540239d959096d98f61
```

Implement only 5.5, open one PR, validate comprehensively, update `implementer.md` to READY_FOR_REVIEW, then STOP.

> Mathematically validated scoring engine; empirical validation pending.
