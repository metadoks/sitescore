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
FINAL_REVIEW_HEAD_SHA: 9a8cb1bccf36447f273dc52c16533f57f81dde22
VALIDATED_SHA: 2bd9fc99d752c65efe6093383ac044460b00ffc9
VALIDATED_TO_FINAL_COMMITS: 2
VALIDATED_TO_FINAL_DIFF: ONLY .github/workflows/faz6-6-5-validation.yml AND .github/workflows/faz6-6-5-frozen-validation.yml REMOVED
POST_VALIDATION_PRODUCT_CODE_CHANGES: NONE

EXPECTED_COMMERCE_VERSION: 0.6.0
EXPECTED_MIGRATION_HEAD: 0005_recovery_reconciliation
N8N_RUNTIME_VERSION: 2.33.4
N8N_VALIDATED_IMAGE_DIGEST: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
LOCKED_ORDER_WORKFLOW_SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
RECOVERY_SCHEDULE_WORKFLOW_SHA256: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c

COMMERCE_CI_RUN_ID: 32401479448
COMMERCE_CI_JOB_ID: 96530437038
COMMERCE_CI_CONCLUSION: SUCCESS
FROZEN_CI_RUN_ID: 32401479454
FROZEN_CI_JOB_ID: 96530437137
FROZEN_CI_CONCLUSION: SUCCESS
COMMERCE_TESTS: 382 PASS
N8N_STATIC_TESTS: 12 PASS
FROZEN_TOTAL_TESTS: 1504 PASS
COMBINED_COMMERCE_FROZEN_PYTEST: 1886 PASS
POSTGRESQL_VERSION: 16
PYTHON_VERSION: 3.11
MIGRATION_CYCLE: PASS
PRIVATE_S3_REGRESSION: PASS
REDIS_CELERY_TRANSPORT: PASS
FROZEN_SCOPE_SCAN: PASS
SECRET_BOUNDARY_SCAN: PASS

R65_A_STALE_REAL_STRIPE_INBOX_RESUME: PASS
R65_B_SERVER_POLL_PAYMENT_RECONCILIATION: PASS
R65_C_UNPUBLISHED_OUTBOX_RECOVERY: PASS
R65_D_PUBLISHED_SAME_IDENTITY_REPLAY: PASS
R65_E_DOWNSTREAM_STUCK_REPLAY_CONVERGENCE: PASS
R65_F_INVARIANT_FINDING_FAIL_CLOSED: PASS
RECOVERY_LEASE_CRASH_RECLAIM: PASS
RECOVERY_STALE_WORKER_NO_OVERWRITE: PASS
RECOVERY_BOUNDED_BATCH_BACKOFF: PASS
NO_DB_TRANSACTION_ACROSS_EXTERNAL_HTTP: PASS
NO_SYNTHETIC_STRIPE_EVENT_IDENTITY: PASS
POLL_RECEIPT_ATOMICITY: PASS
WEBHOOK_VS_POLL_CONVERGENCE: PASS

N8N_RECOVERY_SCHEDULE_IMPORT: PASS
N8N_RECOVERY_SCHEDULE_PUBLISH: PASS
N8N_RECOVERY_NATURAL_SCHEDULE_TRIGGER: PASS
N8N_RECOVERY_SINGLE_BOUNDED_CALL: PASS
N8N_RECOVERY_REPLAY_ANALYSIS_PENDING: PASS
N8N_RECOVERY_REPLAY_REPORT_PENDING: PASS
N8N_RECOVERY_REPLAY_REFUND_RESPONSE_LOSS: PASS
N8N_RECOVERY_REPLAY_DELIVERY_UNCERTAIN: PASS
N8N_RECOVERY_REPLAY_LOCKED_WORKFLOW_CONVERGENCE: PASS

BLOCKERS: NONE
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

## Implemented scope

FAZ 6.5 adds only the Reviewer-authorized bounded production recovery/reconciliation layer. Recovery remains an at-least-once convergence mechanism and does not create a second source of payment, analysis, report, refund, fulfillment, delivery, scoring, readiness, financial, decision, or confidence truth.

Implemented recovery classes:

- stale signature-verified Stripe inbox rows still in `received` resume with the original real Stripe event identity and fresh exact Checkout evidence;
- stale pending-payment orders may server-poll only their exact bound Checkout Session, with the existing immutable Checkout/Price/quantity/USD/livemode/API-version binding; a winning paid/expired transition persists a distinct immutable server-poll reconciliation receipt and never fabricates a Stripe Event or inbox row;
- unpublished `order.paid.v1` events are delivered using their existing durable identity and are marked published only after confirmed accepted 2xx;
- stale published nonterminal orders replay the same durable outbox UUID/type/order/original occurred-at without rewriting `published_at`; every replay attempt is durably audited;
- analysis/report/refund/delivery stuck-state recovery occurs only by replaying the locked order workflow, which re-enters the existing Commerce authority primitives;
- impossible/contradictory invariant shapes become sanitized durable recovery findings rather than synthetic repair.

Durability added by migration `0005_recovery_reconciliation` includes bounded recovery-run/state records, expiring lease identity, immutable payment-poll receipts, outbox replay audit, sanitized recovery findings, and the original verified Stripe candidate-order correlation required for crash-safe inbox resumption.

The recovery worker commits claim/lease state before external I/O. Stripe/n8n network calls run with no recovery DB transaction or row lock held. After I/O the exact lease is re-proved; expired/replaced leases cannot be finalized by stale workers. Retryable/uncertain paths use durable bounded backoff.

Protected production boundary:

```text
POST /v1/automation/recovery/run
Authorization: existing COMMERCE_AUTOMATION_API_KEY
request body: empty
```

The response exposes aggregate counts only. The caller cannot select order IDs, target states, provider results, retry counts, timestamps, batch size, or business truth.

A separate minimal native n8n schedule workflow runs every five minutes and only calls the Commerce recovery endpoint with the existing automation bearer. It contains no Code/Function business authority and receives no Stripe/Postmark/SiteScore/DB/S3/Redis/Celery/customer/delivery-token secrets or business material.

The already-LOCKED `sitescore-order-paid-v1` workflow remains byte-for-byte at SHA-256 `02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1`.

## Exact-head validation

Authoritative validated SHA:

`2bd9fc99d752c65efe6093383ac044460b00ffc9`

Commerce/n8n workflow run `32401479448`, job `96530437038`: SUCCESS.

Evidence includes Commerce 382 PASS, PostgreSQL 16 migration upgrade/downgrade/re-upgrade PASS at `0005_recovery_reconciliation`, n8n static 12 PASS, exact n8n 2.33.4 runtime, locked order-workflow regression, recovery-schedule import/publication/natural trigger, one bounded recovery scan, and real stuck-state same-identity replay convergence.

Frozen workflow run `32401479454`, job `96530437137`: SUCCESS.

Frozen evidence: report 24 + API 105 + app 19 + pipeline 53 + benchmarks 191 + metrics 67 + spatial 180 + providers 418 + data 361 + core 86 = 1504 PASS. Private S3, Redis/Celery, frozen-scope and secret-boundary proofs also PASS.

Commerce + frozen pytest total = 1886 PASS.

After successful exact-head validation, only the two temporary checkpoint validation workflows were removed. GitHub compare proves validated SHA -> final review head is exactly two commits and exactly these two removed paths:

```text
.github/workflows/faz6-6-5-validation.yml
.github/workflows/faz6-6-5-frozen-validation.yml
```

No product/source/test semantic change exists after validation.

## Handoff

PR #28 is open, non-draft, mergeable and unmerged at exact final head `9a8cb1bccf36447f273dc52c16533f57f81dde22`. Live `main` remains exact expected base `bdf43a891ca14941ba2f2c4f115e4a15bec0015a`.

FAZ 6.5 is READY_FOR_REVIEW. Implementer STOP. No merge/LOCK is assumed or performed. FAZ 6-FINAL has not been started and remains prohibited until a later user-authorized 6.5 LOCK followed by a fresh Reviewer transition.
