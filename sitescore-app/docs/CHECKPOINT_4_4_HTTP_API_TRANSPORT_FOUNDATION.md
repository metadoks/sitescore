# FAZ 4.4 — HTTP / API Transport Foundation

## Status

Implementation checkpoint for a framework-independent transport adapter over the locked FAZ 4.3 application analysis use-case.

This document also serves as the durable FAZ 4.4 consumer-contract record required by `API-CONSUMER-H001`. It records implemented values, explicit absences, and unresolved external-API policy without inventing behavior.

This document does not grant merge authority. User-only `LOCK` remains required after independent Reviewer acceptance.

## Frozen input authority

The transport entry accepts only the in-process factory-owned authority produced by FAZ 4.2:

```text
ApplicationCoreAnalysisInput
```

It does not construct, deserialize, infer, or promote application authority from JSON, mappings, fingerprints, caller flags, serialized ids, hashes, tokens, or response bodies.

The execution boundary is:

```text
canonical ApplicationCoreAnalysisInput
-> handle_application_analysis_transport(...)
-> locked analyze_application_core_input(...) exactly once on success
-> canonical ApplicationAnalysisResult
-> resolver-backed canonical core_result
-> exact CanonicalAnalysisResult.to_dict() semantics
-> owned transport snapshot
```

The transport layer is an adapter, not a second scoring or analysis orchestrator.

## Public API

```python
ApplicationHttpResponse
handle_application_analysis_transport(application_core_input)
```

`ApplicationHttpResponse` is a frozen framework-neutral DTO with:

```text
status_code: int
body: dict[str, object]
```

It is transport data only and is never recognized as execution authority.

## Success contract

A successful canonical invocation returns:

```text
status_code = 200
```

The body is a deep transport snapshot of the exact canonical core result serialization semantics:

```text
{
  "analysis_fingerprint": ...,
  "model_versions": ...,
  "location": ...,
  "financial": ...,
  "decision": ...,
  "confidence": ...
}
```

The implementation does not recompute, rename, round, relabel, regenerate, or reinterpret core result meaning. The exact core fingerprint is preserved.

The body is JSON-safe because the locked core `CanonicalAnalysisResult.to_dict()` performs canonical enum/tuple/dataclass serialization and the transport takes an owned deep snapshot.

Mutation isolation is intentional:

- mutating the response body does not mutate canonical application/core results;
- mutating canonical result objects after response construction does not retroactively mutate the transport body.

## Error/status contract

Invalid or noncanonical execution authority is mapped to:

```json
{
  "error": {
    "code": "invalid_application_authority",
    "message": "Invalid application analysis authority."
  }
}
```

with HTTP-style status `400`.

Unexpected application execution/projection failure is mapped to:

```json
{
  "error": {
    "code": "analysis_execution_failed",
    "message": "Application analysis failed."
  }
}
```

with HTTP-style status `500`.

No exception `repr`, traceback, filesystem path, provider secret, API key, object id, or raw upstream response is reflected in transport errors. The handler catches `Exception`, not `BaseException`.

No synthetic 422/blocked flow is introduced in this checkpoint because no new canonical external blocked-ingestion boundary is authorized here.

## Authority and anti-forgery invariants

The transport handler:

1. delegates to the locked public FAZ 4.3 `analyze_application_core_input` use-case;
2. does not call core `analyze()` directly;
3. does not call individual revenue/location/financial/decision/confidence engines;
4. does not generate fingerprints or model versions;
5. validates the returned application result through the locked public FAZ 4.3 canonical-result surface before projection;
6. obtains the core result through its resolver-backed property;
7. exposes no raw-authority deserializer.

A JSON success body cannot be passed back as `ApplicationCoreAnalysisInput` or `ApplicationAnalysisResult` authority.

## API consumer contract ledger

The ledger below is authoritative for what FAZ 4.4 actually provides. A field marked absent or unresolved must not be inferred from naming, future-roadmap intent, or downstream consumer needs.

### API package/version

```text
RESOLVED: sitescore-app==0.1.0
```

Runtime package dependencies remain exactly:

```text
sitescore-data==0.1.0
sitescore-pipeline==0.1.0
sitescore-core==0.1.0
```

### API contract version

```text
UNRESOLVED_IN_FAZ4: no separate external/network API contract version or versioned route lifecycle is frozen in FAZ 4.4.
```

The durable contract source for this checkpoint is this document together with the actual exported Python runtime surface and its tests. `sitescore-app` package version remains `0.1.0`; that package version must not be reinterpreted as a separately frozen public HTTP API version.

### Endpoint / route inventory

```text
NOT_PROVIDED_IN_FAZ4: no network-callable HTTP endpoint or deployed route exists in this checkpoint.
```

The only implemented transport entry is the in-process Python function:

```text
handle_application_analysis_transport(application_core_input)
```

Therefore FAZ 4.4 does not claim `/analyze`, `/analyses`, `/v1/...`, or any other public route.

### HTTP methods

```text
NOT_APPLICABLE_TO_CURRENT_FOUNDATION: no network route exists, so GET/POST/PUT/PATCH/DELETE method policy is not frozen.
```

### Request schema

```text
RESOLVED for the implemented in-process boundary:
ApplicationCoreAnalysisInput (canonical, factory-owned, in-process authority only)
```

```text
NOT_PROVIDED_IN_FAZ4 for an external HTTP request body: no raw JSON/dict request schema can create or impersonate ApplicationCoreAnalysisInput authority.
```

Any future network request-ingestion contract must build the canonical upstream authority through separately authorized orchestration rather than deserializing a claimed authority object.

### Response schema

```text
RESOLVED for the implemented in-process transport DTO:
ApplicationHttpResponse(status_code: int, body: dict[str, object])
```

Successful body keys are the exact canonical core serialization semantics:

```text
analysis_fingerprint
model_versions
location
financial
decision
confidence
```

Error body schema is specified below.

### Domain status model

```text
RESOLVED for this handler's reachable transport outcomes:
SUCCESS
INVALID_APPLICATION_AUTHORITY
ANALYSIS_EXECUTION_FAILED
```

The handler does not invent an independent scoring-readiness state machine. `NOT_SCORE_READY` cannot be converted into a fake score or a successful empty result. This 4.4 entry accepts only an already-canonical `ApplicationCoreAnalysisInput`; upstream readiness/blocking and pipeline-error truth remain owned by the earlier canonical application/pipeline boundaries.

No caller-provided status string grants authority or changes canonical state.

### HTTP-style status mapping

```text
RESOLVED:
200 -> successful canonical analysis projection
400 -> invalid_application_authority
500 -> analysis_execution_failed
```

```text
NOT_PROVIDED_IN_FAZ4:
422 blocked mapping is not implemented because no new canonical external blocked-ingestion boundary was authorized.
```

These are framework-neutral HTTP-style response semantics. They do not imply that a deployed HTTP server currently exists.

### Error schema

```text
RESOLVED:
{
  "error": {
    "code": <stable machine-readable string>,
    "message": <stable non-sensitive message>
  }
}
```

Current stable values:

```text
400: invalid_application_authority / "Invalid application analysis authority."
500: analysis_execution_failed / "Application analysis failed."
```

Internal exception text, repr, traceback, object identity, paths, secrets, API keys, and upstream raw responses are not part of the consumer contract.

### Request identifier semantics

```text
NOT_PROVIDED_IN_FAZ4: no request ID is generated, accepted, propagated, or exposed by the current transport foundation.
```

### Analysis identifier semantics

```text
RESOLVED only for canonical result fingerprint semantics:
analysis_fingerprint is returned unchanged from the exact CanonicalAnalysisResult.
```

`analysis_fingerprint` is canonical analysis-result metadata; FAZ 4.4 does not define it as a mutable request ID, job ID, polling token, idempotency key, or authorization credential.

```text
NOT_PROVIDED_IN_FAZ4: no separate analysis lifecycle identifier is introduced.
```

### Job identifier semantics

```text
NOT_PROVIDED_IN_FAZ4: no job object, job ID, queue identity, or asynchronous work identity exists.
```

### Sync vs async execution behavior

```text
RESOLVED for the implemented handler: synchronous in-process execution.
```

The implemented call path is:

```text
canonical input -> analyze_application_core_input(...) -> final ApplicationHttpResponse return
```

```text
UNRESOLVED_IN_FAZ4 for a future external HTTP service: network execution policy is not frozen because no network route/server exists.
```

FAZ 4.4 does not implement asynchronous submission, queueing, deferred completion, or background workers.

### Timeout expectations

```text
NOT_PROVIDED_IN_FAZ4: no transport timeout, server timeout, client timeout, deadline, cancellation, or timeout error contract is defined.
```

Consumers must not infer retry safety or timing guarantees from the synchronous Python call shape.

### Result retrieval model

```text
RESOLVED for the implemented handler: result is returned directly by the same synchronous in-process function call.
```

```text
NOT_PROVIDED_IN_FAZ4 for external retrieval: no result-resource URL, retrieval endpoint, durable result store, or later fetch API exists.
```

### Polling model

```text
NOT_PROVIDED_IN_FAZ4: no polling endpoint, poll token, poll interval, status resource, or terminal-state polling protocol exists.
```

### Callback / webhook model

```text
NOT_PROVIDED_IN_FAZ4: no callback URL, webhook registration, webhook delivery, signature, retry, or event schema exists.
```

### Retry expectations

```text
UNRESOLVED_IN_FAZ4: no external retry contract is frozen.
```

The current in-process handler does not provide a consumer-facing retry guarantee. Consumers must not assume that repeated invocations are deduplicated or side-effect-safe merely because canonical analysis is deterministic for equivalent frozen inputs.

### Idempotency semantics

```text
IDEMPOTENCY: NOT PROVIDED IN FAZ 4
```

No idempotency key, deduplication store, duplicate-request policy, logical request identity, or retry-safe external request contract is implemented.

### Authentication boundary/status

```text
NOT_PROVIDED_IN_FAZ4: no authentication, authorization, account, session, JWT, API key, OAuth, tenant, or caller-identity boundary is implemented.
```

Application authority is an in-process canonical object capability; it is not authentication and must not be exposed as a serialized trust token.

### Machine-readable schema / OpenAPI status and location

```text
NOT_APPLICABLE_TO_CURRENT_FOUNDATION: no framework/network route exists from which a truthful OpenAPI route schema can be generated.
```

No OpenAPI document is claimed or published in FAZ 4.4. Current contract sources are version-controlled:

```text
sitescore-app/src/sitescore_app/transport.py
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/tests/test_http_api_transport_foundation.py
sitescore-app/docs/CHECKPOINT_4_4_HTTP_API_TRANSPORT_FOUNDATION.md
```

A future machine-readable external API schema must reflect actual runtime routes and may only be added when those routes are separately authorized and implemented.

### Known limitations

```text
RESOLVED known limitations:
- no network-callable endpoint
- no external JSON request-ingestion authority bridge
- no public HTTP method/path/version lifecycle
- no request ID
- no separate analysis lifecycle ID
- no job ID or async execution
- no timeout contract
- no retrieval endpoint or result store contract
- no polling
- no callbacks/webhooks
- no retry guarantee
- no idempotency
- no authentication/authorization
- no OpenAPI/runtime route schema
- no CORS/rate-limit/API-gateway policy
- no n8n workflow or deployed n8n-callable network endpoint
```

These are explicit checkpoint boundaries, not implied future defaults.

### Backward-compatibility expectations

```text
RESOLVED for the frozen FAZ 4 contract boundary:
after FAZ 4 freeze, a change that alters frozen runtime-observable consumer semantics or authority boundaries must be escalated as CONTRACT_CHANGE_REQUIRED: 1 before silent modification.
```

Examples include changing:

```text
public exported transport symbols
accepted execution-authority type
success response canonical meaning
stable error/status mapping
stable machine error codes
raw-authority rejection semantics
synchronous current-handler semantics
```

Because FAZ 4.4 provides no external route/method/API-version lifecycle, it makes no compatibility promise for a nonexistent network endpoint. A later external API must define its own authorized versioning and compatibility contract without pretending it was already frozen here.

## Future consumer / n8n invariants

FAZ 4 does not implement n8n. No current n8n-ready network endpoint exists.

If a later authorized external callable API boundary is implemented, future n8n orchestration MAY:

```text
- submit/invoke only through that canonical API contract;
- receive or poll canonical status only if that behavior is actually implemented;
- branch workflow based on canonical API state;
- pass completed canonical results to later report/delivery systems.
```

Future n8n orchestration MUST NOT:

```text
- calculate category scores;
- calculate Location Score;
- infer readiness;
- replace missing values;
- re-run or reimplement core formulas;
- fabricate successful analysis;
- alter canonical result semantics;
- treat transport JSON, fingerprints, ids, hashes, or caller flags as scoring/application authority.
```

The same authority restriction applies to future payment, report, delivery, or orchestration consumers: they may consume canonical API state/results when such external APIs exist, but they do not gain scoring authority.

## Explicit FAZ 4.4 out-of-scope inventory

```text
NOT_PROVIDED_IN_FAZ4:
n8n workflows
Stripe/payment
payment webhooks
report/PDF generation
email delivery
auth/accounts/JWT/session
frontend/UI
queue/background workers
deployment/container orchestration
provider API expansion
empirical calibration
COMB-005 approval
FAZ 5/6 functionality
```

This ledger does not authorize any of those capabilities.

## Runtime/documentation consistency

This hardening adds no new runtime behavior. The consumer ledger records the existing code truth:

```text
transport.py owns the framework-neutral DTO/handler and 200/400/500 mapping;
analysis_use_case.py remains the sole application-side analysis execution authority;
CanonicalAnalysisResult.to_dict() remains the success serialization source;
no route/framework/deserializer/idempotency/auth/polling/webhook code exists.
```

No documentation-only endpoint, OpenAPI schema, async job flow, retry guarantee, idempotency behavior, authentication scheme, or network deployment is asserted.

## Framework and product-policy firewall

FAZ 4.4 intentionally selects no web framework and adds no runtime dependency.

No route/path, hostname, port, OpenAPI lifecycle, CORS policy, rate limit, API gateway, authentication, account/session/JWT, payment, webhook, report/PDF, email, UI, queue, deployment/container, provider expansion, n8n, calibration, or COMB-005 approval is implemented or frozen here.

The package remains:

```text
sitescore-app version = 0.1.0
runtime dependencies:
  sitescore-data==0.1.0
  sitescore-pipeline==0.1.0
  sitescore-core==0.1.0
```

## COMB-005 production truth

Unchanged:

```text
approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition_method = UNRESOLVED
production road_parking_access_score = unavailable / non-authoritative
```

Controlled SCORE_READY fixtures in transport tests only exercise downstream mechanics and do not establish empirical production readiness.

## Persistent change scope

Expected persistent FAZ 4.4 changes are app-local only:

```text
sitescore-app/src/sitescore_app/transport.py
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/tests/test_http_api_transport_foundation.py
sitescore-app/docs/CHECKPOINT_4_4_HTTP_API_TRANSPORT_FOUNDATION.md
```

No frozen upstream production package source is modified.

## Phase boundary

After implementation and regression evidence, FAZ 4.4 must stop at `READY_FOR_REVIEW`.

The next roadmap step after independent Reviewer acceptance and explicit user `LOCK` is **FAZ 4-FINAL integrated audit/freeze**. No FAZ 4.5 is authorized.
