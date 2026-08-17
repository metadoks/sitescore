# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.1
CHECKPOINT_TITLE: API Consumer Reliability + Execution Lifecycle

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
CODE_BRANCH: faz5/5-1-api-consumer-lifecycle
REVIEWED_HEAD_SHA: NONE
PR: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: NONE
```

---

# 1. PREDECESSOR POST-LOCK VERIFICATION

Reviewer independently verified the user-authorized FAZ 5.0 LOCK before opening this checkpoint.

```text
FAZ 5.0 PR: #16
Reviewer-approved head: 380ead27e8944ad7d6378f55c4948eb412c75c2c
PR state: CLOSED
PR merged: TRUE
merge commit: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
current main: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
merge parent 1: c34445e59ea37b4aa430ba1ffa1b4021be52c752
merge parent 2: 380ead27e8944ad7d6378f55c4948eb412c75c2c
```

The second parent is exactly the Reviewer-approved 5.0 head. No stale review or base drift occurred.

FAZ 5.0 is therefore locked and the new exact base for 5.1 is:

```text
92d00cda34d337ce5c4e172d5184c9e3f1f55b11
```

---

# 2. CHECKPOINT PURPOSE

Implement **FAZ 5.1 only**.

Convert the truthful 5.0 ingress foundation into a machine-consumer-safe asynchronous analysis resource with:

```text
scoped Bearer service API-key authentication
consumer isolation
durable PostgreSQL analysis state
durable DB-backed idempotency
race-safe duplicate handling
Celery worker execution
Redis broker transport
stable polling semantics
explicit timeout semantics
canonical terminal result persistence
```

Canonical public model:

```text
POST /v1/analyses
-> authenticated + idempotent durable acceptance
-> 202 + analysis_id

GET /v1/analyses/{analysis_id}
-> authenticated consumer-owned resource
-> current lifecycle state / terminal result
```

This checkpoint must make a future n8n consumer able to know exactly:

```text
how to authenticate
how to submit
how to retry a submission safely
how to use Idempotency-Key
what analysis_id means
what states exist
which states are terminal
how to poll
how not_score_ready differs from failed
what timeout means
```

Do **not** implement n8n itself.

---

# 3. FROZEN 5.0 / FAZ 4 AUTHORITY TO PRESERVE

The 5.0 external request contract remains the V1 ingress authority boundary:

```text
untrusted JSON
-> strict Pydantic request models
-> server request_id UUIDv4
-> distinct server analysis_id UUIDv4
-> factory-owned AnalysisIngressCommand
-> exact frozen sector-specific RevenueInput
```

Do not weaken 5.0 validation or allow caller authority injection.

The frozen FAZ 4 application chain remains mathematical/application authority:

```text
canonical ReadinessEvaluation
-> frozen pipeline terminal factory
-> RealDataPipelineResult
-> factory-owned ApplicationPipelineResult
-> canonical application scoring gate
-> factory-owned ApplicationScoringInput
-> exact frozen category aggregation
-> factory-owned ApplicationCategoryAggregationResult
-> exact frozen core CategoryScores + AnalysisInput adapter
-> factory-owned ApplicationCoreAnalysisInput
-> exact frozen sitescore.analyze.analyze exactly once per successful invocation
-> CanonicalAnalysisResult
-> factory-owned ApplicationAnalysisResult
-> framework-neutral transport projection
```

5.1 may orchestrate this chain downstream but may not reimplement its scoring, weighting, financial, decision, confidence, normalization, benchmark or readiness semantics.

The frozen application gate explicitly distinguishes:

```text
ELIGIBLE
NOT_SCORE_READY
PIPELINE_ERROR
INCONSISTENT_TERMINAL_STATE
```

These meanings must not be collapsed.

---

# 4. REQUIRED TECHNOLOGY / EXACT DEPENDENCY TARGETS

Continue package:

```text
sitescore-api
```

Package version for this checkpoint:

```text
sitescore-api==0.2.0
```

External API version remains:

```text
/v1
```

Keep existing 5.0 pins and add the selected 5.1 runtime stack.

Required exact targets:

```text
fastapi==0.140.0
pydantic==2.13.4
httpx==0.28.1
SQLAlchemy==2.0.51
alembic==1.18.5
psycopg[binary]==3.3.4
celery==5.6.3
redis==7.4.1
```

Keep the repository's compatible pytest baseline:

```text
pytest==8.4.2
```

All directly imported local SiteScore packages must be exact local/frozen version pins (`==0.1.0`) as actually required by the implementation. Do not add frozen packages merely because they exist; add a direct dependency only when production code directly imports it.

The selected Redis Python client is intentionally pinned to the 7.x stable line for this Celery 5.6.x checkpoint rather than silently adopting a newer major line. Exact resolver/runtime compatibility must be proven in CI.

If these selected dependency decisions are technically incompatible in the actual resolver/runtime and cannot be made correct without changing the selected architecture:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

and STOP.

---

# 5. ALLOWED PRODUCT SCOPE

Primary product scope:

```text
sitescore-api/**
```

Expected additions/refactors may include, as appropriate:

```text
configuration/settings
DB engine/session layer
SQLAlchemy models
repositories
Alembic environment + migrations
authentication/service-key layer
idempotency canonicalization
lifecycle state machine
transactional outbox
Celery application/tasks
worker execution service
server-owned canonical execution orchestration
route/response updates
tests/docs
narrow admin/provisioning CLI or programmatic helper for service API keys
```

A temporary validation-only workflow under `.github/workflows/**` is authorized only for clean Postgres/Redis/Celery integration evidence. If used, remove it before the final candidate unless Reviewer later explicitly accepts it as permanent CI scope.

Do not modify frozen FAZ 3 / FAZ 4 product semantics.

If a correct production execution path genuinely requires a frozen runtime-semantic change:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

and STOP instead of mutating frozen code.

---

# 6. DURABLE OPERATIONAL TRUTH

Non-negotiable ownership:

```text
PostgreSQL = durable analysis/lifecycle/idempotency/auth metadata truth
Redis = broker/queue transport only
Celery = execution infrastructure only
Celery result backend = NOT product truth
```

Do not persist canonical analysis state only in:

```text
Redis
Celery AsyncResult
process memory
filesystem pseudo-database
worker-local cache
```

Celery tasks should not require a Redis result backend to serve the public GET resource.

Prefer:

```text
task_ignore_result = true
```

or equivalent architecture proving that PostgreSQL alone is the public lifecycle source of truth.

---

# 7. IDENTITY MODEL

Keep these identities separate:

```text
request_id
analysis_id
Celery task_id
analysis_fingerprint
consumer_id
API key identity
```

Required meaning:

```text
request_id
= one HTTP request operation; fresh server UUIDv4 per request

analysis_id
= durable external analysis resource; server UUIDv4

Celery task_id
= internal broker/worker execution identity; never public analysis identity

analysis_fingerprint
= frozen canonical result metadata only; never auth/idempotency/request/job authority

consumer_id
= authenticated machine-consumer owner of resources
```

A retried POST receives a new `request_id` but, when idempotency matches, must resolve to the existing logical `analysis_id`.

Do not expose Celery task IDs in V1 external responses.

---

# 8. POSTGRESQL DATA MODEL — MINIMUM SEMANTICS

Exact private class/table names may vary, but the durable model must represent at least the following concepts.

## 8.1 Consumers

```text
consumer_id UUID primary key
name / label
active flag
created_at
```

No end-user account/payment model is authorized.

## 8.2 Service API keys

```text
internal key record id
public lookup key_id / prefix
consumer_id FK
one-way secret digest
scopes
active/revoked state
created_at
revoked_at nullable
```

Raw API-key secret must never be stored in PostgreSQL, committed source, logs, error responses or task payloads.

## 8.3 Analyses

Durable record must include at least:

```text
analysis_id UUID PK
consumer_id FK
creation request_id UUID
api_version
state
canonical validated request payload JSONB
canonical request hash
Idempotency-Key or equivalent durable unique value
internal Celery task_id nullable/persisted
created_at
updated_at
started_at nullable
finished_at nullable
deadline_at
terminal result status/body nullable
safe failure code/message nullable
```

Store the validated canonical caller intent required for worker reconstruction. Never store Authorization headers or raw API-key secrets.

## 8.4 Dispatch outbox

Use a durable transactional outbox or equivalent DB-first dispatch record.

At minimum:

```text
outbox row identity
analysis_id unique FK
internal task_id
created_at
dispatched_at nullable
attempt count
safe last-dispatch-error metadata nullable
```

The analysis row and its initial dispatch intent must be committed atomically in one PostgreSQL transaction.

---

# 9. AUTHENTICATION CONTRACT

Use scoped Bearer service API keys.

Header:

```text
Authorization: Bearer <service-api-key>
```

Required current scopes:

```text
analysis:write
analysis:read
report:write
report:read
```

5.1 routes enforce only the analysis scopes now. Report scopes are reserved for later FAZ 5 report endpoints and must not create report functionality in 5.1.

Required route authorization:

```text
POST /v1/analyses -> analysis:write
GET  /v1/analyses/{analysis_id} -> analysis:read
```

Service-key design requirements:

```text
high-entropy random secret
public lookup identifier distinct from secret
one-way digest stored, not plaintext
server-side secret pepper/configuration where used
constant-time digest comparison
revocation/active checks
consumer active check
```

A suitable implementation is a token carrying a non-secret lookup key ID plus a high-entropy secret, with HMAC-SHA256 or another reviewed one-way verifier over the secret using server-owned configuration. Do not use a fast plaintext database lookup of the raw secret.

If a provisioning helper/CLI is added, it may print the full token exactly once at creation; it must not persist or later recover the raw secret.

Stable auth errors:

```text
401 authentication_required / invalid_api_key
403 insufficient_scope
```

Use `WWW-Authenticate: Bearer` on appropriate 401 responses.

Do not log raw Authorization headers.

---

# 10. CONSUMER ISOLATION

Every durable analysis belongs to exactly one authenticated `consumer_id`.

A consumer must not read another consumer's resource merely by knowing/guessing the UUID.

For GET, use existence-hiding semantics:

```text
missing analysis for current consumer
OR
analysis belongs to another consumer
-> 404 analysis_not_found
```

Do not leak cross-consumer existence through 403/metadata/timing-sensitive secondary lookups when a single owner-scoped query can be used.

Idempotency uniqueness is consumer-scoped, not global across all consumers.

---

# 11. IDEMPOTENCY CONTRACT

`Idempotency-Key` is required for:

```text
POST /v1/analyses
```

Treat it as an opaque, non-blank, bounded header value. Reject control characters and unreasonable length. A maximum in the 128–255 byte range is acceptable; choose and document one exact limit.

Canonical target:

```text
authenticated consumer_id
+ Idempotency-Key
+ canonical request hash
```

Required semantics:

```text
same consumer + same key + same canonical payload
-> same analysis_id
-> no second logical analysis resource
-> POST remains safe to retry

same consumer + same key + different canonical payload
-> 409 idempotency_conflict

same key under different consumers
-> independent resources permitted
```

Critical race rule:

```text
durable PostgreSQL UNIQUE constraint
```

must protect the boundary.

A Python pre-check without DB uniqueness is insufficient.

On uniqueness conflict, re-read the authoritative owner-scoped record and compare the canonical request hash.

## 11.1 Canonical request hash

Hash only the validated request intent, not operational/auth identities.

Recommended deterministic input:

```text
Pydantic-validated model_dump(mode="json", exclude_none=False)
-> deterministic JSON
   sort_keys=True
   separators=(",", ":")
   ensure_ascii=False
   allow_nan=False
-> UTF-8
-> SHA-256
```

Because the 5.0 models trim strings and normalize accepted numeric values, semantically equivalent accepted representations should converge after validation where the models make them equivalent.

Exclude from hash:

```text
request_id
analysis_id
Idempotency-Key
Authorization/API key
task_id
analysis_fingerprint
server timestamps
```

The request hash is duplicate-detection metadata only. It is not scoring/application authority.

Stable missing-key/conflict errors should be machine-readable, e.g.:

```text
400 idempotency_key_required / invalid_idempotency_key
409 idempotency_conflict
```

---

# 12. DB/BROKER DUAL-WRITE SAFETY — TRANSACTIONAL OUTBOX

Do not implement:

```text
DB INSERT/COMMIT
then fire-and-forget Celery send
with no durable retry record
```

That creates an accepted analysis that can be permanently orphaned when Redis/publish fails.

Required model:

```text
transaction:
  insert analysis(state=queued)
  insert dispatch_outbox(analysis_id, task_id)
commit

then best-effort publish
```

If publish succeeds, mark the outbox row dispatched.
If publish fails, keep the durable outbox pending and keep the analysis resource durable.

Provide a retrying dispatcher/outbox drain mechanism. A periodic Celery-beat task, explicit dispatcher service, or equivalent narrow mechanism is acceptable, provided the pending DB outbox remains authoritative and can recover after broker restoration.

A same-payload idempotent POST replay should also be allowed to trigger a safe best-effort redispatch of a still-pending outbox rather than creating a new analysis.

Generate/persist an internal Celery task ID before publication and reuse that persisted ID for redispatch of the same dispatch intent. It must remain distinct from `analysis_id`.

Broker publish acknowledgement ambiguity may create duplicate task messages. The worker must therefore be safe under at-least-once delivery.

---

# 13. PUBLIC LIFECYCLE STATE MACHINE

Use exactly these V1 public states unless actual source evidence forces a documented equivalent naming decision:

```text
queued
running
completed
not_score_ready
failed
timed_out
```

Terminal states:

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

No `cancelled` endpoint/state is required in 5.1. Document explicitly:

```text
V1 analysis cancellation: NOT_SUPPORTED
```

Do not silently invent cancellation semantics.

Allowed conceptual transitions:

```text
queued -> running
queued -> timed_out
queued -> failed           only for durable execution/dispatch terminal failure rules explicitly defined
running -> completed
running -> not_score_ready
running -> failed
running -> timed_out
```

Terminal states are immutable. A late worker must not overwrite `timed_out`, `failed`, `completed` or `not_score_ready` with a different terminal state.

Use transactional compare-and-set / row locking so impossible state regressions fail closed.

---

# 14. WORKER DELIVERY / CONCURRENCY SEMANTICS

Celery/Redis delivery is at-least-once infrastructure. Do not claim exactly-once task execution.

The product guarantee is:

```text
one durable logical analysis resource per consumer/idempotency tuple
```

and safe state/result updates under duplicate task delivery.

Worker task payload must contain only the minimal internal locator, preferably:

```text
analysis_id
```

Do not put raw Authorization tokens, API secrets or a caller-authored canonical result in the broker message.

To prevent concurrent duplicate execution of one analysis, use a PostgreSQL-backed execution claim/lock. A session-level PostgreSQL advisory lock keyed deterministically from `analysis_id`, combined with the durable state machine, is an acceptable design:

```text
only one active worker may hold the execution lock
if duplicate message cannot acquire lock -> retry/no-op safely
if previous worker dies, DB session closes and the lock is released
```

Do not use Redis locks as the authoritative single-execution guard.

A worker that acquires the DB execution lock may safely retry a nonterminal `running` analysis left by a dead prior worker; document that infrastructure retry may repeat external acquisition work after a crash, but it must never create a second logical `analysis_id` and must never concurrently commit two terminal results.

---

# 15. TIMEOUT SEMANTICS

Timeout is a lifecycle concept, not a generic HTTP timeout.

Define a server-owned configured maximum analysis deadline and persist:

```text
deadline_at
```

The exact default/config key must be documented. Do not allow the caller to choose arbitrary worker deadlines in 5.1.

Required behavior:

```text
queued/running + now >= deadline_at
-> durable timed_out terminal state
```

Use both:

```text
worker/Celery soft-hard time limits as execution guard
AND
durable PostgreSQL deadline reconciliation
```

because a hard-killed worker may not execute cleanup code.

A periodic reconciliation task is acceptable, but GET/repository retrieval must also be able to atomically reconcile an expired nonterminal record before returning it so timeout truth does not depend solely on Redis/Celery availability.

If a worker later attempts to persist a successful result after the record became `timed_out`, the terminal compare-and-set must reject the late overwrite.

---

# 16. SERVER-OWNED CANONICAL EXECUTION SERVICE

5.1 must not stop at a fake lifecycle that can only transition under a test stub.

Implement a production execution service boundary in `sitescore-api` that reconstructs the durable validated request intent and legitimately composes the frozen provider/pipeline/application path.

Required high-level authority chain:

```text
durable validated request intent
-> server-owned deployment/provider configuration
-> frozen Census geocoding / provider evidence acquisition
-> frozen measurement / benchmark / readiness authority
-> frozen pipeline terminal factory
-> exact frozen application factories/gate
-> exact frozen core analysis only when ELIGIBLE
-> canonical terminal transport/result
```

Important source facts already verified:

```text
frozen Census address geocoder exists
server/deployment Census manifest/benchmark/vintage/policies remain non-caller authority
frozen application build_application_pipeline_result requires canonical readiness, sector, resolved_location, derived_metrics, source_metadata and optional evidence snapshots
frozen application gate distinguishes NOT_SCORE_READY / PIPELINE_ERROR / inconsistent state / eligible
```

There is no authorization to manufacture a `RealDataPipelineResult`, `ApplicationScoringInput`, `ApplicationCoreAnalysisInput` or `CanonicalAnalysisResult` from stored JSON merely to make the worker green.

The execution service must use the real frozen public factories.

If external provider HTTP/storage adapters are needed, they may be implemented downstream in `sitescore-api` using server-owned configuration and the frozen provider protocols. `httpx==0.28.1` is authorized as a runtime dependency for such network transport.

Do not accept provider manifest, vintage, policy, source refs, trusted coordinates or benchmark authority from the API caller.

If actual frozen public APIs make a correct production orchestration impossible without changing frozen semantics or relying on private unsupported internals:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

and STOP. Do not fabricate a successful executor.

---

# 17. CANONICAL TERMINAL MAPPING

The worker/lifecycle layer must map frozen application truth without changing semantics.

## 17.1 Eligible/scored

Only after canonical frozen application eligibility and exact frozen analysis execution succeeds:

```text
state = completed
result = deep-owned JSON-safe canonical transport body
```

Do not recompute score, financial outputs, decision, confidence, model versions or fingerprint in the API/worker layer.

## 17.2 NOT_SCORE_READY

If the frozen application gate reports canonical `NOT_SCORE_READY`:

```text
state = not_score_ready
```

Do not call core analyze.

Persist/project stable reason information directly from canonical gate/readiness reason codes. Do not invent a zero score or successful scored result.

## 17.3 PIPELINE_ERROR / inconsistent authority / execution exception

Map to:

```text
state = failed
```

with safe machine-readable error metadata.

`PIPELINE_ERROR` must never become `not_score_ready` or an empty successful result.

Do not persist tracebacks, raw secret-bearing exception reprs or provider credentials in public failure messages.

## 17.4 Timeout

Map only through the durable deadline semantics to:

```text
state = timed_out
```

Timeout is not `failed` and not `not_score_ready`.

---

# 18. PUBLIC RESPONSE CONTRACT

Keep the stable 5.0 SiteScore error envelope.

## 18.1 POST /v1/analyses

Required headers:

```text
Authorization: Bearer ...
Idempotency-Key: ...
```

Successful new or same-payload idempotent replay:

```text
HTTP 202
api_version: v1
request_id: fresh request UUIDv4
analysis_id: durable resource UUIDv4
state: current public lifecycle state
```

A replay must not return a new analysis ID.

Do not expose task_id.

## 18.2 GET /v1/analyses/{analysis_id}

Authenticated owner with `analysis:read` receives HTTP 200 for an existing resource regardless of queued/running/terminal state.

Response must include at least:

```text
api_version
request_id
analysis_id
state
created_at
updated_at
```

State-specific rules:

```text
queued/running:
  result absent/null
  error absent/null

completed:
  canonical result present
  error absent/null

not_score_ready:
  no scored canonical result
  canonical reason/status projection present

failed:
  no successful result
  safe machine error metadata present

timed_out:
  no successful result
  stable timeout metadata present
```

For nonterminal states, a `Retry-After` header with one documented polling interval is recommended and may be implemented. Do not make client polling cadence scoring authority.

Missing/foreign analysis:

```text
404 analysis_not_found
```

---

# 19. RETRY / POLLING CONTRACT FOR FUTURE N8N

Document the exact machine-consumer rules.

Required semantics:

```text
POST retry:
  reuse SAME Idempotency-Key and SAME payload

GET retry:
  safe and side-effect free except allowed timeout reconciliation

202:
  resource durably exists; begin polling GET

queued/running:
  nonterminal; poll again

completed:
  terminal scored result

not_score_ready:
  terminal business/data-readiness outcome; NOT infrastructure failure

failed:
  terminal execution failure

timed_out:
  terminal deadline outcome
```

At minimum document that these are not blindly retryable without changing conditions:

```text
401
403
409 idempotency_conflict
422 validation failure
```

For transport/5xx failures before a client knows acceptance, retry POST with the SAME idempotency key and payload.

V1 callback/webhook support remains:

```text
NONE
```

V1 integration model remains polling.

---

# 20. ALEMBIC / MIGRATION CONTRACT

Add a reproducible Alembic environment inside the package or an equivalent package-owned migration tree.

Required:

```text
initial migration from empty PostgreSQL database
all 5.1 tables/constraints/indexes
upgrade head succeeds
schema uniqueness/foreign keys/checks actually enforced
downgrade behavior defined and tested where safe
fresh upgrade after downgrade succeeds
```

Do not rely on SQLAlchemy `create_all()` as the production schema authority.

Tests must run against real PostgreSQL, not SQLite pretending to be PostgreSQL.

---

# 21. CONFIGURATION / SECRET BOUNDARY

All operational configuration is server/deployment-owned.

At minimum define explicit settings for:

```text
PostgreSQL URL
Redis/Celery broker URL
API-key verification pepper/secret
analysis deadline/timeout
provider credentials/configuration actually required by canonical executor
server-owned provider manifests/policies/benchmarks actually required
```

Do not hard-code secrets.
Do not commit real API keys/passwords.
Do not return them in errors.
Do not log them.

Missing required production configuration must fail closed rather than silently fall back to an insecure default.

Test settings/fake external credentials are permitted in test-only scope.

---

# 22. REQUIRED TESTS — AUTH / ISOLATION

At minimum:

```text
missing Authorization -> stable 401
malformed/unknown key -> stable 401
revoked key -> stable 401
inactive consumer -> stable 401/403 documented behavior
missing scope -> 403
analysis:write permits POST
analysis:read permits GET
write-only key cannot GET
read-only key cannot POST
raw key secret absent from DB
raw key secret absent from logs/errors
two consumers cannot read each other's analysis
foreign UUID and missing UUID produce same public 404 concept
```

---

# 23. REQUIRED TESTS — IDEMPOTENCY / RACES

At minimum:

```text
missing Idempotency-Key rejected
invalid/blank/oversized key rejected
same consumer + same key + same payload -> same analysis_id
replay receives fresh request_id
same consumer + same key + different payload -> 409
same key across different consumers -> separate resources
canonical payload hash deterministic
request_id/auth/idempotency/task/fingerprint excluded from hash
```

Concurrency test against PostgreSQL:

```text
two simultaneous same-key same-payload creates
-> exactly one analyses row
-> exactly one logical analysis_id
-> exactly one durable outbox intent
```

Race with same key/different payload:

```text
exactly one wins
other deterministically resolves to 409
```

No in-memory-only uniqueness tests are sufficient.

---

# 24. REQUIRED TESTS — OUTBOX / BROKER

At minimum:

```text
analysis + outbox committed atomically
broker unavailable after DB commit does not lose analysis
POST still does not fabricate execution success
pending outbox survives process restart
redispatch reuses persisted internal task_id
successful dispatch marks outbox dispatched
publish-ack ambiguity / duplicate message does not create new analysis
Redis deletion/restart does not delete durable analysis state
Celery AsyncResult is not used as GET truth
```

---

# 25. REQUIRED TESTS — WORKER / STATE MACHINE

At minimum:

```text
queued -> running -> completed
queued/running -> not_score_ready via canonical gate
pipeline error -> failed
unexpected safe execution failure -> failed
deadline expiration -> timed_out
terminal state cannot regress
late success cannot overwrite timed_out
late duplicate cannot overwrite completed
worker receives analysis_id, not API secret
worker reconstructs durable validated request intent server-side
worker uses factory-owned ingress/core/application authority
```

Duplicate-delivery concurrency test must prove the PostgreSQL execution claim prevents simultaneous execution of one analysis.

At least one scored integration path must exercise the exact frozen application/core chain rather than injecting a prebuilt `CanonicalAnalysisResult`/`ApplicationHttpResponse` as a fake worker result.

At least one not-score-ready integration path must exercise canonical frozen pipeline/gate semantics and prove core analyze is not invoked.

External network/provider responses may be deterministic test fakes at the provider/HTTP boundary. They may not replace internal canonical application authority with fabricated terminal DTOs.

---

# 26. REQUIRED TESTS — API / OPENAPI

Update runtime OpenAPI tests to prove:

```text
/v1 paths remain exact
Bearer security scheme declared
POST requires/authenticates write scope semantically
GET requires/authenticates read scope semantically
Idempotency-Key documented for POST
202 schema includes durable analysis_id/state
GET lifecycle enum exact
401/403/404/409/422/500/503 as actually possible are declared
internal task_id absent
raw API-key schema absent
no report/payment/n8n endpoints introduced
```

Do not handwrite a schema that differs from runtime behavior.

---

# 27. REQUIRED TESTS — MIGRATIONS / DEPENDENCIES / FULL REGRESSION

Use a clean validation environment with real service containers, recommended:

```text
PostgreSQL 16.x or 17.x
Redis 7.4.x
Python 3.11
```

Prove exact imported versions for the selected Python dependency pins.

Run:

```text
sitescore-api full unit + integration suite
all frozen package regression suites
```

Historical frozen reference remains:

```text
sitescore-app:         19
sitescore-pipeline:    53
sitescore-benchmarks: 191
sitescore-metrics:     67
sitescore-spatial:    180
sitescore-providers:  418
sitescore-data:       361
sitescore-core:        86
TOTAL FROZEN:        1375
```

Report actual fresh counts; do not copy the historical numbers as evidence.

If a temporary validation workflow is used, record run/job IDs and validated SHA. Remove the workflow before final review unless explicitly retained by a later Reviewer decision. If removed after validation, prove validated-SHA -> final-head delta contains only workflow removal or separately reviewed non-product cleanup.

---

# 28. DOCUMENTATION ARTIFACT

Create/update a durable checkpoint document such as:

```text
sitescore-api/docs/CHECKPOINT_5_1_API_CONSUMER_LIFECYCLE.md
```

It must truthfully record:

```text
package/API versions
auth mechanism + service-key format/provisioning
scope model
consumer isolation
Idempotency-Key rules
canonical request hash rules
analysis_id/request_id/task_id/fingerprint distinctions
PostgreSQL durable truth
Redis/Celery non-authority role
transactional outbox/recovery semantics
lifecycle states + terminal states
worker retry/at-least-once semantics
timeout semantics
cancellation unsupported
POST/GET request/response/error behavior
polling/retry guidance for future n8n
callback/webhook absent
canonical executor authority chain
configuration/secrets boundary
known limitations
```

Preserve canonical validity statement:

> Mathematically validated scoring engine; empirical validation pending.

Do not describe payment, report generation, n8n workflow or deployment as implemented.

---

# 29. EXPLICIT OUT OF SCOPE

Do not implement in 5.1:

```text
Stripe/payment/payment webhooks
n8n workflow JSON
customer email delivery
report package/report endpoints
OpenAI narrative
Jinja2/WeasyPrint/Matplotlib report work
S3 report storage
production global rate limiting
full observability platform
provider budget-control platform
frontend/account signup UI
empirical calibration/validation
V2 / Compare / Find
FAZ 6+
```

Do not create a hidden 5.2 or FAZ 6 inside 5.1.

---

# 30. IMPLEMENTATION / GIT PROTOCOL

Use exactly one new product branch:

```text
faz5/5-1-api-consumer-lifecycle
```

Base it exactly on:

```text
main
92d00cda34d337ce5c4e172d5184c9e3f1f55b11
```

Use one PR against `main`.

Any Reviewer hardening remains on this same branch and PR.

Do not merge.
Do not self-LOCK.
Do not start 5.2.

After implementation:

1. push branch,
2. open PR to `main`,
3. update `implementer.md`,
4. record exact base/head/PR,
5. record changed files and migrations,
6. record dependency resolver/import versions,
7. record PostgreSQL/Redis/Celery integration evidence,
8. record exact auth/idempotency/concurrency/outbox/state-machine tests,
9. record fresh full frozen regression,
10. record CI run/job IDs where used,
11. set `IMPLEMENTER_STATE: READY_FOR_REVIEW`,
12. STOP.

If source evidence requires frozen contract change:

```text
CONTRACT_CHANGE_REQUIRED: 1
IMPLEMENTER_STATE: BLOCKED_FOR_REVIEW
```

If selected stack/dependency decision is incompatible:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
IMPLEMENTER_STATE: BLOCKED_FOR_REVIEW
```

Then STOP.

---

# 31. ACCEPTANCE CRITERIA

Checkpoint 5.1 can become READY_TO_LOCK only when Reviewer independently verifies one exact PR head satisfies all of the following:

```text
[ ] exact expected base / one PR / correct branch
[ ] frozen FAZ 3/4 and locked 5.0 semantics preserved
[ ] PostgreSQL is sole durable lifecycle truth
[ ] Alembic migration reproducible on real PostgreSQL
[ ] Redis is broker transport only
[ ] Celery task/result state is not public truth
[ ] request_id / analysis_id / task_id / analysis_fingerprint distinct
[ ] scoped Bearer service API key implemented
[ ] raw service secrets not stored/logged
[ ] consumer isolation enforced
[ ] POST requires analysis:write
[ ] GET requires analysis:read
[ ] Idempotency-Key required and bounded
[ ] canonical request hash deterministic
[ ] DB uniqueness closes idempotency race
[ ] same key/same payload returns same logical resource
[ ] same key/different payload returns deterministic 409
[ ] transactional outbox closes DB/broker dual-write gap
[ ] pending dispatch recoverable after Redis failure
[ ] duplicate task delivery cannot create concurrent duplicate execution
[ ] public lifecycle exactly queued/running/completed/not_score_ready/failed/timed_out or approved equivalent
[ ] terminal state immutability enforced
[ ] timeout is durable and late worker cannot overwrite it
[ ] V1 cancellation explicitly unsupported
[ ] worker composes real frozen authority chain; no fabricated canonical result
[ ] eligible path invokes exact frozen analysis only through frozen application authority
[ ] not_score_ready does not invoke core analyze
[ ] pipeline error != not_score_ready/success
[ ] terminal result persisted in PostgreSQL
[ ] POST 202 means durable resource exists
[ ] GET polling contract truthful
[ ] OpenAPI matches runtime auth/idempotency/lifecycle behavior
[ ] future n8n retry/polling contract documented
[ ] no callback/webhook claim
[ ] no 5.2/report/payment/n8n implementation leakage
[ ] exact dependency/runtime validation passes
[ ] sitescore-api tests pass on real Postgres/Redis/Celery integration
[ ] fresh frozen regression passes
[ ] CONTRACT_CHANGE_REQUIRED = 0
[ ] DESIGN_DECISION_REVIEW_REQUIRED = 0
[ ] BLOCKERS = NONE
```

Reviewer acceptance is exact-SHA-specific.

---

# 32. STOP CONDITION

Implement **only FAZ 5.1** under this contract.

When implementation and evidence are complete:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

Then STOP and wait for the user's next Reviewer `Devam` cycle.

Do not start 5.2.
Do not merge.
Do not LOCK.
