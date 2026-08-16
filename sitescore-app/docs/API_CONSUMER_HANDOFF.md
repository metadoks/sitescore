# SiteScore AI — API Consumer Handoff

## 1. Purpose

This is the durable FAZ 4 consumer-facing handoff for future report, payment, n8n, delivery, and other orchestration layers. It documents only behavior FAZ 4 actually implements or explicitly leaves unresolved. It does not grant scoring authority to downstream consumers and does not authorize future-layer implementation.

## 2. Final FAZ 4 status and durable SHA closure

Pre-lock state:

```text
FAZ_4_FINAL_STATUS: FREEZE_CANDIDATE_PENDING_REVIEW_AND_USER_LOCK
AUDIT_BASE_SHA: a0c2461a7c23618273ab44496011d849584d19fa
FINAL_REVIEWED_CANDIDATE_SHA: PENDING_UNTIL_REVIEWER_READY_TO_LOCK
FINAL_MERGED_FROZEN_MAIN_SHA: PENDING_UNTIL_USER_LOCK

FINAL_SHA_CLOSURE_REF: ops/faz4-final-freeze-closure
FINAL_SHA_CLOSURE_PATH: docs/FAZ4_FINAL_FREEZE_CLOSURE.md
```

A candidate commit cannot reliably self-embed its own final SHA and a pre-merge file cannot know the future merge SHA. Frozen `main` therefore must not be moved after merge merely to write those values. Literal closure is recorded on the dedicated non-runtime ref above.

After successful final LOCK, the closure artifact MUST contain actual literal values:

```text
FAZ_4_STATUS: FROZEN
FINAL_PR: #14
FINAL_REVIEWED_CANDIDATE_SHA: <exact Reviewer-approved PR #14 head>
FINAL_MERGED_FROZEN_MAIN_SHA: <actual PR #14 merge commit == exact main immediately after merge>
API_CONSUMER_HANDOFF_PATH: sitescore-app/docs/API_CONSUMER_HANDOFF.md
FINAL_AUDIT_RECORD_PATH: docs/FAZ4_FINAL_AUDIT_FREEZE_CANDIDATE.md
```

The closure artifact is repository governance evidence only. It is not merged into frozen `main`, does not become application/runtime authority, and may not invent product/API semantics.

### Deterministic LOCK-turn closure procedure

1. Re-fetch Reviewer state, PR #14, and `main`.
2. Require exact `READY_TO_LOCK` / `LOCK_IF_USER_AUTHORIZED`, exact reviewed head/base/current main, open mergeable PR, zero contract/version/reopen gates, and no blockers.
3. Require explicit user `LOCK`.
4. Merge PR #14 with exact-head guard.
5. Re-fetch PR #14, `main`, and merge commit.
6. Require:

```text
PR #14 merged == TRUE
merge_commit_sha == current main
merge parent 1 == pre-lock main/base
merge parent 2 == exact Reviewer-approved head
```

7. Only after those facts exist, create/update `ops/faz4-final-freeze-closure` and write `docs/FAZ4_FINAL_FREEZE_CLOSURE.md` with the literal values above.
8. Do not merge that closure-record commit into frozen `main`.
9. Update normal Implementer coordination record and STOP.
10. On the next normal `Devam`, Reviewer independently verifies PR/main/parents and the closure artifact.
11. Only then Reviewer may declare `FAZ_4_STATUS: FROZEN`.

If closure tooling fails, Implementer records `LOCK_CLOSURE_INCOMPLETE`; Reviewer must not declare FAZ 4 frozen.

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

The package version is not a public network API version.

## 5. Endpoint inventory

```text
NOT_PROVIDED_IN_FAZ4: no network-callable HTTP endpoint or deployed route exists.
```

Implemented transport entry:

```python
handle_application_analysis_transport(application_core_input)
```

This is a framework-neutral, synchronous, in-process Python call. No `/analyze`, `/analyses`, `/v1/...`, GET/POST inventory, host, port, server, or deployment contract is provided.

## 6. HTTP methods

```text
NOT_APPLICABLE_TO_CURRENT_FOUNDATION: no network route exists, so GET/POST/PUT/PATCH/DELETE policy is not frozen.
```

## 7. Request schema summary

```text
RESOLVED: canonical factory-owned ApplicationCoreAnalysisInput
```

External raw JSON request schema:

```text
NOT_PROVIDED_IN_FAZ4
```

Raw JSON, dicts, copied DTOs, fingerprints, hashes, ids, tokens, or caller flags cannot create/impersonate application authority. A future external ingestion layer must separately build canonical upstream authority through authorized application flow.

## 8. Response schema summary

```text
RESOLVED:
ApplicationHttpResponse(
  status_code: int,
  body: dict[str, object],
)
```

Successful body is a deep-owned JSON-safe snapshot of exact `CanonicalAnalysisResult.to_dict()` semantics, including canonical result metadata/components such as:

```text
analysis_fingerprint
model_versions
location
financial
decision
confidence
```

Transport does not recompute scores, fingerprints, model versions, or decision semantics.

## 9. Domain status / error model

Reachable transport outcomes:

```text
SUCCESS
INVALID_APPLICATION_AUTHORITY
ANALYSIS_EXECUTION_FAILED
```

Transport does not invent a second readiness state machine.

```text
NOT_SCORE_READY != successful score
PIPELINE_ERROR != empty successful payload
```

## 10. HTTP-style status mapping

```text
RESOLVED:
200 -> successful canonical analysis projection
400 -> invalid_application_authority
500 -> analysis_execution_failed
```

```text
NOT_PROVIDED_IN_FAZ4: 422 blocked mapping
```

These are framework-neutral response semantics only; they do not imply a deployed HTTP server.

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

No traceback, exception repr, object id, path, secret, API key, or raw upstream response is exposed.

## 12. Request identifier semantics

```text
NOT_PROVIDED_IN_FAZ4: no request ID is generated, accepted, propagated, or exposed.
```

## 13. Analysis identifier semantics

```text
RESOLVED: analysis_fingerprint is preserved unchanged from the exact CanonicalAnalysisResult.
```

It is canonical result metadata only, not a request ID, job ID, polling token, idempotency key, authentication credential, or execution authority.

```text
NOT_PROVIDED_IN_FAZ4: separate analysis lifecycle identifier
```

## 14. Job identifier semantics

```text
NOT_PROVIDED_IN_FAZ4: no job object, job ID, queue identity, or asynchronous work identity exists.
```

## 15. Sync / async behavior

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

```text
UNRESOLVED_IN_FAZ4: future external network execution policy
```

No async submission, queueing, deferred completion, or background worker is implemented.

## 16. Timeout expectations

```text
NOT_PROVIDED_IN_FAZ4: no client/server timeout, deadline, cancellation, or timeout-error contract.
```

## 17. Result retrieval semantics

```text
RESOLVED: result is returned directly by the same synchronous in-process call.
NOT_PROVIDED_IN_FAZ4: no result-resource URL, durable result store, retrieval endpoint, or later fetch API.
```

## 18. Polling semantics

```text
NOT_PROVIDED_IN_FAZ4: no polling endpoint, poll token, interval, status resource, or terminal-state polling protocol.
```

## 19. Callback / webhook semantics

```text
NOT_PROVIDED_IN_FAZ4: no callback URL, webhook registration/event/signature/delivery retry/schema.
```

## 20. Retry expectations

```text
UNRESOLVED_IN_FAZ4: no external retry contract or retry-safety guarantee is frozen.
```

Canonical determinism must not be reinterpreted as request deduplication or retry safety.

## 21. Idempotency

```text
IDEMPOTENCY: NOT PROVIDED IN FAZ 4
```

No idempotency key, duplicate-request store, logical request identity, or duplicate-submission behavior exists.

## 22. Authentication boundary / status

```text
NOT_PROVIDED_IN_FAZ4: no authentication, authorization, account, tenant, API key, OAuth, JWT, session, or caller-identity boundary.
```

Canonical in-process application authority is not authentication and must never be serialized as a trust token.

## 23. Machine-readable API schema / OpenAPI

```text
NOT_APPLICABLE_TO_CURRENT_FOUNDATION: no network framework/route exists from which a truthful runtime OpenAPI contract can be generated.
```

No OpenAPI document is claimed in FAZ 4.

Current version-controlled contract sources:

```text
sitescore-app/src/sitescore_app/transport.py
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/tests/test_http_api_transport_foundation.py
sitescore-app/docs/CHECKPOINT_4_4_HTTP_API_TRANSPORT_FOUNDATION.md
sitescore-app/docs/API_CONSUMER_HANDOFF.md
```

## 24. Backward-compatibility expectations

After FAZ 4 freeze, changes to frozen runtime-observable consumer semantics or application-authority boundaries require explicit reopening/escalation.

Examples:

```text
public exported transport symbols
accepted execution-authority type
success response canonical meaning
stable 200/400/500 mapping
stable machine error codes
raw-authority rejection semantics
synchronous in-process handler semantics
```

Required escalation for a frozen-contract change:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

No compatibility promise exists for nonexistent network route/method/version behavior.

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
- no external retrieval endpoint/result store
- no polling
- no callbacks/webhooks
- no retry guarantee
- no idempotency
- no authentication/authorization
- no OpenAPI/runtime route schema
- no CORS/rate-limit/API-gateway policy
- no deployed n8n-callable network endpoint
```

## 26. Downstream consumer invariants

Once a separately authorized external canonical API actually exists, future n8n orchestration MAY:

```text
- invoke/submit through that canonical API;
- receive/poll canonical status only if actually implemented;
- branch on canonical API state;
- pass completed canonical results downstream.
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

The same restriction applies to future report, payment, email, and delivery consumers.

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

## 28. Scoring/readiness invariants consumers must preserve

```text
missing != zero
unavailable != bad
uncalibrated != calibrated
SCORE_READY != SCORED
NOT_SCORE_READY != successful score
PIPELINE_ERROR != empty successful payload
```

No consumer may neutral-fill, renormalize missing weights, or reinterpret unavailable evidence as successful analysis.

## 29. COMB-005 consumer truth

```text
approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition_method = UNRESOLVED
production road_parking_access_score = unavailable / non-authoritative
```

Controlled test fixtures do not imply empirical approval.

## 30. Final handoff rule

This artifact is the durable FAZ 4 consumer contract handoff. Future phases may extend it only through authorized contract/version evolution. The literal final reviewed/frozen SHAs are durably closed through `ops/faz4-final-freeze-closure:docs/FAZ4_FINAL_FREEZE_CLOSURE.md` after the exact user-authorized LOCK procedure above; the closure record never replaces this consumer contract and is never runtime authority.
