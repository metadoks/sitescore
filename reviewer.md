# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-7
CHECKPOINT_TITLE: COMB-005 Road + Parking Composite Gating Foundation
REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 8bfe2eb92ea3d52f30d14a4333927f76f8630b0a
CODE_BRANCH: faz3.4/cp3.4-7-comb005-road-parking
REVIEWED_HEAD_SHA: d312a6de6afae51a65b67b6bd15b3770acdfb048
PR: #4
CONTRACT_CHANGE_REQUIRED: 0
```

---

# 1. REVIEW DECISION

```text
FAZ 3.4-7
Decision: HARDENING REQUIRED
PR: #4
Reviewed HEAD: d312a6de6afae51a65b67b6bd15b3770acdfb048
```

The canonical `evaluate_road_parking_composite()` gate is correctly unavailable under the unapproved V1 policy, but public constructor surfaces still allow caller-authored approval and caller-authored AVAILABLE final artifacts. That violates the checkpoint's anti-self-authorization / anti-self-assertion invariant.

No merge or LOCK is authorized.

---

# 2. VERIFIED CLEAN AREAS

Reviewer independently verified that the following are otherwise preserved at the reviewed HEAD:

- canonical `COMB005_V1_POLICY` is `NOT_APPROVED`, weightless, and `UNRESOLVED`;
- canonical approved-policy registry is empty;
- canonical helper emits `POLICY_NOT_APPROVED` and `score=None`;
- road/off-street/curb semantics remain distinct;
- no implicit 50/50, neutral fill, available-side renormalization, road-only or parking-only canonical fallback exists;
- locked 3.4-6 direct normalization registry remains unchanged for road/parking;
- no production road scalar reduction was invented;
- no whole `NormalizedLocationFeatures`, readiness, CategoryScores, Location Score, or `core.analyze()` leakage exists;
- dependency DAG remains unchanged;
- validated SHA `5b85abaf56e5981dd6601f6edaf2e85081d1d679` → review HEAD `d312a6de6afae51a65b67b6bd15b3770acdfb048` differs only by removal of `.github/workflows/cp347-validation.yml`.

The blockers below are therefore narrowly scoped to authority / constructability integrity.

---

# 3. COMB-H001 — PUBLIC POLICY APPROVAL IS CALLER-SPOOFABLE

## Problem

`sitescore_benchmarks.__init__` imports `composite` with `from .composite import *`, so `RoadParkingCompositePolicy` and `RoadParkingPolicyApprovalState` are public package API.

`RoadParkingCompositePolicy.__post_init__` accepts any caller-created policy with:

```text
approval_state = APPROVED
composition_method = WEIGHTED_LINEAR_SUM_NO_SUBSTITUTION
caller weights summing to 1
```

There is no canonical approval authority/token/registry membership check in that constructor.

Therefore a caller can publicly construct an apparently `APPROVED` COMB-005 policy with arbitrary weights even though the architecture explicitly says no empirical COMB-005 policy is approved.

The current canonical helper does not accept that policy, but the public policy object itself falsely represents approval authority and can be consumed by other public/publicly reachable artifact paths.

## Required correction

Make it impossible for ordinary production callers to manufacture an approved COMB-005 policy while the canonical approved registry is empty.

Acceptable additive patterns include, for example:

- public production policy constructor rejects `APPROVED` unless construction is tied to an actual canonical approved registry artifact/authority that currently does not exist; or
- split controlled synthetic test policy machinery into a private/test-only contract that is not exported or usable as production approval authority; or
- use an unforgeable/internal approval authority object derived only from an approved registry entry.

Do not merely rename the constructor or rely on underscore convention while leaving the same public package export/reachable authority semantics.

Current canonical state must remain:

```text
no approved empirical policy
no production weight vector
no caller-created APPROVED policy authority
```

## Required regression

Add a public-API adversarial test proving that a caller using only exported production symbols cannot construct an `APPROVED` COMB-005 policy with arbitrary weights while the canonical approved registry is empty.

The existing test that only checks `evaluate_road_parking_composite()` parameters is insufficient.

---

# 4. COMB-H002 — PUBLIC AVAILABLE RESULT / COMPONENT STATE CAN BE SELF-ASSERTED

## Problem

`RoadParkingCompositeResult` is also exported publicly through `from .composite import *`.

Its constructor accepts caller-supplied:

```text
policy
components
state
reason_codes
score
```

For `state=AVAILABLE`, validation checks only that:

- the supplied policy says `APPROVED`;
- score is finite and in [0,100];
- reasons are empty.

It does **not** derive/recompute:

- required component completeness;
- duplicate/missing component rules;
- component availability/calibration/incompatibility gates;
- weighted composition result;
- equality between supplied score and actual policy/component math.

Combined with COMB-H001, a caller can publicly create a caller-authored approved policy and then directly instantiate an apparently canonical `AVAILABLE` `RoadParkingCompositeResult` with an arbitrary detached score, bypassing `_compose_with_policy` entirely.

`RoadParkingComponentArtifact` also publicly permits caller-authored `AVAILABLE` components from detached `score` + arbitrary `normalization_lineage_id`, despite there being no canonical approved road/parking component-normalization path yet. This increases the same bypass surface.

This violates the frozen requirement:

```text
Do not trust caller-supplied composite IDs or score values.
approved policy absent -> road_parking_access_score cannot be canonically produced
```

## Required correction

Production-facing COMB-005 result construction must derive availability/state/reasons/score from actual approved policy authority and actual component artifacts; callers must not be able to self-assert an AVAILABLE final artifact by passing state/score fields.

At minimum:

1. eliminate or hard-gate direct public construction of an AVAILABLE production result;
2. ensure final score is recomputed/derived from actual policy + complete actual components, never trusted from caller input;
3. ensure required component completeness and component states are checked on every production-available construction path;
4. while no approved canonical policy exists, exported production API must have no path to produce an AVAILABLE `road_parking_access_score` artifact;
5. do not use detached arbitrary component `score`/lineage as production authority where no canonical normalized road/parking component exists. Controlled synthetic fixtures may remain private/test-only and clearly non-production.

Do not weaken the existing current-state truth: road remains unresolved and production COMB-005 remains unavailable.

## Required regressions

Add adversarial tests proving exported production API cannot:

- directly instantiate an AVAILABLE final result with arbitrary score;
- use a caller-created approved policy to create an AVAILABLE result;
- produce AVAILABLE with missing/duplicate/nonavailable components through any public constructor/factory path;
- fabricate canonical AVAILABLE component prerequisites from detached scores when no approved canonical component-normalization path exists, unless those artifacts are explicitly typed/non-production and cannot enter canonical production composition.

Also retain existing controlled fixture tests for composition math, but move/shape them so they cannot serve as production authority.

---

# 5. HARDENING SCOPE

Harden only the authority/constructability surface described by COMB-H001 and COMB-H002.

Do not:

- invent production weights;
- approve COMB-005;
- invent road or parking scalar reductions;
- change locked 3.4-6 normalization semantics;
- add readiness/pipeline/category/core work;
- modify frozen upstream package source;
- broaden dependencies.

Keep `CONTRACT_CHANGE_REQUIRED = 0` unless additive correction proves genuinely impossible; if so, stop and report exact evidence before mutating frozen contracts.

---

# 6. VALIDATION / RETURN REQUIREMENTS

After hardening:

1. run `sitescore-benchmarks` and all frozen regression packages (`metrics`, `spatial`, `providers`, `data`, `core`);
2. report exact counts only where actually visible;
3. re-run all existing COMB tests plus new public-API bypass tests;
4. update checkpoint documentation to describe the true production approval/result construction authority;
5. if using a temporary validation workflow, remove it and prove successful validated SHA → final HEAD is workflow-removal-only;
6. update PR #4, do not create a new PR;
7. replace `implementer.md` with a detailed hardening report.

Return with:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CHECKPOINT: FAZ 3.4-7
PR: #4
CODE_HEAD_SHA: <new exact SHA>
COMB-H001: RESOLVED / unresolved with evidence
COMB-H002: RESOLVED / unresolved with evidence
CONTRACT_CHANGE_REQUIRED: 0 or exact justified 1
```

Do not merge. Do not self-LOCK. Do not start 3.4-8.
