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

REVIEWER_STATE: POST_LOCK_PUBLICATION_POLICY_PARITY_HARDENING_REQUIRED
IMPLEMENTER_ACTION: APPLY_SINGLE_PUBLISH_POLICY_PARITY_CORRECTION_THEN_COMPLETE_7_1_ONLY
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b

CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
PR_STATE: CLOSED
PR_DRAFT: FALSE
PR_MERGED: TRUE
PR_MERGEABLE: FALSE

OBSERVED_HEAD_SHA: f54e3c25a0aca26782b94bb427a14744c6b6fa14
REVIEWED_HEAD_SHA: f54e3c25a0aca26782b94bb427a14744c6b6fa14

FINAL_GREEN_PUSH_RUN: 35459207216
FINAL_GREEN_PR_RUN: 35459209786
FINAL_PUSH_REQUIRED_GATE_JOB: 105943963854
FINAL_PR_REQUIRED_GATE_JOB: 105944676923

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-APP-BASE-001: RESOLVED_EXACT_REVIEWER_AUTHORIZED_RESIDUAL
OPS71-N8N-DHI-001: RESOLVED_AUTHENTICATED_PULL_PASS
OPS71-N8N-VULN-001: RESOLVED_FINAL_SECURITY_GATE_GREEN
OPS71-GOV-001: RESOLVED_LIVE_RULESET_VERIFIED
OPS71-PUBLISH-001: MECHANICAL_POLICY_PARITY_DEFECT_CORRECTIVE_AUTHORIZED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
TECHNICAL_READY_FOR_LOCK_GATE: YES
READY_FOR_REVIEW: YES
READY_TO_LOCK: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

---

## POST-LOCK PUBLISH CORRECTIVE — AUTHORIZED

The merged FAZ 7.1 exact head and governance remain valid. Post-LOCK publication run `35465322918` reached terminal FAILURE only at:

```text
Generate application SBOM and enforce vulnerability policy on published digests
job = 105956479419
exit = 42
```

Everything before that point passed, including:

```text
exact main checkout = PASS
GHCR authentication = PASS
application image build/publish = PASS
frozen n8n rebuild/validation = PASS
frozen n8n runtime/security gate = PASS
n8n publish = PASS
published digest resolution = PASS

published API digest =
sha256:389ab3e3ad0b8b5a8ece0136f75f5505cbb2164b589f2e4030455cd955ca9243

published Commerce digest =
sha256:204b9fcf4658c8a54c967ecceee37aea2ca92da0042ef263934fb72a7112420e

published n8n digest =
sha256:64281333061b995883e2877aa07057c3a3b66575017810705a67a9d9e85be28e
```

Failure evidence:

```text
API_VULNERABILITY_BLOCKERS=1
CVE-2026-82049
severity=HIGH
package=python
version=3.11.16
scanner fix candidate=[3.14.0b1]
```

This is NOT a new security finding and NOT a new design decision. The exact same finding was already independently reviewed and accepted on the final PR candidate as:

```text
REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

The permanent PR validation workflow already contains the required bounded policy:

```text
CVE-2026-82049 exact Python 3.11.16 residual only
CISA KEV reconciliation required
application/source/runtime archive-extraction reachability proof required
public tar/tar.gz ingress proof required
raw Grype finding remains visible
exact residual count required
all other CRITICAL or HIGH-with-fix remains blocking
```

The post-LOCK publication workflow failed because it still uses the older generic policy and does not mirror this exact accepted residual classification.

Reviewer authorizes one post-LOCK corrective only:

```text
base = current main 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
scope = .github/workflows/faz7-publish-images.yml ONLY

required change:
make published API/Commerce image security validation enforce the same exact
CVE-2026-82049 residual/KEV/reachability policy already frozen in
.github/workflows/faz7-container-ci.yml.

FORBIDDEN:
application/business source changes
Dockerfile/base/dependency changes
n8n identity changes
workflow JSON changes
scanner suppression
blanket CVE ignore
SiteScore-authored VEX
threshold weakening
new release candidate selection
FAZ 7.2 work
```

The corrective must be made through a protected-main PR. It must preserve the raw published-image Grype evidence and fail closed for every vulnerability other than the exact already-authorized residual.

Acceptance for corrective closure:

```text
corrective PR required-gate = PASS
corrective PR changes exactly one file
corrective merge uses normal merge commit
post-merge faz7-publish-images = SUCCESS
API published-image residual = exact CVE-2026-82049 only
Commerce published-image residual = exact CVE-2026-82049 only
CISA KEV = 0
no new policy blockers
published n8n exact validated digest proof = PASS
SBOM = PASS
provenance = PASS
Cosign signing = PASS
attestations = PASS
publication evidence artifact = PASS
```

No further Reviewer round-trip is required for YAML/shell mechanics. Implementer must carry this bounded corrective through PR, CI and merge only after the normal Reviewer lock gate for the corrective exact head. FAZ 7.2 remains prohibited in this chat.

---

## POST-LOCK PUBLICATION CORRECTIVE — AUTHORIZED

Post-LOCK publication run:

```text
run = 35465322918
main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
status = COMPLETED
conclusion = FAILURE
```

Successful before failure:

```text
exact main checkout = PASS
GHCR auth = PASS
application image build/push = PASS
frozen n8n rebuild/validation/push = PASS
published digest resolution = PASS
```

First failing step:

```text
Generate application SBOM and enforce vulnerability policy on published digests
API_VULNERABILITY_BLOCKERS=1
BLOCKER = CVE-2026-82049 / HIGH / python 3.11.16 / scanner fix hint 3.14.0b1
exit = 42
```

This is not a newly discovered product/security blocker. Exact
`CVE-2026-82049` for CPython 3.11.16 was already independently reviewed on
the exact PR head and accepted only under:

```text
REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

with raw scanner visibility, CISA KEV=0, and zero tar/tar.gz extraction or
public archive-ingress reachability. The permanent PR gate contains this exact
bounded classification, while the post-LOCK publish workflow still uses the
older generic HIGH-with-any-fix-hint predicate. Therefore publication policy
drift caused the failure.

A complete publication-workflow audit also identified two stale n8n publication
inputs that must be corrected in the same single corrective, to avoid another
partial round trip:

```text
1. publish setup-node/test currently = 26.5.1
   frozen reviewed n8n host Node = 26.7.0

2. publish workflow has no fail-closed dhi.io login step
   permanent frozen DHI credential contract requires:
     DHI_USERNAME
     DHI_TOKEN
     docker login dhi.io --password-stdin
```

### Exact authorized corrective scope

Create one corrective PR from current protected main and change only the
minimum publication/governance-support files required to make
`.github/workflows/faz7-publish-images.yml` consistent with the already
reviewed FAZ 7.1 contracts.

Required behavior:

```text
A. application published-digest security gate:
   - keep raw Syft/Grype evidence
   - keep CISA KEV reconciliation
   - accept only exact CVE-2026-82049 on python 3.11.16
   - only under the already-reviewed residual-risk record
   - repeat/prove the same unreachable archive-extraction/public-ingress containment
   - require exactly one authorized residual per application image as applicable
   - any other CRITICAL or actionable HIGH remains blocking
   - no generic waiver, no blanket ignore, no SiteScore-authored VEX

B. n8n publication host toolchain:
   - setup/test Node = 26.7.0
   - N8N_VERSION/source commit/source tree/build/runtime digests unchanged

C. DHI publication auth:
   - fail closed on missing DHI_USERNAME or DHI_TOKEN
   - docker login dhi.io using --password-stdin
   - minimum/read-only credential use
   - logout on always()
   - no secret printing, commit, artifact, or anonymous fallback

D. retain:
   - exact main-source publication semantics
   - linux/amd64
   - immutable sha-<main SHA> tags/digests
   - n8n local-validated image ID == published pulled image ID proof
   - SBOM + provenance + keyless Cosign signing/attestation
   - evidence artifact upload
```

Forbidden:

```text
application/business source change
frozen n8n workflow JSON change
n8n candidate/version/source-tree change
security-threshold weakening
new residual exception
scanner suppression
generic CVE ignore
production deployment/IaC
FAZ 7.2 work
direct unprotected main write
```

Because `main` is protected, this must use a dedicated corrective branch/PR.
The corrective PR must pass the existing `faz7 / required-gate` under the
current governance rule before merge. User LOCK remains required for that
corrective merge if the protocol treats it as a new protected-main merge.

After corrective merge, the resulting main-triggered
`faz7-publish-images` run must reach SUCCESS and provide exact API, Commerce
and n8n digests plus publication evidence. Reviewer will then verify
main/tree/parents, ruleset, published digest evidence and mark FAZ 7.1
`LOCKED_VERIFIED`.

No 7.2 work is authorized in this chat.

---

## POST-LOCK PUBLICATION CORRECTIVE DECISION

The first post-LOCK publication run is terminal and failed:

```text
run = 35465322918
job = 105956479419
head/main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
status = COMPLETED
conclusion = FAILURE
```

Successful before failure:

```text
exact main checkout = PASS
GHCR authentication = PASS
application image build/publish = PASS
frozen n8n rebuild/validation = PASS
frozen n8n publish = PASS
published digest resolution = PASS
```

Resolved immutable published digests from the failed run:

```text
API = sha256:389ab3e3ad0b8b5a8ece0136f75f5505cbb2164b589f2e4030455cd955ca9243
Commerce = sha256:204b9fcf4658c8a54c967ecceee37aea2ca92da0042ef263934fb72a7112420e
n8n registry manifest = sha256:64281333061b995883e2877aa07057c3a3b66575017810705a67a9d9e85be28e
n8n validated local image digest = sha256:095a63519813b5fea1f742fc41e13635c93e727a9684459eee456141100a5db7
```

The first failing step was:

```text
Generate application SBOM and enforce vulnerability policy on published digests
API_VULNERABILITY_BLOCKERS=1
BLOCKER ('CVE-2026-82049', 'HIGH', 'python', '3.11.16', ['3.14.0b1'])
exit code = 42
```

Reviewer determination:

```text
NEW_SECURITY_VULNERABILITY = NO
NEW_REACHABILITY = NO EVIDENCE
DESIGN_CHANGE_REQUIRED = NO
SECURITY_THRESHOLD_WEAKENING_AUTHORIZED = NO
SCANNER_SUPPRESSION_AUTHORIZED = NO
SITE_SCORE_VEX_AUTHORIZED = NO
OPS71-PUBLISH-001 = MECHANICAL_POLICY_PARITY_DEFECT
```

Reason: permanent PR CI already carries an exact bounded policy for CVE-2026-82049. It requires the raw finding to remain visible, requires package/version exactly python 3.11.16, classifies only that exact HIGH residual, proves no tar/tar.gz extraction/ingress reachability, checks the current CISA KEV feed, and blocks all other CRITICAL or fixed HIGH findings. The publication workflow still uses the older generic rule and therefore contradicts the already-reviewed application security contract.

One additional parity defect is visible in the publication workflow: it sets up Node 26.5.1 while the frozen n8n lock and final validation authority are Node 26.7.0. The n8n publication build succeeded, but permanent publication policy must use the frozen 26.7.0 setup identity.

### Authorized corrective scope

Create one post-LOCK FAZ 7.1 corrective PR from exact current main:

```text
base = main@3abbbd97b87b699d01f6013b560ee79e09d1cd8c
scope = .github/workflows/faz7-publish-images.yml ONLY
```

Required changes only:

1. Replace publication application vulnerability classification with policy parity to the already-reviewed `.github/workflows/faz7-container-ci.yml` application gate:
   - fetch current CISA KEV;
   - require the existing residual-risk record/classification;
   - run the same source/runtime/public-tar reachability containment proof;
   - allow only exact `CVE-2026-82049 / HIGH / python / 3.11.16` when it is not KEV and containment is clean;
   - require that exact residual once per application image;
   - keep raw Grype/SBOM output;
   - block any KEV, any CRITICAL, and any other HIGH with fix versions.
2. Change publication Node setup from 26.5.1 to exact 26.7.0 and assert `node --version == v26.7.0` before the frozen n8n build.
3. Do not alter application/business source, Dockerfiles, dependency locks, frozen n8n identity, workflow JSON, scanner thresholds, governance, IaC, or cloud resources.
4. Do not add blanket ignores, scanner suppression, local CPython patch, beta Python migration, SiteScore-authored VEX, or generic CVE allowlists.

Required validation before merge:

```text
faz7 / required-gate = PASS on corrective PR exact head
source-boundary = PASS
static-contracts = PASS
container-validation = PASS
n8n-validation = PASS
FAZ6 replay = PASS
changed files = publish workflow only
```

Then Implementer must return `READY_FOR_REVIEW`. Reviewer will audit exact corrective head. A NEW literal user `LOCK` is required for the corrective merge because the prior LOCK authorized exact reviewed head `f54e3c25...`, not a new commit.

After corrective merge, the new main-triggered `faz7-publish-images` run must finish SUCCESS including:

```text
application published digest scan = PASS
published n8n equivalence/SBOM = PASS
provenance predicates = PASS
Cosign signatures = PASS
SBOM attestations = PASS
provenance attestations = PASS
publication evidence artifact = PRESENT
```

Only then may Reviewer set:

```text
FAZ_7_1_STATUS = LOCKED_VERIFIED
NEXT_CHECKPOINT_AUTHORIZED = NO
FAZ_7_2_STARTED = NO
```

No FAZ 7.2 work is authorized in this chat.

---

## POST-LOCK PUBLISH CORRECTIVE — EXACT SCOPE

Post-LOCK publish run `35465322918` completed with **FAILURE** at exactly one step:

```text
Generate application SBOM and enforce vulnerability policy on published digests
API_VULNERABILITY_BLOCKERS=1
BLOCKER ('CVE-2026-82049','HIGH','python','3.11.16',['3.14.0b1'])
exit code = 42
```

All preceding publication operations passed, including exact-main checkout, GHCR authentication, application image publication, frozen n8n rebuild/validation/publication, and published digest resolution.

Reviewer determination:

```text
NEW_SECURITY_BLOCKER = NO
DESIGN_DECISION_REQUIRED = NO
THRESHOLD_WEAKENING = NO
ROOT_CAUSE = POST_LOCK_PUBLISH_POLICY_PARITY_DEFECT
```

The exact same raw finding is already independently reviewed and accepted in the permanent PR CI under:

```text
CVE-2026-82049
package = python
version = 3.11.16
severity = HIGH
classification =
REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

Permanent PR CI already requires:
- exact id/package/version match,
- CISA KEV check first,
- reachability containment evidence,
- exact residual count,
- all other CRITICAL and actionable HIGH findings remain blockers.

The publish workflow currently uses an older generic rule:

```text
CRITICAL => blocker
HIGH with any scanner fix version => blocker
```

and therefore incorrectly interprets Grype's unrelated `3.14.0b1` fix suggestion as an actionable Python 3.11-series fix.

Authorized corrective is **only**:

1. modify `.github/workflows/faz7-publish-images.yml` application published-digest scan policy so the exact CVE-2026-82049 / python / 3.11.16 residual receives the same classification and constraints as `.github/workflows/faz7-container-ci.yml`;
2. retain CISA KEV-first blocking semantics;
3. retain all other CRITICAL and actionable HIGH blocking semantics;
4. do not add generic ignores, scanner suppression, SiteScore VEX, wildcard Python exceptions, dependency upgrades, image/base changes, or product semantic changes;
5. ensure both API and Commerce published-digest scans require the exact residual once and zero other blockers;
6. rerun through protected-main PR/merge governance;
7. after merge, require `faz7-publish-images` SUCCESS including n8n published-image identity, SBOM, provenance, Cosign signatures/attestations, and immutable publication evidence.

Current already-published application digests from failed run:

```text
API = sha256:389ab3e3ad0b8b5a8ece0136f75f5505cbb2164b589f2e4030455cd955ca9243
Commerce = sha256:204b9fcf4658c8a54c967ecceee37aea2ca92da0042ef263934fb72a7112420e
```

No FAZ 7.2 work is authorized. This is a FAZ 7.1 post-LOCK corrective only.

```text
OPS71-PUBLISH-POLICY-001: MECHANICAL_POLICY_PARITY_CORRECTIVE_REQUIRED
FAZ_7_1_LOCKED_VERIFIED: NO
FAZ_7_2_STARTED: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
```

---

## POST-LOCK PUBLICATION FAILURE — EXACT MECHANICAL REMEDIATION AUTHORIZED

Post-LOCK workflow run `35465322918` is terminal FAILURE on main merge commit:

```text
main / merge commit = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
tree = 06f9e3a3a7cb806ad5273e7855b586724bd65f7a
reviewed head parent = f54e3c25a0aca26782b94bb427a14744c6b6fa14
workflow = faz7-publish-images
job = publish / 105956479419
```

Successful publication work before the failure:

```text
exact main checkout = PASS
GHCR authentication = PASS
application image build/publish = PASS
frozen n8n rebuild/validate/publish = PASS
published digest resolution = PASS

API digest =
sha256:389ab3e3ad0b8b5a8ece0136f75f5505cbb2164b589f2e4030455cd955ca9243

Commerce digest =
sha256:204b9fcf4658c8a54c967ecceee37aea2ca92da0042ef263934fb72a7112420e

n8n digest =
sha256:64281333061b995883e2877aa07057c3a3b66575017810705a67a9d9e85be28e
```

The first and only failing step is:

```text
Generate application SBOM and enforce vulnerability policy on published digests
API_VULNERABILITY_BLOCKERS=1
BLOCKER ('CVE-2026-82049', 'HIGH', 'python', '3.11.16', ['3.14.0b1'])
exit code = 42
```

This does NOT represent a new vulnerability or a new security decision. The same exact raw finding was already independently reviewed and accepted in the permanent pre-merge container gate under the exact bounded classification:

```text
CVE = CVE-2026-82049
severity = HIGH
package = python
version = 3.11.16
classification =
REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
CISA KEV = 0
source extraction paths = NONE
runtime extraction paths = NONE
public tar/tar.gz ingress = NONE
```

Permanent `.github/workflows/faz7-container-ci.yml` already implements the authoritative exact policy at its application-security scan. The post-LOCK publish workflow currently uses a simpler generic rule and therefore rejects the already-authorized exact residual. This is a mechanical policy-parity defect.

### Authorized code scope

Create a 7.1 post-LOCK closure correction based on current main and modify ONLY:

```text
.github/workflows/faz7-publish-images.yml
```

The correction must make the published-image application scan enforce the SAME exact residual contract as the permanent pre-merge application scan.

Required properties:

```text
1. Keep raw Grype finding visible.
2. Keep CISA KEV = blocker.
3. Permit ONLY the exact tuple:
   CVE-2026-82049 / HIGH / python / 3.11.16
4. Require the exact residual to be present exactly once per API/Commerce image.
5. Preserve generic blocker rule for every other:
   CRITICAL
   HIGH with available fix
6. Preserve/emit an application security summary for published images.
7. Verify the existing risk record contains:
   CVE-2026-82049
   REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
8. Do not add scanner suppression, blanket ignore, SiteScore-authored VEX,
   Python beta upgrade, local CPython patch, or broader waiver.
9. No frozen product/business source change.
10. No n8n/workflow JSON change.
11. No IaC/cloud/deployment change.
```

Preferred implementation is to copy/reuse the exact decision logic already present in `.github/workflows/faz7-container-ci.yml` rather than invent a second security policy.

### Required closure flow

Because `main` is protected, this correction must go through a normal PR and the permanent `faz7 / required-gate`.

Implementer must:
- branch from exact current main `3abbbd97b87b699d01f6013b560ee79e09d1cd8c`;
- apply only the authorized publish-workflow parity correction;
- obtain exact-head `faz7 / required-gate = SUCCESS`;
- hand back `READY_FOR_REVIEW`;
- do not merge without Reviewer exact-head `READY_TO_LOCK` and literal user `LOCK`.

After the corrective PR is merged, the main-triggered `faz7-publish-images` run must reach terminal SUCCESS and produce:
- exact API/Commerce/n8n published digests;
- published application and n8n SBOM evidence;
- published-image security evidence;
- provenance;
- Cosign signatures/attestations;
- immutable publication artifact.

Only then may Reviewer mark:

```text
FAZ_7_1_STATUS: LOCKED_VERIFIED
```

No FAZ 7.2 work is authorized in this chat or by this correction.

---

## POST-LOCK MERGE VERIFICATION

Reviewer live verification after user-authorized LOCK:

```text
PR #34 = CLOSED / MERGED
reviewed head = f54e3c25a0aca26782b94bb427a14744c6b6fa14
merge commit = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
main tree = 06f9e3a3a7cb806ad5273e7855b586724bd65f7a
parent 1 = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
parent 2 = f54e3c25a0aca26782b94bb427a14744c6b6fa14
compare merge-commit...main = IDENTICAL
ahead = 0
behind = 0
main protected = TRUE
```

Merge integrity PASS. Exact reviewed head was merged by normal merge commit with the expected old-main parent.

Post-LOCK publication workflow is now the sole remaining 7.1 closure activity:

```text
workflow = faz7-publish-images
run = 35465322918
head/main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
status = IN_PROGRESS

checkout exact main = PASS
GHCR auth = PASS
Node setup = PASS
application image build/publish = PASS
frozen n8n rebuild/validate/publish = IN_PROGRESS
published digest resolution = PENDING
published-image security/SBOM = PENDING
provenance/sign/attestation = PENDING
publication evidence upload = PENDING
```

Therefore merge is verified, but FAZ 7.1 is not yet declared LOCKED_VERIFIED until the post-LOCK publication workflow reaches terminal success and immutable published digests/evidence are available. No code change, new implementation, or FAZ 7.2 work is authorized while this run is active.

---

## 0. Final governance verification — PASS

Reviewer live-read the GitHub branch and repository rules after owner configuration.

```text
main protected = TRUE
protection enabled = TRUE
active repository ruleset = main
ruleset id = 23707380
target = refs/heads/main
enforcement = active

pull request required = TRUE
required approving review count = 0
required status check = required-gate
GitHub UI/check identity = faz7 / required-gate
strict required status checks = TRUE

deletion rule = ACTIVE / BLOCKED
non-fast-forward rule = ACTIVE / FORCE PUSH BLOCKED
bypass actors = []
current_user_can_bypass = never

allow_merge_commit = TRUE
allow_squash_merge = FALSE
allow_rebase_merge = FALSE
allow_auto_merge = FALSE
```

The ruleset's pull-request rule advertises merge/squash/rebase method capability, but repository-level settings disable squash and rebase, so the effective allowed repository merge path is merge commit only.

Exact reviewed PR state remains:

```text
PR #34 = OPEN / DRAFT / MERGEABLE / UNMERGED
reviewed head = f54e3c25a0aca26782b94bb427a14744c6b6fa14
main = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
faz7 / required-gate = SUCCESS
technical/security blockers = NONE
governance blockers = NONE
```

Reviewer decision:

```text
OPS71-GOV-001: RESOLVED_LIVE_RULESET_VERIFIED
READY_TO_LOCK: NO
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
```

The Implementer must not change the reviewed head before merge. After the user sends literal `LOCK` in the Implementer chat, the Implementer may transition PR #34 out of draft if required and perform a normal merge commit for exact head `f54e3c25a0aca26782b94bb427a14744c6b6fa14`. Reviewer will then verify the resulting main SHA/tree/parents before marking FAZ 7.1 LOCKED_VERIFIED.
---

## 1. Independent exact-head Reviewer audit

Reviewer independently audited exact PR head:

```text
f54e3c25a0aca26782b94bb427a14744c6b6fa14
```

PR #34 remains OPEN / DRAFT / MERGEABLE / UNMERGED against:

```text
main = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
```

The PR changed-file set is restricted to the authorized FAZ 7.1 container,
supply-chain, CI, runtime-helper and documentation scope. No frozen SiteScore
application/business package source and no frozen n8n workflow JSON changed.

Frozen workflow hashes remain:

```text
order:
02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1

recovery:
f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

No cloud/IaC resource mutation and no production secret commit is present in
the reviewed changed-file set.

---

## 2. Exact-head CI — independently verified GREEN twice

### Push run

```text
run = 35459207216

static-contracts      = SUCCESS
faz6-commerce-replay  = SUCCESS
source-boundary       = SUCCESS
n8n-validation        = SUCCESS
container-validation  = SUCCESS
required-gate         = SUCCESS
```

### Pull-request run

```text
run = 35459209786

static-contracts      = SUCCESS
faz6-commerce-replay  = SUCCESS
source-boundary       = SUCCESS
n8n-validation        = SUCCESS
container-validation  = SUCCESS
required-gate         = SUCCESS
```

Permanent required check identity remains:

```text
faz7 / required-gate
```

---

## 3. Application validation — PASS

Exact-head hosted evidence confirms:

```text
API tests = 114 PASS
report tests = 24 PASS
Commerce tests = 416 PASS + exactly 1 authorized deselect
FAZ6 frozen Commerce replay = 417 PASS

linux/amd64 = PASS
non-root/read-only runtime = PASS
API web/worker/beat = PASS
Commerce web/dispatcher = PASS
PDF/font runtime = PASS
SBOM/Grype/image hygiene = PASS
```

Application runtime authority remains:

```text
python:3.11.16-slim-trixie
sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
DEBIAN_SUITE=trixie
target=linux/amd64
```

Exact temporary application residual:

```text
CVE-2026-82049
classification =
REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

Artifact evidence independently verified:

```text
API_CISA_KEV_MATCHES = 0
COMMERCE_CISA_KEV_MATCHES = 0
API_POLICY_BLOCKERS = 0
COMMERCE_POLICY_BLOCKERS = 0

source_extraction_matches = []
runtime_smoke_extraction_matches = []
public_tar_ingress_token_matches = []
```

Raw finding remains present; no scanner suppression, blanket waiver,
SiteScore-authored VEX, Python beta migration or local CPython patch was used.

Re-review trigger remains the first of:
- fixed Python 3.11.x security release,
- suitable official CPython 3.11 backport,
- any application tar/tar.gz extraction/ingestion path,
- before PUBLIC_LAUNCH authorization.

---

## 4. n8n final security/runtime audit — PASS

Frozen n8n authority:

```text
version = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0

builder =
node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019

DHI runtime =
dhi.io/node:26.7.0-alpine3.24-dev@sha256:4b494d89fb26c950ce97865acf45b480dc7a6868fdc2b81c2d66599702eeac3f
```

Final exact-head security summary independently inspected from artifact:

```text
BLOCKING_CRITICAL = 0
BLOCKING_HIGH = 0
CISA_KEV = 0
ACTIONABLE_OS_HIGH = 0
NEW_UNDISPOSITIONED_HIGH = 0

adm-zip HIGH = 0
brace-expansion HIGH = 0
fast-uri HIGH = 0
git HIGH = 0
ip-address HIGH = 0
pcre2 HIGH = 0
snowflake-sdk HIGH = 0
toml HIGH = 0
```

Exact residual set only:

```text
zlib 1.3.2-r0:
  CVE-2026-85091

nodemailer 8.0.10:
  GHSA-P6GQ-J5CR-W38F
  GHSA-2X7J-588G-CCC2

@tiptap/core 3.27.0:
  GHSA-J95F-988M-3J2F
```

Raw Grype findings remain visible and separately dispositioned. No additional
HIGH/CRITICAL residual is accepted.

Security remediation proof:

```text
adm-zip = 0.6.1
epub2 parent major change = FALSE

Git capability pruning removed exactly:
  git
  git-init-template
  pcre2

shared_non_git_runtime_removed = []

snowflake-sdk@2.1.0 = ABSENT
toml@3.0.0 = ABSENT
shared_non_snowflake_removed = []
```

Official runtime inventory proof:

```text
httpRequest = PRESENT
snowflake = ABSENT
emailSend = ABSENT
executeCommand = ABSENT
localFileTrigger = ABSENT
git = ABSENT
gitTool = ABSENT
```

Runtime/static evidence:

```text
n8n static = 12 PASS
N8N_RUNTIME_VERSION = 2.37.10
N8N_WORKFLOW_IMPORT = PASS
N8N_PUBLISH_STATE_PROOF = PASS
N8N_WEBHOOK_AUTH = PASS
N8N_ORCHESTRATION_INTEGRATION = PASS
N8N_WAIT_RESTART = PASS
N8N_RECOVERY_WORKFLOW_IMPORT = PASS
N8N_RECOVERY_NATURAL_SCHEDULE_TRIGGER = PASS
N8N_RECOVERY_SINGLE_BOUNDED_CALL = PASS
N8N_RECOVERY_SCHEDULER_RUNTIME = PASS
N8N_RECOVERY_REPLAY_ANALYSIS_PENDING = PASS
N8N_RECOVERY_REPLAY_REPORT_PENDING = PASS
N8N_RECOVERY_REPLAY_REFUND_RESPONSE_LOSS = PASS
N8N_RECOVERY_REPLAY_DELIVERY_UNCERTAIN = PASS
N8N_RECOVERY_REPLAY_LOCKED_WORKFLOW_CONVERGENCE = PASS
FROZEN_N8N_2_37_10_SNOWFLAKE_PRUNED_SECURITY_RUNTIME_GATE = PASS
```

---

## 5. Supply-chain evidence

Exact-head artifacts:

```text
application artifact:
id = 10589397389
sha256 = ee513e71bc05c6d3b453178b5e58156bf27ea3c7f49cc52f887d412517a51b66

n8n artifact:
id = 10588888591
sha256 = cc9519f68badb127b604cced62f5dbdd9b614573fbf3044883c82f7c41abc402
```

n8n artifact contains SBOM, Grype, upstream OpenVEX reconciliation,
release/source context, provenance, dependency graph proof, package-pruning
proof and runtime smoke evidence.

Permanent GitHub Actions dependencies are full 40-character SHA pinned.
DHI authentication is fail-closed and secrets are not committed to repository
source or artifact evidence.

---

## 6. Sole remaining blocker — owner GitHub governance

Reviewer live readback after technical green:

```text
main SHA = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
main protected = FALSE
protection enabled = FALSE
required status checks = NONE
rulesets = []

allow_merge_commit = TRUE
allow_squash_merge = TRUE
allow_rebase_merge = TRUE
allow_auto_merge = FALSE
```

The GitHub integration available to Reviewer has no repository-administration
write permission for branch protection/settings, so this cannot be corrected
from this chat.

Owner must configure the repository to exactly:

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

No additional technical/code work is authorized or required.

After owner configuration, Reviewer must live-read back branch/repository
settings. If exact governance passes with PR head still
`f54e3c25a0aca26782b94bb427a14744c6b6fa14`, Reviewer may issue
`READY_TO_LOCK` for that exact SHA.

Do not merge now. Do not start FAZ 7.2.

```text
TECHNICAL_SECURITY_BLOCKERS: NONE
OPS71-GOV-001: OWNER_CONFIGURATION_REQUIRED_CONFIRMED
READY_FOR_REVIEW: YES
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
FAZ_7_2_STARTED: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```


---

## POST-LOCK PUBLICATION CORRECTIVE — AUTHORITATIVE REVIEWER DECISION

The first post-LOCK publication run is terminal and failed:

```text
workflow = faz7-publish-images
run = 35465322918
head/main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
status = COMPLETED
conclusion = FAILURE
failed step = Generate application SBOM and enforce vulnerability policy on published digests
```

Everything before that point passed:

```text
exact main checkout = PASS
GHCR authentication = PASS
application image build/publish = PASS
frozen n8n rebuild/validation = PASS
n8n frozen runtime/security gate = PASS
n8n workflow/runtime/recovery proofs = PASS
published digest resolution = PASS
```

Resolved partial published digests from the failed run:

```text
API = sha256:389ab3e3ad0b8b5a8ece0136f75f5505cbb2164b589f2e4030455cd955ca9243
Commerce = sha256:204b9fcf4658c8a54c967ecceee37aea2ca92da0042ef263934fb72a7112420e
n8n registry manifest = sha256:64281333061b995883e2877aa07057c3a3b66575017810705a67a9d9e85be28e
n8n validated local image identity = sha256:095a63519813b5fea1f742fc41e13635c93e727a9684459eee456141100a5db7
```

These sha-3abbbd97... package versions are PARTIAL / NON-AUTHORITATIVE because the publication workflow did not reach published-image SBOM completion, provenance, Cosign signing/attestation, or immutable evidence upload. They MUST NOT be used as FAZ 7.2 deployment inputs.

### Root cause — publication policy drift, not a new vulnerability

The failed published API image reports exactly:

```text
CVE-2026-82049
severity = HIGH
package = python
version = 3.11.16
fix versions reported by Grype = [3.14.0b1]
```

This is the exact application residual already independently reviewed and accepted on the final PR head as:

```text
REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

Permanent PR CI already proves, for both API and Commerce:

```text
CISA KEV = 0
exact CVE-2026-82049 residual present once
source tar/tar.gz extraction paths = NONE
runtime extraction paths = NONE
public tar ingress tokens = NONE
all other policy blockers = 0
```

The publish workflow still contains the older generic rule:

```text
CRITICAL => block
HIGH + any fix version => block
```

and therefore incorrectly re-blocks the already-authorized exact residual merely because Grype lists the unrelated Python 3.14.0b1 beta as a fix.

This is a deterministic policy-alignment defect in the publication workflow. It is NOT:
- a newly disclosed vulnerability,
- a new reachable security condition,
- a contract/design change,
- authority to weaken the scanner,
- authority for a blanket CVE ignore.

A second publication drift is also present:

```text
publish host setup = Node 26.5.1
final frozen n8n builder/runtime family = Node 26.7.0
```

The first publication run's n8n rebuild still passed, but the host setup is stale and must be aligned in the same corrective to avoid carrying contradictory release evidence.

### Bounded corrective authorization

Create a new FAZ 7.1 corrective branch/PR from exact current main:

```text
base main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
allowed permanent file change =
.github/workflows/faz7-publish-images.yml
```

No other permanent path is authorized.

Required corrective changes:

1. Align publication host Node setup and explicit version assertion from 26.5.1 to exact 26.7.0.

2. Replace the published API/Commerce generic vulnerability classifier with the SAME exact application security policy already accepted in permanent container-validation:
   - keep raw Syft SPDX + raw Grype evidence,
   - fetch/check current CISA KEV,
   - require the committed residual-risk record and immutable Trixie base identity,
   - re-run the source/runtime/public-ingress reachability containment proof,
   - permit only exact `CVE-2026-82049 / HIGH / python / 3.11.16` under classification `REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX`,
   - require that exact residual exactly once for each API and Commerce image,
   - block any KEV match,
   - block every CRITICAL,
   - block every other fixable HIGH,
   - emit published-image security summary evidence.

3. Do NOT alter:
   - application/business source,
   - Python/base-image identity,
   - frozen n8n 2.37.10 source commit/tree,
   - n8n workflow JSON bytes,
   - n8n hardening/pruning logic,
   - vulnerability thresholds beyond the already-authorized exact residual,
   - Cosign/SBOM/provenance design,
   - GitHub governance/ruleset,
   - cloud/IaC/deployment state.

4. Keep permanent Actions dependencies full-SHA pinned.

### Corrective acceptance / terminal closure

Implementer must complete the corrective PR to one terminal handoff:

```text
changed permanent files = exactly .github/workflows/faz7-publish-images.yml
faz7 / required-gate on corrective PR exact head = PASS
source-boundary = PASS
static-contracts = PASS
container-validation = PASS
n8n-validation = PASS
FAZ6 replay = PASS
frozen app/workflow source diff = NONE
security threshold weakening = NONE
```

Then Reviewer independently audits the exact corrective head.

Because the previous literal LOCK was consumed by PR #34, a NEW literal user `LOCK` is required before the corrective PR may merge.

After corrective merge, the automatically triggered `faz7-publish-images` run on the new main must reach:

```text
application publish = PASS
n8n rebuild/validate/publish = PASS
digest resolution = PASS
published application SBOM/security policy = PASS
published n8n exact-image/SBOM proof = PASS
provenance = PASS
Cosign signatures = PASS
SBOM attestations = PASS
provenance attestations = PASS
immutable publication evidence artifact = PASS
overall workflow = SUCCESS
```

Only then Reviewer will record:

```text
FAZ_7_1_STATUS: LOCKED_VERIFIED
NEXT_CHECKPOINT_AUTHORIZED: NO
FAZ_7_2_STARTED: NO
```

FAZ 7.2 remains explicitly out of scope for this chat and must start only in a new conversation.

Control state:

```text
OPS71-PUBLISH-001: BOUNDED_POST_LOCK_CORRECTIVE_REQUIRED
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
SECURITY_REOPEN_REQUIRED: 0
READY_TO_LOCK: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
FAZ_7_2_STARTED: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```


---

## POST-LOCK PUBLICATION CORRECTIVE REVIEW — AUTHORIZED

Post-LOCK publication run:

```text
workflow = faz7-publish-images
run = 35465322918
head/main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
status = COMPLETED
conclusion = FAILURE
failed job = publish / step 8
failed step = Generate application SBOM and enforce vulnerability policy on published digests
```

Successful preceding publication work:

```text
exact main checkout = PASS
GHCR authentication = PASS
application image build/publish = PASS
frozen n8n rebuild/validation/publish = PASS
published digest resolution = PASS
```

Published n8n digest observed from the successful publish step:

```text
ghcr.io/metadoks/sitescore-n8n
sha256:64281333061b995883e2877aa07057c3a3b66575017810705a67a9d9e85be28e
```

Exact failure:

```text
API_VULNERABILITY_BLOCKERS=1
BLOCKER ('CVE-2026-82049', 'HIGH', 'python', '3.11.16', ['3.14.0b1'])
exit code = 42
```

Reviewer finding:

The failure is NOT a new vulnerability, new reachability result, KEV match, or
security-design reopen. The permanent pre-merge container-validation already
classifies this exact raw finding under the reviewed residual contract:

```text
id = CVE-2026-82049
severity = HIGH
package = python
version = 3.11.16
classification =
REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

The pre-merge policy additionally proves:

```text
CISA KEV match = 0
source tar/tar.gz extraction matches = []
runtime extraction matches = []
public tar ingress token matches = []
raw Grype finding remains visible
generic HIGH waiver = NONE
scanner suppression = NONE
SiteScore-authored VEX = NONE
```

The publish workflow is stale relative to that approved policy. Its current
step 8 uses only:

```text
CRITICAL => blocker
HIGH + non-empty scanner fix list => blocker
```

and therefore treats Grype's cross-series/beta `3.14.0b1` suggestion as if it
were an approved same-series Python 3.11 remediation. This is a publication
policy-parity defect.

### Authorized correction — exact narrow scope

Create one corrective branch/PR from current protected main and change ONLY:

```text
.github/workflows/faz7-publish-images.yml
```

unless a mechanically necessary test/evidence helper under
`deploy/containers/**` is strictly required to avoid duplicating the already
frozen policy logic.

The published-image application security gate must implement the SAME exact
classification semantics already green in
`.github/workflows/faz7-container-ci.yml`:

1. Fetch/use CISA KEV evidence and fail if the finding or related vulnerability
   IDs intersect KEV.
2. Preserve the raw Grype finding in publication evidence.
3. Accept only the exact tuple:
   `CVE-2026-82049 / HIGH / python / 3.11.16`.
4. Require the existing residual-risk record and exact classification string.
5. Require the same no-reachability proof for source/runtime/public archive
   ingress.
6. Require exactly one authorized residual occurrence per application image
   where the pre-merge contract expects it.
7. Keep all other CRITICAL findings blocking.
8. Keep all other HIGH findings with actionable fixes blocking.
9. Do not interpret `3.14.0b1` as an approved Python 3.11 same-series fix.
10. Do not suppress, delete, ignore, or mutate raw scanner output.

Forbidden:

```text
blanket HIGH ignore
scanner suppression
SiteScore-authored VEX
changing Python/application source
upgrading to Python beta
local CPython patch
weakening pre-merge container-validation
changing frozen n8n identity/workflows
changing published image content merely to bypass scanner output
starting FAZ 7.2
```

### Corrective acceptance

The correction is complete only when:

```text
corrective PR exact-head required-gate = SUCCESS
Reviewer exact-head audit = PASS
user literal LOCK = YES
corrective merge = normal merge commit
main protection/governance remains PASS
post-merge faz7-publish-images = SUCCESS
API published digest = recorded
Commerce published digest = recorded
n8n published digest = recorded
published API/Commerce SBOM + security evidence = PASS
published n8n exact-candidate identity/SBOM = PASS
provenance predicates = PASS
Cosign signing = PASS
SBOM/provenance attestations = PASS
publication evidence artifact = PRESENT
FAZ_7_1_LOCKED_VERIFIED = YES
FAZ_7_2_STARTED = NO
```

No further Reviewer round-trip is required for ordinary YAML/shell/evidence
mechanics before the corrective Implementer handoff. The Implementer must
continue to a terminal corrective `READY_FOR_REVIEW` or return only a true
new security/design/platform blocker.
