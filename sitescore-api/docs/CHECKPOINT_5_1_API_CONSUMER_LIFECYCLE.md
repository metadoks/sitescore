# SiteScore AI — FAZ 5.1 API Consumer Reliability + Execution Lifecycle

## Status and versions

- Package: `sitescore-api==0.2.0`
- External API: `/v1`
- Base checkpoint: locked FAZ 5.0
- PostgreSQL: durable product truth
- Redis: broker transport only
- Celery: execution infrastructure only; task results are ignored

> Mathematically validated scoring engine; empirical validation pending.

## Authentication and service keys

V1 uses scoped machine-consumer Bearer service API keys:

```http
Authorization: Bearer ssk1_<public-key-id>.<secret>
```

The key ID is a public lookup identifier. The secret is high entropy and is shown only once by provisioning. PostgreSQL stores an HMAC-SHA256 verifier produced with a server-owned pepper; it never stores the raw secret. Verification uses constant-time digest comparison and checks key revocation/active state plus consumer active state.

Defined scopes are `analysis:write`, `analysis:read`, `report:write`, and `report:read`. FAZ 5.1 enforces only the two analysis scopes. Report scopes reserve vocabulary only and do not create report functionality.

- POST requires `analysis:write`.
- GET requires `analysis:read`.
- Authentication failures are stable 401 errors with `WWW-Authenticate: Bearer`.
- Missing scope is stable 403 `insufficient_scope`.

## Consumer isolation

Every analysis belongs to exactly one authenticated `consumer_id`. GET performs an owner-scoped query. A missing UUID and a UUID owned by another consumer both return 404 `analysis_not_found`; the API does not reveal cross-consumer existence.

Idempotency uniqueness is also consumer-scoped.

## Identity model

The following identities are intentionally distinct:

- `request_id`: fresh server UUIDv4 for every HTTP operation, including idempotent replays.
- `analysis_id`: durable external analysis resource UUIDv4.
- `task_id`: internal Celery dispatch identity, persisted in PostgreSQL and never exposed in V1 responses.
- `analysis_fingerprint`: canonical frozen result metadata only; not request, auth, idempotency, or job authority.
- `consumer_id`: authenticated machine-consumer owner.
- service-key record/key ID: authentication identity, distinct from consumer and analysis identities.

## Idempotency-Key

`Idempotency-Key` is mandatory for POST. It is opaque, nonblank, control-character-free, and limited to **200 UTF-8 bytes**.

Canonical request hash input is the validated Pydantic model:

```text
model_dump(mode="json", exclude_none=False)
-> JSON sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
-> UTF-8
-> SHA-256
```

Operational/auth identities are excluded from the hash: request ID, analysis ID, Idempotency-Key, Authorization/API key, task ID, analysis fingerprint, and timestamps.

Semantics:

- same consumer + same key + same canonical payload -> same `analysis_id`, no second logical resource;
- same consumer + same key + different payload -> 409 `idempotency_conflict`;
- same key for different consumers -> independent resources.

A PostgreSQL UNIQUE constraint on `(consumer_id, idempotency_key)` closes the race. On uniqueness conflict the server re-reads the authoritative owner/key record and compares the canonical request hash.

## Durable acceptance and transactional outbox

POST acceptance transaction:

```text
insert analysis(state=queued)
insert dispatch_outbox(analysis_id, persisted task_id)
COMMIT
```

Only after that durable commit does the API make a best-effort broker publish. A Redis/publish failure does not erase the accepted resource. The pending outbox row records only safe generic dispatch error metadata and can be drained later. Redispatch reuses the same persisted internal task ID.

A same-payload idempotent replay may trigger another safe dispatch attempt for a pending resource; it does not create a second analysis.

Broker acknowledgement ambiguity can duplicate task messages. Celery/Redis therefore provide at-least-once delivery, not exactly-once execution.

## Public lifecycle

Exact V1 states:

```text
queued
running
completed
not_score_ready
failed
timed_out
```

Terminal states: `completed`, `not_score_ready`, `failed`, `timed_out`.

Nonterminal states: `queued`, `running`.

Conceptual transitions:

```text
queued -> running
queued -> timed_out
queued -> failed
running -> completed
running -> not_score_ready
running -> failed
running -> timed_out
```

Terminal states are immutable. Worker writes use PostgreSQL row locking plus terminal checks; a late success cannot overwrite `timed_out` and duplicate delivery cannot replace an existing terminal result.

V1 analysis cancellation: **NOT_SUPPORTED**.

## Worker delivery and execution claim

Celery task payload contains only `analysis_id`. Authorization tokens, API secrets, caller-authored results, and canonical result bodies are never placed on the broker.

A PostgreSQL session-level advisory lock derived deterministically from `analysis_id` is the active-execution claim. Redis locks are not authority. Only one worker session can execute a logical analysis at a time. If a worker dies, the DB session releases its advisory lock. A later infrastructure retry may repeat external acquisition work, but it cannot create a second logical analysis or concurrently commit two terminal states.

Celery is configured with ignored results and no product result backend. Public GET never consults `AsyncResult`.

## Timeout semantics

The server owns the analysis deadline. Default configuration is:

```text
SITESCORE_ANALYSIS_DEADLINE_SECONDS=900
SITESCORE_WORKER_SOFT_LIMIT_SECONDS=840
SITESCORE_WORKER_HARD_LIMIT_SECONDS=900
```

The durable `deadline_at` is stored in PostgreSQL. A queued/running record with `now >= deadline_at` becomes terminal `timed_out` with stable `analysis_deadline_exceeded` metadata.

Timeout truth is reconciled in three places:

1. worker start/terminal persistence checks,
2. periodic reconciliation task,
3. owner-scoped GET before returning the resource.

This means timeout truth does not depend on Redis or on a hard-killed worker running cleanup code.

## Canonical execution authority

Durable validated caller intent is reconstructed into the server-owned 5.0 `AnalysisIngressCommand`. Provider/benchmark evidence is not accepted from API JSON. A deployment-owned execution evidence source supplies frozen typed evidence and benchmark artifacts; production configuration for this source is server-owned.

The execution service then uses the real frozen public chain:

```text
server-owned typed evidence / benchmark artifacts
-> frozen sitescore-metrics measurements
-> frozen benchmark normalize_feature
-> frozen COMB-005 evaluation
-> frozen normalized feature assembly
-> frozen scoring readiness
-> frozen application pipeline result
-> frozen application scoring gate
```

If the gate is `NOT_SCORE_READY`, the API creates a factory-owned canonical not-score-ready capability from the exact canonical `ApplicationPipelineResult`, persists readiness/reason projection, and **does not call core analyze**.

Only if the frozen gate is genuinely `ELIGIBLE` may the service continue through frozen application scoring/category/core-input factories and `analyze_application_core_input`. `completed` persistence additionally requires a server-factory-owned capability bound to an exact canonical `ApplicationAnalysisResult`. Plain JSON, a fingerprint, a caller flag, or stored request data cannot authorize `completed`.

### Current locked production truth

Frozen COMB-005 has no approved production road/parking composite policy. Its canonical production result is `POLICY_NOT_APPROVED`, has no numeric score, and makes road/parking readiness unavailable. Therefore the current real canonical production path is expected to terminate:

```text
queued -> running -> not_score_ready
```

`completed` is modeled and guarded for a future frozen authority state, but FAZ 5.1 **does not claim that the current locked model can produce a scored completed result**. No score, zero score, neutral value, or fabricated terminal DTO is substituted.

## POST /v1/analyses

Required headers:

```http
Authorization: Bearer ...
Idempotency-Key: ...
```

Successful new creation or same-payload replay:

```text
HTTP 202
api_version=v1
request_id=<fresh UUIDv4>
analysis_id=<durable UUIDv4>
state=<current lifecycle state>
```

`task_id` is never returned. Nonterminal responses include `Retry-After: 3` by default.

## GET /v1/analyses/{analysis_id}

Authenticated owner with `analysis:read` receives HTTP 200 for an existing resource in any lifecycle state. Response includes API version, fresh request ID, analysis ID, state, created/updated timestamps, and state-appropriate result/readiness/error fields.

- queued/running: no result/error; poll again.
- completed: canonical scored result present; no error.
- not_score_ready: no scored result; canonical readiness/gate reason projection present.
- failed: no successful result; safe machine error metadata.
- timed_out: no successful result; stable timeout metadata.

Missing or foreign resource -> 404 `analysis_not_found`.

## Future n8n retry and polling contract

V1 integration is polling. Callback/webhook support: **NONE**.

- To retry POST after transport/5xx uncertainty, reuse the **same Idempotency-Key and same payload**.
- A 202 means the resource durably exists in PostgreSQL; begin GET polling.
- queued/running are nonterminal; poll again after the documented interval.
- completed is a terminal scored result.
- not_score_ready is a terminal business/data-readiness result, not infrastructure failure.
- failed is terminal execution failure.
- timed_out is terminal deadline outcome.
- Do not blindly retry 401, 403, 409 idempotency conflict, or 422 validation failure without correcting the condition.

## PostgreSQL schema and migrations

Alembic is production schema authority. Initial migration creates:

- `consumers`
- `service_api_keys`
- `analyses`
- `dispatch_outbox`

The migration owns FK, UNIQUE, CHECK, and index definitions and supports downgrade to empty then fresh upgrade. Production does not use SQLAlchemy `create_all()` as schema authority.

## Configuration and secrets

Required deployment configuration includes:

- `SITESCORE_DATABASE_URL` — PostgreSQL only
- `SITESCORE_BROKER_URL` — Redis broker URL
- `SITESCORE_API_KEY_PEPPER` — at least 32 UTF-8 bytes
- analysis deadline and worker soft/hard limits
- `SITESCORE_EVIDENCE_SOURCE_FACTORY` — deployment-owned canonical evidence-source factory when execution is enabled
- provider credentials/manifests/policies/benchmark artifacts required by that evidence source

No real credentials are committed. Missing required production configuration fails closed. Errors persist/return only safe generic messages and never raw Authorization headers, API-key secrets, provider credentials, or tracebacks.

## Explicit limitations / out of scope

FAZ 5.1 does not implement Stripe/payment, payment webhooks, report endpoints, report generation, OpenAI narrative, Jinja2/WeasyPrint/Matplotlib, S3 report storage, n8n workflow JSON, customer email delivery, frontend signup/account UI, production global rate limiting, empirical calibration/validation, V2/Compare/Find, or FAZ 6+ functionality.
