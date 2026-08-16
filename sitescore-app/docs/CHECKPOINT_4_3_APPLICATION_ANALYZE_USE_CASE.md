# FAZ 4.3 — Application Analyze Use-Case Orchestration

## Scope

This checkpoint adds exactly one application capability:

```text
canonical ApplicationCoreAnalysisInput
-> trusted exact frozen core AnalysisInput
-> frozen sitescore-core analyze() exactly once
-> exact CanonicalAnalysisResult
-> factory-owned ApplicationAnalysisResult
```

FAZ 4.4 transport work is not included.

## Canonical input authority

Production orchestration accepts only the factory-owned `ApplicationCoreAnalysisInput` from locked FAZ 4.2. Raw `AnalysisInput`, raw category values, raw `CanonicalAnalysisResult`, detached fingerprints, and caller authority flags are not accepted.

The use case consumes `_resolve_trusted_application_core_analysis_input` privately and revalidates the exact trusted core input immediately before and immediately after the core call. If identity or semantic authority changes across execution, no application result authority is registered.

## Single core execution authority

The only scoring/orchestration call is the frozen `sitescore.analyze.analyze` callable captured as the canonical core authority. App production code does not invoke individual revenue/location/financial/decision/confidence engines, model-version assembly, category weights, or fingerprint generation.

## Application result authority

`ApplicationAnalysisResult` is constructor-blocked and factory-owned. Its closure-private binding records:

- exact canonical `ApplicationCoreAnalysisInput`;
- exact trusted `AnalysisInput` and construction-time semantic record;
- exact `CanonicalAnalysisResult` returned by core;
- exact core analysis fingerprint;
- exact model_versions/location/financial/decision/confidence component identities and semantic records;
- complete recursive `CanonicalAnalysisResult` semantic record.

Public result access is resolver-backed and fails closed after nested or direct mutation.

## Firewalls

No new dependency or version change. No frozen upstream production source change. No HTTP/API/request-response transport, auth, payment, report/PDF, UI, queue, deployment, or n8n work. COMB-005 remains NOT_APPROVED and real production readiness is not claimed.
