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

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: acc213ac52f980789164d9fedcd4e18deeefcf75
LIVE_MAIN_SHA_AT_CONTRACT: acc213ac52f980789164d9fedcd4e18deeefcf75
CODE_BRANCH: faz6/6-3-production-n8n-orchestration
PR: NOT_YET_OPEN
REVIEWED_HEAD_SHA: NONE

N8N_RUNTIME_VERSION: 2.33.4
N8N_CONTAINER_TAG: n8nio/n8n:2.33.4

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
FAZ_6_3_STATUS: IMPLEMENTATION_REQUESTED
START_6_4: NO
```

---

# 1. FAZ 6.2 POST-LOCK CLOSURE — VERIFIED

Reviewer independently verified the user-authorized FAZ 6.2 LOCK against live GitHub.

```text
PR: #25
PR_STATE: CLOSED
PR_MERGED: TRUE

pre-lock main/base:
8027239b4b168e98e8ee16e15787366632017156

Reviewer-approved exact PR head:
3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628

merge commit / new main:
acc213ac52f980789164d9fedcd4e18deeefcf75

merge parent 1:
8027239b4b168e98e8ee16e15787366632017156

merge parent 2:
3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628
```

The merge commit is exactly the expected two-parent merge of the pre-lock main and the exact Reviewer-approved head. No unexpected main drift occurred between approval and merge.

FAZ 6.2 is therefore closed as:

```text
FAZ_6_2_STATUS: LOCKED
COM62-H001: RESOLVED
```

The frozen regression entering 6.3 remains:

```text
sitescore-commerce: 255 PASS
frozen FAZ 3/4/5: 1504 PASS
combined: 1759 PASS
```

---

# 2. FAZ 6.3 MISSION

Implement only the production n8n orchestration workflow and the minimum commerce-side dispatch boundary required to deliver the already-durable `order.paid.v1` outbox event into that workflow.

Canonical chain for this checkpoint:

```text
commerce durable paid transition
-> commerce.outbox_events / order.paid.v1
-> narrow outbox dispatcher
-> protected n8n production webhook
-> fetch authoritative commerce automation state
-> POST commerce advance when server guidance requires it
-> Wait / poll commerce state
-> converge on:
     delivery_pending    -> STOP cleanly; FAZ 6.4 owns delivery
     refunded            -> STOP
     attention_required  -> STOP
     expired             -> STOP
```

n8n is an orchestrator only. It never becomes payment, analysis, report, refund, delivery, or scoring authority.

---

# 3. STRICT SCOPE BOUNDARY

Allowed in 6.3:

```text
automation/n8n/workflows/
automation/n8n/docs/
automation/n8n/tests/
reproducible pinned n8n runtime configuration
minimum sitescore-commerce outbox->n8n dispatch code/config/tests if required
minimum commerce configuration for the n8n webhook destination/auth
checkpoint documentation and CI validation
```

Forbidden in 6.3:

```text
FAZ 3/4/5 frozen source changes
scoring/readiness/decision/financial/report truth changes
new SiteScore analysis/report semantics
Stripe payment authority redesign
new refund eligibility rules
Postmark integration
customer delivery grant/token
public /d/{token} download route
marking an order fulfilled
email acceptance/delivery state
broad FAZ 6.5 reconciliation scanner/scheduler
production cloud/Kubernetes/autoscaling/observability program
FAZ 7 work
```

If a genuine requirement forces frozen FAZ 3/4/5 semantics to change:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

If the selected architecture cannot be implemented correctly without redesign:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

Stop rather than silently expanding scope.

---

# 4. EXACT n8n RUNTIME PIN

Use exactly:

```text
n8n version: 2.33.4
container: n8nio/n8n:2.33.4
```

Do not use floating tags:

```text
latest
stable
next
beta
```

Validation must prove the running container reports exactly `2.33.4`.

Capture the resolved container image digest in CI/handoff evidence. If the implementation stores a digest pin in runtime configuration, it must correspond to the validated 2.33.4 image; do not invent a digest in code/docs without resolving it from the actual image.

External task runners are not required by this checkpoint because business logic must not be implemented in Code nodes. Do not add `n8nio/runners` or another execution subsystem unless unavoidable and explicitly justified in the handoff; if added, pin it exactly and treat it as review scope.

---

# 5. REPOSITORY AUTHORITY FOR WORKFLOW

Durable workflow authority is the sanitized GitHub export, not n8n's internal database/history.

Repository layout must be equivalent to:

```text
automation/n8n/
  workflows/
    <production order.paid.v1 workflow>.json
    <optional error workflow>.json
  docs/
    CHECKPOINT_6_3_PRODUCTION_N8N_ORCHESTRATION.md
  tests/
    <static/integration validation>
```

A reproducible runtime definition may live under the same subtree, for example a Docker Compose/runtime manifest used for validation.

Required workflow identity:

```text
stable human-readable workflow name
explicit repository workflow version identity
sanitized exported JSON committed to GitHub
SHA-256 of final exported workflow JSON recorded in implementer.md
```

Do not rely on an n8n database-generated workflow ID as the SiteScore business identity.

The exported JSON must contain no credential values, tokens, passwords, authorization headers with literal secrets, webhook secrets, DB URLs/passwords, Stripe secrets, SiteScore service keys, Postmark tokens, S3 credentials, or private report bytes.

Credential references/credential names are acceptable; credential values are not.

---

# 6. n8n PRIVILEGE / SECRET MINIMIZATION

n8n must NOT receive or directly use:

```text
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
SiteScore analysis/report service key
Postmark server token
commerce PostgreSQL credentials
frozen SiteScore DB credentials
Redis/Celery credentials for business execution
S3/object-store credentials
```

Outbound n8n business calls use only the existing narrowly scoped commerce automation credential:

```text
COMMERCE_AUTOMATION_API_KEY
```

Inbound commerce -> n8n trigger must also be protected. Use an n8n-native webhook authentication mechanism or equivalent narrow transport-only ingress credential. If a separate ingress secret is used, it must:

```text
be transport-only
be stored as an n8n credential/environment secret, never in exported JSON
be known only to the commerce dispatcher and n8n ingress
not grant Stripe/SiteScore/Postmark/DB authority
not substitute for commerce business-state verification
```

The ingress credential and the outbound commerce automation credential are distinct security roles even if implementation chooses one secure secret-management mechanism for both. Do not weaken the webhook to an unauthenticated public trigger merely to keep a one-secret design.

---

# 7. `order.paid.v1` TRIGGER CONTRACT

The durable source is the already-existing commerce outbox row.

The dispatcher sends only the minimal server-owned trigger payload equivalent to:

```json
{
  "event_id": "<commerce outbox UUID>",
  "event_type": "order.paid.v1",
  "order_id": "<order UUID>",
  "occurred_at": "<server timestamp>"
}
```

The exact field source must be server-owned durable data. Do not use caller/browser/n8n values to construct payment truth.

Do NOT include:

```text
Stripe raw event/payment payload
Checkout URL
PaymentIntent details
customer analysis request
SiteScore service credentials
commerce automation credential
Postmark token
report content/PDF
private object-store identity
```

n8n may validate transport shape and `event_type == order.paid.v1`, but the trigger payload is not payment authority. The first business action must query the commerce automation API for current durable server state.

Duplicate event delivery is expected and valid.

---

# 8. MINIMUM COMMERCE OUTBOX DISPATCHER

6.1 created `commerce.outbox_events`; 6.3 may add only the narrow delivery mechanism required to send unpublished `order.paid.v1` rows to the protected n8n webhook.

Required semantics:

```text
load durable unpublished outbox event
-> construct minimal payload from durable event/order identity
-> perform HTTP request OUTSIDE PostgreSQL transaction/row lock
-> only after a confirmed accepted 2xx response mark published_at (or equivalent durable dispatch success)
```

For timeout/network error/5xx/uncertain response:

```text
do not claim published success
retain same durable outbox event identity
retry the same logical event later
never mint a second paid outbox identity for the same order
```

A timeout may mean n8n received the event. Therefore retry can produce duplicate workflow execution; this is intentional at-least-once transport and must converge safely.

Multiple dispatcher processes may race and cause duplicate sends; correctness must not depend on exactly-once HTTP delivery. If a DB claim/lease mechanism is added, it must remain recoverable after process crash and must not permanently strand an event.

No DB transaction may be intentionally held across n8n network I/O.

Do not implement the broad 6.5 stale-event/recovery scanner in this checkpoint. A focused dispatcher entrypoint/service/command sufficient for normal outbox delivery and retry is allowed.

If commerce runtime source changes, bump `sitescore-commerce` coherently to the next checkpoint version (`0.4.0`) and update docs/tests. If the checkpoint is implemented entirely as automation/runtime artifacts without commerce runtime modification, do not bump the Python package merely for aesthetics.

If schema changes are genuinely required, use a new commerce Alembic revision after `0003_fulfillment_refund`; do not modify historical migrations. Schema change is not mandatory if current `published_at` semantics are sufficient.

---

# 9. EXISTING COMMERCE AUTOMATION CONTRACT IS AUTHORITATIVE

6.3 must consume the existing 6.2 routes rather than bypass them:

```text
GET  /v1/automation/orders/{order_id}
POST /v1/automation/orders/{order_id}/advance
```

Both use the narrow commerce automation bearer.

The public workflow projection is already closed to:

```text
api_version = v1
order_id
order_state
payment_state
fulfillment_state
retryable
terminal
next_action = wait | advance | refund | delivery | none
```

n8n must not call the frozen SiteScore API directly. It must not call Stripe directly. It must not read commerce PostgreSQL directly.

It must not submit:

```text
analysis JSON
analysis_id
report_id
paid=true
refund amount
refund reason
Stripe IDs
fulfillment state
```

`POST /advance` body remains empty. `order_id` is only a trigger/lookup identity; commerce re-validates all business truth server-side.

---

# 10. CANONICAL n8n STATE MACHINE FOR 6.3

The workflow should be implemented primarily with native nodes equivalent to:

```text
Webhook
HTTP Request
Switch / IF
Wait
Stop And Error / terminal no-op handling
```

Default requirement:

```text
ZERO Code nodes for business orchestration logic
```

If a Code node is truly unavoidable, Implementer must document why a native node cannot do the job and every line becomes Reviewer audit scope. A Code node may never calculate or decide business truth.

Canonical execution:

```text
1. receive authenticated order.paid.v1 event
2. validate only transport shape/event type
3. GET commerce automation status for order_id
4. branch ONLY on commerce response fields
5. when next_action == advance:
      POST /advance with empty body
      GET status again
6. when next_action == refund:
      POST /advance with empty body
      GET status again
   (commerce independently re-proves refund eligibility and Stripe state)
7. when next_action == wait:
      Wait
      GET status again
8. when next_action == delivery:
      STOP cleanly at delivery_pending
      do NOT fabricate delivery or fulfilled state; FAZ 6.4 owns this
9. when next_action == none or terminal == true:
      STOP without mutating business truth
```

Expected commerce outcomes include:

```text
not_started / paid
-> advance
-> analysis_pending / analysis_running
-> repeated advance/poll under server authority
-> report_pending
-> advance
-> delivery_pending
-> 6.3 STOP, awaiting 6.4
```

Unfulfillable outcomes:

```text
not_score_ready
analysis_failed
analysis_timed_out
report_failed
-> next_action refund
-> POST /advance
-> commerce re-proves canonical terminal resource
-> commerce reconciles/creates the one durable Stripe refund operation
-> n8n observes refunded / refund-pending / attention state
-> stop or wait according to commerce guidance
```

n8n must preserve the distinction between:

```text
analysis truth
report truth
payment truth
refund truth
future delivery truth
```

Workflow execution success is never `fulfilled` authority.

---

# 11. WAIT / RETRY / RESTART SEMANTICS

The workflow is at-least-once and restart-safe.

Required behavior:

```text
HTTP timeout / 429 / 5xx
-> retry the same commerce operation/order identity
-> no new analysis/report/refund identity authored by n8n

long-running analysis
-> Wait / poll
-> do not create parallel analysis

n8n restart during Wait
-> persisted workflow execution may resume OR the same order.paid.v1 event may be replayed
-> either path must converge through commerce durable state

same order retrigger
-> GET current commerce state
-> continue/no-op from durable truth
```

Retries must be bounded per execution. Reaching an n8n retry/execution horizon may fail the workflow execution, but it must NOT write or infer a terminal commerce business state. A later replay must be able to continue from durable commerce truth.

Use a documented finite polling interval suitable for integration tests and production configuration. Do not busy-loop.

Do not use n8n workflow static data/execution history as dedupe or business authority. It may be operational evidence only.

---

# 12. ERROR WORKFLOW / FAILURE HANDLING

Provide either a separate sanitized error workflow or an explicit safe workflow failure path.

It may capture only safe operational evidence such as:

```text
workflow version
commerce event_id
order_id
safe HTTP status / sanitized commerce error code
execution timestamp
```

It must not persist/log:

```text
Authorization header
webhook ingress secret
commerce automation secret
full customer purchase intent
Stripe payload/card/payment details
SiteScore service key
raw provider error bodies containing secrets
report bytes
```

Error handling must never mark an order paid/refunded/fulfilled or synthesize analytical/report truth.

---

# 13. REQUIRED ADVERSARIAL / INTEGRATION COVERAGE

Implementation must prove at least:

```text
1. exact n8n runtime reports 2.33.4
2. workflow export imports into a clean/persistent 2.33.4 runtime
3. exported JSON contains no secret values
4. zero business Code nodes (preferably zero Code nodes total)
5. only intended commerce HTTP destination/credential boundary is used
6. unauthenticated/invalid-auth order.paid.v1 webhook is rejected
7. malformed trigger payload is rejected/stopped safely
8. wrong event_type is rejected/stopped safely
9. valid paid event first queries commerce authority before advancing
10. duplicate identical event delivery converges without duplicate business effects
11. different event deliveries for same order converge safely
12. same order workflow re-trigger converges from current commerce state
13. analysis_pending / analysis_running waits and polls; no parallel analysis
14. completed analysis advances to report path
15. report ready reaches delivery_pending and STOPs without delivery/fulfilled fabrication
16. not_score_ready reaches server refund path
17. analysis failed reaches server refund path
18. analysis timed_out reaches server refund path
19. report failed reaches server refund path while preserving analysis success semantics
20. refund pending/retry path follows commerce guidance and does not choose amount/reason
21. commerce HTTP 5xx then recovery retries safely
22. commerce HTTP timeout/uncertain response then replay converges safely
23. n8n restart while waiting/re-import/replay does not require fake local business state
24. outbox dispatcher 2xx marks the same durable event published
25. outbox dispatcher timeout/5xx leaves event retryable/unpublished
26. dispatcher response-loss + replay may trigger duplicate n8n execution but one commerce logical fulfillment chain remains
27. dispatcher payload is minimal and contains no customer analysis request/payment payload/secrets
28. no DB transaction is held across n8n HTTP I/O
29. frozen FAZ 3/4/5 source remains untouched
30. no FAZ 6.4 delivery/Postmark/token code
31. no broad FAZ 6.5 recovery scanner
```

Use deterministic local/fake commerce/provider fixtures where appropriate. Do not require live Stripe, live Postmark, or paid external services for normal CI.

For n8n runtime integration, use a persistent local test volume so a container restart can demonstrate workflow/execution durability behavior without introducing business DB credentials into n8n.

---

# 14. CI / REGRESSION GATE

Require exact-head CI for the 6.3 candidate.

At minimum validate:

```text
n8n 2.33.4 container/runtime identity
resolved container digest captured
workflow JSON parse/import
workflow/static security tests
webhook auth tests
workflow orchestration integration cases
outbox dispatcher tests if commerce changes
secret scan including automation/n8n exports
frozen-scope scan
```

Preserve current baselines:

```text
sitescore-commerce: >=255 PASS, with all previous tests preserved
frozen FAZ 3/4/5: 1504 PASS
```

Any newly added commerce/n8n tests are additive.

If commerce persistence/schema changes, validate with real PostgreSQL 16 and the full Alembic upgrade/downgrade/re-upgrade chain. If no schema change, still run the existing commerce PostgreSQL suite.

Preserve private S3 and Redis/Celery frozen regressions because 6.3 must not accidentally alter upstream runtime behavior.

A temporary GitHub validation workflow may be used and removed after a validated SHA, but if removed the Implementer must prove validated-SHA -> final-head delta is only the workflow removal and contains no product/test/doc semantic changes.

---

# 15. DOCUMENTATION REQUIREMENTS

Create durable 6.3 documentation covering actual implementation:

```text
exact n8n version + container tag + validated digest
workflow name/version/path/SHA-256
runtime/import procedure used in validation
protected ingress webhook path/auth mechanism (secret names only)
outbound commerce API base configuration name
COMMERCE_AUTOMATION_API_KEY reference only, never value
minimal order.paid.v1 payload
outbox dispatch semantics
node inventory
state machine using wait|advance|refund|delivery|none
poll/retry/restart behavior
error workflow behavior
credential inventory by NAME/ROLE only
proof n8n has no Stripe/SiteScore/Postmark/DB/S3 master credentials
6.4 boundary: delivery_pending is a clean stop
known limitations
CI/test baseline
```

Do not describe n8n provider/execution success as commerce fulfillment success.

---

# 16. IMPLEMENTER HANDOFF REQUIREMENTS

At completion, `implementer.md` must record:

```text
CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.3
IMPLEMENTER_STATE: READY_FOR_REVIEW

EXPECTED_BASE_SHA: acc213ac52f980789164d9fedcd4e18deeefcf75
CODE_BRANCH: faz6/6-3-production-n8n-orchestration
PR: #<N>
HEAD_SHA: <exact final head>

N8N_RUNTIME_VERSION: 2.33.4
N8N_CONTAINER_TAG: n8nio/n8n:2.33.4
N8N_VALIDATED_IMAGE_DIGEST: <actual resolved digest>
WORKFLOW_PATH: <exact>
WORKFLOW_VERSION: <exact>
WORKFLOW_SHA256: <exact>
```

Then include:

```text
all changed files
whether sitescore-commerce runtime changed
package version if changed
migration revision if any
outbox dispatcher design/evidence
webhook ingress auth mechanism / secret ENV or credential NAME only
commerce automation credential NAME only
workflow node inventory
proof Code-node business logic absent
workflow import/runtime evidence
duplicate/restart/wait/error-path evidence
commerce tests
frozen 1504 regression
PostgreSQL evidence
secret scan
frozen scope scan
validated SHA / CI run / job
validated->final delta if workflow cleanup occurs
CONTRACT_CHANGE_REQUIRED
DESIGN_DECISION_REVIEW_REQUIRED
ADDITIONAL_REOPEN_REQUIRED
BLOCKERS_REPORTED_BY_IMPLEMENTER
START_6_4: NO
```

Then STOP.

`READY_FOR_REVIEW` is not approval and does not authorize merge or FAZ 6.4.

---

# 17. REVIEWER ACCEPTANCE FOCUS FOR NEXT `Devam`

Reviewer will independently inspect the exact PR head for:

```text
pinned n8n runtime
sanitized workflow export
minimal credentials
protected webhook
outbox delivery correctness
at-least-once duplicate safety
restart/Wait behavior
no Code-node business authority
server-owned commerce status/advance usage
not_score_ready/refund preservation
delivery_pending 6.4 stop
workflow JSON repository authority
secrets/artifact hygiene
exact-head CI
frozen source scope
```

Potential blocker prefix:

```text
N8N63-H001
N8N63-H002
...
```

Reviewer will consolidate all concrete blockers in one review pass.

---

# 18. REVIEWER DECISION

```text
FAZ 6.2: LOCKED
MERGED_MAIN_SHA: acc213ac52f980789164d9fedcd4e18deeefcf75

FAZ 6.3: IMPLEMENTATION_REQUESTED
EXPECTED_BASE_SHA: acc213ac52f980789164d9fedcd4e18deeefcf75
CODE_BRANCH: faz6/6-3-production-n8n-orchestration
N8N_RUNTIME_VERSION: 2.33.4

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
BLOCKERS: NONE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
START_6_4: NO
```

Implementer must now act only after the user's normal `Devam` in the Implementer chat, implement only FAZ 6.3, open/update one PR, write `implementer.md` as `READY_FOR_REVIEW`, and STOP.

No LOCK is authorized for 6.3 at this stage. Reviewer STOP.
