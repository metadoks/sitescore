# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.4
CHECKPOINT_TITLE: Delivery Grant + Transactional Email

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba
LIVE_MAIN_SHA_AT_REVIEW: 7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba
CODE_BRANCH: faz6/6-4-delivery-grant-email
PR: #27
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE: TRUE
PR_MERGED: FALSE
REVIEWED_HEAD_SHA: 11d8ad7c9b9067b0b21eaf733fbfa0ddfb0bc762

VALIDATED_SHA: 2501d6af71b4c9057a8f5b3008d9c4db3ba15377
COMMERCE_VALIDATION_RUN_ID: 32306516241
COMMERCE_VALIDATION_JOB_ID: 96240342784
FROZEN_VALIDATION_RUN_ID: 32306516300
FROZEN_VALIDATION_JOB_ID: 96240342892
VALIDATION_CONCLUSION: SUCCESS
VALIDATED_TO_FINAL_COMMITS: 2
VALIDATED_TO_FINAL_DELTA: ONLY TEMPORARY 6.4 VALIDATION WORKFLOW REMOVALS

COMMERCE_VERSION: 0.5.0
MIGRATION_HEAD: 0004_delivery_email
N8N_RUNTIME_VERSION: 2.33.4
N8N_VALIDATED_IMAGE_DIGEST: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
WORKFLOW_SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1

DEL64-H001: OPEN
DEL64-H002: OPEN
BLOCKERS: DEL64-H001, DEL64-H002
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
FAZ_6_4_STATUS: HARDENING_REQUIRED
START_6_5: NO
```

---

# 1. EXACT STATE REVIEWED

Reviewer independently re-read live GitHub and reviewed the exact final PR head.

```text
main:
7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba

PR #27:
OPEN
DRAFT: FALSE
MERGEABLE: TRUE
MERGED: FALSE

base:
main@7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba

reviewed final head:
11d8ad7c9b9067b0b21eaf733fbfa0ddfb0bc762

validated SHA:
2501d6af71b4c9057a8f5b3008d9c4db3ba15377
```

Validated SHA -> final HEAD is exactly two commits and only removes the two temporary FAZ 6.4 validation workflows. No product/test/runtime content changed after validation.

Base -> reviewed head scope is confined to `sitescore-commerce` 6.4 delivery/email work and the minimum reserved `automation/n8n` delivery branch extension. No frozen FAZ 3/4/5 source mutation and no FAZ 6.5 broad recovery scanner were observed.

---

# 2. POSITIVE REVIEW RESULTS

Reviewer confirmed the following on the exact reviewed head:

```text
sitescore-commerce == 0.5.0
migration head == 0004_delivery_email
256-bit random URL-safe delivery token
digest-only SHA-256 token persistence
no plaintext/encrypted/reversible raw-token column
exact 7-day grant lifetime
revocable and reusable grants
exact order/report grant binding
public /d/{opaque_token} capability proxy
fresh frozen SiteScore report re-verification before download
fresh frozen /content retrieval
PDF MIME / length / Content-SHA256 / local SHA-256 verification
private no-store + no-referrer + nosniff download headers
server-owned COMMERCE_PUBLIC_BASE_URL
Postmark token/from/template/recipient remain server-owned
Postmark call occurs outside DB transaction/row lock
provider MessageID is durable and unique when accepted
provider_accepted + valid bound grant/report transitions atomically to fulfilled/paid/completed
known provider_accepted replay short-circuits duplicate send
uncertain retry can create a fresh grant while prior possible emailed grant remains valid
bounded delivery attempts
email failure does not create refund/payment/analysis/report failure authority
n8n /deliver request body is empty
n8n receives no raw token, recipient, Postmark token, SiteScore key or report bytes
n8n delivery continuation goes through existing finite horizon + Wait path
zero Code/Function business-authority nodes
```

Migration upgrade/downgrade/re-upgrade, PostgreSQL state tests, secret scans and frozen boundary are also otherwise acceptable.

These positive results do not close the two blockers below.

---

# 3. DEL64-H001 — OPEN

## Ambiguous Postmark HTTP-200 acceptance evidence is persisted as definitive non-retryable rejection

The 6.4 contract requires precise provider states and explicitly says uncertain provider outcome caused by timeout, connection loss or response loss must become `provider_uncertain`, never fabricated acceptance or definitive rejection.

The official Postmark single template-send success contract uses:

```text
HTTP 200
ErrorCode = 0
MessageID
To
SubmittedAt
```

The implementation correctly refuses to call HTTP 200 alone accepted. However, after receiving HTTP 200 it currently maps malformed/incomplete success evidence to `PostmarkRejected(... retryable=False)`.

Current examples include:

```text
HTTP 200 + malformed/non-JSON body
HTTP 200 + non-object body
HTTP 200 + invalid/missing ErrorCode
HTTP 200 + ErrorCode=0 + missing MessageID
HTTP 200 + ErrorCode=0 + invalid MessageID
HTTP 200 + ErrorCode=0 + recipient mismatch
HTTP 200 + ErrorCode=0 + invalid SubmittedAt
```

`DeliveryService` catches those as `PostmarkRejected` and calls `record_rejected()`.

For any non-retryable rejection, the durable store immediately transitions:

```text
order_state = attention_required
payment_state = paid
fulfillment_state = delivery_failed
```

This is unsafe for a success-like HTTP 200 whose response body/evidence was corrupted, truncated, incomplete, or otherwise not trustworthy. Postmark may already have accepted the email while commerce has merely lost enough acceptance evidence to bind a MessageID. The customer may therefore receive a valid link while commerce durably records a definitive provider rejection and stops normal delivery recovery.

That is a concrete provider-state/recovery correctness defect.

Required semantics:

```text
explicit, trustworthy provider rejection
-> provider_rejected

ambiguous outcome where acceptance cannot be proven and rejection also cannot be proven
-> provider_uncertain
```

At minimum, after HTTP 200 these cases must NOT become definitive non-retryable `provider_rejected` merely because acceptance evidence cannot be validated:

```text
malformed/truncated/non-JSON response
non-object response
missing/invalid ErrorCode
ErrorCode == 0 but required acceptance evidence is missing/invalid/mismatched
```

They must fail closed as NOT accepted while preserving the uncertainty/retry model. `ErrorCode != 0` remains affirmative provider rejection evidence and may remain `provider_rejected`. Clear non-2xx provider errors may retain the existing rejected/retryable policy as appropriate.

Do not weaken acceptance validation: no case above may be marked `provider_accepted` without all required evidence.

Required tests:

```text
1. HTTP 200 with malformed/truncated JSON -> provider_uncertain, not fulfilled
2. HTTP 200 with invalid/missing ErrorCode -> provider_uncertain, not fulfilled
3. HTTP 200 + ErrorCode=0 but missing/invalid MessageID -> provider_uncertain, not fulfilled
4. HTTP 200 + ErrorCode=0 but To/SubmittedAt cannot be safely bound -> provider_uncertain, not fulfilled
5. uncertain attempt leaves payment paid and retry guidance available while below attempt limit
6. replay creates fresh attempt/grant; prior grant is not blindly revoked
7. later fully validated acceptance -> one durable fulfilled/paid/completed terminal state
8. explicit nonzero ErrorCode remains provider_rejected
```

Use real PostgreSQL for the durable state assertions and isolated fake Postmark HTTP responses, including a raw malformed/truncated 200 body rather than only JSON-shaped fixtures.

```text
DEL64-H001: OPEN
```

---

# 4. DEL64-H002 — OPEN

## Required n8n restart-during-delivery-wait recovery proof is missing

The Reviewer 6.4 validation gate explicitly requires pinned n8n 2.33.4 runtime proof for:

```text
restart during delivery wait converges
provider uncertainty does not fabricate fulfilled
```

The current runtime suite proves:

```text
N8N_DELIVERY_ACCEPTED_TO_FULFILLED=PASS
N8N_DELIVERY_RETRY_PACING=PASS
N8N_DELIVERY_FAILED_STOP=PASS
```

and retains the older 6.3 restart proof:

```text
N8N_REAL_ADVANCE_WAIT_RESTART=PASS
```

But it does not separately stop/restart n8n while a 6.4 delivery execution is in its Wait/retry cycle and prove that the delivery branch resumes/converges from durable commerce truth. A restart proof for the analysis `/advance` branch is not a substitute for the newly introduced `/deliver` branch.

The graph design appears to reuse the same finite Wait path, which is positive, but the checkpoint explicitly requires runtime evidence for the new delivery branch because delivery has distinct at-least-once provider side effects and grant/email retry semantics.

Required runtime proof on exact n8n 2.33.4:

```text
1. trigger an order whose first /deliver remains retryable/provider-uncertain guidance
2. confirm execution enters Wait after bodyless /deliver
3. stop n8n while that delivery execution is waiting
4. restart with the same durable n8n volume/state
5. prove the execution resumes, or a safe duplicate trigger converges from commerce durable state
6. prove no fabricated fulfilled state occurs before commerce reports accepted evidence
7. prove bounded delivery retry/poll horizon is still enforced
8. prove no new analysis/report/payment identity is created
```

Add an explicit runtime evidence label such as:

```text
N8N_DELIVERY_WAIT_RESTART=PASS
```

If the test models provider uncertainty, also prove that n8n treats it only through commerce `next_action` guidance and never authors provider truth itself.

```text
DEL64-H002: OPEN
```

---

# 5. EXACT-HEAD VALIDATION REVIEWED

The existing validation remains useful positive evidence but must be rerun after hardening.

Current exact validated SHA:

```text
2501d6af71b4c9057a8f5b3008d9c4db3ba15377
```

Commerce/n8n run:

```text
run: 32306516241
job: 96240342784
conclusion: SUCCESS
PostgreSQL: 16.15
sitescore-commerce: 313 PASS
n8n static: 9 PASS
n8n runtime: 2.33.4
```

Frozen run:

```text
run: 32306516300
job: 96240342892
conclusion: SUCCESS
checkout: exact validated SHA
frozen FAZ 3/4/5: 1504 PASS
sitescore-report: 24 PASS
sitescore-api: 105 PASS
private S3 regression: PASS
Redis/Celery transport: PASS
frozen-scope scan: PASS
secret boundary scan: PASS
```

Existing n8n image digest:

```text
n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
```

Existing workflow SHA-256:

```text
02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
```

A fresh exact-head commerce+n8n validation and frozen validation are required after DEL64-H001/H002 hardening. Any validated-SHA -> final-head delta must again be independently reviewable and non-semantic.

---

# 6. HARDENING SCOPE

Implementer must harden only PR #27 / FAZ 6.4.

Do NOT:

```text
reopen frozen FAZ 3/4/5
change payment/refund authority
change analysis/report truth
add Postmark webhooks
add broad FAZ 6.5 recovery scanner
persist raw/encrypted delivery tokens
move Postmark secrets into n8n
bypass the server-owned /deliver operation
change n8n runtime away from 2.33.4
```

Expected hardening surface is narrowly:

```text
Postmark outcome classification + tests
PostgreSQL durable uncertainty/replay tests
n8n delivery-wait restart runtime proof
necessary 6.4 docs/static-test updates
fresh exact-head validation workflows/evidence
```

---

# 7. REVIEWER DECISION

```text
FAZ 6.4: HARDENING_REQUIRED
PR: #27
REVIEWED_HEAD_SHA: 11d8ad7c9b9067b0b21eaf733fbfa0ddfb0bc762

DEL64-H001: OPEN
DEL64-H002: OPEN
BLOCKERS: DEL64-H001, DEL64-H002

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
USER_LOCK_AUTHORIZED: NO
START_6_5: NO
```

Implementer must harden the same PR, produce a new exact final head plus fresh exact-head CI evidence, update `implementer.md` to `READY_FOR_REVIEW`, and STOP.

No LOCK is authorized. FAZ 6.5 remains closed. Reviewer STOP.
