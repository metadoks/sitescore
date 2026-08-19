# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.3
CHECKPOINT_TITLE: Production n8n Orchestration Workflow

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: acc213ac52f980789164d9fedcd4e18deeefcf75
LIVE_MAIN_SHA_AT_REVIEW: acc213ac52f980789164d9fedcd4e18deeefcf75
CODE_BRANCH: faz6/6-3-production-n8n-orchestration
PR: #26
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE: TRUE
PR_MERGED: FALSE
REVIEWED_HEAD_SHA: e8649fd0d15f297643bdc128df7ea7fdcc55e74b

VALIDATED_SHA: e687767ebfd4825c448c279a5ff5c82c1e463e68
VALIDATION_RUN_ID: 32279951225
VALIDATION_JOB_ID: 96156101292
VALIDATION_CONCLUSION: SUCCESS
VALIDATED_TO_FINAL_COMMITS: 1
VALIDATED_TO_FINAL_DELTA: ONLY .github/workflows/faz6-6-3-validation.yml REMOVAL

N8N_RUNTIME_VERSION: 2.33.4
N8N_CONTAINER_TAG: n8nio/n8n:2.33.4
N8N_VALIDATED_IMAGE_DIGEST: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
WORKFLOW_PATH: automation/n8n/workflows/sitescore-order-paid-v1.json
WORKFLOW_SHA256: 5b4abd8cbc774633c26a93708992bc68ca396fabd8f1d573c648f73c113d448e

N8N63-H001: OPEN
BLOCKERS: N8N63-H001
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
FAZ_6_3_STATUS: HARDENING_REQUIRED
START_6_4: NO
```

---

# 1. EXACT STATE REVIEWED

Reviewer independently re-read live GitHub and reviewed the exact final PR head.

```text
main:
acc213ac52f980789164d9fedcd4e18deeefcf75

PR #26:
OPEN
DRAFT: FALSE
MERGEABLE: TRUE
MERGED: FALSE

base:
main@acc213ac52f980789164d9fedcd4e18deeefcf75

reviewed head:
e8649fd0d15f297643bdc128df7ea7fdcc55e74b

validated SHA:
e687767ebfd4825c448c279a5ff5c82c1e463e68

validated -> final:
1 commit ahead
0 behind
only changed file:
.github/workflows/faz6-6-3-validation.yml
status: removed
```

Base -> reviewed head changes are confined to `automation/n8n/` and the minimum `sitescore-commerce` dispatcher/package/tests surface. Frozen FAZ 3/4/5 runtime source is untouched. No FAZ 6.4 delivery/Postmark/grant/fulfilled implementation and no FAZ 6.5 broad recovery scanner were introduced.

---

# 2. POSITIVE REVIEW RESULTS

Reviewer confirmed the following major 6.3 boundaries on the exact reviewed head:

```text
sitescore-commerce == 0.4.0
commerce migration head remains 0003_fulfillment_refund
no schema migration added
n8n runtime pinned to 2.33.4
validated container digest captured
workflow repository export has zero Code/Function nodes
workflow contains no literal production secrets
inbound commerce -> n8n transport uses COMMERCE_N8N_INGRESS_SECRET
outbound n8n -> commerce uses distinct COMMERCE_AUTOMATION_API_KEY role
n8n has no Stripe/SiteScore/Postmark/commerce-DB/Redis/S3 master credentials
order.paid.v1 trigger payload is minimal server-owned identity only
valid workflow first queries commerce automation authority before mutation
only commerce automation GET and empty POST /advance are business HTTP calls
report-ready / delivery_pending stops cleanly; no fulfilled fabrication
outbox dispatcher performs n8n HTTP outside PostgreSQL transaction/row lock
confirmed 2xx marks the same durable event published
transport uncertainty/non-2xx leaves the event unpublished for replay
multiple dispatchers may duplicate transport but retain one durable event identity
```

These are accepted positive results but do not override the blocker below.

---

# 3. N8N63-H001 — OPEN

## Long-running real commerce `advance` states bypass Wait/poll horizon and can busy-loop

The frozen/live FAZ 6.2 commerce automation projection is authoritative.

`FulfillmentStore.get_status()` maps business state as follows:

```text
delivery_pending -> next_action=delivery
canonical refund states -> next_action=refund
terminal / attention_required -> next_action=none
otherwise, if payment_state=paid -> next_action=advance
otherwise -> next_action=wait
```

Therefore these real paid fulfillment states return `next_action=advance`:

```text
not_started
analysis_pending
analysis_running
report_pending
```

`POST /v1/automation/orders/{order_id}/advance` then performs the relevant one-step server-owned operation. In particular, for `analysis_pending` / `analysis_running`, it re-polls the exact bound SiteScore analysis and can legitimately return another paid `analysis_pending` / `analysis_running` state whose next action is again `advance`.

The current n8n graph does not pace that path.

Current exact workflow loop:

```text
Get Commerce State
-> Advance Requested?
-> Advance Commerce
-> Get Commerce State
```

`Advance Commerce` connects directly back to `Get Commerce State`.

The only branch that enters:

```text
Within Poll Horizon?
-> Wait Before Poll
-> Get Commerce State
```

is `next_action == wait`.

This means a legitimate long-running production analysis can execute:

```text
GET commerce status       -> advance
POST /advance             -> analysis still running
GET commerce status       -> advance
POST /advance             -> analysis still running
GET commerce status       -> advance
...
```

without entering `SITESCORE_N8N_POLL_SECONDS` Wait and without applying the `SITESCORE_N8N_MAX_POLLS` execution horizon.

Consequences:

```text
unpaced commerce HTTP loop
repeated immediate SiteScore analysis reconciliation
potentially unbounded workflow execution while analysis remains running
load amplification against commerce/SiteScore
explicit 6.3 bounded polling contract bypass
```

This is not a cosmetic orchestration preference. It violates the checkpoint's required long-running analysis / bounded retry semantics and creates a concrete availability/recovery correctness path.

```text
N8N63-H001: OPEN
```

---

# 4. WHY CURRENT GREEN RUNTIME TEST MISSES THE BUG

The n8n fake commerce fixture uses an artificial `WAIT` order whose `analysis_running` projection returns:

```text
next_action = wait
```

for its first reads.

That does not match the real commerce projection, where a paid `analysis_running` order returns:

```text
next_action = advance
```

The current restart/Wait smoke therefore proves persistence for the artificial wait branch, but it does not prove the actual production long-running analysis path.

The static test also currently asserts:

```text
Advance Commerce -> Get Commerce State
```

so it codifies rather than detects the unpaced loop.

Green CI is therefore valid for the tested graph, but the tested fixture does not represent the production state projection at this critical point.

---

# 5. REQUIRED HARDENING

Implementer must harden PR #26 without widening checkpoint scope.

Required semantic behavior:

```text
any continuing orchestration cycle after POST /advance
-> pass through the same finite poll-horizon control
-> Wait for configured SITESCORE_N8N_POLL_SECONDS
-> then GET authoritative commerce state again
```

A native-node shape equivalent to the following is acceptable:

```text
Advance Commerce
-> Within Poll Horizon?
   -> if within horizon: Wait Before Poll -> Get Commerce State
   -> if exceeded: Fail Poll Horizon
```

The exact graph may differ, but mandatory invariants are:

```text
no direct unbounded Advance Commerce -> Get Commerce State cycle
analysis_pending / analysis_running are paced
report_pending continuing cycles are paced
refund/reconciliation continuing cycles are paced where they remain nonterminal
finite configured horizon applies to every continuing execution cycle
no Code/Function node business logic
no n8n-authored analysis/report/refund/payment/delivery truth
horizon failure changes only workflow execution outcome, never commerce business state
later replay can continue from commerce durable truth
```

Do not change the frozen 6.2 commerce truth contract merely to make the workflow test easier. The orchestration must adapt to the existing authoritative projection.

---

# 6. REQUIRED ADVERSARIAL / RUNTIME PROOF FOR HARDENING

Add or correct runtime fixtures so they mirror actual commerce projection.

At minimum prove:

```text
1. paid analysis_pending returns next_action=advance for multiple cycles
   -> each continuing advance cycle is separated by configured Wait
   -> no parallel/new analysis identity is authored

2. paid analysis_running returns next_action=advance for multiple cycles
   -> bounded paced polling
   -> eventual transition can continue to report/delivery boundary

3. a permanently nonterminal paid advance state
   -> reaches SITESCORE_N8N_MAX_POLLS horizon
   -> workflow fails/stops operationally
   -> no fabricated terminal commerce state

4. restart during a paced real advance cycle
   -> resumes or replay converges from commerce durable state

5. duplicate same-event and different-event same-order deliveries
   -> still converge after pacing change

6. actual commerce HTTP 5xx then recovery
   -> native retry/replay behavior demonstrated
   -> no duplicate business authority

7. actual commerce HTTP timeout/uncertain response then recovery/replay
   -> convergence demonstrated
   -> no n8n-authored replacement identity
```

Items 6 and 7 were explicitly required by the 6.3 Reviewer contract but the current fake/runtime smoke does not inject those failures. They must be included in the hardening validation before the checkpoint can become READY_TO_LOCK.

Preserve delivery boundary proof:

```text
delivery_pending -> clean STOP
no Postmark
o delivery grant
no fulfilled mutation
```

---

# 7. VALIDATION EVIDENCE REVIEWED

Reviewer independently inspected the current exact-head validation evidence.

```text
workflow:
faz6-6-3-exact-head-validation

validated SHA:
e687767ebfd4825c448c279a5ff5c82c1e463e68

run:
32279951225

job:
96156101292

conclusion:
SUCCESS

Python:
3.11.15

PostgreSQL:
16.15

sitescore-commerce:
270 PASS

n8n static repository suite:
9 PASS

frozen FAZ 3/4/5:
1504 PASS

combined pytest count reported for package suites:
1783 PASS

n8n runtime:
2.33.4

validated image digest:
n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162

workflow SHA-256:
5b4abd8cbc774633c26a93708992bc68ca396fabd8f1d573c648f73c113d448e

clean instance provisioning/import/publish: PASS
production webhook auth: PASS
runtime orchestration smoke: PASS
Wait restart smoke: PASS
commerce migration cycle: PASS
commerce migration head unchanged at 0003: PASS
secret scan: PASS
frozen-scope scan: PASS
private S3-compatible storage regression: PASS
Redis/Celery transport regression: PASS
```

This run remains useful positive evidence, but it does not close N8N63-H001 because its fake `analysis_running -> wait` projection differs from production commerce and does not exercise the actual `advance` loop. A new exact-head validation run is required after hardening.

---

# 8. REVIEWER DECISION

```text
FAZ 6.3: HARDENING_REQUIRED
PR: #26
REVIEWED_HEAD_SHA: e8649fd0d15f297643bdc128df7ea7fdcc55e74b

N8N63-H001: OPEN
BLOCKERS: N8N63-H001

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
START_6_4: NO
```

Implementer must harden only PR #26 / FAZ 6.3, produce a new exact final head and exact-head CI evidence, update `implementer.md` to `READY_FOR_REVIEW`, and STOP.

No LOCK is authorized. FAZ 6.4 remains closed. Reviewer STOP.
