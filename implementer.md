# SiteScore AI — Implementer → Reviewer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
IMPLEMENTER_STATE: BLOCKED_HARDENED_REBUILD_EVIDENCE_PROOF_MECHANICS
IMPLEMENTER_ACTION: STOP_FOR_REVIEWER_DESIGN_DECISION
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
PR_STATE: OPEN
PR_DRAFT: TRUE
PR_MERGEABLE_AT_LAST_CHECK: TRUE
PR_MERGED: FALSE
CURRENT_HEAD_SHA: 928da8646059c66cbff7c7438acbec8612c7aab3
CURRENT_CHANGED_FILE_COUNT: 20

OPS71_GHA_EXEC_001_STATUS: RESOLVED_CONFIRMED
OPS71_GOV_001_STATUS: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71_N8N_VULN_001_STATUS: HARDENED_REBUILD_PROBE_BLOCKED_BEFORE_SECURITY_SCAN

DESIGN_DECISION_REVIEW_REQUIRED: 1
CONTRACT_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
MERGE_PERFORMED: NO
FAZ_7_2_STARTED: NO

FAZ6_HISTORICAL_N8N_VERSION: 2.33.4
FAZ6_HISTORICAL_N8N_DIGEST: sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
FAZ7_HISTORICAL_N8N_STATUS: SUPERSEDED_FOR_SECURITY
NEW_N8N_BASELINE_STATUS: NOT_SELECTED_PROBE_BLOCKED_BEFORE_SECURITY_SCAN
SELECTED_N8N_VERSION: NONE
SELECTED_N8N_DIGEST: NONE

APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
N8N_WORKFLOW_JSON_CHANGE: NONE
SCANNER_SUPPRESSION: NONE
BLANKET_CVE_IGNORE: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
```

## 1. Reviewer hardened-rebuild correction executed

Reviewer authorized continuation of the upstream-faithful hardened n8n rebuild probe after independently classifying the previous `apk: not found` failure as a runtime-base construction mechanics defect rather than a security-gate result.

The corrected probe followed the Reviewer-required construction model:

```text
- re-enumerate latest official stable n8n at execution time;
- exact stable application source only;
- exact current upstream master n8n Docker build mechanics;
- exact current upstream n8n-base Dockerfile and build-base workflow binding;
- exact upstream DHI Node 26.7.0 base identity;
- build an upstream-equivalent reference base from that recipe;
- build a hardened base from the same recipe with only the explicitly authorized
  `openssh` and `graphicsmagick` top-level package lines omitted;
- do not run apk in the already-finalized n8nio/base image;
- allow upstream recipe itself to remove apk-tools at the end;
- only after package-diff proof, continue into n8n app build, runtime, SBOM/Grype,
  CISA KEV/OpenVEX reconciliation and compatibility gates.
```

No n8n application source, SiteScore application source, business semantics, credential semantics, or workflow bytes were changed.

## 2. Exact upstream identities bound and revalidated

The corrected run re-enumerated upstream releases at execution time. Latest official stable remained:

```text
n8n version = 2.37.7
release tag = n8n@2.37.7
release id = 381094367
published_at = 2026-09-02T08:41:33Z
official image = n8nio/n8n@sha256:869500232f49760d6a422d320d3ead3cb28ee93a00e6f67c89eb3d6b81acd6be
stable source commit = 2a4ca7868dc75edca4c575d6507021e1e6b0ec90
stable source tree = 40ff00093dbc474f82b4a133eb8ca51a3c76734a
```

Current upstream build identities were bound exactly:

```text
master commit = efd3ec9e260ef9ac7d9cbc134952590bedd33acb
master n8n Dockerfile blob = f72e1a3f3aae40319e58989e5fc2a71e687a1b59
master n8n-base Dockerfile blob = 1f2a82aa961a389750d774c88735fb11c5ae7c45
master build-base-image.yml blob = dd9e3badecd4fc1c5e4a51668824f5f214becaae
DHI ref = dhi.io/node:26.7.0-alpine3.24-dev@sha256:4b494d89fb26c950ce97865acf45b480dc7a6868fdc2b81c2d66599702eeac3f
builder = node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019
upstream runtime ref = n8nio/base:26.7.0@sha256:33687300c4e94dc00f42ec79ae15082ae07330ecd82ae1167125905b65908ff8
```

The exact 2.37.7 workspace already contains the upstream security overrides:

```text
ip-address@10 = 10.3.1
brace-expansion@5 = 5.0.9
```

No local dependency migration was applied. Nodemailer was not changed.

Frozen SiteScore workflow hashes remained exact before the probe:

```text
order-paid = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

## 3. Corrected runtime-base construction PASS

Exact corrected execution:

```text
workflow = faz7-7-1-n8n-hardened-rebuild-probe
run = 33680506876
job = 100415643221
source branch head = 41d567dd712940c725f997d4fbc3076741637eb0
PR synthetic merge SHA used by Actions = 0bfe130d8d1eaeb57504cf62fe50b859c3132fcf
```

The previously failing construction area now passes.

Reference upstream-equivalent base:

```text
image = sitescore-n8n-base-reference:26.7.0
local image ID = sha256:9a29f7d553fd327b5725a5698c55ffeafdc6d02e0724cb3feca25c8d1bc06053
architecture = amd64
node = v26.7.0
apk-tools removed by upstream recipe = PASS
```

The reference build visibly used the current patched Alpine packages, including:

```text
openssh family = 10.3_p1-r1
graphicsmagick = 1.3.47-r0
tiff = 4.7.1-r0
librdkafka = 2.14.1-r0
tini = 0.19.0-r3
tzdata = 2026c-r0
ca-certificates = 20260611-r0
```

Hardened base:

```text
image = sitescore-n8n-base-hardened:26.7.0
local image ID = sha256:c8cc9832404912fbc4e99d1c71499e34003c32297f11ba3a078cb01915a5e6d8
architecture = amd64
node = v26.7.0
source delta = only omission of the literal upstream package lines:
  openssh
  graphicsmagick
apk-tools removed by upstream recipe = PASS
```

Therefore the prior `apk: not found` construction blocker is resolved. No post-build mutation of a finalized n8nio/base image was used.

## 4. New mechanical blocker: incomplete Alpine dependency-attribution proof

Step 9, `Prove complete package diff and reverse-dependency ownership`, failed before the n8n production closure build and before any hardened-image security scan.

Exact failure:

```text
removed packages not attributable to omitted roots:
['freetype', 'libbz2', 'libdav1d', 'libde265', 'libedit', 'libheif',
 'libheif-dav1d', 'libheif-jpeg', 'libheif-libde265', 'libjpeg-turbo',
 'libltdl', 'libncursesw', 'libpng', 'libsharpyuv', 'libwebp', 'libwebpmux',
 'libwmflite', 'libxml2', 'ncurses-terminfo-base',
 'openssh-client-common', 'openssh-client-default', 'tiff', 'xz-libs']
```

The image construction itself succeeded. The failure is in the proof algorithm.

The verifier attempted to reconstruct the dependency graph using only direct package-name references from `/lib/apk/db/installed` and deliberately ignored Alpine virtual/provider dependency tokens such as:

```text
so:*
cmd:*
pc:*
```

That simplified graph is not a complete representation of Alpine package dependency/provides resolution. Consequently, dependencies that disappeared legitimately when `openssh` and `graphicsmagick` were omitted were not all reachable through the verifier's direct-name graph and were conservatively classified as unattributed.

Examples are consistent with the intended removed capability families:

```text
openssh-client-common / openssh-client-default / libedit / libncursesw / ncurses-terminfo-base

and graphics/image chain packages including:
tiff / libheif* / libjpeg-turbo / libwebp* / libxml2 / xz-libs / freetype / libpng
```

However, per Reviewer instruction, Implementer is NOT self-authorizing a second proof-model redesign or assuming attribution is correct merely because the names look plausible.

Disposition:

```text
BASE_CONSTRUCTION_MECHANICS: PASS
PACKAGE_DIFF_PROOF: FAIL_MECHANICAL_INCOMPLETE_PROVIDER_GRAPH
N8N_PRODUCTION_CLOSURE_BUILD: NOT_REACHED
FINAL_N8N_IMAGE_BUILD: NOT_REACHED
N8N_RUNTIME_COMPATIBILITY: NOT_REACHED
N8N_SBOM: NOT_REACHED
N8N_GRYPE_SECURITY_SCAN: NOT_REACHED
CISA_KEV_OPENVEX_RECONCILIATION: NOT_REACHED
HARDENED_SECURITY_GATE: NOT_EVALUATED
NODEMAILER_EXCEPTION_GATE: NOT_EVALUATED
N8N_STATIC_TESTS: NOT_REACHED
ORDER_RECOVERY_RUNTIME_SMOKES: NOT_REACHED
```

This run MUST NOT be described as a hardened-image security PASS or security FAIL. No final hardened n8n candidate image was produced or scanned.

## 5. Evidence artifact

Artifact upload succeeded despite the proof failure:

```text
artifact name = faz7-n8n-hardened-rebuild-0bfe130d8d1eaeb57504cf62fe50b859c3132fcf
artifact id = 9866198082
artifact sha256 = 0f81ccac780bae84d69236fd4cb3b0616c2bef30180c847588236a3b42eb7bad
artifact size = 167464 bytes
created_at = 2026-09-02T20:42:58Z
expires_at = 2026-09-16T20:42:58Z
source branch head = 41d567dd712940c725f997d4fbc3076741637eb0
```

The artifact contains 16 files from the corrected construction/proof attempt, including bound upstream identities, base recipes/delta, and package inventories generated before the proof stopped.

## 6. Temporary probe cleanup

After preserving exact run/artifact evidence, the temporary workflow was removed:

```text
.github/workflows/faz7-7-1-n8n-hardened-rebuild-probe.yml
```

Current clean PR head:

```text
928da8646059c66cbff7c7438acbec8612c7aab3
```

PR #34 is again exactly the intended 20 permanent FAZ 7.1 files:

```text
OPEN
DRAFT
MERGEABLE
UNMERGED
changed files = 20
```

No temporary probe asset remains in the permanent PR scope.

## 7. Mandatory STOP

Reviewer explicitly required that if the corrected probe encounters another mechanical build/CI/evidence defect, Implementer must report the exact defect and STOP rather than self-authorize another design substitution.

Therefore:

```text
IMPLEMENTER_STATE: BLOCKED_HARDENED_REBUILD_EVIDENCE_PROOF_MECHANICS
IMPLEMENTER_ACTION: STOP_FOR_REVIEWER_DESIGN_DECISION
OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-N8N-VULN-001: HARDENED_REBUILD_PROBE_BLOCKED_BEFORE_SECURITY_SCAN
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
DESIGN_DECISION_REVIEW_REQUIRED: 1
CONTRACT_CHANGE_REQUIRED: 0
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
MERGE: NO
FAZ_7_2_STARTED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Reviewer must decide whether and how the Alpine package-attribution proof may be corrected (for example, by a complete provider-aware graph or another exact upstream package-manager-derived proof). Implementer will not infer or implement that next proof model without explicit Reviewer authority.
