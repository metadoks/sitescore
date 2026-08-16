# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.0
CHECKPOINT_TITLE: Application / Backend Boundary Foundation
REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
CODE_BRANCH: faz4/cp4.0-application-boundary-foundation
REVIEWED_HEAD_SHA: f38d09ab20bc6687b76fc376b44fa3efb106cefb
PR: #8
CONTRACT_CHANGE_REQUIRED: 0
FAZ_3_STATUS: FROZEN
```

---

# 1. REVIEW DECISION

```text
FAZ 4.0
Decision: HARDENING REQUIRED
PR: #8
Reviewed HEAD: f38d09ab20bc6687b76fc376b44fa3efb106cefb
```

The additive package shape, dependency direction, fail-closed handling of ordinary NOT_SCORE_READY/PIPELINE_ERROR states, scope discipline, and validation are clean. One production authority blocker remains.

Do not merge. Do not self-LOCK. Do not start FAZ 4.1.

---

# 2. VERIFIED CLEAN AREAS

Reviewer independently verified at the exact reviewed HEAD:

- PR #8 is open, mergeable, base `main`, exact head `f38d09ab20bc6687b76fc376b44fa3efb106cefb`;
- persistent diff is exactly five additive files under `sitescore-app`;
- frozen FAZ 3 production source and dependency metadata are unchanged;
- `sitescore-app==0.1.0` depends only on `sitescore-data==0.1.0` and `sitescore-pipeline==0.1.0`;
- no upstream package imports `sitescore_app`;
- no production category aggregation, `CategoryScores`, Location Score, Decision Layer or `core.analyze()` call exists;
- no HTTP/API/auth/payment/report/UI/queue dependency or implementation exists;
- no empirical/calibration shortcut was introduced;
- `ApplicationScoringInput` itself is direct-constructor-disabled and factory-owned through closure-private registry state;
- caller boolean/status override parameters are absent from `build_application_scoring_input()`;
- GitHub Actions run `31928358383` succeeded at validated SHA `4168bde1d220041ceea1653dc7855dea21b69fd2`;
- validated SHA -> reviewed HEAD differs only by removal of `.github/workflows/cp40-validation.yml`.

The blocker below is specifically about whether the object admitted into that otherwise-good app capability is actually canonical pipeline output.

---

# 3. APP-H001 — APPLICATION GATE ACCEPTS CALLER-FABRICATED SCORE_READY TERMINAL DTO AS PRODUCTION AUTHORITY

## Problem

`build_application_scoring_input()` calls `evaluate_application_scoring_gate(pipeline_result)`.

The gate verifies only:

```text
isinstance(pipeline_result, RealDataPipelineResult)
status == SCORE_READY
scoring_readiness is ScoringReadinessResult
scoring_readiness.is_score_ready == True
normalized_features is NormalizedLocationFeatures
```

It does **not** prove that the supplied `RealDataPipelineResult` is the actual object emitted by the frozen canonical `sitescore-pipeline.build_real_data_pipeline_result()` path.

This distinction is load-bearing because the frozen pipeline factory itself has stronger authority upstream: `build_real_data_pipeline_result()` accepts only the exact canonical `ReadinessEvaluation` produced by the closure-owned readiness factory and performs real-unit lineage coherence checks before returning the terminal DTO.

However, after that return, `RealDataPipelineResult` is only a frozen data DTO. FAZ 4.0 currently treats DTO field consistency as equivalent to pipeline-origin authority.

The current checkpoint test suite demonstrates the bypass directly. `_terminal_shell()` uses `object.__new__(RealDataPipelineResult)` and `object.__new__(ScoringReadinessResult)` to fabricate a detached shell, sets:

```text
status = SCORE_READY
is_score_ready = True
normalized_features = synthetic object
```

and then production `build_application_scoring_input(result)` accepts it and creates a canonical app scoring capability.

The fact that `_terminal_shell()` is test-local does not make this safe: the production factory has no way to distinguish that shell from an actual pipeline-produced terminal object. Any ordinary Python caller can reproduce the same public object construction/bypass.

Therefore this checkpoint does not yet satisfy its required invariant:

```text
actual bound pipeline artifact -> application scoring permission
```

Instead it currently permits:

```text
caller-authored terminal DTO fields -> application scoring permission
```

That is a scoring-authority escalation.

## Required correction

Harden the application boundary so canonical `ApplicationScoringInput` can be produced only through a path that proves actual frozen pipeline authority, not merely a structurally plausible `RealDataPipelineResult` DTO.

Preferred additive direction, without mutating frozen FAZ 3:

- make the app-owned capability factory itself invoke/own the canonical frozen pipeline terminal construction path using the exact canonical upstream `ReadinessEvaluation`/required inputs, then immediately bind the returned terminal object; or
- introduce an app-owned execution/result envelope created at the point where FAZ 4 invokes the frozen pipeline factory, and require that exact app-owned envelope/capability for later scoring admission; or
- another additive design that constructively proves the terminal result passed the frozen canonical pipeline factory rather than trusting detached DTO fields.

Do not fix this with:

- another reproducible hash;
- an importable sentinel/token;
- underscore naming;
- a caller boolean such as `trusted=True`;
- checking only `pipeline_version`, readiness fingerprint, status, reason codes, or DTO field equality;
- accepting `ApplicationScoringEligibility(ELIGIBLE)` as authority.

If you conclude there is no additive FAZ 4 solution and the only correct design requires changing frozen `sitescore-pipeline` to expose/register terminal canonical authority, STOP before modifying it and report:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with exact evidence. Do not mutate frozen FAZ 3 under this hardening instruction without reviewer/user protocol.

## Required adversarial regressions

Add tests proving an ordinary caller cannot obtain canonical `ApplicationScoringInput` from:

1. `object.__new__(RealDataPipelineResult)` with synthetic SCORE_READY fields;
2. a directly constructed/forged `ScoringReadinessResult(is_score_ready=True)` surface;
3. a semantically matching copied/reconstructed terminal DTO that did not pass through the canonical frozen pipeline factory;
4. detached readiness fingerprint/status/normalized feature fields alone.

Retain tests proving actual canonical pipeline-origin input can be admitted once such a path exists. If current frozen empirical truth cannot naturally produce SCORE_READY, use a controlled construction path that preserves canonical authority semantics rather than weakening production gating.

---

# 4. SCOPE / SIBLING REQUIREMENTS

While fixing APP-H001, preserve all clean 4.0 behavior:

- additive `sitescore-app` ownership;
- frozen FAZ 3 remains unchanged unless `CONTRACT_CHANGE_REQUIRED=1` is first reported and reviewed;
- no reverse dependency/cycle;
- NOT_SCORE_READY and PIPELINE_ERROR fail closed;
- no partial-feature scoring;
- no missing -> zero or generic neutral 50;
- SCORE_READY != SCORED;
- no production category aggregation or core invocation;
- no copied core weights/dealbreakers/thresholds;
- no HTTP/API/auth/payment/report/UI/queue/deployment work;
- no empirical gate invention.

Do not broaden into FAZ 4.1.

---

# 5. VALIDATION / RETURN REQUIREMENTS

Keep work on the same branch and PR #8.

After hardening:

1. run `sitescore-app`, pipeline, benchmarks, metrics, spatial, providers, data and core suites;
2. add explicit APP-H001 adversarial tests;
3. update checkpoint docs to describe the true authority boundary;
4. remove any temporary validation workflow before final review and prove validated SHA -> final HEAD is workflow-removal-only (or exact tree-neutral equivalent);
5. replace `implementer.md` with detailed hardening evidence.

Return with:

```text
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.0
IMPLEMENTER_STATE: READY_FOR_REVIEW
PR: #8
CODE_HEAD_SHA: <new exact SHA>
APP-H001: RESOLVED / unresolved with evidence
CONTRACT_CHANGE_REQUIRED: 0 or exact justified 1
```

Do not merge. Do not self-LOCK. Do not start FAZ 4.1.
