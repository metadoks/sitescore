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
REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN_SAME_PR
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 3762ec643426e310ff82bdb00b20f58fb4ae9e09
EXPECTED_BASE_TREE_SHA: 3cc9fe7c0f8da20a4c2763661a4df304c96c94ce
CODE_BRANCH: faz7/7-0-production-operational-baseline
PR: #33
REVIEWED_HEAD_SHA: 0a86c97142a5bf85c2196d7038b611e7fcef107c

PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE_AT_REVIEW: TRUE
LIVE_MAIN_SHA: 3762ec643426e310ff82bdb00b20f58fb4ae9e09
LIVE_MAIN_UNCHANGED_FROM_BASE: YES
PERMANENT_CHANGED_FILES: 2
SOURCE_PACKAGE_TREE_DIFF: NONE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO

BLOCKERS:
  OPS70-H002: OPEN
  OPS70-H003: OPEN
  OPS70-H004: OPEN
```

---

# 1. REVIEW SCOPE / EXACT STATE

Reviewer independently audited PR #33 against the FAZ 7.0 contract at exact head:

```text
0a86c97142a5bf85c2196d7038b611e7fcef107c
```

Live GitHub state at review:

```text
base branch = main
base SHA = 3762ec643426e310ff82bdb00b20f58fb4ae9e09
head branch = faz7/7-0-production-operational-baseline
head SHA = 0a86c97142a5bf85c2196d7038b611e7fcef107c
PR #33 = OPEN / NON-DRAFT / MERGEABLE / UNMERGED
live main = 3762ec643426e310ff82bdb00b20f58fb4ae9e09
```

Base-to-head compare is clean and contains exactly:

```text
docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md   +722
docs/PRODUCTION_OPERATIONS_HANDOFF.md      +633
```

No SiteScore source package, Commerce source, n8n workflow/runtime, dependency, migration, Docker, OpenTofu, cloud resource, scoring, financial, report, payment, or orchestration semantic file is changed.

The scope boundary is therefore PASS.

---

# 2. ACCEPTED PARTS OF THE IMPLEMENTATION

The current documents correctly preserve or record all of the following and these areas do not need redesign:

```text
selected FAZ 7 platform remains unchanged
Mathematically validated scoring engine; empirical validation pending
COMB-005 remains NOT_APPROVED / unresolved
Stripe / Commerce PG / SiteScore API / Valkey-Celery / n8n / Postmark / Spaces authority split
commerce-dispatcher remains one-shot
future dispatcher loop is deployment-owned and business-authority-free
Celery broker is rediss:// in production
Celery result backend remains none
worker ack/prefetch/time-limit semantics are preserved
api-worker staging initial concurrency = 1
api-beat exactly one intended scheduler instance
n8n 2.33.4 frozen lineage/digest/workflow hashes are retained
n8n PostgreSQL persistence is correctly identified as a later 7.2 target, not current deployed fact
api-web is internal-only
Commerce public candidates are only orders / Stripe webhook / opaque download
Commerce automation routes are internal-only
n8n editor/admin/general REST remain non-public
current repository has no canonical production Docker/OpenTofu/App Platform deployment proof
main protection remains false and is deferred to 7.1
no cloud deployment/resource mutation is claimed
```

The validation run `32485920900` at validated head
`1cdc2463292265b87bceb09add7c27095a7c175f` is real and completed SUCCESS. Reviewer also verified that validated-head -> final-head changes only remove the temporary validation workflow, so permanent document bytes at that validation point and final reviewed head are identical.

However, the current validation workflow did not satisfy every acceptance item in the Reviewer contract, and the documents omit several mandatory contract fields. These are hardening blockers, not redesign blockers.

---

# 3. OPS70-H002 — RUNTIME CONTRACT REQUIRED FIELDS INCOMPLETE

```text
OPS70-H002: OPEN
SEVERITY: LOCK BLOCKER
FILE: docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md
```

## 3.1 Staging / production separation matrix schema is incomplete

The issued Reviewer contract required the runtime separation matrix to contain columns equivalent to:

```text
staging identity
production identity
may share? yes/no
reason
secret? yes/no
creation checkpoint
```

and at minimum the required resource rows including:

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

The current runtime-contract matrix has only:

```text
Resource / authority
Staging
Production
Sharing rule
```

It therefore omits the mandatory explicit fields:

```text
reason
secret? yes/no
creation checkpoint
```

and it does not include the required `backup targets` row.

### Required hardening

Expand the existing matrix; do not create a second contradictory matrix.

For every row provide explicit:

```text
staging identity/target
production identity/target
may share? YES/NO
reason
secret? YES/NO
creation/implementation checkpoint
```

Use later checkpoint ownership consistently:

```text
7.1 containers/supply-chain/GitHub governance
7.2 IaC/staging/networking/secrets and resource creation
7.3 observability/Better Stack/SLO
7.4 traffic/provider-cost controls
7.5 capacity/release safety
7.6 backup/restore/data protection/DR
7.7 staging E2E/load/failure drills
```

Do not imply a resource already exists when it is only a target.

## 3.2 Managed PostgreSQL contract is missing mandatory transport/network/PITR clauses

The Reviewer contract required the per-environment PostgreSQL contract to state explicitly:

```text
separate least-privilege users
TLS
private/VPC path where platform supports
trusted sources
PITR enabled later when infrastructure is created
connection budgets reserved for 7.5 capacity proof
```

The current document records isolated logical DBs/users and migration ownership, but does not explicitly freeze all of:

```text
TLS requirement
private/VPC path requirement
trusted-source restriction
PITR target when infrastructure is created
```

### Required hardening

Add these as normative PostgreSQL requirements. Keep actual deployment/proof deferred to 7.2 and PITR/restore evidence to 7.6 as appropriate. Do not claim they are already deployed.

## 3.3 Spaces contract must explicitly bind region + endpoint

The Reviewer contract required per-environment Spaces configuration to include:

```text
explicit region + endpoint
```

The current document describes the adapter as configurable and defers exact endpoint/credentials to 7.2, but the normative Spaces requirement list itself omits the explicit region+endpoint requirement.

### Required hardening

Add a normative statement that each environment's Spaces configuration must explicitly bind the intended bucket, region and HTTPS endpoint; exact values remain 7.2 IaC/secrets configuration and must not contain secret material in documentation.

---

# 4. OPS70-H003 — ENVIRONMENT INVENTORY TRACEABILITY SCHEMA INCOMPLETE

```text
OPS70-H003: OPEN
SEVERITY: LOCK BLOCKER
FILE: docs/PRODUCTION_OPERATIONS_HANDOFF.md
```

The Reviewer contract explicitly required every production-relevant environment-variable inventory row to expose these fields:

```text
name
consumer component
source file
required/optional/defaulted
secret? yes/no
staging/prod sharing rule
rotation impact
notes/validation constraints
```

The current handoff is substantively strong, but several tables rely on section-level prose such as `Direct source: ...` instead of carrying the required per-row `source file` field, and some tables omit an explicit `consumer component` or `rotation impact` column.

Examples:

```text
5.1 API table: no per-row source-file column
5.3 narrative table: no per-row source-file column
5.4 Commerce table: no consumer-component or source-file column
5.5 dispatcher table: no consumer-component/source-file/rotation-impact columns
5.6 n8n table: no consumer-component/source-file/rotation-impact columns
```

This matters because this document is the operational handoff that later IaC/secrets work will consume; source traceability must remain row-local and unambiguous.

### Required hardening

Normalize the environment inventory so every variable row, including SDK-level credential rows where documented, has explicit columns equivalent to:

```text
Variable
Consumer
Source
Required/default
Secret?
Staging/prod sharing
Rotation/operational impact
Constraints/notes
```

It is acceptable for multiple rows to repeat the same source path. Do not reduce existing detail to shorten the table.

For SDK/provider-chain values not directly read by SiteScore source, mark the source accurately, e.g.:

```text
Source = boto3 credential provider chain / SDK-level, not direct SiteScore os.getenv
Source = OpenAI SDK credential provider / SDK-level, not direct SiteScore os.getenv
```

Do not invent provider environment-variable names that current source does not bind.

---

# 5. OPS70-H004 — REQUIRED 9-PASS BROKER-TLS TEST RUN WAS NOT EXECUTED

```text
OPS70-H004: OPEN
SEVERITY: LOCK BLOCKER
EVIDENCE: validation run 32485920900 / job 96782267264
```

The Reviewer contract required:

```text
run the focused broker-TLS tests from the new base/branch
expected unchanged result = 9 PASS
```

Reviewer independently inspected the successful validation job log.

The job did **not** run pytest for:

```text
sitescore-api/tests/test_broker_tls_compatibility.py
```

Instead it performed static source checks such as:

```text
assert '("redis://", "rediss://")' in settings
assert 'Celery("sitescore_api", broker=settings.broker_url, backend=None)' in celery
assert 'rediss://' in tests
print('BROKER_TLS_SOURCE_PROOF=PASS')
```

That static proof is useful but does not satisfy the explicitly required executable regression gate.

### Required hardening

After documentation hardening is complete, run the actual focused tests from the same PR branch/head lineage and record exact output:

```text
sitescore-api/tests/test_broker_tls_compatibility.py
EXPECTED: 9 passed
```

Use the package's pinned/test-compatible environment. The exact command may vary with working directory, but the report must include the command and exact pass count.

If a temporary validation workflow is used:

```text
1. update both docs first
2. run validation on that exact document revision
3. include actual focused pytest = 9 PASS
4. remove only the temporary validation workflow
5. prove validated-head -> final-head diff is only temporary workflow removal
```

Permanent PR scope after cleanup must remain exactly the two authorized docs.

Do not change the broker corrective source/test file merely to satisfy this gate.

---

# 6. HARDENING SCOPE

Continue on the same branch and PR:

```text
branch = faz7/7-0-production-operational-baseline
PR = #33
base = 3762ec643426e310ff82bdb00b20f58fb4ae9e09
```

Permanent hardening changes remain limited to:

```text
docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md
docs/PRODUCTION_OPERATIONS_HANDOFF.md
```

A temporary GitHub Actions validation workflow is allowed only as ephemeral evidence and must be removed before final handoff.

Still forbidden:

```text
application source changes
package/dependency changes
migration changes/execution
Commerce/n8n semantic changes
Docker/OpenTofu implementation
cloud resource creation/deployment
branch protection mutation
scoring/financial/report/payment authority changes
FAZ 7.1 implementation
```

---

# 7. REQUIRED RE-VALIDATION

Before returning `READY_FOR_REVIEW`, Implementer must provide exact evidence for the new final head:

```text
A. PR #33 remains open/non-draft/unmerged
B. live main remains the expected base or any movement is explicitly reconciled
C. git diff --check PASS
D. permanent changed files = exactly the two authorized docs
E. source/package/n8n diff = NONE
F. package inventory proof PASS
G. actual focused broker-TLS pytest = 9 PASS
H. Celery static source/binding proof PASS
I. n8n 2.33.4 + frozen image/workflow identities PASS
J. dispatcher one-shot proof PASS
K. separation matrix contains all required columns and rows
L. PostgreSQL contract explicitly contains TLS/private-VPC/trusted-source/PITR target clauses
M. Spaces contract explicitly requires bucket + region + endpoint binding
N. env inventory rows expose Consumer + Source + Required/default + Secret + Sharing + Rotation + Constraints
O. no secret values introduced
P. no cloud/resource/governance mutation performed
```

If validation uses a temporary workflow, prove again that validated -> final head changes only remove that workflow and do not alter permanent document bytes.

---

# 8. BLOCKER DISPOSITION

Current disposition:

```text
OPS70-H001: CLOSED  # rediss corrective
OPS70-H002: OPEN    # runtime-contract mandatory field completeness
OPS70-H003: OPEN    # env inventory row-level traceability schema
OPS70-H004: OPEN    # required executable broker-TLS 9-PASS gate absent
```

No contract reopen is required. These are same-checkpoint hardening items.

```text
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
```

---

# 9. IMPLEMENTER STOP FORMAT AFTER HARDENING

After all three blockers are addressed, update `implementer.md` and stop with:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.0
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO
BASE_SHA: 3762ec643426e310ff82bdb00b20f58fb4ae9e09
BRANCH: faz7/7-0-production-operational-baseline
PR: #33
HEAD_SHA: <new exact final SHA>
OPS70-H002: RESOLUTION_REPORTED
OPS70-H003: RESOLUTION_REPORTED
OPS70-H004: RESOLUTION_REPORTED
FOCUSED_BROKER_TLS_TESTS: 9 PASS
PERMANENT_CHANGED_FILES: 2
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Do not merge. Do not start 7.1.

Reviewer will independently re-audit the new exact PR head and issue either:

```text
HARDENING_REQUIRED
```

or:

```text
READY_TO_LOCK
```

Only literal user `LOCK` after exact-SHA `READY_TO_LOCK` authorizes merge.
