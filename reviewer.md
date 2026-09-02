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
REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: CORRECT_HARDENED_N8N_RUNTIME_BASE_CONSTRUCTION_AND_RERUN_PROBE
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 36e159fd1dccfa9b689b2d0ec00a1d20d04edb9c
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_PROBE_MECHANICS_FAILED_BEFORE_SCAN

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

The original FAZ 7.1 contract and all later Reviewer security addenda remain authoritative except where this narrow hardening correction explicitly supersedes probe mechanics.

```text
original full 7.1 contract coordination commit:
  c61c772ccd8192cce0475b4fd30a0cb0a74b1b37

actionable n8n security decision:
  bb2c72a75eba92f825e0be4d873f030f13e97c46

verified vendor OpenVEX reconciliation decision:
  deb05237d075fac4f046264ada5933fb8a0de813

upstream-faithful hardened n8n rebuild probe decision:
  b4053b3d6e01dc4aa6f42b83b12c3336d07c0b89
```

Nothing here weakens exact-head review/LOCK, scanner visibility, frozen SiteScore application/business semantics, frozen n8n workflow bytes, GitHub governance, or the prohibition on FAZ 7.2 / FAZ 8 start.

---

# 2. INDEPENDENT REVIEWER FINDING — PROBE FAILED BEFORE SECURITY EVALUATION

Reviewer independently inspected the live hardened rebuild run and exact job steps.

```text
PR head = 36e159fd1dccfa9b689b2d0ec00a1d20d04edb9c
commit = ci(faz7): probe upstream-faithful hardened n8n rebuild
workflow = faz7-7-1-n8n-hardened-rebuild-probe
run = 33676328747
job = 100401815558
run conclusion = FAILURE
```

Steps 1–9 completed successfully, including:

```text
- exact SiteScore checkout
- runner preparation
- pinned pnpm / Node 26.7.0 setup
- latest-stable re-enumeration
- exact upstream stable source/build identity binding
- stable production closure build
- upstream-faithful rebuilt candidate image build
```

Failure occurred at step 10 only:

```text
step = Remove only Reviewer-authorized unused OS capabilities
failure = /bin/sh: apk: not found
```

The upstream `n8nio/base` runtime intentionally removes `apk-tools`. Therefore attempting `apk info` / `apk del` in a post-build hardening layer is mechanically invalid.

Everything after step 10 was skipped:

```text
runtime/import proof = NOT_EXECUTED
SPDX = NOT_EXECUTED
Grype = NOT_EXECUTED
OpenVEX/KEV reconciliation = NOT_EXECUTED
hardened security gate = NOT_EXECUTED
nodemailer reachability proof = NOT_EXECUTED
static contracts = NOT_EXECUTED
final probe decision = NOT_EXECUTED
```

Therefore:

```text
N8N_HARDENED_SECURITY_RESULT: NOT_DETERMINED
N8N_HARDENED_CANDIDATE_ACCEPTED: NO
N8N_HARDENED_CANDIDATE_REJECTED_FOR_SECURITY: NO
```

This is a probe-construction defect, not evidence that the hardened strategy passed or failed its vulnerability gate.

Current PR scope was also independently checked: the 21st changed path is only the temporary hardened-probe workflow. No frozen application source or n8n workflow JSON is changed.

---

# 3. HARDENING CORRECTION — BUILD THE REDUCED RUNTIME BASE BEFORE APK-TOOLS REMOVAL

The prior security design remains unchanged. Only package-removal mechanics are superseded.

The Implementer MUST NOT invoke `apk` inside the already-built upstream `n8nio/base` final image.

Instead, construct an ephemeral hardened runtime base from the exact upstream n8n base-image build recipe before `apk-tools` is removed.

The already-bound upstream master build identity for this probe is:

```text
upstream master commit = efd3ec9e260ef9ac7d9cbc134952590bedd33acb
upstream Node line = 26.7.0 / Alpine 3.24
upstream builder image = node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019
upstream published runtime image = n8nio/base:26.7.0@sha256:33687300c4e94dc00f42ec79ae15082ae07330ecd82ae1167125905b65908ff8
upstream build-base DHI ref = dhi.io/node:26.7.0-alpine3.24-dev@sha256:4b494d89fb26c950ce97865acf45b480dc7a6868fdc2b81c2d66599702eeac3f
```

Before use, the probe must cryptographically/source-bind the upstream `docker/images/n8n-base/Dockerfile` and `.github/workflows/build-base-image.yml` at that exact upstream commit and verify that the DHI ref above is the Node 26.7.0 matrix input. If this identity no longer verifies, STOP rather than silently substitute another base.

---

# 4. EXACTLY AUTHORIZED BASE RECIPE DELTA

Start from the exact upstream base-image Dockerfile semantics for the bound upstream commit.

The only deliberate top-level runtime package-install delta authorized is:

```text
OMIT: openssh
OMIT: graphicsmagick
```

All other upstream base-image behavior must remain equivalent, including the font installation/cleanup path and these retained runtime packages/capabilities:

```text
tini
tzdata
ca-certificates
libc6-compat
librdkafka
Node runtime
upstream PATH / symlink behavior
NODE_PATH
WORKDIR
final apk-tools removal
```

Do NOT deliberately omit, remove, downgrade, or locally patch:

```text
libssl3
libcrypto3
libexpat
libc / musl runtime
Node runtime libraries
librdkafka
or any package required by a frozen SiteScore n8n node
```

Do not run blanket `apk upgrade`.
Do not copy arbitrary host libraries into the image.
Do not use Debian/Ubuntu or another Alpine line.
Do not substitute an unbound third-party base.

`tiff` and other packages may disappear only as dependency fallout from omitting the two authorized top-level capabilities. They may not be independently deleted by an ad-hoc file/package removal step.

---

# 5. REQUIRED PACKAGE-DIFF PROOF

Build both of these in the same probe context:

```text
A. reference upstream-equivalent base from the exact bound upstream base recipe + exact DHI ref
B. hardened base from the same recipe/ref with only openssh and graphicsmagick omitted
```

Retain complete sorted package inventories for A and B plus a machine-readable diff.

For every package absent from B, evidence must show either:

```text
1. it is openssh / graphicsmagick itself; or
2. it is a transitive dependency whose reverse-dependency closure in A is solely attributable to the omitted capabilities and is not required by any retained runtime package.
```

If any removed package has a retained reverse dependency, ambiguous ownership, or is required by Node/n8n/SiteScore workflow execution:

```text
STOP
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

The probe must also retain exact `/etc/apk/repositories` evidence and final installed package versions for reproducibility/security review.

---

# 6. FINAL N8N IMAGE CONSTRUCTION

Use the exact selected stable n8n source already bound by the prior probe rules.

Use the exact bound upstream master n8n Dockerfile/build mechanics, but pass the locally built hardened runtime base as `RUNTIME_IMAGE` rather than trying to mutate `n8nio/base` afterward.

The builder/native-module path must remain the exact upstream build path. Do not edit n8n application source.

The prior npm rules remain unchanged:

```text
brace-expansion@5 = upstream-adopted fixed 5.0.9 required
ip-address@10 = upstream-adopted fixed 10.3.1 required
nodemailer local 9.x migration = FORBIDDEN unless upstream adopts it
```

Preserve:

```text
NODES_EXCLUDE includes:
  n8n-nodes-base.executeCommand
  n8n-nodes-base.localFileTrigger
  n8n-nodes-base.emailSend
```

This exclusion is part of the security/runtime contract, not permission to change frozen workflow bytes.

---

# 7. RERUN ALL ORIGINAL HARDENED SECURITY GATES

After the corrected image is constructed, the probe must execute every gate that was skipped in run `33676328747`.

At minimum:

```text
- linux/amd64 identity
- non-root runtime
- n8n --version == selected official stable version
- actual process startup/loadability
- both frozen workflow imports
- exact frozen workflow SHA256 values
- pinned SPDX JSON SBOM
- full raw pinned Grype JSON
- CISA KEV correlation
- exact upstream OpenVEX reconciliation where applicable
- no scanner suppression/ignore/severity remapping
- n8n static contract suite
- order-paid compatibility smoke
- recovery compatibility smoke
```

The existing hardened security threshold remains unchanged:

```text
CISA KEV = 0
CRITICAL = 0
all OS HIGH = 0 unless exact applicable verified upstream VEX
brace-expansion HIGH = eliminated
ip-address HIGH = eliminated
no new HIGH introduced
```

The only possible residual HIGH remains the previously authorized exact nodemailer reachability case, and only if it is literally the sole residual HIGH/CRITICAL finding and every previously specified reachability/containment proof passes.

No broader risk waiver is authorized.

---

# 8. OFFICIAL-STABLE PREFERENCE STILL APPLIES

At the start of the rerun, re-enumerate official stable n8n releases again.

If a newer official stable release exists:

```text
1. scan/validate its official linux/amd64 image first;
2. if it satisfies the security gate, abandon the hardened custom path;
3. if it fails, retain the evidence and only then continue the exact-source hardened path under the same rules.
```

Do not silently stay on 2.37.7 if a newer stable release exists.

---

# 9. PROBE OUTCOME RULE

If corrected probe passes all security/runtime/workflow gates:

```text
OPS71-N8N-VULN-001: HARDENED_CANDIDATE_PROBE_PASS
```

Then the Implementer is authorized to convert the successful probe mechanics into permanent, reproducible FAZ 7.1 container/supply-chain files and continue the remaining existing 7.1 gates:

```text
- permanent n8n image lock/provenance
- source-boundary CI correction
- FAZ6 frozen Commerce replay = 417 PASS
- API 114 PASS
- report 24 PASS
- Commerce 416 PASS + exact one phase-local deselect
- API/Commerce image/non-root/PDF/SBOM checks
- exact-head faz7 / required-gate
- governance completion
```

If the corrected probe fails any security/runtime/workflow gate, report exact blocker evidence and STOP.

If it fails only due another mechanical build/CI defect, report the exact defect and STOP; do not self-authorize a new design substitution.

---

# 10. GOVERNANCE / LOCK STATE

Governance requirements remain unchanged and unresolved:

```text
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
```

No merge is authorized.
No user LOCK exists.
No FAZ 7.2 start is authorized.
No FAZ 8 start is authorized.

Required next Implementer handoff after rerun:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
IMPLEMENTER_STATE: <PROBE_PASS_CONTINUING_7_1 | BLOCKED_WITH_EXACT_EVIDENCE | READY_FOR_REVIEW>
IMPLEMENTER_ACTION: STOP
USER_LOCK_AUTHORIZED: NO
PR: #34
HEAD_SHA: <exact>
HARDENED_PROBE_RUN: <run>
HARDENED_PROBE_JOB: <job>
HARDENED_BASE_SOURCE_BINDING: PASS/FAIL
HARDENED_PACKAGE_DIFF: PASS/FAIL
N8N_RAW_CRITICAL: <count>
N8N_RAW_HIGH: <count>
N8N_CISA_KEV: <count>
N8N_SECURITY_GATE: PASS/FAIL
N8N_ORDER_WORKFLOW_HASH: <exact>
N8N_RECOVERY_WORKFLOW_HASH: <exact>
N8N_RUNTIME_COMPATIBILITY: PASS/FAIL
DESIGN_DECISION_REVIEW_REQUIRED: <0|1>
READY_FOR_REVIEW: <YES|NO>
READY_TO_LOCK: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
```
