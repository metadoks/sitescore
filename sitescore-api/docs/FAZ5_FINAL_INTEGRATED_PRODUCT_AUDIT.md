# FAZ 5-FINAL — Integrated Product Interface / Report Audit

## Audit status

Checkpoint: `5-FINAL`

Authoritative base:

```text
main@8f757b81c0cb69e5e6be62f45e94ff9a57432cca
```

Branch:

```text
faz5/5-final-integrated-product-audit
```

Purpose: integrated FAZ 5 freeze-readiness audit only. This checkpoint does not add a new product subsystem and does not start FAZ 6.

> Mathematically validated scoring engine; empirical validation pending.

## Integrated chain audited

The approved product-facing chain remains:

```text
external request
-> /v1 API
-> Bearer authentication / scopes
-> idempotent PostgreSQL acceptance
-> PostgreSQL outbox
-> Celery worker
-> canonical acquisition + frozen readiness/application analysis
-> CanonicalCompletedOutcome | CanonicalNotScoreReadyOutcome
-> canonical report facts
-> ReportDomainModel
-> ValidatedReportNarrative
-> deterministic presentation policy
-> HTML/CSS + charts
-> PDF rendering
-> private S3-compatible object
-> PostgreSQL report resource
-> authenticated report metadata/content API
```

No alternate analytical or report-authority chain was found or introduced by 5-FINAL.

## Authority findings

### External/API boundary

- `/v1` routes remain transport/resource orchestration only.
- Route code contains no scoring formula implementation.
- Caller JSON cannot provide trusted score, confidence, decision, financial, provenance, storage-key, report-hash or canonical-result authority.
- `POST /v1/reports` remains resolver-only and does not rerun analysis or reconstruct authority from `AnalysisModel.result_body`.
- Analysis/report UUIDs and fingerprints are resource identities/evidence, not canonical object authority.

### Worker/canonical analysis boundary

- Worker remains the only execution bridge into `CanonicalAnalysisExecutor`.
- Production acquisition remains server-owned through the locked canonical deployment/provider chain.
- `CanonicalCompletedOutcome` requires genuine canonical application authority.
- `CanonicalNotScoreReadyOutcome` remains distinct from scored success.
- Missing/unavailable/uncalibrated semantics are not rewritten to zero/bad/calibrated by API/report layers.

### Report boundary

The report chain remains identity-bound:

```text
live CanonicalCompletedOutcome
-> exact factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
-> ValidatedReportNarrative
-> PresentationPolicy
-> PDF
-> PreparedReportArtifact
```

The report package does not import `sitescore_api`; the API consumes the locked report package directionally. Report rendering/narrative/presentation layers do not become scoring authority.

## Durable lifecycle / artifact findings

The locked invariants remain:

- PostgreSQL is durable lifecycle, idempotency and report-metadata truth.
- Redis/Celery are execution transport only; Celery result backend is disabled.
- terminal analysis states are immutable;
- worker execution and timeout publication coordinate on one server-derived PostgreSQL advisory-lock key;
- genuine pre-deadline canonical success is protected during report finalization by `canonical_success_at`, which is coordination evidence only;
- `analysis=completed` is paired with exactly one terminal current report resource;
- report state is closed `ready|failed`;
- different-report-id conflicts fail the actual `(analysis_id, report_artifact_version)` resource closed;
- ambiguous commit handling reconciles fresh PostgreSQL truth before destructive object compensation;
- report-ready content is bound to exact SHA-256, byte length, MIME and PDF signature expectations;
- report failure does not falsify genuine analytical success.

## API / security / consumer findings

Expected runtime surface remains exactly:

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

Supported service scopes remain exactly:

```text
analysis:write
analysis:read
report:write
report:read
```

The integrated audit preserves:

- Bearer service-key authentication;
- authenticated consumer ownership isolation;
- foreign/missing resource non-disclosure behavior;
- `Idempotency-Key + canonical request hash + PostgreSQL uniqueness`;
- server-generated analysis/report IDs;
- separate request correlation ID;
- sanitized machine errors;
- OpenAPI/runtime route agreement;
- polling-only V1;
- no callback/webhook delivery;
- no cancellation contract.

## Infrastructure / migration findings

Final schema chain remains:

```text
0001_faz5_1
-> 0002_faz5_5
-> 0003_faz5_5
```

Locked runtime requirements to re-prove in exact-head validation:

- PostgreSQL 16 migration on fresh DB;
- private S3-compatible PUT/HEAD/GET/DELETE with no public ACL;
- real Redis broker;
- real Celery worker;
- `task_acks_late=True`;
- `task_reject_on_worker_lost=True`;
- disabled Celery result backend;
- real timeout reconciliation task;
- exact pinned package versions.

## Narrative / visual / PDF findings

Locked `sitescore-report==0.3.0` remains the sole report rendering package consumed by the API.

The 5-FINAL audit accepts the previously locked report invariants and re-runs the full report suite:

- canonical numeric facts are projected, not recomputed;
- narrative claims remain typed/validated and cannot author independent scoring truth;
- deterministic fallback uses the same validated narrative contract;
- tables/charts/presentation do not recompute analytical semantics;
- missing/unavailable values remain distinct from zero/bad;
- score/decision/confidence/financial truth remains analysis/report-provenance bound;
- PDF bytes remain bound to exact durable metadata;
- report/narrative/presentation/template/renderer versions remain persisted.

## Automation consumer handoff

Repository durable consumer contract:

```text
AUTOMATION_CONSUMER_HANDOFF.md
```

It explicitly records that:

```text
n8n is an orchestration consumer, not scoring/report truth authority.
FAZ 5 does not contain the production n8n workflow itself.
```

The document covers endpoints, auth/scopes, IDs, lifecycle, idempotency, uncertain POST retry, polling/Retry-After, report resolution/content, ownership/non-disclosure, integrity expectations, current COMB-005 limitation and future-orchestration authority boundaries.

## Scope exclusions verified

5-FINAL does not implement:

```text
payment / Stripe
production n8n workflow
email delivery
commercial order state
frontend account flow
callback/webhook execution
FAZ 6
```

## Implementer audit conclusion

At audit-authoring time no integrated blocker requiring frozen FAZ 3/4 semantic reopen or fixed FAZ 5 architecture change was identified.

Therefore Implementer-side flags remain intended as:

```text
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
```

This conclusion is not a freeze decision. Exact-head CI must pass, Implementer must hand off the exact candidate, Reviewer must independently review it, and only a literal user `LOCK` may authorize final merge/freeze.