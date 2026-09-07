# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
REVIEWER_STATE: MECHANICAL_REMEDIATION_AUTHORIZED_CONTINUE
IMPLEMENTER_ACTION: APPLY_CANONICAL_RESOLVED_PNPM_STORE_FIX_TO_PROBE_THEN_COMPLETE_7_1_TO_TERMINAL_STATE
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 6728f77b8b7519d90f35f83b97c94b2cd99e37d6
REVIEWED_HEAD_SHA: NONE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SNOWFLAKE_PRUNING_DESIGN_VALID_MECHANICAL_RESOLVED_STORE_FIX_NOT_YET_APPLIED_TO_PROBE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
```

---

## 1. Authority continuity

All prior FAZ 7.1 Reviewer decisions remain authoritative, including the n8n 2.37.10 deterministic unused-Snowflake capability-pruning authorization and the exact remediation boundary established in the previous Reviewer handoff.

The accepted capability boundary remains:

```text
NODES_EXCLUDE retains:
  n8n-nodes-base.executeCommand
  n8n-nodes-base.localFileTrigger
  n8n-nodes-base.emailSend
  n8n-nodes-base.snowflake

snowflake-sdk@2.1.0 may be removed only from graph-proven Snowflake-only production closure.
toml@3.0.0 may be removed only when snowflake-sdk@2.1.0 is its sole production parent.
shared non-Snowflake production dependencies must remain.
```

Still prohibited: frozen SiteScore application/business changes, frozen n8n workflow JSON changes, n8n/Snowflake application-source patching, incompatible toml major override, unadopted Snowflake parent upgrade, scanner suppression, SiteScore-authored VEX, arbitrary dependency upgrades, FAZ 7.2 cloud/IaC work, merge before READY_TO_LOCK + user LOCK, and FAZ 8 work.

---

## 2. Fresh live audit at head 6728f77

PR #34 is live as:

```text
state = OPEN
merged = FALSE
mergeable = TRUE
draft = TRUE
base = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
head = 6728f77b8b7519d90f35f83b97c94b2cd99e37d6
changed files = 22
```

Two temporary mechanics-only workflow paths are currently present:

```text
.github/workflows/faz7-7-1-n8n-snowflake-prune-probe.yml
.github/workflows/faz7-7-1-snowflake-path-patcher.yml
```

They are temporary and must not remain in terminal READY_FOR_REVIEW scope.

Exact-head permanent `faz7` run `34066622151` remains red while technical work is incomplete:

```text
source-boundary = PASS
static-contracts = PASS
faz6-commerce-replay = PASS
container-validation = FAIL_MECHANICAL_RUNTIME_PACKAGING_SMOKE
n8n-validation = FAIL_PRE_PERMANENTIZATION
required-gate = FAIL because mandatory upstream jobs are red
```

The API runtime dependency/package smoke failure is mechanical container packaging work and does not require Reviewer return.

---

## 3. Exact Snowflake resolved-store finding

The current Snowflake probe still contains the previously-rejected unresolved-path derivation:

```python
pnpm_root=(root/'.pnpm').resolve()
store_key=m.relative_to(root/'.pnpm').parts[0]
real_store=(root/'.pnpm'/store_key).resolve()
real_dir=m.parent.resolve()
```

Therefore the canonical resolved-store fix has NOT yet been applied to the actual probe at this head.

Commit `6728f77b8b7519d90f35f83b97c94b2cd99e37d6` adds a temporary helper workflow named `faz7-7-1-snowflake-path-patcher`. Its emitted replacement is directionally consistent with the Reviewer-authorized mechanical correction:

```python
real_dir=m.parent.resolve()
pnpm_root=(root/'.pnpm').resolve()
store_candidates=[p.resolve() for p in real_dir.parents if p.parent.resolve()==pnpm_root]
if len(store_candidates)!=1:
    fail_closed
real_store=store_candidates[0]
```

However adding a push-triggered helper in the same commit does not itself alter the existing probe, and the live exact head has no separate successful path-patcher run attached to it. The branch is therefore an intermediate mechanics state, not a new Reviewer blocker and not READY_FOR_REVIEW.

Canonical classification:

```text
ROOT_CAUSE: RESOLVED_PNPM_STORE_FIX_NOT_YET_MATERIALIZED_IN_PROBE
CLASSIFICATION: MECHANICAL_IMPLEMENTATION_STATE
NEW_DESIGN_DECISION_REQUIRED: NO
SNOWFLAKE_PRUNING_DESIGN_REOPENED: NO
```

---

## 4. Required Implementer continuation

Implementer must consume the already-authorized correction into the actual probe/permanent mechanics, then execute it and prove fail-closed deletion targets before pruning:

```text
resolved snowflake delete target = exactly snowflake-sdk@2.1.0 real pnpm store
resolved toml delete target = exactly toml@3.0.0 real pnpm store
snowflake target != n8n-nodes-base store
toml has no non-Snowflake production parent
expected delete-target set == actual delete-target set
```

Required after-prune inventory:

```text
n8n-nodes-base@2.37.4 = PRESENT
snowflake-sdk@2.1.0 = ABSENT
toml@3.0.0 = ABSENT
shared_non_snowflake_removed = []
no unrelated version change
```

If exact real-store pruning can be completed with those proofs, continue automatically through all remaining FAZ 7.1 mechanics. If it cannot be done without deleting shared parent/package state, only then return as a true design/security blocker.

Do not return to Reviewer for YAML, shell, quoting, path, Docker packaging, psycopg/runtime dependency, test-environment, artifact, or evidence mechanics.

---

## 5. Terminal technical target

Before the next Reviewer handoff, complete all of the following on one exact final head:

```text
latest official stable guard = PASS
n8n exact stable source/tree = PASS
Snowflake capability prune graph + final inventory = PASS
n8n version/linux-amd64/non-root/startup/loadability = PASS
frozen workflow hashes/imports = PASS
n8n static = PASS
order-paid webhook/auth/payload smoke = PASS
recovery schedule/API smoke = PASS
Snowflake node unavailable = PASS
CISA KEV = 0
CRITICAL = 0
OS HIGH = 0
fast-uri vulnerable findings = 0
ip-address vulnerable findings = 0
brace-expansion vulnerable findings = 0
toml vulnerable findings = 0
no new HIGH introduced
only previously-authorized nodemailer residual HIGH may remain if every containment proof passes
Commerce = 416 PASS + exactly one authorized phase-local deselect
FAZ6 Commerce replay = 417 PASS
API = 114 PASS
report = 24 PASS
API/Commerce/n8n runtime and non-root smokes = PASS
PDF/font smoke = PASS
permanent n8n hardening assets + n8n-image.lock = COMPLETE
SPDX/raw Grype/OpenVEX/KEV/provenance evidence = COMPLETE
source-boundary = PASS
static-contracts = PASS
container-validation = PASS
n8n-validation = PASS
faz7 / required-gate = PASS on exact final head
frozen application source diff = NONE
frozen n8n workflow JSON diff = NONE
cloud/IaC mutation = NONE
production secret commit = NONE
```

After successful absorption, remove both temporary Snowflake probe/patcher workflows before terminal handoff.

---

## 6. Governance last

Only after all technical gates are green, enforce/verify:

```text
main protected = TRUE
pull request required = TRUE
required check = faz7 / required-gate
strict = TRUE
force push blocked
deletion blocked
admin/bypass disabled where supported
merge commit enabled
squash merge disabled
rebase merge disabled
auto merge disabled
```

If connector authority cannot mutate these settings, return one consolidated owner-governance blocker after technical completion.

---

## 7. Next handoff must be terminal

The next Implementer handoff may be only:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

or

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

```text
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
FAZ_7_2_STARTED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
