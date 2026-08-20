# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6-FINAL
CHECKPOINT_TITLE: Integrated Commerce Audit + Freeze Candidate

REVIEWER_STATE: IMPLEMENTATION_AUTHORIZED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 287367ce8eb708efce0ebae0a2f9c90d681cce01
LIVE_MAIN_SHA_AT_OPEN: 287367ce8eb708efce0ebae0a2f9c90d681cce01
EXPECTED_CODE_BRANCH: faz6/6-final-integrated-commerce-audit-freeze
EXPECTED_COMMERCE_VERSION: 0.6.0
EXPECTED_MIGRATION_HEAD: 0005_recovery_reconciliation
EXPECTED_N8N_RUNTIME_VERSION: 2.33.4
EXPECTED_N8N_IMAGE_DIGEST: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
LOCKED_ORDER_WORKFLOW_SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
RECOVERY_SCHEDULE_WORKFLOW_SHA256: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
CURRENT_COMMERCE_BASELINE_TESTS: 403 PASS
CURRENT_N8N_STATIC_BASELINE: 12 PASS
FROZEN_FA3_5_BASELINE: 1504 PASS

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
FAZ_6_5_STATUS: LOCKED
FAZ_6_FINAL_STATUS: IMPLEMENTATION_AUTHORIZED
START_POST_FAZ6: NO
```

---

# 1. PURPOSE OF 6-FINAL

FAZ 6-FINAL is an integrated **audit + freeze-candidate checkpoint**.

It is NOT a new product subsystem and is NOT authorization to add new commerce behavior.

The implementation checkpoints 6.0 through 6.5 are already individually locked. 6-FINAL must prove that their composition preserves one coherent authority chain across:

```text
purchase intent
-> durable order + immutable catalog/Checkout operation
-> Stripe Checkout
-> verified Stripe webhook and/or server reconciliation
-> durable paid order
-> exactly-one order.paid.v1 durable outbox identity
-> n8n orchestration consumer
-> frozen SiteScore /v1 analysis + report contracts
-> canonical fulfillment or full-refund path
-> secure PDF delivery grant
-> Postmark transactional send evidence
-> fulfilled OR paid+delivery_failed/attention OR refunded
-> bounded recovery/reconciliation
```

The final audit must preserve the product truth disclaimer:

> Mathematically validated scoring engine; empirical validation pending.

FAZ 6-FINAL must not present engineering/integration validation as empirical business-outcome validation.

---

# 2. AUTHORITATIVE LOCK PROVENANCE TO RE-PROVE

Implementer must independently re-read live GitHub and record the exact merged chain. Do not rely only on this handoff text.

Expected chain:

```text
FAZ 6 start main:
0e370940ee5c8c1253db72fa7e33078fb4ef3b2c

6.0 PR #23
approved head: 8a4e358709ae7a662bf079722db042fb6e319ffd
merge: af3b9567d644f6bcf0410af704dd7d86de41b5ce

6.1 PR #24
approved head: 719a17c4359524337f57298252a59ccb89dcd0aa
merge: 8027239b4b168e98e8ee16e15787366632017156

6.2 PR #25
approved head: 3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628
merge: acc213ac52f980789164d9fedcd4e18deeefcf75

6.3 PR #26
approved head: 64887a560c4af492312e726f990363fc5010345d
merge: 7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba

6.4 PR #27
approved head: 1f22c4a09c08c2803c746b87a20209d7fdf6c574
merge: bdf43a891ca14941ba2f2c4f115e4a15bec0015a

6.5 PR #28
approved head: 4ed902dd9ebf230dcb983392705ab0d95bb0c846
merge: 287367ce8eb708efce0ebae0a2f9c90d681cce01
```

Required provenance gate:

- each PR is merged/closed;
- each PR base is the immediately preceding locked `main`;
- each merge commit parent-2 is the exact approved head;
- the final live `main` is exact `287367ce8eb708efce0ebae0a2f9c90d681cce01` before 6-FINAL branch creation;
- no alternate/squash/rebase substitution or unexplained drift;
- no frozen FAZ 3/4/5 source mutation anywhere in the FAZ 6 chain.

Any mismatch is a blocker. Do not repair history.

---

# 3. STRICT 6-FINAL CHANGE SCOPE

Expected final branch:

```text
faz6/6-final-integrated-commerce-audit-freeze
```

Create it only from exact:

```text
main@287367ce8eb708efce0ebae0a2f9c90d681cce01
```

6-FINAL is audit-only. Allowed durable product-repository changes are narrowly:

```text
sitescore-commerce/docs/FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md
sitescore-commerce/tests/test_faz6_final_freeze_gate.py
```

A separate final audit test file may be split into a small number of clearly named freeze-gate files only if technically necessary. Documentation may reference existing n8n docs/runbook; do not rewrite locked checkpoint documentation merely for style.

Temporary exact-SHA validation workflow files under `.github/workflows/` are allowed during validation and must be removed before final READY_FOR_REVIEW unless an existing repository policy requires them to remain.

NOT authorized in initial 6-FINAL candidate:

```text
production runtime/source changes
new commerce endpoint
new state or state transition
new Stripe/Postmark/SiteScore authority
new migration or schema change
package version bump
new dependency or dependency upgrade
n8n version upgrade
n8n workflow semantic change
locked workflow JSON change
refund/delivery/recovery behavioral change
frozen FAZ 3/4/5 source change
FAZ 7 / later-phase implementation
```

Expected final frozen runtime remains:

```text
sitescore-commerce == 0.6.0
migration head == 0005_recovery_reconciliation
n8n == 2.33.4
order workflow SHA256 == 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery schedule SHA256 == f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

If the integrated audit discovers a product/runtime defect that requires changing an already locked checkpoint, DO NOT silently fix it in 6-FINAL. Set:

```text
ADDITIONAL_REOPEN_REQUIRED: 1
```

identify the exact affected locked checkpoint/invariant, record evidence in `implementer.md`, and STOP for Reviewer authority review.

If the issue changes a frozen contract, additionally set `CONTRACT_CHANGE_REQUIRED: 1`. If architecture must be redesigned, additionally set `DESIGN_DECISION_REVIEW_REQUIRED: 1`.

---

# 4. MANDATORY FINAL AUDIT ARTIFACT

Create:

```text
sitescore-commerce/docs/FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md
```

It must be evidence-oriented, not marketing prose, and contain at minimum the following sections.

## 4.1 Exact base / provenance

Record:

- exact base SHA;
- 6.0–6.5 PR/head/merge chain;
- commerce version;
- migration head and complete migration chain;
- pinned provider/runtime dependencies;
- locked n8n runtime digest;
- exact workflow SHA-256 values;
- frozen FAZ 3/4/5 baseline.

## 4.2 Integrated authority chain

Document the exact server-authoritative chain and identify the owner of each truth:

```text
order/catalog/Checkout operation truth -> commerce/PostgreSQL
payment truth -> verified Stripe evidence + commerce durable transition
analysis/report truth -> frozen SiteScore /v1 service
orchestration -> n8n consumer only
refund truth -> canonical unfulfillable SiteScore proof + fresh Stripe refund evidence
delivery grant truth -> commerce/PostgreSQL digest-bound capability
email provider acceptance -> Postmark response evidence
recovery truth -> fresh provider evidence + existing durable identities + fenced commerce writes
```

No browser redirect, client field, n8n field, email receipt assumption or storage URL may become business authority.

## 4.3 Public/API surface audit

The final audit must enumerate and freeze the current commerce HTTP surface, including:

```text
POST /v1/orders
POST /v1/webhooks/stripe
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
GET  /d/{opaque_token}
```

Prove that automation POST bodies remain empty/server-owned and protected by the automation Bearer boundary; the public download route receives only the opaque capability token and does not accept caller-selected report/storage/provider authority.

The frozen SiteScore service surface consumed by commerce remains the existing FAZ 5 `/v1` contract; commerce must not import or write frozen SiteScore private DB/package state.

## 4.4 Order / Checkout / idempotency audit

Re-prove compositionally:

- server-owned catalog/product/Stripe Price authority;
- exact immutable Checkout operation snapshot before provider I/O;
- stable provider idempotency key across local response/bind loss and config drift;
- caller idempotency key + canonical request hash + PostgreSQL uniqueness;
- browser success/cancel redirect never establishes payment truth;
- no caller-selected amount/currency/Price/provider identity.

## 4.5 Stripe payment authority audit

Re-prove:

- raw-body webhook size bound and official signature verification boundary;
- real Stripe Event identity semantics; no raw-body hash as semantic identity;
- semantic duplicate safety and true identity conflict fail-closed;
- fresh server retrieval of Checkout Session + line items;
- exact API version/livemode/session/client-reference/catalog/Price/quantity/currency binding;
- authoritative paid requires complete + paid + valid bound PaymentIntent;
- no `no_payment_required` authority path;
- webhook-first bind-loss recovery;
- exactly one durable paid transition and exactly one `order.paid.v1` identity;
- server polling remains a distinct reconciliation receipt and never fabricates `evt_*` or webhook inbox evidence.

## 4.6 Fulfillment / frozen SiteScore boundary audit

Re-prove:

- stable analysis operation key/request snapshot/hash;
- commerce calls frozen SiteScore only through authenticated network `/v1` contract;
- commerce does not score, normalize, benchmark, decide, calculate confidence, financials or render report truth;
- analysis/report binding is exact and durable;
- report resolution only after server-observed completed analysis;
- canonical `not_score_ready`, `failed`, `timed_out` and report failure semantics remain distinct;
- report-ready content is revalidated through the frozen authenticated content endpoint.

## 4.7 Full-refund authority audit

Re-prove:

- refund is never triggered by email/delivery failure;
- refund eligibility uses fresh server-side canonical unfulfillable proof;
- refund amount is the full captured amount only;
- stable refund operation/provider idempotency identity;
- list/reconcile-before-create behavior;
- exact reserved `sitescore_*` metadata binding;
- partial/mixed/multiple/conflicting refund histories fail closed;
- external already-full refund is accepted only under the locked unattributed exact-full rules;
- terminal refunded state cannot later fabricate fulfillment.

## 4.8 n8n orchestration audit

Re-prove:

- n8n is orchestration only, never payment/scoring/report/refund/delivery authority;
- exact pinned `2.33.4` image digest;
- locked workflow hashes are byte-identical;
- no Code/Function node business logic authority;
- no Stripe secret, Postmark token, SiteScore private key, DB/Redis/S3 master credential, recipient email, raw delivery token or report bytes in workflow state;
- all continuing advance/refund/wait/delivery paths pass through finite horizon + Wait pacing;
- restart and duplicate trigger converge from commerce durable state;
- horizon exhaustion fails workflow execution only and does not invent commerce truth;
- delivery uses bodyless commerce `/deliver`, not direct Postmark;
- recovery scheduler calls only the protected count/sanitized commerce recovery surface.

## 4.9 Delivery / email audit

Re-prove:

- CSPRNG delivery capability has >=256-bit entropy;
- raw token never persists; only SHA-256 digest persists;
- exact order/report binding;
- exactly seven-day default UTC expiry;
- reusable until expiry, revocable, not one-time burned by scanners;
- public `/d/{opaque_token}` performs fresh paid/not-refunded/current-binding/report-ready/content-integrity checks;
- no private S3 URL/key/credential exposure or redirect;
- server-owned HTTPS public base URL, never Host-header authority;
- safe non-oracular errors and private/no-store/nosniff/no-referrer headers;
- Postmark send occurs outside DB transaction;
- provider acceptance requires the complete locked evidence set;
- `provider_accepted` means provider accepted/submitted, not human receipt;
- ambiguous HTTP-200/incomplete acceptance evidence remains `provider_uncertain`;
- nonzero explicit provider error remains rejection;
- uncertainty can create a fresh grant/attempt without automatically revoking the old still-valid grant;
- fulfillment only after paid + completed analysis + ready report + valid grant + durable accepted Postmark MessageID;
- delivery failure leaves payment paid.

## 4.10 Recovery / reconciliation audit

Re-prove:

- bounded oldest-first scanning;
- durable lease/token/expiry and `FOR UPDATE SKIP LOCKED` claim behavior;
- provider/network I/O occurs outside DB transaction;
- post-I/O writes are exact-lease fenced;
- stale worker cannot overwrite a reclaimed/new worker result;
- legacy pre-0005 real Stripe inbox continuity works after populated 0004 -> 0005 upgrade without invented event authority;
- new-lineage missing/mismatching candidate identity fails closed;
- paid outbox replay validates durable Stripe paid authority before any n8n I/O;
- unpublished send and published replay preserve the exact original outbox event identity;
- historical `published_at` is not rewritten as a new logical event;
- recovery never synthesizes new payment/refund/report/delivery authority;
- impossible/corrupt shapes become sanitized durable findings/attention.

## 4.11 Security / privacy / secret boundary audit

Audit source, configs, workflow JSON, docs and tests for:

```text
Stripe secret leakage
Stripe webhook secret leakage
Postmark token leakage
SiteScore service credential leakage
DB/Redis/S3 master credential leakage
raw delivery token persistence/logging
recipient/customer email leakage into n8n
provider raw response body persistence where forbidden
private storage URL exposure
Host-header derived delivery URL authority
caller-controlled amount/Price/currency/provider state
unsanitized public/provider errors
```

Document intentional sensitive fields that must exist in commerce durable storage, such as customer email, and prove they do not cross into unauthorized n8n/public error surfaces.

## 4.12 State / money invariant matrix

The audit artifact must contain an explicit table or equivalent executable mapping for at least these classes:

```text
pending payment
expired/unpaid
paid + analysis pending/running
paid + report pending
paid + delivery pending
paid + provider_uncertain delivery
paid + delivery_failed/attention
fulfilled
refund pending
refunded
corrupt/impossible -> attention
```

For each, record:

- legal payment state;
- legal fulfillment state;
- whether n8n may advance;
- whether refund may occur;
- whether delivery may occur;
- terminal/retryable meaning;
- authoritative evidence required for next transition.

At minimum prove these global invariants:

```text
fulfilled => payment remains paid and canonical report delivery conditions were proven
refunded => full Stripe refund authority was proven and fulfillment cannot become completed afterward
delivery failure alone => NO refund
browser redirect => NO paid authority
n8n decision => NO money/scoring/report authority
recovery replay => same durable logical identity, not new payment/order/report authority
```

## 4.13 Failure/crash/replay matrix

Document and test the existing behavior for representative crash windows:

```text
Stripe Checkout success / local bind loss
verified webhook inbox durable / process crash
Stripe paid transition / outbox publication gap
n8n trigger response loss
analysis POST response loss
report resolver response loss/local bind loss
refund create response loss
Postmark request response loss/ambiguous response
n8n restart during advance Wait
n8n restart during delivery Wait
recovery worker lease expiry/reclaim during provider I/O
published paid-outbox replay after n8n horizon/crash
```

No matrix row may claim exactly-once external side effects where the provider boundary only guarantees at-least-once/reconciliation semantics.

## 4.14 Known limitations / non-claims

Final freeze artifact must explicitly preserve current limitations, including where applicable:

- empirical validation is pending until its later authorized phase;
- n8n is not analytical authority;
- provider acceptance is not proof that a human opened/read email;
- provider-uncertain delivery may result in duplicate same-report emails after safe retry;
- no public expired-link regeneration contract in 6.4;
- no broad manual state-override API;
- FAZ 6-FINAL is not a live-production charge/refund/email certification unless such provider-test-mode evidence is actually present and recorded;
- no later-phase frontend/account/product work is implied by FAZ 6 freeze.

Do not silently upgrade these limitations into stronger claims.

---

# 5. EXECUTABLE FINAL FREEZE GATE

Create:

```text
sitescore-commerce/tests/test_faz6_final_freeze_gate.py
```

The gate must inspect current repository/runtime contracts rather than merely assert arbitrary strings in the final audit document.

At minimum it must protect:

1. exact commerce version `0.6.0`;
2. migration revisions `0001` -> `0002` -> `0003` -> `0004` -> `0005` and no unexpected `0006`;
3. exact public/automation/download route set expected for FAZ 6;
4. no commerce private import into frozen `sitescore_api` internals and no frozen package source mutation in final PR;
5. exact n8n workflow files and expected hashes;
6. pinned n8n runtime version/digest declarations;
7. automation workflow absence of forbidden provider/master secrets and direct authority nodes;
8. payment/fulfillment/refund/delivery/recovery critical invariant markers from production code;
9. final audit artifact contains exact base/provenance, authority boundaries, known limitations and all three escalation flags;
10. empirical-validation disclaimer remains present.

Prefer AST/structured JSON/config inspection over brittle prose matching when practical.

The final freeze gate may add evidence but must not become a second implementation of business logic.

---

# 6. EXACT-SHA FINAL VALIDATION

Before READY_FOR_REVIEW, Implementer must run fresh exact-SHA validation on the final audit candidate.

## 6.1 Commerce + n8n integrated gate

Required:

```text
Python 3.11.x exact recorded
PostgreSQL 16.x exact recorded
sitescore-commerce full test suite
new 6-FINAL freeze gate
n8n static suite
exact n8n 2.33.4 runtime smoke
pip check
```

Current minimum starting baselines before adding final gate tests are:

```text
commerce: 403 PASS
n8n static: 12 PASS
```

Final commerce count must therefore be >=403 and the exact new total must be reported. A lower count is a blocker unless the Reviewer explicitly authorized a test removal, which is not currently authorized.

## 6.2 Migration validation

Fresh real PostgreSQL must prove:

```text
fresh DB upgrade through 0001 -> 0005
downgrade/re-upgrade cycle
populated 0004 -> 0005 legacy inbox continuity test
current schema constraints/triggers/indexes
```

No migration `0006` is expected.

## 6.3 Provider/crash authority tests

Run the full existing commerce adversarial suite, including the locked Stripe, refund, Postmark uncertainty, lease fencing, replay and corruption cases. Do not replace real PostgreSQL state-changing tests with mocks.

External provider network calls may remain controlled fake/test endpoints where existing tests intentionally validate wire behavior. The audit must not call that a live-production provider certification.

## 6.4 n8n runtime validation

Use the exact pinned n8n image digest and re-run all existing 6.3/6.4/6.5 runtime smoke coverage, including pacing, finite horizon, duplicate/retry convergence, delivery Wait restart and recovery scheduler/replay behavior.

Final validation must recompute and assert both workflow hashes.

## 6.5 Frozen regression gate

Run the exact frozen FAZ 3/4/5 baseline:

```text
sitescore-report: 24
sitescore-api: 105
sitescore-app: 19
sitescore-pipeline: 53
sitescore-benchmarks: 191
sitescore-metrics: 67
sitescore-spatial: 180
sitescore-providers: 418
sitescore-data: 361
sitescore-core: 86
TOTAL: 1504 PASS
```

Also re-run:

```text
frozen scope scan
secret boundary scan
private S3-compatible artifact regression
Redis/Celery transport regression
```

Frozen 1504 must remain exact unless an independently authorized frozen reopen exists. None exists now.

## 6.6 Validation cleanup rule

Record:

- exact validated SHA;
- workflow run/job IDs;
- conclusions;
- exact test totals;
- runtime versions/digests/hashes.

If temporary validation workflow files are removed after the successful validated SHA, final head may differ only by those non-product removals. Report the exact validated -> final commit count and file delta.

Any production/doc/test/workflow semantic change after validation requires a fresh exact-SHA validation.

---

# 7. FINAL PR / HANDOFF RULES

Implementer must:

1. create the exact expected branch from exact base;
2. create a PR to `main`;
3. keep initial durable changes audit-doc + final freeze-gate only;
4. run final integrated validation;
5. remove temporary validation workflows if used;
6. re-check final head vs validated SHA;
7. update `implementer.md` with exact evidence;
8. STOP for Reviewer.

Expected successful handoff state:

```text
CURRENT_CHECKPOINT: 6-FINAL
IMPLEMENTER_STATE: READY_FOR_REVIEW
USER_LOCK_AUTHORIZED: NO
BLOCKERS: NONE
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
START_POST_FAZ6: NO
```

Reviewer will independently inspect the exact final head, full FAZ 6 provenance, audit artifact, executable freeze gate, source boundaries, migration chain, n8n artifacts, security/money invariants and exact-SHA CI.

Only Reviewer may issue `READY_TO_LOCK` after that independent audit.

Only a literal user `LOCK` sent to Implementer after Reviewer `READY_TO_LOCK` may authorize final merge/freeze.

---

# 8. FREEZE DECISION SEMANTICS

6-FINAL successful merge does not occur merely because tests pass. Final freeze requires all of:

```text
all FAZ 6.0-6.5 provenance exact
no hidden production change in 6-FINAL
integrated audit complete
final freeze gate meaningful and passing
commerce full tests passing
n8n static/runtime passing
frozen 1504 passing
migration continuity passing
money/payment/refund/delivery/recovery authority coherent
security/secret boundaries clean
no unresolved blocker
all three escalation flags = 0
Reviewer READY_TO_LOCK
literal user LOCK
exact approved head merged with exact parentage
post-LOCK live main verification
```

Until that post-LOCK verification occurs:

```text
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_FINAL_STATUS: NOT_LOCKED
START_POST_FAZ6: NO
```

Reviewer STOP after opening this checkpoint.