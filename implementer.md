# SiteScore AI — Implementer → Reviewer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-4
IMPLEMENTER_STATE: WAITING_TO_START
CODE_BRANCH: faz3.4/cp3.4-4-benchmark-distribution
CODE_HEAD_SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
PR: NONE
CONTRACT_CHANGE_REQUIRED: 0
```

---

# Purpose

This file is the canonical Implementer → Reviewer handoff channel.

The Implementer chat must replace this file after each implementation, hardening, or user-authorized LOCK transition with a detailed factual report of what actually happened in GitHub.

The Reviewer will not treat this report as proof. It will independently inspect the exact GitHub PR, source, tests/CI where available, dependency boundaries, and HEAD SHA.

---

# Required report after normal implementation/hardening

Use:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
REPOSITORY: metadoks/sitescore
CHECKPOINT: <checkpoint>
BASE_SHA: <full SHA>
CODE_BRANCH: <branch>
CODE_HEAD_SHA: <full SHA>
PR: #<number>
CONTRACT_CHANGE_REQUIRED: 0 or 1
```

Then document in detail:

1. Changed files.
2. Contracts/classes/functions added or changed.
3. Exact behavior implemented.
4. Completeness / missingness / compatibility semantics.
5. Identity and lineage behavior.
6. Dependency or package metadata changes.
7. Tests executed, package by package, with exact pass counts.
8. Tests not executed and why.
9. Import/DAG audit.
10. Documentation updates.
11. Known unresolved/calibration-gated items intentionally preserved.
12. Self-audit and adversarial cases attempted.
13. Any potential reviewer attention points.

Do not claim `READY_TO_LOCK`, `LOCKED`, or reviewer approval.

---

# Required report after user-authorized LOCK

Only perform a LOCK transition when the user explicitly sends `LOCK` and latest `reviewer.md` says:

```text
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
```

Verify that `REVIEWED_HEAD_SHA` in `reviewer.md` exactly matches current PR HEAD before merging.

After successful transition replace this file with:

```text
IMPLEMENTER_STATE: LOCKED
CHECKPOINT: <checkpoint>
REVIEWED_HEAD_SHA: <full SHA>
PR: #<number>
MERGED_MAIN_SHA: <full SHA>
LOCK_TRANSITION_STATUS: SUCCESS
```

and explain merge method, expected-head-SHA verification, resulting main state, tests known at lock time, any tag/lock-record status, and confirmation that the next checkpoint was NOT started.

If the branch moved after review, do not merge. Write:

```text
IMPLEMENTER_STATE: LOCK_BLOCKED_REVIEW_STALE
```

with both reviewed and current HEAD SHAs.

---

# Current state

No 3.4-4 implementation handoff has been written yet.

On the next user `devam`, the Implementer chat must read the latest `reviewer.md` from this same coordination branch and execute the declared action.
