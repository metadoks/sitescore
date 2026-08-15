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
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 8bfe2eb92ea3d52f30d14a4333927f76f8630b0a
CODE_BRANCH: faz3.4/cp3.4-7-comb005-road-parking
REVIEWED_HEAD_SHA: NONE
PR: NONE
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
```

---

# 1. PREVIOUS CHECKPOINT LOCK VERIFICATION

FAZ 3.4-6 is accepted, user-authorized and merged.

Reviewer independently verified:

```text
PR #3 state: closed
PR #3 merged: true
reviewed branch HEAD: 7b8e4594ba3e58b31ae5163960220832e28b4970
merge/main SHA: 8bfe2eb92ea3d52f30d14a4333927f76f8630b0a
```

Current `main` points to:

```text
8bfe2eb92ea3d52f30d14a4333927f76f8630b0a
```

No checkpoint 3.4-7 branch existed at publication time.

Create exactly one branch from this exact baseline:

```text
faz3.4/cp3.4-7-comb005-road-parking
```

Re-fetch first if repository state changed. Do not reset legitimate work or create a duplicate branch.

---

# 2. CHECKPOINT PURPOSE

Implement only:

```text
FAZ 3.4 — CHECKPOINT 3.4-7
COMB-005 Road + Parking Composite Gating Foundation
```

This checkpoint owns the structural contract around the frozen downstream normalized feature:

```text
road_parking_access_score
```

The core invariant is:

```text
road and parking remain separate real-world evidence/metrics
+
final road_parking_access_score exists only under an explicitly approved calibrated composite policy
```

There is currently no approved empirical COMB-005 weight set.

Therefore this checkpoint must **not invent production weights**.

The checkpoint must establish the typed policy/gating/composition foundation so that:

```text
approved COMB-005 policy absent
→ road_parking_access_score is NOT AVAILABLE / cannot be canonically produced
```

and so that any future approved policy is explicit, versioned, lineage-bound and non-substituting.

---

# 3. FROZEN COMB-005 PRINCIPLE

The frozen architecture says:

```text
road_reachable_area_km2
parking_public_offstreet_capacity
parking_legal_curb_length_m
```

are distinct real-unit inputs/evidence.

The frozen downstream model exposes only one final accessibility subfeature slot:

```text
road_parking_access_score
```

That final composite is calibration-gated.

Forbidden behavior:

```text
road-only -> road_parking_access_score
parking-only -> road_parking_access_score
50/50 road + parking
parking missing -> neutral 50
road missing -> neutral 50
renormalize weights onto available side
silent substitution
hidden default weights
heuristic fallback weights
```

Do not implement any of these.

---

# 4. CURRENT UPSTREAM STATE MUST REMAIN HONEST

Current canonical metric foundation status:

```text
road_reachable_area_km2
→ unresolved / nonnumeric until approved road multi-scale scalar reduction exists

parking_public_offstreet_capacity
→ numeric pass-through candidate

parking_legal_curb_length_m
→ numeric pass-through candidate
```

Checkpoint 3.4-6 intentionally created no direct normalized road or parking feature policies and no `road_parking_access_score`.

Do not alter the locked unresolved road metric merely to make COMB-005 demonstrable.

A structural COMB-005 policy framework may exist while canonical production composition remains unavailable.

Distinguish:

```text
composite semantics structurally defined
!=
approved empirical weights available
!=
inputs currently numerically available
!=
road_parking_access_score ready
```

---

# 5. PACKAGE OWNERSHIP / DEPENDENCY BOUNDARY

Primary implementation should remain additive in:

```text
sitescore-benchmarks
```

because this layer already owns benchmark normalization semantics and the individual normalized feature results introduced by 3.4-6.

Current direct SiteScore dependencies remain:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

Do not add direct:

```text
sitescore-data
sitescore-core
sitescore-providers
sitescore-pipeline
```

dependencies merely for convenience.

Do not mutate frozen upstream package contracts unless truly impossible additively. If impossible, report:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with exact evidence and stop before broadening the DAG.

Expected result is `CONTRACT_CHANGE_REQUIRED = 0`.

---

# 6. WHAT THIS CHECKPOINT SHOULD MODEL

Introduce a minimal explicit COMB-005 semantic family, equivalent in behavior to:

```text
RoadParkingCompositePolicy
RoadParkingCompositeState
RoadParkingCompositeResult
```

Exact names are not frozen.

The design must clearly distinguish at least:

```text
POLICY_NOT_APPROVED
INPUT_NOT_AVAILABLE
INPUT_NOT_ELIGIBLE / INPUT_NOT_CALIBRATED as applicable
AVAILABLE
```

or an equivalent explicit typed state model.

Do not conflate:

```text
policy missing
input missing
input unresolved
input incompatible
```

into one numeric fallback.

---

# 7. APPROVED POLICY MUST BE ACTUAL AUTHORITY

A canonical available composite must require an actual versioned policy object whose identity binds at minimum:

```text
policy id
policy version
required component feature/metric semantics
weight vector or composition parameters
missing-side behavior
calibration/approval state or equivalent authority
output normalized feature key = road_parking_access_score
```

A detached caller string such as:

```text
policy_version="1.0"
```

must not by itself authorize composition.

Likewise, callers must not be able to pass:

```text
approved=True
weights=(0.5,0.5)
```

into a generic canonical function and thereby self-authorize a production composite.

If there is no approved V1 COMB-005 policy in the frozen architecture, the canonical registry for production must contain no approved weight-bearing policy.

It is acceptable to provide a typed unresolved/unapproved policy declaration proving that composition is gated.

---

# 8. NO INVENTED EMPIRICAL WEIGHTS

Do not choose any production weights such as:

```text
0.5 / 0.5
0.7 / 0.3
road 70 / parking 30
sector-specific weights
```

without an already-approved frozen empirical policy.

No such approved weight set currently exists.

Therefore production/canonical COMB-005 should remain unavailable by default.

Synthetic tests may use deliberately noncanonical/private fixtures to test generic composition math only if:

- they cannot be confused with an approved production policy;
- policy approval remains explicit;
- test fixture weights never enter canonical V1 registry;
- production constructors reject unapproved policy use.

Prefer testing gating semantics over inventing unnecessary generic composition machinery.

---

# 9. COMPONENT SEMANTICS

Road/parking evidence must remain separate.

Do not collapse the real-unit metrics into one detached raw number before lineage checks.

If this checkpoint models normalized prerequisites/components, preserve which actual input generated each component.

Potential component families include:

```text
road component
public off-street parking component
legal curb component
```

but do not invent extra final downstream normalized slots.

The only frozen final output target is:

```text
road_parking_access_score
```

Do not add public V1 feature slots such as:

```text
road_access_score
parking_access_score
curb_access_score
```

as if they were part of the frozen downstream feature surface.

Internal typed component artifacts are acceptable if clearly not downstream feature slots.

---

# 10. PARKING SEMANTICS MUST REMAIN DISTINCT

Preserve locked parking distinctions:

```text
parking_public_offstreet_capacity
parking_legal_curb_length_m
```

They are not interchangeable.

Do not treat:

```text
polygon area as capacity
unknown capacity as zero
NoMappedParking as NoParking
private/customer-only parking as public parking
curb length as parking-space count
```

Checkpoint 3.4-7 must not invent a scalar parking reduction unless an approved policy exists.

If a scalar parking component is itself empirically unresolved, represent that explicitly and let COMB-005 remain unavailable.

---

# 11. ROAD SEMANTICS MUST REMAIN DISTINCT

`road_reachable_area_km2` is the frozen real-unit road candidate, but its multi-scale scalar reduction remains unresolved.

Do not create a numeric road normalized component from unresolved road evidence by:

```text
choosing one drive contour arbitrarily
averaging contours
max/min contour selection
area sum
fixed weighted scale reduction
```

unless an already-approved policy exists.

No such approved production reduction currently exists.

Therefore canonical road contribution may remain unavailable.

---

# 12. MISSINGNESS / NO SUBSTITUTION

The composition contract must preserve:

```text
missing != zero
unknown != neutral
unresolved != calibrated
```

If any required component for an approved policy is absent/unavailable/incompatible, the canonical final composite must not silently:

```text
fill 0
fill 50
copy the available side
renormalize remaining weights
```

Instead produce an explicit unavailable/gated result with deterministic reasons.

---

# 13. NORMALIZED INPUT GATE

If an eventual approved COMB-005 policy consumes normalized component values, every actual component accepted as numeric must satisfy explicit structural criteria consistent with the architecture, such as:

```text
finite
0 <= value <= 100
available
eligible
calibrated
correct component identity / lineage
```

Do not accept detached `float` values as the production authority when actual normalization/evidence artifacts exist.

If currently no canonical normalized road/parking component artifacts exist because their reductions are unresolved, do not fabricate them. The correct canonical result is unavailable.

---

# 14. OUTPUT CONTRACT

The final COMB-005 output, when and only when legitimately available under an approved policy, must target exactly:

```text
road_parking_access_score
```

with normalized semantics:

```text
unit = score_0_100
0 <= score <= 100
```

No clamping should hide invalid math.

Do not add rounding, quantization, smoothing or nonlinear transforms unless explicitly part of an approved future policy.

Unavailable COMB-005 must have:

```text
score = None
```

or equivalent nonnumeric state.

Never represent policy-not-approved as score 0 or 50.

---

# 15. IDENTITY / LINEAGE

A canonical COMB-005 result identity should bind, as applicable:

```text
actual policy identity
policy approval/calibration state
required component artifact identities
actual source/normalization lineage for components
output feature key
state
reason codes
score when available
```

If policy changes weights or missing-side semantics, identity must change.

If component lineage changes, result identity must change.

Caller ordering, timestamps, worker ordering and filesystem paths must not affect semantic identity.

Do not trust caller-supplied composite IDs or score values.

---

# 16. CANONICAL PRODUCTION REGISTRY / POLICY STATE

Because no approved empirical COMB-005 weights currently exist, canonical V1 behavior must make this fact impossible to overlook.

Choose one clear pattern consistent with repository style, for example:

```text
COMB005 policy registry has no approved executable policy
```

or

```text
canonical COMB005 policy object explicitly state=UNCALIBRATED / NOT_APPROVED and cannot emit score
```

What is forbidden is a production-looking default policy carrying arbitrary weights.

The public API should make the current canonical state obvious and deterministic.

---

# 17. INTERACTION WITH CHECKPOINT 3.4-6

Do not weaken or rewrite locked 3.4-6 direct feature normalization.

3.4-6 deliberately has no direct normalization entry for:

```text
road_reachable_area_km2
parking_public_offstreet_capacity
parking_legal_curb_length_m
```

Preserve this.

Do not add those raw metrics to `FEATURE_NORMALIZATION_POLICIES_V1` merely to make COMB-005 inputs easy.

If component normalization requires future calibration, model its absence explicitly.

COMB-005 must not bypass 3.4-6 by generating a final score directly from unrelated raw numbers.

---

# 18. INTERACTION WITH FROZEN NormalizedLocationFeatures

The frozen downstream `NormalizedLocationFeatures` contains:

```text
road_parking_access_score: MetricValue
road_parking_composite_policy_version: str | None
```

This checkpoint should produce enough typed lineage/policy status for later adapter/readiness logic to populate those fields honestly.

Do not modify `sitescore-data`.

Do not assemble the complete `NormalizedLocationFeatures` object yet.

That integration/readiness work belongs to 3.4-8.

---

# 19. REQUIRED ADVERSARIAL TEST MATRIX

Add tests at minimum for:

## COMB-001 — no approved policy

Canonical COMB-005 execution with current production registry cannot produce numeric `road_parking_access_score`.

Expected:

```text
explicit POLICY_NOT_APPROVED / equivalent
score is None
```

## COMB-002 — no implicit 50/50

Prove no canonical 50/50 policy exists.

Search/API/registry test should prevent accidental arbitrary default weights.

## COMB-003 — road-only substitution forbidden

Available road side + missing/unavailable parking side cannot yield final composite.

## COMB-004 — parking-only substitution forbidden

Available parking side + missing/unavailable road side cannot yield final composite.

## COMB-005 — no missing-side neutral

Missing side never becomes 50.

## COMB-006 — no renormalization

If a hypothetical approved multi-component fixture expects both sides, missing one side must not renormalize remaining weights to 100%.

## COMB-007 — unresolved road remains unresolved

Current canonical `road_reachable_area_km2` unresolved state cannot be transformed into a numeric road contribution by this checkpoint.

## COMB-008 — parking capacity and curb length remain distinct

Prove they are not silently merged/interchanged.

## COMB-009 — no downstream feature-slot invention

No public `road_access_score`, `parking_access_score`, `curb_access_score` frozen feature slots are added.

## COMB-010 — no caller self-authorization

Canonical API must not accept caller-provided `approved=True`, arbitrary weights or detached final score as authority.

## COMB-011 — identity policy sensitivity

Changing an actual policy identity/weights in a controlled noncanonical fixture changes result identity.

## COMB-012 — identity component sensitivity

Changing component artifact lineage changes result identity.

## COMB-013 — score bounds if controlled available fixture exists

Any deliberately controlled available composite result is finite and within [0,100].

## COMB-014 — no later-scope leakage

No ScoringReadiness, RealDataPipelineResult, CategoryScores, Location Score or `core.analyze()`.

## COMB-015 — canonical production state remains unavailable

After all generic/test helpers exist, assert current canonical V1 COMB-005 still does not emit a production score because approved empirical policy is absent.

---

# 20. TEST / REGRESSION REQUIREMENTS

Run at least:

```text
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Report exact counts where actually visible.

Do not claim counts that were not emitted/verified.

If using a temporary branch-only validation workflow, remove it before final review HEAD and prove by commit comparison that source/tests/docs are unchanged between successful validated SHA and final HEAD.

Do not modify frozen package source merely to make regression tests pass.

---

# 21. ARCHITECTURE / SCOPE GUARDS

Update architecture guards so they continue to prove:

```text
no sitescore-core import
no sitescore-data direct import
no sitescore-providers import
no pipeline/app import
no reverse metrics -> benchmarks dependency
no arbitrary weight constants masquerading as production COMB-005
no readiness/category/core scoring leakage
```

Be careful: tests themselves may contain illustrative controlled fixture weights. Architecture guards should target production source / canonical registry, not falsely reject test-only fixture constants.

---

# 22. DOCUMENTATION

Add a checkpoint record, recommended path:

```text
sitescore-benchmarks/docs/CHECKPOINT_3_4_7_COMB005_ROAD_PARKING.md
```

Document explicitly:

- 3.4-6 locked baseline;
- road and parking remain separate;
- current road unresolved state;
- parking capacity vs curb-length distinction;
- no approved production COMB-005 weights;
- current canonical composite unavailable state;
- policy/gating contracts;
- missing-side behavior = fail/unavailable, never substitution;
- no 50/50;
- no neutral 50;
- no renormalization;
- identity/lineage;
- tests;
- dependency DAG;
- unresolved empirical decision preserved;
- no readiness/core scoring.

Validity claim remains:

```text
Mathematically validated scoring engine; empirical validation pending.
```

Do not imply COMB-005 empirical calibration is complete.

---

# 23. SELF-AUDIT BEFORE HANDOFF

Before reporting READY_FOR_REVIEW, explicitly self-audit:

```text
canonical approved COMB-005 weights invented? NO
50/50 default? NO
road-only substitution? NO
parking-only substitution? NO
missing-side 50? NO
renormalization? NO
road unresolved semantics preserved? YES
parking capacity vs curb distinction preserved? YES
final output target only road_parking_access_score? YES
caller self-authorization path? NONE
current canonical production composite numeric? NO
identity binds actual policy/components? YES
new runtime dependency? NONE expected
frozen upstream mutation? NONE
readiness/core scoring leakage? NONE
```

If any answer differs, fix before handoff or report exact blocker.

---

# 24. IMPLEMENTER HANDOFF REQUIREMENTS

When complete:

1. commit/push the checkpoint branch;
2. open one PR against `main`;
3. do not merge;
4. update `implementer.md` on `ops/reviewer-implementer-handoff`;
5. report exact:
   - base SHA;
   - code HEAD SHA;
   - PR number;
   - changed files;
   - contracts/API surface;
   - canonical COMB-005 production state;
   - whether any approved weights exist;
   - missingness/substitution semantics;
   - identities/lineage;
   - tests/CI;
   - dependency/DAG audit;
   - unresolved empirical decisions;
   - self-audit;
   - `CONTRACT_CHANGE_REQUIRED`.

Final implementer state must be:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

Do not write `READY_TO_LOCK` or `LOCKED`.

---

# 25. STOP CONDITION

Do not start checkpoint 3.4-8.

Do not implement scoring readiness, full `NormalizedLocationFeatures` assembly, `RealDataPipelineResult`, CategoryScores, Location Score or `core.analyze()`.

Stop after PR + `implementer.md` handoff.

# END — FAZ 3.4-7 IMPLEMENTATION INSTRUCTION
