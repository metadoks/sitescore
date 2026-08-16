# SiteScore AI — Authority Corrective Reopen: Pipeline / App

## Status

This record documents the user-authorized narrow corrective reopen for:

- `PIPE-AUTH-H001`
- `APP-H002`

The historical FAZ 4.0 LOCK / merge remains factual. The authority defect was discovered later during FAZ 4.1 pre-implementation inspection; this record does not rewrite that history.

```text
FAZ 3: FROZEN, except the explicitly authorized narrow pipeline authority correction below
FAZ 4.0: HISTORICALLY LOCKED / MERGED
FAZ 4.1: NOT STARTED
USER_REOPEN_AUTHORIZED: YES
CONTRACT_CHANGE_REQUIRED: 1
```

## Authorized scope

Production source changes are limited to:

```text
sitescore-pipeline/src/sitescore_pipeline/integration.py
sitescore-app/src/sitescore_app/gating.py
```

Associated adversarial tests and this corrective record are additive.

No changes are authorized or made to scoring math, normalization math, benchmark math, provider semantics, spatial semantics, metrics semantics, data contracts, core weights, dealbreakers, empirical calibration, HTTP/API, payment, report/PDF, UI, n8n, or FAZ 4.1 category aggregation.

## Root cause

The inherited implementation treated registered Python object identity as sufficient execution authority. Under the repository's adversarial model, `dataclass(frozen=True)` does not prevent `object.__setattr__` from mutating a registered instance after construction.

The corrected rule is:

```text
factory origin
+ construction-time trusted binding
+ post-registration integrity verification
= canonical execution authority
```

Object identity, caller-visible booleans, and reconstructable hashes are not sufficient on their own.

## PIPE-AUTH-H001 correction

`sitescore-pipeline` now keeps closure-private construction-time bindings inside `_install_canonical_factories()`.

For every canonical `NormalizedFeatureAssembly`, the binding retains the construction-time authority payload:

```text
features
direct_results
feature_policies
compatibility
approved_fallback_policies
artifact_identities
assembly_id
semantic authority attestation
```

Canonical resolution requires both:

1. exact registered object identity; and
2. integrity of current public fields against the construction-time binding.

The semantic attestation is recomputed so nested semantic mutation is detected, including mutation inside normalized feature values.

For every canonical `ReadinessEvaluation`, closure-private state binds:

```text
exact assembly object
exact ScoringReadinessResult object
readiness-result semantic attestation
```

Replacement of `assembly` or `result`, or semantic mutation of the readiness result such as changing `is_score_ready`, fails closed.

Readiness derivation and terminal construction consume closure-resolved construction-time values. They do not perform a canonical check and then continue using caller-mutated public fields as authority.

## APP-H002 correction

`sitescore-app` now keeps closure-private construction-time bindings inside `_install_application_factories()`.

Bindings are:

```text
ApplicationPipelineResult
-> exact construction-time RealDataPipelineResult

ApplicationScoringInput
-> exact construction-time ApplicationPipelineResult
```

The wrapper reference is weakly held for registry cleanup while the bound authority object is retained privately.

`require_canonical_application_pipeline_result(...)` verifies:

- registered wrapper identity; and
- `.pipeline_result is` the exact construction-time terminal.

`require_canonical_application_scoring_input(...)` verifies:

- registered scoring-input identity;
- `.application_pipeline_result is` the exact construction-time wrapper; and
- the nested application wrapper still resolves as canonical.

`build_application_scoring_input(...)` makes its eligibility decision from the closure-resolved trusted terminal rather than the mutable public wrapper attribute.

## Adversarial regression matrix

The corrective tests exercise `object.__setattr__` directly.

Pipeline regressions prove rejection of post-registration replacement/mutation of:

- `assembly.features`
- `assembly.direct_results`
- `assembly.feature_policies`
- `assembly.compatibility`
- `assembly.approved_fallback_policies`
- `assembly.artifact_identities`
- `assembly.assembly_id`
- `readiness.assembly`
- `readiness.result`
- nested `readiness.result.is_score_ready`
- nested forged numeric `road_parking_access_score`

Existing copied/reconstructed authority-object regressions remain in place. The unmodified canonical path preserves current production truth: COMB-005 remains unavailable and the tested terminal remains `NOT_SCORE_READY`.

App regressions prove rejection of:

- redirected `ApplicationPipelineResult.pipeline_result`
- redirected `ApplicationScoringInput.application_pipeline_result`
- manual/copy-equivalent wrapper authority
- raw forged terminal DTOs
- caller-controlled ready/trusted/force/status/fingerprint/features authority parameters

The unmodified canonical wrapper path remains valid.

## Version and semantic governance

Public factory signatures remain stable and package versions remain `0.1.0`.

```text
SCORING_MATH_CHANGED: NO
NORMALIZATION_MATH_CHANGED: NO
COMB005_STATE_CHANGED: NO
EMPIRICAL_GATE_CHANGED: NO
FAZ_4_1_IMPLEMENTATION_STARTED: NO
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
```

## Validation

An initial successful full-regression execution applied the exact corrective transform in its workspace and then committed that tested source as:

```text
source commit: 9c4f80da4385771848d0b3fd3b4b296470b8c152
workflow: authority-corrective-validation
run: 31943607498
conclusion: SUCCESS
sitescore-app: 12 PASS
sitescore-pipeline: 53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics: 67 PASS
sitescore-spatial: PASS
sitescore-providers: PASS
sitescore-data: PASS
sitescore-core: PASS
```

A prior bootstrap run (`31943413778`) failed at workflow parsing before any job or source correction executed. It is superseded and is not validation evidence.

Before Reviewer handoff, a validation-only workflow is run on the final source/tests/docs candidate SHA. That final run and the exact validated-SHA-to-final-HEAD workflow-removal comparison are recorded in `implementer.md`.

## Relock requirement

This corrective reopen does not self-LOCK and does not merge itself. Independent Reviewer verification remains required. Any merge/relock transition remains user-authorized only.

FAZ 4.1 remains explicitly NOT STARTED.
