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

REVIEWER_STATE: IMPLEMENTATION_AUTHORIZED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
LIVE_MAIN_SHA_AT_REVIEW: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
CODE_BRANCH: faz6/6-5-recovery-reconciliation
PR: NOT_CREATED
PR_STATE: NONE
PR_DRAFT: FALSE
PR_MERGED: FALSE

EXPECTED_COMMERCE_VERSION: 0.6.0
EXPECTED_MIGRATION_HEAD: 0005_recovery_reconciliation
N8N_RUNTIME_VERSION: 2.33.4
N8N_IMAGE_DIGEST_BASELINE: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
LOCKED_ORDER_WORKFLOW_SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1

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
FAZ_6_5_STATUS: IMPLEMENTATION_AUTHORIZED
START_6_5: YES
START_6_FINAL: NO
```

---

# 1. POST-LOCK VERIFICATION — FAZ 6.4

Reviewer independently verified the user-authorized FAZ 6.4 merge before opening 6.5.

```text
PR #27: CLOSED / MERGED
approved head: 1f22c4a09c08c2803c746b87a20209d7fdf6c574
merge commit: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
live main: bdf43a891ca14941ba2f2c4f115e4a15bec0015a
merge parent 1: 7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba
merge parent 2: 1f22c4a09c08c2803c746b87a20209d7fdf6c574
merge tree: 384d4d9a4384d9a9d6767f2a7c30520e05ef3d67
approved-head tree: 384d4d9a4384d9a9d6767f2a7c30520e05ef3d67
```

Implementer handoff records literal user `LOCK`, exact reviewed head, exact merge parentage, and no 6.5 work before authorization.

Therefore:

```text
FAZ 6.4: LOCKED
FAZ 6.5: OPEN FOR IMPLEMENTATION
```

---

# 2. CHECKPOINT MISSION

FAZ 6.5 closes the production recovery gap left intentionally open by 6.1–6.4.

The system already has safe per-order primitives for:

```text
Stripe webhook payment authority
order.paid.v1 durable outbox
n8n orchestration
analysis/report reconciliation
refund reconciliation
Postmark delivery uncertainty/retry
secure delivery capability
```

But those primitives can still require a later invocation after process death, webhook loss, n8n horizon exhaustion, transport response loss, or an unpublished/stale outbox event.

FAZ 6.5 must add a bounded, durable, repeatable recovery scanner that makes these states converge without creating a second business-authority path.

Canonical recovery model:

```text
periodic scheduler
-> protected Commerce recovery run
-> Commerce selects bounded stale candidates
-> fresh provider/server evidence where required
-> reuse existing durable authority primitives
-> replay the existing order.paid.v1 identity when orchestration must restart
-> converge or defer
-> contradictory/invariant-breaking evidence fails closed
```

Recovery is not permission to invent payment, analysis, report, refund, delivery or fulfillment truth.

---

# 3. FROZEN AUTHORITY BOUNDARIES

The following remain frozen and must not be weakened.

## 3.1 Payment

Only verified Stripe evidence may change payment truth.

For a server-poll recovery path, Commerce may retrieve the exact already-bound Checkout Session and line items using the same pinned Stripe API version and the same 6.1 `validate_binding` semantics.

A recovery poll MUST NOT fabricate a Stripe Event ID, synthetic `evt_*`, webhook signature, or fake inbox row.

## 3.2 Analysis/report

Frozen SiteScore `/v1` API remains the only analysis/report authority.

Recovery must not import frozen SiteScore packages directly, write SiteScore DB tables, derive scoring truth, or manufacture report readiness.

## 3.3 Refund

Existing 6.2 server-side Stripe PaymentIntent/refund history validation remains authoritative. Recovery must re-enter that existing logic; it must not add a looser refund path.

## 3.4 Delivery

Existing 6.4 validated Postmark acceptance evidence remains required for `fulfilled`.

Recovery must never interpret email open/read, HTTP success alone, n8n success, or a grant existing as fulfillment proof.

## 3.5 n8n

n8n remains orchestration/scheduling only. It receives no Stripe secret, Postmark secret, SiteScore service key, database credential, raw delivery token, recipient, report bytes, refund authority, or business-state mutation authority.

---

# 4. REQUIRED RECOVERY CLASSES

The scanner must cover all of the following classes.

## R65-A — Stale verified Stripe inbox event

A Stripe event may have been signature-verified and durably recorded as `received`, then the process can die before fresh provider reconciliation or final state commit.

Recovery must:

```text
find stale stripe_event_inbox rows still in received
use the original real stripe_event_id and stored event metadata
correlate the stored Stripe object/session to the unique local checkout binding
freshly retrieve the exact Checkout Session + line items
apply the existing event-type/API-version/livemode/binding rules
resume the original reconciliation using the original real event identity
```

Do not reopen `processed`, `ignored`, or `attention_required` inbox rows automatically.

## R65-B — Missing webhook / direct Checkout Session poll

A pending-payment order may have a durable Checkout Session binding but no usable webhook delivery.

For a sufficiently stale `pending_payment / pending` order with an exact bound Stripe Checkout Session, recovery may fresh-poll that exact session.

Allowed results:

```text
status=complete + payment_status=paid + PaymentIntent present + exact binding
-> atomic paid transition + checkout reconciliation + exactly one order.paid.v1 outbox

status=expired + payment_status=unpaid + exact binding
-> atomic expired transition

open/unpaid or otherwise nonterminal-but-valid
-> no business-state transition; defer

binding mismatch / contradictory terminal truth / malformed provider evidence
-> fail closed; durable recovery finding; no fabricated transition
```

This direct poll path requires a durable server-reconciliation receipt and MUST NOT write a fake `last_reconciliation_event_id`.

## R65-C — Unpublished paid outbox

For an exact durable `order.paid.v1` event with `published_at IS NULL`, recovery may invoke the existing protected n8n ingress using the exact stored outbox identity and payload contract.

Only a confirmed accepted 2xx may set `published_at`.

Timeout/connection loss/5xx/429 must leave the event unpublished for later retry.

## R65-D — Published outbox but stale nonterminal order

A published event does not prove that the n8n execution eventually converged. The execution may have crashed or exhausted its finite horizon.

For a stale paid nonterminal order whose exact `order.paid.v1` row is already published, recovery may replay the SAME durable event identity to the same protected n8n ingress.

Rules:

```text
same outbox_id
the same event_type
same order_id
same original occurred_at
no new order.paid.v1 row
no new event identity
published_at remains historical and is not cleared/re-written
replay itself is durably audited
```

A replay may create another n8n execution, but existing Commerce idempotency must guarantee no duplicate analysis, report, refund, or fulfilled business effect.

## R65-E — Refund/delivery/analysis/report recovery after n8n loss

Recovery must not duplicate these provider/state machines inside the scanner.

It restarts orchestration by the exact durable outbox replay. n8n then follows authoritative Commerce `next_action`, which re-enters the already-locked 6.2/6.4 runtime services.

This covers, among others:

```text
analysis_pending / analysis_running
report_pending
not_score_ready / analysis_failed / analysis_timed_out / report_failed refund paths
refund_pending / response-loss recovery
delivery_pending
provider_uncertain delivery retry
known provider_accepted convergence
```

## R65-F — Invariant corruption / attention

Recovery must NEVER silently repair invariant shapes that should be impossible after locked atomic transitions.

Examples:

```text
payment_state=paid with no order.paid.v1 outbox
multiple order.paid.v1 rows or identity conflict
paid order with contradictory Stripe binding
refunded/fulfilled/expired terminal order requiring a new business transition
SiteScore/Stripe/Postmark identity mismatch
reserved SiteScore refund metadata conflict
```

These become durable sanitized recovery findings / operator attention. Do not synthesize missing authoritative evidence.

Existing `attention_required` orders are not automatically reopened by FAZ 6.5.

---

# 5. DURABLE RECOVERY PERSISTENCE

Expected schema head:

```text
0005_recovery_reconciliation
```

At minimum, implement durable equivalents of the following concepts.

## 5.1 `recovery_state`

One bounded scheduler/retry record per order.

Required semantics:

```text
order_id PK/FK
attempt_count >= 0
consecutive_failures >= 0
next_attempt_at
last_checked_at nullable
last_action nullable
last_outcome nullable
last_error_code nullable, sanitized and bounded
lease_token UUID nullable
lease_expires_at nullable
created_at
updated_at
```

Lease token is concurrency identity, not a secret.

Lease fields must be pair-consistent. Expired leases are reclaimable. A crash after claiming work must not permanently strand the order.

## 5.2 Poll-based payment reconciliation receipt

When direct server polling — not a webhook event — actually causes a paid or expired transition, persist a durable immutable receipt in the same atomic transaction as the business-state transition.

Required evidence includes at least:

```text
receipt_id
order_id
source = stripe_checkout_server_poll_v1
stripe_checkout_session_id
observed session status
observed payment status
observed PaymentIntent id if present
observed livemode
canonical evidence hash over the validated authority fields including line-item binding
transition target = paid | expired
observed_at
created_at
```

There must be no raw Stripe response persistence and no fake webhook/Event identity.

Exactly one authoritative local terminal payment transition may win. Concurrency with a real webhook must converge through row locks/uniqueness to the same final state and exactly one paid outbox event.

## 5.3 Replay audit

Published-outbox recovery replay must be durably observable without changing outbox historical publication truth.

Persist or equivalently prove:

```text
order_id
outbox_id
replay attempt identity
attempt time
result = accepted | uncertain | retryable_rejected | attention
sanitized failure/status code
```

Do not store n8n secrets or provider response bodies.

---

# 6. CLAIMING, CONCURRENCY, AND TRANSACTIONS

Recovery scanning is at-least-once and crash-safe.

Required behavior:

1. Select candidates in deterministic order, oldest eligible first.
2. Claim only a bounded batch.
3. Commit the claim/lease before any external HTTP.
4. Never hold a DB transaction, row lock, or advisory transaction lock across Stripe, SiteScore, Postmark, or n8n HTTP.
5. After I/O, reacquire the exact row and re-check current durable state before applying a result.
6. A stale worker may not overwrite a newer worker's lease/result.
7. Concurrent recovery runs may duplicate safe reads/replays but may not duplicate business authority.
8. Backoff must be bounded and durable; a continuously failing provider must not cause a hot loop.
9. Terminal states must age out of active recovery work cleanly.

Recommended production defaults, unless an implementation-level constraint requires a documented Reviewer-visible adjustment:

```text
recovery schedule: every 5 minutes
batch size: 10
stale verified inbox threshold: 120 seconds
pending-payment poll threshold: 300 seconds
published-orchestration replay threshold: 1200 seconds
lease duration: 120 seconds
maximum backoff: 3600 seconds
```

All values must be server-owned configuration with bounded validation. Callers cannot override them per request.

---

# 7. RECOVERY SCHEDULER BOUNDARY

Production recovery must be autonomously invocable.

Preferred contract:

```text
POST /v1/automation/recovery/run
Authorization: existing COMMERCE_AUTOMATION_API_KEY
request body: empty
```

The endpoint may run one bounded recovery batch only. It must not accept order IDs, target states, provider results, retry counts, timestamps, or business truth from n8n.

Sanitized response may contain counts only, for example:

```text
api_version
run_id
claimed
reconciled
published
replayed
deferred
attention
```

No PII, Stripe IDs, PaymentIntent IDs, delivery tokens, recipient, report ID, provider body, or secret may be returned.

Use a separate minimal n8n recovery schedule workflow if scheduling is implemented through n8n:

```text
Schedule Trigger
-> POST Commerce /v1/automation/recovery/run with empty body
-> stop
```

No Code/Function business logic. No direct Stripe/SiteScore/Postmark/DB calls. The existing locked order workflow should remain semantically unchanged; published-outbox recovery re-enters it through the same protected `order.paid.v1` webhook.

n8n remains pinned to `2.33.4`. Do not silently upgrade during 6.5.

---

# 8. TRANSPORT CLASSIFICATION

Recovery must distinguish retryable transport failure from deterministic configuration/contract rejection.

For n8n ingress replay/dispatch:

```text
2xx -> confirmed accepted
connection/timeout -> uncertain; retry later
429 -> retryable
5xx -> retryable
401/403 -> configuration/auth attention; do not hot-loop
400/422 malformed-contract response -> attention; same invalid request must not be hammered
other unexpected responses -> fail closed with documented classification
```

No transport outcome may alter payment/refund/report/delivery truth directly.

---

# 9. PAYMENT POLL ATOMICITY

The existing 6.1 webhook path currently couples `apply_reconciliation` to a real Stripe inbox event. FAZ 6.5 must not abuse that method by inventing an event.

Refactor only as needed so webhook reconciliation and server-poll reconciliation share one internal atomic payment transition core while preserving distinct authority records:

```text
webhook source -> real stripe_event_inbox row + real event_id
server poll source -> poll reconciliation receipt, no event_id fabrication
```

Both paths must enforce the same immutable Checkout binding and the same terminal-state contradiction rules.

Paid transition still atomically creates at most one `order.paid.v1` outbox row.

---

# 10. OBSERVABILITY AND SECURITY

Required operational evidence:

```text
bounded counters for scan outcomes
sanitized error/failure codes
recovery run identity
order/outbox internal UUIDs may be used in server logs where operationally necessary
no customer_email
no delivery raw token
no Stripe/Postmark secret
no SiteScore service key
no private S3 URL/credential
no raw provider response body
```

Recovery endpoint and scheduler must not expose an unauthenticated admin/control plane.

Do not add a public "force paid", "force fulfilled", "force refund", "retry this order" or state override endpoint.

---

# 11. FORBIDDEN SCOPE

FAZ 6.5 must NOT:

```text
edit frozen FAZ 3/4/5 source
change scoring/benchmark/financial/decision/confidence semantics
add direct SiteScore DB access
add direct n8n DB access
create synthetic Stripe Event IDs
relax Stripe Checkout/Price/quantity/USD/livemode/API-version binding
relax refund metadata/history validation
relax Postmark acceptance validation
persist raw/reversible delivery capability tokens
expose private S3/MinIO object URLs
add customer account/auth redesign
add manual state override APIs
add Postmark webhooks unless separately Reviewer-authorized
upgrade n8n from 2.33.4
start FAZ 6-FINAL before 6.5 LOCK
```

No automatic FAZ 6.6 exists.

---

# 12. REQUIRED ADVERSARIAL TESTS

Use real PostgreSQL for all state-changing/concurrency proofs.

At minimum prove:

## Stripe / payment

```text
stale real received webhook resumes with the original real event_id
missing webhook + fresh complete/paid exact session -> paid exactly once
missing webhook + fresh expired/unpaid exact session -> expired exactly once
open/unpaid session -> defer, no transition
poll binding mismatch -> no paid/expired transition
poll does not fabricate stripe_event_inbox row or evt_* identity
poll transition persists immutable server-poll receipt
webhook vs poll race -> one terminal truth + one paid outbox
paid-after-expired contradiction -> fail closed
expired-after-paid contradiction -> fail closed
```

## Outbox / n8n

```text
unpublished outbox + 2xx -> published
unpublished outbox + response loss -> remains unpublished, same identity retries
published stale order -> replay uses same outbox_id and occurred_at
published replay never clears/changes published_at
replay response loss -> later same-identity replay converges
429/5xx retry with backoff
401/403 and malformed-contract response -> attention classification, no hot-loop
paid order missing required outbox -> no synthetic event; recovery finding
```

## End-to-end stuck states

```text
published event + analysis_pending after original n8n horizon -> recovery replay -> converge
published event + report_pending -> recovery replay -> converge
published event + refund_pending/response-loss -> recovery replay -> existing refund reconciliation converges
published event + delivery provider_uncertain -> recovery replay -> existing delivery semantics converge or bounded attention
fulfilled/refunded/expired -> no provider I/O
attention_required -> no automatic reopen
```

## Concurrency/crash

```text
two recovery runners cannot create duplicate payment transition/outbox
claim crash -> expired lease reclaim
worker response after lease loss cannot overwrite newer result
no DB transaction held over external HTTP
bounded batch and durable next_attempt_at/backoff
```

## Scheduler / n8n runtime

If n8n schedules recovery, exact pinned runtime `2.33.4` must prove:

```text
schedule workflow imports/publishes
only Commerce recovery endpoint is called
body is empty
existing automation Bearer is used
no Code/Function authority node
no direct provider/DB/S3 call
one schedule invocation produces one bounded Commerce scan
order recovery replay re-enters existing protected order workflow and converges
```

---

# 13. VALIDATION GATE

Before `READY_FOR_REVIEW`, Implementer must provide a fresh exact-head validation SHA and run/job evidence.

Required gate:

```text
Python 3.11
PostgreSQL 16
sitescore-commerce expected version 0.6.0
migration head 0005_recovery_reconciliation
migration upgrade -> downgrade -> re-upgrade PASS
full commerce suite PASS
all recovery PostgreSQL adversarial tests PASS
n8n static PASS
pinned n8n 2.33.4 runtime recovery proof PASS
frozen FAZ 3/4/5 total 1504 PASS
private S3 regression PASS
Redis/Celery frozen transport PASS
frozen-scope scan PASS
secret-boundary scan PASS
```

Any validation workflow added only for checkpoint proof may be removed after successful validation, but validated-SHA -> final-head delta must contain only independently reviewable non-semantic validation-workflow removal(s).

---

# 14. IMPLEMENTER EXECUTION PROTOCOL

Implementer must:

1. Freshly read this `reviewer.md` and live `main`.
2. Verify `main == bdf43a891ca14941ba2f2c4f115e4a15bec0015a` before branching.
3. Create/use only `faz6/6-5-recovery-reconciliation` from that exact base.
4. Implement only FAZ 6.5.
5. Open one PR targeting `main`.
6. Run fresh exact-head validation.
7. Update `implementer.md` with exact base/head, PR, migration/version, changed scope, test counts, CI run/job IDs, recovery invariants and any unresolved concern.
8. Set `IMPLEMENTER_STATE: READY_FOR_REVIEW` and STOP.

Implementer must not merge and must not request/assume LOCK.

Reviewer will independently inspect the exact final head and may return `HARDENING_REQUIRED` or `READY_TO_LOCK`.

```text
FAZ 6.5: IMPLEMENTATION_AUTHORIZED
START_6_5: YES
START_6_FINAL: NO
```

Reviewer STOP.