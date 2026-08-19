# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.1
CHECKPOINT_TITLE: Stripe Webhook Payment Authority + Durable Reconciliation

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: af3b9567d644f6bcf0410af704dd7d86de41b5ce
LIVE_MAIN_SHA_AT_REVIEW: af3b9567d644f6bcf0410af704dd7d86de41b5ce
CODE_BRANCH: faz6/6-1-webhook-payment-authority
PR: #24
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE: TRUE
PR_MERGED: FALSE
REVIEWED_HEAD_SHA: 89f9f41b381412775aae732e4dc75d2b56919ade

VALIDATED_SHA: 6b06b590d7512ff51ba2a7655aeaff79013af53b
VALIDATION_RUN_ID: 32247997208
VALIDATION_JOB_ID: 96052624136
VALIDATION_CONCLUSION: SUCCESS
VALIDATED_TO_FINAL_COMMITS: 1
VALIDATED_TO_FINAL_DELTA: ONLY .github/workflows/faz6-6-1-validation.yml REMOVAL

COM61-H001: OPEN
BLOCKERS: COM61-H001
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: LOCKED
FAZ_6_1_STATUS: HARDENING_REQUIRED
START_6_2: NO
```

---

# 1. EXACT STATE REVIEWED

Reviewer independently verified live GitHub state before issuing this decision.

```text
main:
af3b9567d644f6bcf0410af704dd7d86de41b5ce

PR #24:
OPEN
DRAFT: FALSE
MERGEABLE: TRUE
MERGED: FALSE

base:
main@af3b9567d644f6bcf0410af704dd7d86de41b5ce

final reviewed head:
89f9f41b381412775aae732e4dc75d2b56919ade

validated SHA:
6b06b590d7512ff51ba2a7655aeaff79013af53b

validated -> final:
1 commit
only .github/workflows/faz6-6-1-validation.yml removed

final changed product files:
12
all under sitescore-commerce/

frozen FAZ 3/4/5 runtime source changes:
NONE
```

Authoritative CI evidence at validated SHA:

```text
workflow: faz6-6-1-exact-head-validation
run: 32247997208
job: 96052624136
conclusion: SUCCESS
Python: 3.11.15
PostgreSQL: 16.15
sitescore-commerce: 83 PASS
frozen total: 1504 PASS
combined total: 1587 PASS
migration upgrade/downgrade/upgrade: PASS
migration namespace: PASS
secret scan: PASS
frozen-scope scan: PASS
private S3-compatible regression: PASS
Redis/Celery regression: PASS
```

These green tests do not close COM61-H001 because the missing adversarial case is not represented by the current duplicate-event tests.

---

# 2. REVIEWER-CONFIRMED 6.1 CONTROLS

The following core architecture is present and materially aligned with the 6.1 contract:

```text
POST /v1/webhooks/stripe exists
exact raw body is used before signature verification
Stripe-Signature is required
256 KiB ingress limit exists
300 second signature tolerance exists
Stripe webhook secret is server-side
Event API version is checked when present
Event and retrieved Session livemode are checked
required V1 event surface is completed + expired
async payment events are non-authoritative/ignored
webhook event type alone never marks paid
Checkout Session is retrieved server-side
line items are retrieved server-side
mode/order/product/catalog/Price/quantity/currency bindings are enforced
paid requires complete + paid + PaymentIntent identity
no_payment_required is not accepted as paid
webhook-first provider-success/local-bind-loss recovery exists
existing different Session binding is not overwritten
server-observed reconciliation evidence is persisted
pending -> paid transition exists
pending -> expired transition exists
paid is not downgraded by late expiration
expired is not silently upgraded by contradictory paid truth
paid transition + order.paid.v1 outbox are in one PostgreSQL transaction
unique (order_id, outbox_type) prevents duplicate paid outbox
outbox dispatcher is absent by design
analysis/report/refund/n8n/Postmark/delivery are absent
no PostgreSQL transaction is intentionally held across Stripe network I/O
```

The blocker below is specifically about durable event identity / retry recovery semantics.

---

# 3. COM61-H001 — RAW BODY HASH IS INCORRECTLY PART OF DUPLICATE EVENT IDENTITY

## Problem

Current `CommerceStore.record_stripe_event()` persists `raw_body_sha256`, which is correct as evidence.

However, on a repeated Stripe Event ID it currently compares this tuple:

```text
stripe_event_type
stripe_object_id
event_api_version
livemode
event_created_at
raw_body_sha256
```

against the incoming delivery and raises `EventIdentityConflict` if any element differs.

This incorrectly promotes the exact raw HTTP-body byte representation to durable event identity.

The 6.1 contract requires:

```text
Event ID is the minimum transport dedupe authority.
same Stripe event ID delivered repeatedly -> one durable inbox identity
received-but-not-processed duplicate -> resumes processing
```

`raw_body_sha256` was required as delivery evidence, not as a guarantee that every legitimate redelivery of the same Event ID is byte-for-byte identical.

Stripe requires signature verification against each delivery's exact raw request body, but duplicate-event guidance is based on the Stripe Event ID. Stripe does not provide a contract that all valid deliveries/manual redeliveries of one Event ID must have identical JSON byte serialization.

Therefore a legitimate semantically identical Event ID can be validly signed yet differ only in harmless JSON serialization details such as whitespace or key ordering. Under the current implementation:

```text
first valid delivery
-> inbox row persisted as received
-> processing is interrupted or Stripe reconciliation returns retryable 503

same Stripe Event ID delivered again
-> valid Stripe signature
-> same type/object/version/mode/created semantics
-> raw JSON bytes differ harmlessly
-> raw_body_sha256 differs
-> EventIdentityConflict
-> HTTP 409
-> event can no longer resume processing through that retry path
```

If this occurs before the paid transition, a real paid Checkout can remain pending even though Stripe is correctly redelivering the same event.

This is a meaningful payment recovery correctness failure and therefore a hardening blocker.

```text
COM61-H001: OPEN
```

---

# 4. REQUIRED HARDENING FOR COM61-H001

Do not remove raw-body signature verification and do not stop recording a raw-body hash as evidence.

Instead separate:

```text
TRANSPORT / SEMANTIC EVENT IDENTITY
from
DELIVERY-BYTE EVIDENCE
```

Required behavior:

1. `stripe_event_id` remains the durable dedupe key.
2. Essential semantic conflict checks may include immutable signed Event semantics such as:
   - event type
   - Stripe object/session ID
   - event API version
   - livemode
   - event created timestamp
   - any other deliberately persisted immutable correlation field required by the contract.
3. `raw_body_sha256` MUST NOT by itself make a semantically identical redelivery of the same Stripe Event ID an identity conflict.
4. Keep a raw-body digest as audit evidence. Acceptable designs include:
   - preserving the first-delivery digest only, or
   - maintaining separate last-delivery/delivery-evidence semantics if explicitly modeled.
5. A true semantic conflict for the same Stripe Event ID must still fail closed and never mutate payment/order truth.
6. A same-ID, same-semantic, different-raw-bytes delivery must:
   - dedupe to the same inbox identity,
   - increment retry/attempt evidence as appropriate,
   - return safe 2xx if already processed, or
   - resume processing if still `received`.
7. Do not weaken Stripe signature verification: every incoming raw body must still be verified against its own `Stripe-Signature` before inbox mutation.

---

# 5. REQUIRED ADVERSARIAL TESTS

Add deterministic tests covering at minimum:

```text
A. Same Event ID + same semantic event + same raw bytes
   -> one inbox identity
   -> retry-safe

B. Same Event ID + same semantic event + different valid JSON serialization
   example: whitespace/key-order difference
   -> each delivery independently passes Stripe signature verification
   -> one inbox identity
   -> NO EventIdentityConflict solely because raw hash differs

C. Case B while first delivery remains received/unprocessed due provider timeout
   -> second delivery resumes reconciliation
   -> paid transition succeeds when provider becomes authoritative
   -> exactly one order.paid.v1 outbox

D. Same Event ID + true semantic conflict
   e.g. different event type or different Checkout Session ID
   -> fail closed
   -> no new money transition

E. Real PostgreSQL concurrency/retry regression remains green
```

Use the official Stripe verifier in at least the serialization-difference test so the proof demonstrates two separately valid signatures over two different raw byte strings representing the same semantic Event.

---

# 6. SCOPE / FREEZE REQUIREMENTS

Hardening remains strictly inside FAZ 6.1.

Allowed scope:

```text
sitescore-commerce/
checkpoint-specific tests/docs
optional temporary exact-head CI workflow
```

Do not implement:

```text
6.2 fulfillment
analysis dispatch
report dispatch
refunds
n8n
Postmark
delivery grants
public report download
```

Frozen FAZ 3/4/5 source packages remain immutable.

No contract change, design escalation, or locked-checkpoint reopen is required for this fix.

---

# 7. REVIEWER DECISION

```text
FAZ 6.1: HARDENING_REQUIRED
PR: #24
REVIEWED_HEAD_SHA: 89f9f41b381412775aae732e4dc75d2b56919ade

COM61-H001: OPEN
BLOCKERS: COM61-H001

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
START_6_2: NO
```

Implementer must harden the same PR/checkpoint, publish a fresh exact-head validation result, update `implementer.md` to `READY_FOR_REVIEW`, and STOP.

Reviewer does not merge.
Reviewer STOP.
