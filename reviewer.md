# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: AUTHORITY-CORRECTIVE-REOPEN
CHECKPOINT_TITLE: PIPE-AUTH-H001 + APP-H002 Authority Corrective Reopen

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 16427d8bb74611a3de46652d55b708edc93b055b
CODE_BRANCH: corrective/authority-reopen-pipe-app
REVIEWED_HEAD_SHA: c8cc9cee90981578fba5d088f1008e8f8b1a511a
PR: #9

CONTRACT_CHANGE_REQUIRED: 1
USER_REOPEN_AUTHORIZED: YES
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

FAZ_3_STATUS: FROZEN_WITH_NARROW_USER_AUTHORIZED_CORRECTIVE_REOPEN
FAZ_4_0_STATUS: HISTORICALLY_LOCKED_MERGED
FAZ_4_1_IMPLEMENTATION_STATUS: NOT_STARTED

PIPE-AUTH-H001: RESOLVED
APP-H002: OPEN

BLOCKERS:
- APP-H002-R001: exact factory-returned RealDataPipelineResult semantic state remains mutable in place after app registration and is not construction-time integrity-bound
```

---

# 1. REVIEW SCOPE AND EXACT SHA

Reviewer independently inspected actual GitHub state for the user-authorized corrective reopen only.

Verified:

```text
main: 16427d8bb74611a3de46652d55b708edc93b055b
PR: #9
PR state: OPEN
merged: FALSE
mergeable: TRUE
base: main
base SHA: 16427d8bb74611a3de46652d55b708edc93b055b
head branch: corrective/authority-reopen-pipe-app
reviewed head: c8cc9cee90981578fba5d088f1008e8f8b1a511a
changed files: 5
```

Persistent changed filenames are exactly:

```text
docs/AUTHORITY_CORRECTIVE_REOPEN_PIPE_APP.md
sitescore-app/src/sitescore_app/gating.py
sitescore-app/tests/test_authority_corrective_reopen.py
sitescore-pipeline/src/sitescore_pipeline/integration.py
sitescore-pipeline/tests/test_readiness_pipeline.py
```

No FAZ 4.1 implementation was found.

This decision is exact-SHA-specific to:

```text
c8cc9cee90981578fba5d088f1008e8f8b1a511a
```

---

# 2. VALIDATION / ACTIONS — VERIFIED CLEAN FOR REVIEWED CANDIDATE

Reviewer independently verified the final validation run:

```text
workflow: authority-corrective-validation
run ID: 31944221603
job ID: 95157706187
validated SHA: db7d0aa43d529ab766f3eabbbea1fd77d9f34acf
status: completed
conclusion: success
```

The job directly ran:

```text
Corrective scope audit: SUCCESS
sitescore-app tests: SUCCESS
sitescore-pipeline tests: SUCCESS
sitescore-benchmarks tests: SUCCESS
sitescore-metrics tests: SUCCESS
sitescore-spatial tests: SUCCESS
sitescore-providers tests: SUCCESS
sitescore-data tests: SUCCESS
sitescore-core tests: SUCCESS
```

Reviewer also independently compared validated SHA to final PR HEAD:

```text
base: db7d0aa43d529ab766f3eabbbea1fd77d9f34acf
head: c8cc9cee90981578fba5d088f1008e8f8b1a511a
status: ahead
commits: 1
only changed path: .github/workflows/authority-corrective-validation.yml
change: REMOVED
```

Therefore source/tests/docs at reviewed HEAD are the exact validated candidate; only the temporary workflow was removed afterward.

The passing suite is valid regression evidence, but it does not override the uncovered authority case below because the present test matrix does not exercise that case.

---

# 3. PIPE-AUTH-H001 — RESOLVED AT REVIEWED HEAD

Reviewer accepts the pipeline-side correction at this SHA.

`sitescore-pipeline/src/sitescore_pipeline/integration.py` now binds canonical `NormalizedFeatureAssembly` construction-time authority in closure-private registry state, including:

```text
features
direct_results
feature_policies
compatibility
approved_fallback_policies
artifact_identities
assembly_id
semantic attestation
```

Canonical resolution requires both registered factory-owned identity and integrity against the construction-time binding.

The implementation also binds `ReadinessEvaluation` to:

```text
exact assembly object
exact readiness result object
construction-time readiness semantic attestation
```

and verifies the nested canonical assembly again before trusting readiness.

Critically, `derive_scoring_readiness(...)` consumes closure-resolved trusted assembly values, and `build_real_data_pipeline_result(...)` consumes closure-resolved trusted assembly/readiness values for:

```text
normalized features
readiness status
real-unit coherence
terminal status
terminal readiness
```

It does not validate a registered outer object and then intentionally continue from a replacement public assembly/readiness reference.

Direct `object.__setattr__` regressions cover the required assembly fields, readiness assembly/result replacement, nested `is_score_ready` mutation, forged numeric road/parking mutation, copied/reconstructed authority objects, and the unmodified canonical NOT_SCORE_READY path.

Therefore at reviewed SHA:

```text
PIPE-AUTH-H001: RESOLVED
```

Do not redesign or broaden the pipeline correction unless required to support the app hardening below.

---

# 4. APP-H002 — PARTIAL FIX IS NOT SUFFICIENT

The app correction successfully closes one mutation class:

```text
canonical ApplicationPipelineResult
-> replace .pipeline_result with a different terminal object
-> rejected

canonical ApplicationScoringInput
-> replace .application_pipeline_result with another wrapper
-> rejected
```

The closure registry now remembers the exact terminal object and exact app wrapper object accepted at construction.

However, `resolve_pipeline_result(...)` currently proves only:

```python
value.pipeline_result is trusted_terminal
```

It does not prove that the semantic authority-bearing fields of that exact `trusted_terminal` still equal their construction-time state.

This is load-bearing because `RealDataPipelineResult` is a frozen dataclass, but the repository's explicit adversarial model already treats `object.__setattr__` as a valid post-construction mutation mechanism.

The exact same factory-returned terminal object can therefore be mutated in place while preserving this condition:

```text
value.pipeline_result is trusted_terminal == True
```

The present app binding detects reference redirection, but not semantic mutation of the bound authority object itself.

---

# 5. APP-H002-R001 — REPRODUCIBLE SAME-TERMINAL AUTHORITY BYPASS

## Severity

```text
BLOCKER
FALSE SCORE_READY AUTHORITY REMAINS POSSIBLE
COMB-005 APP-GATE BYPASS REMAINS POSSIBLE
POST-REGISTRATION MUTATION REMAINS AUTHORITATIVE
```

The current real canonical production path is NOT_SCORE_READY because COMB-005 is not approved.

After obtaining a legitimate factory-owned `ApplicationPipelineResult`, a caller can retain the exact terminal identity and mutate the terminal itself.

Conceptually:

```python
app_result = build_application_pipeline_result(...)
terminal = app_result.pipeline_result

# same exact factory-returned terminal object
object.__setattr__(terminal, "status", PipelineStatus.SCORE_READY)
object.__setattr__(terminal.scoring_readiness, "is_score_ready", True)

# app_result.pipeline_result is still terminal
# resolve_pipeline_result(app_result) therefore accepts current implementation

build_application_scoring_input(app_result)
```

Current `build_application_scoring_input(...)` does:

```text
resolve_pipeline_result(app_result)
-> returns the same trusted_terminal object
-> evaluate_application_scoring_gate(trusted_terminal)
```

The gate then reads the terminal's CURRENT mutable public state:

```text
pipeline_result.status
pipeline_result.scoring_readiness.is_score_ready
pipeline_result.normalized_features
```

If those fields were mutated in place, the exact registered terminal identity remains unchanged and the gate can describe it as ELIGIBLE.

The old NOT_SCORE_READY `reason_codes` do not protect this path because the app gate does not require the SCORE_READY terminal's full constructor invariants to be re-established, and re-running public DTO validation alone would not satisfy the required construction-time authority rule anyway.

This is the same class of defect the corrective reopen was created to eliminate:

```text
factory-owned object
+
post-registration object.__setattr__ mutation
+
retained execution authority
```

Therefore APP-H002 is not resolved at this SHA.

---

# 6. FORGED ROAD/PARKING / NORMALIZED-FEATURE CONSEQUENCE

The same-terminal attack is not limited to `status`.

`terminal.normalized_features` is itself a frozen DTO whose fields can be altered with the same adversarial mechanism.

A caller can keep the exact construction-time `RealDataPipelineResult` object and mutate the nested normalized feature surface, including:

```text
road_parking_access_score
```

toward a caller-created numeric/calibrated/eligible metric.

Current `resolve_pipeline_result(...)` does not attest the nested semantic state of the trusted terminal, so the app wrapper still passes canonicality as long as `.pipeline_result` continues to point to the exact same terminal object.

This means app-layer construction-time authority is not yet bound to the actual normalized-feature truth returned by the canonical pipeline factory.

The frozen COMB-005 source itself remains correct; the defect is that app authority can continue to trust mutated state of the exact returned DTO.

---

# 7. POST-GRANT SCORING CAPABILITY IS ALSO REDIRECTABLE SEMANTICALLY

There is a second manifestation of the same root blocker.

`ApplicationScoringInput` properties currently traverse public mutable references dynamically:

```text
pipeline_result
sector_key
normalized_features
readiness_fingerprint
```

The scoring-input registry binds the exact `ApplicationPipelineResult` wrapper object, but not an immutable construction-time scoring-authority snapshot.

Therefore even if a scoring input was legitimately created in a controlled SCORE_READY path, later in-place mutation of the same exact bound terminal can change what the capability exposes without changing either registered outer identity.

Examples that must not remain possible:

```text
same exact terminal.sector_key mutated
-> scoring_input.sector_key changes

same exact terminal.normalized_features mutated
-> scoring_input.normalized_features changes

same exact terminal.scoring_readiness mutated
-> scoring_input.readiness_fingerprint / readiness truth changes
```

`require_canonical_application_scoring_input(...)` currently revalidates only wrapper identity/reference binding; it does not establish that the exact terminal's authority-bearing semantics remain equal to the construction-time app binding.

This is unsafe for future FAZ 4.1 because category aggregation must consume a stable canonical `ApplicationScoringInput`, including the exact sector and normalized features that earned permission.

---

# 8. WHY THE CURRENT APP TESTS DO NOT CLOSE THIS CASE

The new corrective app test correctly verifies replacement of:

```text
ApplicationPipelineResult.pipeline_result
ApplicationScoringInput.application_pipeline_result
```

with DIFFERENT objects.

It also confirms that caller-controlled status/fingerprint/features are not standalone factory parameters.

However, it does not test mutation of authority-bearing fields inside the SAME exact registered terminal object.

In particular, the required hardening suite currently lacks direct `object.__setattr__` regressions for at least:

```text
exact bound terminal.status
exact bound terminal.sector_key
exact bound terminal.scoring_readiness semantic state
exact bound terminal.normalized_features semantic state
exact bound normalized_features.road_parking_access_score
post-grant mutation observed through ApplicationScoringInput properties
```

A signature assertion proving that detached `status` or `normalized_features` are not function parameters is not equivalent to proving that the construction-time terminal state is immutable authority.

---

# 9. REQUIRED APP-H002 HARDENING

Remain strictly inside the already user-authorized APP-H002 corrective scope.

No new reopen is required at present.

The corrected app authority must establish:

```text
factory origin
+
exact construction-time terminal object binding
+
construction-time authority-semantic binding of that terminal
+
post-registration integrity verification
+
trusted downstream consumption
```

At minimum, all terminal state that can grant or parameterize later scoring authority must be construction-time bound, including:

```text
PipelineStatus
SectorKey
NormalizedLocationFeatures authority surface
ScoringReadinessResult authority surface / readiness fingerprint
```

The implementation must also account for nested semantic mutation of the normalized-feature/readiness DTOs, not only replacement of their outer references.

A valid implementation may use closure-private immutable construction-time snapshots/attestations or an equivalent mechanism.

Do not treat any of the following alone as sufficient:

```text
terminal object identity
frozen dataclass
re-running __post_init__
public hash
public readiness fingerprint
field equality without factory-origin binding
```

The expected construction-time state must remain closure-private/factory-bound.

## Trusted consumption requirement

`build_application_scoring_input(...)` must make its authorization decision from verified construction-time authority, not from semantically mutated current public terminal fields.

Likewise a canonical `ApplicationScoringInput` must not expose altered sector/features/readiness after registration merely because the outer wrapper/scoring-input identities remain the same.

Do not implement:

```text
validate wrapper identity
-> continue reading mutable terminal public state
```

or:

```text
validate scoring-input identity
-> return capability whose public properties dynamically follow mutated terminal state
```

The exact implementation pattern is left to Implementer, provided public signatures/version governance remain stable and the resulting authority is genuinely closure-bound.

---

# 10. MANDATORY NEW APP-H002-R001 TESTS

Add direct `object.__setattr__` regressions proving at least:

```text
A. canonical real NOT_SCORE_READY ApplicationPipelineResult
   -> mutate SAME exact terminal.status to SCORE_READY
   -> cannot create ApplicationScoringInput

B. same exact terminal
   -> mutate nested scoring_readiness.is_score_ready False -> True
   -> canonical app authority rejects / cannot grant scoring permission

C. same exact terminal normalized_features
   -> forge numeric/calibrated/eligible road_parking_access_score
   -> rejected

D. same exact terminal sector_key
   -> replace with another sector
   -> rejected / cannot alter scoring authority sector

E. same exact terminal scoring_readiness/readiness_fingerprint nested semantics
   -> mutated after registration
   -> rejected

F. controlled legitimate scoring input
   -> mutate SAME exact terminal after scoring-input registration
   -> require_canonical_application_scoring_input rejects

G. controlled legitimate scoring input
   -> post-registration terminal/feature/sector/readiness mutation
   -> scoring-input properties cannot expose mutated authority as canonical state

H. existing different-terminal wrapper redirection tests remain passing

I. current real COMB-005 canonical path remains NOT_SCORE_READY
```

Use `object.__setattr__` directly.

The test must demonstrate failure of downstream authorization/canonical capability, not merely DTO validation or signature shape.

---

# 11. COMB-005 / SEMANTIC FIREWALL — VERIFIED UNCHANGED

Reviewer independently inspected frozen COMB-005 production source at reviewed head.

Verified:

```text
COMB005_V1_POLICY.approval_state: NOT_APPROVED
weights: ()
composition_method: UNRESOLVED
missing_side_behavior: REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1: ()
production composite score: None
```

No actual COMB-005 approval/weight/fallback change exists in PR #9.

The blocker above is an app execution-authority bypass around the correct frozen production truth, not a change to COMB-005 itself.

---

# 12. VERSION / DEPENDENCY / SCOPE AUDIT — PASS

Reviewer independently verified:

```text
sitescore-app version: 0.1.0
sitescore-app deps:
- sitescore-data==0.1.0
- sitescore-pipeline==0.1.0

sitescore-pipeline version: 0.1.0
sitescore-pipeline deps:
- sitescore-data==0.1.0
- sitescore-benchmarks==0.1.0

sitescore-app -> sitescore-core: NOT ADDED
new runtime dependencies: NONE
pyproject changes in PR: NONE
```

Base-to-head diff contains no production source changes in:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
sitescore-benchmarks
```

No category aggregation, core scoring adapter, `CategoryScores`, `core.analyze()`, Location Score, Decision Layer, HTTP/API, auth, payment, report/PDF, UI, queue/deployment, or n8n implementation was found.

Therefore:

```text
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
FAZ_4_1_IMPLEMENTATION_STATUS: NOT_STARTED
```

---

# 13. CONSOLIDATED REVIEW DECISION

At exact reviewed SHA:

```text
PIPE-AUTH-H001: RESOLVED
APP-H002: OPEN
APP-H002-R001: OPEN

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
```

The PR must NOT be merged or LOCKed at this SHA.

Implementer should harden only APP-H002-R001, retain the accepted pipeline correction, add the required same-terminal adversarial regressions, update corrective documentation if needed, and run fresh full regression because source/tests will change.

After hardening, `implementer.md` must return with:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
PR: #9
CODE_HEAD_SHA: <new exact head>
PIPE-AUTH-H001: IMPLEMENTED / unchanged unless necessary
APP-H002: IMPLEMENTED
APP-H002-R001: IMPLEMENTED
FAZ_4_1_IMPLEMENTATION_STATUS: NOT_STARTED
```

Also report new validation run/job IDs, exact validated SHA, final PR HEAD, and validated-SHA -> final-HEAD compare.

Do not merge.
Do not self-LOCK.
Do not start FAZ 4.1.

STOP.
