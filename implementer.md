# SiteScore AI — Implementer → Reviewer Handoff

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.5
CHECKPOINT_TITLE: Recovery + Reconciliation
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
LIVE_MAIN_SHA_AT_HANDOFF: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
CODE_BRANCH: faz6/6-5-recovery-reconciliation
PR: #28
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE: TRUE
PR_MERGED: FALSE
FINAL_REVIEW_HEAD_SHA: 4ed902dd9ebf230dcb983392705ab0d95bb0c846
VALIDATED_SHA: 415d394e114316a908c58c1b8daeaf44a3136401
VALIDATED_TO_FINAL_COMMITS: 2
VALIDATED_TO_FINAL_DIFF: ONLY TEMPORARY 6.5 VALIDATION WORKFLOWS REMOVED
POST_VALIDATION_PRODUCT_CODE_CHANGES: NONE

EXPECTED_COMMERCE_VERSION: 0.6.0
EXPECTED_MIGRATION_HEAD: 0005_recovery_reconciliation
N8N_RUNTIME_VERSION: 2.33.4
N8N_VALIDATED_IMAGE_DIGEST: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
LOCKED_ORDER_WORKFLOW_SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
RECOVERY_SCHEDULE_WORKFLOW_SHA256: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c

COMMERCE_CI_RUN_ID: 32406078523
COMMERCE_CI_JOB_ID: 96545367855
COMMERCE_CI_CONCLUSION: SUCCESS
FROZEN_CI_RUN_ID: 32406078549
FROZEN_CI_JOB_ID: 96545368022
FROZEN_CI_CONCLUSION: SUCCESS
COMMERCE_TESTS: 403 PASS
N8N_STATIC_TESTS: 12 PASS
FROZEN_TOTAL_TESTS: 1504 PASS
COMBINED_COMMERCE_FROZEN_PYTEST: 1907 PASS
POSTGRESQL_VERSION: 16.15
PYTHON_VERSION: 3.11.16
MIGRATION_CYCLE: PASS
PRIVATE_S3_REGRESSION: PASS
REDIS_CELERY_TRANSPORT: PASS
FROZEN_SCOPE_SCAN: PASS
SECRET_BOUNDARY_SCAN: PASS

REC65-H001: RESOLVED_BY_IMPLEMENTER_PENDING_REVIEW
REC65-H002: RESOLVED_BY_IMPLEMENTER_PENDING_REVIEW
BLOCKERS: NONE_REPORTED_BY_IMPLEMENTER_PENDING_REVIEWER_REVIEW
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: LOCKED
FAZ_6_1_STATUS: LOCKED
FAZ_6_2_STATUS: LOCKED
FAZ_6_3_STATUS: LOCKED
FAZ_6_4_STATUS: LOCKED
FAZ_6_5_STATUS: READY_FOR_REVIEW
START_6_FINAL: NO
```

## Reviewer hardening closure

Reviewer opened `REC65-H001` and `REC65-H002` against prior reviewed head `9a8cb1bccf36447f273dc52c16533f57f81dde22`. Both were hardened on the same branch and PR without widening FAZ 6.5 authority.

### REC65-H001 — legacy 0004 -> 0005 received-event lineage

Migration `0005_recovery_reconciliation` now handles a populated FAZ 6.4 database safely. Existing real Stripe inbox rows still in `received` can be deterministically correlated only through their stored exact Checkout Session identity to the structurally unique local Checkout Session binding. A safely correlated legacy row resumes using the original real `stripe_event_id`; no synthetic Event ID, fake webhook/inbox row, or fabricated verified-event lineage is created. An orphan/uncorrelatable legacy row is quarantined to sanitized `attention_required`. New post-0005 verified events remain bound to `verified_event_v1` candidate-order lineage and cannot use the legacy fallback when that immutable candidate correlation is absent.

PostgreSQL hardening tests cover populated 0004 -> 0005 paid and expired resumption, original-event preservation, orphan quarantine, unique local Checkout Session correlation, and post-0005 missing-candidate fail-closed behavior.

### REC65-H002 — durable paid authority before outbox publish/replay

Before any recovery n8n publish/replay I/O, the implementation now proves coherent durable paid Stripe authority: local payment truth is paid, an exact Checkout Session binding exists, stored session/payment state is `complete/paid`, PaymentIntent exists, livemode is present and matches configuration, reconciliation evidence exists, and the winning poll receipt or processed real Stripe event is coherent with that binding.

Adversarial PostgreSQL tests independently corrupt missing PaymentIntent, session-not-complete, payment-not-paid, absent livemode, livemode mismatch, session identity conflict, and missing reconciliation timestamp for both unpublished and already-published outbox cases. Each corrupted shape fails closed to a sanitized `paid_*` recovery finding with zero n8n calls, zero replay audit, and no change to original outbox publication history. Valid shapes still send the exact original outbox UUID and original `occurred_at`.

## Recovery invariants retained

- stale real Stripe `received` recovery uses the original real Event identity;
- direct server poll does not fabricate Stripe Events/inbox rows and persists its own immutable payment-poll receipt only when its terminal transition wins;
- webhook/poll races converge to one terminal payment truth and at most one `order.paid.v1` event;
- unpublished outbox publication and stale published replay use the same durable outbox identity;
- published replay never clears or rewrites historical `published_at`;
- downstream analysis/report/refund/delivery recovery re-enters the locked Commerce/n8n authority path rather than duplicating those state machines;
- claim/lease commits occur before provider I/O and no recovery DB transaction/row lock is held across external HTTP;
- expired leases are reclaimable and stale workers cannot finalize after lease loss;
- bounded server-owned batch/backoff prevents hot loops;
- terminal/attention states are not automatically reopened;
- impossible paid/outbox/identity shapes fail closed to durable sanitized findings.

## Protected scheduler boundary

Production control remains:

```text
POST /v1/automation/recovery/run
Authorization: existing COMMERCE_AUTOMATION_API_KEY
request body: empty
```

The response exposes aggregate counts only. Caller/n8n cannot choose order ID, target state, provider truth, retry count, timestamps, batch size, payment/refund/delivery truth, or analytics identity.

The separate native n8n recovery schedule workflow runs every five minutes and only invokes this bounded Commerce endpoint. It contains no Code/Function business logic and receives no Stripe/Postmark/SiteScore/DB/S3/Redis/Celery/customer/delivery-token material. n8n remains exactly 2.33.4.

The already-LOCKED order workflow remains byte-for-byte at SHA-256 `02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1`.

## Exact-head validation

Authoritative validated SHA:

`415d394e114316a908c58c1b8daeaf44a3136401`

Commerce/n8n run `32406078523`, job `96545367855`: SUCCESS.

Evidence includes Python 3.11.16, PostgreSQL 16.15, package 0.6.0, migration upgrade/downgrade/re-upgrade at `0005_recovery_reconciliation`, full Commerce **403 PASS**, n8n static **12 PASS**, exact pinned n8n runtime/digest, locked order-workflow regressions, recovery scheduler import/publication/natural 5-minute trigger/single bounded call, and same-identity recovery replay convergence for analysis pending, report pending, refund response loss and delivery uncertainty.

Frozen run `32406078549`, job `96545368022`: SUCCESS.

Frozen regression remains **1504 PASS**: report 24 + API 105 + app 19 + pipeline 53 + benchmarks 191 + metrics 67 + spatial 180 + providers 418 + data 361 + core 86. Private S3, Redis/Celery transport, frozen-scope and secret-boundary proofs also PASS.

Commerce + frozen pytest total = **1907 PASS**.

After exact-head validation, only the two temporary validation workflows were removed. GitHub compare proves:

```text
validated: 415d394e114316a908c58c1b8daeaf44a3136401
final:     4ed902dd9ebf230dcb983392705ab0d95bb0c846
ahead_by: 2
changed paths:
  .github/workflows/faz6-6-5-validation.yml              REMOVED
  .github/workflows/faz6-6-5-frozen-validation.yml       REMOVED
```

No product/source/test semantic changes exist after validation.

## Handoff

PR #28 is open, non-draft, mergeable and unmerged at exact final head `4ed902dd9ebf230dcb983392705ab0d95bb0c846`. Live `main` remains exact expected base `bdf43a891ca14941ba2f2c4f115e4a15bec0015a`.

Implementer reports both Reviewer blockers resolved with fresh exact-head evidence and STOPs for independent Reviewer re-review. No merge or LOCK was performed or assumed. FAZ 6-FINAL remains NOT STARTED.
