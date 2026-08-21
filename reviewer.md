# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.0
CHECKPOINT_TITLE: Production Baseline + Operational Contract + Compatibility Audit
REVIEWER_STATE: CONTRACT_ISSUED
IMPLEMENTER_ACTION: IMPLEMENT_CHECKPOINT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 3762ec643426e310ff82bdb00b20f58fb4ae9e09
EXPECTED_BASE_TREE_SHA: 3cc9fe7c0f8da20a4c2763661a4df304c96c94ce
CODE_BRANCH: faz7/7-0-production-operational-baseline
PR: TBD
REVIEWED_HEAD_SHA: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: FROZEN
FAZ_6_FINAL_MERGE_COMMIT: ee45e4fdd3d805137387a0fc1198eedf8d461fb2

ENTRY_CORRECTIVE_PR: #32
ENTRY_CORRECTIVE_REVIEWED_HEAD: d5207d6d5a7483d7150ae0c68034428a5d70d6e2
ENTRY_CORRECTIVE_MERGE_COMMIT: 3762ec643426e310ff82bdb00b20f58fb4ae9e09
ENTRY_CORRECTIVE_STATUS: LOCKED_VERIFIED
OPS70-H001: RESOLVED_CLOSED
BROKER_TLS_GATE: PASS_ON_MAIN
PRODUCTION_BROKER_TARGET: rediss://

MAIN_BRANCH_PROTECTED: FALSE
CANONICAL_DOCKER_ASSETS_OBSERVED: NONE
CANONICAL_OPENTOFU_IAC_OBSERVED: NONE
PRODUCTION_DEPLOYMENT_OBSERVED: NONE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

---

# 1. POST-LOCK ENTRY CORRECTIVE VERIFICATION

Reviewer independently verified the locked broker-TLS corrective before reopening normal FAZ 7.0.

Live GitHub state:

```text
PR #32: CLOSED / MERGED
reviewed corrective head:
  d5207d6d5a7483d7150ae0c68034428a5d70d6e2
merge commit / live main:
  3762ec643426e310ff82bdb00b20f58fb4ae9e09
merge tree:
  3cc9fe7c0f8da20a4c2763661a4df304c96c94ce
parent 1:
  ee45e4fdd3d805137387a0fc1198eedf8d461fb2
parent 2:
  d5207d6d5a7483d7150ae0c68034428a5d70d6e2
```

The merge commit records user-authorized LOCK and exact reviewed-head merge semantics.

Live `main` now validates broker URLs as:

```python
if not self.broker_url.startswith(("redis://", "rediss://")):
    raise ValueError("broker_url must use Redis")
```

Therefore:

```text
redis://  -> retained for local/test compatibility
rediss:// -> representable for encrypted production Valkey transport
unsupported schemes -> rejected
```

No TLS downgrade, rewrite, dependency change, Commerce change, n8n change, schema change, scoring change, or business-authority change was merged by the corrective.

Disposition:

```text
OPS70-H001: CLOSED
NORMAL FAZ 7.0: AUTHORIZED TO IMPLEMENT
```

---

# 2. CHECKPOINT PURPOSE

FAZ 7.0 establishes the **authoritative production runtime baseline and operational contract** before containerization, IaC, staging deployment, observability, traffic controls, resilience, backups, load testing, or production-readiness proof.

This checkpoint is deliberately documentation/inventory-first.

It must answer, from live source rather than assumptions:

```text
What runtime processes exist?
How is each process started?
Which package/version owns it?
Which environment variables does it consume?
Which values are secrets?
Which routes/ports may ever be public?
Which components must remain internal?
Which durable stores exist and who owns them?
Which external providers are called?
How do staging and production differ and remain isolated?
What migration authority exists?
What scheduler/worker singleton or concurrency constraints exist?
What health model will later be deployed?
Which production gaps remain for FAZ 7.1+?
```

FAZ 7.0 must **not** make deployment architecture implicit. Later checkpoints must be able to consume these documents as executable design authority.

---

# 3. SELECTED PRODUCTION PLATFORM — FROZEN FOR FAZ 7

Do not silently replace this stack:

```text
Application platform: DigitalOcean App Platform
Relational database: DigitalOcean Managed PostgreSQL
Broker: DigitalOcean Managed Valkey
Object storage: DigitalOcean Spaces
Private networking: DigitalOcean VPC / App Platform internal networking
Container registry: GHCR
CI/CD: GitHub Actions
Infrastructure as Code: OpenTofu
Public production ingress / edge controls: Cloudflare
Central logs: Better Stack
Load testing: k6
```

If live technical evidence proves a selected component cannot satisfy a mandatory contract, stop and report:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

Do not substitute a different vendor or weaken a security requirement without Reviewer contract change and user authority.

Current DigitalOcean contract recheck on 2026-08-21 confirms:

```text
Managed Valkey requires SSL/TLS client connections.
App Platform supports internal services with no public internet endpoint.
App Platform supports VPC connectivity to VPC-enabled resources.
App Platform services must bind their exposed application port on 0.0.0.0.
```

The broker compatibility corrective now makes the required `rediss://` transport representable by the frozen API.

---

# 4. CURRENT LIVE GAPS — RECORD, DO NOT FIX IN 7.0

Reviewer reverified these as current production gaps:

```text
main branch protected = false
no canonical production Dockerfile set observed
no canonical OpenTofu production stack observed
no App Platform staging/production deployment spec observed
no production/staging cloud deployment proven
no production ingress proof
no Better Stack production log pipeline proof
no Cloudflare production WAF/rate-limit proof
no backup/restore drill proof
no DR proof
no k6 production-readiness load evidence
```

These are expected future-checkpoint gaps, not reasons to modify runtime code in 7.0.

Checkpoint ownership:

```text
7.1 -> containers / supply chain / GitHub governance
7.2 -> IaC / staging deployment / networking / secrets
7.3 -> observability / SLO / alerts
7.4 -> traffic safety / abuse / provider-cost controls
7.5 -> resilience / backpressure / capacity / release safety
7.6 -> backups / restore / data protection / DR
7.7 -> staging E2E / load / failure drills / readiness evidence
```

Do not pull work from those checkpoints into 7.0 unless Reviewer explicitly reopens scope.

---

# 5. REQUIRED PERMANENT DELIVERABLES

Create exactly these production baseline documents:

```text
docs/PRODUCTION_OPERATIONS_HANDOFF.md
docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md
```

No production source-code change is expected or authorized in normal 7.0.

No migration is authorized.
No package version bump is authorized.
No dependency change is authorized.
No Dockerfile is authorized yet.
No OpenTofu file is authorized yet.
No GitHub branch/ruleset mutation is authorized yet.
No cloud resource creation is authorized.
No staging or production deploy is authorized.

If a source defect is discovered that makes the selected runtime contract impossible, stop instead of fixing it opportunistically:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

---

# 6. `docs/PRODUCTION_OPERATIONS_HANDOFF.md` — REQUIRED CONTENT

This document must be a source-grounded operational inventory, not a high-level architecture essay.

At minimum include all sections below.

## 6.1 Exact frozen/active package inventory

Record package name and exact current version for every production-relevant package, including at least:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
sitescore-benchmarks
sitescore-pipeline
sitescore-app
sitescore-report
sitescore-api
sitescore-commerce
n8n
```

Record exact source file from which each version is derived.

Known entry facts to independently reverify:

```text
sitescore-api == 0.3.0
sitescore-report == 0.3.0
sitescore-commerce == 0.6.0
n8n == 2.33.4
```

Do not use chat history as version evidence.

## 6.2 Runtime process inventory

Derive exact launch/import authority from source and package metadata for:

```text
commerce-web
api-web
api-worker
api-beat
commerce-dispatcher
n8n-automation
```

For each process record:

```text
owner package
entry module / console script
exact intended run command shape
network listener or no listener
public/internal/worker classification
durable state dependencies
external provider dependencies
singleton / horizontal-scaling constraint
termination behavior relevant to safe shutdown
```

Do not invent a run command merely because it is conventional. Trace actual FastAPI app objects, Celery app builders, console scripts, and n8n frozen runtime evidence.

## 6.3 Commerce dispatcher one-shot contract

Live source currently exposes:

```text
sitescore-commerce-dispatch-paid-outbox
```

and `dispatcher.main()` calls exactly one `dispatch_once()` invocation before exiting.

The handoff must explicitly record:

```text
CURRENT FORM: ONE-SHOT
FUTURE DEPLOYMENT REQUIREMENT: deployment-owned supervisor/loop
EMPTY behavior: short sleep in wrapper before next invocation
transport failure behavior: bounded backoff
signals: clean termination
business/payment authority in wrapper: FORBIDDEN
outbox/event identity mutation in wrapper: FORBIDDEN
```

The future supervisor may repeatedly invoke the frozen one-shot command but must not reimplement payment/order/outbox semantics.

## 6.4 Celery runtime contract

Read live `sitescore-api` Celery source and record at least:

```text
broker binding source
broker URL source
result backend behavior
worker queue/task registration
worker soft/hard limits
acks_late
acks_on_failure_or_timeout
reject_on_worker_lost
prefetch multiplier
beat schedule
```

Reverify the frozen schedules:

```text
drain_outbox: 10 seconds
reconcile_timeouts: 15 seconds
```

Record deployment requirements:

```text
api-worker -> horizontally bounded, staging initial concurrency = 1
api-beat -> exactly one intended scheduler instance
api-beat horizontal scaling -> forbidden absent scheduler-dedup proof
```

## 6.5 n8n frozen runtime contract

Inventory current n8n evidence and record:

```text
version = 2.33.4
frozen image digest
order-paid workflow identity/hash
recovery workflow identity/hash
persistence requirement = PostgreSQL
N8N_ENCRYPTION_KEY requirement
replica target = 1 initially
editor/admin/rest surface = non-public
allowed externally reachable workflow ingress = exact locked order-paid webhook path only
```

Reverify the previously frozen expected identities from live repository evidence. If any exact hash differs from the frozen FAZ 6 record, stop and report blocker rather than normalizing the difference.

## 6.6 Environment-variable inventory

Enumerate **every production-relevant environment variable consumed by source** for:

```text
SiteScore API web/worker/beat
Commerce web
Commerce dispatcher
n8n
report/object storage
provider clients
OpenAI narrator if applicable
Postmark
Stripe
```

For each variable record columns:

```text
name
consumer component
source file
required/optional/defaulted
secret? yes/no
staging/prod shared? must be NO where isolation is required
rotation impact
notes/validation constraints
```

Do not include actual secret values.

At minimum classify these classes as secrets when present:

```text
DB credentials
Valkey credentials
Stripe secret key
Stripe webhook secret
Postmark token
SiteScore service/API key material
Commerce automation API key
Commerce n8n ingress secret
n8n encryption key
Spaces access/secret keys
OpenAI key
provider API credentials
API key pepper
```

## 6.7 External dependency matrix

Record source-grounded outbound dependencies and authority roles, including as applicable:

```text
Stripe
Postmark
OpenAI
Google Places
Census ACS
OSM/Nominatim
Mapbox / routing provider(s)
DigitalOcean PostgreSQL
DigitalOcean Valkey
DigitalOcean Spaces
n8n
```

For each state:

```text
caller
purpose
authority level
transport requirement
timeout/retry behavior if visible
failure posture
cost-bearing? yes/no
```

Do not describe a provider as business truth if frozen architecture treats it only as evidence/transport.

## 6.8 Migration inventory

Record independent migration authorities for:

```text
sitescore-api
sitescore-commerce
n8n persistence schema/runtime
```

For API and Commerce identify:

```text
Alembic configuration path
migration head
production predeploy command shape
single-writer requirement
failure behavior = blocks deployment
```

Do not run production migrations in this checkpoint.

---

# 7. `docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md` — REQUIRED CONTENT

This is the normative FAZ 7 runtime topology contract consumed by 7.1–7.7.

## 7.1 Environment isolation

Define two independent environments:

```text
staging
production
```

They must not share:

```text
Stripe secret keys
Stripe webhook secrets
Stripe Price IDs where environment-specific
Postmark token
SiteScore service key / API-key material
Commerce automation key
Commerce n8n ingress secret
n8n encryption key
DB credentials or customer data
Valkey credentials
Spaces bucket or storage credentials
delivery capability tokens
real customer email flow
```

Staging uses Stripe **test mode**.

Document any variables that may be identical because they are non-secret constants, while preserving separate secret material and durable state.

## 7.2 Component graph

Define the intended topology for each environment:

```text
Cloudflare
  -> commerce-web [public allowlisted routes only]
  -> n8n order-paid ingress [exact path only, controlled HTTPS]

commerce-web
  -> commerce PostgreSQL
  -> Stripe
  -> Postmark where frozen flow requires
  -> SiteScore api-web over internal routing
  -> Spaces only through frozen delivery/report path as applicable

commerce-dispatcher
  -> commerce PostgreSQL
  -> exact n8n order-paid HTTPS ingress

api-web [internal only]
  -> API PostgreSQL
  -> broker/storage/providers as required

api-worker
  -> API PostgreSQL
  -> Managed Valkey via rediss://
  -> Spaces
  -> providers/report dependencies

api-beat
  -> Managed Valkey via rediss://
  -> API task scheduling only

n8n-automation
  -> n8n PostgreSQL
  -> Commerce automation API over internal/private route
```

Correct any edge above if live frozen source proves it false, and explain the source evidence. Do not alter frozen business authority to force the diagram to match this prompt.

## 7.3 Component deployment classes

Normative targets:

### commerce-web

```text
DigitalOcean App Platform service
public service
immutable image digest later in 7.1/7.2
TCP/process health acceptable if no frozen /health route
```

Public internet allowlist must ultimately be only:

```text
POST /v1/orders
POST /v1/webhooks/stripe
GET /d/{opaque_token}
```

Commerce automation routes are internal only.

### api-web

```text
App Platform internal service
no public ingress
immutable API image later
TCP/process health acceptable
private Commerce -> API routing only
```

### api-worker

```text
App Platform worker
no public route
bounded concurrency
staging initial concurrency = 1
```

### api-beat

```text
App Platform worker
exactly one intended instance
no horizontal scale without deduplication proof
```

### commerce-dispatcher

```text
App Platform worker
runs deployment-owned supervisor around frozen one-shot command
no public route
```

### n8n-automation

```text
frozen n8n 2.33.4 lineage
PostgreSQL persistence
N8N_ENCRYPTION_KEY
one replica initially
editor/admin/rest non-public
only exact locked order-paid webhook path externally reachable
```

## 7.4 Database contract

Per environment define Managed PostgreSQL with isolated databases/users:

```text
sitescore_api
sitescore_commerce
n8n
```

Require:

```text
separate least-privilege users
TLS
private/VPC path where platform supports
trusted sources
PITR enabled later when infrastructure is created
connection budgets per component reserved for 7.5 capacity proof
```

Never give n8n application credentials for SiteScore API or Commerce DBs.

## 7.5 Managed Valkey contract

Per environment:

```text
private/VPC reachable
SSL/TLS required
auth/trusted sources enabled
target URL = rediss://...
```

The locked corrective means API Settings now accepts this target.

Do not use `redis://` in production merely because it remains supported for local/test compatibility.

## 7.6 Spaces contract

Per environment:

```text
separate staging/prod buckets
private objects
bucket listing off/public ACL off
report CDN off
versioning target = on
least-privilege credentials
explicit region + endpoint
no direct customer object URL
```

Customer delivery remains through frozen delivery-grant authority.

## 7.7 n8n HTTPS / path-isolation constraint

Commerce production settings require an HTTPS n8n webhook URL.

The runtime contract must state:

```text
production Commerce -> n8n ingress must be HTTPS
only exact order-paid webhook path may be externally reachable
n8n editor/admin/rest must not become public as a side effect
```

If App Platform routing cannot prove safe path isolation for the n8n service, the allowed later design is a minimal operations-owned relay that:

```text
accepts only the exact webhook path
applies authentication/rate/body controls
forwards to internal n8n
contains no payment/order/business authority
```

Do not solve this by exposing the whole n8n service.

## 7.8 Public/private route matrix

Create a table covering every known HTTP surface.

Public candidates are strictly limited to:

```text
Commerce:
  POST /v1/orders
  POST /v1/webhooks/stripe
  GET /d/{opaque_token}

n8n:
  exact frozen order-paid webhook ingress only
```

Internal only:

```text
SiteScore /v1/* analysis/report API
Commerce /v1/automation/*
n8n editor/admin/rest
DB endpoints
Valkey endpoint
object storage credentials/origins
workers/beat/dispatcher
```

For every Commerce route, derive the exact live route path and method from source rather than copying only this list.

## 7.9 Health semantics

Do not reopen frozen application code merely to add health endpoints in 7.0.

Runtime contract:

```text
liveness/health = process + socket/TCP where sufficient
dependency health = observed separately
readiness must not fabricate business/scoring readiness
```

A TCP-successful app with unavailable DB/provider may be process-live but dependency-degraded; document these separately.

## 7.10 Release/migration boundary preview

Record future release constraints without implementing them:

```text
production deploy only from user-LOCKed main SHA
immutable image digests
explicit production GitHub Environment approval
no automatic deploy_on_push to production
API + Commerce Alembic migrations as explicit predeploy jobs
migration failure blocks release
release record must bind source SHA + image digests + migration heads + deploy result
```

---

# 8. FROZEN AUTHORITY BOUNDARIES — MUST APPEAR IN BOTH DOCUMENTS

Both docs must clearly preserve:

```text
Stripe = external processor evidence
Commerce PostgreSQL = durable commercial truth
SiteScore API/PostgreSQL = analysis/report durable truth
Redis/Valkey/Celery = transport/execution, not durable business truth
n8n = orchestration only
Postmark = email transport/provider evidence
Spaces object = report artifact storage, not scoring authority
```

And analytical authority remains frozen:

```text
COMB-005 approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition = UNRESOLVED
real production analysis may correctly terminate not_score_ready
```

Forbidden in all operational documentation/design:

```text
fake road/parking scores
default score 50
neutral fallback
hidden renormalization
deployment shortcut that fabricates score readiness
claim that staging/load testing is empirical business validation
```

Canonical validity statement remains:

```text
Mathematically validated scoring engine; empirical validation pending.
```

---

# 9. STAGING / PRODUCTION SEPARATION MATRIX

The runtime contract must contain a matrix with at least these rows:

```text
App Platform app/project
PostgreSQL cluster / DBs
Valkey cluster
Spaces bucket
Stripe mode/key/webhook secret/Price IDs
Postmark credentials
SiteScore service credentials
Commerce automation key
Commerce n8n ingress secret
n8n DB
n8n encryption key
Cloudflare hostname/policies
Better Stack source/token
provider API credentials/budgets
OpenAI credential/budget
customer emails
backup targets
```

Columns:

```text
staging identity
production identity
may share? yes/no
reason
secret? yes/no
creation checkpoint
```

For secret rows, do not write actual values.

---

# 10. SOURCE-TO-RUNTIME TRACEABILITY

Every important runtime assertion in the docs must cite an exact repository path, symbol, package metadata record, workflow JSON/hash record, or frozen audit artifact.

Minimum source anchors include:

```text
sitescore-api/src/sitescore_api/settings.py
sitescore-api Celery app/task source
sitescore-api FastAPI app/routes source
sitescore-api pyproject + Alembic config
sitescore-commerce/src/sitescore_commerce/settings.py
sitescore-commerce/src/sitescore_commerce/dispatcher.py
sitescore-commerce FastAPI route source
sitescore-commerce/pyproject.toml
sitescore-commerce Alembic config/migrations
automation/n8n workflow/runtime evidence
automation/n8n static/runtime test evidence
FAZ 6 final integrated audit
```

Do not cite historical chat text as runtime evidence.

---

# 11. COMPATIBILITY AUDIT / STOP CONDITIONS

During 7.0, explicitly verify and record:

```text
A. API Settings accepts rediss:// on current main.
B. Celery receives the broker URL unchanged.
C. production target remains rediss://.
D. Commerce production external/base/n8n URLs retain HTTPS requirements.
E. dispatcher remains one-shot.
F. n8n version/digest/workflow hashes match frozen FAZ 6 identities.
G. API/Commerce DB migrations remain independent.
H. no runtime currently requires SQLite/in-memory durable truth in production.
I. no source route forces api-web to be internet-public.
J. no frozen source requires n8n editor/admin to be public.
```

If any of A–J fails materially, stop and set the appropriate control flag/blocker rather than documenting an impossible topology.

In particular:

```text
unencrypted production broker -> BLOCK
internal API forced public -> BLOCK
n8n admin forced public -> BLOCK
shared staging/prod secret requirement -> BLOCK
frozen n8n identity drift -> BLOCK
Commerce dispatcher cannot be safely supervised without changing authority -> BLOCK
```

Use blocker family:

```text
OPS70-H001, OPS70-H002, ...
```

`OPS70-H001` is already consumed and CLOSED for the rediss corrective. Do not reuse it for a different finding.

---

# 12. GITHUB / REPOSITORY BASELINE RECORD

Record current repository governance baseline in the 7.0 docs:

```text
main protected = false
required status checks = none/enforcement off at current observation
```

This is **not** acceptable for production release, but remediation belongs to 7.1.

Also record current supply-chain/IaC baseline:

```text
canonical production Docker assets: not observed at 7.0 entry
canonical OpenTofu production stack: not observed at 7.0 entry
```

Implementer must independently repeat repository-wide discovery before writing this statement. If assets do exist, inventory them instead of repeating Reviewer’s search result.

---

# 13. REQUIRED VALIDATION EVIDENCE

Because 7.0 is documentation-only, acceptance is driven by source traceability and freeze preservation rather than new runtime behavior.

Before `READY_FOR_REVIEW`, provide:

```text
1. exact BASE_SHA and HEAD_SHA
2. PR number and state
3. git diff --name-only <base>...<head>
4. git diff --stat <base>...<head>
5. git diff --check
6. proof permanent PR diff is limited to the two authorized docs
7. source inventory commands/searches used
8. exact current package versions
9. exact broker compatibility proof from current main/tests
10. exact n8n frozen identity proof
11. exact dispatcher one-shot proof
12. exact branch-protection observation
13. explicit statement: no cloud deployment/resource mutation performed
14. explicit statement: no secret values committed
```

Also run the focused broker-TLS tests from the new base/branch and record their exact result.

At minimum expected unchanged focused result:

```text
9 PASS
```

If any production source/test file appears in the checkpoint PR diff, stop: 7.0 scope has been violated unless Reviewer explicitly reopened the contract.

The historical FAZ 6 provenance-only Commerce test remains phase-local. Do not edit it in 7.0. No Commerce/n8n code bytes are authorized to change.

---

# 14. REQUIRED `implementer.md` HANDOFF

When implementation is complete, Implementer must update its coordination file and stop with:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.0
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO
BASE_SHA: 3762ec643426e310ff82bdb00b20f58fb4ae9e09
BRANCH: faz7/7-0-production-operational-baseline
PR: #N
HEAD_SHA: <exact SHA>
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS_REPORTED_BY_IMPLEMENTER: NONE
PERMANENT_FILES_CHANGED:
- docs/PRODUCTION_OPERATIONS_HANDOFF.md
- docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md
```

If a blocker exists, replace the zero/none values truthfully and stop.

Do not merge.
Do not issue your own LOCK.
Do not begin 7.1.

---

# 15. REVIEWER ACCEPTANCE STANDARD

Reviewer will independently audit the exact PR HEAD for:

```text
scope correctness
source-to-document traceability
package/runtime inventory completeness
environment-variable completeness
secret classification
staging/prod isolation
public/private route accuracy
Celery worker/beat constraints
Commerce dispatcher one-shot treatment
n8n frozen identity/persistence/admin isolation
PostgreSQL/Valkey/Spaces authority boundaries
TLS compatibility
migration ownership
health semantics
cloud-platform compatibility
frozen analytical/business authority preservation
absence of future-checkpoint implementation leakage
absence of secrets
```

Reviewer will return one of:

```text
HARDENING_REQUIRED
READY_TO_LOCK
```

READY_TO_LOCK will bind to one exact HEAD SHA only.

Only literal user `LOCK` permits merge.

---

# 16. 7.0 EXIT CRITERIA

FAZ 7.0 may be marked READY_TO_LOCK only when:

```text
production runtime inventory is complete and source-grounded
staging/prod isolation is explicit
component graph is explicit
public/private boundary is explicit
rediss:// production contract is explicit and compatible
one-shot dispatcher supervision requirement is explicit
Celery beat singleton requirement is explicit
n8n persistence/encryption/admin isolation is explicit
DB/Valkey/Spaces ownership is explicit
migration authority is explicit
current repo/governance gaps are explicit
all later-checkpoint work is clearly deferred
no production source code changed
no cloud deployment occurred
no secret leaked
no blocker remains
```

FAZ 7.1 is not authorized until 7.0 receives user LOCK, is merged, and Reviewer performs post-lock verification.

---

# 17. FINAL REVIEWER DECLARATION

```text
FAZ 7.0 ENTRY CORRECTIVE: LOCKED / VERIFIED
OPS70-H001: CLOSED
LIVE MAIN: 3762ec643426e310ff82bdb00b20f58fb4ae9e09
BROKER TLS GATE: PASS
NORMAL FAZ 7.0: CONTRACT ISSUED
IMPLEMENTER MAY IMPLEMENT 7.0 ONLY
PRODUCTION DEPLOY: NOT AUTHORIZED
FAZ 7.1: NOT AUTHORIZED
FAZ 8: NOT AUTHORIZED
PUBLIC LAUNCH: NOT AUTHORIZED
LOCK AUTHORITY: USER ONLY
```
