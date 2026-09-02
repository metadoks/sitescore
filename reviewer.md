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
IMPLEMENTER_ACTION: RESUME_7_1_WITH_APK_SOLVER_BOUND_PACKAGE_ATTRIBUTION_PROOF
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 928da8646059c66cbff7c7438acbec8612c7aab3
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
LIVE_MAIN_PROTECTED: FALSE
LIVE_REQUIRED_CHECKS: NONE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_UNDER_APK_SOLVER_BOUND_PROOF

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

The original FAZ 7.1 contract and all later Reviewer security addenda remain authoritative except where this addendum explicitly supersedes package-attribution proof mechanics.

```text
original full 7.1 contract coordination commit:
  c61c772ccd8192cce0475b4fd30a0cb0a74b1b37

actionable n8n security decision:
  bb2c72a75eba92f825e0be4d873f030f13e97c46

verified vendor OpenVEX reconciliation decision:
  deb05237d075fac4f046264ada5933fb8a0de813

upstream-faithful hardened n8n rebuild decision:
  b4053b3d6e01dc4aa6f42b83b12c3336d07c0b89

runtime-base construction correction:
  afabb82f6cdcbb77f647de889d8433b3d0092984
```

Nothing here weakens exact-head review/LOCK, scanner visibility, frozen SiteScore application/business semantics, frozen n8n workflow bytes, governance requirements, or the prohibition on FAZ 7.2 / FAZ 8 start.

---

# 2. INDEPENDENT REVIEWER FINDING

Reviewer independently inspected Implementer handoff, live PR #34, live main, and exact corrected probe logs.

Current live state:

```text
PR #34 = OPEN / DRAFT / MERGEABLE / UNMERGED
base = main@fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
head = 928da8646059c66cbff7c7438acbec8612c7aab3
changed files = 20
main = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
main protected = FALSE
```

The 20-file permanent PR scope contains no frozen SiteScore application source file and no `automation/n8n/workflows/**` file.

Corrected hardened rebuild execution independently verified:

```text
run = 33680506876
job = 100415643221
source branch head used by probe = 41d567dd712940c725f997d4fbc3076741637eb0
synthetic PR merge SHA = 0bfe130d8d1eaeb57504cf62fe50b859c3132fcf
```

Step results:

```text
reference/hardened base construction = PASS
package-diff attribution proof = FAIL
production closure build = SKIPPED
final hardened n8n image = SKIPPED
runtime/import = SKIPPED
SPDX/Grype = SKIPPED
KEV/OpenVEX = SKIPPED
security gate = SKIPPED
static/runtime workflow smokes = SKIPPED
```

The prior `apk: not found` mechanics defect is resolved. Both exact-source bases built successfully and the hardened source delta was exactly the omission of the two Reviewer-authorized package lines:

```text
openssh
graphicsmagick
```

The new failure is in the hand-written attribution verifier, not in APK resolution or the candidate security gate.

Reviewer independently confirmed the verifier deliberately discards provider/virtual dependencies:

```text
if token.startswith(('!','so:','cmd:','pc:')): return None
```

It then tries to infer the removal closure using only direct package-name edges from `/lib/apk/db/installed`. That graph is incomplete for Alpine/APK semantics and therefore cannot authoritatively prove the removal closure.

Exact failure:

```text
removed packages not attributable to omitted roots:
['freetype', 'libbz2', 'libdav1d', 'libde265', 'libedit', 'libheif',
 'libheif-dav1d', 'libheif-jpeg', 'libheif-libde265', 'libjpeg-turbo',
 'libltdl', 'libncursesw', 'libpng', 'libsharpyuv', 'libwebp', 'libwebpmux',
 'libwmflite', 'libxml2', 'ncurses-terminfo-base',
 'openssh-client-common', 'openssh-client-default', 'tiff', 'xz-libs']
```

The build log itself shows these families being installed underneath `graphicsmagick` and `openssh`, which is consistent with the intended hardening. But consistency by package name is not accepted as proof.

Therefore:

```text
BASE_CONSTRUCTION_MECHANICS: PASS
PACKAGE_ATTRIBUTION_PROOF: FAIL_MECHANICAL_CUSTOM_GRAPH_INCOMPLETE
N8N_HARDENED_SECURITY_RESULT: NOT_DETERMINED
N8N_HARDENED_CANDIDATE_ACCEPTED: NO
N8N_HARDENED_CANDIDATE_REJECTED_FOR_SECURITY: NO
```

---

# 3. DESIGN DECISION — APK SOLVER IS THE ATTRIBUTION AUTHORITY

The Implementer is authorized to correct only the package-attribution proof model.

Do NOT implement another custom dependency/provides resolver.

The authoritative causal proof must come from Alpine APK's own solver operating on an evidence-only image built from the same exact bound upstream recipe and repositories.

```text
DECISION: AUTHORIZE_APK_SOLVER_BOUND_PACKAGE_ATTRIBUTION_PROOF
PURPOSE: prove that the complete removed package closure is caused only by removing openssh and graphicsmagick
CANDIDATE_SEMANTICS_CHANGE: NONE
SECURITY_THRESHOLD_CHANGE: NONE
```

---

# 4. REQUIRED SOLVER-BOUND PROOF

Build three evidence identities from the exact same bound upstream n8n-base recipe / DHI ref / repository configuration in the same probe:

```text
A. REFERENCE_FINAL
   exact upstream-equivalent final base
   includes openssh + graphicsmagick
   final upstream apk-tools removal retained

B. HARDENED_FINAL
   exact same recipe
   only deliberate top-level package-line omissions:
     openssh
     graphicsmagick
   final upstream apk-tools removal retained

C. SOLVER_EVIDENCE
   exact REFERENCE recipe and packages
   evidence-only delta: defer the final `apk del apk-tools` until after APK solver proof
```

`SOLVER_EVIDENCE` is disposable test evidence only. It may never become the production candidate base.

Before solver mutation, retain from C:

```text
/etc/apk/repositories
/etc/apk/world
/lib/apk/db/installed
sorted package name+version inventory
```

Then, inside C, execute APK's actual package removal transaction for exactly:

```text
apk del openssh graphicsmagick
```

Requirements:

```text
transaction exit = 0
full stdout/stderr retained
post-transaction /etc/apk/world retained
post-transaction /lib/apk/db/installed retained
post-transaction sorted package inventory retained
```

Do not pass an explicit transitive package list to `apk del`.
Do not manually delete package files.
Do not use a custom provider graph to decide the closure.
Do not add/remove any third top-level capability.

After the solver transaction, perform the exact upstream final cleanup:

```text
apk del apk-tools
```

Then retain the final solver-derived package inventory.

---

# 5. REQUIRED EXACT EQUALITY CHECKS

The proof passes only if all of the following are exact:

```text
1. REFERENCE_FINAL source recipe = exact upstream bound recipe.
2. HARDENED_FINAL source diff = exactly two omitted package lines:
     openssh
     graphicsmagick
3. No package exists in HARDENED_FINAL that is absent from REFERENCE_FINAL.
4. APK solver transaction starts from the exact reference package state before final apk-tools removal.
5. APK solver removes openssh and graphicsmagick successfully without an explicit transitive package list.
6. SOLVER_EVIDENCE final package name+version inventory after solver removal + upstream apk-tools cleanup
   ==
   HARDENED_FINAL package name+version inventory.
7. Therefore:
   REFERENCE_FINAL minus HARDENED_FINAL
   ==
   the package closure actually removed by APK because the two authorized roots were removed,
   excluding only the separately-known evidence-stage apk-tools handling.
8. Required retained packages remain present at exact versions, including:
   tini
   tzdata
   ca-certificates
   libc6-compat
   librdkafka
   libssl3
   libcrypto3
   libexpat
9. Node 26.7.0 runtime remains loadable in HARDENED_FINAL.
10. `/etc/apk/repositories` binding is identical across reference/hardened/solver evidence construction.
```

A parser may be used only to normalize and compare inventories/transaction records. It must not replace APK as the dependency/provides resolution authority.

If APK's own removal transaction produces a final inventory different from omission-built HARDENED_FINAL:

```text
STOP
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

If any retained required package is lost:

```text
STOP
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

---

# 6. LATEST-STABLE RULE REMAINS ACTIVE

Reviewer rechecked upstream releases on 2026-09-03. The current official stable 2.x release observed remains:

```text
n8n@2.37.7
release id = 381094367
draft = false
prerelease = false
published_at = 2026-09-02T08:41:33Z
```

The Implementer must still re-enumerate at execution time.

If a newer official stable 2.x release exists, validate its official image first under the existing security policy. Do not silently remain on 2.37.7.

---

# 7. AFTER PACKAGE ATTRIBUTION PASSES

If the APK-solver proof passes, continue the already-authorized hardened probe without another Reviewer round-trip and execute every previously skipped gate:

```text
- exact stable n8n production closure build
- final linux/amd64 hardened n8n image
- non-root runtime
- n8n --version exact selected stable
- process startup/loadability
- frozen workflow imports
- frozen workflow hashes exact
- SPDX JSON SBOM
- full raw pinned Grype JSON
- CISA KEV correlation
- verified upstream OpenVEX reconciliation where applicable
- hardened security threshold
- exact nodemailer residual exception only if literally sole residual HIGH and every reachability control passes
- n8n static contracts
- order-paid compatibility smoke
- recovery compatibility smoke
```

Security threshold is unchanged. No scanner suppression, severity remapping, blanket ignore, custom SiteScore VEX, or broader residual-risk waiver is authorized.

If the hardened security/runtime/workflow probe passes:

```text
OPS71-N8N-VULN-001: HARDENED_CANDIDATE_PROBE_PASS
```

The Implementer may then convert successful mechanics into permanent reproducible FAZ 7.1 files and continue the remaining existing 7.1 gates.

If a security/runtime/workflow gate fails, STOP with exact evidence.
If another unrelated mechanical design defect appears, STOP with exact evidence.

---

# 8. PERMANENT PR / GOVERNANCE STATE

Current permanent PR #34 scope remains 20 files and contains no temporary probe workflow.

Governance is still unresolved:

```text
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
main protected = FALSE
required checks = NONE
```

Before READY_FOR_REVIEW / READY_TO_LOCK, the original governance requirements remain mandatory:

```text
main protected = TRUE
pull request required = TRUE
required status check = faz7 / required-gate
strict/up-to-date = TRUE
force pushes blocked
branch deletion blocked
merge commits enabled
squash disabled
rebase disabled
auto-merge disabled
```

No merge is authorized.
No user LOCK exists.
No FAZ 7.2 start is authorized.
No FAZ 8 start is authorized.

---

# 9. REQUIRED NEXT IMPLEMENTER HANDOFF

After executing this decision, update `implementer.md` and STOP with one of:

```text
IMPLEMENTER_STATE: PROBE_PASS_CONTINUING_7_1
IMPLEMENTER_STATE: BLOCKED_WITH_EXACT_EVIDENCE
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

Include at minimum:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
PR: #34
HEAD_SHA: <exact permanent PR head>

APK_SOLVER_PROOF_RUN: <run>
APK_SOLVER_PROOF_JOB: <job>
REFERENCE_BASE_BUILD: PASS/FAIL
HARDENED_BASE_BUILD: PASS/FAIL
APK_SOLVER_TRANSACTION: PASS/FAIL
APK_SOLVER_FINAL_INVENTORY_EQUALS_HARDENED: PASS/FAIL
HARDENED_PACKAGE_DIFF: PASS/FAIL

SELECTED_N8N_VERSION: <latest official stable>
SELECTED_N8N_DIGEST: <exact if selected>
N8N_RAW_CRITICAL: <count or NOT_REACHED>
N8N_RAW_HIGH: <count or NOT_REACHED>
N8N_CISA_KEV: <count or NOT_REACHED>
N8N_SECURITY_GATE: PASS/FAIL/NOT_REACHED
N8N_ORDER_WORKFLOW_HASH: <exact>
N8N_RECOVERY_WORKFLOW_HASH: <exact>
N8N_RUNTIME_COMPATIBILITY: PASS/FAIL/NOT_REACHED

OPS71-GHA-EXEC-001: RESOLVED
OPS71-GOV-001: <state>
OPS71-N8N-VULN-001: <state>
DESIGN_DECISION_REVIEW_REQUIRED: <0|1>
READY_FOR_REVIEW: <YES|NO>
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
