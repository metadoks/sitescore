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
REVIEWER_STATE: TRUE_BLOCKERS_DECIDED_BOUNDED_TRIXIE_AND_DHI_OWNER_ACTION
IMPLEMENTER_ACTION: APPLY_BOUNDED_TRIXIE_REFRESH_WIRE_DHI_AUTH_AND_COMPLETE_TO_TERMINAL_HANDOFF
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: f531d0612961bfe099ef9f1e1429dd2c0b9a435e
REVIEWED_HEAD_SHA: NONE

LIVE_FAZ7_RUN: 34608218961
LIVE_CONTAINER_VALIDATION_JOB: 103291835180
LIVE_N8N_VALIDATION_JOB: 103291835247

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: CONTINUE_FROZEN_2_37_10_SNOWFLAKE_PRUNING
OPS71-APP-BASE-001: EMERGENCY_REOPEN_D_TRIXIE_REFRESH_AUTHORIZED
OPS71-N8N-DHI-001: OWNER_EXTERNAL_REGISTRY_CREDENTIAL_ACTION_REQUIRED

FAZ71_CANDIDATE_CUTOFF_DATE: 2026-09-07
FAZ71_N8N_CANDIDATE_VERSION: 2.37.10
FAZ71_N8N_SOURCE_COMMIT: 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
FAZ71_N8N_SOURCE_TREE: 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
FAZ71_N8N_OFFICIAL_AMD64_DIGEST_REFERENCE: sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
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

## 1. Decision scope

The Implementer terminal blocker handoff at exact PR head
`f531d0612961bfe099ef9f1e1429dd2c0b9a435e` is accepted as a true
Reviewer decision point with two independent blockers:

1. the previously authorized Bookworm-only application-base refresh cannot
   satisfy the terminal application-image security target because the
   required fixed package state is not available inside that frozen family;
2. the frozen n8n hardening path uses the exact pinned `dhi.io` runtime base,
   but GitHub Actions currently has no credential path for authenticated DHI
   pulls.

Neither blocker authorizes application/business-semantics changes, n8n
workflow changes, scanner suppression, or a moving-latest restart.

---

## 2. OPS71-APP-BASE-001 — bounded Bookworm → Trixie expansion AUTHORIZED

The FAZ 7.1 Emergency Reopen Rule condition D is satisfied: the candidate
cannot meet the already-frozen security gate safely while remaining inside
the Bookworm-only restriction.

The application-base authority is therefore expanded exactly once from
Bookworm to Debian Trixie under the following hard boundary:

```text
Python family = 3.11.x ONLY
Debian family = trixie / slim-trixie ONLY
architecture = linux/amd64 ONLY
base source = Docker Official Image for Python ONLY
base reference = immutable digest REQUIRED
APT package source = reproducible Debian snapshot strategy REQUIRED
application/business source semantics change = FORBIDDEN
unrelated Python dependency modernization = FORBIDDEN
another distro/family change = FORBIDDEN
blanket apt upgrade detached from reproducible build = FORBIDDEN
scanner suppression / blanket ignore / SiteScore-authored waiver = FORBIDDEN
```

The currently available official `python:3.11.16-slim-trixie` line is an
acceptable candidate family. Implementer MUST resolve the exact immutable
linux/amd64-compatible digest at implementation time, use a deterministic
Trixie snapshot/package input, and prove the full existing runtime/regression
contract.

Required terminal application evidence remains:

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
no new undispositioned HIGH introduced by the refresh
SBOM/Grype/image-hygiene evidence = COMPLETE
```

The first exact Trixie version/digest/snapshot combination that satisfies the
terminal gate becomes frozen for FAZ 7.1. Do NOT chase later ordinary image or
snapshot refreshes after that green evidence unless the existing Emergency
Reopen Rule is independently triggered again.

The old `Bookworm/slim-bookworm only` restriction is superseded only by this
section; all other anti-loop and frozen-application restrictions remain in
force.

---

## 3. OPS71-N8N-DHI-001 — authenticated DHI pull path AUTHORIZED

The frozen n8n candidate remains exactly:

```text
n8n = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
DHI runtime input = exact digest already pinned in deploy/containers/n8n-image.lock
Snowflake/TOML resolution = existing graph-proven capability pruning
```

Do NOT replace the DHI runtime silently with a weaker public runtime image.
The registry-auth failure is an external credential problem, not authority to
reselect n8n or reopen the Snowflake/TOML design.

Implementer is authorized to wire authenticated `dhi.io` access into the
permanent GitHub Actions n8n-validation job using repository/organization
Actions secrets only.

Required credential contract:

```text
registry = dhi.io
username secret reference = DHI_USERNAME
credential/token secret reference = DHI_TOKEN
credential scope = read-only / minimum required pull access
secret values in repository = FORBIDDEN
secret values in logs/artifacts/docs = FORBIDDEN
plaintext command-line token exposure = FORBIDDEN
```

Preferred permanent CI mechanism is the Docker CLI already present on the
runner, for example a non-echoing `docker login dhi.io` using password-stdin,
with `DHI_USERNAME` and `DHI_TOKEN` supplied from `${{ secrets.* }}`. A
third-party login action is unnecessary; if one is used anyway it must obey
the existing full-40-character-SHA pin rule and least permissions.

A missing secret must fail closed before attempting the hardened n8n build.
No fallback to anonymous pull, alternate registry, unpinned image, or weaker
base is authorized.

Owner action is required outside repository contents: create/provide a Docker
credential that can pull the exact frozen `dhi.io` image and store it as the
two GitHub Actions secrets above. Docker account password SHOULD NOT be used
when an access token is available. Organization-owned read-only automation
credentials are preferred where available.

If valid authentication is configured but the exact frozen image remains
inaccessible because the account/organization lacks entitlement, stop once
with:

```text
OPS71-N8N-DHI-001: PLAN_OR_ENTITLEMENT_BLOCKED
```

That is the only DHI-related true blocker authorized for another Reviewer
round trip.

---

## 4. Existing n8n security design remains authoritative

The previously accepted capability boundary remains unchanged:

```text
NODES_EXCLUDE retains:
  n8n-nodes-base.executeCommand
  n8n-nodes-base.localFileTrigger
  n8n-nodes-base.emailSend
  n8n-nodes-base.snowflake
```

Required post-prune state remains:

```text
n8n-nodes-base@2.37.4 = PRESENT
snowflake-sdk@2.1.0 = ABSENT
toml@3.0.0 = ABSENT
shared_non_snowflake_removed = []
no unrelated version change
Snowflake node unavailable at runtime = PASS
```

Existing authorized dependency hardening remains limited to the already
reviewed families. Do not introduce a parent-source patch, incompatible TOML
override, arbitrary package upgrade, scanner suppression, or SiteScore-authored
VEX waiver.

The exact previously-authorized nodemailer residual HIGH may remain only if it
is still the sole residual HIGH and every established containment control is
proven. No second residual CRITICAL/HIGH exception is authorized.

---

## 5. Terminal completion contract — no more partial blocker returns

After the owner provides the two DHI secret values, Implementer MUST continue
through all remaining mechanics in one run/continuation:

```text
[ ] bounded Trixie application refresh implemented and pinned
[ ] application vulnerability policy green
[ ] DHI authenticated pull succeeds without credential disclosure
[ ] frozen n8n 2.37.10 hardened image completes
[ ] Snowflake/TOML post-prune inventory exact
[ ] frozen n8n workflow hashes/imports/static/smokes PASS
[ ] n8n security gate PASS under the existing residual-risk contract
[ ] n8n-image.lock/SBOM/Grype/OpenVEX/provenance evidence complete
[ ] API = 114 PASS
[ ] report = 24 PASS
[ ] Commerce = 416 PASS + exactly 1 deselect
[ ] FAZ6 replay = 417 PASS
[ ] source-boundary PASS
[ ] static-contracts PASS
[ ] container-validation PASS
[ ] n8n-validation PASS
[ ] `faz7 / required-gate` PASS on ONE exact final HEAD
[ ] temporary diagnostic workflows/assets absent
[ ] frozen application source diff = NONE
[ ] frozen n8n workflow JSON diff = NONE
[ ] cloud/IaC mutation = NONE
[ ] production secret commit = NONE
```

Do NOT return for YAML, shell, Docker, snapshot, digest-resolution, test,
artifact, evidence, or quoting mechanics. Resolve those mechanically.

Do NOT reselect n8n because a routine post-cutoff release exists.
Do NOT restart scanning against moving future timestamps after the first exact
green terminal snapshot.
Do NOT start FAZ 7.2.
Do NOT merge.

---

## 6. Governance remains the final gate

Once technical CI is completely green, verify/enforce exactly:

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

If available GitHub authority cannot apply those settings, return once with
one consolidated owner-governance action. Do not reopen technical work.

---

## 7. Required next handoff

The next Implementer handoff after DHI owner credential configuration MUST be
exactly one of:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

with one exact final HEAD and complete evidence; or, only if actually proven:

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

for `OPS71-N8N-DHI-001: PLAN_OR_ENTITLEMENT_BLOCKED`, an Emergency Reopen Rule
condition, or the final consolidated GitHub owner-governance action.

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
