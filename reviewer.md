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
REVIEWER_STATE: DESIGN_DECISION_ISSUED
IMPLEMENTER_ACTION: RESUME_7_1_WITH_DETERMINISTIC_SNOWFLAKE_CAPABILITY_PRUNING_AND_COMPLETE_TO_TERMINAL_STATE
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 588da74d12ee9ac00540a516af52b645d932477f
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_UNDER_EXACT_SNOWFLAKE_CAPABILITY_PRUNING_AUTHORITY

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

The original FAZ 7.1 contract and every later Reviewer security/governance decision remain authoritative except where this decision supersedes the previously-attempted `toml -> 4.2.0` compatibility-constrained override path.

The following remain prohibited:

```text
- frozen SiteScore application/business semantic changes
- frozen n8n workflow JSON changes
- n8n application-source patches
- scanner suppression or blanket CVE ignores
- SiteScore-authored VEX
- arbitrary npm/pnpm dependency upgrades
- arbitrary parent-package major upgrades
- alternate CI / self-hosted runner workaround
- cloud/IaC work from FAZ 7.2
- merge before exact-head READY_TO_LOCK + user literal LOCK
- FAZ 8 work
```

Standing mechanical remediation authority remains active. Implementer must continue through ordinary YAML/shell/build/test-environment/evidence defects without Reviewer round-trips.

---

# 2. FRESH REVIEWER AUDIT — CURRENT BLOCKER IS REAL

Current clean PR state independently observed by Reviewer:

```text
PR #34 = OPEN / DRAFT / MERGEABLE / UNMERGED
base = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
head = 588da74d12ee9ac00540a516af52b645d932477f
changed files = 20
```

Current latest official non-draft/non-prerelease n8n stable remains:

```text
n8n = 2.37.10
official linux/amd64 digest = sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
```

Implementer proved the production dependency chain:

```text
toml@3.0.0
└─ snowflake-sdk@2.1.0
   └─ n8n-nodes-base@2.37.4
```

The direct parent `snowflake-sdk@2.1.0` declares:

```text
toml: ^3.0.0
```

Therefore direct `toml -> 4.2.0` override violates the parent contract and MUST NOT be used.

Reviewer independently checked later Snowflake SDK manifests:

```text
snowflake-sdk 2.2.0 -> toml ^3.0.0
snowflake-sdk 3.0.0 -> toml ^3.0.0
snowflake-sdk 3.1.0 -> toml ^3.0.0
snowflake-sdk 3.2.0 -> toml ^3.0.0
current snowflake-sdk 3.3.0 -> toml ^5.0.0
```

Upgrading n8n's `snowflake-sdk` from 2.1.0 to 3.3.0 would be an unrelated parent major upgrade and is NOT authorized in FAZ 7.1.

Current upstream n8n master itself still declares:

```text
snowflake-sdk = 2.1.0
```

So there is no upstream-adopted parent upgrade suitable for a narrow backport.

---

# 3. DESIGN DECISION — REMOVE THE UNUSED SNOWFLAKE CAPABILITY INSTEAD OF FORCING ITS VULNERABLE DEPENDENCY

SiteScore's frozen n8n workflows do not use the Snowflake node. Reviewer repository search found no SiteScore Snowflake usage. The exact n8n Snowflake node is:

```text
displayName = Snowflake
node name = snowflake
node type = n8n-nodes-base.snowflake
runtime import = snowflake-sdk
```

n8n's supported configuration exposes `NODES_EXCLUDE` specifically to prevent unneeded nodes from loading.

Therefore Implementer is authorized to reduce the final SiteScore n8n production capability surface by excluding Snowflake and deterministically pruning only the production dependency closure that becomes unreachable solely because Snowflake is disabled.

This is a security capability reduction, not an n8n application-source patch.

---

# 4. REQUIRED NODES_EXCLUDE STATE

Permanent production/staging n8n environment contract must include at least:

```text
n8n-nodes-base.executeCommand
n8n-nodes-base.localFileTrigger
n8n-nodes-base.emailSend
n8n-nodes-base.snowflake
```

Preserve every previously-authorized excluded node. Do not remove prior exclusions.

Required proof:

```text
- frozen workflow hashes remain exact
- neither frozen workflow references n8n-nodes-base.snowflake
- runtime configuration contains n8n-nodes-base.snowflake in NODES_EXCLUDE
- running n8n does not expose/load/execute the Snowflake node
- attempting to resolve/use the Snowflake node fails as unavailable/disabled
```

If the node still loads despite NODES_EXCLUDE, STOP as a true design/security blocker.

---

# 5. DETERMINISTIC PRODUCTION DEPENDENCY PRUNING AUTHORITY

Implementer MAY prune the final deployed production dependency graph after the exact selected stable production closure is materialized.

The pruning algorithm must be graph-derived, deterministic, and narrowly bound to Snowflake.

Start root:

```text
snowflake-sdk@2.1.0
```

The final image may remove:

```text
- the installed snowflake-sdk@2.1.0 package instance/symlink
- toml@3.0.0 if and only if graph proof shows snowflake-sdk is its sole remaining production parent
- any additional transitive package instance if and only if graph proof shows it has no remaining production parent outside the Snowflake closure
```

MUST NOT remove a shared production package merely because it appears under the Snowflake dependency tree.

Do not edit `packages/nodes-base` application source. Do not edit the Snowflake node source. Do not rewrite Snowflake's published package manifest. Do not fake a package version.

A deterministic build helper under the already-authorized `deploy/containers/**` scope may perform this pruning.

---

# 6. MANDATORY GRAPH / FILESYSTEM EVIDENCE

Before pruning, capture machine-readable production graph evidence including equivalent of:

```text
pnpm why --prod --recursive snowflake-sdk --json
pnpm why --prod --recursive toml --json
```

Also capture:

```text
- installed production package inventory before pruning
- direct + transitive parent relation map
- exact filesystem/package instances selected for removal
- shared-parent analysis for every removed transitive package
- installed production package inventory after pruning
- machine-readable before/after package delta
```

The evidence must prove:

```text
snowflake-sdk production parents before = only n8n-nodes-base Snowflake capability
snowflake-sdk installed copies after = 0
toml@3.0.0 production parents before = only snowflake-sdk@2.1.0
toml vulnerable installed copies after = 0
no shared non-Snowflake production dependency was removed
no package outside graph-proven exclusive closure changed version
no arbitrary dependency upgrade occurred
```

If `toml@3.0.0` has any other production parent in the exact candidate graph, it MUST NOT be removed through this authority and Implementer must STOP.

---

# 7. FUNCTIONAL SAFETY GATE AFTER PRUNING

After pruning, rebuild/start the final linux/amd64 candidate from scratch and prove all of the following on final bytes:

```text
n8n --version = selected official stable
linux/amd64 = PASS
non-root = PASS
startup/loadability = PASS
health = PASS
frozen order workflow import = PASS
frozen recovery workflow import = PASS
frozen workflow hashes = exact
n8n static contracts = PASS
order-paid webhook/auth/payload smoke = PASS
recovery schedule/API smoke = PASS
Snowflake node unavailable = PASS
no workflow migration = PASS
no credential semantic migration = PASS
```

The successful frozen workflow imports and runtime smokes are mandatory proof that removing the unused Snowflake dependency did not destabilize general node loading.

---

# 8. SECURITY GATE AFTER PRUNING

All previously-authorized hardening remains active, including:

```text
APK solver removal:
  openssh
  graphicsmagick

retained runtime security targets:
  libcrypto3 = 3.5.8-r0
  libssl3 = 3.5.8-r0
  libexpat = 2.8.4-r0

upstream-adopted dependency targets:
  fast-uri = 3.1.6
  ip-address@10 = 10.3.1
  brace-expansion@5 = 5.0.9
```

The old `toml -> 4.2.0` override is superseded and MUST NOT be applied.

Final security requirement:

```text
CISA KEV = 0
CRITICAL = 0
OS HIGH = 0
fast-uri vulnerable findings = 0
ip-address vulnerable findings = 0
brace-expansion vulnerable findings = 0
toml vulnerable findings = 0
snowflake-sdk/toml removed-capability closure findings = 0
no new HIGH introduced
```

The only possible residual HIGH remains the previously-authorized conditional candidate:

```text
nodemailer 8.0.10
GHSA-p6gq-j5cr-w38f
```

It may remain only if it is literally the sole CRITICAL/HIGH residual and every prior emailSend/SMTP/admin-surface containment proof passes. Otherwise FAIL.

No vulnerability may be hidden by scanner ignore or SiteScore VEX.

---

# 9. PERMANENT SUPPLY-CHAIN CHARACTERIZATION

If successful, canonical final n8n characterization is:

```text
N8N_APPLICATION_SOURCE: EXACT_OFFICIAL_STABLE_SOURCE
N8N_BUILD_MECHANICS: EXACT_UPSTREAM_BOUND
N8N_RUNTIME_BASE: UPSTREAM_DERIVED_SITE_SCORE_HARDENED
N8N_RUNTIME_SECURITY_DELTA: APK_SOLVER_CAPABILITY_REMOVAL_PLUS_EXACT_PINNED_RUNTIME_PATCHES
N8N_DEPENDENCY_SECURITY_DELTA: EXACT_UPSTREAM_ADOPTED_BACKPORTS_PLUS_GRAPH_PROVEN_UNUSED_SNOWFLAKE_CAPABILITY_PRUNING
N8N_DISABLED_CAPABILITY: n8n-nodes-base.snowflake
```

Permanent documentation/risk record must explain:

```text
- why Snowflake is excluded
- frozen SiteScore workflows do not require it
- vulnerable toml is reachable only through excluded Snowflake capability in the proven graph
- exact graph/filesystem pruning method
- re-review trigger if a future SiteScore workflow requires Snowflake
- re-review trigger if upstream n8n adopts a fixed Snowflake dependency closure
```

---

# 10. PATCH-FORWARD CONTINUITY

Before every final candidate run, re-enumerate latest official stable and test official image first.

If a later patch stable appears:

- if upstream has fixed the Snowflake/toml closure, prefer the upstream fixed closure and do not prune unnecessarily;
- if the exact same Snowflake-only vulnerable closure remains and frozen SiteScore workflows still do not use Snowflake, this pruning authority carries forward;
- if Snowflake becomes shared/reachable by another required node, a new CRITICAL/HIGH package family appears, a CISA KEV appears, or the runtime/build architecture materially changes, STOP for Reviewer.

Do not stop for ordinary mechanics.

---

# 11. COMPLETE ALL REMAINING 7.1 GATES CONTINUOUSLY

Once n8n passes, continue without Reviewer round-trip through every remaining mechanical/permanentization item.

Already-established evidence reported by Implementer includes:

```text
source-boundary = PASS
full-40-character Actions pin checker = PASS
static-contracts = PASS
FAZ6 frozen Commerce replay = 417 PASS
API regression = 114 PASS
report regression = 24 PASS
API/Commerce image build + amd64/non-root/read-only identity = PASS
frozen application source diff = NONE
frozen n8n workflow JSON diff = NONE
```

Still required on one exact final PR head:

```text
Commerce = 416 PASS + exactly one authorized phase-local deselect
permanent n8n build assets + n8n-image.lock
final n8n digest / SBOM / raw Grype / KEV / OpenVEX reconciliation
nodemailer containment evidence if applicable
API/Commerce/n8n provenance + supply-chain evidence
API/Commerce runtime/PDF-font smokes
source-boundary = PASS
static-contracts = PASS
n8n-validation = PASS
faz6-commerce-replay = PASS
container-validation = PASS
faz7 / required-gate = PASS
frozen application source diff = NONE
frozen n8n workflow JSON diff = NONE
cloud/IaC mutation = NONE
committed production secrets = NONE
```

Temporary probes must be removed once their successful mechanics/evidence are absorbed into permanent CI.

---

# 12. GOVERNANCE IS THE LAST CONSOLIDATED OWNER GATE

After all technical gates pass, live repository governance must be:

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

Current connector authority may not expose these mutations. If so, Implementer must finish every technical gate first, then return exactly one consolidated owner-configuration blocker with precise UI values.

If repository plan/capability makes the required governance impossible, return a true governance/design blocker.

---

# 13. NEXT IMPLEMENTER HANDOFF — TERMINAL STATES ONLY

Implementer must now continue continuously and return only one of:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

or

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

Do not stop for mechanical CI/build/test/evidence issues.

If `READY_FOR_REVIEW`, handoff must include exact final head, final changed-file list, exact workflow run/job/artifact IDs and every security/test/governance proof required above.

Reviewer will then perform the full exact-head audit in one pass.

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
