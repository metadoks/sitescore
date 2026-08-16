# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.4
CHECKPOINT_TITLE: HTTP / API Transport Foundation

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: b2df2c5f7f447f193544f15b285ec5af3f8bdc6e
CODE_BRANCH: faz4/4.4-http-api-transport-foundation
REVIEWED_HEAD_SHA: NONE
PR: NONE

CONTRACT_CHANGE_REQUIRED: 0
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
DEPENDENCY_CHANGE_AUTHORIZED: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_0_STATUS: HISTORICALLY_LOCKED_MERGED
AUTHORITY_CORRECTIVE_REOPEN_STATUS: LOCKED_MERGED
FAZ_4_1_IMPLEMENTATION_STATUS: LOCKED_MERGED
FAZ_4_2_IMPLEMENTATION_STATUS: LOCKED_MERGED
FAZ_4_3_IMPLEMENTATION_STATUS: LOCKED_MERGED
FAZ_4_4_IMPLEMENTATION_STATUS: IMPLEMENTATION_REQUESTED

BLOCKERS: NONE
```

---

# 1. TRANSITION AUTHORITY / EXACT BASE

The user requested continuation after FAZ 4.3 was independently verified LOCKED / MERGED.

Reviewer independently verified current `main` exactly:

```text
b2df2c5f7f447f193544f15b285ec5af3f8bdc6e
```

FAZ 4.4 is authorized only from that base.

Historical truth remains:

```text
FAZ 3: FROZEN
FAZ 4.0: HISTORICALLY LOCKED / MERGED
Authority corrective reopen: RESOLVED / LOCKED / MERGED
FAZ 4.1: LOCKED / MERGED
FAZ 4.2: LOCKED / MERGED
FAZ 4.3: LOCKED / MERGED
FAZ 4.4: NOW AUTHORIZED
```

Do not reopen or rewrite earlier checkpoints.

---

# 2. CHECKPOINT OBJECTIVE

Implement a framework-independent HTTP/API transport foundation around the locked FAZ 4.3 application use-case.

Canonical boundary:

```text
canonical ApplicationCoreAnalysisInput
-> transport handler delegates exactly once to locked analyze_application_core_input(...)
-> canonical ApplicationAnalysisResult
-> deterministic JSON-safe transport success projection
```

The transport layer may also expose explicit framework-neutral error/status envelopes for transport callers.

This checkpoint MUST NOT create or accept a raw JSON imitation of application execution authority.

---

# 3. CRITICAL AUTHORITY RULE — HTTP PAYLOAD IS NOT APPLICATION AUTHORITY

The current canonical execution authority chain is in-process and factory-owned:

```text
ApplicationPipelineResult
-> ApplicationScoringInput
-> ApplicationCategoryAggregationResult
-> ApplicationCoreAnalysisInput
-> ApplicationAnalysisResult
```

Therefore FAZ 4.4 MUST NOT accept caller-provided JSON/dict payloads that directly claim to be any of these authorities.

Explicitly forbidden as an authority shortcut:

```text
raw dict -> AnalysisInput
raw dict -> CategoryScores
raw dict -> ApplicationCoreAnalysisInput
raw dict -> ApplicationAnalysisResult
caller-provided analysis_fingerprint as proof
trusted=true
ready=true
force=true
skip_validation=true
serialized object ids/tokens/hashes as authority
```

Do not reconstruct locked authority objects from transport fields.

A future external request-ingestion/product workflow may assemble the upstream canonical authority through separately authorized application/provider orchestration. That is not invented in 4.4.

---

# 4. FRAMEWORK-INDEPENDENT TRANSPORT HANDLER

Recommended public shape:

```text
handle_application_analysis_transport(
    application_core_input: ApplicationCoreAnalysisInput,
) -> ApplicationHttpResponse
```

Equivalent naming is acceptable.

Requirements:

1. only canonical `ApplicationCoreAnalysisInput` is accepted;
2. delegate to the locked public FAZ 4.3 use-case `analyze_application_core_input` exactly once on success;
3. do not call frozen core `analyze()` directly from transport;
4. do not call individual core engines;
5. do not duplicate 4.3 authority validation;
6. success response must be derived only from the canonical `ApplicationAnalysisResult` produced by 4.3;
7. no detached/raw `CanonicalAnalysisResult` may be accepted by the public transport entry as execution authority.

The transport handler is an application adapter, not a second analysis orchestrator.

---

# 5. SUCCESS RESPONSE CONTRACT

Introduce a framework-neutral transport response type, recommended:

```text
ApplicationHttpResponse
```

A simple frozen transport DTO is acceptable because it is not execution authority.

Success semantics should be explicit and stable, for example:

```text
status_code: 200
body: JSON-safe mapping
```

The success body MUST preserve the exact canonical core result meaning and MUST be generated from the locked canonical result after authority validation.

Recommended success body:

```text
{
  "analysis_fingerprint": <exact core fingerprint>,
  "model_versions": ...,
  "location": ...,
  "financial": ...,
  "decision": ...,
  "confidence": ...
}
```

Using exact `CanonicalAnalysisResult.to_dict()` output after canonical 4.3 authority validation is preferred unless a strictly equivalent deterministic projection is demonstrated.

Do NOT:

```text
recompute scores
round presentation values
rename business semantics arbitrarily
invent alternate decision labels
replace confidence values
regenerate fingerprint
regenerate model versions
```

Presentation/report formatting is out of scope.

---

# 6. RESPONSE BODY IS TRANSPORT DATA, NOT AUTHORITY

A serialized JSON/dict response is not reusable as application execution authority.

Tests must establish:

```text
JSON success body != ApplicationAnalysisResult authority
JSON success body != ApplicationCoreAnalysisInput authority
```

Do not provide deserialization APIs that grant execution authority from the response body.

---

# 7. ERROR / STATUS FOUNDATION

FAZ 4.4 may define a small framework-neutral error envelope and explicit status mapping, but it must remain conservative and must not expose internal stack traces or implementation details.

Recommended transport error shape:

```text
{
  "error": {
    "code": <stable machine-readable code>,
    "message": <non-sensitive stable message>
  }
}
```

At minimum distinguish:

```text
invalid_application_authority -> 400
analysis_execution_failed     -> 500
```

If the implementation can consume an existing `ApplicationScoringBlocked` surface through an explicitly canonical boundary without inventing upstream request orchestration, a stable 422-style blocked outcome may be added. Otherwise do not fabricate a blocked flow in 4.4.

Do not expose exception repr, traceback, internal object ids, filesystem paths, provider secrets, API keys, or raw upstream responses.

Unknown/unexpected application exceptions must fail closed to a generic server-error response.

---

# 8. EXCEPTION DISCIPLINE

The transport layer must not silently convert programming/integrity violations into successful responses.

Recommended behavior:

```text
TypeError / ValueError caused by invalid noncanonical transport input
-> deterministic 400 error envelope

unexpected exception from application analysis execution
-> deterministic generic 500 error envelope
```

Tests should verify no exception message containing adversarial/sensitive content is reflected verbatim into the transport response.

Do not catch `BaseException`, `KeyboardInterrupt`, or `SystemExit`.

---

# 9. NO WEB FRAMEWORK DEPENDENCY IN 4.4

No framework selection has been frozen in the repository.

Therefore this checkpoint MUST NOT add a runtime dependency on:

```text
FastAPI
Starlette
Flask
Django
Pydantic
Uvicorn
Gunicorn
```

unless Reviewer first reports:

```text
DEPENDENCY_CHANGE_REQUIRED: 1
```

and receives new user authority.

Current `sitescore-app` dependencies remain exactly:

```text
sitescore-data==0.1.0
sitescore-pipeline==0.1.0
sitescore-core==0.1.0
```

Package version remains `0.1.0`.

The output of 4.4 should be directly usable by a later thin framework adapter without changing application/core authority semantics.

---

# 10. NO ROUTE/PATH CONTRACT INVENTION

Do not freeze a public URL path such as `/v1/analyze`, hostname, port, API gateway scheme, CORS policy, rate limit, OpenAPI document, deployment topology, or API-version lifecycle in this checkpoint unless an existing frozen contract already specifies it.

The repository currently provides no such frozen route/framework contract.

4.4 is the transport **foundation**, not deployment/public API product policy.

---

# 11. TRANSPORT DETERMINISM / JSON SAFETY

For a canonical analysis result, transport projection must be deterministic and JSON-safe.

Tests must prove at minimum:

```text
same canonical core result semantics -> same transport body semantics
all success body keys/values are JSON-serializable
Enums are serialized to transport-safe primitive values
Tuples/nested dataclasses are serialized consistently with core canonical serialization
analysis_fingerprint is exact and unchanged
```

Use `json.dumps(...)` in tests to prove the produced success body is JSON-safe.

Do not depend on `repr()` for public response semantics.

---

# 12. FAZ 4.3 AUTHORITY MUST REMAIN INTACT

Transport must consume the locked public 4.3 use-case rather than reaching into private `_resolve_trusted_application_analysis_result` unless a read-only response projection requires canonical validation and no public equivalent suffices.

Preferred pattern:

```text
analysis_result = analyze_application_core_input(application_core_input)
require_canonical_application_analysis_result(analysis_result)
core_result = analysis_result.core_result
body = core_result.to_dict()
```

The public `core_result` property is resolver-backed and therefore revalidates the entire 4.3 authority chain.

Do not weaken or bypass 4.3 mutation protection.

---

# 13. MUTATION / SNAPSHOT SEMANTICS

The transport body should be an owned snapshot of the canonical result at response-construction time.

After success response construction:

- mutating the response body must not mutate canonical application/core result objects;
- mutating canonical result objects after response construction must not retroactively mutate the already-built transport body.

Use deep transport serialization rather than exposing live nested dataclass/dict references.

The transport DTO itself need not become another execution-authority registry.

---

# 14. REQUIRED ADVERSARIAL TEST MATRIX

At minimum prove:

```text
1. canonical ApplicationCoreAnalysisInput accepted
2. handler delegates to public 4.3 use-case exactly once on success
3. raw AnalysisInput rejected/mapped to deterministic 400
4. raw CanonicalAnalysisResult rejected/mapped to deterministic 400
5. manual/forged ApplicationCoreAnalysisInput rejected/mapped to deterministic 400
6. pre-mutated canonical 4.2 authority does not produce success
7. canonical ApplicationAnalysisResult success projection preserves exact core fingerprint
8. success body equals canonical core serialization semantics
9. success body is json.dumps-safe
10. success body mutation does not mutate canonical result
11. canonical result mutation after response creation does not mutate response snapshot
12. response body cannot be passed back as application authority
13. invalid-authority error has stable machine code
14. invalid-authority error does not expose internal exception text
15. unexpected execution exception -> generic deterministic 500
16. unexpected error body does not expose traceback/internal exception text
17. no direct core analyze call in transport production source
18. no direct calculate_* engine calls
19. no generate_analysis_fingerprint/current_model_versions use
20. no raw authority deserializer
21. no web-framework imports/dependencies
22. no route/path/OpenAPI/CORS/rate-limit product-policy freeze
23. app version remains 0.1.0
24. dependency set unchanged
25. no frozen upstream production source changes
26. COMB-005 remains NOT_APPROVED
27. full repository regression passes
```

If an explicit blocked/422 transport outcome is implemented, add adversarial tests proving it is reached only from a genuine canonical blocked application condition rather than caller-provided status strings.

---

# 15. CHANGE SCOPE

Expected persistent changes should be app-local, e.g.:

```text
sitescore-app/src/sitescore_app/transport.py
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/tests/test_http_api_transport_foundation.py
sitescore-app/docs/CHECKPOINT_4_4_HTTP_API_TRANSPORT_FOUNDATION.md
```

A narrow app-local helper change is acceptable only if justified.

Do NOT modify production source under:

```text
sitescore-core/
sitescore-data/
sitescore-pipeline/
sitescore-benchmarks/
sitescore-metrics/
sitescore-spatial/
sitescore-providers/
```

Do not alter frozen FAZ 4.0-4.3 semantics.

No pyproject dependency/version change is expected.

---

# 16. COMB-005 / PRODUCTION TRUTH FIREWALL

Frozen truth remains:

```text
COMB-005: NOT_APPROVED
approved registry: ()
weights: ()
composition_method: UNRESOLVED
production road_parking_access_score: unavailable / non-authoritative
```

A successful controlled transport test using canonical test fixtures does NOT mean the real production pipeline is score-ready.

Do not change readiness, benchmark, calibration, or road/parking composite semantics.

---

# 17. VALIDATION REQUIREMENTS

Run full repository regression on the exact implementation candidate.

Current locked baseline before 4.4 changes:

```text
sitescore-app:         18 PASS
sitescore-pipeline:    53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics:     67 PASS
sitescore-spatial:    180 PASS
sitescore-providers:  418 PASS
sitescore-data:       361 PASS
sitescore-core:        86 PASS
TOTAL:               1374 / 1374 PASS
```

Report exact package counts, Actions run/job ids, validated SHA, persistent final head, and validated-SHA -> final-head diff.

If a temporary workflow is used, remove it after successful validation and prove that only workflow removal occurred after the validated candidate.

---

# 18. IMPLEMENTER HANDOFF REQUIREMENTS

Implementer must report:

```text
BASE_SHA
CODE_BRANCH
CODE_HEAD_SHA
PR
exact changed-file list
public transport APIs
success response schema
error/status schema
how 4.3 delegation is preserved
how raw authority deserialization is prevented
snapshot/deep-serialization behavior
dependency/version status
COMB-005 status
FAZ 4.4 firewall status
full regression evidence
validated SHA -> final HEAD integrity
```

Do not claim READY_TO_LOCK or merge authority.

---

# 19. PHASE-BOUNDARY FIREWALL

FAZ 4.4 must NOT implement:

```text
auth/accounts/JWT/session
Stripe/payment/webhooks
report/PDF generation
email delivery
UI/frontend
queue/background workers
deployment/container orchestration
n8n
provider API integration expansion
empirical calibration
COMB-005 approval
```

After 4.4 is independently reviewed and user-LOCKED, the next step is **FAZ 4-FINAL integrated audit/freeze**, not an invented FAZ 4.5.

STOP after implementing 4.4 and reporting READY_FOR_REVIEW.
