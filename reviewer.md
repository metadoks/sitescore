# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.0
CHECKPOINT_TITLE: External API Ingress + Versioned Contract Foundation

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: c34445e59ea37b4aa430ba1ffa1b4021be52c752
CODE_BRANCH: faz5/5-0-external-api-ingress-contract
REVIEWED_HEAD_SHA: NONE
PR: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN

CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: NONE
```

---

# 1. REVIEWER LIVE-STATE VERIFICATION

Reviewer independently re-fetched GitHub before issuing this contract.

Verified predecessor state:

```text
current main:
c34445e59ea37b4aa430ba1ffa1b4021be52c752

FAZ 4 final reviewed head:
1c6205c0c2fef6c6e17e16179ef459a943fc51d6

FAZ 4 merge PR:
#14 CLOSED / MERGED

merge commit:
c34445e59ea37b4aa430ba1ffa1b4021be52c752

merge parent 1:
a0c2461a7c23618273ab44496011d849584d19fa

merge parent 2:
1c6205c0c2fef6c6e17e16179ef459a943fc51d6

FAZ 4 closure commit:
48efe38ac159e77cdf9a005ce97dd6a629768a6e

FAZ 4 status:
FROZEN
```

The exact Reviewer-approved FAZ 4 head is the second parent of the frozen main merge. No later product commit exists on `main` at issuance time.

The durable FAZ 4 consumer handoff was also re-read at:

```text
sitescore-app/docs/API_CONSUMER_HANDOFF.md
```

It truthfully records that FAZ 4 provides only an in-process canonical application boundary and does **not** provide an external API version, network route, raw JSON authority schema, request ID, analysis lifecycle ID, job ID, polling, idempotency, authentication, or OpenAPI route contract.

This checkpoint begins only after that frozen state.

---

# 2. CHECKPOINT PURPOSE

Implement **FAZ 5.0 only**.

Create the external, versioned API ingress foundation in a new downstream package:

```text
sitescore-api
```

using:

```text
FastAPI
Pydantic v2
URL API versioning under /v1
```

The checkpoint establishes the truthful untrusted-JSON -> validated external request -> server-owned ingress-command boundary and the canonical analysis-resource route surface.

It does **not** claim to complete the durable asynchronous lifecycle. PostgreSQL, SQLAlchemy, Alembic, Celery, Redis, durable idempotency, service-key authentication and consumer isolation are Checkpoint 5.1 concerns.

Therefore 5.0 must not fabricate a functioning durable analysis resource merely to return `202`.

---

# 3. SOURCE-GROUNDED FROZEN AUTHORITY FINDINGS

Reviewer inspected the frozen public surfaces before defining this contract.

## 3.1 Frozen provider path exists, but no all-in-one external executor exists

The frozen provider layer includes a legitimate U.S. address-resolution path:

```text
CensusAddressRequest
-> CensusGeocoderClient.acquire_geocode(...)
-> parsed geocode evidence
-> coordinate geography lookup
-> GeographyRef[] / ResolvedLocation
```

The frozen Census manifest, benchmark/vintage compatibility, persistence policy, provider transport, artifact store, source refs and related evidence are deployment/provider authority. They are **not** external caller inputs.

The U.S. V1 provider baseline covers the 50 states + District of Columbia. Territories are not silently coerced into the U.S. contract.

No single frozen public function was found that accepts an untrusted address/business JSON object and legitimately executes the entire provider -> metric -> benchmark -> pipeline -> application -> core chain.

FAZ 5 may later add downstream orchestration, but must not manufacture a terminal DTO or bypass frozen authority to simulate such an executor.

## 3.2 Frozen pipeline starts from canonical evidence/normalization authority

`sitescore-pipeline` exports canonical factories including:

```text
assemble_normalized_location_features(...)
derive_scoring_readiness(...)
build_real_data_pipeline_result(...)
```

It consumes canonical measurement / normalization / benchmark inputs. A raw address is not itself pipeline authority.

## 3.3 Frozen application chain must remain exact

`sitescore-app` exports the frozen chain:

```text
build_application_pipeline_result(...)
-> evaluate_application_scoring_gate(...)
-> build_application_scoring_input(...)
-> aggregate_application_category_scores(...)
-> build_application_core_analysis_input(...)
-> analyze_application_core_input(...)
```

The exact frozen core `analyze()` is invoked only through the application analysis use case on a factory-owned `ApplicationCoreAnalysisInput`.

FAZ 5.0 must not invoke `sitescore.analyze.analyze` directly and must not import or orchestrate individual scoring engines.

## 3.4 Frozen sector values

The exact frozen external sector semantics are:

```text
coffee
restaurant
gym
beauty
```

Do not invent aliases such as `coffee_shop` as canonical API values in V1.

## 3.5 Frozen business/financial input types

The existing frozen core requires sector-specific revenue inputs plus operating costs.

Exact revenue-input fields are:

```text
COFFEE
- target_population
- target_rate
- capture_rate_conservative
- capture_rate_base
- capture_rate_optimistic
- visit_frequency_per_month
- average_ticket

RESTAURANT
- seats
- turnover_per_day
- utilization_conservative
- utilization_base
- utilization_optimistic
- average_ticket
- operating_days_per_month

GYM
- target_population
- penetration_rate_conservative
- penetration_rate_base
- penetration_rate_optimistic
- usable_area
- members_per_area_unit
- monthly_membership_fee

BEAUTY
- stations
- operating_hours_per_week
- average_service_duration_hours
- utilization_conservative
- utilization_base
- utilization_optimistic
- average_ticket
```

Common operating-cost inputs are:

```text
monthly_rent
fixed_labor
fixed_overhead
```

The API may accept these **business/financial assumptions** as user input, but it must not accept caller-calculated canonical outputs.

The server-side ingress factory must construct the exact frozen sector-specific core `RevenueInput` type so the frozen type/range invariants remain authoritative. Do not duplicate revenue or financial formulas in `sitescore-api`.

## 3.6 Fields that are NOT caller authority

Although the frozen `AnalysisInput` eventually contains additional fields such as geographic/data-quality metadata, the external caller must not directly assert them as canonical truth.

Do not expose caller-authoritative forms of:

```text
CategoryScores
ApplicationScoringInput
ApplicationCategoryAggregationResult
ApplicationCoreAnalysisInput
CanonicalAnalysisResult
ReadinessEvaluation
RealDataPipelineResult
NormalizedLocationFeatures
location_score
category scores
financial outputs
break-even outputs
decision
confidence
score_ready
trusted
force
analysis_fingerprint
readiness_fingerprint
geographic_level
data_age_years
data_coverage
input_qualities
provider manifests
provider benchmark/vintage compatibility
provider persistence policy
resolved coordinates as trusted geocode result
GeographyRef / source_refs
artifact refs / content hashes as trust tokens
```

If equivalent names are supplied as unexpected JSON fields, the request must be rejected by strict schema validation rather than silently ignored.

---

# 4. PACKAGE / DEPENDENCY CONTRACT

Create:

```text
sitescore-api/
```

Package metadata:

```text
name = sitescore-api
version = 0.1.0
requires-python = >=3.11
```

New direct runtime dependencies for this checkpoint must be pinned exactly:

```text
fastapi==0.140.0
pydantic==2.13.4
sitescore-core==0.1.0
```

`sitescore-core` is permitted here only for exact frozen public types required at ingress, such as `Sector` and sector-specific `RevenueInput` construction. It does **not** authorize a direct call to core `analyze()` or individual core engines.

Test dependencies must be reproducible and compatible with the repository's established pytest 8.x baseline:

```text
httpx==0.28.1
pytest==8.4.2
```

Do not introduce in 5.0:

```text
PostgreSQL driver
SQLAlchemy
Alembic
Celery
Redis
OpenAI SDK
Jinja2
WeasyPrint
Matplotlib
S3 SDK
Stripe SDK
n8n-specific dependency
```

Frozen upstream packages must not gain a dependency on `sitescore-api`.

No dependency cycle is allowed.

---

# 5. ALLOWED PRODUCT SCOPE

Product PR changes are limited to the new package:

```text
sitescore-api/**
```

This includes its:

```text
pyproject.toml
README.md
src/sitescore_api/**
tests/**
docs/**
```

Do **not** modify frozen FAZ 3 or FAZ 4 product source or metadata in:

```text
sitescore-core/**
sitescore-data/**
sitescore-providers/**
sitescore-spatial/**
sitescore-metrics/**
sitescore-benchmarks/**
sitescore-pipeline/**
sitescore-app/**
```

If correct implementation genuinely requires changing frozen runtime-observable semantics:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

and STOP for escalation instead of changing them.

If one of the selected architecture/dependency decisions proves technically incompatible with actual source/runtime evidence:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

and STOP for escalation rather than silently substituting another stack.

---

# 6. REQUIRED MODULE RESPONSIBILITIES

Exact private filenames may vary, but the package must separate these responsibilities clearly.

A reasonable target structure is:

```text
sitescore-api/
├── pyproject.toml
├── README.md
├── docs/
│   └── CHECKPOINT_5_0_EXTERNAL_API_INGRESS.md
├── src/sitescore_api/
│   ├── __init__.py
│   ├── version.py
│   ├── models.py
│   ├── errors.py
│   ├── ingress.py
│   ├── lifecycle.py
│   ├── routes.py
│   └── app.py
└── tests/
    └── ...
```

The implementation may refine private names, but must preserve the following separation:

```text
Pydantic external models
!= server-owned ingress command
!= lifecycle/submission port
!= FastAPI route glue
!= frozen scoring/application authority
```

Route functions must remain thin.

---

# 7. EXTERNAL REQUEST CONTRACT

## 7.1 Strict Pydantic V2 models

All external request models must use strict unknown-field rejection equivalent to:

```text
extra = forbid
```

Whitespace-only required strings must not be accepted.

Finite numeric validation is mandatory. `NaN`, `Infinity`, booleans-as-numbers and other coercions that would undermine the frozen numeric contract must be rejected.

Do not allow a valid JSON shape to impersonate internal application authority.

## 7.2 Location input

V1 is explicitly U.S.-address based for this checkpoint.

Expose a typed address model equivalent in semantics to:

```text
country_code = "US" only
street: required non-empty trimmed string
city: optional non-empty trimmed string
state: optional non-empty trimmed string
zip_code: optional non-empty trimmed string
```

Cross-field rule must mirror the frozen Census address requirement:

```text
street + ZIP
OR
street + city + state
```

Caller must not supply:

```text
CensusGeographyManifest
benchmark
vintage
layer IDs
provider policy
provider URL
artifact store
retrieved_at authority
resolved latitude/longitude as trusted provider result
source refs
```

Those remain server/deployment concerns.

## 7.3 Sector-discriminated request

Prefer one externally visible discriminated union using the exact top-level `sector` field:

```text
coffee
restaurant
gym
beauty
```

Each sector variant must pair only with its exact matching `business_inputs` model.

A coffee request carrying restaurant fields, or a gym request carrying beauty fields, must fail validation rather than be coerced.

## 7.4 Business input validation

Mirror the frozen core validation at the API boundary where it improves client error quality, but the server-owned ingress factory must still instantiate the exact frozen core `RevenueInput` object before accepting the internal command.

Do not implement business formulas in the Pydantic models.

Required invariant examples include:

```text
rates/utilizations/penetration fractions in [0, 1]
conservative <= base <= optimistic
positive ticket / fee / area / station / seat requirements where frozen core requires them
nonnegative population / turnover / frequency where frozen core permits zero
positive operating-day counts where frozen core requires them
```

## 7.5 Costs

Expose:

```text
monthly_rent
fixed_labor
fixed_overhead
```

Each must be finite and nonnegative, matching the frozen core contract.

Do not calculate cost ratios or financial outputs in the API layer.

---

# 8. SERVER-OWNED INGRESS COMMAND

Create a server-owned, immutable ingress representation that cannot be constructed by Pydantic deserialization alone.

It may contain only legitimate caller intent after validation, plus server-generated operational identity, for example:

```text
server request_id
candidate server analysis_id for submission
address intent
exact frozen Sector
exact frozen RevenueInput object
operating-cost inputs
```

The exact private design may differ, but these rules are mandatory:

```text
external Pydantic model != authority-bearing application DTO
construction is through a server-side factory
factory constructs exact frozen RevenueInput type
factory revalidates sector/business-input coherence
factory does not create CategoryScores
factory does not create ReadinessEvaluation
factory does not manufacture RealDataPipelineResult
factory does not create ApplicationScoringInput
factory does not create ApplicationCoreAnalysisInput
factory does not calculate score/financial/decision/confidence
```

This ingress command is **request intent**, not scoring authority.

---

# 9. REQUEST IDENTITY FOUNDATION

Every `/v1` request handled by the API must receive a **server-generated UUIDv4 request ID**.

Rules:

```text
request_id is generated by the server
request_id is distinct from analysis_id
request_id is distinct from Celery task_id
request_id is distinct from analysis_fingerprint
caller-supplied X-Request-ID must not become authority
```

Expose the server request ID consistently:

```text
response body where a SiteScore response envelope exists
and
X-Request-ID response header
```

Validation failures must also carry the server request ID.

Do not use the core `analysis_fingerprint` as request identity.

---

# 10. VERSIONED FASTAPI ROUTE FOUNDATION

Create a FastAPI application/factory with `/v1` routing.

Required resources:

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
```

OpenAPI must be generated from the actual runtime Pydantic route models. No handwritten OpenAPI document may contradict runtime behavior.

Do not expose internal frozen DTO schemas as public request schemas.

## 10.1 POST /v1/analyses

The route must:

```text
1. accept only the strict typed external request
2. obtain the server-generated request_id
3. generate a distinct server UUIDv4 analysis_id candidate
4. build the server-owned ingress command
5. delegate to a lifecycle/submission port
6. never execute scoring math in the route
```

The route must not directly call:

```text
sitescore.analyze.analyze
core engines
category aggregation
pipeline terminal factory
provider network clients
```

Provider-to-analysis execution orchestration is not to be invented inside the HTTP route.

## 10.2 GET /v1/analyses/{analysis_id}

Accept only a valid UUID analysis identifier and delegate to the lifecycle/read port.

Do not return a fabricated `not_found`, `completed`, `queued` or other lifecycle state without authoritative lifecycle storage.

---

# 11. 5.0 LIFECYCLE PORT — TRUTHFUL DEFERRED IMPLEMENTATION

Define an injected interface/protocol for the analysis resource backend so that 5.1 can attach PostgreSQL/Celery-backed behavior without rewriting route semantics.

The interface should separate at minimum:

```text
submit analysis intent
retrieve analysis resource by analysis_id
```

A test fake is permitted only to verify route/contract behavior. It must not be shipped or described as durable product truth.

The production/default 5.0 backend has no durable store and therefore must behave truthfully:

```text
POST valid request
-> 503 analysis_lifecycle_unavailable
-> no successful analysis resource claim
-> no returned analysis_id as if persisted

GET valid analysis_id
-> 503 analysis_lifecycle_unavailable
-> no fabricated lifecycle state
```

Do **not** implement an in-memory dictionary, process-local queue, filesystem pseudo-database, or fake Celery task table to claim analysis persistence.

A `202 Accepted` response schema may be structurally prepared and exercised against an explicitly injected **test-only** accepted backend, but production/default 5.0 execution must not return 202 until a backend has actually accepted durable resource creation. The durable acceptance guarantee is completed in 5.1.

A future `202` representation must keep these meanings distinct:

```text
request_id = this HTTP operation
analysis_id = durable external analysis resource
```

Do not expose a Celery task ID in the public API contract.

---

# 12. ERROR CONTRACT

All `/v1` API errors must use one stable machine-readable envelope.

Required semantic fields:

```text
api_version
request_id
error.code
error.message
```

Validation errors may additionally contain structured safe details.

Required stable error concepts for 5.0 include at least:

```text
request_validation_failed
analysis_lifecycle_unavailable
internal_server_error
```

Do not expose Python tracebacks, exception reprs, provider secrets, request credentials, internal file paths or raw internal authority objects.

For Pydantic/FastAPI validation failures, normalize the framework error into the SiteScore error envelope rather than exposing a second incompatible error shape.

`422` is appropriate for request schema/semantic validation failures.

`503` is required for the deliberately unavailable 5.0 lifecycle backend.

Unexpected internal failures must not be mislabeled as successful or `not_score_ready` analysis outcomes.

---

# 13. OPENAPI CONTRACT

OpenAPI tests must prove runtime truth.

At minimum verify:

```text
/v1/analyses exists with POST
/v1/analyses/{analysis_id} exists with GET
POST request is the four-sector discriminated union
all external request models forbid unknown fields
sector literals are exactly coffee/restaurant/gym/beauty
internal authority fields are absent from public request schema
stable error model is declared
503 lifecycle-unavailable response is declared
no report/payment/n8n endpoints exist
```

If a 202 schema is declared for forward compatibility, documentation must state that the default 5.0 backend cannot produce it and that durable acceptance semantics are completed in 5.1.

---

# 14. AUTHENTICATION / IDEMPOTENCY / ASYNC SCOPE BOUNDARY

The following are deliberately **not implemented in 5.0**:

```text
Bearer service API key authentication
consumer identity
scopes
consumer isolation
Idempotency-Key semantics
canonical request hash
durable uniqueness
PostgreSQL analysis record
Celery worker execution
Redis broker transport
retry contract
polling lifecycle states
```

Do not implement partial/in-memory substitutes.

The 5.0 documentation must state prominently:

```text
AUTHENTICATION: NOT_IMPLEMENTED_IN_5_0
DURABLE_ANALYSIS_LIFECYCLE: NOT_IMPLEMENTED_IN_5_0
IDEMPOTENCY: NOT_IMPLEMENTED_IN_5_0
PRODUCTION_EXTERNAL_EXPOSURE: NOT_READY
```

This is not a defect in 5.0; it is the explicit checkpoint boundary. 5.1 will close it.

Because authentication/consumer ownership is absent, the 5.0 default backend must not expose stored analysis data.

---

# 15. SECURITY / AUTHORITY ADVERSARIAL TESTS

Tests must cover at least:

1. Unknown root field rejected.
2. Unknown nested field rejected.
3. `category_scores` injection rejected.
4. `location_score` injection rejected.
5. `decision` injection rejected.
6. `confidence` injection rejected.
7. `analysis_fingerprint` injection rejected.
8. `readiness_fingerprint` injection rejected.
9. `score_ready=true` rejected.
10. `trusted=true` rejected.
11. `force=true` rejected.
12. provider manifest/benchmark/vintage injection rejected.
13. source/artifact reference injection rejected.
14. caller geographic/data-quality authority fields rejected.
15. sector/business subtype mismatch rejected.
16. NaN / Infinity rejected.
17. bool supplied where numeric value is expected rejected.
18. invalid rate ordering rejected.
19. negative common costs rejected.
20. invalid U.S. address shape rejected.
21. non-US country rejected.
22. malformed analysis UUID path rejected.
23. caller-provided request ID cannot replace server UUIDv4 request_id.
24. request validation failure returns stable SiteScore error envelope.
25. default POST cannot return 202 or a persisted analysis claim.
26. default GET cannot fabricate a resource or lifecycle state.
27. route implementation does not call core `analyze()` or individual core engines.
28. no process-local dictionary/cache is used as claimed lifecycle truth.

---

# 16. POSITIVE CONTRACT TESTS

Provide valid request examples/tests for all four sectors.

Each must prove:

```text
Pydantic request validates
correct exact frozen Sector is selected
correct exact frozen RevenueInput type is constructed
all original user business values are preserved without calculation
common costs are preserved
server request_id is UUIDv4
analysis_id candidate is a distinct UUIDv4
external Pydantic object itself is not treated as application scoring authority
```

For a deliberately injected test lifecycle backend, it is permissible to prove the future-facing route envelope/delegation contract, provided the tests and docs make clear that this backend is non-production and non-durable.

---

# 17. ARCHITECTURE TESTS

Add static/structural tests that fail if:

```text
sitescore-api imports sitescore.engines.*
sitescore-api directly imports sitescore.analyze for execution
route modules contain score/financial/decision formula logic
frozen packages import sitescore_api
new FAZ 5.1+ infrastructure dependencies appear in sitescore-api 5.0
```

If `sitescore-core` is imported, limit production imports to exact public schema/config types needed for request translation; there must be no direct core execution path.

The frozen upstream package files must be byte-for-byte unchanged by the product PR.

---

# 18. DOCUMENTATION ARTIFACT

Create:

```text
sitescore-api/docs/CHECKPOINT_5_0_EXTERNAL_API_INGRESS.md
```

It must record factual 5.0 behavior, including:

```text
package/version
API version = v1
route inventory
request schema by sector
U.S.-only address limitation in this checkpoint
server-owned request_id semantics
analysis_id intended semantics
forbidden caller-authority fields
error envelope + status semantics
default lifecycle-unavailable behavior
no durable resource creation in 5.0
no authentication in 5.0
no idempotency in 5.0
no worker/queue/database in 5.0
no report/PDF/n8n/payment implementation
frozen FAZ 4 downstream authority boundary
product validity statement:
Mathematically validated scoring engine; empirical validation pending.
```

Do not describe planned 5.1 behavior as already implemented.

---

# 19. TEST / VALIDATION REQUIREMENTS

Implementer must run the new package tests and provide exact commands/results in `implementer.md`.

At minimum:

```text
sitescore-api test suite: PASS
```

Then verify the frozen baseline has not regressed by running all existing package test suites or the repository's established equivalent full-regression command.

The previous frozen recorded baseline is:

```text
sitescore-app:         19
sitescore-pipeline:    53
sitescore-benchmarks: 191
sitescore-metrics:     67
sitescore-spatial:    180
sitescore-providers:  418
sitescore-data:       361
sitescore-core:        86
TOTAL:               1375
```

Do not treat those historical counts as new execution evidence. Report the actual results from the 5.0 branch.

Frozen main currently has no `.github/workflows` directory. A new GitHub Actions workflow is **not required** for this checkpoint and is outside the allowed product-file scope above. Reviewer will inspect available PR/Actions status during review. Local reproducible test evidence is mandatory.

---

# 20. FORBIDDEN CHANGES / SCOPE LEAKAGE

Do not implement or authorize in 5.0:

```text
PostgreSQL durable lifecycle
SQLAlchemy models
Alembic migrations
Celery worker
Redis broker
Idempotency-Key guarantee
service API keys / scopes
cross-consumer authorization
report package
report endpoints
OpenAI narrative
Jinja2 templates
WeasyPrint
Matplotlib charts
S3 object storage
Stripe
payment webhooks
n8n workflow
email delivery
production rate limiting
empirical calibration/validation
Compare / Find
V2 API
```

Do not create a hidden 5.1 inside 5.0.

---

# 21. IMPLEMENTATION / GIT PROTOCOL

Use exactly one product branch:

```text
faz5/5-0-external-api-ingress-contract
```

Base it on exactly:

```text
main
c34445e59ea37b4aa430ba1ffa1b4021be52c752
```

Use one PR for Checkpoint 5.0.

Any Reviewer hardening remains on the same branch and same PR.

Do not merge.

Do not self-LOCK.

After implementation:

1. push the branch,
2. open the PR against `main`,
3. update `implementer.md` on `ops/reviewer-implementer-handoff`,
4. record exact base SHA, exact PR head SHA, PR number, changed files, dependency pins and test evidence,
5. set Implementer state to `READY_FOR_REVIEW`,
6. STOP.

---

# 22. ACCEPTANCE CRITERIA

Checkpoint 5.0 can become `READY_TO_LOCK` only if Reviewer independently verifies all of the following on one exact PR head:

```text
[ ] branch is based on exact expected main SHA
[ ] only allowed product scope changed
[ ] frozen FAZ 3/4 source remains unchanged
[ ] sitescore-api package is reproducible and pinned
[ ] FastAPI /v1 runtime routes exist
[ ] POST /v1/analyses exists
[ ] GET /v1/analyses/{analysis_id} exists
[ ] external request is strict Pydantic typed schema
[ ] sector vocabulary exactly matches frozen core
[ ] all four sector request variants are covered
[ ] exact frozen RevenueInput types are constructed server-side
[ ] external JSON cannot supply scoring/readiness/result authority
[ ] external JSON cannot supply provider/deployment authority
[ ] request_id is server UUIDv4 and separate from analysis_id
[ ] analysis_id is server UUIDv4 identity foundation, not fingerprint/task ID
[ ] no core analyze or engine execution occurs in route layer
[ ] no fake terminal/pipeline/application DTO is manufactured
[ ] no in-memory durable-lifecycle claim exists
[ ] default 5.0 POST/GET truthfully report lifecycle unavailability
[ ] stable machine-readable error envelope is used
[ ] validation errors use the same SiteScore envelope
[ ] OpenAPI is generated from runtime models and matches routes
[ ] no authentication/idempotency/DB/queue is falsely claimed implemented
[ ] U.S.-only location scope is explicit
[ ] docs match runtime behavior
[ ] new package tests pass
[ ] frozen regression passes
[ ] no FAZ 5.1 / report / FAZ 6 leakage
[ ] CONTRACT_CHANGE_REQUIRED = 0
[ ] DESIGN_DECISION_REVIEW_REQUIRED = 0
```

Reviewer acceptance will be exact-SHA-specific.

---

# 23. STOP CONDITION

Implement **only Checkpoint 5.0** under this contract.

When implementation and evidence are complete:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

Then STOP and wait for the user's next Reviewer `Devam` cycle.

Do not start Checkpoint 5.1.
Do not merge.
Do not LOCK.
