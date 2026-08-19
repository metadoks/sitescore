# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.0
CHECKPOINT_TITLE: Commerce / Order Domain + Stripe Checkout Foundation

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 0e370940ee5c8c1253db72fa7e33078fb4ef3b2c
CODE_BRANCH: faz6/6-0-commerce-order-checkout
PR: #23
REVIEWED_HEAD_SHA: 6790cc2eccb858f80857103e99f9b5562e8db485

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: HARDENING_REQUIRED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

BLOCKERS:
- COM60-H001 — Checkout retry request is not durably replayable with exact original Stripe parameters across restart/config drift.
- COM60-H002 — Alembic 0001 downgrade attempts to drop the commerce schema while commerce.alembic_version still occupies that schema, making the implemented rollback path unsafe/broken.
```

---

# 1. REVIEW SCOPE / EXACT GITHUB STATE

Reviewer independently re-read the live repository and exact PR candidate.

Verified:

```text
live main:
0e370940ee5c8c1253db72fa7e33078fb4ef3b2c

PR #23:
OPEN
DRAFT: FALSE
MERGEABLE: TRUE
MERGED: FALSE

PR base:
main@0e370940ee5c8c1253db72fa7e33078fb4ef3b2c

PR head:
6790cc2eccb858f80857103e99f9b5562e8db485

merge-base with frozen main:
0e370940ee5c8c1253db72fa7e33078fb4ef3b2c

base -> head:
4 commits ahead / 0 behind
22 changed files
all changed product files under sitescore-commerce/
no frozen FAZ 3/4/5 runtime source changed
```

Implementer handoff and live PR metadata agree on exact head/base/branch/PR identity.

The reviewed package is:

```text
sitescore-commerce==0.1.0
```

The reviewed migration is:

```text
0001_commerce_order_checkout
```

The reviewed Stripe pins are:

```text
stripe==15.4.0
STRIPE_API_VERSION=2026-07-29.dahlia
```

No FAZ 6.1+ subsystem was found in the PR.

---

# 2. POSITIVE FINDINGS — ACCEPTED PORTIONS

The following portions of the 6.0 implementation are accepted at reviewed head, subject to regression preservation during hardening:

```text
new isolated sitescore-commerce package
commerce PostgreSQL schema
commerce-owned Alembic version namespace
strict POST /v1/orders
server-generated order_id
strict caller request with extra=forbid
location_report_v1 allowlist
caller amount/currency/Price/quantity/discount/payment forgery rejection
four-sector local AnalysisRequest compatibility boundary
no runtime sitescore_api import
server-owned Stripe Price configuration
hosted Checkout / mode=payment / card-only / quantity=1
server-owned client_reference_id + metadata binding
Stripe SDK pin 15.4.0
Stripe API pin 2026-07-29.dahlia
separate order/payment/fulfillment state dimensions
6.0-only initial state tuple pending_payment/pending/not_started
no paid transition
PostgreSQL-backed caller idempotency
raw caller idempotency key not persisted
stable server-owned Stripe operation key
no DB transaction held across Stripe network call
sanitized provider/persistence HTTP errors
success/cancel browser correlation is not payment authority
no frozen package source changes
```

The PostgreSQL concurrency test demonstrates that same caller key + same payload converges to one durable order and one checkout-operation row.

These accepted findings do not override the blockers below.

---

# 3. COM60-H001 — DURABLE STRIPE RETRY PARAMETER SNAPSHOT MISSING

## Status

```text
COM60-H001: OPEN
SEVERITY: BLOCKER
CATEGORY: external-call uncertainty / provider idempotency / money-path integrity
```

## Contract violated

The 6.0 Reviewer contract requires:

```text
all retries for the same Checkout creation operation
-> exact same Stripe idempotency key
-> exact same parameters
```

and requires recovery after timeout/dropped response to reuse the same logical provider operation.

## Actual implementation

The durable checkout row stores:

```text
provider_idempotency_key
catalog_version
product_code
stripe_price_id
```

but the service does not replay the provider request from that durable snapshot.

On every unbound retry it executes conceptually:

```text
entry = catalog_from_settings(current_settings)
...
create_checkout(
    entry = current settings-derived catalog entry,
    success_url = success_url(current_settings, order_id),
    cancel_url = cancel_url(current_settings, order_id),
    provider_idempotency_key = durable checkout row key,
)
```

Therefore the provider idempotency key is durable, but the full request parameter set is not.

The stored `checkout_sessions.stripe_price_id` is not used to reconstruct the retry request. Resolved success/cancel URLs are not persisted at all.

## Concrete failure path

```text
1. order + checkout operation committed with Price A / redirect config A
2. Stripe request is attempted
3. response is lost OR process crashes before local binding
4. deployment restarts with Price B and/or redirect config B
5. same order is retried
6. same Stripe idempotency key is reused
7. request is rebuilt with Price/redirect parameters B
```

This creates two unsafe outcomes:

```text
A) Stripe accepted the original request
   -> same key + different parameters cannot safely replay the original operation
   -> deterministic recovery breaks

B) Stripe never accepted the original request
   -> retry can create the Checkout Session from changed Price/redirect configuration
   -> durable local operation snapshot and actual provider operation diverge
```

A commerce payment path cannot depend on deployment configuration remaining unchanged across the exact crash window the idempotency design is intended to survive.

## Required hardening

Before any Stripe POST, persist an immutable provider-operation request snapshot sufficient to reconstruct the exact logical Checkout request after restart.

At minimum:

```text
server-selected stripe_price_id
catalog_version
product_code
quantity / operation version semantics
resolved success_url
resolved cancel_url
customer email or immutable reference to the exact durable order value
provider idempotency key
```

Implementation may persist the full safe request projection or equivalent immutable fields, but retries MUST be built from durable operation truth rather than fresh mutable deployment settings.

The already persisted server Price ID must actually be used for retry construction.

`validate_checkout_result()` must validate against the durable operation/catalog snapshot used for that request, not a newly resolved current catalog entry.

Do not persist Stripe secret material.

Do not create a new order or a new provider idempotency key to solve this.

## Required adversarial tests

Add explicit tests proving at least:

```text
COM60-H001-T1
create durable operation with Price A
-> mutate runtime Price config to Price B before retry
-> retry still sends Price A
-> same provider idempotency key

COM60-H001-T2
create durable operation with redirect bases A
-> mutate runtime redirect config to B before retry/restart simulation
-> retry still sends exact resolved A success/cancel URLs
-> same provider idempotency key

COM60-H001-T3
provider succeeds but local bind fails
-> later retry after config drift
-> same exact provider request projection is replayed
-> same returned Session can be durably bound

COM60-H001-T4
current catalog/config drift cannot mutate an existing unbound checkout operation
```

Use PostgreSQL-backed evidence for the restart/durable-snapshot behavior; an in-memory fake alone is not sufficient for the durability claim.

---

# 4. COM60-H002 — IMPLEMENTED ALEMBIC DOWNGRADE IS NOT SAFE

## Status

```text
COM60-H002: OPEN
SEVERITY: BLOCKER
CATEGORY: migration correctness / rollback integrity
```

## Actual implementation

`0001_commerce_order_checkout.py` defines a real downgrade path that conceptually does:

```text
drop checkout_sessions
drop order_idempotency
drop orders
DROP SCHEMA IF EXISTS commerce
```

However the migration config deliberately places Alembic's version table at:

```text
commerce.alembic_version
```

Alembic still needs that version table while processing the revision transition. Thus the schema is not empty when the revision's downgrade body attempts `DROP SCHEMA IF EXISTS commerce`.

The current CI validates only forward `upgrade head`; it does not exercise the implemented downgrade path.

## Failure consequence

The repository advertises an executable downgrade function that can fail during controlled rollback because the migration attempts to remove the namespace containing its own live version bookkeeping table.

This is a concrete migration correctness failure, not a request for a new rollback feature.

## Required hardening

Choose a migration-safe solution that preserves the isolated commerce Alembic namespace. Examples include:

```text
- do not drop the commerce schema inside revision downgrade; let the Alembic version-table lifecycle remain valid,
OR
- another demonstrably correct Alembic-compatible strategy
```

Do not use `CASCADE` merely to force deletion of migration bookkeeping without proving Alembic's post-downgrade behavior.

## Required PostgreSQL test

On real PostgreSQL 16, prove the implemented lifecycle actually works:

```text
fresh DB
-> upgrade head
-> downgrade base
-> upgrade head
-> PASS
```

Then re-prove schema/table/version isolation and constraints after the final upgrade.

---

# 5. CI / VALIDATION EVIDENCE REVIEWED

The Implementer-provided authoritative validation was independently inspected.

```text
validated SHA:
3cb5427b663ef38876c9f9f62e12e6bbb29f48d8

workflow:
faz6-6-0-exact-head-validation

run:
32238540680

job:
96023819318

conclusion:
SUCCESS
```

Reviewer verified from Actions evidence:

```text
Python 3.11.15
pip check PASS
stripe 15.4.0 exact pin PASS
PostgreSQL 16.15
sitescore-commerce 49 PASS
commerce migration forward upgrade PASS
commerce schema isolation PASS
secret scan PASS
frozen-scope scan PASS
sitescore-report 24 PASS
sitescore-api 105 PASS
sitescore-app 19 PASS
sitescore-pipeline 53 PASS
sitescore-benchmarks 191 PASS
sitescore-metrics 67 PASS
sitescore-spatial 180 PASS
sitescore-providers 418 PASS
sitescore-data 361 PASS
sitescore-core 86 PASS
frozen subtotal 1375 PASS
frozen total incl. report/api 1504 PASS
combined tests 1553 PASS
```

The validation run is real and green. The blockers are semantic/recovery/migration gaps not exercised by the current green tests.

Validated-to-final closure was also independently verified:

```text
3cb5427b663ef38876c9f9f62e12e6bbb29f48d8
->
6790cc2eccb858f80857103e99f9b5562e8db485

status: ahead
commits: 1
only file delta:
.github/workflows/faz6-6-0-validation.yml REMOVED
```

Therefore the existing green validation correctly applies to the current reviewed runtime/test/migration contents. Hardening will change those contents and requires fresh validation.

---

# 6. HARDENING SCOPE

Implementer must stay on the SAME checkpoint, branch and PR:

```text
CURRENT_CHECKPOINT: 6.0
CODE_BRANCH: faz6/6-0-commerce-order-checkout
PR: #23
```

Allowed hardening scope:

```text
commerce migration correction needed for H002
commerce durable checkout-operation snapshot/replay needed for H001
service/store/checkout adapter changes needed to consume durable snapshot
tests for H001/H002
documentation updates
exact-head validation workflow/evidence if required
```

Forbidden:

```text
6.1 webhook implementation
payment paid transition
payment reconciliation
paid outbox
analysis dispatch
report dispatch
refund
n8n
Postmark
delivery grant
public download
frozen FAZ 3/4/5 semantic changes
```

Do not solve either blocker by weakening idempotency, dropping request validation, forwarding caller authority, or changing frozen SiteScore semantics.

---

# 7. REQUIRED REVALIDATION

After both blockers are resolved, perform fresh validation on the hardened candidate.

At minimum re-prove:

```text
all sitescore-commerce tests PASS
new H001 durable replay/config-drift tests PASS
real PostgreSQL 16 upgrade -> downgrade -> upgrade PASS
commerce namespace/isolation PASS
exact Stripe SDK/API pins PASS
pip check PASS
secret scan PASS
frozen scope scan PASS
frozen report/API/packages baseline >= 1504 PASS
no 6.1+ scope leakage
```

If a temporary exact-head workflow is removed after successful validation, independently prove the validated-to-final delta is only that workflow removal, exactly as in the prior valid closure pattern.

Update `implementer.md` to `READY_FOR_REVIEW` with:

```text
new exact HEAD SHA
resolved COM60-H001 evidence
resolved COM60-H002 evidence
new test counts
PostgreSQL rollback-cycle evidence
validation run/job IDs
validated-to-final delta proof if applicable
BLOCKERS_REPORTED_BY_IMPLEMENTER
```

---

# 8. REVIEWER DECISION

```text
FAZ 6.0: NOT READY TO LOCK
REVIEWED_HEAD_SHA: 6790cc2eccb858f80857103e99f9b5562e8db485
PR: #23

COM60-H001: OPEN
COM60-H002: OPEN

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
START_6_1: NO
```

Implementer must resolve both blockers in one consolidated hardening pass and STOP at `READY_FOR_REVIEW`.

Reviewer STOP.
