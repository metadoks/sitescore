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

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba
LIVE_MAIN_SHA_AT_REVIEW: 7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba
CODE_BRANCH: faz6/6-4-delivery-grant-email
PR: NONE
PR_STATE: NONE
REVIEWED_HEAD_SHA: NONE

EXPECTED_COMMERCE_VERSION: 0.5.0
EXPECTED_MIGRATION_HEAD: 0004_delivery_email
N8N_RUNTIME_VERSION: 2.33.4
N8N_CONTAINER_TAG: n8nio/n8n:2.33.4
LOCKED_6_3_WORKFLOW: automation/n8n/workflows/sitescore-order-paid-v1.json

DEL64-H001: NOT_OPENED
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
FAZ_6_4_STATUS: IMPLEMENTATION_REQUESTED
START_6_5: NO
```

---

# 1. OPENING STATE / AUTHORITY

Reviewer independently re-read live GitHub before opening this checkpoint.

```text
live main:
7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba

FAZ 6.3:
LOCKED

PR #26 merge:
7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba

merge parents:
acc213ac52f980789164d9fedcd4e18deeefcf75
64887a560c4af492312e726f990363fc5010345d
```

FAZ 6.4 begins only from that exact main.

Canonical authority remains:

```text
Stripe = payment processor evidence
commerce PostgreSQL = durable order/payment/refund/delivery truth
frozen sitescore-api = analysis/report resource truth
frozen sitescore-report = PDF/report truth
n8n = orchestration only
Postmark = transactional email transport evidence
customer delivery token = access capability only
```

A token, MessageID, email response, n8n execution or customer HTTP request is never analytical/payment/report authority.

---

# 2. CHECKPOINT SCOPE

Implement only the canonical FAZ 6.4 deliverables:

```text
opaque expiring download grant
hashed/digest-only token persistence
public download proxy
frozen report-content verification
Postmark transactional template/API adapter
provider acceptance evidence
delivery retries
fulfilled order condition
```

The existing frozen commerce states already include:

```text
order:
fulfilled / attention_required

payment:
paid

fulfillment:
delivery_pending / completed / delivery_failed
```

Use those meanings; do not collapse order/payment/fulfillment into one state.

Expected additive implementation area:

```text
sitescore-commerce
+ minimum automation/n8n delivery-branch extension
```

Expected package version:

```text
sitescore-commerce==0.5.0
```

Expected additive commerce migration:

```text
0004_delivery_email
```

No frozen FAZ 3/4/5 source mutation is authorized.

---

# 3. LOCKED 6.3 BOUNDARY MUST BE PRESERVED

Current locked workflow deliberately stops here:

```text
next_action=delivery
-> Stop At Delivery Pending
```

FAZ 6.4 may replace/extend only that reserved downstream delivery boundary so the workflow can ask commerce to perform delivery and then observe authoritative commerce state.

This is additive 6.4 work and does NOT reopen FAZ 6.3 provided all locked 6.3 invariants remain intact:

```text
n8n == 2.33.4
protected order.paid.v1 ingress
minimal event_id/event_type/order_id/occurred_at trigger
COMMERCE_N8N_INGRESS_SECRET only for ingress transport
COMMERCE_AUTOMATION_API_KEY only for commerce automation calls
no Stripe secret in n8n
no SiteScore service key in n8n
no Postmark token in n8n
no DB/Redis/S3 credential in n8n
zero Code/Function business-authority nodes
finite Wait/poll horizon
no direct busy loop
duplicate/restart convergence
commerce PostgreSQL remains truth
```

A dedicated server-owned operation equivalent to:

```text
POST /v1/automation/orders/{order_id}/deliver
```

is authorized and preferred.

Requirements:

```text
same dedicated Bearer automation auth
request body must be empty
caller supplies no report_id
caller supplies no recipient
caller supplies no token
caller supplies no provider result
caller supplies no fulfilled flag
response/status must not expose raw token or Postmark secret
```

After a delivery operation, n8n must re-enter the existing finite horizon/Wait/re-read path before any continuing retry cycle. No delivery busy-loop.

---

# 4. DELIVERY GRANT CONTRACT

Implement cryptographically strong opaque capability tokens.

Mandatory V1 properties:

```text
minimum raw entropy: 256 bits
URL-safe opaque representation
raw token exists only transiently in customer/email flow
commerce DB stores digest/hash only
SHA-256 digest is acceptable because raw token is uniformly high-entropy random
unique digest
order-bound
report-bound
default lifetime: exactly 7 days from issuance
reusable for repeated customer downloads until expiry
revocable
not one-time-consumed
```

Do not store any plaintext/raw token column, encrypted-token recovery column, complete delivery URL, or raw token in durable logs/outbox/provider-evidence rows.

The token is a capability, not identity authority. Grant creation must require server-side proof that:

```text
order payment_state == paid
order fulfillment_state == delivery_pending
bound fulfillment analysis == completed
bound report_id exists
bound report state == ready
report belongs to the exact bound analysis/order
```

Arbitrary foreign `report_id` substitution must fail closed.

Grant records should durably preserve equivalent non-secret facts:

```text
grant_id
order_id
report_id
token_digest
issued_at
expires_at
revoked_at nullable
created_at
updated_at
```

Multiple historical grants for the same order/report MAY exist when required by retry/recovery. Every grant remains independently bound and valid only until its own expiry/revocation.

Do not require a single-use token. Email security scanners may follow links before the human customer.

---

# 5. RAW-TOKEN / CRASH / RETRY RULE

Digest-only persistence creates an intentional recovery constraint: after the process loses an in-memory raw token, it cannot reconstruct that token from the database.

Do NOT solve this by weakening the contract with:

```text
plaintext token persistence
encrypted raw-token persistence
reversible token storage
predictable/deterministic low-entropy tokens
```

Use durable delivery-attempt semantics instead.

Required behavior for a send attempt:

```text
1. server verifies exact paid order + exact ready bound report
2. generate strong random grant token
3. persist grant digest + durable delivery-attempt identity before provider call
4. retain raw token only in process memory for construction of the email link
5. commit DB work
6. call Postmark OUTSIDE the DB transaction/row lock
7. validate provider response
8. persist accepted/rejected/uncertain evidence
9. only durable accepted provider evidence may complete fulfillment
```

If Postmark outcome is uncertain because of timeout/connection loss/response loss, do not fabricate `provider_accepted` and do not mark fulfilled.

An uncertain retry may create a fresh delivery attempt and fresh grant because the previous raw token cannot be reconstructed. The previous grant MUST NOT be blindly revoked merely because the provider response was lost: the first email may actually have been accepted, and revoking its link would break a possibly delivered customer message.

Therefore, under an uncertain-send replay, duplicate transactional messages are tolerated as an at-least-once transport consequence, but:

```text
all links remain bound to the same exact order/report
all valid links resolve the same verified PDF
no second analysis/report/payment authority is created
known provider-accepted state short-circuits later duplicate delivery triggers
no exactly-once email claim is made
```

This rule must be tested explicitly.

---

# 6. PUBLIC DOWNLOAD PROXY

Implement a customer-facing capability route equivalent to:

```text
GET /d/{opaque_token}
```

No separate customer account/login system is required in FAZ 6.4; the high-entropy token itself is the access capability.

Request processing must fail closed:

```text
hash incoming token
resolve exact digest
verify not expired
verify not revoked
verify exact order/report binding still coherent
verify order/report is a deliverable state
use server-owned frozen SiteScore credential
freshly GET exact bound /v1/reports/{report_id}
require exact report_id + exact analysis_id + state=ready
retrieve exact /v1/reports/{report_id}/content
re-verify customer-bound content metadata/integrity
return verified PDF bytes
```

The frozen SiteScore report-content endpoint already performs storage integrity verification. Commerce must still verify the upstream response against the exact bound report resource and must not infer or guess any S3 path.

At minimum verify as applicable:

```text
HTTP success
report state ready
exact report/analysis binding
application/pdf MIME
content byte length when reported
Content-SHA256 / report content_sha256 coherence
local SHA-256 of returned bytes
safe filename/content disposition
```

Do not expose or forward:

```text
SITESCORE_API_SERVICE_KEY
S3 URL
S3 bucket
S3 key
object-store credentials
upstream Authorization header
internal debug/provider errors
```

Customer response should preserve safe download semantics such as:

```text
Content-Type: application/pdf
Content-Disposition: attachment with safe server-verified filename
Cache-Control: private, no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
```

Invalid/expired/revoked/foreign tokens must not reveal internal object identity or storage details.

Raw tokens must never be written by application logging. Document that production reverse-proxy/access-log configuration must redact or suppress `/d/{token}` path tokens; deployment-wide log hardening remains a FAZ 7 operational concern, but 6.4 must not itself log them.

---

# 7. SERVER-OWNED DOWNLOAD URL

The customer link host/base is server configuration, never caller/n8n authority.

Add validated server-side configuration equivalent to:

```text
COMMERCE_PUBLIC_BASE_URL
```

Production requirements:

```text
absolute HTTPS
no embedded userinfo/credentials
no query
no fragment
no caller override
```

The final email URL is derived only by commerce from:

```text
server public base + /d/{raw token}
```

This prevents caller-controlled/phishing/exfiltration link construction.

---

# 8. POSTMARK TRANSACTIONAL EMAIL CONTRACT

Postmark exists only behind `sitescore-commerce`.

Use the current official Postmark transactional template API contract:

```text
POST https://api.postmarkapp.com/email/withTemplate
Accept: application/json
Content-Type: application/json
X-Postmark-Server-Token: <secret from environment>
```

Use the already-pinned `httpx==0.28.1` unless a genuine blocker requires a dependency change. Do not add an unnecessary provider SDK merely for this checkpoint.

Server configuration should be equivalent to:

```text
POSTMARK_SERVER_TOKEN          secret
POSTMARK_FROM_EMAIL            server-owned sender
POSTMARK_TEMPLATE_ALIAS        server-owned/versioned template alias
POSTMARK_TIMEOUT_SECONDS       bounded timeout
COMMERCE_PUBLIC_BASE_URL       server-owned customer origin
```

Recommended transactional message stream:

```text
outbound
```

Template model may contain only customer-appropriate material required for delivery, such as:

```text
order/report reference
secure download URL
expiry timestamp / 7-day wording
```

Do NOT send:

```text
raw analytics JSON
Stripe secrets/internal payment objects
SiteScore service key
storage path/bucket/key
Postmark token
debug stack/error details
```

Recipient is always the durable server-owned `order.customer_email`. n8n/caller cannot override `To`.

Sender/template alias/message stream are server-owned configuration. n8n/caller cannot override them.

The Postmark token must never be returned, persisted in domain rows, or exposed to n8n.

No marketing email implementation.

No Postmark delivery/bounce webhook is authorized in 6.4. If later proposed, Reviewer must first inspect the then-current official webhook security contract; do not invent an HMAC/signature mechanism.

---

# 9. POSTMARK PROVIDER EVIDENCE

A provider request is NOT accepted merely because HTTP transport succeeded.

For V1, provider acceptance requires the official response semantics equivalent to:

```text
HTTP 200
ErrorCode == 0
non-empty MessageID
To == exact durable recipient
SubmittedAt is parseable provider timestamp
```

Persist durable evidence equivalent to:

```text
delivery_attempt_id
order_id
report_id
grant_id
provider = postmark
recipient
server-owned template alias/version identity
attempt number
attempt_started_at
provider_message_id nullable
provider_submitted_at nullable
status
safe failure category/code
created_at
updated_at
```

Use precise states. Allowed semantics should distinguish at least:

```text
prepared / dispatch_started
provider_accepted
provider_rejected
provider_uncertain
```

Do NOT call the accepted state:

```text
delivered
received
read
opened
```

Postmark `provider_accepted` means the provider accepted the transactional send request. It is not proof that a human inbox received or opened the email.

Provider MessageID, when known, must be persisted and protected against conflicting rebinding.

Provider response/message text persisted for diagnostics must be bounded and sanitized; never store secrets or raw token/download URL in failure text.

---

# 10. FULFILLED CONDITION

Commerce may transition to successful fulfillment only after all of the following server-owned conditions are true:

```text
payment_state == paid
exact bound analysis == completed
exact bound report == ready
valid non-revoked delivery grant was used for the accepted attempt
Postmark response is durably validated as provider_accepted
provider MessageID is durably bound to that attempt
```

Then the durable commerce terminal state is:

```text
order_state = fulfilled
payment_state = paid
fulfillment_state = completed
```

`fulfilled` therefore means:

```text
purchased verified report is available through a valid SiteScore delivery capability
+
transactional send request was durably accepted by Postmark
```

It does NOT mean the customer read/opened the message.

A browser opening the download link by itself must never mark payment or email provider acceptance.

---

# 11. DELIVERY FAILURE / RETRY SEMANTICS

Delivery failure is separate from analytical/payment truth.

Never do this solely because Postmark/email delivery failed:

```text
payment -> failed/refunded
analysis -> failed
report -> failed
```

Email delivery failure alone is NOT automatic refund authority.

Required retry behavior:

```text
duplicate n8n delivery trigger after known provider_accepted -> no second send; converge on fulfilled
provider_rejected -> durable failed attempt; server may allow bounded retry according to server-owned policy
provider_uncertain -> no fabricated success; later retry/recovery remains safe under the raw-token rule above
retry exhaustion/non-retryable configuration failure -> delivery_failed + attention_required is acceptable
payment remains paid
analysis/report truth remains unchanged
```

While retry is still authorized, the automation projection must continue to return `next_action=delivery` and must not accidentally fall through to `advance`.

After non-retryable/exhausted delivery failure:

```text
order_state = attention_required
payment_state = paid
fulfillment_state = delivery_failed
next_action = none
```

Broad scheduled repair/reconciliation of delivery failures belongs to FAZ 6.5.

---

# 12. DATABASE / MIGRATION REQUIREMENTS

Add only commerce-owned delivery persistence.

Expected migration head:

```text
0004_delivery_email
```

Suggested tables/resources:

```text
delivery_grants
delivery_attempts
```

Mandatory database-level protections as applicable:

```text
UUID primary identities
order FK
unique token_digest
bounded/validated digest shape
provider_message_id unique when non-null
attempt-number uniqueness per order or equivalent durable operation identity
status CHECK constraints
timestamp coherence
no raw token column
no Postmark secret column
```

Cross-order/report substitution must be prevented by durable relations + service invariant checks.

Migration validation must prove:

```text
0003_fulfillment_refund -> 0004_delivery_email upgrade
0004 -> 0003 downgrade
re-upgrade to 0004
commerce schema/version table remains isolated
frozen sitescore-api schema untouched
```

No DB transaction/row lock may be held across SiteScore or Postmark network I/O.

---

# 13. REQUIRED ADVERSARIAL TESTS

At minimum add deterministic tests for:

```text
strong token entropy/shape
digest-only persistence
no raw token in DB/log/domain API
exact 7-day default expiry
repeated download before expiry succeeds
expired token rejected
revoked token rejected
random/unknown token rejected
foreign order/report binding rejected
tampered durable grant/report binding rejected
report not ready rejected
report ID mismatch rejected
analysis binding mismatch rejected
upstream SiteScore auth/404/409/5xx/malformed content fail closed
upstream PDF MIME mismatch rejected
byte-length mismatch rejected
content hash mismatch rejected
S3/private storage details never surface
server-owned public base cannot be caller overridden
server-owned recipient cannot be caller/n8n overridden
Postmark secret absent from n8n/workflow/API/logs
HTTP 200 + ErrorCode != 0 is NOT accepted
HTTP 200 + missing/invalid MessageID is NOT accepted
response recipient mismatch is NOT accepted
known provider_accepted replay sends no duplicate
provider rejected -> retry-safe durable attempt
Postmark timeout/response lost -> provider_uncertain, NOT fulfilled
uncertain replay -> new attempt may send a fresh grant while prior possible emailed grant remains valid
multiple valid retry grants still resolve identical exact bound PDF
provider accepted + DB response/HTTP response lost -> replay converges without new analysis/report/payment authority
provider accepted -> fulfilled/completed/paid
email failure -> payment stays paid and analysis/report truth unchanged
```

Use real PostgreSQL coverage for state-changing and uniqueness/concurrency paths.

Use an isolated fake Postmark HTTP server for deterministic wire-level failure injection. Do not send email to real customers in CI.

---

# 14. N8N INTEGRATION TESTS

Update only the reserved 6.4 delivery branch of the locked workflow.

Prove with pinned n8n `2.33.4` runtime:

```text
delivery_pending -> commerce delivery operation
no Postmark token in n8n
no raw grant token exposed to n8n
bodyless delivery trigger
provider accepted -> commerce GET observes terminal fulfilled/completed
retryable delivery -> finite Wait/poll -> later delivery call
no delivery busy-loop
duplicate same-event execution converges
restart during delivery wait converges
provider uncertainty does not fabricate fulfilled
non-retryable delivery_failed -> attention/no action stop
all previous 6.3 pacing/restart/5xx/timeout tests remain green
```

The repository-exported sanitized workflow JSON remains authority and must be import/publish-tested exactly as in 6.3.

If workflow version changes, bump its explicit SiteScore workflow version and document the exact new workflow SHA-256 in Implementer evidence.

n8n runtime version itself must remain `2.33.4` in this checkpoint unless Reviewer explicitly reopens that decision.

---

# 15. CONFIGURATION / SECRET RULES

No real secrets or customer PII fixtures in repository.

New secret/config names only, never values, may be documented.

Expected new configuration surface:

```text
POSTMARK_SERVER_TOKEN
POSTMARK_FROM_EMAIL
POSTMARK_TEMPLATE_ALIAS
POSTMARK_TIMEOUT_SECONDS
COMMERCE_PUBLIC_BASE_URL
```

The existing server-only SiteScore credential continues to be used by commerce for frozen report retrieval.

Do not give n8n:

```text
POSTMARK_SERVER_TOKEN
SITESCORE_API_SERVICE_KEY
S3 credentials
commerce DB credentials
```

Production public base and provider endpoint must use HTTPS.

---

# 16. VALIDATION / CI GATE

Before `READY_FOR_REVIEW`, Implementer must produce fresh exact-head evidence for the same PR/branch.

Require at minimum:

```text
fresh PostgreSQL 16 migration cycle through 0004
full sitescore-commerce suite
real PostgreSQL delivery state tests
n8n static suite
pinned n8n 2.33.4 import/publish/runtime integration
isolated Postmark wire-contract integration
public download proxy integration against frozen SiteScore report/content behavior
full frozen FAZ 3/4/5 regression = 1504 PASS
secret scan
frozen-scope scan
private S3 regression
Redis/Celery regression
```

Postmark's official special `POSTMARK_API_TEST` token may be used only as optional non-delivering validation; deterministic CI must not depend on a real customer inbox.

Temporary exact-head validation workflow is acceptable. If validation is run on a temporary workflow commit and then only that workflow is removed, provide exact validated-SHA -> final-head compare proof as in prior checkpoints.

---

# 17. OUT OF SCOPE / STOP BOUNDARY

Do NOT implement in 6.4:

```text
Postmark bounce/delivery webhook tracking
marketing email
customer account system
frontend download dashboard
broad lost-event scanner
scheduled global reconciliation
expired-grant customer recovery portal
manual fake fulfilled endpoint
manual fake paid/ready state
production observability stack
rate limiting/autoscaling/deployment platform
FAZ 6.5 recovery scanner
FAZ 7+
```

FAZ 6.5 remains closed.

---

# 18. IMPLEMENTER HANDOFF REQUIREMENT

Implementer must use exactly:

```text
base:
main@7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba

branch:
faz6/6-4-delivery-grant-email

one branch
one PR
```

Before stopping, `implementer.md` must record at minimum:

```text
CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.4
IMPLEMENTER_STATE: READY_FOR_REVIEW
EXPECTED_BASE_SHA
CODE_BRANCH
PR
HEAD_SHA
changed files
sitescore-commerce version
migration head
new delivery tables/resources
public download route
Postmark API/template contract
new ENV names only
n8n workflow version/path/SHA
n8n runtime version
Postmark isolated integration evidence
PostgreSQL migration/state evidence
commerce test count
frozen regression count
exact validation run/job/SHA
validated->final delta
secret/frozen-scope evidence
CONTRACT_CHANGE_REQUIRED
DESIGN_DECISION_REVIEW_REQUIRED
ADDITIONAL_REOPEN_REQUIRED
BLOCKERS_REPORTED_BY_IMPLEMENTER
```

Then STOP.

---

# 19. REVIEWER OPENING DECISION

```text
FAZ 6.4: IMPLEMENTATION_REQUESTED
EXPECTED_BASE_SHA: 7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba
CODE_BRANCH: faz6/6-4-delivery-grant-email

BLOCKERS: NONE AT OPENING
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
USER_LOCK_AUTHORIZED: NO
START_6_5: NO
```

Implement only FAZ 6.4, update the one PR and `implementer.md`, then STOP for independent Reviewer audit.
