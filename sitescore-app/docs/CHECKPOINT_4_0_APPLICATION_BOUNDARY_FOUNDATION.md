# FAZ 4.0 — Application / Backend Boundary Foundation

## Status

```text
BASE_MAIN_SHA: b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
FAZ_3_STATUS: FROZEN
PACKAGE: sitescore-app==0.1.0
CONTRACT_CHANGE_REQUIRED: 0
SCOPE: APPLICATION DOMAIN BOUNDARY ONLY
```

This checkpoint is additive. It does not mutate the frozen FAZ 3 packages and does not declare FAZ 4 complete.

## Ownership

`sitescore-app` owns the application transition from a frozen terminal `RealDataPipelineResult` toward future category/core scoring. At 4.0 it establishes only the fail-closed scoring-input boundary. It does not aggregate categories or call the core.

## Runtime dependency direction

Current 4.0 dependencies are intentionally minimal:

```text
sitescore-app
  -> sitescore-data==0.1.0
  -> sitescore-pipeline==0.1.0
```

`sitescore-core` was inspected as the future scoring authority but is not yet a runtime dependency because 4.0 contains no production scoring adapter/call. A later reviewed checkpoint may add the direct core dependency when the adapter actually needs it.

No frozen upstream package imports `sitescore_app`; no reverse dependency is introduced.

## Frozen interfaces inspected

### sitescore-data

Actual current source was inspected for:

- `RealDataPipelineResult`
- `PipelineStatus`
- `ScoringReadinessResult`
- `NormalizedLocationFeatures`
- `ReadyCategoryScorePayload`
- `SectorKey`

`RealDataPipelineResult` explicitly states `SCORE_READY != SCORED` and validates that `SCORE_READY` requires a non-null readiness result with `is_score_ready=True` plus normalized features. `NOT_SCORE_READY` requires readiness false. `PIPELINE_ERROR` must not carry readiness.

`ReadyCategoryScorePayload` is a DTO-local validation surface for four already-computed category values; it does not compute or prove their application derivation. For that reason it is not treated as scoring authority in 4.0.

### sitescore-pipeline

The package exports the canonical normalized assembly/readiness/terminal builders. 4.0 consumes the frozen terminal result boundary rather than reaching behind the pipeline into providers, metrics, spatial, or benchmark internals.

### sitescore-core

Actual source was inspected for:

- `CategoryScores` in `sitescore.schemas.location`;
- `analyze(data: AnalysisInput) -> CanonicalAnalysisResult`;
- `Sector` / `Category`;
- `SECTOR_CATEGORY_WEIGHTS`;
- `DEALBREAKERS` / `DealbreakerRule`.

These remain canonical core authorities. 4.0 copies none of their constants and does not invoke `analyze()`.

## Readiness gate

Application scoring eligibility is derived only from the actual terminal pipeline result:

```text
status == SCORE_READY
AND
scoring_readiness is ScoringReadinessResult
AND
scoring_readiness.is_score_ready is True
AND
normalized_features is NormalizedLocationFeatures
```

`NOT_SCORE_READY` and `PIPELINE_ERROR` fail closed. Inconsistent forged terminal shells also fail closed. No `ready=True`, `force=True`, `skip_readiness=True`, detached readiness fingerprint, or caller status parameter exists on the production scoring-input factory.

## Authority boundary

`ApplicationScoringInput` is immutable, non-directly-constructible, factory-owned, and retains the exact `RealDataPipelineResult` object rather than copying detached scores/IDs. A closure-private weak registry distinguishes factory-issued capability objects from manual shells. Future scoring adapters must call `require_canonical_application_scoring_input` before consuming one.

This capability means only **application scoring is permitted to begin**. It contains no category values and is not a scored result.

## No partial scoring / hidden neutralization

4.0 does not:

- fill missing normalized features with zero;
- apply generic neutral 50;
- renormalize around missing inputs;
- manufacture COMB-005 output;
- invent empirical/calibration values;
- construct `CategoryScores`;
- construct `ReadyCategoryScorePayload`;
- call `sitescore-core analyze()`.

Current canonical production may legitimately remain `NOT_SCORE_READY` because FAZ 3 empirical gates are intentionally unresolved.

## Explicitly out of scope

No HTTP/API framework or endpoint, auth/account flow, payment/Stripe, webhook, report/PDF renderer, UI/frontend, email delivery, queue, n8n/commercial automation, deployment, category aggregation, Location Score orchestration, Decision Layer execution, or financial orchestration is introduced.

## Next checkpoint boundary

A later Reviewer-authorized FAZ 4 checkpoint may implement category aggregation/core adaptation. It must consume this readiness capability, use frozen core/config authorities rather than duplicate constants, and preserve the Location/Financial separation. 4.0 itself stops before that work.

## Validation

Validation must run `sitescore-app` plus all seven frozen FAZ 3 package suites. Exact run/SHAs and directly visible counts are recorded in the PR/handoff after validation. Temporary validation workflow, if used, is removed before review.
