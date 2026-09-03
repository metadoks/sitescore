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
IMPLEMENTER_ACTION: RESUME_7_1_TO_COMPLETION_UNDER_STANDING_MECHANICAL_REMEDIATION_AUTHORITY
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 9bc557a6d32b62a1a66527ef10ee0358953ec04e
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
LIVE_MAIN_PROTECTED: FALSE
LIVE_REQUIRED_CHECKS: NONE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_AFTER_APK_SOLVER_ATTRIBUTION_PASS

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

The original FAZ 7.1 contract and all later Reviewer security decisions remain authoritative except where this decision explicitly supersedes mechanics or the meaning of the retained `libc6-compat` requirement.

Key prior Reviewer decisions include:

```text
original 7.1 contract:
  c61c772ccd8192cce0475b4fd30a0cb0a74b1b37
verified vendor OpenVEX reconciliation:
  deb05237d075fac4f046264ada5933fb8a0de813
upstream-faithful hardened n8n rebuild probe:
  b4053b3d6e01dc4aa6f42b83b12c3336d07c0b89
corrected runtime-base construction:
  afabb82f6cdcbb77f647de889d8433b3d0092984
APK-solver-bound attribution decision:
  f518b7a8dc649d5d7dc99d96f7977d01b176fc0d
```

Nothing here weakens frozen SiteScore application/business semantics, frozen n8n workflow bytes, scanner visibility, supply-chain evidence, exact-head review/LOCK, or governance requirements.

---

# 2. INDEPENDENT REVIEWER FINDING — APK SOLVER ATTRIBUTION PASSED

Reviewer independently inspected Implementer handoff and artifact from:

```text
workflow = faz7-7-1-n8n-apk-solver-probe
run = 33690496085
job = 100447897731
source head = 8fece108dd4993efe00a2ab183b7aaaf1c06f781
Actions synthetic merge SHA = 2734dc0c5ca185b571e8e99ee676575ae91abe45
artifact id = 9870011667
artifact sha256 = 0ba6d0e48ede8ae2dab63fbe5599119415069d9b402ed9719b406e51f5e353c6
```

The package-manager-authority proof succeeded through the intended attribution/equality gates:

```text
REFERENCE_BASE_BUILD: PASS
HARDENED_BASE_BUILD: PASS
SOLVER_EVIDENCE_BASE_BUILD: PASS
APK_SOLVER_TRANSACTION: EXECUTED
SOLVER_FINAL_INVENTORY == HARDENED_FINAL_INVENTORY: PASS
REFERENCE_MINUS_HARDENED == APK_SOLVER_REMOVAL_CLOSURE: PASS
openssh absent from hardened: PASS
graphicsmagick absent from hardened: PASS
```

APK itself removed the exact closure produced by:

```text
apk del openssh graphicsmagick
```

No explicit transitive package list was supplied. Therefore the previous custom dependency/provider graph problem is closed.

---

# 3. DESIGN DECISION — `libc6-compat` IS A REQUIRED APK CAPABILITY, NOT A REQUIRED LITERAL PACKAGE NAME

The prior retained-runtime language used `libc6-compat` as the required compatibility capability. It MUST NOT be interpreted as requiring that exact literal package record when the exact upstream Alpine/DHI solver satisfies the world requirement through a provider.

The preserved hardened installed database contains:

```text
P:gcompat
V:1.1.0-r4
p:libc6-compat=1.1.0-r4 so:ld-linux-x86-64.so.2=2 so:libgcompat.so.0=0
r:libc6-compat
```

The preserved APK world still contains:

```text
libc6-compat
```

The exact upstream n8n-base recipe also requests:

```text
apk add ... libc6-compat ...
```

Therefore APK resolved the requested `libc6-compat` capability to installed provider `gcompat==1.1.0-r4` for this exact DHI/Alpine base. This satisfies the retained-component requirement.

Canonical result:

```text
LIBC6_COMPAT_CAPABILITY: SATISFIED
LIBC6_COMPAT_PROVIDER: gcompat==1.1.0-r4
LIBC6_COMPAT_PROVIDER_EVIDENCE: APK_INSTALLED_DB_PROVIDES_PLUS_WORLD_REQUIREMENT
REQUIRED_RETAINED_COMPONENT_SET: PASS_IF_ALL_OTHER_REQUIRED_COMPONENTS_PRESENT
```

Implementer MUST retain this provider evidence in the successful final n8n evidence package. Do not add a redundant literal `libc6-compat` package, do not force-install another compatibility package, and do not change the upstream recipe solely to make the package name literal.

---

# 4. STANDING MECHANICAL REMEDIATION AUTHORITY — DO NOT STOP FOR EACH MINOR CI/PROOF DEFECT

To avoid repeated Reviewer round-trips, Implementer is now explicitly authorized to continue through purely mechanical build/CI/evidence defects until either the entire FAZ 7.1 candidate is READY_FOR_REVIEW or a TRUE DESIGN/SECURITY/GOVERNANCE BLOCKER is reached.

Without another Reviewer decision, Implementer MAY:

```text
- correct shell/Python/YAML syntax and quoting;
- correct GitHub Actions checkout/history/merge-base mechanics;
- correct artifact paths, evidence serialization and parsing;
- replace incomplete hand-written evidence parsing with authoritative tool output;
- correct Docker build-context/path/ARG wiring;
- retry transient upstream download/build failures;
- correct test environment dependencies needed to reproduce frozen tests, including git and frozen repo packages;
- correct FAZ6 Commerce replay environment until exact historical-equivalent 417 PASS;
- rerun temporary probes and remove them after evidence preservation;
- convert a successful hardened n8n probe into permanent reproducible FAZ 7.1 container/supply-chain files;
- update authorized n8n lock/provenance/docs/tests/workflow references to the final accepted candidate;
- correct permanent CI so all existing gates execute on the exact final PR head.
```

These actions do NOT require a new Reviewer stop provided all security and frozen-boundary requirements remain unchanged.

Implementer MUST NOT use this standing authority to:

```text
- change SiteScore scoring/business/application semantics;
- modify frozen n8n workflow JSON bytes;
- weaken/remove any test or security gate;
- suppress/ignore/remap scanner findings;
- author a SiteScore VEX for n8n;
- add arbitrary dependency upgrades;
- locally migrate nodemailer to 9.x unless upstream adopts that path under prior rules;
- broaden public ingress or begin FAZ 7.2 cloud/IaC work;
- commit production secrets;
- merge the PR;
- weaken GitHub governance requirements.
```

If a correction can be made without changing those protected semantics/policies, Implementer should fix, rerun, and continue rather than STOP for another Reviewer design decision.

---

# 5. TRUE STOP CONDITIONS

Implementer must STOP and return to Reviewer only if one of these occurs:

```text
A. final n8n security gate has any CRITICAL finding not covered by exact applicable upstream vendor VEX;
B. any CISA KEV match exists;
C. any residual HIGH exists other than the exact previously authorized nodemailer reachability case;
D. the nodemailer case fails any required reachability/containment control;
E. a required frozen SiteScore workflow cannot load/run without semantic modification;
F. satisfying the candidate requires editing frozen SiteScore application/business source or frozen n8n workflow bytes;
G. satisfying the candidate requires a dependency/security policy not already authorized by Reviewer;
H. a newer official stable n8n release changes the required design materially and cannot be handled by the already-authorized official-first selection rule;
I. GitHub plan/capability makes the frozen governance requirements impossible rather than merely manually configurable;
J. a material architecture/platform incompatibility is discovered.
```

Ordinary mechanical CI/proof failures are no longer a mandatory Reviewer STOP.

---

# 6. CONTINUE N8N HARDENED CANDIDATE TO COMPLETION

At each fresh final-candidate run, re-enumerate official stable n8n releases. If a newer official stable exists, validate its official linux/amd64 image first. Use the official image if it satisfies the full security gate; otherwise retain failure evidence and continue the exact-source hardened path under prior authority.

If hardened path remains necessary, continue from the now-passed APK solver attribution and produce the final candidate. Mandatory evidence remains:

```text
linux/amd64 identity
non-root runtime
n8n --version == selected official stable version
actual startup/loadability
exact frozen workflow hashes
both frozen workflow imports
order-paid runtime compatibility smoke
recovery runtime compatibility smoke
n8n static contracts
SPDX JSON SBOM
raw pinned Grype JSON
CISA KEV correlation
exact upstream OpenVEX binding/reconciliation
no scanner suppression/ignore/severity remapping
full final package inventory
libc6-compat capability/provider proof
```

Security threshold remains:

```text
CISA KEV = 0
CRITICAL = 0 unless exact applicable verified vendor not_affected VEX
all OS HIGH = 0 unless exact applicable verified vendor VEX
brace-expansion HIGH = eliminated
ip-address HIGH = eliminated
no new HIGH introduced
```

The only possible residual HIGH remains the exact previously authorized nodemailer advisory and only when literally no other HIGH/CRITICAL remains and all reachability/containment requirements pass.

---

# 7. AFTER N8N PASS — FINISH ALL REMAINING 7.1 GATES WITHOUT REVIEWER ROUND-TRIPS

If the n8n candidate passes, immediately finish the rest of FAZ 7.1 in the same PR:

```text
API current suite = 114 PASS
report = 24 PASS
Commerce forward-applicable = 416 PASS + exact one phase-local deselect
FAZ6 frozen Commerce replay = 417 PASS
dispatcher supervisor tests = PASS
API image build/runtime/non-root/PDF/font = PASS
Commerce image build/runtime/non-root = PASS
API/Commerce/n8n SBOMs = PASS
API/Commerce vulnerability policy = PASS
permanent Actions full-40-char SHA pins = PASS
source-boundary = PASS on exact final head
faz7 / required-gate = PASS on exact final head
frozen app source diff = NONE
n8n workflow JSON diff = NONE
cloud/IaC mutation = NONE
secret committed = NONE
```

Permanent PR scope may expand only with files already authorized by the original 7.1 contract or narrowly necessary container/supply-chain helpers that are explicitly enumerated in Implementer handoff. No frozen source changes.

---

# 8. GOVERNANCE — COMPLETE LAST, THEN STOP ONLY IF OWNER UI ACTION IS STILL REQUIRED

Governance remains mandatory:

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

Current known state remains noncompliant:

```text
main protected = FALSE
required checks = NONE
```

Implementer should complete every code/evidence/CI gate first. If the available GitHub tooling still cannot mutate branch protection / repository merge settings, then and only then report a single consolidated owner-action blocker with exact settings to change. Do not stop earlier merely because governance is still pending.

If the repository plan itself prevents required governance, independently establish the capability limitation and return:

```text
OPS71-GOV-001: PLAN_CAPABILITY_BLOCKED
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

---

# 9. REQUIRED NEXT HANDOFF

The next Implementer handoff should be one of only two useful terminal states:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

with exact final head and all 7.1 evidence, or:

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

with one consolidated blocker report.

Do not return merely for another mechanical parser/build/test-environment defect covered by Section 4.

```text
READY_TO_LOCK: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
