# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6-FINAL
CHECKPOINT_TITLE: Integrated Commerce Audit + Final Freeze Candidate

REVIEWER_STATE: IMPLEMENTATION_AUTHORIZED
IMPLEMENTER_ACTION: RESUME_6_FINAL
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: df4e3181712e7f426f8f1752628952a620c98f05
LIVE_MAIN_SHA_AT_RESUME: df4e3181712e7f426f8f1752628952a620c98f05

PREVIOUS_FINAL_PR: #29
PREVIOUS_FINAL_HEAD: 1adce96b9645dc572c6819e1f782fd30ae83da91
PREVIOUS_FINAL_MERGE_BASE: 287367ce8eb708efce0ebae0a2f9c90d681cce01
PREVIOUS_FINAL_RELATION_TO_NEW_MAIN: DIVERGED
PREVIOUS_FINAL_ACTION: REBASE_OR_RECREATE_FROM_EXACT_NEW_MAIN_BEFORE_REVIEW

CORRECTIVE_PR: #30
CORRECTIVE_REVIEWED_HEAD: 813e3436bc3f899a774c853a6a81ba7924b54c42
CORRECTIVE_MERGE_COMMIT: df4e3181712e7f426f8f1752628952a620c98f05
CORRECTIVE_LOCK_STATE: LOCKED

COMMERCE_VERSION: 0.6.0
MIGRATION_HEAD: 0005_recovery_reconciliation
N8N_RUNTIME_VERSION: 2.33.4
N8N_VALIDATED_IMAGE_DIGEST: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
LOCKED_ORDER_WORKFLOW_SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
RECOVERY_SCHEDULE_WORKFLOW_SHA256: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c

FIN6-H001: RESOLVED
FIN6-H002: RESOLVED_ON_LOCKED_MAIN
BLOCKERS: NONE
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: LOCKED_WITH_CORRECTIVE
FAZ_6_1_STATUS: LOCKED
FAZ_6_2_STATUS: LOCKED
FAZ_6_3_STATUS: LOCKED
FAZ_6_4_STATUS: LOCKED
FAZ_6_5_STATUS: LOCKED
FAZ_6_FINAL_STATUS: IMPLEMENTATION_AUTHORIZED
START_POST_FAZ6: NO
NO_6_6: YES
```

---

# 1. RESUME AUTHORITY

Reviewer resumes FAZ 6-FINAL only after independently verifying the corrective LOCK for PR #30.

Authoritative new final base is exactly:

```text
main@df4e3181712e7f426f8f1752628952a620c98f05
```

This base contains the locked runtime HTTP-surface correction for `FIN6-H002`.

The previous final candidate PR #29 was created from old base:

```text
287367ce8eb708efce0ebae0a2f9c90d681cce01
```

and its current head is:

```text
1adce96b9645dc572c6819e1f782fd30ae83da91
```

Live compare against new main is diverged, with merge-base still the old pre-corrective main. Therefore PR #29 in its current state is NOT lock-eligible and MUST NOT be merged.

Implementer may either:

1. rebuild/rebase the existing final branch so its effective base/ancestry is exact new locked main and PR #29 becomes a clean audit-only candidate; or
2. close/replace PR #29 with a fresh final branch/PR created from exact new locked main.

Whichever path is chosen, the final review candidate must have a clean permanent diff against `df4e3181712e7f426f8f1752628952a620c98f05` and must receive fresh exact-head validation.

---

# 2. FINAL CHECKPOINT PURPOSE

FAZ 6-FINAL is an integrated audit and freeze checkpoint, not a new feature checkpoint.

No new commerce capability, authority path, state transition, endpoint, migration, dependency, n8n behavior, provider behavior, or post-FAZ6 feature may be introduced.

The final checkpoint must prove that the complete locked FAZ 6 system is internally coherent as one production commerce chain:

```text
purchase intent
-> durable order/catalog snapshot
-> Stripe Checkout
-> verified Stripe payment authority
-> durable paid order
-> exactly-one durable order.paid.v1 identity
-> outbox dispatch
-> n8n bounded orchestration
-> frozen SiteScore /v1 analysis/report truth
-> secure delivery grant + Postmark evidence
-> fulfilled
```

and the canonical unfulfillable path:

```text
paid
-> authoritative SiteScore not_score_ready / failed / timed_out
   OR authoritative report failed
-> fresh server-side proof
-> exact full Stripe refund
-> durable refunded state
```

Recovery/reconciliation must converge those same authorities without synthetic Stripe evidence, duplicate money movement, false fulfillment, identity replacement, or bypass of frozen SiteScore truth.

---

# 3. PERMITTED PERMANENT FINAL DIFF

The final candidate remains audit/freeze-only.

Expected permanent files are limited to:

```text
sitescore-commerce/docs/FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md
sitescore-commerce/tests/test_faz6_final_freeze_gate.py
```

The existing corrective production files are already part of `main`; they are NOT final-PR changes:

```text
sitescore-commerce/src/sitescore_commerce/api.py
sitescore-commerce/tests/test_runtime_http_surface.py
```

The final audit/freeze artifacts may be revised to incorporate the corrective lock evidence.

Temporary exact-head validation workflows under `.github/workflows/` are permitted for validation only and must be removed before READY_FOR_REVIEW unless repository policy requires otherwise.

Any new permanent production/runtime/migration/dependency/n8n change discovered to be necessary during final audit is NOT authorized inside 6-FINAL. STOP and report it for Reviewer decision.

---

# 4. MANDATORY FINAL FREEZE INVARIANTS

The final freeze gate and audit artifact must cover the integrated locked system, including at minimum:

## 4.1 Commerce/order/catalog

- immutable order purchase-intent snapshot/hash lineage;
- catalog/product/price/currency/amount authority;
- Checkout Session/order binding;
- idempotent order creation and Checkout operation identity;
- no client redirect as payment authority.

## 4.2 Stripe payment authority

- official Stripe signature verification and bounded webhook body;
- verified event identity semantics independent of raw-body serialization;
- fresh server-side Checkout/PaymentIntent reconciliation;
- paid requires exact complete + paid + non-empty PaymentIntent + livemode/catalog coherence;
- webhook-first and recovery paths converge to the same durable paid authority;
- no synthetic event, fake `evt_*`, polling receipt impersonation, or arbitrary payment mutation.

## 4.3 Outbox / fulfillment

- paid transition and `order.paid.v1` outbox identity remain atomic;
- replay never replaces original outbox identity/occurred-at authority;
- SiteScore analysis/report bindings remain stable and cross-service only through frozen `/v1` API;
- n8n never becomes scoring, readiness, analysis, report, refund, or delivery truth.

## 4.4 Refund money safety

- refund eligibility is based only on fresh authoritative SiteScore failure/not-ready proof;
- refund is full/exact for the original received amount/currency;
- Stripe refund response-loss reconciliation converges without duplicate refund;
- contradictory/missing Stripe authority fails closed to attention, not money movement.

## 4.5 Delivery / email

- raw delivery token is never persisted/logged/provider-metadata exposed;
- only token digest persists;
- delivery route revalidates payment/binding/report/content authority and proxies bytes rather than redirecting to private storage;
- report content integrity/ownership requirements remain enforced;
- Postmark HTTP success without complete accepted evidence cannot mark fulfillment;
- provider uncertainty cannot create false fulfilled state;
- duplicate email risk remains bounded to same report under at-least-once semantics.

## 4.6 Recovery / reconciliation

- lease/fencing and stale-worker protection remain valid;
- legacy pre-0005 Stripe inbox lineage recovery remains structurally correlated and fail-closed;
- paid replay validates durable Stripe paid authority before n8n I/O;
- provider 4xx/429/5xx/timeouts follow the locked attention/retry boundaries;
- crash/restart/replay preserves durable authority and identity.

## 4.7 n8n

Freeze exactly:

```text
runtime version: 2.33.4
image digest: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
order workflow SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery workflow SHA256: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

Prove finite pacing/horizon, restart behavior, duplicate replay convergence, delivery-pending boundary, recovery scheduler single bounded call, and no direct Stripe/SiteScore/Postmark/DB/S3 authority bypass from n8n.

## 4.8 Runtime HTTP surface — corrective invariant now mandatory in final freeze

The final integrated freeze must no longer rely only on source AST extraction.

It must incorporate executable resolved-runtime evidence proving the actual constructed FastAPI application exposes exactly:

```text
POST /v1/orders
POST /v1/webhooks/stripe
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
GET  /d/{opaque_token}
```

and no additional HTTP route.

At minimum final validation must execute the permanent runtime regression on new locked main and prove:

```text
/openapi.json absent
/docs absent
/redoc absent
/docs/oauth2-redirect absent
resolved app.routes == exact authorized seven-route set
```

The AST fail-closed registration gate from FIN6-H001 may remain as defense-in-depth, but it is not sufficient by itself.

## 4.9 Frozen boundaries / security

- `sitescore-commerce==0.6.0` remains exact;
- migration head remains `0005_recovery_reconciliation`;
- no frozen FAZ 3/4/5 source mutation;
- frozen SiteScore API/report contracts remain unchanged;
- no direct commerce writes into frozen API-owned tables;
- no secret/raw token/private storage URL leakage;
- dependency/runtime pin identities remain locked;
- product claim remains exactly: `Mathematically validated scoring engine; empirical validation pending.`
- no empirical business-outcome validation claim;
- no false exactly-once claim where system semantics are at-least-once + idempotent convergence.

---

# 5. REQUIRED ADVERSARIAL / RECOVERY MATRIX

Final audit evidence must cover the already-locked behavior across representative integrated failure paths, including:

```text
A. happy paid -> analysis complete -> report ready -> delivery accepted -> fulfilled
B. duplicate/out-of-order Stripe webhook -> no duplicate paid/outbox
C. missing webhook -> server reconciliation -> paid once
D. legacy verified inbox recovery -> original real event identity resumes
E. unpublished outbox recovery -> same identity published
F. published stale replay -> same durable identity preserved
G. n8n timeout/restart/response-loss -> paced convergence
H. canonical unfulfillable analysis/report -> fresh proof -> full refund
I. Stripe refund response loss -> reconcile existing refund, no duplicate money movement
J. Postmark uncertainty -> no false fulfillment, retry same report
K. delivery token expiry/revocation/ownership/integrity -> fail closed
L. contradictory durable paid authority -> attention and zero n8n I/O
M. stale recovery worker -> lease/fencing prevents stale mutation
N. provider auth/client/rate/server/timeout classes -> locked attention/retry behavior
O. process crash around transactional boundaries -> durable convergence
P. secret/raw-token/private-URL leakage scans -> clean
Q. frozen scope/import/dependency boundaries -> clean
R. migration empty + upgrade/downgrade/re-upgrade through 0005 -> clean
S. frozen /v1 idempotency/report-content integrity -> unchanged
T. runtime HTTP surface -> exact seven routes, framework docs/OpenAPI absent
```

No new production code may be added merely to manufacture these outcomes. Use locked tests/runtime evidence and final freeze tests.

---

# 6. FRESH EXACT-HEAD VALIDATION REQUIRED

All pre-corrective final validation evidence is stale for freeze purposes.

Before READY_FOR_REVIEW, fresh validation must run from the new final candidate based on exact:

```text
df4e3181712e7f426f8f1752628952a620c98f05
```

Required validation includes:

```text
full sitescore-commerce suite PASS
final permanent freeze gate PASS
runtime app.routes exact-seven proof PASS
migration 0001 -> 0005 / downgrade base / re-upgrade PASS
migration head == 0005_recovery_reconciliation
n8n static baseline PASS
locked order n8n 2.33.4 runtime PASS
recovery scheduler runtime PASS
recovery replay convergence PASS
frozen FAZ 3/4/5 total == 1504 PASS
private S3 regression PASS
Redis/Celery transport PASS
frozen scope scan PASS
secret boundary scan PASS
package/workflow/image identity checks PASS
```

Fresh CI must checkout the exact validated final SHA explicitly.

If temporary validation workflows are deleted after validation, validated-SHA -> final-head delta must contain only those workflow removals. No product/runtime/test/audit semantic change is allowed after validated SHA without revalidation.

Record the new Commerce/final test total rather than reusing the stale pre-corrective count.

---

# 7. FINAL AUDIT ARTIFACT / FREEZE CANDIDATE RECORD

`FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md` must be updated to reflect the actual post-corrective integrated state.

At minimum record:

```text
final base SHA = df4e3181712e7f426f8f1752628952a620c98f05
corrective PR #30 merge SHA and FIN6-H002 resolution
commerce version 0.6.0
migration head 0005_recovery_reconciliation
n8n version/image/workflow hashes
resolved runtime exact-seven HTTP surface
all FAZ 6.0-6.5 lock provenance
fresh validated SHA
fresh CI run/job IDs
fresh Commerce/final test count
frozen 1504 baseline
money/state/security/recovery authority summary
empirical-validation disclaimer
all blockers/flags
```

The artifact is a freeze candidate record. It cannot know the eventual final merge commit before user-authorized LOCK; post-LOCK merge identity remains coordination-record authority.

---

# 8. PRODUCTION CHANGE DISCOVERY RULE

FAZ 6-FINAL remains audit-only.

If the fresh final audit finds another defect requiring production/runtime/migration/dependency/n8n semantic change:

1. do NOT patch it inside final audit authority;
2. STOP;
3. record the concrete blocker and affected locked checkpoint in `implementer.md`;
4. Reviewer decides whether `ADDITIONAL_REOPEN_REQUIRED`, `CONTRACT_CHANGE_REQUIRED`, or `DESIGN_DECISION_REVIEW_REQUIRED` is necessary.

No locked checkpoint may be silently rewritten by final audit.

---

# 9. IMPLEMENTER HANDOFF REQUIREMENTS

Implementer must now:

1. start from exact locked `main@df4e3181712e7f426f8f1752628952a620c98f05`;
2. rebase/recreate the FAZ 6-FINAL candidate so old pre-corrective lineage is removed from the active freeze candidate;
3. ensure permanent diff is audit/freeze-only;
4. update final audit/freeze gate for the corrective runtime-surface invariant;
5. run fresh exact-head full validation;
6. remove temporary validation workflows if used;
7. verify validated->final delta is non-semantic cleanup only;
8. write `implementer.md` with exact evidence;
9. STOP at READY_FOR_REVIEW.

Required handoff fields include at least:

```text
CURRENT_CHECKPOINT: 6-FINAL
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
EXPECTED_BASE_SHA: df4e3181712e7f426f8f1752628952a620c98f05
PR: <rebuilt #29 or replacement PR>
FINAL_HEAD_SHA: <exact>
VALIDATED_SHA: <exact>
FINAL_BASE_ANCESTRY_VERIFIED: YES
FIN6-H001: RESOLVED
FIN6-H002: RESOLVED
RUNTIME_HTTP_SURFACE: EXACT_7_ROUTES_PASS
BLOCKERS: NONE
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
USER_LOCK_AUTHORIZED: NO
START_POST_FAZ6: NO
```

Do not merge. Do not start any 6.6 or post-FAZ6 phase.

---

# 10. REVIEWER NEXT GATE

On next user `Devam`, Reviewer will independently verify the fresh final candidate against live GitHub state, including:

- exact new base and ancestry;
- old PR #29 lineage replacement/rebase correctness or replacement PR correctness;
- permanent changed-file scope;
- final audit artifact consistency;
- executable freeze gate completeness;
- resolved runtime exact-seven HTTP surface;
- full integrated state/money/security/recovery matrix;
- fresh exact-SHA CI and logs;
- validated-to-final cleanup delta;
- frozen 1504 baseline and all locked runtime identities;
- no production semantic drift and no post-FAZ6 scope creep.

Only if every final gate is clean may Reviewer issue:

```text
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
BLOCKERS: NONE
```

Until then FAZ 6 remains IN_PROGRESS.

Reviewer STOP.
