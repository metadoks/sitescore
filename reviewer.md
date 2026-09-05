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
IMPLEMENTER_ACTION: RESUME_7_1_WITH_N8N_2_37_10_TOML_4_2_0_COMPATIBILITY_CONSTRAINED_BACKPORT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: b012d4ee69257c4a6652340fda935690a28d8ffa
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
LIVE_MAIN_PROTECTED: FALSE
LIVE_REQUIRED_CHECKS: NONE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_UNDER_N8N_2_37_10_TOML_BACKPORT_AUTHORITY

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

The original FAZ 7.1 contract and every later Reviewer security/governance decision remain authoritative except where this decision explicitly rebinds the selected stable to n8n 2.37.10 and adds one narrowly-scoped production dependency remediation for `toml`.

No frozen SiteScore scoring/business/application semantics may change. Frozen n8n workflow JSON bytes remain immutable. No scanner suppression, blanket ignore, SiteScore-authored VEX, arbitrary dependency upgrade, deployment shortcut, merge, FAZ 7.2 work, or FAZ 8 work is authorized.

Standing mechanical remediation authority remains active. Implementer MUST continue through ordinary YAML/shell/build/test-environment/evidence defects without returning to Reviewer unless a true design/security/governance blocker occurs.

---

# 2. FRESH REVIEWER FINDING — CURRENT OFFICIAL STABLE IS N8N 2.37.10

Reviewer independently re-enumerated upstream releases. Current official non-draft/non-prerelease stable is:

```text
version = 2.37.10
release tag = n8n@2.37.10
release id = 382600929
published_at = 2026-09-04T09:13:04Z
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
official linux/amd64 digest = sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
```

Implementer official-first probe evidence:

```text
workflow = faz7-7-1-n8n-23710-official-probe
run = 33972295439
job = 101322830102
artifact id = 9971353356
artifact sha256 = 2b3300eb002da3cd710984df689c4cb57ceed4cf97b838c67283d85c78dfcba7
```

Runtime/import/SBOM/OpenVEX/KEV mechanics passed before the security gate. Frozen workflow hashes remained exact.

Official-image security result is a TRUE FAIL:

```text
N8N_RAW_CRITICAL = 12
N8N_RAW_HIGH = 42
N8N_CISA_KEV_MATCHES = 0
N8N_ACTIONABLE_GATE = FAIL
```

The previously-authorized blocker families remain present. A new production package family is also present:

```text
package = toml
installed = 3.0.0
package type = npm
GHSA-v5mp-jgw5-2x6j = HIGH
GHSA-82x6-q7mm-w9cf = HIGH
```

Reviewer independently inspected the raw Grype/SPDX artifact and confirmed both findings are attached to the production image copy at:

```text
/usr/local/lib/node_modules/n8n/node_modules/.pnpm/toml@3.0.0/node_modules/toml/package.json
```

---

# 3. TOML SECURITY DECISION — EXACT 4.2.0 IS THE ONLY AUTHORIZED TARGET

The two advisories have different minimum patched versions:

```text
GHSA-v5mp-jgw5-2x6j:
  affected < 4.1.2
  patched = 4.1.2

GHSA-82x6-q7mm-w9cf:
  affected < 4.2.0
  patched = 4.2.0
```

Therefore `4.1.2` is insufficient for the combined gate. The minimum version that closes BOTH findings is exactly:

```text
toml = 4.2.0
```

This is a major-version dependency change relative to `3.0.0`. Reviewer has not established an upstream-master `toml` override equivalent to the already-proven `fast-uri`, `ip-address`, and `brace-expansion` overrides. Therefore this authorization is deliberately compatibility-constrained and MUST NOT be treated as a generic dependency-upgrade precedent.

Implementer MAY add exactly one production-closure override/pin:

```text
toml -> 4.2.0
```

No other `toml` version is authorized by this decision.

---

# 4. MANDATORY REVERSE-DEPENDENCY AND LOCK-GRAPH PROOF BEFORE ACCEPTING THE BACKPORT

Before candidate promotion, Implementer MUST bind the exact production reverse dependency chain from the selected 2.37.10 source/lock graph using authoritative pnpm/lockfile evidence.

Required evidence:

```text
- exact 2.37.10 pre-change production lock graph;
- `pnpm why --prod toml` or deterministic equivalent from the exact source closure;
- every direct production parent that resolves to toml@3.0.0;
- pre/post lock graph diff;
- proof that the only intentional new npm resolution is toml@4.2.0 plus dependency metadata intrinsically required by that exact package version;
- proof no vulnerable toml@3.0.0 production copy remains;
- proof no second vulnerable toml copy remains under another path;
- proof no direct parent manifest declares an upper bound incompatible with 4.2.0.
```

If a production parent explicitly constrains `toml` to an incompatible major and the override violates that declared contract, STOP as a true design/security blocker. Do not patch parent application source to force compatibility.

No n8n application source may be edited.

---

# 5. TOML 4.2.0 TARGETED COMPATIBILITY GATE

Because this is a major-version backport, generic startup alone is insufficient. The final built production closure MUST prove at minimum:

```text
require('toml/package.json').version == 4.2.0
require('toml').parse exists
basic TOML parse smoke succeeds
prototype-pollution regression payload does not pollute Object.prototype
pathological deep-nesting advisory reproduction does not crash the n8n process / is rejected or safely contained by the patched package behavior
```

For every direct production parent identified by Section 4, add a narrowly-scoped module-load/usage smoke sufficient to prove that its `toml` integration still loads under 4.2.0. Do not modify parent source to make the smoke pass.

The full n8n functional gate remains mandatory afterward:

```text
linux/amd64
non-root
n8n --version = 2.37.10
startup/loadability
exact frozen workflow hashes
both frozen workflow imports
n8n static contracts
order-paid webhook/auth/payload compatibility smoke
recovery schedule/API compatibility smoke
no workflow migration
no node substitution
no credential semantic migration
```

If `toml@4.2.0` breaks the selected stable runtime/parent integration, STOP. Do not downgrade to a still-vulnerable version and do not create a reachability exception for these two advisories.

---

# 6. CARRY FORWARD THE EXISTING N8N HARDENING AUTHORITY TO 2.37.10

Subject to the fresh-stable guard, the previously-authorized hardened rebuild controls carry forward to exact n8n 2.37.10 source:

```text
OS capability reduction through APK solver:
  openssh absent
  graphicsmagick absent
  transitive removal only through APK solver proof

exact retained-runtime targets:
  libcrypto3 = 3.5.8-r0
  libssl3    = 3.5.8-r0
  libexpat   = 2.8.4-r0

exact upstream-adopted npm backports:
  fast-uri = 3.1.6
  ip-address@10 = 10.3.1
  brace-expansion@5 = 5.0.9

new exact compatibility-constrained backport:
  toml = 4.2.0
```

Use exact stable application source plus the already-authorized exact-current-upstream build mechanics only. Preserve Alpine 3.24 unless upstream patch-forward mechanics change under the existing rule. No blanket `apk upgrade`, no floating npm resolution, no unrelated dependency upgrade, no alternate Linux distribution, no scanner suppression.

`nodemailer` 9.x local migration remains NOT authorized unless a later upstream-adopted path is independently bound. The existing single-nodemailer residual exception remains the only possible residual HIGH path.

---

# 7. FINAL SECURITY THRESHOLD

The final hardened image MUST be rescanned from final linux/amd64 bytes with pinned Syft/Grype, exact-release OpenVEX verification, and CISA KEV correlation.

Mandatory result:

```text
CISA_KEV = 0
CRITICAL = 0
OS_HIGH = 0
fast-uri vulnerable findings = 0
ip-address vulnerable findings = 0
brace-expansion vulnerable findings = 0
toml vulnerable findings = 0
no new HIGH introduced
```

The only possible residual HIGH is exactly the previously-authorized conditional case:

```text
package = nodemailer
installed = 8.0.10
advisory = GHSA-p6gq-j5cr-w38f
```

It may remain only if literally no other CRITICAL/HIGH remains and every previously-defined reachability/containment control passes. Generic OpenVEX reconciliation must remain truthful; do not rewrite/suppress the residual.

---

# 8. CONTINUE ALL REMAINING FAZ 7.1 WORK WITHOUT REVIEWER ROUND-TRIPS

The current Implementer evidence already establishes substantial progress:

```text
source-boundary = PASS
full-40-character Actions pin checker = PASS
static-contracts = PASS
FAZ6 frozen Commerce replay = 417 PASS
API regression = 114 PASS
report regression = 24 PASS
API/Commerce image build + amd64/non-root/read-only identity = PASS
```

The Commerce forward-applicable regression still needs the mechanics-only exact deselection correction and must end at:

```text
Commerce = 416 PASS + exactly one authorized phase-local deselect
```

Once n8n passes, permanentize the accepted candidate and finish on one exact PR head:

```text
n8n permanent lock/build/provenance = PASS
API/Commerce/n8n SBOM and security policy = PASS
API web/worker/beat + PDF/font runtime = PASS
Commerce web/dispatcher runtime = PASS
source-boundary = PASS
static-contracts = PASS
FAZ6 replay = 417 PASS
API = 114 PASS
report = 24 PASS
Commerce = 416 PASS + exactly one deselect
faz7 / required-gate = PASS
frozen application source diff = NONE
frozen n8n workflow JSON diff = NONE
cloud/IaC mutation = NONE
production secret committed = NONE
```

Mechanical failures in these gates are covered by standing remediation authority. Fix and rerun; do not return to Reviewer for them individually.

---

# 9. PATCH-FORWARD CONTINUITY — TOML FAMILY NOW INCLUDED

If a newer patch-level official stable appears before final candidate completion, official-image-first validation remains mandatory.

Implementer MAY continue without another Reviewer decision only when ALL are true:

```text
- change is patch-level stable continuity;
- frozen workflows still import unchanged;
- no new CISA KEV exists;
- all CRITICAL/HIGH package families are within the already-authorized set, now including toml;
- the same or safer exact target versions eliminate those findings;
- no new security exception is required;
- no materially different Node/base/build architecture is required;
- no workflow/API/credential semantic migration is required.
```

If a new CRITICAL/HIGH package family appears, a new KEV appears, the required toml remediation changes beyond the proven 4.2.0-compatible path, or a broader dependency/base change is required, STOP as a true design/security blocker.

---

# 10. GOVERNANCE — COMPLETE LAST

Governance remains mandatory and currently pending:

```text
main protected = TRUE
PR required = TRUE
required status check = faz7 / required-gate
strict/up-to-date = TRUE
force push = blocked
branch deletion = blocked
bypass/admin bypass disabled where supported
merge commits = enabled
squash = disabled
rebase = disabled
auto-merge = disabled
```

Known current state remains noncompliant:

```text
main protected = FALSE
required checks = NONE
```

Complete all technical/evidence gates first. If connected GitHub tooling still cannot mutate branch protection/repository merge settings, return ONE consolidated owner-action blocker after everything else is green. If the repository plan makes the required governance impossible rather than merely manually configurable, return `OPS71-GOV-001: PLAN_CAPABILITY_BLOCKED` with evidence.

---

# 11. REQUIRED NEXT IMPLEMENTER HANDOFF

Do not stop again for ordinary CI/parser/build/test mechanics.

The next useful Implementer handoff must be one of:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

with exact final head and all FAZ 7.1 evidence, or:

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

with one consolidated true blocker.

```text
READY_TO_LOCK: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
