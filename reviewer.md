# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.0
CHECKPOINT_TITLE: Production Operational Baseline + Deployment Contract

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: ee45e4fdd3d805137387a0fc1198eedf8d461fb2
EXPECTED_BASE_TREE_SHA: 5660f97ad59a8d48419d29e57ee0fc3e2d140e24
CODE_BRANCH: faz7/7-0-production-operational-baseline
PR: TBD
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_VERIFIED: YES
FAZ6_FINAL_PR: #31
FAZ6_FINAL_PR_STATE: CLOSED_MERGED
FAZ6_FINAL_REVIEWED_HEAD: 9856619a98fca93f14027347e26f04a13e18163c
FAZ6_FINAL_MERGE_COMMIT: ee45e4fdd3d805137387a0fc1198eedf8d461fb2
FAZ6_FINAL_MERGE_PARENT_1: df4e3181712e7f426f8f1752628952a620c98f05
FAZ6_FINAL_MERGE_PARENT_2: 9856619a98fca93f14027347e26f04a13e18163c
FAZ6_FINAL_TREE_MATCH: YES
FAZ6_CORRECTIVE_PR: #30
FAZ6_CORRECTIVE_MERGE_COMMIT: df4e3181712e7f426f8f1752628952a620c98f05

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: FROZEN
FAZ_6_FINAL_STATUS: LOCKED

LIVE_MAIN_BLOB_COUNT: 476
PRODUCTION_OPERATIONS_HANDOFF_PRESENT: NO
DOCKERFILE_COUNT: 0
GITHUB_ACTION_WORKFLOW_COUNT: 0
APP_PLATFORM_SPEC_PRESENT: NO
OPENTOFU_TERRAFORM_PRESENT: NO
PRODUCTION_DEPLOYMENT_PRESENT: NO

DIGITALOCEAN_PLATFORM_SELECTION: RETAINED_FOR_7_0
VALKEY_TLS_COMPATIBILITY: UNPROVEN_7_1_ENTRY_GATE
PRODUCTION_ACQUISITION_FACTORY: ABSENT
PRODUCTION_PROVIDER_ENV_SCHEMA: ABSENT
PRODUCTION_START_COMMANDS: NOT_PINNED

BLOCKERS: NONE_AT_CONTRACT_ISSUANCE
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
```

---

# 1. REVIEWER INDEPENDENT LIVE-GITHUB FINDINGS

Reviewer fetched live `main`, both coordination files, PR #31, corrective PR #30, the FAZ 6 final integrated audit, the exact repository tree, runtime settings, package manifests, migrations, n8n runtime/workflows and current platform files.

Authoritative entry state is:

```text
main@ee45e4fdd3d805137387a0fc1198eedf8d461fb2
tree@5660f97ad59a8d48419d29e57ee0fc3e2d140e24
```

PR #31 is merged from reviewed head `9856619a98fca93f14027347e26f04a13e18163c` onto corrective locked base `df4e3181712e7f426f8f1752628952a620c98f05`. Reviewer and Implementer coordination records agree on parentage, merge tree and frozen FAZ 6 state. No FAZ 7 source work exists on `main`.

The required FAZ 6-era `PRODUCTION_OPERATIONS_HANDOFF.md` or an equivalent complete production operations document is absent. This remains a documentation/process gap, not evidence that frozen analytical, payment or report authority is defective. Checkpoint 7.0 must close it by deriving truth from the exact live repository; FAZ 6 must not be reopened merely to rename or backfill an old artifact.

The root `STAGING_MANIFEST.json` is a historical frozen-package source/hash manifest. It is **not** evidence of a deployed staging environment.

---

# 2. EXACT CURRENT RUNTIME INVENTORY TO PRESERVE IN THE BASELINE

The Implementer must independently re-read these files at the expected base and record the same facts, correcting only if live GitHub proves a factual difference.

## 2.1 SiteScore API

```text
package: sitescore-api==0.3.0
ASGI object: sitescore_api.app:app
runtime builder: sitescore_api.runtime:build_runtime
Celery application: sitescore_api.tasks:celery_app
service-key CLI: sitescore-provision-service-key
PostgreSQL migration chain:
  0001_faz5_1_consumer_lifecycle
  -> 0002_faz5_5_report_artifact
  -> 0003_faz5_5_canonical_success_boundary
```

Frozen application routes:

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

The constructed FastAPI application also retains its framework OpenAPI/docs routes. Because `sitescore-api` is a private/internal service in the FAZ 7 target, those routes must not be made public. Checkpoint 7.0 must inventory them as current runtime exposure, not pretend they are absent.

Celery semantics currently encoded in source:

```text
result backend: disabled
task_ignore_result: true
late ACK: true
ACK on failure/timeout: true
reject on worker lost: true
prefetch multiplier: 1
soft limit: 840 seconds default
hard limit: 900 seconds default
analysis durable deadline: 900 seconds default
beat: drain_outbox every 10 seconds
beat: reconcile_timeouts every 15 seconds
```

Current operational gaps to state explicitly:

- no production Dockerfile;
- no pinned ASGI server dependency or repository-owned production web command;
- no repository-owned worker/beat start command;
- module-level API creation intentionally tolerates missing runtime configuration and can construct an app with `runtime=None`; production deployment therefore needs an external fail-closed preflight/start boundary in 7.1 rather than assuming import success proves readiness;
- SQLAlchemy pool sizing is not configured beyond `pool_pre_ping=True`;
- no application health route exists;
- no production `CanonicalAcquisitionDeployment` factory exists;
- provider credential/configuration environment names for such a factory do not yet exist;
- without `SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY`, canonical execution uses the missing-evidence boundary and cannot manufacture score readiness.

## 2.2 SiteScore Commerce

```text
package: sitescore-commerce==0.6.0
ASGI factory: sitescore_commerce.api:create_app
paid-outbox CLI: sitescore-commerce-dispatch-paid-outbox
PostgreSQL migration chain:
  0001_commerce_order_checkout
  -> 0002_webhook_payment_authority
  -> 0003_fulfillment_refund
  -> 0004_delivery_email
  -> 0005_recovery_reconciliation
Stripe SDK: 15.4.0
Stripe API: 2026-07-29.dahlia
```

Exact frozen constructed application surface:

```text
POST /v1/orders
POST /v1/webhooks/stripe
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
GET  /d/{opaque_token}
```

Implicit OpenAPI/Swagger/ReDoc/OAuth helper routes remain disabled. No health endpoint may be added in 7.0.

The paid-outbox CLI processes at most one durable unpublished event per invocation. It is not a long-running service. This must be represented accurately. A future near-real-time dispatcher needs a supervised bounded loop/worker design; a 15-minute platform cron is not acceptable for normal paid-order dispatch latency.

Current operational gaps to state explicitly:

- no production Dockerfile;
- no pinned ASGI server dependency or production web command;
- no long-running/supervised paid-outbox dispatcher process;
- SQLAlchemy pool sizing is not operationally specified;
- README title/version is historically stale (`0.1.0`) while authoritative package/runtime version is `0.6.0`; do not use the README title as version authority;
- no application health route exists and the exact-seven route freeze forbids silently adding one.

## 2.3 n8n

```text
runtime version: 2.33.4
current compose image reference: n8nio/n8n:2.33.4
validated image identity:
  n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
local compose binding: 127.0.0.1:5678 -> 5678
current persistence: named local volume /home/node/.n8n
order workflow export: active=false
recovery workflow export: active=false
order workflow SHA256:
  02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery workflow SHA256:
  f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
recovery schedule: every 5 minutes
```

The current compose file is a local runtime proof, not a production specification. It uses an image tag rather than the validated digest and local-volume persistence rather than managed PostgreSQL. Production must not copy those two limitations forward.

## 2.4 Report/object-storage runtime

`sitescore-api` uses boto3 `S3CompatibleObjectStorage`; it stores PDF bytes in private S3-compatible storage and keeps metadata/lifecycle truth in PostgreSQL. DigitalOcean Spaces compatibility remains a 7.1 proof obligation. Customer delivery continues through frozen authenticated/opaque-token application paths; direct public object URLs are forbidden.

The report narrative layer uses deterministic fallback unless `SITESCORE_NARRATIVE_MODEL_ID` is configured. If configured, the OpenAI SDK uses its normal credential boundary, including `OPENAI_API_KEY`; LLM output remains constrained and non-authoritative.

## 2.5 Repository/platform state

Exact live-tree inspection found:

```text
Dockerfiles: none
.github/workflows: none
DigitalOcean App Platform spec: none
OpenTofu/Terraform: none
production topology document: none
secrets/configuration contract: none
production release workflow: none
deployed staging evidence: none
```

These are expected checkpoint inputs, not license to fabricate completed infrastructure.

---

# 3. CHECKPOINT 7.0 PURPOSE

Create a complete, durable and testable production-operations baseline derived from `main@ee45e4fdd3d805137387a0fc1198eedf8d461fb2`.

Checkpoint 7.0 is documentation, architecture and verification-tooling work only. It must define what exists, what does not exist, the selected production topology, trust/exposure/cost boundaries, exact configuration-name contract, later-phase entry gates and acceptance evidence.

Checkpoint 7.0 does **not** deploy cloud resources, build production images, create secrets, activate workflows, change runtime routes, or start 7.1.

---

# 4. REQUIRED DELIVERABLES

Create exactly these durable artifacts unless a path collision is proven before work begins:

```text
docs/production/PRODUCTION_OPERATIONS_HANDOFF.md
docs/production/PRODUCTION_TOPOLOGY.md
docs/production/SECRETS_AND_CONFIGURATION_CONTRACT.md
docs/production/THREAT_AND_COST_BOUNDARIES.md
docs/production/CHECKPOINT_7_0_PRODUCTION_OPERATIONAL_BASELINE.md
ops/production/verify_checkpoint_7_0.py
ops/production/tests/test_checkpoint_7_0.py
```

Optional only when needed to make the directory navigable:

```text
docs/production/README.md
ops/production/README.md
```

No other permanent file may change.

A temporary exact-head validation workflow may be used only at:

```text
.github/workflows/faz7-7-0-exact-head-validation.yml
```

If used, it must have minimum `contents: read` permissions, no `pull_request_target`, no cloud/provider secrets, no deployment step and no write permission. It must be removed before READY_FOR_REVIEW. The Implementer must record the validated SHA, run/job IDs, conclusions and the exact validated-to-final delta. A permanent CI/release workflow belongs to 7.1, not 7.0.

---

# 5. SELECTED TARGET TOPOLOGY TO DOCUMENT

Retain the DigitalOcean MVP platform family. Official platform documentation confirms App Platform supports public services, internal services, workers, jobs, internal ports, TCP health checks and GHCR image tags/digests. Managed PostgreSQL/Valkey support trusted-source/VPC restriction. Spaces supports private objects, versioning and supported lifecycle controls.

The target topology document must contain both `CURRENT AT 7.0 BASE` and `TARGET FOR 7.1+`; never collapse target design into a claim that resources already exist.

Target logical components:

```text
DigitalOcean App Platform / staging first

1. commerce-web
   - public ingress only for required customer/Stripe/download paths
   - internal reachability for authenticated automation paths
   - exact frozen seven-route application unchanged

2. sitescore-api
   - internal service only
   - no public ingress

3. sitescore-celery-worker
   - worker component, no public route
   - bounded concurrency to be fixed/measured in 7.1/7.4

4. sitescore-celery-beat
   - singleton scheduler authority
   - no duplicate beat replicas

5. commerce-paid-outbox-worker
   - long-running supervised bounded dispatch loop
   - invokes the existing one-event dispatcher safely
   - no 15-minute cron substitution for normal paid-order flow

6. n8n
   - internal service on port 5678
   - editor/admin not publicly routed
   - required order-paid webhook reachable from commerce over private app network
   - separate managed PostgreSQL database/user

7. migration-api job
   - controlled pre-deploy/single-authority Alembic upgrade to API head

8. migration-commerce job
   - controlled pre-deploy/single-authority Alembic upgrade to Commerce head

9. Managed PostgreSQL
   - one cost-conscious cluster permitted initially
   - separate logical DBs and least-privilege users: sitescore_api, sitescore_commerce, n8n

10. Managed Valkey
    - Celery broker transport only
    - no durable business truth

11. private Spaces bucket
    - report objects
    - no public listing/object ACL

12. GHCR + GitHub Actions
    - immutable image identity and staged promotion beginning in 7.1
```

## 5.1 Public ingress allowlist

App Platform ingress must eventually expose only:

```text
POST /v1/orders
POST /v1/webhooks/stripe
GET  /d/{opaque_token}
```

The following Commerce routes remain real and frozen but must be reachable only through the private/internal service origin and their existing authentication:

```text
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
```

Checkpoint 7.0 must document that path-level edge routing is an infrastructure exposure rule, not a mutation of `create_app().routes`. 7.1 must prove unmatched public automation paths fail at the edge while all seven routes remain present internally.

`sitescore-api`, n8n editor/admin, workers, jobs, PostgreSQL, Valkey and Spaces objects receive no public application ingress.

## 5.2 Health-check decision

Do not add `/health`, `/ready` or any other route in 7.0.

Document the provisional 7.1 approach:

- TCP health checks for Commerce and SiteScore API web components by omitting an HTTP health path;
- separate authenticated smoke/dependency gates after deployment;
- process-exit/restart plus explicit queue/DB/worker monitoring for non-HTTP workers;
- any future application health endpoint requires explicit frozen-contract review.

## 5.3 App Platform cron constraint

Official DigitalOcean documentation states scheduled App Platform jobs run at a minimum interval of 15 minutes. Therefore normal paid-outbox dispatch must not be designed as a scheduled job. A long-running worker is the selected direction. The five-minute n8n recovery scheduler remains separate recovery/reconciliation authority and must not become the normal event-publish authority.

---

# 6. EXACT CONFIGURATION-NAME INVENTORY

`SECRETS_AND_CONFIGURATION_CONTRACT.md` must classify every name as `required`, `optional`, `conditional`, `platform-injected`, or `future-7.1`, and as `secret`, `sensitive locator`, or `non-secret`. Values must be placeholders only.

## 6.1 Existing SiteScore API names

```text
SITESCORE_DATABASE_URL                         required secret/sensitive locator
SITESCORE_BROKER_URL                           required secret/sensitive locator
SITESCORE_API_KEY_PEPPER                       required secret
SITESCORE_ANALYSIS_DEADLINE_SECONDS            optional non-secret
SITESCORE_POLL_RETRY_AFTER_SECONDS             optional non-secret
SITESCORE_WORKER_SOFT_LIMIT_SECONDS            optional non-secret
SITESCORE_WORKER_HARD_LIMIT_SECONDS            optional non-secret
SITESCORE_REPORT_STORAGE_BUCKET                optional/non-secret name
SITESCORE_REPORT_STORAGE_REGION                optional non-secret
SITESCORE_REPORT_STORAGE_ENDPOINT_URL          optional sensitive locator
SITESCORE_REPORT_MAX_BYTES                     optional non-secret
SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY       conditional non-secret module:callable
SITESCORE_NARRATIVE_MODEL_ID                    optional non-secret
OPENAI_API_KEY                                 conditional secret when model configured
AWS_ACCESS_KEY_ID                              required secret for Spaces runtime
AWS_SECRET_ACCESS_KEY                          required secret for Spaces runtime
AWS_SESSION_TOKEN                              conditional secret if temporary credentials are used
```

The boto3 credential names are SDK credential boundary names; the SiteScore settings dataclass does not read them directly.

No production provider factory/config schema exists. The document must record, without inventing values, that ACS API credential, Valhalla endpoint/binding, Overture artifacts, GTFS artifacts, benchmark artifacts and artifact-store configuration require a future deployment adapter/config contract. They must not be falsely marked configured in 7.0.

## 6.2 Existing Commerce names

```text
COMMERCE_ENV
SITESCORE_COMMERCE_DATABASE_URL
STRIPE_SECRET_KEY
STRIPE_PRICE_LOCATION_REPORT_V1
STRIPE_API_VERSION
STRIPE_WEBHOOK_SECRET
STRIPE_EXPECTED_LIVEMODE
COMMERCE_SUCCESS_URL_BASE
COMMERCE_CANCEL_URL_BASE
SITESCORE_API_BASE_URL
SITESCORE_API_SERVICE_KEY
SITESCORE_API_TARGET_ID
SITESCORE_API_TIMEOUT_SECONDS
COMMERCE_AUTOMATION_API_KEY
POSTMARK_SERVER_TOKEN
POSTMARK_FROM_EMAIL
POSTMARK_TEMPLATE_ALIAS
POSTMARK_TIMEOUT_SECONDS
COMMERCE_PUBLIC_BASE_URL
COMMERCE_N8N_ORDER_PAID_WEBHOOK_URL
COMMERCE_N8N_INGRESS_SECRET
COMMERCE_N8N_TIMEOUT_SECONDS
```

The two bearer secrets must remain distinct:

```text
COMMERCE_N8N_INGRESS_SECRET != COMMERCE_AUTOMATION_API_KEY
```

## 6.3 Existing n8n names

```text
N8N_ENCRYPTION_KEY
N8N_HOST
N8N_PORT
N8N_PROTOCOL
N8N_WEBHOOK_URL
N8N_USE_WORKFLOW_PUBLICATION_SERVICE
N8N_DIAGNOSTICS_ENABLED
N8N_VERSION_NOTIFICATIONS_ENABLED
N8N_PERSONALIZATION_ENABLED
N8N_BLOCK_ENV_ACCESS_IN_NODE
EXECUTIONS_DATA_SAVE_ON_ERROR
EXECUTIONS_DATA_SAVE_ON_SUCCESS
COMMERCE_N8N_INGRESS_SECRET
COMMERCE_AUTOMATION_API_KEY
SITESCORE_COMMERCE_AUTOMATION_BASE_URL
SITESCORE_N8N_POLL_SECONDS
SITESCORE_N8N_MAX_POLLS
```

The current workflow deliberately needs environment access; `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` must be treated as a narrow workflow requirement and a security risk to constrain, not a general license for Code/Function authority.

## 6.4 n8n managed-PostgreSQL target names

Document as `future-7.1`, based on official n8n PostgreSQL configuration names:

```text
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST
DB_POSTGRESDB_PORT
DB_POSTGRESDB_DATABASE
DB_POSTGRESDB_USER
DB_POSTGRESDB_PASSWORD
DB_POSTGRESDB_SCHEMA
DB_POSTGRESDB_SSL_ENABLED
DB_POSTGRESDB_SSL_CA or its supported file form when required
```

Exact TLS variable combination must be verified against n8n `2.33.4` during 7.1; 7.0 must not put certificates or credentials in Git.

## 6.5 Release/platform names reserved for 7.1

Record only names/schema, never values:

```text
DIGITALOCEAN_ACCESS_TOKEN or chosen narrowly scoped equivalent
DO_APP_ID_STAGING
DO_APP_ID_PRODUCTION
GHCR deployment credential identity, if App Platform cannot use an approved native connection
platform-injected PORT
```

No production resource ID, URL, account ID, database hostname, bucket name, token or credential value may be invented in 7.0.

---

# 7. VALKEY/CELERY COMPATIBILITY ENTRY GATE

DigitalOcean Managed Valkey requires TLS. Current `sitescore-api` validation accepts only a broker URL beginning `redis://`, and `build_celery()` contains no explicit broker SSL configuration. Therefore Managed Valkey compatibility is **unproven**, not assumed.

Checkpoint 7.0 must record this exact gap and the following 7.1 stop condition:

```text
Before any Managed Valkey staging deployment:
1. prove a TLS-authenticated connection using the exact pinned redis==7.4.1 / celery==5.6.3 runtime;
2. prove late ACK, reject-on-worker-lost, result-backend-disabled and redelivery behavior;
3. do not disable TLS certificate verification;
4. if the frozen settings/runtime must change, set CONTRACT_CHANGE_REQUIRED=1 and stop for Reviewer/user authority;
5. do not fall back to an internet-exposed or plaintext managed broker.
```

This unresolved 7.1 entry gate does not block documentation-only 7.0, but it forbids 7.1 deployment claims until resolved.

---

# 8. DATABASE, MIGRATION AND STORAGE CONTRACT

The operations handoff must state:

- PostgreSQL is durable truth; Valkey/Celery and n8n transport are not product truth.
- One managed PostgreSQL cluster is allowed initially only with three separate logical databases and three least-privilege users.
- API credentials cannot access Commerce or n8n databases; Commerce credentials cannot access API or n8n databases; n8n credentials cannot access API or Commerce databases.
- TLS/private hostname/trusted-source controls are mandatory.
- API Alembic head is `0003_faz5_5_canonical_success_boundary`.
- Commerce Alembic head is `0005_recovery_reconciliation`.
- API and Commerce migrations are separate controlled single-authority jobs.
- replicas never race migrations on startup.
- n8n owns its own schema migrations only in the n8n database.
- report object bucket is private; public listing and public object ACL are forbidden.
- Spaces versioning/lifecycle design is deferred to 7.5 but the target and current absence must be recorded.
- `storage_key`, bucket, credentials and endpoint remain non-customer data.

---

# 9. THREAT AND COST BOUNDARIES

`THREAT_AND_COST_BOUNDARIES.md` must include at least these trust boundaries and mitigations/phase owners:

| Threat/cost boundary | Required 7.0 statement |
|---|---|
| Public order creation | Untrusted intent; no money/score authority; abuse and budget controls belong to 7.3. |
| Stripe webhook | Signature + fresh provider verification remain payment authority; edge controls must preserve legitimate retries. |
| Public download token | Capability is random, digest-only at rest, expiry/revocation checked; logs must redact raw token. |
| Commerce automation routes | Existing bearer auth plus private ingress; never expose as unauthenticated operator API. |
| n8n webhook | Narrow ingress secret; event is transport trigger, not payment truth. |
| n8n editor/admin | No public route; no broad provider/DB credentials. |
| SiteScore API | Internal scoped service key; IDs/hashes are not authority. |
| PostgreSQL | Cross-database least privilege; authoritative lifecycle/payment/report state. |
| Valkey | Volatile Celery transport only; no durable business truth. |
| Spaces | Private object store; customer receives proxied verified bytes only. |
| OpenAI | Optional narrator-selection provider only; fallback exists; no scoring/decision authority. |
| Provider APIs/artifacts | Timeouts/retries/budget telemetry required later; absence never becomes zero/success. |
| GitHub Actions/GHCR | Minimum permissions, immutable digest, provenance/SBOM/scans beginning 7.1. |
| Logs/telemetry | No secrets, raw delivery tokens, Authorization values, DB URLs or sensitive provider payloads. |
| Budget stop | May stop new admission/sales only; never strands already-paid orders outside fulfillment/refund convergence. |

Do not invent legal compliance certification. List retained data classes and mark legal retention periods as policy/legal decisions when not technically frozen.

---

# 10. SLO, RECOVERY AND OPERATIONAL TARGETS TO RECORD

Record these initial targets as targets, not achieved evidence:

```text
public Commerce/API availability: 99.5% monthly
paid-order fulfillment success excluding canonical not_score_ready: >=99%
no lost paid order from orchestration crash: 100% invariant
no duplicate money movement from retries: 100% invariant
no unauthorized report disclosure: 100% invariant
RPO target: <=1 hour for transactional DB truth where provider PITR supports it
RTO target: <=4 hours for core paid-order processing
```

Also inventory required future alert classes from the master plan: webhook verification/reconciliation failures, stuck paid orders, queue backlog, worker absence, provider failures, DB/Valkey pressure, n8n failures, refund delay, Postmark uncertainty, recovery findings, backup/restore failures and budget thresholds.

Checkpoint 7.0 must mark telemetry, alert implementation and measured thresholds as not yet implemented; those belong to 7.2+.

---

# 11. ALLOWED SCOPE

Allowed:

- derive factual operations documentation from exact live source;
- create the five required documents;
- create pure verification tooling/tests for the 7.0 document contract;
- record official primary-source platform references;
- record current gaps and later checkpoint entry gates;
- create one branch and one PR from the exact base;
- use a temporary read-only validation workflow under the closed path above.

---

# 12. OUT OF SCOPE / FORBIDDEN

Do not:

- modify any existing `sitescore-*` source, tests, manifests, migrations, README or frozen docs;
- modify n8n runtime/workflow bytes;
- change the seven Commerce routes or five V1 API routes;
- add health/admin/debug endpoints;
- add Dockerfiles, App Platform specs, OpenTofu/Terraform or permanent GitHub Actions in 7.0;
- provision DigitalOcean, Stripe, Postmark, OpenAI, GitHub or DNS resources;
- create, rotate or commit real secrets;
- activate n8n workflows;
- create DBs, buckets, registry images or deployments;
- update dependencies;
- implement observability, rate limiting, cost gates, resilience, backups or load tests yet;
- approve COMB-005, empirical calibration or any FAZ 8 work;
- claim production/staging readiness;
- merge without literal user `LOCK` after Reviewer READY_TO_LOCK.

Any frozen-package change requires:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

Any proven DigitalOcean topology incompatibility requires:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

Any need to reopen a locked checkpoint requires:

```text
ADDITIONAL_REOPEN_REQUIRED: 1
```

Stop and report; do not silently work around it.

---

# 13. VERIFICATION TOOLING CONTRACT

`ops/production/verify_checkpoint_7_0.py` must use the Python standard library only and provide a nonzero exit on mismatch. It must verify at least:

- required 7.0 files exist;
- each required document embeds the exact baseline SHA and clearly separates current from target state;
- operations handoff contains all runtime processes, routes, migrations, environment names, frozen identities and known gaps above;
- topology contains public/private boundaries and no public n8n/API/DB/Valkey/Spaces object exposure;
- secrets contract contains names/placeholders only and no value shaped like a credential;
- threat/cost document protects Stripe retries and paid-order convergence;
- no document claims staging/production deployment exists;
- `sitescore-api` and `sitescore-commerce` package versions/migration heads remain unchanged;
- Commerce exact-seven route freeze remains represented;
- n8n version and both workflow hashes in documentation equal the frozen records;
- current base contains no Dockerfile, permanent workflow or IaC **as a historical recorded finding**, without installing a future-facing permanent assertion that would break legitimate 7.1 additions;
- changed-file allowlist is exact when supplied base/head SHAs are available.

The verifier must not read secrets or call external providers/cloud APIs.

`ops/production/tests/test_checkpoint_7_0.py` must adversarially prove the verifier rejects at least:

- wrong base SHA;
- missing runtime process;
- missing configuration name;
- public n8n editor claim;
- public report bucket claim;
- mutable `latest` image authority;
- naive Stripe/global rate-limit language;
- paid orders abandoned by a budget stop;
- production-deployed overclaim;
- secret-looking committed placeholder/value;
- changed-file allowlist violation.

Do not make tests depend on network access or real secrets.

---

# 14. REQUIRED VALIDATION EVIDENCE

Before `READY_FOR_REVIEW`, provide:

```text
1. exact base SHA proof
2. exact branch and PR
3. git diff --name-status <base>...HEAD
4. changed-file allowlist PASS
5. python ops/production/verify_checkpoint_7_0.py ... PASS
6. pytest for ops/production/tests PASS with count
7. sitescore-commerce full suite: expected 417 PASS
8. frozen FAZ 3/4/5 suite: expected 1504 PASS
9. n8n static suite: expected 12 PASS
10. secret scan over changed files: PASS
11. no Dockerfile/IaC/permanent workflow/runtime source change: PASS
12. Markdown link/path validation: PASS
13. temporary CI run/job IDs and conclusion if CI was used
14. exact final head SHA
15. all final file SHA-256 values
```

If environment limitations prevent a historical suite from running, do not substitute a false PASS. Record exact command, failure class and why the documentation-only diff remains reviewable; Reviewer decides whether it is blocking.

---

# 15. ACCEPTANCE CRITERIA

Checkpoint 7.0 is reviewable only when all are true:

- branch starts exactly from `ee45e4fdd3d805137387a0fc1198eedf8d461fb2`;
- one PR targets `main`;
- permanent diff is confined to the allowlist;
- `PRODUCTION_OPERATIONS_HANDOFF.md` is complete and live-derived;
- current/target state distinction is explicit throughout;
- no configuration value or resource identity is invented;
- all existing environment names and current process/route/migration facts are present;
- production provider-factory/config absence is explicit;
- Valkey TLS compatibility remains an explicit 7.1 gate;
- public/private ingress model protects automation routes and n8n editor;
- Commerce exact-seven and API frozen V1 semantics are unchanged;
- TCP health strategy avoids route mutation;
- paid-outbox worker direction respects App Platform cron minimum and preserves durable identity;
- PostgreSQL least privilege, migration authority and n8n DB separation are explicit;
- Spaces remains private and customer delivery remains proxied/verified;
- threat/cost model preserves legitimate Stripe retries and already-paid convergence;
- SLO/RPO/RTO are labelled targets, not achieved results;
- verifier and adversarial tests pass;
- no FAZ 7.1 implementation or cloud mutation occurred;
- Implementer handoff matches GitHub reality.

---

# 16. IMPLEMENTER HANDOFF REQUIREMENTS

When complete, update only `implementer.md` on the coordination branch with:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.0
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: WAIT_FOR_REVIEW
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_SHA: ee45e4fdd3d805137387a0fc1198eedf8d461fb2
CODE_BRANCH: faz7/7-0-production-operational-baseline
PR: #N
HEAD_SHA: <exact>
CHANGED_FILES: <exact list>
VALIDATION: <exact commands/counts/results>
BLOCKERS: NONE or exact blocker IDs
CONTRACT_CHANGE_REQUIRED: 0|1
DESIGN_DECISION_REVIEW_REQUIRED: 0|1
ADDITIONAL_REOPEN_REQUIRED: 0|1
```

Include:

- detailed work summary by file;
- live-derived current inventory;
- every recorded operational gap;
- platform-source references used;
- validation SHA/run evidence;
- file SHA-256 list;
- confirmation that no secret/cloud resource/deployment/runtime mutation occurred.

Do not request or infer LOCK. Stop after `READY_FOR_REVIEW`.

---

# 17. REVIEWER SOURCE REFERENCES FOR PLATFORM FACTS

Use current official primary documentation and preserve retrieval date in the checkpoint record:

- DigitalOcean App Spec reference: https://docs.digitalocean.com/products/app-platform/reference/app-spec/
- App Platform internal services: https://docs.digitalocean.com/products/app-platform/how-to/manage-services/
- App Platform jobs/cron: https://docs.digitalocean.com/products/app-platform/how-to/manage-jobs/
- App Platform health checks: https://docs.digitalocean.com/products/app-platform/how-to/manage-health-checks/
- App Platform container images/GHCR: https://docs.digitalocean.com/products/app-platform/how-to/deploy-from-container-images/
- App Platform VPC: https://docs.digitalocean.com/products/app-platform/how-to/enable-vpc/
- Managed PostgreSQL security/connectivity: https://docs.digitalocean.com/products/databases/postgresql/how-to/secure/ and https://docs.digitalocean.com/products/databases/postgresql/how-to/connect/
- Managed Valkey security/connectivity: https://docs.digitalocean.com/products/databases/valkey/how-to/secure/ and https://docs.digitalocean.com/products/databases/valkey/how-to/connect/
- Spaces compatibility/versioning/private access: https://docs.digitalocean.com/products/spaces/reference/s3-compatibility/ and https://docs.digitalocean.com/products/spaces/how-to/
- n8n PostgreSQL configuration: https://docs.n8n.io/deploy/host-n8n/configure-n8n/choose-n8ns-database and https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/database

If a current official source contradicts this contract, set the appropriate review-required flag and stop rather than choosing prose over live evidence.

---

# 18. STOP CONDITION

Implement only Checkpoint 7.0 on the exact branch/base above. Do not start 7.1. Do not merge. Do not self-LOCK.

Reviewer will perform exact-head, full-diff, full-file and evidence review only after Implementer records `READY_FOR_REVIEW` and the user sends the next literal `Devam`.
