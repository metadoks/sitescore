# SiteScore AI — Implementer → Reviewer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.0
CHECKPOINT_TITLE: External API Ingress + Versioned Contract Foundation

IMPLEMENTER_STATE: READY_FOR_REVIEW
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

BASE_SHA: c34445e59ea37b4aa430ba1ffa1b4021be52c752
CODE_BRANCH: faz5/5-0-external-api-ingress-contract
CODE_HEAD_SHA: e83123e588a14e741962e26416df3950ce15440b
PR: #16
PR_STATE: OPEN
PR_MERGEABLE: TRUE
PR_MERGED: FALSE

REVIEWER_STATE_SEEN: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION_SEEN: IMPLEMENT
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS_REPORTED_BY_IMPLEMENTER: NONE_CODE_SCOPE

VALIDATED_CODE_TREE_SHA: e83123e588a14e741962e26416df3950ce15440b
EXACT_PIN_RUNTIME_VALIDATION: NOT_EXECUTED_IN_CURRENT_RUNTIME
FULL_FROZEN_REGRESSION_REEXECUTION: NOT_EXECUTED_IN_CURRENT_RUNTIME
CI_WORKFLOW_RUNS_FOR_HEAD: NONE
COMBINED_STATUS_CONTEXTS_FOR_HEAD: NONE
```

## 1. Implementation summary

Implemented only Reviewer-authorized FAZ 5 / Checkpoint 5.0 in the new downstream package:

```text
sitescore-api==0.1.0
```

No frozen package was edited.

Implemented network/API foundation:

```text
FastAPI
Pydantic v2
/v1
POST /v1/analyses
GET /v1/analyses/{analysis_id}
```

The runtime surface is intentionally not a durable analysis lifecycle. The default production backend is unavailable and valid submit/retrieve requests fail truthfully with:

```text
503
analysis_lifecycle_unavailable
```

No fake in-memory/process-local persistence and no fabricated completed resource are created.

## 2. Changed files

GitHub compare from exact base to exact head reports 17 changed files, all additions under `sitescore-api/**`:

```text
sitescore-api/README.md
sitescore-api/docs/CHECKPOINT_5_0_EXTERNAL_API_INGRESS.md
sitescore-api/pyproject.toml
sitescore-api/src/sitescore_api/__init__.py
sitescore-api/src/sitescore_api/app.py
sitescore-api/src/sitescore_api/errors.py
sitescore-api/src/sitescore_api/ingress.py
sitescore-api/src/sitescore_api/lifecycle.py
sitescore-api/src/sitescore_api/models.py
sitescore-api/src/sitescore_api/routes.py
sitescore-api/src/sitescore_api/version.py
sitescore-api/tests/conftest.py
sitescore-api/tests/test_architecture.py
sitescore-api/tests/test_ingress.py
sitescore-api/tests/test_models.py
sitescore-api/tests/test_openapi.py
sitescore-api/tests/test_routes.py
```

GitHub compare facts:

```text
base: c34445e59ea37b4aa430ba1ffa1b4021be52c752
head: e83123e588a14e741962e26416df3950ce15440b
merge base: c34445e59ea37b4aa430ba1ffa1b4021be52c752
status: ahead
frozen-package changed files: 0
```

## 3. Public contract

### External request

`AnalysisRequest` is a strict discriminated union keyed by exact frozen sector literals:

```text
coffee
restaurant
gym
beauty
```

Every external request model uses unknown-field rejection.

Location contract:

```text
country_code: required literal US
street: required / trimmed / non-blank
city: optional / trimmed / non-blank when present
state: optional / trimmed / non-blank when present
zip_code: optional / trimmed / non-blank when present

valid shape:
street + zip_code
OR
street + city + state
```

Numeric ingress rejects:

```text
bool-as-number
numeric-string coercion
NaN
+Infinity
-Infinity
float-conversion overflow / non-finite values
range/order violations
```

Sector-specific business field names match the frozen RevenueInput contracts. Common costs are:

```text
monthly_rent
fixed_labor
fixed_overhead
```

## 4. Authority / state flow

Implemented authority boundary:

```text
untrusted external JSON
-> strict Pydantic request validation
-> server-generated request_id UUIDv4
-> server-generated distinct analysis_id UUIDv4 candidate
-> server-owned immutable AnalysisIngressCommand factory
-> exact frozen sector-specific RevenueInput dataclass
-> injected AnalysisLifecycleBackend submit/retrieve port
```

The ingress command is not a Pydantic deserialization target and direct construction without its private factory token fails.

The API does not construct or accept serialized canonical authority objects such as:

```text
ReadinessEvaluation
RealDataPipelineResult
ApplicationScoringInput
ApplicationCategoryAggregationResult
ApplicationCoreAnalysisInput
CanonicalAnalysisResult
CategoryScores
```

Caller-supplied readiness/trust/force/score/fingerprint/provider/benchmark/vintage/source/artifact authority fields are rejected as extras.

The API route layer does not call:

```text
sitescore.analyze.analyze
core engines
category aggregation
pipeline terminal factory
provider clients
```

and contains no scoring/revenue/break-even/decision/confidence/normalization/benchmark formula authority.

## 5. Identity semantics

Every handled request receives a server-generated UUIDv4 `request_id`.

Caller `X-Request-ID` cannot replace server authority.

Responses expose the server request identity through:

```text
X-Request-ID
request_id in SiteScore response envelopes
```

POST also creates a distinct server UUIDv4 `analysis_id` candidate before lifecycle delegation.

These meanings remain separate:

```text
request_id
analysis_id
future task_id
core analysis_fingerprint
```

Default 5.0 lifecycle failure does not return an `analysis_id` and does not claim persistence.

## 6. Error contract

Stable SiteScore error envelope:

```text
api_version
request_id
error.code
error.message
optional safe details
```

Covered concepts:

```text
422 request_validation_failed
503 analysis_lifecycle_unavailable
500 internal_server_error
404 route_not_found
405 method_not_allowed
```

Validation details include safe location/message/type only; raw input values are not echoed. Internal exception details, tracebacks, secret values and internal paths are not returned.

## 7. Runtime / dev dependencies

Exact package metadata pins:

```text
runtime:
fastapi==0.140.0
pydantic==2.13.4
sitescore-core==0.1.0

dev:
httpx==0.28.1
pytest==8.4.2
```

No 5.1+ or later dependencies were added:

```text
PostgreSQL / driver: NO
SQLAlchemy: NO
Alembic: NO
Celery: NO
Redis: NO
OpenAI: NO
Jinja2: NO
WeasyPrint: NO
Matplotlib: NO
S3 SDK: NO
Stripe: NO
```

## 8. Test evidence

### 8.1 sitescore-api

Executed against a local tree whose 17 committed `sitescore-api/**` blob hashes were matched to exact GitHub head `e83123e588a14e741962e26416df3950ce15440b`.

Command equivalent:

```text
PYTHONPATH=src:<exact-frozen-core>/src pytest -q
```

Result:

```text
68 / 68 PASS
```

Coverage includes:

```text
all four valid sectors
exact frozen RevenueInput subtype construction
original legitimate business/cost value projection
extra authority field rejection
nested unknown-field rejection
sector/subtype mismatch
bool/numeric-string/non-finite/overflow rejection
range/order validation
US address cross-field validation
explicit country requirement
server request UUIDv4 generation
caller request-id non-authority
request_id != analysis_id
factory-owned immutable ingress command
default POST 503 truthfulness
default GET 503 truthfulness
no analysis_id on unavailable default lifecycle
injected test backend 202/GET delegation only
backend identity mismatch fail-closed
stable 422/404/405/500 envelopes
raw validation value non-echo
runtime OpenAPI route/schema assertions
forbid-extra OpenAPI assertions
forbidden authority fields absent from request schema
no direct core engine/analyze imports
no route arithmetic
no process-local default lifecycle store
exact dependency pin assertions
no reverse frozen -> sitescore-api imports in locally available repo tree
```

Additional syntax validation:

```text
python -m compileall -q src tests
PASS
```

### 8.2 frozen sitescore-core

The locally supplied frozen `sitescore-core` snapshot was checked against current `main` for the exact ingress-relevant blobs:

```text
revenue_inputs.py blob: e65e762a4cbcb56bd7644985885d057a31a07fcf
sectors.py blob: d655396d5d7db133f2d9fde68d11e6331108aa59
```

Those hashes match GitHub frozen `main`.

Executed:

```text
PYTHONPATH=src pytest -q
```

Result:

```text
86 / 86 PASS
```

## 9. Validation limitations — do not overclaim

The current execution image contains:

```text
FastAPI 0.128.2
Pydantic 2.13.4
HTTPX 0.28.1
pytest 9.0.2
```

Therefore the Reviewer-required dependency pins are committed exactly, but this environment did NOT execute the suite under exact FastAPI `0.140.0` and pytest `8.4.2`.

Also, only the exact frozen core package was locally available for direct re-execution. The historical frozen baseline:

```text
1375 / 1375 PASS
```

is preserved as historical Reviewer/freeze evidence only and is NOT claimed here as a fresh 5.0 full-regression execution.

Fresh full-suite execution for:

```text
sitescore-app
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
```

was not possible in this runtime.

GitHub scope comparison nevertheless proves the 5.0 PR modifies zero frozen-package files.

## 10. CI evidence

For exact code head:

```text
e83123e588a14e741962e26416df3950ce15440b
```

GitHub currently reports:

```text
combined status contexts: none
pull-request workflow runs: none
```

No temporary workflow was introduced because Reviewer explicitly did not require one and workflow scope was not part of 5.0.

## 11. Security / fail-closed audit

```text
external JSON grants internal authority: NO
caller ready/trusted/force flags accepted: NO
caller score/decision/confidence accepted: NO
caller fingerprint as authority accepted: NO
caller coordinates/provider authority accepted: NO
fake in-memory durable resource created: NO
traceback/raw exception returned: NO
caller X-Request-ID trusted: NO
request_id reused as analysis_id: NO
backend identity mismatch accepted: NO
secret hard-coding introduced: NO
```

Authentication is intentionally NOT implemented in 5.0 and production external exposure remains NOT READY.

## 12. Scope audit

Checkpoint documentation explicitly records:

```text
AUTHENTICATION: NOT_IMPLEMENTED_IN_5_0
DURABLE_ANALYSIS_LIFECYCLE: NOT_IMPLEMENTED_IN_5_0
IDEMPOTENCY: NOT_IMPLEMENTED_IN_5_0
PRODUCTION_EXTERNAL_EXPOSURE: NOT_READY
```

Not implemented:

```text
5.1 durable lifecycle
PostgreSQL / SQLAlchemy / Alembic
Celery / Redis
auth / consumer isolation / durable idempotency
report/PDF
OpenAI narrative
S3
Stripe
n8n workflow
email delivery
FAZ 6
```

## 13. Known unresolved validation items

```text
VAL-5.0-001: exact FastAPI 0.140.0 + pytest 8.4.2 execution not available in current runtime
VAL-5.0-002: complete frozen 1375-suite regression not re-executed in current runtime
```

These are validation-environment limitations, not known product-code defects and do not require a contract/design change by the Implementer.

Reviewer must independently decide whether additional validation/hardening is required before READY_TO_LOCK.

## 14. Product validity

> Mathematically validated scoring engine; empirical validation pending.

No empirical validation/calibration completion is claimed.

## 15. Next authority

Implementation is complete for the exact current 5.0 PR head and is submitted for independent review.

```text
NEXT_ACTION_OWNER: REVIEWER
IMPLEMENTER_ACTION: STOP
```

Do not merge. Do not start 5.1. Explicit user `LOCK` remains mandatory only after Reviewer issues exact-head READY_TO_LOCK.
