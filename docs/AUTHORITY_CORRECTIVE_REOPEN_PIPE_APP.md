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

`sitescore-pipeline` keeps closure-private construction-time bindings inside `_install_canonical_factories()`.

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

Canonical resolution requires both exact registered object identity and integrity of current public fields against the construction-time binding. The semantic attestation detects nested semantic mutation, including mutation inside normalized feature values.

For every canonical `ReadinessEvaluation`, closure-private state binds the exact assembly object, exact `ScoringReadinessResult` object, and readiness-result semantic attestation. Replacement of `assembly` or `result`, or semantic mutation such as changing `is_score_ready`, fails closed.

Readiness derivation and terminal construction consume closure-resolved construction-time values rather than caller-mutated public fields.

## APP-H002 correction

`sitescore-app` keeps closure-private construction-time bindings inside `_install_application_factories()`.

The app binding now covers both object origin and authority semantics. `ApplicationPipelineResult` binds:

```text
exact construction-time RealDataPipelineResult
construction-time PipelineStatus
construction-time SectorKey
construction-time NormalizedLocationFeatures authority surface
construction-time ScoringReadinessResult authority surface
construction-time readiness fingerprint
closure-private recursive semantic record for the authority surface
```

Canonical resolution therefore requires:

1. exact registered wrapper identity;
2. `.pipeline_result is` the exact construction-time terminal; and
3. the current terminal status/sector/features/readiness semantic record exactly matches its construction-time record.

This closes `APP-H002-R001`: retaining the same exact `RealDataPipelineResult` object no longer preserves authority if the caller mutates its status, sector, normalized feature semantics, readiness flag, or readiness fingerprint with `object.__setattr__`.

`build_application_scoring_input(...)` authorizes from the verified construction-time binding rather than reading mutable live terminal state after a wrapper check.

`ApplicationScoringInput` additionally binds the exact accepted application wrapper, exact terminal, authority record, sector, normalized feature object, and readiness fingerprint. Its canonical resolver revalidates the underlying application binding on every authority access.

The public capability properties:

```text
pipeline_result
sector_key
normalized_features
readiness_fingerprint
```

are installed from closure-captured resolvers. After any post-registration authority mutation, these properties fail closed instead of dynamically traversing and exposing redirected/mutated public state.

No caller-visible hash, boolean, registry, resolver, or token grants authority.

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
- same-terminal `NOT_SCORE_READY -> SCORE_READY` status mutation
- same-readiness `is_score_ready: False -> True` mutation
- same-feature-surface forged numeric/calibrated/eligible `road_parking_access_score`
- same-terminal sector mutation
- same-readiness readiness-fingerprint mutation
- mutation after a legitimate controlled scoring input has been granted
- capability-property access after post-registration authority mutation
- manual/copy-equivalent wrapper authority
- raw forged terminal DTOs
- caller-controlled ready/trusted/force/status/fingerprint/features authority parameters

Existing different-object redirect protection remains intact.

## COMB-005 firewall

The corrective reopen does not modify COMB-005 policy, approval registry, weights, composition semantics, or current production truth.

```text
COMB-005: NOT_APPROVED
approved registry: empty
weights: empty
road_parking_access_score: unavailable / nonnumeric in current production truth
```

No missingness fallback, neutral score, replacement weight, implicit approval, or empirical calibration is introduced.

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

## Validation governance

A validation-only GitHub Actions workflow is used to run the full package regression and corrective scope audit. The final source/tests/docs candidate SHA and Actions run are recorded in `implementer.md` after success. The temporary workflow is then removed, and the validated-SHA-to-final-HEAD comparison must show workflow removal only.

Historical earlier validation evidence remains useful for the first corrective pass but is superseded for APP-H002-R001 by the fresh hardening validation.

## Relock requirement

This corrective reopen does not self-LOCK and does not merge itself. Independent Reviewer verification remains required. Any merge/relock transition remains user-authorized only.

FAZ 4.1 remains explicitly NOT STARTED.
