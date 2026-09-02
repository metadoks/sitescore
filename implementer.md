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
IMPLEMENTER_STATE: BLOCKED_APK_SOLVER_REQUIRED_RETAINED_COMPONENT_MISSING
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
CURRENT_HEAD_SHA: 9bc557a6d32b62a1a66527ef10ee0358953ec04e
CURRENT_CHANGED_FILE_COUNT: 20

OPS71_GHA_EXEC_001_STATUS: RESOLVED_CONFIRMED
OPS71_GOV_001_STATUS: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71_N8N_VULN_001_STATUS: APK_SOLVER_GATE_BLOCKED_BEFORE_SECURITY_SCAN

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
NEW_N8N_BASELINE_STATUS: NOT_SELECTED_APK_SOLVER_GATE_BLOCKED
SELECTED_N8N_VERSION: NONE
SELECTED_N8N_DIGEST: NONE

APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
N8N_WORKFLOW_JSON_CHANGE: NONE
N8N_APPLICATION_SOURCE_PATCH: NONE
PERMANENT_FA7_1_SOURCE_CHANGE_FROM_THIS_PROBE: NONE
SCANNER_SUPPRESSION: NONE
BLANKET_CVE_IGNORE: NONE
SITE_SCORE_AUTHORED_VEX: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
```

## 1. Reviewer APK-solver decision executed

Reviewer explicitly authorized replacing the incomplete custom package dependency graph with Alpine APK itself as the sole package-attribution authority.

The authorized proof model required three bases constructed from the same exact upstream n8n-base recipe:

```text
A = reference upstream-equivalent base
B = hardened base with only top-level openssh + graphicsmagick package lines omitted
C = solver-evidence base equivalent to A, except final apk-tools removal is deferred only long enough to execute the evidence transaction
```

On C the exact package-manager transaction was required:

```text
apk del openssh graphicsmagick
apk del apk-tools
```

Normalized package-name + version inventories were then compared. No custom dependency/provider graph was used for attribution.

## 2. Exact upstream identities revalidated

Execution-time release enumeration confirmed latest official stable remained:

```text
n8n version = 2.37.7
release tag = n8n@2.37.7
release id = 381094367
published_at = 2026-09-02T08:41:33Z
official image = n8nio/n8n@sha256:869500232f49760d6a422d320d3ead3cb28ee93a00e6f67c89eb3d6b81acd6be
stable source commit = 2a4ca7868dc75edca4c575d6507021e1e6b0ec90
stable source tree = 40ff00093dbc474f82b4a133eb8ca51a3c76734a
```

Bound upstream build identities remained:

```text
master build commit = efd3ec9e260ef9ac7d9cbc134952590bedd33acb
master n8n Dockerfile blob = f72e1a3f3aae40319e58989e5fc2a71e687a1b59
master n8n-base Dockerfile blob = 1f2a82aa961a389750d774c88735fb11c5ae7c45
master build-base-image.yml blob = dd9e3badecd4fc1c5e4a51668824f5f214becaae
DHI ref = dhi.io/node:26.7.0-alpine3.24-dev@sha256:4b494d89fb26c950ce97865acf45b480dc7a6868fdc2b81c2d66599702eeac3f
builder = node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019
upstream runtime ref = n8nio/base:26.7.0@sha256:33687300c4e94dc00f42ec79ae15082ae07330ecd82ae1167125905b65908ff8
```

The exact 2.37.7 source already carried:

```text
ip-address@10 = 10.3.1
brace-expansion@5 = 5.0.9
```

No local dependency migration was applied. Nodemailer was not changed. Frozen workflow bytes remained exact:

```text
order-paid = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

## 3. APK-solver probe execution

```text
workflow = faz7-7-1-n8n-apk-solver-probe
run = 33690496085
job = 100447897731
source branch head = 8fece108dd4993efe00a2ab183b7aaaf1c06f781
Actions synthetic PR merge SHA = 2734dc0c5ca185b571e8e99ee676575ae91abe45
```

Initial gates passed:

```text
GitHub-hosted execution = PASS
latest-stable re-enumeration = PASS
exact upstream source/blob binding = PASS
frozen workflow hash binding = PASS
Node 26.7.0 / pnpm build-chain setup = PASS
```

All three exact base constructions succeeded:

```text
REFERENCE_BASE_IMAGE_ID = sha256:eb3475154a1aca1ab7ef267e04d84c4658f05027115949c131b8c5e5fb94bbe4
HARDENED_BASE_IMAGE_ID = sha256:c5da14f660fbdbcf33c370c085b7d0bd7632abc6dbe3a080a276799cceab4a94
SOLVER_EVIDENCE_BASE_IMAGE_ID = sha256:4983c3f8e1ac3259706d03c10a9b0d0847b507a4edcb4579446e55469873349e
architecture = amd64
node = v26.7.0
```

Reference and hardened production bases completed the upstream final apk-tools removal. Solver-evidence base intentionally retained apk-tools only for the authorized transaction.

## 4. APK solver attribution reached and inventory equality checks advanced successfully

The exact solver transaction executed:

```text
COMMAND=apk del openssh graphicsmagick
COMMAND=apk del apk-tools
```

The verifier advanced past the following mandatory assertions without failure:

```text
- hardened contains no package/version absent from reference;
- solver pre-state, excluding evidence-only apk-tools, equals the exact reference final inventory;
- solver final inventory equals the omission-built hardened final inventory;
- reference-minus-hardened package closure equals the APK solver removal closure;
- both authorized top-level roots openssh and graphicsmagick are absent from the hardened diff/final state.
```

Therefore the previous custom-provider-graph blocker is resolved by APK package-manager authority. Implementer does not infer dependency ownership manually; the evidence is the APK transaction plus exact normalized inventory equality.

## 5. Mandatory retained-component criterion FAILED

After the equality assertions, the Reviewer-required retained runtime package check failed on one literal package name:

```text
required retained packages missing: ['libc6-compat']
```

The Reviewer-required retained set was:

```text
tini
tzdata
ca-certificates
libc6-compat
librdkafka
libssl3
libcrypto3
libexpat
```

The proof therefore does NOT satisfy the complete Reviewer gate even though APK attribution/inventory equality advanced successfully.

Implementer does not reinterpret `gcompat` or any other installed provider as equivalent to the literal `libc6-compat` requirement. Whether the contract means exact package identity, an APK-provided capability, or another acceptable runtime-equivalence proof is now a Reviewer design decision.

Disposition:

```text
REFERENCE_BASE_BUILD: PASS
HARDENED_BASE_BUILD: PASS
SOLVER_EVIDENCE_BASE_BUILD: PASS
APK_SOLVER_TRANSACTION: EXECUTED
APK_SOLVER_INVENTORY_EQUALITY: ADVANCED_PAST_ASSERTIONS_WITHOUT_FAILURE
HARDENED_PACKAGE_ATTRIBUTION: APK_SOLVER_PROVEN
REQUIRED_RETAINED_COMPONENT_SET: FAIL_LIBC6_COMPAT_MISSING

N8N_PRODUCTION_CLOSURE_BUILD: NOT_REACHED
FINAL_HARDENED_N8N_IMAGE: NOT_REACHED
N8N_RUNTIME_COMPATIBILITY: NOT_REACHED
N8N_SBOM: NOT_REACHED
N8N_GRYPE_SECURITY_SCAN: NOT_REACHED
CISA_KEV_OPENVEX_RECONCILIATION: NOT_REACHED
HARDENED_SECURITY_GATE: NOT_EVALUATED
NODEMAILER_EXCEPTION_GATE: NOT_EVALUATED
N8N_STATIC_TESTS: NOT_REACHED
ORDER_RECOVERY_RUNTIME_SMOKES: NOT_REACHED
```

This execution is neither a hardened-image security PASS nor a hardened-image security FAIL.

## 6. Evidence artifact

Artifact upload succeeded:

```text
artifact name = faz7-n8n-apk-solver-2734dc0c5ca185b571e8e99ee676575ae91abe45
artifact id = 9870011667
artifact sha256 = 0ba6d0e48ede8ae2dab63fbe5599119415069d9b402ed9719b406e51f5e353c6
artifact size = 401440 bytes
created_at = 2026-09-02T22:34:28Z
expires_at = 2026-09-16T22:34:26Z
source branch head = 8fece108dd4993efe00a2ab183b7aaaf1c06f781
```

## 7. Temporary probe cleanup

After evidence preservation, the temporary solver workflow was removed:

```text
.github/workflows/faz7-7-1-n8n-apk-solver-probe.yml
```

Cleanup commit / current clean PR head:

```text
9bc557a6d32b62a1a66527ef10ee0358953ec04e
```

PR #34 returned to the intended permanent scope:

```text
OPEN
DRAFT
MERGEABLE
UNMERGED
changed files = 20
additions = 3864
deletions = 0
```

No temporary solver probe remains in the permanent PR diff. The probe did not modify any of the 20 permanent FAZ 7.1 source paths.

## 8. Mandatory STOP

Reviewer explicitly required STOP rather than manual interpretation if the full package proof criteria were not met.

Therefore:

```text
IMPLEMENTER_STATE: BLOCKED_APK_SOLVER_REQUIRED_RETAINED_COMPONENT_MISSING
IMPLEMENTER_ACTION: STOP_FOR_REVIEWER_DESIGN_DECISION
OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-N8N-VULN-001: APK_SOLVER_GATE_BLOCKED_BEFORE_SECURITY_SCAN
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

Reviewer must explicitly decide how the `libc6-compat` retained-runtime requirement is to be interpreted/proven for this exact upstream Alpine/DHI base before implementation resumes. Implementer will not substitute `gcompat`, modify the base recipe, weaken the retained-component criterion, or continue into security/runtime promotion without that authority.
