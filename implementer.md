# SiteScore AI — Implementer → Reviewer Handoff

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
IMPLEMENTER_STATE: BLOCKED_AWAITING_REVIEWER_DESIGN_DECISION
IMPLEMENTER_ACTION: STOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
PR_STATE: OPEN
PR_DRAFT: TRUE
PR_MERGEABLE_AT_LAST_CHECK: TRUE
PR_MERGED: FALSE
CURRENT_HEAD_SHA: b2dc44a3c1a93c5918bd3185ccafbb0b4ce6cc4b

BLOCKER_ID: OPS71-N8N-VULN-001
BLOCKER_CLASS: FROZEN_N8N_SUPPLY_CHAIN_VULNERABILITY_POLICY
BLOCKER_STATUS: OPEN
DESIGN_DECISION_REVIEW_REQUIRED: 1
CONTRACT_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO

N8N_FROZEN_IMAGE: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
N8N_BASELINE_CHANGE_PERFORMED: NONE
APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
FAZ_7_2_STARTED: NO
MERGE_PERFORMED: NO
```

## 1. Why implementation stopped

The Reviewer-issued FAZ 7.1 contract defines this vulnerability gate:

```text
CRITICAL vulnerability -> FAIL / LOCK BLOCKER
HIGH vulnerability with an available fixed version -> FAIL / LOCK BLOCKER
blanket ignore list -> FORBIDDEN
scanner disablement -> FORBIDDEN
```

The same contract explicitly requires the Implementer to stop and report:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

when a HIGH/CRITICAL issue is present in the frozen n8n digest and remediation would require changing a frozen version/business baseline.

The exact frozen n8n digest was therefore scanned without retagging, upgrading, rebuilding, suppressing findings, or weakening policy.

## 2. Exact evidence identity

```text
PR: #34
PR head at evidence run: b2dc44a3c1a93c5918bd3185ccafbb0b4ce6cc4b
GitHub Actions run: 32560317363
GitHub Actions job: 97000785115
Evidence artifact: faz7-7-1-bootstrap-evidence
Artifact ID: 9472649384
Artifact digest: sha256:4e8b07fb00c00b7e1e25e7a8fcc4a20c6c1f9d20f9f16df83cd41b4013bd9d5e
Frozen n8n digest: sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
```

Evidence artifact includes:

```text
artifacts/n8n-image-contract.txt
artifacts/n8n-policy.json
artifacts/n8n.grype.json
artifacts/n8n.spdx.json
api/requirements.lock
api/apt-runtime.lock
commerce/requirements.lock
base-image.lock
build-tools.lock
supply-chain-tools.lock
test-tools.lock
```

The image contract proof recorded:

```text
N8N_ARCH=amd64
N8N_USER=node
```

Therefore the frozen image satisfied the required AMD64 and non-root identity probes before vulnerability enforcement.

## 3. Successful pre-blocker supply-chain proofs

The read-only evidence run completed these gates successfully before the policy blocker:

```text
immutable container/tool lock re-resolution = PASS
hashed Python lock regeneration/reproducibility = PASS
fixed Debian snapshot native-runtime lock reproducibility = PASS
frozen n8n linux/amd64 pull/inspection = PASS
frozen n8n non-root user proof = PASS
frozen n8n SPDX SBOM generation = PASS
frozen n8n Grype JSON generation = PASS
evidence artifact upload = PASS
```

No product source tree was modified to obtain these results.

## 4. Vulnerability result

Raw Grype result contained:

```text
CRITICAL: 4 matches
HIGH: 34 matches
MEDIUM: 33 matches
LOW: 4 matches
```

Reviewer policy converts findings into blockers as follows:

```text
all CRITICAL findings block, even when no fix version is reported
HIGH findings block when an available fixed version is reported
```

The generated `n8n-policy.json` therefore contains exactly:

```text
blocker_count = 30
CRITICAL blockers = 4
HIGH-with-fix blockers = 26
unique advisory IDs = 22
affected package families = 13
```

Affected package families:

```text
@opentelemetry/propagator-jaeger
brace-expansion
fast-uri
graphicsmagick
ip-address
js-yaml
linkify-it
nanoid
nodemailer
postcss
tar
undici
vm2
```

## 5. Exact blocker list from `n8n-policy.json`

### CRITICAL — 4 blocker matches

| Advisory | Package | Installed | Scanner fix version(s) |
|---|---|---:|---|
| GHSA-cfcw-xp6x-25gj | vm2 | 3.11.5 | 3.11.6 |
| GHSA-m283-3h24-438v | vm2 | 3.11.5 | 3.11.6 |
| CVE-2025-32460 | graphicsmagick | 1.3.47-r0 | **none reported** |
| GHSA-m5w8-4gq2-6f8x | vm2 | 3.11.5 | 3.11.6 |

### HIGH with available fixed version — 26 blocker matches

| Advisory | Package | Installed | Scanner fix version(s) |
|---|---|---:|---|
| GHSA-6g55-p6wh-862q | postcss | 8.5.10 | 8.5.12 |
| GHSA-45rx-2jwx-cxfr | @opentelemetry/propagator-jaeger | 2.7.1 | 2.9.0 |
| GHSA-rgw5-rvv9-x895 | brace-expansion | 2.1.2 | 2.1.4 |
| GHSA-rgw5-rvv9-x895 | brace-expansion | 5.0.5 | 5.0.9 |
| GHSA-rgw5-rvv9-x895 | brace-expansion | 5.0.7 | 5.0.9 |
| GHSA-r292-9mhp-454m | tar | 7.5.19 | 7.5.21 |
| GHSA-r292-9mhp-454m | tar | 7.5.19 | 7.5.21 |
| GHSA-r28c-9q8g-f849 | postcss | 8.5.10 | 8.5.18 |
| GHSA-v245-v573-v5vm | linkify-it | 5.0.1 | 5.0.2 |
| GHSA-mh99-v99m-4gvg | brace-expansion | 2.1.2 | 2.1.3 |
| GHSA-mh99-v99m-4gvg | brace-expansion | 5.0.5 | 5.0.8 |
| GHSA-mh99-v99m-4gvg | brace-expansion | 5.0.7 | 5.0.8 |
| GHSA-gmc2-2x9w-cgh9 | vm2 | 3.11.5 | 3.11.6 |
| GHSA-3jxr-9vmj-r5cp | brace-expansion | 5.0.5 | 5.0.7 |
| GHSA-4cwx-7wf7-3272 | undici | 7.28.0 | 7.29.0 |
| GHSA-28wg-ghj8-5hjv | nanoid | 3.3.11 | 3.3.16 |
| GHSA-28wg-ghj8-5hjv | nanoid | 3.3.8 | 3.3.16 |
| GHSA-2v37-7h3g-55p8 | nanoid | 3.3.11 | 3.3.18 |
| GHSA-2v37-7h3g-55p8 | nanoid | 3.3.8 | 3.3.18 |
| GHSA-mwp4-54f8-5fhr | ip-address | 10.1.1 | 10.3.1 |
| GHSA-mwp4-54f8-5fhr | ip-address | 10.2.0 | 10.3.1 |
| GHSA-v2hh-gcrm-f6hx | fast-uri | 3.1.3 | 3.1.4 |
| GHSA-7p8r-x3mc-p8w7 | fast-uri | 3.1.3 | 3.1.5 |
| GHSA-5p4m-2wfm-xmqj | js-yaml | 4.3.0 | 4.3.1 |
| GHSA-p6gq-j5cr-w38f | nodemailer | 8.0.10 | 9.0.1 |
| GHSA-v836-6xw4-9cx3 | vm2 | 3.11.5 | 3.11.6 |

The duplicated `tar` blocker row is preserved exactly because the scanner/policy artifact emitted two matching artifacts for that advisory/package/version. No deduplication was used to alter policy count.

## 6. Current PR #34 scope at blocked head

At `b2dc44a3c1a93c5918bd3185ccafbb0b4ce6cc4b`, PR #34 is OPEN / DRAFT / MERGEABLE / UNMERGED and its current changed files are exactly:

```text
.github/workflows/faz7-7-1-bootstrap-locks.yml
deploy/containers/api/apt-runtime.lock
deploy/containers/api/requirements.lock
deploy/containers/base-image.lock
deploy/containers/build-tools.lock
deploy/containers/commerce/requirements.lock
deploy/containers/supply-chain-tools.lock
deploy/containers/test-tools.lock
```

The bootstrap workflow is temporary evidence/bootstrap machinery and is not being represented as the final permanent FAZ 7.1 CI workflow.

No changes exist under frozen application/business source paths in this blocked head.

## 7. Actions intentionally NOT taken

Because the frozen n8n digest tripped the Reviewer-defined policy gate, Implementer intentionally did **not**:

```text
upgrade n8n version
authorize or select a replacement n8n digest
retag the frozen n8n image
rebuild n8n
patch n8n packages in-place
add vulnerability ignores/waivers
turn off or weaken Grype/SBOM enforcement
continue into final Dockerfile/runtime implementation beyond the blocker gate
create DigitalOcean/OpenTofu/Cloudflare/Better Stack resources
start FAZ 7.2
merge PR #34
```

## 8. Reviewer decision required

Reviewer must independently inspect the evidence and issue an explicit design decision for `OPS71-N8N-VULN-001`.

The Implementer will not choose among baseline-changing or security-disposition options. In particular, any authorization to select a different n8n version/digest, alter the frozen n8n identity, or otherwise resolve this gate must come from Reviewer authority and must state the exact permitted scope and required revalidation.

Until such a decision exists:

```text
IMPLEMENTER_STATE: BLOCKED_AWAITING_REVIEWER_DESIGN_DECISION
IMPLEMENTER_ACTION: STOP
DESIGN_DECISION_REVIEW_REQUIRED: 1
USER_LOCK_AUTHORIZED: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
```

Frozen product statement remains:

> Mathematically validated scoring engine; empirical validation pending.

`COMB-005` remains `NOT_APPROVED`; composition remains unresolved and production may legitimately terminate `not_score_ready`.
