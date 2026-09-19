# FAZ 4.0 — Application / Backend Boundary Foundation

## Status

```text
BASE_MAIN_SHA: b2906b9cc1b8e4bf3c17f6d3801753bc89c581cf
FAZ_3_STATUS: FROZEN
PACKAGE: sitescore-app==0.1.0
CONTRACT_CHANGE_REQUIRED: 0
APP-H001: RESOLVED
SCOPE: APPLICATION DOMAIN BOUNDARY ONLY
```

This checkpoint is additive. It does not mutate the frozen FAZ 3 packages and does not declare FAZ 4 complete.

## Ownership

`sitescore-app` owns the application transition from frozen pipeline execution toward future category/core scoring. At 4.0 it establishes only the fail-closed execution-origin and scoring-input boundary. It does not aggregate categories or call the core.

## Runtime dependency direction

Current 4.0 dependencies are intentionally minimal:

```text
sitescore-app
  -> sitescore-data==0.1.0
  -> sitescore-pipeline==0.1.0
```

`sitescore-core` was inspected as the future scoring authority but is not yet a runtime dependency because 4.0 contains no production scoring adapter/call. No frozen upstream package imports `sitescore_app`; no reverse dependency is introduced.

## Frozen interfaces inspected

### sitescore-data

Actual frozen source was inspected for `RealDataPipelineResult`, `PipelineStatus`, `ScoringReadinessResult`, `NormalizedLocationFeatures`, `ReadyCategoryScorePayload`, and `SectorKey`.

`RealDataPipelineResult` validates terminal field consistency and explicitly preserves `SCORE_READY != SCORED`. However, it is a data DTO, not proof that the frozen canonical pipeline factory produced an instance. This distinction is now treated as load-bearing.

`ReadyCategoryScorePayload` validates four already-computed category values DTO-locally; it does not derive or prove them and is not production scoring authority in 4.0.

### sitescore-pipeline

Actual frozen source was inspected for canonical normalized assembly/readiness/terminal builders. The frozen `build_real_data_pipeline_result()` requires the exact closure-owned `ReadinessEvaluation` returned by canonical `derive_scoring_readiness()` and performs overlapping real-unit lineage coherence before emitting the terminal DTO.

### sitescore-core

Actual source was inspected for `CategoryScores`, `analyze(data: AnalysisInput) -> CanonicalAnalysisResult`, `Sector` / `Category`, `SECTOR_CATEGORY_WEIGHTS`, and `DEALBREAKERS` / `DealbreakerRule`. These remain canonical core authorities. 4.0 copies none of their constants and does not invoke `analyze()`.

## APP-H001 authority hardening

The first review found that a caller-fabricated `RealDataPipelineResult` shell with `status=SCORE_READY`, forged readiness true, and synthetic normalized features could satisfy shape-only gate evaluation. That DTO consistency is not sufficient production authority.

The corrected design introduces a separate app-owned execution proof:

```text
canonical frozen ReadinessEvaluation
    -> sitescore-app build_application_pipeline_result(...)
    -> closure-captured frozen sitescore-pipeline build_real_data_pipeline_result(...)
    -> exact returned RealDataPipelineResult
    -> factory-owned ApplicationPipelineResult
    -> build_application_scoring_input(ApplicationPipelineResult)
```

`ApplicationPipelineResult` is immutable, direct-constructor-disabled, and factory-owned through closure-private registry state. Its factory itself invokes the exact frozen terminal builder. The frozen builder therefore remains responsible for canonical readiness authority and real-unit coherence before the app can register an execution result.

`build_application_scoring_input()` no longer accepts a raw `RealDataPipelineResult`. It accepts only the exact factory-owned `ApplicationPipelineResult`. A manually allocated wrapper, copied/reconstructed terminal DTO, forged `ScoringReadinessResult`, detached readiness fingerprint/status/features, or raw SCORE_READY DTO cannot grant scoring permission.

The frozen terminal factory reference is captured inside the app factory installer closure and no module-global token/sentinel/hash/trust boolean is used as authority.

`evaluate_application_scoring_gate()` remains a descriptive terminal-state classifier only. It is intentionally **not** an authorization mechanism: even a fabricated DTO that looks eligible cannot be promoted into `ApplicationScoringInput` without app-owned canonical execution provenance.

## Readiness gate

After canonical execution-origin authority is proven, scoring eligibility still requires:

```text
status == SCORE_READY
AND
scoring_readiness is ScoringReadinessResult
AND
scoring_readiness.is_score_ready is True
AND
normalized_features is NormalizedLocationFeatures
```

`NOT_SCORE_READY` and `PIPELINE_ERROR` remain fail-closed. No `ready=True`, `force=True`, `skip_readiness=True`, detached readiness fingerprint, caller status, category score, or Location Score authorization parameter exists.

Current frozen empirical truth may legitimately remain `NOT_SCORE_READY` because COMB-005 and other empirical gates remain unresolved. 4.0 does not fabricate a production SCORE_READY path merely to exercise a happy path.

## SCORE_READY != SCORED

`ApplicationScoringInput` means only that a later application scoring stage is permitted to begin. It contains no category values and is not a scored result. No scored output is written back into frozen pipeline/data DTOs.

## No partial scoring / hidden neutralization

4.0 does not fill missing features with zero, apply generic neutral 50, renormalize around missing inputs, manufacture COMB-005 output, invent empirical/calibration values, construct `CategoryScores`, construct `ReadyCategoryScorePayload`, or call `sitescore-core analyze()`.

## Adversarial regressions

Tests explicitly prove that canonical application scoring authority cannot be obtained from:

1. `object.__new__(RealDataPipelineResult)` with synthetic SCORE_READY fields;
2. forged/direct readiness surfaces;
3. copied/reconstructed terminal DTOs;
4. detached status/readiness fingerprint/normalized feature fields;
5. manually allocated `ApplicationPipelineResult` or `ApplicationScoringInput` shells.

They also verify the app-owned pipeline factory delegates into the frozen canonical terminal factory, which rejects noncanonical `ReadinessEvaluation` before app registration can occur.

## Explicitly out of scope

No HTTP/API framework or endpoint, auth/account flow, payment/Stripe, webhook, report/PDF renderer, UI/frontend, email delivery, queue, n8n/commercial automation, deployment, category aggregation, Location Score orchestration, Decision Layer execution, or financial orchestration is introduced.

## Next checkpoint boundary

A later Reviewer-authorized FAZ 4 checkpoint may implement category aggregation/core adaptation. It must consume the factory-owned application scoring capability, use frozen core/config authorities rather than duplicate constants, and preserve Location/Financial separation. 4.0 stops before that work.

## Validation

Validation runs `sitescore-app` plus all seven frozen FAZ 3 package suites. Exact run/SHAs and directly visible counts are recorded in the PR/handoff. Any temporary validation workflow is removed before final review, with validated SHA -> final review HEAD provenance recorded exactly.
