# SiteScore AI — API Consumer Handoff

## 1. Purpose

This is the durable FAZ 4 consumer-facing handoff for future report, payment, n8n, delivery, and other orchestration layers.

It documents only the API/transport behavior that FAZ 4 actually implements or explicitly leaves unresolved. It does not create a new communication workflow, does not grant scoring authority to downstream consumers, and does not authorize future-layer implementation.

## 2. Final FAZ 4 status / SHA closure

Pre-lock state:

```text
FAZ_4_FINAL_STATUS: FREEZE_CANDIDATE_PENDING_REVIEW_AND_USER_LOCK
AUDIT_BASE_SHA: a0c2461a7c23618273ab44496011d849584d19fa
FINAL_REVIEWED_CANDIDATE_SHA: PENDING_UNTIL_REVIEW
FINAL_MERGED_FROZEN_MAIN_SHA: PENDING_UNTIL_USER_LOCK_AND_REVIEWER_VERIFICATION
```

Durable resolution rules:

```text
FINAL_REVIEWED_CANDIDATE_SHA_RESOLUTION:
  exact head SHA of branch faz4/final-integrated-audit-freeze at Reviewer READY_TO_LOCK

FINAL_MERGED_FROZEN_MAIN_SHA_RESOLUTION:
  merge_commit_sha of the accepted 4-FINAL PR and exact main SHA independently
  verified after user-authorized LOCK
```

The literal future commit/merge SHA is never guessed. A commit cannot reliably self-embed its own resulting SHA, and the merge SHA does not exist before merge.

FAZ 4 is not `FROZEN` until Reviewer independently closes this SHA resolution against actual GitHub state.

## 3. API package / version

```text
RESOLVED: sitescore-app==0.1.0
```

Runtime dependencies:

```text
sitescore-data==0.1.0
sitescore-pipeline==0.1.0
sitescore-core==0.1.0
```

## 4. API contract version

```text
UNRESOLVED_IN_FAZ4: no separate external/network API contract version or versioned route lifecycle is frozen in FAZ 4.
```

`sitescore-app==0.1.0` is the application package version. It must not be reinterpreted as a separately frozen public network API version.

## 5. Endpoint inventory

```text
NOT_PROVIDED_IN_FAZ4: no network-callable HTTP endpoint or deployed route exists.
```

Implemented transport entry:

```python
handle_application_analysis_transport(application_core_input)
```

It is a framework-neutral, in-process Python call.

FAZ 4 does not claim:

```text
/analyze
/analyses
/v1/...
GET /analyses/{id}
POST /analyses
or any other network route
```

## 6. HTTP methods

```text
NOT_APPLICABLE_TO_CURRENT_FOUNDATION: no network route exists, so GET/POST/PUT/PATCH/DELETE method policy is not frozen.
```

## 7. Request schema summary

Implemented in-process request authority:

```text
RESOLVED: canonical factory-owned ApplicationCoreAnalysisInput
```

The transport function accepts only the canonical in-process authority built by FAZ 4.2.

External network/raw JSON request schema:

```text
NOT_PROVIDED_IN_FAZ4
```

Raw JSON, dicts, copied DTOs, fingerprints, hashes, ids, tokens, or caller flags cannot create or impersonate `ApplicationCoreAnalysisInput` authority.

A future external request-ingestion layer must separately build canonical upstream authority through an authorized application pipeline. It may not deserialize a claimed authority object.

## 8. Response schema summary

Implemented response DTO:

```text
RESOLVED:
ApplicationHttpResponse(
  status_code: int,
  body: dict[str, object],
)
```

Successful body is a deep-owned JSON-safe snapshot of exact `CanonicalAnalysisResult.to_dict()` semantics and contains:

```text
analysis_fingerprint
model_versions
location
financial
decision
confidence
```

No score recomputation, rounding, renaming, relabeling, fingerprint regeneration, or model-version regeneration occurs in transport.

## 9. Domain status / error model

Reachable transport outcomes:

```text
SUCCESS
INVALID_APPLICATION_AUTHORITY
ANALYSIS_EXECUTION_FAILED
```

Transport does not invent a second readiness state machine.

Frozen truth remains:

```text
NOT_SCORE_READY != successful score
PIPELINE_ERROR != empty successful payload
```

No caller-provided status string grants application/scoring authority.

## 10. HTTP-style status mapping

```text
RESOLVED:
200 -> successful canonical analysis projection
400 -> invalid_application_authority
500 -> analysis_execution_failed
```

```text
NOT_PROVIDED_IN_FAZ4:
422 blocked mapping
```

These are framework-neutral HTTP-style response semantics. They do not imply a deployed HTTP server.

## 11. Error schema

```text
RESOLVED:
{
  "error": {
    "code": <stable machine-readable string>,
    "message": <stable non-sensitive message>
  }
}
```

Current values:

```text
400:
  code = invalid_application_authority
  message = Invalid application analysis authority.

500:
  code = analysis_execution_failed
  message = Application analysis failed.
```

Transport does not reflect exception repr/traceback, object ids, filesystem paths, provider secrets, API keys, or raw upstream responses.

## 12. Request identifier semantics

```text
NOT_PROVIDED_IN_FAZ4: no request ID is generated, accepted, propagated, or exposed.
```

## 13. Analysis identifier semantics

```text
RESOLVED:
analysis_fingerprint is preserved unchanged from the exact CanonicalAnalysisResult.
```

`analysis_fingerprint` is canonical result metadata only. It is not:

```text
request ID
job ID
polling token
idempotency key
authentication credential
execution authority
```

Separate analysis lifecycle identifier:

```text
NOT_PROVIDED_IN_FAZ4
```

## 14. Job identifier semantics

```text
NOT_PROVIDED_IN_FAZ4: no job object, job ID, queue identity, or asynchronous work identity exists.
```

## 15. Sync / async behavior

Current implemented handler:

```text
RESOLVED: synchronous in-process final-response execution
```

Flow:

```text
canonical ApplicationCoreAnalysisInput
-> handle_application_analysis_transport(...)
-> locked analyze_application_core_input(...)
-> final ApplicationHttpResponse returned in same call
```

Future external network execution policy:

```text
UNRESOLVED_IN_FAZ4
```

FAZ 4 does not implement async submission, queueing, deferred completion, or background workers.

## 16. Timeout expectations

```text
NOT_PROVIDED_IN_FAZ4: no client/server timeout, deadline, cancellation, or timeout-error contract is defined.
```

Consumers must not infer retry safety or timing guarantees from the synchronous in-process call shape.

## 17. Result retrieval semantics

Current handler:

```text
RESOLVED: result is returned directly by the same synchronous in-process call.
```

External retrieval model:

```text
NOT_PROVIDED_IN_FAZ4: no result-resource URL, durable result store, retrieval endpoint, or later fetch API exists.
```

## 18. Polling semantics

```text
NOT_PROVIDED_IN_FAZ4: no polling endpoint, poll token, interval, status resource, or terminal-state polling protocol exists.
```

## 19. Callback / webhook semantics

```text
NOT_PROVIDED_IN_FAZ4: no callback URL, webhook registration, webhook event, signature, delivery retry, or callback schema exists.
```

## 20. Retry expectations

```text
UNRESOLVED_IN_FAZ4: no external retry contract or retry-safety guarantee is frozen.
```

Determinism of canonical analysis for equivalent frozen inputs must not be misrepresented as request deduplication or retry safety.

## 21. Idempotency

```text
IDEMPOTENCY: NOT PROVIDED IN FAZ 4
```

No idempotency key, duplicate-request store, logical request identity, or duplicate-submission behavior exists.

## 22. Authentication boundary / status

```text
NOT_PROVIDED_IN_FAZ4: no authentication, authorization, account, tenant, API key, OAuth, JWT, session, or caller-identity boundary exists.
```

Canonical in-process application authority is not authentication and must not be serialized as a trust token.

## 23. Machine-readable API schema / OpenAPI

```text
NOT_APPLICABLE_TO_CURRENT_FOUNDATION: no network framework/route exists from which a truthful runtime OpenAPI contract can be generated.
```

No OpenAPI document is claimed in FAZ 4.

Current version-controlled contract sources are:

```text
sitescore-app/src/sitescore_app/transport.py
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/tests/test_http_api_transport_foundation.py
sitescore-app/docs/CHECKPOINT_4_4_HTTP_API_TRANSPORT_FOUNDATION.md
sitescore-app/docs/API_CONSUMER_HANDOFF.md
```

A future machine-readable external schema must reflect actual separately authorized runtime routes.

## 24. Backward-compatibility expectations

After FAZ 4 freeze, changes to frozen runtime-observable consumer semantics or authority boundaries require explicit reopening/escalation before modification.

Examples include changing:

```text
public exported transport symbols
accepted execution-authority type
success response canonical meaning
stable 200/400/500 mapping
stable machine error codes
raw-authority rejection semantics
current synchronous in-process handler semantics
```

Required escalation:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

FAZ 4 makes no compatibility promise for a nonexistent network route/method/version lifecycle.

## 25. Known limitations

```text
- no network-callable endpoint
- no external JSON request-ingestion authority bridge
- no public route/method/API-version lifecycle
- no request ID
- no separate analysis lifecycle ID
- no job ID
- no async execution
- no timeout contract
- no external retrieval endpoint/result-store contract
- no polling
- no callbacks/webhooks
- no retry guarantee
- no idempotency
- no authentication/authorization
- no OpenAPI/runtime route schema
- no CORS/rate-limit/API-gateway policy
- no deployed n8n-callable network endpoint
```

These are explicit FAZ 4 boundaries, not implied defaults for later phases.

## 26. Downstream consumer invariants

Once a separately authorized external canonical API actually exists, future n8n orchestration MAY:

```text
- invoke/submit through that canonical API contract;
- receive/poll canonical status only if polling is actually implemented;
- branch workflow based on canonical API state;
- pass completed canonical results to report/payment/delivery systems.
```

Future n8n MUST NOT:

```text
- calculate category scores;
- calculate Location Score;
- infer readiness;
- replace missing values;
- re-run or reimplement frozen core formulas;
- fabricate successful analysis;
- alter canonical result semantics;
- treat JSON/fingerprint/id/hash/flags as scoring/application authority.
```

The same restriction applies to future report, payment, email, and delivery consumers. They consume canonical state/results; they do not become scoring authorities.

## 27. Explicit out-of-scope items

FAZ 4 does not implement:

```text
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
empirical calibration/validation completion
COMB-005 approval
FAZ 5/6 functionality
```

## 28. Scoring/readiness invariants that consumers must preserve

```text
missing != zero
unavailable != bad
uncalibrated != calibrated
SCORE_READY != SCORED
NOT_SCORE_READY != successful score
PIPELINE_ERROR != empty successful payload
```

No consumer may replace missing values, invent neutral scores, renormalize missing weights, or reinterpret unavailable evidence as a successful analysis.

## 29. COMB-005 consumer truth

```text
approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition_method = UNRESOLVED
production road_parking_access_score = unavailable / non-authoritative
```

Consumers must not assume road/parking composite approval from the existence of controlled test fixtures.

## 30. Final handoff rule

This artifact is the durable FAZ 4 consumer contract handoff. Future phases may extend it only through authorized contract/version evolution.

Until an external callable boundary is actually implemented, no consumer may claim that SiteScore exposes a deployed HTTP API merely because the framework-neutral transport DTO/function exists.
