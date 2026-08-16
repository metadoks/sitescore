# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.3
CHECKPOINT_TITLE: Application Analyze Use-Case Orchestration

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 5cd39f48b6c0a4882e0be3402dfa9303b791350f
CODE_BRANCH: faz4/4.3-application-analyze-orchestration
REVIEWED_HEAD_SHA: NONE
PR: NONE

CONTRACT_CHANGE_REQUIRED: 0
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
DEPENDENCY_CHANGE_AUTHORIZED: NONE — reuse existing sitescore-core==0.1.0 dependency

FAZ_3_STATUS: FROZEN
FAZ_4_0_STATUS: HISTORICALLY_LOCKED_MERGED
AUTHORITY_CORRECTIVE_REOPEN_STATUS: LOCKED_MERGED
FAZ_4_1_IMPLEMENTATION_STATUS: LOCKED_MERGED
FAZ_4_2_IMPLEMENTATION_STATUS: LOCKED_MERGED
FAZ_4_3_IMPLEMENTATION_STATUS: IMPLEMENTATION_REQUESTED
FAZ_4_4_IMPLEMENTATION_STATUS: NOT_STARTED

BLOCKERS: NONE
```

---

# 1. TRANSITION AUTHORITY / EXACT BASE

The user requested continuation after FAZ 4.2 was independently verified LOCKED / MERGED.

Reviewer independently re-fetched current `main` and verified exactly:

```text
5cd39f48b6c0a4882e0be3402dfa9303b791350f
```

FAZ 4.3 is authorized to begin from exactly that base.

Historical truth remains:

```text
FAZ 3: FROZEN
FAZ 4.0: HISTORICALLY LOCKED / MERGED
Authority corrective reopen: USER-AUTHORIZED, RESOLVED, LOCKED / MERGED
FAZ 4.1: LOCKED / MERGED
FAZ 4.2: LOCKED / MERGED
FAZ 4.3: NOW AUTHORIZED
FAZ 4.4: NOT STARTED
```

Do not rewrite or reopen earlier history.

---

# 2. CHECKPOINT OBJECTIVE

Implement exactly one application use-case capability:

```text
canonical ApplicationCoreAnalysisInput
-> trusted closure-bound exact core AnalysisInput
-> frozen sitescore-core analyze(AnalysisInput)
-> exact CanonicalAnalysisResult
-> factory-owned application analysis-result authority
```

Recommended output authority:

```text
ApplicationAnalysisResult
```

Recommended public production APIs:

```text
analyze_application_core_input(
    application_core_input: ApplicationCoreAnalysisInput,
) -> ApplicationAnalysisResult

require_canonical_application_analysis_result(
    value: ApplicationAnalysisResult,
) -> ApplicationAnalysisResult
```

Equivalent naming is acceptable if the authority semantics are identical.

This checkpoint owns invocation of the already-frozen canonical core analysis orchestrator.

It does NOT own HTTP/API transport.

---

# 3. SINGLE CANONICAL EXECUTION AUTHORITY — CORE `analyze()` ONLY

FAZ 4.3 MUST use the actual frozen core orchestrator as the only scoring/execution authority:

```text
sitescore.analyze.analyze
```

or the package's canonical exported equivalent if already defined.

Frozen core `analyze(data: AnalysisInput)` already executes, in order:

```text
Revenue Engine
-> Location Engine
-> Financial Engine
-> Decision Engine
-> Confidence Engine
-> Model Metadata
-> deterministic analysis fingerprint
-> CanonicalAnalysisResult
```

Therefore sitescore-app MUST NOT duplicate, partially recreate or independently call these engine functions in production:

```text
calculate_revenue
calculate_location_score
calculate_financial_metrics
calculate_decision
calculate_confidence
generate_analysis_fingerprint
current_model_versions
```

Do not reproduce core engine formulas, category weights, penalty rules, decision rules, financial rules, confidence rules, model-version assembly or fingerprint logic in the app.

Production orchestration should invoke the frozen core `analyze()` exactly once per successful application analysis execution.

---

# 4. ONLY CANONICAL 4.2 INPUT AUTHORITY

The only production execution input is exact factory-owned canonical:

```text
ApplicationCoreAnalysisInput
```

from locked FAZ 4.2.

Do NOT accept as execution authority:

```text
raw AnalysisInput
raw ApplicationCategoryAggregationResult
raw CategoryScores
raw revenue input
raw normalized features
raw RealDataPipelineResult
caller-supplied CanonicalAnalysisResult
caller-supplied analysis fingerprint
trusted=True
ready=True
force=True
skip_validation=True
public hash/token/sentinel
```

A structurally valid raw core `AnalysisInput` is not application authority.

---

# 5. TRUSTED FAZ 4.2 INPUT CONSUMPTION — NO VALIDATE-THEN-READ DOWNGRADE

Locked FAZ 4.2 already owns a closure-private resolver:

```text
_resolve_trusted_application_core_analysis_input
```

The public `ApplicationCoreAnalysisInput.analysis_input` property is resolver-backed, but under the project threat model public object surfaces remain potentially redirectable by direct `object.__setattr__`.

FAZ 4.3 should therefore consume the trusted closure binding directly, not use this weaker pattern:

```text
require_canonical_application_core_analysis_input(value)
-> later trust/read caller-visible mutable state without a construction-time resolver
```

Preferred flow:

```text
resolve exact canonical ApplicationCoreAnalysisInput
-> obtain closure-bound exact AnalysisInput object
-> revalidate input authority immediately before core execution
-> call frozen core analyze(exact AnalysisInput)
-> revalidate the same 4.2 input authority immediately after execution
-> only then register the downstream application analysis authority
```

An equivalent architecture is acceptable only if it proves the exact same origin + semantic-integrity guarantees.

Do not export the private 4.2 resolver through `sitescore_app.__all__` as a public authority shortcut.

---

# 6. TOCTOU / EXECUTION-INTEGRITY REQUIREMENTS

The authority transition crosses actual core execution. Therefore 4.3 must defend against input mutation/redirection before, during and after the core call.

At minimum:

1. resolve and validate the canonical 4.2 authority before execution;
2. capture the exact trusted `AnalysisInput` identity and its construction-time authority context;
3. execute core `analyze()` with that exact object;
4. re-resolve/revalidate the 4.2 authority after core returns;
5. ensure the trusted `AnalysisInput` identity/state is still the same authority that was executed;
6. fail closed rather than registering a result if input authority changed across the call.

Tests SHOULD monkeypatch/wrap the core analyze callable or otherwise use a controlled execution hook to mutate/redirection-attempt the nested 4.2 input during execution and prove no downstream application result authority is granted.

Do not solve this with a caller-visible boolean, token or detached hash.

---

# 7. EXACT CORE OUTPUT — NO APP RECOMPUTATION

The production result from core execution must be the actual:

```text
sitescore.schemas.canonical.CanonicalAnalysisResult
```

returned by the frozen core `analyze()` call.

The app MUST NOT reconstruct a second `CanonicalAnalysisResult` from copied fields and then treat the copy as canonical execution output.

The app MUST NOT recalculate or overwrite:

```text
analysis_fingerprint
model_versions
location
financial
decision
confidence
```

The exact object returned by core is the core result identity that must be bound into application authority.

---

# 8. FACTORY-OWNED APPLICATION ANALYSIS RESULT AUTHORITY

A raw `CanonicalAnalysisResult`, even if genuinely produced by a direct caller invocation of core `analyze()`, is NOT application use-case authority.

Introduce a factory-owned app-layer result/capability, recommended:

```text
ApplicationAnalysisResult
```

The wrapper must be constructor-blocked / factory-owned using the established closure-private authority pattern.

Construction-time binding must include at least:

```text
exact canonical ApplicationCoreAnalysisInput
exact trusted core AnalysisInput executed
construction-time semantic record of that trusted core AnalysisInput authority
exact CanonicalAnalysisResult returned by core
analysis_fingerprint at construction time
model_versions construction-time semantic state
location construction-time semantic state
financial construction-time semantic state
decision construction-time semantic state
confidence construction-time semantic state
complete recursive CanonicalAnalysisResult semantic record
```

If the existing `_semantic_record` authority helper from FAZ 4.2 can be reused safely without exposing mutable authority globally, reuse/refactor narrowly rather than inventing a weaker duplicate.

A private/non-exported 4.2 trusted resolver may be imported within app production source for this purpose.

---

# 9. RESULT MUTABILITY / POST-EXECUTION INTEGRITY

Frozen dataclass syntax is not sufficient under the project adversarial model.

Core `CanonicalAnalysisResult` and nested frozen result objects can still be mutated with direct `object.__setattr__` in adversarial tests.

Canonical application analysis validation must detect/reject at minimum:

```text
ApplicationAnalysisResult redirected to another ApplicationCoreAnalysisInput
ApplicationAnalysisResult redirected to another CanonicalAnalysisResult
CanonicalAnalysisResult.analysis_fingerprint mutation
CanonicalAnalysisResult.model_versions replacement/mutation
CanonicalAnalysisResult.location replacement
nested LocationResult field mutation
CanonicalAnalysisResult.financial replacement
nested FinancialResult field mutation
nested FinancialResult.revenue / RevenueScenarios field mutation
CanonicalAnalysisResult.decision replacement
nested DecisionResult field mutation
CanonicalAnalysisResult.confidence replacement
nested ConfidenceResult field mutation
nested canonical ApplicationCoreAnalysisInput mutation after analysis result registration
nested category/scoring/pipeline authority mutation propagating through 4.2 after result registration
```

The complete recursive result semantic record may satisfy multiple nested checks, but targeted adversarial regressions must demonstrate the important surfaces explicitly.

Public result properties, if exposed, should be resolver-backed so mutation causes fail-closed access rather than silently returning mutated execution output.

---

# 10. FINGERPRINT / MODEL VERSION AUTHORITY

The core owns both:

```text
current_model_versions()
generate_analysis_fingerprint(...)
```

FAZ 4.3 MUST trust the exact fields of the returned core result only after binding and integrity validation.

Do NOT generate an app-specific alternate analysis fingerprint for scoring identity.

Do NOT overwrite or normalize the core fingerprint.

Do NOT reconstruct model versions independently in the app.

If an app-level authority identity is desired internally, it must not replace or masquerade as the canonical core `analysis_fingerprint`.

The application result must preserve exactly the core-returned fingerprint and model-version semantics.

---

# 11. DETERMINISM / SINGLE-CALL TESTING

Tests must prove deterministic orchestration for stable canonical inputs.

At minimum:

```text
same semantically identical controlled canonical input surface
+ same frozen model versions
-> same core analysis result semantics / same analysis_fingerprint
```

Do not claim that two distinct factory authority objects are the same identity; determinism here means core analysis semantics/fingerprint for equivalent controlled input, not authority interchangeability.

Also prove the production application orchestration calls the canonical core `analyze()` exactly once for one successful invocation.

No hidden secondary core analyze call for validation, comparison, fingerprinting or DTO conversion is allowed.

---

# 12. CORE OUTPUT CONTRACT PRESERVATION

No app-layer transformation may alter the meaning of the returned canonical result.

The application authority must preserve the exact core result components:

```text
analysis_fingerprint
model_versions
location
financial
decision
confidence
```

Do not add a second location score, alternative financial result, app-specific decision label, confidence override or fallback score in 4.3.

Do not round or format core output for presentation. Formatting belongs to later transport/report boundaries.

---

# 13. STRICT FAZ 4.4 FIREWALL

FAZ 4.3 stops after canonical core analysis execution and factory-owned application result authority.

Explicitly forbidden in production during this checkpoint:

```text
FastAPI / Flask / Django / Starlette
HTTP routes/endpoints
request/response transport schemas
JSON transport envelope design
HTTP status mapping
API versioning
CORS
rate limiting
auth/accounts/session/JWT
Stripe/payment/webhooks
report/PDF generation
email delivery
UI/frontend
queue/background worker
deployment/container/orchestration
n8n
```

Do not create transport-facing API DTOs merely for future convenience.

FAZ 4.4 remains NOT_STARTED.

---

# 14. COMB-005 / REAL PRODUCTION TRUTH FIREWALL

FAZ 4.3 must not alter readiness or fabricate a real production execution path.

Frozen truth remains:

```text
COMB-005: NOT_APPROVED
approved registry: ()
weights: ()
composition_method: UNRESOLVED
production road_parking_access_score: unavailable / non-authoritative
```

Therefore the real pipeline may still be blocked before reaching canonical 4.1/4.2/4.3 scoring execution.

Controlled test-only canonical SCORE_READY -> category -> core-input authority fixtures are permitted to test orchestration mechanics.

They are NOT evidence of empirical production readiness or COMB-005 approval.

Do not modify frozen benchmark/pipeline readiness semantics.

---

# 15. DEPENDENCY / VERSION / CHANGE-SCOPE RULES

No new runtime dependency is authorized.

Expected `sitescore-app` dependency set remains exactly:

```text
sitescore-data==0.1.0
sitescore-pipeline==0.1.0
sitescore-core==0.1.0
```

Package version remains:

```text
sitescore-app==0.1.0
```

Expected production changes are narrowly app-local, for example:

```text
sitescore-app/src/sitescore_app/analysis_adapter.py   # only if narrow trusted-helper refactor is needed
sitescore-app/src/sitescore_app/analysis_use_case.py # or equivalent orchestration module
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/tests/...
sitescore-app/docs/CHECKPOINT_4_3_APPLICATION_ANALYZE_USE_CASE.md
```

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

Do not modify 4.1 category formulas/weights/readiness semantics.

If frozen upstream production change appears necessary, STOP and report:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

---

# 16. MANDATORY TEST MATRIX

At minimum add/maintain tests proving the following.

## 16.1 Input authority / anti-forgery

```text
1. raw AnalysisInput rejected by application orchestration entry
2. raw CanonicalAnalysisResult cannot become application authority
3. manual ApplicationCoreAnalysisInput rejected
4. copy/reconstructed ApplicationCoreAnalysisInput rejected
5. detached category/result/fingerprint/trusted/ready/force inputs do not exist in orchestration signature
6. mutated canonical 4.2 authority before execution -> rejected / core analyze not called
```

## 16.2 Exact core execution

```text
7. canonical frozen core analyze callable is used
8. exact trusted AnalysisInput identity is passed to core analyze
9. successful application invocation calls core analyze exactly once
10. returned exact core CanonicalAnalysisResult identity is bound, not reconstructed
11. all four sectors execute successfully under controlled canonical fixtures where core inputs are valid
12. output analysis_fingerprint equals exact core-returned fingerprint
13. output model_versions/location/financial/decision/confidence are the exact core-returned component identities unless core itself returns copies internally
```

## 16.3 TOCTOU

```text
14. nested 4.2/core-input mutation before execution blocks call
15. controlled mutation/redirection during core analyze call prevents downstream authority registration
16. nested 4.2/core-input mutation after result registration invalidates ApplicationAnalysisResult
```

## 16.4 Result anti-forgery / post-registration mutation

```text
17. manually allocated ApplicationAnalysisResult rejected
18. copy/reconstructed ApplicationAnalysisResult rejected
19. wrapper redirected to another canonical core input rejected
20. wrapper redirected to another core result rejected
21. analysis_fingerprint object.__setattr__ mutation rejected
22. model_versions replacement or field mutation rejected
23. LocationResult mutation rejected
24. FinancialResult mutation rejected
25. nested RevenueScenarios mutation rejected
26. DecisionResult mutation rejected
27. ConfidenceResult mutation rejected
```

## 16.5 Determinism / no duplicate orchestration

```text
28. equivalent controlled canonical business input semantics produce same core analysis fingerprint under same frozen model versions
29. no app engine formulas are reimplemented
30. no direct calculate_* engine function usage in production app orchestration
31. no app-side generate_analysis_fingerprint/current_model_versions call
32. no second core analyze call hidden in validation
```

## 16.6 Firewalls / production truth

```text
33. COMB-005 remains NOT_APPROVED and production composite remains unavailable
34. no dependency/version change
35. no frozen upstream production source diff
36. no HTTP/API/auth/payment/report/UI/deployment/n8n work
37. FAZ 4.4 remains NOT_STARTED
```

Use asymmetric/sector-specific controlled inputs so wrong-sector or swapped-result behavior cannot pass accidentally.

---

# 17. FULL REGRESSION / ACTIONS REQUIREMENT

Before READY_FOR_REVIEW validate all packages:

```text
sitescore-app
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Use GitHub Actions evidence Reviewer can independently inspect.

Report exact pass counts for every package and total.

If a temporary validation workflow is used, remove it before final review HEAD and report:

```text
validated SHA
final PR HEAD
exact validated SHA -> final HEAD comparison
```

Acceptable post-validation delta is only temporary workflow removal. Any source/test/doc/dependency change after validation requires fresh validation.

---

# 18. IMPLEMENTER RETURN CONTRACT

When complete, update only `implementer.md` with at least:

```text
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.3
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: 5cd39f48b6c0a4882e0be3402dfa9303b791350f
CODE_BRANCH: faz4/4.3-application-analyze-orchestration
CODE_HEAD_SHA: <exact>
PR: #N
CONTRACT_CHANGE_REQUIRED: 0
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
FAZ_4_3_IMPLEMENTATION_STATUS: IMPLEMENTED_READY_FOR_REVIEW
FAZ_4_4_IMPLEMENTATION_STATUS: NOT_STARTED
```

Also report:

- exact changed filenames;
- exact core analyze import/call path;
- proof exact trusted AnalysisInput identity reaches core;
- proof one core analyze call per successful invocation;
- application result authority design;
- full construction-time result semantic binding;
- adversarial input/result/TOCTOU matrix;
- deterministic fingerprint evidence;
- COMB-005/current production truth;
- dependency/version unchanged evidence;
- full Actions run/job IDs and exact package counts;
- validated SHA -> final HEAD compare;
- proof FAZ 4.4 was not started.

Do NOT merge.
Do NOT self-LOCK.
Do NOT start FAZ 4.4.

STOP after Reviewer handoff.

---

# 19. REVIEWER ACCEPTANCE GATE

READY_TO_LOCK is possible only if Reviewer can independently conclude for the exact PR head:

> FAZ 4.3 accepts only canonical factory-owned FAZ 4.2 core-input authority; resolves the closure-bound exact `AnalysisInput`; invokes the frozen core `analyze()` exactly once as the sole engine/orchestration authority; revalidates the input across the execution boundary; binds the exact returned `CanonicalAnalysisResult` into factory-owned application authority with recursive construction-time integrity over fingerprint, model versions, location, financial, decision and confidence results; rejects forged/copied/post-registration/nested/TOCTOU mutations; introduces no dependency/version or frozen upstream changes; preserves COMB-005 production truth; full regression is green; and FAZ 4.4 transport work remains not started.

Until then:

```text
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
FAZ_4_3_IMPLEMENTATION_STATUS: IMPLEMENTATION_REQUESTED
FAZ_4_4_IMPLEMENTATION_STATUS: NOT_STARTED
```

STOP.
