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
REVIEWER_STATE: FINAL_BOUNDED_SECURITY_CLOSURE_AUTHORIZED
IMPLEMENTER_ACTION: COMPLETE_ADM_ZIP_PATCH_GIT_CAPABILITY_PRUNE_AND_EXACT_PYTHON_RESIDUAL_THEN_TERMINAL_CI
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 9601b9704d743dd5b34fee4ee727698a74d9cab5
REVIEWED_HEAD_SHA: NONE
LIVE_FAZ7_RUN: 35448352107
LIVE_CONTAINER_VALIDATION_JOB: 105911101555
LIVE_N8N_VALIDATION_JOB: 105911101243

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-APP-BASE-001: EXACT_CVE_RESIDUAL_REACHABILITY_PROOF_AUTHORIZED
OPS71-N8N-DHI-001: RESOLVED_AUTHENTICATED_PULL_PASS
OPS71-N8N-VULN-001: FINAL_BOUNDED_SECURITY_CLOSURE_AUTHORIZED

FAZ71_CANDIDATE_CUTOFF_DATE: 2026-09-07
FAZ71_N8N_CANDIDATE_VERSION: 2.37.10
FAZ71_N8N_SOURCE_COMMIT: 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
FAZ71_N8N_SOURCE_TREE: 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
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

## 0C. Superseding Reviewer decision — final bounded security closure

### Exact live state

```text
head = 9601b9704d743dd5b34fee4ee727698a74d9cab5
run = 35448352107

source-boundary       = PASS
static-contracts      = PASS
faz6-commerce-replay  = PASS
container-validation = FAIL only at application security scan
n8n-validation        = FAIL only at final two HIGH findings
required-gate         = FAIL because of the two failed security jobs
```

Security remediation already achieved:

```text
n8n CRITICAL: 2 -> 0
n8n raw HIGH: 25 -> 7
CISA KEV: 0
new undispositioned HIGH: 0
libcurl fixed to 8.22.0-r0
fast-uri vulnerable finding: 0
brace-expansion vulnerable finding: 0
ip-address vulnerable finding: 0
Snowflake/TOML findings: 0
```

No moving-latest n8n release rebase is authorized. Frozen n8n remains 2.37.10
with exact source commit/tree already recorded.

### A. adm-zip GHSA-7q85-xj36-vmfc — PATCH BACKPORT AUTHORIZED

Current graph evidence:

```text
adm-zip = 0.6.0
parent path = epub2@3.0.2 -> adm-zip
advisory = GHSA-7q85-xj36-vmfc / CVE-2026-77301
fixed version = 0.6.1
```

The advisory is a HIGH uncontrolled-memory-allocation/DoS issue and upstream
adm-zip 0.6.1 is the published fixed version.

Implementer is authorized to move ONLY:

```text
adm-zip 0.6.0 -> 0.6.1
```

using the existing frozen build-graph override mechanism.

Required evidence:

```text
pnpm why --prod adm-zip
direct parent/range or override-compatibility proof
lock diff limited to adm-zip required closure
no unrelated version churn
compiled/runtime adm-zip = 0.6.1
GHSA-7q85-xj36-vmfc finding = 0
n8n source commit/tree unchanged
full export/import/workflow runtime smokes PASS
```

No epub2 parent-major change and no n8n source patch is authorized.

### B. pcre2 CVE-2026-89161 — REMOVE UNUSED GIT CAPABILITY, DO NOT WAIVE

Evidence from the exact hardened image shows:

```text
pcre2 10.47-r1 is required by runtime package git
the final image world contains git
frozen SiteScore workflows contain no n8n-nodes-base.git
frozen SiteScore workflows contain no n8n-nodes-base.gitTool
Alpine 3.24/edge currently exposes pcre2 10.47-r1
upstream PCRE2 fixes CVE-2026-89161 in 10.48
```

Therefore the safer bounded resolution is unused-capability pruning rather than
inventing an Alpine package waiver or importing a foreign/manual library.

Authorized:

```text
add to NODES_EXCLUDE:
  n8n-nodes-base.git
  n8n-nodes-base.gitTool

remove runtime package:
  git

allow apk dependency cleanup to remove:
  pcre2
  git-init-template
  and only dependencies proven exclusive to removed git capability
```

Required proof:

```text
frozen workflows contain neither Git nor Git Tool node
export:nodes:
  n8n-nodes-base.git = ABSENT
  n8n-nodes-base.gitTool = ABSENT
  httpRequest and all frozen-required nodes remain PRESENT

runtime package inventory:
  git = ABSENT
  pcre2 = ABSENT
  CVE-2026-89161 = ABSENT
  CVE-2026-89157 = ABSENT

shared_non_git_runtime_removed = []
or an explicit machine-derived list proving every removed package is
Git-exclusive and not required by frozen runtime/workflows
```

After removal, all existing n8n version/import/order/recovery runtime smokes must
still pass.

Forbidden:

```text
manual pcre2 library copy
Alpine edge repository mixing
third-party package repository
scanner ignore
SiteScore-authored VEX
CVE-2026-89161 residual waiver
```

If Git capability pruning breaks a frozen workflow/runtime dependency, stop with
one true blocker; do not silently restore pcre2 as a residual.

### C. Application CVE-2026-82049 — EXACT TEMPORARY RESIDUAL AUTHORIZED

Correction to Implementer handoff wording:

The actual API and Commerce runtime Dockerfiles and immutable base lock are:

```text
python:3.11.16-slim-trixie
sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
DEBIAN_SUITE=trixie
```

The workflow-level `PYTHON_IMAGE=python:3.11.16-slim-bookworm...` is a CI
helper/replay image and is NOT the scanned API/Commerce runtime base.

CVE-2026-82049 concerns CPython `tarfile` extraction filters and crafted tar
archives involving hard links to symlinks.

Reviewer live repository search against the frozen application source found:

```text
tarfile = no application-source matches
extractall = no application-source matches
shutil.unpack_archive = no application-source matches
zipfile = used for GTFS ZIP parsing, not tarfile extraction
```

Python upstream status at this decision point:

```text
Python 3.11.16 is the current 3.11 security release
CVE-2026-82049 was disclosed after 3.11.16
the upstream issue is gh-157190
main and 3.13 fixes exist
3.12 backport is still open
no published fixed 3.11.x release is available
scanner's 3.14.0b1 suggestion is NOT an acceptable same-series production upgrade
```

Therefore this ONE application finding may be treated as an exact,
reachability-constrained residual rather than forcing Python 3.14 beta or
patching CPython locally.

Authorized residual ID only:

```text
CVE-2026-82049
package = CPython 3.11.16
classification = REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

Implementer must create/update a dedicated application security residual record
and CI evidence proving:

```text
raw Grype finding remains visible
CISA KEV = 0
runtime application source contains no:
  import tarfile
  from tarfile
  tarfile.extract
  extractall
  shutil.unpack_archive

no public API route accepts tar/tar.gz archive extraction
no runtime smoke invokes tarfile extraction
API 114 PASS
report 24 PASS
Commerce 416 PASS + exactly one authorized deselect
FAZ6 Commerce replay 417 PASS
```

Expiry/re-review trigger:

```text
FIRST OF:
- a fixed Python 3.11.x security release becomes available
- CPython merges/publishes a 3.11 backport suitable for the official runtime
- application introduces any tar/tar.gz ingestion/extraction path
- before PUBLIC_LAUNCH authorization
```

At that trigger this residual automatically reopens; it is not a permanent
waiver.

Forbidden:

```text
Python 3.14 beta migration
local CPython source patch in this checkpoint
scanner suppression/ignore
generic Python-HIGH waiver
SiteScore-authored VEX
```

### D. Existing exact n8n residual set remains bounded

The previously authorized exact residuals remain permitted only with their
existing containment/evidence:

```text
nodemailer:
  GHSA-p6gq-j5cr-w38f
  GHSA-2x7j-588g-ccc2

@tiptap/core:
  GHSA-j95f-988m-3j2f

zlib:
  CVE-2026-85091
```

pcre2 residuals are expected to DISAPPEAR entirely after Git capability pruning.

No additional HIGH/CRITICAL residual is authorized.

### E. Final exact-head security acceptance

After this one consolidated continuation:

```text
CISA KEV = 0
actionable CRITICAL = 0
actionable/remediable OS HIGH = 0
adm-zip GHSA-7q85-xj36-vmfc = 0
pcre2 CVE-2026-89161 = 0
pcre2 CVE-2026-89157 = 0
fast-uri/brace-expansion/ip-address/Snowflake/TOML findings = 0
NEW_UNDISPOSITIONED_HIGH = 0

application residuals:
  ONLY CVE-2026-82049 under the exact temporary record above

n8n residuals:
  ONLY the exact previously authorized nodemailer/tiptap/zlib records
```

All raw scanner reports remain preserved. No threshold weakening.

### F. Anti-loop / next handoff

Implementer is authorized to complete all mechanical consequences of:

```text
adm-zip 0.6.1 lock regeneration
Git capability exclusion
git/pcre2 runtime package pruning
residual-risk record generation
CI evidence classification
artifact formatting
runtime/static smoke repairs caused only by these exact changes
```

without another Reviewer round trip.

Next Implementer handoff must be either:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

with one exact final green head/run,

or ONE consolidated true blocker outside the authority above.

Final GitHub owner-governance configuration remains a separate last gate after
technical required-gate GREEN.

---

## 0B. Superseding Reviewer security decision — bounded remediation reopen

### Trigger

Exact-head security artifact:

```text
head = f1420f40de52db19dd947ec67411202ee8c9ab71
run = 35403633443
n8n-validation job = 105788708568
artifact = faz7-n8n-final-evidence-f1420f40de52db19dd947ec67411202ee8c9ab71
artifact id = 10572440379
artifact sha256 = 5aa75bbb3db7efee196ee52e2753db3e12b3a4a36fe6bdcbc4cb52cdbf03fb36
```

The mechanical runtime-evidence issues are resolved. The terminal gate now exposes
real inherited/remediable security findings:

```text
CISA KEV = 0
BLOCKING_CRITICAL = 2
OS_HIGH = 10
OTHER_HIGH = 24
NEW_HIGH = 0
```

The two CRITICAL findings are both `libcurl 8.21.0-r0` and have a scanner-fixed
version `8.22.0-r0`.

This satisfies the terminal-closure emergency security reopen condition. The
Reviewer therefore authorizes ONE consolidated security remediation pass.
Routine moving-latest n8n reselection remains prohibited.

### Frozen application/n8n identity that MUST NOT change

```text
n8n version = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
workflow hashes = unchanged
application/business semantics = unchanged
Snowflake/TOML pruning = unchanged
```

### A. Upstream-aligned Node/DHI security-base refresh — AUTHORIZED

Reviewer verified current n8n upstream master uses:

```text
builder:
node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019

DHI base:
dhi.io/node:26.7.0-alpine3.24-dev@sha256:4b494d89fb26c950ce97865acf45b480dc7a6868fdc2b81c2d66599702eeac3f

upstream runtime reference:
n8nio/base:26.7.0@sha256:33687300c4e94dc00f42ec79ae15082ae07330ecd82ae1167125905b65908ff8
```

The frozen n8n 2.37.10 source MAY be rebuilt on this exact upstream-aligned
Node 26.7.0 / Alpine 3.24 toolchain/base pair. This is a security-base refresh,
not a moving n8n release rebase.

Required proof:

```text
Node major remains 26
Alpine remains 3.24
linux/amd64
all base references immutable by digest
n8n --version = 2.37.10
source commit/tree unchanged
full runtime/workflow/import/export smoke PASS
SBOM + Grype regenerated
```

First run the final scan after this base refresh BEFORE adding further OS package
surgery. The refresh is expected to absorb the libcurl and bundled-npm findings
where upstream base packaging has already moved.

### B. OS package remediation — targeted only

If the refreshed exact DHI base still contains remediable CRITICAL/HIGH Alpine
packages, Implementer MAY update only the specifically affected runtime package
families from the same Alpine 3.24 repositories.

Rules:

```text
NO blanket apk upgrade
NO distro change
NO third-party repository
NO manual copied libraries
NO scanner ignore/suppression
NO SiteScore-authored VEX
```

For each targeted package, record before/resolved-after version and repository
source in evidence. If repository resolution is used during discovery, freeze
the first green resolved versions into deterministic build evidence/lock.

Known priority:

```text
libcurl >= 8.22.0-r0 or vendor-backported fixed equivalent
pcre2 = fixed/backported Alpine 3.24 build if available
zlib = fixed/backported Alpine 3.24 build if available
```

CVE-2026-89157 is 32-bit-specific; the product target is linux/amd64. It may be
classified in the separate Reviewer risk record as architecture-not-affected
ONLY with the raw finding retained and external advisory evidence recorded.
Do not encode that as a SiteScore-authored VEX.

CVE-2026-89161 remains remediation-required if a fixed/backported package exists.

For CVE-2026-85091, if no fixed Alpine 3.24 package exists at the final exact-head
snapshot, the raw scanner finding MUST remain visible and may be classified only
as:

```text
REVIEWER_ACCEPTED_UPSTREAM_UNFIXED_RESIDUAL
```

with all of:

```text
CISA KEV = 0
severity/reachability note
upstream/vendor no-fix evidence
owner = FAZ7 security review
expiry/re-review trigger = package fix publication OR before public launch
```

This is an explicit risk record, not a VEX assertion and not scanner suppression.

### C. npm dependency remediation — upstream-aligned first

Reviewer verified current n8n upstream master already carries these security
versions/policies:

```text
fast-uri = 3.1.6
ip-address@10 = 10.3.1
brace-expansion@5 = 5.0.9
js-yaml = 4.3.2
multer = ^2.3.0
```

Implementer MAY backport these exact upstream-aligned dependency changes into the
frozen 2.37.10 build graph, regenerate the lock deterministically, and prove no
unrelated version churn.

Important artifact observation:

```text
brace-expansion 5.0.8 finding path = /usr/lib/node_modules/npm/...
ip-address 10.2.0 finding path = /usr/lib/node_modules/npm/...
```

Those two findings are bundled-npm/base-image findings, not proof that the
frozen n8n graph override failed. Prefer the Node/DHI refresh to remediate them.
If they remain only in bundled npm and npm is not required by the final SiteScore
runtime, removal of bundled npm/npm-cli from the FINAL runtime image is authorized
only after proving:

```text
n8n startup PASS
n8n export:nodes PASS
both frozen workflow imports PASS
order-paid/recovery runtime smokes PASS
no SiteScore production contract requires community-node installation
```

Do not remove Node itself or pnpm/build tooling from build stages merely to hide
findings.

### D. Additional patch/minor backports with fixes

Current scanner fixes include:

```text
@xmldom/xmldom 0.8.14 -> 0.8.15
js-yaml 4.3.1 -> 4.3.2
multer 2.2.0 -> 2.3.0
```

`@xmldom/xmldom 0.8.15` is authorized ONLY if production-graph proof shows
every direct parent/range remains compatible and no peer-contract conflict is
introduced.

For every local npm backport:

```text
pnpm why --prod evidence
parent-range proof
lock diff limited to required closure
no unrelated package version change
n8n source files unchanged
full runtime/workflow smoke PASS
```

### E. Tiptap and Nodemailer — no unauthorized major/family leap

Current n8n upstream master still retains:

```text
@tiptap/core = 3.27.0
nodemailer = 8.0.10
@xmldom/xmldom = 0.8.14
```

Therefore:

```text
DO NOT locally force nodemailer 9.x
DO NOT partially bump only @tiptap/core to 3.30.5 while its exact peer family remains 3.27.0
DO NOT apply source patches to n8n/tiptap/nodemailer
```

The two exact nodemailer HIGH advisories may remain as Reviewer-accepted residual
risk ONLY if the established containment proof remains true:

```text
n8n-nodes-base.emailSend = excluded
frozen workflows contain no emailSend
no SMTP/N8N_EMAIL_MODE/N8N_SMTP transport configured
editor/admin/API not publicly exposed
no alternate workflow path exposes arbitrary nodemailer message construction
raw Grype findings remain visible
risk record lists BOTH exact advisory IDs and fixed-version triggers
re-review before public launch or on upstream n8n adoption
```

Allowed nodemailer residual IDs for this checkpoint only:

```text
GHSA-p6gq-j5cr-w38f
GHSA-2x7j-588g-ccc2
```

The `@tiptap/core` HIGH may remain only if Implementer proves it is confined to
the non-public editor/UI surface and frozen automation workflows/public webhook
paths do not execute the vulnerable Markdown attribute parser. Record the exact
advisory `GHSA-j95f-988m-3j2f`, raw finding, containment, and re-review trigger.
No generic Tiptap-family waiver is authorized.

If that reachability/containment proof cannot be made, stop with ONE consolidated
security blocker rather than performing an unreviewed Tiptap family upgrade.

### F. Final security gate after this pass

The final exact-head report MUST preserve raw scanner output and separately show
the dispositioned policy result.

Required:

```text
CISA KEV = 0
CRITICAL actionable = 0
remediable OS HIGH = 0
fast-uri vulnerable findings = 0
Snowflake/TOML findings = 0
no NEW undispositioned HIGH
no scanner suppression
no blanket ignore
no SiteScore-authored VEX
```

Only exact, documented residuals explicitly authorized above may survive, with
raw findings retained:

```text
nodemailer:
  GHSA-p6gq-j5cr-w38f
  GHSA-2x7j-588g-ccc2

optional only with proof:
  GHSA-j95f-988m-3j2f (@tiptap/core editor-only containment)
  CVE-2026-89157 (amd64 architecture-not-affected)
  CVE-2026-85091 (upstream-unfixed residual)
```

No other HIGH/CRITICAL residual is authorized.

### G. Anti-loop instruction

Implementer is authorized to perform the base refresh, targeted package fixes,
graph-proven npm backports, evidence/risk-record updates and all resulting
mechanical CI repairs in ONE continuation.

Do not stop for:

```text
Dockerfile syntax
lock regeneration
pnpm/yaml mechanics
artifact path issues
test harness timing
scanner evidence formatting
package-version discovery within the bounds above
```

Stop only for:

```text
a fixed dependency requires a parent-major/source change outside this authority
a remaining CRITICAL has no bounded remediation
a remaining HIGH is outside the exact residual list above
DHI entitlement/auth fails
final GitHub owner-governance action
```

Next Implementer handoff must be terminal:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

or one consolidated true blocker.

---

## 0A. Superseding Reviewer decision — authenticated type-file root cause

Exact-head run:

```text
head = 1992bdd8f74a736ba7ee129d4d89a0c011386a76
run = 35399578554
n8n-validation job = 105776153483
```

Result:

```text
source-boundary       = PASS
static-contracts      = PASS
container-validation = PASS
faz6-commerce-replay  = PASS
DHI authentication   = PASS
hardened n8n image build = PASS
n8n-validation        = FAIL at node-type runtime evidence
required-gate         = FAIL only because n8n-validation failed
```

Uploaded final evidence artifact:

```text
artifact id = 10570901495
artifact sha256 = b26ccbe06134adf20562c694ced09f611eae4509095ce9e74f7ca4b6d8dccc72
```

Evidence proves n8n itself completed migrations, registered the JS task runner, reported version 2.37.10, completed workflow dependency indexing, and exposed the editor. The captured unauthenticated `/types/nodes.json` body remained:

```text
n8n is starting up. Please wait
```

Reviewer verified the exact frozen upstream source commit
`5542b8b6419cb6925cca8f11b270c9bfbe09d85e`:

- `packages/cli/src/server.ts` explicitly wraps
  `/types/nodes.json`, `/types/credentials.json`, and `/types/node-versions.json`
  in `AuthService.createAuthMiddleware(...)`.
- Therefore an unauthenticated `curl /types/nodes.json` is not a valid terminal runtime inventory contract for this frozen release.
- The same exact frozen source provides the official command
  `n8n export:nodes --output <path>`, implemented by
  `packages/cli/src/commands/export/nodes.ts`, which loads node types through
  `LoadNodesAndCredentials`.

Classification:

```text
CLASSIFICATION: MECHANICAL_EVIDENCE_IMPLEMENTATION_DEFECT
NEW_DESIGN_DECISION_REQUIRED: NO
EMERGENCY_SECURITY_REOPEN: NO
N8N_CANDIDATE_RESELECTION_REQUIRED: NO
```

Authorized remediation is narrow:

```text
REMOVE:
unauthenticated /types/nodes.json polling as the node inventory proof

KEEP:
healthz/startup runtime smoke
frozen n8n 2.37.10 identity
frozen DHI runtime digest
Snowflake/TOML pruning
NODES_EXCLUDE
all existing security thresholds
workflow hashes
application/business semantics

ADD/USE:
official frozen-runtime command:
n8n export:nodes --output <temporary evidence path>

PROVE FROM EXPORTED INVENTORY:
n8n-nodes-base.httpRequest = PRESENT
n8n-nodes-base.snowflake = ABSENT
n8n-nodes-base.emailSend = ABSENT
n8n-nodes-base.executeCommand = ABSENT
n8n-nodes-base.localFileTrigger = ABSENT
```

The export must execute from the final hardened candidate image with the frozen
`NODES_EXCLUDE` environment in force. The evidence path/output may be temporary
or artifact-only. Do not create an owner account, do not bypass authentication,
do not weaken authentication, and do not expose editor/admin/API surfaces merely
to read type files.

The prior wait-time increases were diagnostic mechanics only; do not increase
the HTTP polling timeout again. Continue directly to one exact-head terminal CI
run after this replacement.

Next Implementer handoff remains terminal-only:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

or a true design/security/owner-governance blocker.

---

## 0. Live reviewer observation — exact head 044cd95

Live PR #34 has advanced beyond the prior handoff to exact head:

```text
044cd95aadf170e44e7ee8d823e7735509a4539f
run = 35288901923
```

The delta from `1a01ec7de87692fc5d12b8520357d41a5d4dd14e` is confined to `deploy/containers/n8n-frozen-candidate-ci.sh`; no frozen application or n8n workflow JSON path changed.

Current exact-head jobs observed by Reviewer:

```text
source-boundary       = PASS
static-contracts      = PASS
container-validation = PASS
faz6-commerce-replay  = PASS
DHI authentication   = PASS
n8n-validation        = IN_PROGRESS at frozen source-build/hardening/security gate
required-gate         = pending n8n-validation
```

No new design/security decision is required at this observation point. Do not introduce further code churn unless this exact-head run produces a concrete terminal failure requiring remediation.

---

## 1. Exact-head state

Live PR #34 remains on exact head:

```text
1a01ec7de87692fc5d12b8520357d41a5d4dd14e
```

Latest exact-head rerun remains run:

```text
run = 35156778651
source-boundary = PASS
static-contracts = PASS
FAZ6 Commerce replay = PASS (417)
container-validation = PASS
n8n-validation = FAIL
required-gate = FAIL only because n8n-validation failed
```

The historical DHI owner-secret blocker is now RESOLVED. Exact job `105159800082` proves the permanent DHI authentication step passed and the frozen DHI digest was successfully pulled.

The n8n job then completed the exact frozen 2.37.10 source build and Snowflake/TOML pruning successfully:

```text
n8n source build = PASS
snowflake-sdk@2.1.0 = REMOVED
toml@3.0.0 = REMOVED
shared_non_snowflake_removed = []
version_changes = []
```

The first failing operation is later, while assembling the hardened DHI runtime base:

```text
apk add --no-cache busybox-binsh

installed/base busybox:
  busybox-1.38.0_git20260724-r5

repository busybox-binsh candidate:
  busybox-binsh-1.37.0_git20260817-r33
  requires busybox=1.37.0_git20260817-r33

result:
  package solver conflict
  exit code = 1
```

This is a MECHANICAL IMPLEMENTATION DEFECT, not a new security/design blocker. The build command itself is already executing under `/bin/sh` before the attempted `busybox-binsh` installation, so the explicit installation is redundant for this exact DHI base.

Reviewer decision:

```text
OPS71-N8N-VULN-001:
MECHANICAL_BUSYBOX_BINSH_PACKAGE_CONFLICT_REMEDIATION_AUTHORIZED

NEW_DESIGN_DECISION_REQUIRED: NO
EMERGENCY_SECURITY_REOPEN: NO
```

Authorized remediation is narrowly bounded:

```text
REMOVE ONLY:
apk add --no-cache busybox-binsh && \\

KEEP UNCHANGED:
frozen n8n 2.37.10 identity
frozen DHI runtime digest
Snowflake/TOML pruning
libcrypto3/libssl3/libexpat exact security pins
openssh/graphicsmagick removal
NODES_EXCLUDE contract
security thresholds
workflow hashes
application/business behavior
```

Do not replace the DHI base, do not pin a mismatched BusyBox family, and do not weaken the security gate. Implementer is authorized to perform this mechanical edit and continue directly to terminal CI without another Reviewer round trip unless a true design/security blocker appears.

---

## 2. Trixie bounded refresh is implemented

The Reviewer-authorized Bookworm → Trixie emergency expansion has been consumed on the live PR branch.

Current immutable application base lock is:

```text
PYTHON_IMAGE_TAG=python:3.11.16-slim-trixie
PYTHON_IMAGE_DIGEST=sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
PYTHON_IMAGE=python:3.11.16-slim-trixie@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
TARGET_PLATFORM=linux/amd64
DEBIAN_SUITE=trixie
DEBIAN_SECURITY_SUITE=trixie-security
DEBIAN_SNAPSHOT=20260916T000000Z
```

The exact-head workflow has already passed image build, non-root/read-only runtime proof, and the API/report/Commerce applicable regression step. Source-boundary also proves frozen application/workflow source boundaries remain intact.

Terminal application acceptance remains unchanged:

```text
API = 114 PASS
report = 24 PASS
Commerce = 416 PASS + exactly 1 authorized deselect
FAZ6 Commerce replay = 417 PASS
linux/amd64 = PASS
non-root/read-only = PASS
API web/worker/beat = PASS
Commerce web/dispatcher = PASS
PDF/font = PASS
CISA KEV = 0
CRITICAL = 0
OS HIGH = 0
no new undispositioned HIGH introduced by refresh
SBOM/Grype/image-hygiene evidence = COMPLETE
```

The first fully green exact Trixie candidate becomes frozen. Do not chase later routine base refreshes after that point.

---

## 3. DHI owner action is resolved

Repository Actions credentials are now present and the exact-head rerun proves:

```text
Authenticate frozen DHI runtime registry = PASS
dhi.io token exchange = PASS
frozen DHI metadata/pull = PASS
```

Therefore:

```text
OPS71-N8N-DHI-001: RESOLVED_AUTHENTICATED_PULL_PASS
```

No further owner credential action is required for the current frozen candidate. Do not expose, rotate, commit, print, or otherwise alter the credentials as part of this mechanical remediation.

---

## 4. Frozen n8n authority remains unchanged

```text
n8n = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
Snowflake/TOML resolution = graph-proven unused-capability pruning
```

Required post-prune state:

```text
n8n-nodes-base@2.37.4 = PRESENT
snowflake-sdk@2.1.0 = ABSENT
toml@3.0.0 = ABSENT
shared_non_snowflake_removed = []
NODES_EXCLUDE retains executeCommand/localFileTrigger/emailSend/snowflake
```

The exact previously-authorized nodemailer residual HIGH may remain only if it is still the sole residual HIGH and all established containment controls are proven. No second residual CRITICAL/HIGH exception is authorized.

Forbidden:

```text
moving-latest n8n restart
weaker anonymous runtime-base fallback
scanner suppression / blanket CVE ignore
SiteScore-authored VEX waiver
incompatible TOML override
parent-source feature patch
frozen application/business semantic change
frozen n8n workflow JSON change
self-hosted/alternative CI
credential commit
```

---

## 5. Terminal completion contract

Implementer must now apply the single authorized BusyBox mechanical remediation and continue to one terminal handoff without returning for ordinary mechanics:

```text
[ ] application Trixie vulnerability policy GREEN
[ ] DHI authenticated pull PASS
[ ] frozen n8n hardened runtime build PASS
[ ] Snowflake/TOML final inventory exact
[ ] n8n workflow hashes/import/static/runtime smoke PASS
[ ] n8n security gate PASS under existing residual-risk contract
[ ] n8n SBOM/Grype/OpenVEX/provenance complete
[ ] API 114 PASS
[ ] report 24 PASS
[ ] Commerce 416 PASS + exactly 1 deselect
[ ] FAZ6 replay 417 PASS
[ ] source-boundary PASS
[ ] static-contracts PASS
[ ] container-validation PASS
[ ] n8n-validation PASS
[ ] faz7 / required-gate PASS on one exact final HEAD
[ ] temporary diagnostics absent
[ ] frozen application source diff NONE
[ ] frozen n8n workflow diff NONE
[ ] cloud/IaC mutation NONE
[ ] production secret commit NONE
```

Next Implementer handoff must be `READY_FOR_REVIEW`, except only a proven DHI entitlement blocker, emergency security reopen, or final owner-governance action.

---

## 6. Governance remains final gate

After the technical required-gate is fully green, enforce/verify:

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

Do not start FAZ 7.2 and do not merge before exact-head Reviewer `READY_TO_LOCK` plus literal user `LOCK` in the Implementer flow.

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


### Live superseding observation — 2026-09-19

Current PR #34 exact head has advanced to:

```text
1992bdd8f74a736ba7ee129d4d89a0c011386a76
run = 35399578554
```

Current exact-head state:

```text
source-boundary       = PASS
static-contracts      = PASS
container-validation = PASS
faz6-commerce-replay  = PASS
DHI authentication   = PASS
n8n-validation        = IN_PROGRESS
required-gate         = pending n8n-validation
```

The delta from the prior observed head is confined to `deploy/containers/n8n-frozen-candidate-ci.sh`; current commit only extends the bounded node-types readiness wait for n8n migrations. No frozen application or workflow JSON change is introduced. No new design/security decision is required while this exact-head run is active.
