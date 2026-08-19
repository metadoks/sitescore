# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.2
CHECKPOINT_TITLE: Paid Fulfillment Binding + Canonical Unfulfillable Full Refund Authority

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 8027239b4b168e98e8ee16e15787366632017156
LIVE_MAIN_SHA_AT_REVIEW: 8027239b4b168e98e8ee16e15787366632017156
CODE_BRANCH: faz6/6-2-fulfillment-refund
PR: #25
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE: TRUE
PR_MERGED: FALSE
REVIEWED_HEAD_SHA: 7d9ad5dbf9bfc045a7d7fb971dc80c6851e9ec08

VALIDATED_SHA: eeff565f318475b4b5796d92502894998332db15
VALIDATION_RUN_ID: 32256557493
VALIDATION_JOB_ID: 96079494257
VALIDATION_CONCLUSION: SUCCESS
VALIDATED_TO_FINAL_COMMITS: 1
VALIDATED_TO_FINAL_DELTA: ONLY .github/workflows/faz6-6-2-validation.yml REMOVAL

COM62-H001: OPEN
BLOCKERS: COM62-H001
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: LOCKED
FAZ_6_1_STATUS: LOCKED
FAZ_6_2_STATUS: HARDENING_REQUIRED
START_6_3: NO
```

---

# 1. EXACT STATE REVIEWED

Reviewer independently re-read live GitHub and reviewed the exact final PR head.

```text
main:
8027239b4b168e98e8ee16e15787366632017156

PR #25:
OPEN
DRAFT: FALSE
MERGEABLE: TRUE
MERGED: FALSE

base:
main@8027239b4b168e98e8ee16e15787366632017156

reviewed head:
7d9ad5dbf9bfc045a7d7fb971dc80c6851e9ec08

validated SHA:
eeff565f318475b4b5796d92502894998332db15

validated -> final:
1 commit ahead
0 behind
only changed file:
.github/workflows/faz6-6-2-validation.yml
status: removed
```

Base -> reviewed head contains only `sitescore-commerce/` product changes. Frozen FAZ 3/4/5 runtime source remains untouched. No 6.3 n8n workflow, 6.4 delivery/email, or 6.5 broad reconciliation scanner was introduced.

---

# 2. POSITIVE REVIEW RESULTS

The following major 6.2 authority boundaries were confirmed on the reviewed head:

```text
sitescore-commerce == 0.3.0
0003_fulfillment_refund migration present
SiteScore consumed through authenticated HTTP /v1 only
no runtime sitescore-api import/dependency/direct table access
stable durable sitescore:analysis:v1:<order_id> operation identity
analysis payload/target snapshot persisted before provider I/O
analysis/report IDs bound durably and non-overwritable
fresh server-side terminal reproof before refund eligibility
stable sitescore:refund:v1:<order_id> operation identity
PaymentIntent retrieved and server-validated before refund
provider refunds listed before refund creation
explicit full amount derived from provider payment evidence
Stripe API version explicitly pinned
payment/refund/provider IDs not caller-authorable
POST automation trigger requires exact bearer before order lookup
POST automation body must be empty
sanitized automation status response
provider I/O remains outside durable row-lock transaction
migration namespace remains commerce-owned
```

The successful path terminates at `delivery_pending`; no report content download or delivery authority was implemented in 6.2.

---

# 3. COM62-H001 — OPEN

## SiteScore-shaped mismatched provider refund is misclassified as benign external full refund

The checkpoint contract deliberately distinguishes three cases:

```text
1. exact SiteScore refund metadata match
   -> recover/reconcile

2. truly unattributed external already-succeeded exact full refund
   -> reconcile as externally fully refunded

3. SiteScore-shaped but mismatching refund metadata
   -> attention_required, fail closed
```

The implementation does not preserve that distinction.

Current logic first defines an exact matching SiteScore refund using all durable metadata:

```text
sitescore_order_id
sitescore_refund_operation
sitescore_refund_reason
```

If no exact match is found, every remaining provider refund is treated by the generic external-history branch. That branch accepts a refund as an external full refund when there is exactly one refund with:

```text
same PaymentIntent
same currency
positive amount
status == succeeded
amount == original full amount
```

It does not first reject a refund that already carries reserved SiteScore refund metadata with a conflicting order, operation, or reason.

Therefore this provider evidence can currently be accepted as `external_full=True`:

```text
refund.payment_intent = exact durable PaymentIntent
refund.amount = exact full amount
refund.currency = USD
refund.status = succeeded
refund.metadata.sitescore_order_id = DIFFERENT ORDER
refund.metadata.sitescore_refund_operation = stripe_full_refund_v1
refund.metadata.sitescore_refund_reason = analysis_failed
```

The refund fails the exact SiteScore match, falls into the generic external-full branch, and can transition the local order/payment state to `refunded` instead of `attention_required`.

This is a durable money-lineage / authority misattribution and directly violates the documented fail-closed provider-history policy. It is therefore a Reviewer blocker.

```text
COM62-H001: OPEN
```

---

# 4. REQUIRED HARDENING

Implementer must harden provider-history classification before the external-full recovery path.

Reserved SiteScore refund metadata keys are at least:

```text
sitescore_order_id
sitescore_refund_operation
sitescore_refund_reason
```

Required behavior:

```text
exact expected SiteScore metadata identity
-> matching SiteScore recovery path

NO reserved SiteScore refund metadata present
+ exactly one same-PaymentIntent exact succeeded full refund
-> external_full recovery may remain allowed

ANY reserved SiteScore refund metadata present
but expected SiteScore refund identity is not exact
-> attention_required
-> no refunded transition
-> no new refund create
-> no blind top-up
```

Partially populated SiteScore metadata is also SiteScore-shaped and must fail closed; it must not be reclassified as unattributed external evidence.

The implementation may choose a helper/classifier, but the semantic boundary above is mandatory.

---

# 5. REQUIRED ADVERSARIAL COVERAGE

Add tests proving at least:

```text
1. existing exact full succeeded refund + wrong sitescore_order_id
   -> attention_required
   -> no refunded transition
   -> no create

2. existing exact full succeeded refund + wrong sitescore_refund_operation
   -> attention_required
   -> no refunded transition
   -> no create

3. existing exact full succeeded refund + wrong sitescore_refund_reason
   -> attention_required
   -> no refunded transition
   -> no create

4. partially populated reserved SiteScore refund metadata
   -> attention_required
   -> no external_full classification

5. truly unattributed metadata == {}
   + exact succeeded full refund
   -> external_full reconciliation still works
   -> no second refund

6. exact matching SiteScore metadata
   -> matching recovery still works
   -> no second refund
```

At least the state-changing cases must be exercised against real PostgreSQL where relevant so durable order/payment/refund-operation state is proved, not only an in-memory fake.

---

# 6. VALIDATION EVIDENCE

Reviewer independently verified the existing exact-head validation evidence:

```text
workflow:
faz6-6-2-exact-head-validation

validated SHA:
eeff565f318475b4b5796d92502894998332db15

run:
32256557493

job:
96079494257

conclusion:
SUCCESS

Python:
3.11.16

PostgreSQL:
16.15

sitescore-commerce:
237 PASS

frozen total:
1504 PASS

combined pytest total:
1741 PASS

migration upgrade -> downgrade base -> upgrade head:
PASS

0003 commerce namespace proof:
PASS

secret scan:
PASS

frozen-scope scan:
PASS

private S3-compatible storage regression:
PASS

Redis/Celery transport regression:
PASS
```

The green suite does not resolve COM62-H001 because the current tests cover exact matching SiteScore refunds, partial/multiple/conflicting history, and a truly unattributed `{}` external full refund, but do not cover a full succeeded refund carrying reserved SiteScore metadata with a mismatched SiteScore identity.

---

# 7. REVIEWER DECISION

```text
FAZ 6.2: HARDENING_REQUIRED
PR: #25
REVIEWED_HEAD_SHA: 7d9ad5dbf9bfc045a7d7fb971dc80c6851e9ec08

COM62-H001: OPEN
BLOCKERS: COM62-H001

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
START_6_3: NO
```

Implementer must harden only PR #25 / FAZ 6.2, update `implementer.md` with a new exact head and exact validation evidence, then stop at `READY_FOR_REVIEW`.

No LOCK is authorized. Reviewer STOP.
