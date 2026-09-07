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
REVIEWER_STATE: TERMINAL_CLOSURE_POLICY_ISSUED
IMPLEMENTER_ACTION: COMPLETE_7_1_ON_FROZEN_CANDIDATE_CUTOFF_WITHOUT_NONCRITICAL_REBASE_LOOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: e397cd77606f84809e282ad9b1de2075610b0676
REVIEWED_HEAD_SHA: NONE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: CONTINUE_UNDER_FROZEN_2_37_10_CANDIDATE_AND_AUTHORIZED_SNOWFLAKE_CAPABILITY_PRUNING

FAZ71_CANDIDATE_CUTOFF_DATE: 2026-09-07
FAZ71_N8N_CANDIDATE_VERSION: 2.37.10
FAZ71_N8N_SOURCE_COMMIT: 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
FAZ71_N8N_SOURCE_TREE: 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
FAZ71_N8N_OFFICIAL_AMD64_DIGEST_REFERENCE: sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
FAZ71_MOVING_LATEST_STABLE_GUARD: DISABLED_AFTER_CUTOFF_EXCEPT_EMERGENCY_REOPEN

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

## 1. Purpose of this optimized terminal handoff

FAZ 7.1 has accumulated excessive implementation/review iterations because the previous rule continuously rebound the checkpoint to the newest upstream n8n patch and newest scanner knowledge while the candidate was still being hardened.

That behavior is now intentionally terminated for this checkpoint.

The goal of the next Implementer run is not to discover a newer platform baseline. The goal is to finish, attest, and hand off one exact FAZ 7.1 release candidate.

This policy does NOT weaken the security gate. It converts the gate from a moving target into a reproducible release-candidate boundary.

---

## 2. Frozen FAZ 7.1 candidate cutoff

For purposes of closing FAZ 7.1, the authoritative n8n baseline is frozen to:

```text
version = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
official amd64 digest reference = sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
cutoff date = 2026-09-07
```

A newer ordinary n8n patch release appearing after this cutoff MUST NOT automatically rebase/restart FAZ 7.1.

A newer non-emergency patch belongs to later normal dependency/security maintenance after 7.1 lock.

The old rule `latest official stable guard = must continuously select newest stable` is superseded for this checkpoint by:

```text
candidate identity guard = exact frozen 2.37.10 source/tree/build inputs
```

Do not restart 7.1 merely because 2.37.11 or another routine patch appears.

---

## 3. Emergency reopen rule — the ONLY post-cutoff moving-target exception

After this handoff, a newer release/advisory/scanner update may reopen the frozen candidate only when at least one of these conditions is proven:

```text
A. CISA KEV match affects a component present in the candidate; OR
B. a NEW undispositioned CRITICAL affects a component present in the candidate; OR
C. a newly disclosed vulnerability is directly reachable through SiteScore's enabled runtime/workflows/public attack surface and materially defeats an existing security boundary; OR
D. the frozen candidate cannot be built/run safely without a broader architecture/dependency change.
```

The following by themselves are NOT grounds to restart candidate selection:

```text
new ordinary n8n patch release
new MEDIUM/LOW advisory
new HIGH in an already-reviewed/contained family without changed reachability
scanner database timestamp changing after the exact candidate evidence run
upstream dependency churn unrelated to SiteScore enabled runtime
new optional node/package that is absent or deterministically excluded from final image
```

If an emergency reopen condition is hit, stop once with one consolidated true blocker. Do not enter exploratory patch-forward loops.

---

## 4. Existing n8n security design remains authoritative

The accepted capability boundary remains:

```text
NODES_EXCLUDE retains:
  n8n-nodes-base.executeCommand
  n8n-nodes-base.localFileTrigger
  n8n-nodes-base.emailSend
  n8n-nodes-base.snowflake
```

The Snowflake/TOML resolution remains capability reduction, not a dependency-contract violation:

```text
snowflake-sdk@2.1.0 may be removed only from graph-proven Snowflake-only production closure.
toml@3.0.0 may be removed only when snowflake-sdk@2.1.0 is its sole production parent.
shared non-Snowflake production dependencies must remain.
```

Required after-prune inventory:

```text
n8n-nodes-base@2.37.4 = PRESENT
snowflake-sdk@2.1.0 = ABSENT
toml@3.0.0 = ABSENT
shared_non_snowflake_removed = []
no unrelated version change
Snowflake node unavailable at runtime = PASS
```

Still prohibited:

```text
frozen SiteScore business/application behavior changes
frozen n8n workflow JSON changes
n8n/Snowflake application-source patching
incompatible toml major override
unadopted Snowflake parent upgrade
blanket scanner suppression
blanket CVE ignore
SiteScore-authored VEX used to waive an otherwise actionable vulnerability
arbitrary unrelated dependency upgrades
alternate CI/self-hosted runner workaround
FAZ 7.2 cloud/IaC work
merge before READY_TO_LOCK + literal user LOCK
FAZ 8 work
```

---

## 5. Application container security refresh authority — bounded, one-way

The current application image security gate has surfaced vulnerabilities in the previously frozen Python/Debian container baseline. Implementer is authorized to perform ONE bounded application-base security refresh without returning to Reviewer, provided all of the following remain true:

```text
Python major/minor family = 3.11.x only
Debian family = bookworm/slim-bookworm only
architecture = linux/amd64
base reference = immutable digest
no application/business source semantics change
no unrelated Python dependency modernization
no distro replacement
no blanket apt upgrade detached from the reproducible image build
no scanner suppression
```

Implementer must choose the smallest secure same-family immutable base/snapshot update that closes the actionable candidate findings and passes the full frozen regression/runtime set.

Once that refreshed base produces the first fully green candidate security run, pin its exact version/digest/snapshot into the permanent lock/evidence and DO NOT chase later ordinary base refreshes during FAZ 7.1.

A later base change before LOCK is permitted only under the Emergency Reopen Rule in section 3.

---

## 6. Security evidence snapshot policy

For each final image, preserve the exact scanner/tool/database identities used for the terminal evidence run where available.

The final exact-head security evidence must satisfy, at the time of that terminal run:

```text
CISA KEV = 0
CRITICAL = 0
OS HIGH = 0
fast-uri vulnerable findings = 0
ip-address vulnerable findings = 0
brace-expansion vulnerable findings = 0
toml vulnerable findings = 0
Snowflake vulnerable closure = absent
no NEW undispositioned HIGH introduced by the hardening/refresh
```

The previously-authorized nodemailer residual HIGH may remain only if it is still exactly the previously reviewed advisory/version and every containment control remains proven:

```text
frozen workflows do not use emailSend
emailSend excluded
no SMTP transport injected
unsafe alternate execution/file nodes excluded as already required
editor/admin/API non-public in target deployment design
risk record complete with owner/expiry/re-review
no second residual CRITICAL/HIGH exception
```

After a terminal exact-head run satisfies this policy, a later scanner DB update alone does not invalidate the candidate unless section 3 emergency criteria are met.

---

## 7. Current known progress — do not redo passing work without cause

The Implementer should preserve already-achieved green work and rerun only as required by exact-head CI after changes.

Known achieved/accepted progress includes:

```text
source-boundary = PASS
static-contracts = PASS
FAZ6 Commerce replay = PASS
API regression = 114 PASS
report regression = 24 PASS
Commerce = 416 PASS + exactly one authorized phase-local deselect
API/Commerce build + runtime/non-root mechanics have materially progressed
Snowflake graph/pruning mechanics reached PASS before final hardened runtime assembly
frozen application source semantics change = NONE
frozen n8n workflow JSON change = NONE
```

Do not reopen frozen business/model/application design because a container or scanner mechanic changes.

---

## 8. Terminal technical checklist — one exact final head

Implementer must now finish all remaining work on one exact final PR head:

```text
N8N IDENTITY / BUILD
[ ] exact n8n 2.37.10 source commit/tree pinned
[ ] exact builder/runtime/base/Dockerfile identities pinned
[ ] Snowflake/TOML exclusive closure prune proven
[ ] n8n version = 2.37.10
[ ] linux/amd64 = PASS
[ ] non-root = PASS
[ ] startup/loadability = PASS

N8N FUNCTIONAL
[ ] frozen workflow hashes/imports = PASS
[ ] n8n static = PASS
[ ] order-paid webhook/auth/payload smoke = PASS
[ ] recovery schedule/API smoke = PASS
[ ] Snowflake node unavailable = PASS

SECURITY / SUPPLY CHAIN
[ ] application base bounded security refresh complete if needed
[ ] CISA KEV = 0
[ ] CRITICAL = 0
[ ] OS HIGH = 0
[ ] authorized npm-family findings = 0
[ ] no new undispositioned HIGH
[ ] only exact authorized nodemailer residual HIGH if containment passes
[ ] SPDX/SBOM complete
[ ] raw Grype evidence complete
[ ] OpenVEX/upstream disposition evidence complete where applicable
[ ] provenance/attestation complete
[ ] n8n-image.lock/permanent hardening assets complete

APPLICATION REGRESSION / RUNTIME
[ ] API = 114 PASS
[ ] report = 24 PASS
[ ] Commerce = 416 PASS + exactly 1 authorized deselect
[ ] FAZ6 Commerce replay = 417 PASS
[ ] API/Commerce/n8n runtime and non-root smokes = PASS
[ ] PDF/font smoke = PASS

CI / SCOPE
[ ] source-boundary = PASS
[ ] full 40-char Actions pin checker = PASS
[ ] static-contracts = PASS
[ ] container-validation = PASS
[ ] n8n-validation = PASS
[ ] faz7 / required-gate = PASS on exact final head
[ ] temporary probe/patcher workflows removed
[ ] frozen application source diff = NONE
[ ] frozen n8n workflow JSON diff = NONE
[ ] cloud/IaC mutation = NONE
[ ] production secret commit = NONE
```

Do not create new probes when an existing permanent job can prove the same property. If a temporary probe is unavoidable for a one-time mechanical diagnosis, remove it before terminal handoff.

---

## 9. Governance is the final gate, not an excuse to reopen technical work

After all technical gates are green, enforce/verify exactly:

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

If available GitHub authority cannot mutate these settings, stop ONCE with one consolidated owner action containing every required UI setting.

If the repository plan/account cannot support required protection on a private repository, report exactly:

```text
OPS71-GOV-001: PLAN_CAPABILITY_BLOCKED
```

Do not reopen container/n8n work because governance is manual.

---

## 10. Anti-loop execution rules

From this handoff until terminal return:

```text
DO NOT stop for YAML/shell/quoting/path/Docker/test-environment/artifact/evidence mechanics.
DO NOT reselect n8n because an ordinary newer patch exists.
DO NOT rescan/rebase endlessly against later database timestamps after a green terminal evidence snapshot.
DO NOT introduce new security requirements beyond this contract unless Emergency Reopen Rule applies.
DO NOT return partial progress reports as blockers.
DO NOT start FAZ 7.2.
DO NOT merge.
```

Implementer owns all mechanical corrections required to reach the terminal state.

When multiple mechanical issues remain, resolve them in one continuation rather than returning one at a time.

---

## 11. Required next Implementer handoff — terminal only

The next Implementer handoff MUST be exactly one of:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

with one exact final HEAD and complete evidence; or:

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

with ONE consolidated blocker that satisfies either the Emergency Reopen Rule or the final owner-governance condition.

No other intermediate STOP is authorized.

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
