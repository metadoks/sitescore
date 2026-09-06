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
IMPLEMENTER_ACTION: FIX_EXACT_SNOWFLAKE_PRUNE_PATH_RESOLUTION_DEFECT_AND_COMPLETE_7_1_TO_TERMINAL_STATE
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 737a59a81512c954c5a51cd33e1331b294b11d8f
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SNOWFLAKE_PRUNING_DESIGN_VALID_MECHANICAL_PATH_RESOLUTION_FIX_REQUIRED

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

# 1. AUTHORITY CONTINUITY

All FAZ 7.1 Reviewer decisions through coordination commit
`5736757d47c03f57225abc6a2b24030faafad349` remain authoritative.

In particular, the deterministic unused-Snowflake capability-pruning design remains authorized and unchanged:

```text
NODES_EXCLUDE must retain:
  n8n-nodes-base.executeCommand
  n8n-nodes-base.localFileTrigger
  n8n-nodes-base.emailSend
  n8n-nodes-base.snowflake

snowflake-sdk@2.1.0 may be removed only from graph-proven Snowflake-only production closure.
toml@3.0.0 may be removed only if snowflake-sdk@2.1.0 is its sole production parent.
shared non-Snowflake production dependencies MUST remain.
```

The following remain prohibited:

```text
- frozen SiteScore application/business semantic changes
- frozen n8n workflow JSON changes
- n8n application-source or Snowflake-node source patching
- toml major override that violates snowflake-sdk contract
- snowflake-sdk major upgrade not adopted by n8n upstream
- scanner suppression / blanket CVE ignore / SiteScore-authored VEX
- arbitrary dependency upgrades
- cloud/IaC work from FAZ 7.2
- merge before exact-head READY_TO_LOCK + user literal LOCK
- FAZ 8 work
```

Standing mechanical-remediation authority remains active. Implementer MUST NOT return to Reviewer for ordinary YAML/shell/path/build/test/evidence mechanics.

---

# 2. FRESH LIVE REVIEWER AUDIT

Reviewer independently observed live PR #34 at:

```text
head = 737a59a81512c954c5a51cd33e1331b294b11d8f
base = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
state = OPEN
DRAFT = TRUE
mergeable = TRUE
merged = FALSE
changed files = 21
```

The 21st path is the temporary probe:

```text
.github/workflows/faz7-7-1-n8n-snowflake-prune-probe.yml
```

No frozen SiteScore application source or frozen n8n workflow JSON path is changed.

Exact-head permanent `faz7` run:

```text
run = 33993919061
head = 737a59a81512c954c5a51cd33e1331b294b11d8f
source-boundary = PASS
static-contracts = PASS
faz6-commerce-replay = PASS
n8n-validation = FAIL_PRE_PERMANENTIZATION
container-validation = FAIL_MECHANICAL_COMMERCE_DESELECT_REMAINS
required-gate = FAIL_BECAUSE_MANDATORY_UPSTREAM_JOBS_RED
```

This is concrete progress: source-boundary, permanent static contracts, and frozen FAZ6 Commerce replay are now green on the live head.

---

# 3. SNOWFLAKE-PRUNE PROBE — DESIGN PROOF PASSED, FINAL ASSEMBLY FAILED

Exact temporary probe:

```text
workflow = faz7-7-1-n8n-snowflake-prune-probe
run = 33993917159
job = 101380875339
head = 737a59a81512c954c5a51cd33e1331b294b11d8f
artifact id = 9977791100
artifact sha256 = bc5e678a3427c74a7ebb7832ffddc12f967f37fb8a35e41ac18f5c8417322dbb
```

Steps that PASS before the failure:

```text
latest stable/source/workflow-hash guard = PASS
production graph materialization = PASS
parent-contract + exclusive-prune derivation = PASS
upstream-bound hardened runtime base = PASS
exact stable n8n closure + authorized dependency backports = PASS
```

Failure occurs at:

```text
Finalize Snowflake-pruned hardened candidate = FAIL
```

Security/runtime final gates therefore were not reached in this run.

---

# 4. INDEPENDENT ARTIFACT AUDIT — EXACT ROOT CAUSE IS MECHANICAL

Reviewer downloaded and independently inspected artifact `9977791100`.

`parent-map.json` correctly proves the intended production graph:

```text
snowflake-sdk@2.1.0 parents = [n8n-nodes-base@2.37.4]
toml@3.0.0 parents = [snowflake-sdk@2.1.0]
snowflake_sdk_external_parents = []
toml_external_parents = []
```

It also records the intended authorized removed packages:

```text
snowflake-sdk@2.1.0
toml@3.0.0
```

However `package-delta.json` proves the probe actually removed the wrong package store:

```text
removed:
  n8n-nodes-base@2.37.4
  toml@3.0.0

snowflake-sdk@2.1.0 remains installed
```

Reviewer independently compared the before/after inventories:

```text
BEFORE:
  n8n-nodes-base@2.37.4 = 1
  snowflake-sdk@2.1.0 = 1
  toml@3.0.0 = 1

AFTER:
  n8n-nodes-base@2.37.4 = 0
  snowflake-sdk@2.1.0 = 1
  toml@3.0.0 = 0
```

This is NOT evidence that the Snowflake-pruning design is unsafe. It is an implementation bug in the probe's filesystem store selection.

Exact defect:

```python
# inventory row
'dir': str(m.parent.resolve())
'store': str(m.parents[2].resolve())

# deletion
store = Path(r['store'])
shutil.rmtree(store)
```

For `snowflake-sdk`, the discovered manifest path is reached through the symlink located inside the `n8n-nodes-base` pnpm store. `m.parent.resolve()` correctly resolves to the real Snowflake package directory, but `m.parents[2]` is taken from the UNRESOLVED symlink path before `.resolve()`. That makes `store` point to the `n8n-nodes-base` store rather than the actual `snowflake-sdk` store.

The deletion loop then removes `n8n-nodes-base@2.37.4` instead of `snowflake-sdk@2.1.0`.

Canonical classification:

```text
ROOT_CAUSE: SYMLINK_PATH_STORE_DERIVATION_BUG
CLASSIFICATION: MECHANICAL_IMPLEMENTATION_DEFECT
NEW_DESIGN_DECISION_REQUIRED: NO
SNOWFLAKE_PRUNING_DESIGN_REOPENED: NO
```

---

# 5. EXACT REMEDIATION BOUNDARY

Implementer is authorized to fix only the path/store-selection mechanics so the deletion target is derived from the resolved real package instance/store and cannot resolve to `n8n-nodes-base` or any other shared parent.

Required fail-closed proof before deletion:

```text
resolved delete target for snowflake-sdk identifies package name/version exactly snowflake-sdk@2.1.0
resolved delete target for toml identifies package name/version exactly toml@3.0.0
resolved snowflake delete target is NOT inside / equal to n8n-nodes-base store
resolved toml delete target has no non-Snowflake production parent
expected delete-target set == actual delete-target set
```

Required after-prune inventory result:

```text
n8n-nodes-base@2.37.4 = PRESENT
snowflake-sdk@2.1.0 = ABSENT
toml@3.0.0 = ABSENT
shared_non_snowflake_removed = []
no unrelated version change
```

Do not broaden the pruning algorithm. Do not delete a whole pnpm parent store merely because a symlink to the target package exists beneath it.

If exact real-store deletion cannot be done without deleting shared parent/package state, STOP as a true design blocker. Otherwise continue automatically.

---

# 6. COMPLETE THE FULL N8N GATE AFTER THE MECHANICAL FIX

After the corrected prune, final candidate must prove on final bytes:

```text
n8n --version = selected latest official stable
linux/amd64 = PASS
non-root = PASS
startup/loadability/health = PASS
frozen workflow hashes = exact
order workflow import = PASS
recovery workflow import = PASS
n8n static contracts = PASS
order-paid webhook/auth/payload smoke = PASS
recovery schedule/API smoke = PASS
Snowflake node unavailable = PASS
```

Security requirement remains unchanged:

```text
CISA KEV = 0
CRITICAL = 0
OS HIGH = 0
fast-uri vulnerable findings = 0
ip-address vulnerable findings = 0
brace-expansion vulnerable findings = 0
toml vulnerable findings = 0
snowflake-sdk/toml removed-capability findings = 0
no new HIGH introduced
```

Only the previously-authorized `nodemailer 8.0.10 / GHSA-p6gq-j5cr-w38f` may remain as the sole HIGH, and only if every previously-required emailSend/SMTP/admin-surface containment proof passes.

---

# 7. CONTINUE ALL REMAINING FAZ 7.1 MECHANICS WITHOUT REVIEWER ROUND-TRIP

Once n8n passes, continue directly through:

```text
Commerce = 416 PASS + exactly one authorized phase-local deselect
permanent hardened n8n assets under authorized deploy/containers/** scope
n8n-image.lock
final n8n digest / SPDX / raw Grype / OpenVEX / KEV / provenance
API/Commerce/n8n supply-chain evidence
API/Commerce runtime/PDF/font smokes
source-boundary = PASS
static-contracts = PASS
faz6-commerce-replay = PASS
container-validation = PASS
n8n-validation = PASS
faz7 / required-gate = PASS on exact final head
frozen app diff = NONE
frozen n8n workflow diff = NONE
cloud/IaC mutation = NONE
production secret commit = NONE
```

Remove the temporary Snowflake probe workflow after successful mechanics are absorbed into permanent assets/CI.

Do not stop for the known Commerce deselection-path mechanics or other ordinary CI/output/quoting/path defects.

---

# 8. GOVERNANCE LAST

After all technical gates pass, enforce/verify:

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

If connector authority cannot mutate these settings, return exactly one consolidated owner-configuration blocker only AFTER all technical gates are green. If plan/capability prevents the required governance, return a true governance/design blocker.

---

# 9. NEXT IMPLEMENTER HANDOFF — TERMINAL ONLY

Continue continuously. The next Implementer handoff may be only:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

or

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

Do not stop for mechanical CI/build/test/evidence failures.

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
