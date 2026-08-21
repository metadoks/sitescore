# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.0 ENTRY CORRECTIVE
CHECKPOINT_TITLE: Managed Valkey TLS / rediss:// Transport Compatibility Corrective
REVIEWER_STATE: CONTRACT_CHANGE_REQUIRED
IMPLEMENTER_ACTION: IMPLEMENT_CORRECTIVE
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: ee45e4fdd3d805137387a0fc1198eedf8d461fb2
EXPECTED_BASE_TREE_SHA: 5660f97ad59a8d48419d29e57ee0fc3e2d140e24
CORRECTIVE_BRANCH: faz7/corrective-broker-tls-rediss
PR: TBD
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_VERIFIED: YES
FAZ6_FINAL_PR: #31
FAZ6_FINAL_PR_STATE: CLOSED_MERGED
FAZ6_FINAL_REVIEWED_HEAD: 9856619a98fca93f14027347e26f04a13e18163c
FAZ6_FINAL_MERGE_COMMIT: ee45e4fdd3d805137387a0fc1198eedf8d461fb2
FAZ6_FINAL_MERGE_PARENT_1: df4e3181712e7f426f8f1752628952a620c98f05
FAZ6_FINAL_MERGE_PARENT_2: 9856619a98fca93f14027347e26f04a13e18163c
FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: FROZEN
FAZ_6_FINAL_STATUS: LOCKED

NORMAL_7_0_BRANCH: faz7/7-0-production-operational-baseline
NORMAL_7_0_BRANCH_VS_MAIN: IDENTICAL
NORMAL_7_0_OPEN_PR: NONE
NORMAL_7_0_AUTHORIZED: NO
NORMAL_7_0_PREVIOUS_CONTRACT: SUPERSEDED_PENDING_CORRECTIVE_LOCK

BROKER_TLS_GATE: FAILED
DIGITALOCEAN_MANAGED_VALKEY_TLS_REQUIRED: YES
CURRENT_API_REDISS_SUPPORT: NO
PRODUCTION_BROKER_TARGET: rediss://
BLOCKER_ID: OPS70-H001

CONTRACT_CHANGE_REQUIRED: 1
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
```

---

# 1. REVIEWER DECISION

Normal FAZ 7.0 work is blocked before implementation.

The live `main` source at exact SHA
`ee45e4fdd3d805137387a0fc1198eedf8d461fb2` contains this production API validation in:

```text
sitescore-api/src/sitescore_api/settings.py
```

Canonical current behavior:

```python
if not self.broker_url.startswith("redis://"):
    raise ValueError("broker_url must use Redis")
```

Therefore a secure broker URL beginning with:

```text
rediss://
```

is rejected. The exact predicate is false for `rediss://...` and therefore this is a real transport-compatibility defect, not an IaC/documentation gap.

DigitalOcean Managed Valkey documentation was reverified on 2026-08-21. DigitalOcean states that Managed Valkey traffic is encrypted in transit and that clients are required to connect using SSL/TLS. The connection guide explicitly requires TLS for Managed Valkey connections.

The selected FAZ 7 platform contract requires encrypted Managed Valkey transport. We must not weaken or bypass that platform requirement merely to satisfy a frozen validator.

Result:

```text
OPS70-H001: OPEN
CONTRACT_CHANGE_REQUIRED: 1
NORMAL_FA7_0_IMPLEMENTATION: BLOCKED
```

This corrective must be LOCKED by the user before normal FAZ 7.0 resumes.

---

# 2. WHY THE PREVIOUS NORMAL 7.0 CONTRACT IS SUPERSEDED

The prior coordination contract recorded:

```text
VALKEY_TLS_COMPATIBILITY: UNPROVEN_7_1_ENTRY_GATE
```

That is not acceptable under the FAZ 7 master authority. Broker TLS compatibility is an explicit **7.0 entry gate**, and an incompatibility must stop normal checkpoint flow immediately.

Live verification now resolves that gate:

```text
VALKEY_TLS_COMPATIBILITY: FAILED
```

The existing branch:

```text
faz7/7-0-production-operational-baseline
```

is currently identical to `main` and has no PR. Do not implement the normal 7.0 documentation/topology contract on it yet.

After this corrective is reviewed, user-LOCKed, merged, and post-lock verified, Reviewer will issue a fresh normal 7.0 contract against the new exact `main` SHA.

---

# 3. CORRECTIVE PURPOSE

Add only the minimum secure Redis/Valkey broker URL scheme compatibility required for the selected production transport:

```text
redis://   -> remains supported for existing local/test compatibility
rediss://  -> must become supported for encrypted production broker transport
other schemes -> remain rejected
```

This corrective changes **transport compatibility only**.

It must not create new business, scoring, payment, report, orchestration, deployment, or infrastructure authority.

---

# 4. ALLOWED IMPLEMENTATION SCOPE

Permanent source changes are limited to:

```text
sitescore-api/src/sitescore_api/settings.py
```

and the minimum API test file(s) required to prove the corrective. Preferred narrow test location:

```text
sitescore-api/tests/test_broker_tls_compatibility.py
```

If the Implementer can prove an existing settings-focused test file is a materially cleaner home, that existing test file may be used instead. Do not touch unrelated tests merely to satisfy counts.

No package dependency change is authorized.
No package-version bump is authorized in this corrective.
No schema migration is authorized.
No route change is authorized.
No runtime topology/IaC/Docker change is authorized.
No cloud resource creation is authorized.
No GitHub governance change is authorized here.
No n8n/Commerce change is authorized.

Any permanent change outside the allowed source + minimal tests is a scope blocker unless Reviewer explicitly reopens the contract first.

---

# 5. REQUIRED SOURCE SEMANTICS

The corrected `Settings` validation must satisfy all of the following:

1. A non-empty `redis://...` broker URL continues to pass the existing Redis-family scheme gate.
2. A non-empty `rediss://...` broker URL passes the scheme gate.
3. Unsupported schemes such as `http://`, `https://`, `amqp://`, or arbitrary text remain rejected.
4. The corrective must not rewrite `rediss://` to `redis://`.
5. The corrective must not disable TLS verification or introduce an insecure TLS flag.
6. The corrective must not special-case DigitalOcean hostnames; scheme support must remain provider-neutral Redis/Valkey transport compatibility.
7. Existing required-setting checks remain intact.
8. Existing PostgreSQL validation remains intact.
9. Existing API-key-pepper minimum-length validation remains intact.
10. Existing worker/report/time-limit validation remains intact.

Prefer the smallest explicit validation change. Do not introduce a new URL-parsing dependency for this two-scheme compatibility problem unless a real correctness requirement proves it necessary.

---

# 6. CELERY BINDING MUST REMAIN EXACT

Live source currently constructs Celery as:

```python
Celery("sitescore_api", broker=settings.broker_url, backend=None)
```

The corrective must preserve this authority boundary.

Required proof:

```text
Settings(rediss://...) accepts the secure URL
-> build_celery(settings)
-> Celery broker configuration retains rediss:// transport
```

Do not add a second broker URL, hidden fallback, URL rewrite, or environment-specific downgrade.

The following frozen Celery semantics must remain unchanged:

```text
task_ignore_result = true
task_store_errors_even_if_ignored = false
task_acks_late = true
task_acks_on_failure_or_timeout = true
task_reject_on_worker_lost = true
worker_prefetch_multiplier = 1
soft time limit = existing Settings value
hard time limit = existing Settings value
beat drain_outbox = every 10 seconds
beat reconcile_timeouts = every 15 seconds
```

---

# 7. REQUIRED CORRECTIVE TESTS

Add focused deterministic tests proving at minimum:

```text
TEST-TLS-001  redis:// remains accepted
TEST-TLS-002  rediss:// is accepted
TEST-TLS-003  Settings.from_env accepts SITESCORE_BROKER_URL=rediss://...
TEST-TLS-004  unsupported non-Redis schemes remain rejected
TEST-TLS-005  build_celery preserves rediss:// broker transport without rewrite
```

Use fake local credential/host strings only. No live DigitalOcean connection and no real secret is required for this corrective.

Tests must not weaken existing validation to make fixtures pass.

---

# 8. REQUIRED REGRESSION EVIDENCE

Before `READY_FOR_REVIEW`, Implementer must run and record exact commands, exact pass counts and exact corrective HEAD SHA for:

```text
A. focused broker-TLS corrective tests
B. complete sitescore-api test suite
C. frozen FAZ 3/4/5 regression scenarios (pre-corrective baseline: 1504 PASS)
D. sitescore-commerce suite (pre-corrective baseline: 417 PASS)
E. n8n static suite (baseline: 12 PASS)
F. combined pytest regression covering the prior 1921-PASS Commerce + frozen baseline plus the newly added corrective tests
```

The exact final count may increase because new corrective tests are added. The requirement is:

```text
all prior tests remain passing
+ every new corrective test passes
+ zero skipped/xfail substitutions introduced to hide a regression
```

If an existing test must be changed because it explicitly asserted `rediss://` rejection, report that test and justify the semantic change. Do not broadly rewrite test expectations.

---

# 9. REQUIRED DIFF/FREEZE PROOFS

Implementer report must prove:

```text
base = ee45e4fdd3d805137387a0fc1198eedf8d461fb2
branch = faz7/corrective-broker-tls-rediss
PR = <number>
head = <exact SHA>
```

and include:

```text
git diff --name-only <base>...<head>
git diff --stat <base>...<head>
```

Expected permanent diff is only:

```text
sitescore-api/src/sitescore_api/settings.py
sitescore-api/tests/<minimum corrective test file(s)>
```

Reviewer will reject:

```text
scoring/math changes
COMB-005 changes
financial model changes
application/report authority changes
Commerce/payment changes
n8n changes
Docker/IaC/deployment changes
production cloud changes
secret files
lockfile/dependency churn
unrelated formatting/refactor churn
```

---

# 10. SECURITY ACCEPTANCE GATE

The corrective is acceptable only if Reviewer can independently prove from the exact PR HEAD:

```text
1. rediss:// is accepted by API Settings.
2. rediss:// reaches Celery unchanged.
3. redis:// local/test compatibility remains intact.
4. unsupported schemes remain rejected.
5. no TLS downgrade or verification-disable behavior was introduced.
6. no real credential/secret was committed.
7. no frozen analytical/business authority changed.
8. complete regression is green.
```

This corrective **does not by itself prove a live Managed Valkey connection**. Live staging connectivity belongs to the later infrastructure/staging checkpoints. It only removes the frozen API transport blocker so that a secure `rediss://` production contract is representable.

---

# 11. KNOWN NON-CORRECTIVE GAPS — DO NOT FIX HERE

The following remain real FAZ 7 work but are intentionally outside this corrective:

```text
main branch protection currently disabled
no production Dockerfiles
no permanent GitHub Actions supply-chain workflow
no OpenTofu/IaC
no App Platform production/staging spec
no production deployment
one-shot Commerce dispatcher needs deployment-owned supervision later
n8n production persistence/network isolation remains later work
production acquisition factory/provider env schema absent
public/private ingress proof absent
observability/alerts absent
backup/restore proof absent
load/failure drills absent
```

They will be handled by the normal FAZ 7 checkpoint sequence after this corrective is LOCKED.

---

# 12. IMPLEMENTER STOP FORMAT

When implementation is complete, update `implementer.md` with evidence and stop with:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.0 ENTRY CORRECTIVE
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO
BASE_SHA: ee45e4fdd3d805137387a0fc1198eedf8d461fb2
BRANCH: faz7/corrective-broker-tls-rediss
PR: #N
HEAD_SHA: <exact SHA>
CORRECTIVE_SCOPE: BROKER_TLS_REDISS_ONLY
CONTRACT_CHANGE_REQUIRED: 1
BLOCKER_TARGET: OPS70-H001
TESTS: <exact evidence>
```

Do not merge.
Do not mark the blocker resolved yourself.
Do not resume normal 7.0.

---

# 13. REVIEWER NEXT ACTION

After Implementer reports `READY_FOR_REVIEW`, Reviewer will independently inspect:

```text
PR metadata
exact base/head
all changed files
settings validation semantics
Celery transport binding
focused tests
full regression evidence
secret/scope leakage
```

Reviewer will then issue either:

```text
HARDENING_REQUIRED
```

or exact-SHA:

```text
READY_TO_LOCK
```

Only a literal user `LOCK` permits Implementer to merge the exact reviewed head.

After merge, Reviewer must verify merge parentage/tree and the corrected live `main`. Only then may normal FAZ 7.0 be re-authored and started.

---

# 14. FROZEN AUTHORITY REMINDERS

This corrective must preserve:

```text
COMB-005 approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition = UNRESOLVED
real production analysis may remain not_score_ready
Stripe = external processor evidence
Commerce PostgreSQL = durable commercial truth
SiteScore API = analysis/report truth
n8n = orchestration only
empirical validation = pending
PUBLIC_LAUNCH_AUTHORIZED = NO
START_FAZ8 = NO
```

No transport fix may fabricate scoring readiness or alter money/business truth.

---

# 15. REVIEWER DECLARATION

```text
OPS70-H001 is OPEN.
The current frozen API cannot represent the required TLS Managed Valkey broker URL.
The selected production broker must remain encrypted.
Normal FAZ 7.0 is blocked.
Only the narrow rediss:// transport compatibility corrective above is authorized.
User LOCK is required before the normal FAZ 7 flow can resume.
```
