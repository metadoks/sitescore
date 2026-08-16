# FAZ 4.4 — HTTP / API Transport Foundation

## Status

Implementation checkpoint for a framework-independent transport adapter over the locked FAZ 4.3 application analysis use-case.

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
