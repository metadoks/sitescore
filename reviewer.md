# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.5
CHECKPOINT_TITLE: Recovery + Reconciliation

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
LIVE_MAIN_SHA_AT_REVIEW: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
CODE_BRANCH: faz6/6-5-recovery-reconciliation
PR: #28
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE: TRUE
PR_MERGED: FALSE
REVIEWED_HEAD_SHA: 9a8cb1bccf36447f273dc52c16533f57f81dde22

VALIDATED_SHA: 2bd9fc99d752c65efe6093383ac044460b00ffc9
COMMERCE_VALIDATION_RUN_ID: 32401479448
COMMERCE_VALIDATION_JOB_ID: 96530437038
FROZEN_VALIDATION_RUN_ID: 32401479454
FROZEN_VALIDATION_JOB_ID: 96530437137
VALIDATION_CONCLUSION: SUCCESS
VALIDATED_TO_FINAL_COMMITS: 2
VALIDATED_TO_FINAL_DELTA: ONLY TEMPORARY FAZ 6.5 VALIDATION WORKFLOW REMOVALS

COMMERCE_VERSION: 0.6.0
MIGRATION_HEAD: 0005_recovery_reconciliation
N8N_RUNTIME_VERSION: 2.33.4
N8N_VALIDATED_IMAGE_DIGEST: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
LOCKED_ORDER_WORKFLOW_SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
RECOVERY_SCHEDULE_WORKFLOW_SHA256: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c

REC65-H001: OPEN
REC65-H002: OPEN
BLOCKERS: REC65-H001, REC65-H002
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
FAZ_6_5_STATUS: HARDENING_REQUIRED
START_6_FINAL: NO
```

---

# 1. EXACT STATE REVIEWED

Reviewer independently re-read the live coordination state and GitHub PR.

```text
main:
bdf43a891ca14941ba2f2c4f115e4a15bec0015a

PR #28:
OPEN
DRAFT: FALSE
MERGEABLE: TRUE
MERGED: FALSE

base:
main@bdf43a891ca14941ba2f2c4f115e4a15bec0015a

reviewed final head:
9a8cb1bccf36447f273dc52c16533f57f81dde22

validated SHA:
2bd9fc99d752c65efe6093383ac044460b00ffc9
```

Base -> reviewed head scope is confined to the Reviewer-authorized `sitescore-commerce` FAZ 6.5 recovery/reconciliation surface and the separate minimal n8n recovery schedule/tests. No frozen FAZ 3/4/5 source mutation was observed. The locked order-paid n8n workflow hash remains unchanged.

Validated SHA -> final head is exactly two commits and only removes:

```text
.github/workflows/faz6-6-5-validation.yml
.github/workflows/faz6-6-5-frozen-validation.yml
```

No product, test, migration, n8n workflow JSON or runtime code changed after validation.

---

# 2. POSITIVE REVIEW RESULTS

The exact reviewed implementation has substantial correct 6.5 structure:

```text
sitescore-commerce == 0.6.0
migration head == 0005_recovery_reconciliation
bounded oldest-first recovery claims
FOR UPDATE SKIP LOCKED candidate claiming
durable lease token + expiry
lease reclaim after crash
post-I/O exact lease fencing in production LineageRecoveryService
no DB transaction held across provider/n8n HTTP I/O
real Stripe evidence uses the locked validate_binding contract
server-poll payment transition uses a distinct immutable poll receipt
server poll does not fabricate evt_* or fake Stripe inbox rows
webhook and server-poll payment transitions share one internal locked transition core
exactly-one order.paid.v1 creation remains uniqueness protected
unpublished outbox sends the exact durable event identity
published stale replay preserves the same outbox identity and historical published_at
published replay is append-only audited
n8n recovery endpoint is bodyless and count-only
separate recovery Schedule Trigger contains no Code/Function business authority
locked order workflow remains byte-identical by SHA-256
n8n remains pinned to 2.33.4
frozen FAZ 3/4/5 scope remains untouched
```

These positive results do not close the two concrete recovery blockers below.

---

# 3. REC65-H001 — OPEN

## Pre-0005 stale verified Stripe inbox events become unrecoverable after upgrade

FAZ 6.5 exists in part to recover a real Stripe event that was already signature-verified and durably stored as `processing_state='received'`, followed by a crash before payment reconciliation completed.

The Reviewer contract for R65-A requires recovery to:

```text
use the original real stripe_event_id and stored event metadata
correlate the stored Stripe object/session to the unique local checkout binding
freshly retrieve the exact Checkout Session + line items
resume the original reconciliation using the original real event identity
```

Before migration `0005_recovery_reconciliation`, locked 6.1 inbox rows did not contain `candidate_order_id`.

Migration 0005 currently only adds:

```text
candidate_order_id VARCHAR(64) NULL
```

and performs no migration/backfill or legacy compatibility step for already-existing inbox rows.

Production `LineageRecoveryService._resume_inbox()` then reads the new column and immediately requires:

```text
stored candidate_order_id == recovery claim order_id
```

A legacy pre-0005 row therefore has `candidate_order_id = NULL`, which becomes `None`, fails the equality check, and is durably moved to `attention_required / event_order_correlation_invalid` before fresh Stripe evidence is even fetched.

That makes exactly the already-stranded work which 6.5 is intended to recover unrecoverable by the new recovery path.

This is a migration/recovery correctness blocker, not merely an observability gap.

Required hardening:

1. Preserve the strong non-NULL lineage check for rows where a durable signed-event candidate order is available. A non-NULL mismatching candidate must continue to fail closed before provider I/O.
2. Add a safe legacy path for genuine rows carried forward from the pre-0005 schema. It must correlate the stored real Stripe object/session to exactly one durable local Checkout Session/order binding; it must not invent a Stripe Event identity or trust caller input.
3. Fresh provider evidence must still pass the exact locked Stripe API-version/livemode/session/client-reference/metadata/Price/quantity/currency binding rules before a payment transition.
4. Ambiguous, missing, or conflicting local session correlation must become a sanitized durable finding/attention with no payment transition.
5. Do not fabricate `candidate_order_id` evidence if the implementation cannot prove it. A migration/backfill is acceptable only if the derivation is exact and auditable; a runtime legacy-correlation path is also acceptable.
6. No fake webhook, fake inbox row, synthetic `evt_*`, or poll receipt may be used when resuming a real legacy inbox event. The original real event identity remains the authority record.

Required real PostgreSQL migration/recovery proof:

```text
A. migrate commerce to 0004_delivery_email
B. insert a realistic pending order + exact bound Checkout Session
C. insert a real-looking stale received Stripe inbox row using the 0004 schema
   (there is therefore no candidate_order_id field/value)
D. upgrade the same populated database to 0005_recovery_reconciliation
E. run the production LineageRecoveryService
F. prove original real event_id is resumed
G. prove exact stored Stripe Session correlation + fresh provider binding validation
H. prove paid case -> exactly one paid transition + exactly one order.paid.v1 + inbox processed
I. prove expired case -> exactly one expired transition + inbox processed
J. prove no payment_poll_receipt and no fake event/inbox identity is produced
K. prove no-match / ambiguous / conflicting legacy session correlation fails closed with durable finding and zero business transition
```

A migration cycle on an empty database is not sufficient for this blocker; this must be a data-preserving 0004 -> 0005 upgrade test.

```text
REC65-H001: OPEN
```

---

# 4. REC65-H002 — OPEN

## Paid recovery replay does not verify contradictory durable Stripe binding before re-entering orchestration

R65-F explicitly requires impossible/corrupt recovery shapes to fail closed, including:

```text
paid order with contradictory Stripe binding
```

The current `RecoverySnapshot` carries only these payment-side fields:

```text
order/payment/fulfillment state
order updated_at
stripe_checkout_session_id
outbox identities/publication times
```

It does not carry or validate the durable reconciliation evidence already stored on `checkout_sessions`, including at least:

```text
stripe_payment_intent_id
stripe_session_status
stripe_payment_status
stripe_livemode
reconciled_at / reconciliation lineage as applicable
```

The paid/fulfillment-in-progress recovery branch currently verifies only that there is exactly one `order.paid.v1` outbox. If one exists, it can publish/replay that event to n8n without first proving that the durable local Stripe reconciliation binding is coherent with the paid state.

Therefore a corrupted shape such as:

```text
order.payment_state = paid
exactly one order.paid.v1 exists
but checkout stripe_payment_status != paid
or stripe_session_status != complete
or PaymentIntent is missing
or stored livemode contradicts the configured/provider authority
```

can be re-entered into downstream analysis/report/refund/delivery orchestration instead of becoming the durable R65-F finding required by the contract.

This is a business-authority/invariant recovery blocker because 6.5 is specifically the component that decides whether a stale paid order may be replayed into orchestration.

Required hardening:

1. Before any unpublished paid-outbox send or published paid-outbox replay, validate the durable Stripe paid reconciliation shape for the order.
2. At minimum require the local durable evidence that locked payment transitions write for an authoritative paid state: exact bound Checkout Session, `complete`, `paid`, non-empty bound PaymentIntent, expected livemode, and coherent order/checkout identity. Preserve any stronger existing immutable catalog/product/Price/quantity/customer binding invariants.
3. Contradiction/missing authority must create a sanitized durable recovery finding/attention and perform ZERO n8n I/O.
4. Do not silently repair the corrupted paid binding and do not synthesize missing Stripe evidence.
5. This guard must also protect a stale fulfillment-in-progress/refund-pending order that is still based on the same original paid authority before replaying `order.paid.v1`.
6. Existing valid paid orders must continue to publish/replay the exact same outbox identity with no new payment transition.

Required real PostgreSQL tests must independently corrupt each meaningful paid reconciliation field and prove fail-closed behavior, including at least:

```text
missing PaymentIntent
stripe_session_status != complete
stripe_payment_status != paid
stripe_livemode mismatch/NULL where authoritative paid evidence is required
Checkout Session identity/binding conflict
```

For every corrupt case prove:

```text
no n8n request
no new outbox
no payment mutation
no analysis/report/refund/delivery mutation
sanitized durable recovery finding exists
```

Also retain a valid-control case proving a correctly reconciled paid binding still publishes/replays the exact original `order.paid.v1` identity.

```text
REC65-H002: OPEN
```

---

# 5. EXACT-HEAD VALIDATION REVIEWED

Current validation is useful positive evidence but must be rerun after hardening.

Commerce + n8n exact validated SHA:

```text
run: 32401479448
job: 96530437038
checkout SHA: 2bd9fc99d752c65efe6093383ac044460b00ffc9
Python: 3.11.16
PostgreSQL: 16.15
commerce tests: 382 PASS
n8n static: 12 PASS
migration upgrade/downgrade/re-upgrade: PASS
locked order workflow SHA: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery schedule workflow SHA: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
n8n runtime: 2.33.4
```

Current runtime evidence includes the locked 6.3/6.4 workflow proofs plus recovery scheduler and stuck-state replay convergence for analysis/report/refund/delivery.

Frozen exact validated SHA:

```text
run: 32401479454
job: 96530437137
checkout SHA: 2bd9fc99d752c65efe6093383ac044460b00ffc9
frozen total: 1504 PASS
sitescore-report: 24 PASS
sitescore-api: 105 PASS
private S3 regression: PASS
Redis/Celery transport: PASS
frozen-scope scan: PASS
secret boundary scan: PASS
```

The 1504 frozen total is independently accounted as:

```text
24 + 105 + 19 + 53 + 191 + 67 + 180 + 418 + 361 + 86 = 1504
```

After REC65-H001/H002 hardening, fresh exact-head Commerce+n8n and frozen validation are required. Any validated-SHA -> final-head delta must again be independently reviewable and non-semantic.

---

# 6. HARDENING SCOPE

Implementer must harden the SAME PR #28 and remain within FAZ 6.5.

Expected narrow changes:

```text
legacy pre-0005 Stripe inbox upgrade/recovery compatibility
production LineageRecoveryService correlation hardening
paid durable Stripe-binding guard before n8n publish/replay
real PostgreSQL data-preserving migration tests
real PostgreSQL paid-corruption adversarial tests
necessary 6.5 docs/runbook updates
fresh exact-head validation evidence
```

Do NOT:

```text
reopen FAZ 3/4/5 frozen code
weaken Stripe validate_binding
invent fake Stripe Event IDs/inbox rows
use a poll receipt to impersonate a real inbox event
weaken refund or Postmark authority
create a second order.paid.v1 identity
clear/rewrite historical published_at
add direct SiteScore DB/package authority
put provider secrets in n8n
upgrade n8n beyond locked 2.33.4
start FAZ 6-FINAL
```

---

# 7. REVIEWER DECISION

```text
FAZ 6.5: HARDENING_REQUIRED
PR: #28
REVIEWED_HEAD_SHA: 9a8cb1bccf36447f273dc52c16533f57f81dde22
VALIDATED_SHA: 2bd9fc99d752c65efe6093383ac044460b00ffc9

REC65-H001: OPEN
REC65-H002: OPEN
BLOCKERS: REC65-H001, REC65-H002

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
USER_LOCK_AUTHORIZED: NO
START_6_FINAL: NO
```

Implementer must harden PR #28, produce a new exact final head plus fresh exact-head CI evidence, update `implementer.md` to `READY_FOR_REVIEW`, and STOP.

No LOCK is authorized. FAZ 6-FINAL remains closed. Reviewer STOP.
