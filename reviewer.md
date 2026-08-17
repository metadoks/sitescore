# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.3
CHECKPOINT_TITLE: Narrative / Insight Authority Boundary

REVIEWER_STATE: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
CODE_BRANCH: faz5/5-3-narrative-insight-authority
REVIEWED_HEAD_SHA: 1d0e9fd57bda67cece6f17838f73569170066bf0
PR: #19

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED
FAZ_5_1_STATUS: LOCKED
FAZ_5_2_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

BLOCKERS: NARR53-H001
```

---

# 1. EXACT-HEAD REVIEW STATE

Reviewer independently reviewed the live FAZ 5.3 candidate:

```text
PR: #19
state: OPEN
merged: FALSE
mergeable: TRUE
draft: FALSE
base branch: main
base SHA: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
head branch: faz5/5-3-narrative-insight-authority
head SHA: 1d0e9fd57bda67cece6f17838f73569170066bf0
changed files: 9
```

Current `main` remains exactly the locked FAZ 5.2 merge commit:

```text
8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
```

Base-to-head compare:

```text
merge-base = exact locked base
status = ahead
ahead_by = 11
behind_by = 0
changed files = 9
```

Every final product change is under:

```text
sitescore-report/**
```

Scope/dependency direction is otherwise clean. No 5.4+ rendering/PDF/storage/report-resource/payment/n8n scope was found.

Decision:

```text
REVIEW_DECISION: NEEDS_HARDENING
READY_TO_LOCK: NO
LOCK_RESULT: BLOCKED
```

---

# 2. ACCEPTED / NON-BLOCKING PARTS

The following portions are materially aligned with the 5.3 contract and are not the reason for rejection:

```text
sitescore-report==0.2.0
exact locked 5.2 report authority retained
ReportDomainModel is the canonical narrative source gate
ApprovedNarrativeContext is factory-owned and source-bound
ValidatedReportNarrative is factory-owned and source-bound
OpenAI Responses API adapter path exists
structured Pydantic NarrativeDraft is used
provider model ID is configuration/provenance, not analytical truth
tools=[]
store=False
no web/file/MCP/function tools supplied
provider draft remains untrusted before local validation
canonical anchor equality is checked
unknown/missing evidence keys are rejected
numeric literal rule exists
selected decision/financial/confidence contradictions are rejected
provider failures fall back deterministically
invalid canonical ReportDomainModel remains a hard failure
current real NOT_SCORE_READY production truth remains unchanged
no analysis_id/report_id/resource/PDF/storage/payment scope leakage
```

These accepted observations do not override the blocker below.

---

# 3. NARR53-H001 — UNBOUNDED FREE-FORM PROSE CAN GAIN FINAL NARRATIVE AUTHORITY

## Status

```text
NARR53-H001: OPEN
severity: LOCK BLOCKER
category: semantic authority / evidence grounding
```

The contract requires:

```text
canonical ReportDomainModel
-> bounded canonical context
-> untrusted provider draft
-> deterministic semantic validation
-> ValidatedReportNarrative
```

and requires the provider to:

```text
use only supplied facts
never invent missing evidence
bind insights/recommendations to approved evidence
not create new analytical meaning
```

The current implementation does not fully enforce that boundary.

### 3.1 Current evidence check proves key existence, not claim support

Current `validate_narrative_draft(...)` verifies for strengths/risks/recommendations that each `evidence_key`:

```text
exists in approved.evidence
is present
```

but it does not deterministically prove that the prose attached to that key is semantically supported by that fact.

Therefore an unrelated but existing key can authorize an invented statement.

Conceptual example that is not rejected by the present key-binding logic:

```text
text = "Transit access is excellent."
evidence_keys = ["financial.fixed_costs"]
```

The evidence key can be real and present while being semantically unrelated to the transit claim.

A correct machine-checkable evidence boundary cannot treat “some approved key exists” as proof for arbitrary free-form prose.

### 3.2 Executive summary and caveats have no evidence binding at all

`executive_summary` and each `caveat` are arbitrary free-form strings.

They are checked only by the global lexical/numeric contradiction guards. They do not carry claim IDs/evidence bindings and can therefore introduce unsupported canonical-sounding statements that do not hit the current blacklist.

Example class of incorrect path:

```text
executive_summary = "The area benefits from exceptional transit access."
```

If no current phrase-specific contradiction fires, this can become part of factory-owned `ValidatedReportNarrative` even though no deterministic rule proved that exact claim from the canonical context.

### 3.3 Phrase blacklists do not satisfy the contract’s “equivalent claim” requirement

The current semantic validator rejects selected literal phrase families such as:

```text
empirically validated
guaranteed success
risk-free
high confidence
complete evidence
financially strong
```

This is useful defense-in-depth but it is not a complete semantic authority boundary.

Semantically equivalent wording outside the hard-coded phrase tuples can pass. The contract explicitly requires rejection of claims equivalent to unsupported empirical validation, guarantees, certainty upgrades and canonical contradictions—not only a fixed handful of exact phrasings.

The final authority must not depend on the LLM voluntarily obeying the prompt for all wording not covered by the blacklist.

---

# 4. REQUIRED HARDENING FOR NARR53-H001

Hardening must remain on the same branch and PR:

```text
branch: faz5/5-3-narrative-insight-authority
PR: #19
```

Do not reopen frozen upstream packages. Do not start 5.4.

The required outcome is:

```text
No arbitrary free-form provider assertion can become ValidatedReportNarrative authority merely because:
- anchors match,
- one or more unrelated approved evidence keys exist,
- and the wording avoids the current blacklist.
```

A robust acceptable design is a closed, code-owned semantic claim contract. Exact names may vary, but the implementation must provide equivalent deterministic authority.

Recommended shape:

```text
provider draft item
-> code-owned claim_id / claim_type from a closed enum
-> exact allowed evidence-key set for that claim
-> deterministic compatibility predicate against canonical context
-> only then final narrative authority
```

For example, a claim equivalent to:

```text
STRUCTURAL_BAND_STRONG
```

may be valid only when:

```text
decision.structural_band == "strong"
```

and only with the code-owned evidence binding permitted for that claim.

A claim equivalent to:

```text
SEVERE_RENT_BURDEN
```

may be valid only when the exact canonical risk/status fact is present.

Provider-selected evidence keys must therefore be validated for **semantic compatibility**, not merely membership.

## Free-form text rule

If provider-authored free-form wording remains inside `ValidatedReportNarrative`, it must not be able to add semantic content beyond the validated closed claim.

Acceptable approaches include:

1. **Preferred:** provider selects/orders closed claim IDs and the final customer-facing text is rendered from deterministic code-owned versioned templates; or
2. provider wording is accepted only through a deterministic closed grammar/claim-specific phrase contract that cannot add a second unsupported assertion.

An unconstrained arbitrary string plus a claim/evidence tag is not sufficient.

The same grounding rule applies to:

```text
executive_summary
strengths
risks
recommendations
caveats
```

No section may be an ungrounded authority escape hatch.

The LLM may choose emphasis/order among authorized canonical claims, but it must not mint new canonical/business facts.

---

# 5. REQUIRED ADVERSARIAL TESTS

Add tests that fail on the current implementation and pass after hardening.

At minimum prove all of these provider drafts fall back/reject rather than becoming `generation_mode=llm` authority:

```text
1. unrelated evidence binding
   claim about transit/accessibility
   + evidence key from financial.fixed_costs

2. unsupported executive-summary assertion
   anchors are correct
   no numeric literal
   no current blacklist phrase
   but statement asserts a fact not authorized by canonical claim contract

3. unsupported caveat assertion
   arbitrary new business/location fact in caveats

4. semantic synonym bypass
   wording equivalent to empirical/proven-real-world validation
   but not one of the current exact blacklist strings

5. semantic guarantee/certainty synonym bypass
   equivalent prohibited outcome/certainty claim using alternate wording

6. claim/evidence mismatch
   valid closed claim ID with an evidence key not authorized for that claim

7. source state mismatch
   closed positive claim ID when exact canonical state does not permit it
```

Also prove valid canonical claim IDs across representative strong/weak/low-confidence/risk states remain accepted and deterministic.

No second score/financial/decision/confidence engine may be introduced. Compatibility predicates must use exact existing canonical categorical/status facts.

---

# 6. VALIDATION STATE

The current pre-hardening candidate does have a successful exact validation run:

```text
workflow: faz5-5-3-exact-validation
run ID: 32070473670
job ID: 95512322967
validated SHA: 90760acd862fbb60a0a0e7865f39a4eefac3805a
conclusion: SUCCESS
```

Current reported counts:

```text
sitescore-report: 14 PASS
locked API + frozen baseline: 1463 PASS
combined: 1477 PASS
```

Reviewer independently verified validated-SHA -> current-final-head:

```text
90760acd862fbb60a0a0e7865f39a4eefac3805a
->
1d0e9fd57bda67cece6f17838f73569170066bf0

status: ahead
ahead_by: 1
behind_by: 0
changed files: 1
```

Sole post-validation change:

```text
.github/workflows/faz5-5-3-validation.yml
status: REMOVED
```

This CI evidence is valid for the existing candidate but does not resolve NARR53-H001 because the semantic-grounding bypass is not covered by the current test suite.

Any product/test/doc change made for hardening invalidates this acceptance candidate. After NARR53-H001 is fixed, run a **fresh exact-SHA full validation** and again remove the temporary workflow only after success.

Required baseline remains:

```text
sitescore-api: 88 PASS
sitescore-app: 19 PASS
sitescore-pipeline: 53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics: 67 PASS
sitescore-spatial: 180 PASS
sitescore-providers: 418 PASS
sitescore-data: 361 PASS
sitescore-core: 86 PASS
locked API + frozen: 1463 PASS
sitescore-report: ALL PASS with new exact count
combined = 1463 + new sitescore-report count
```

---

# 7. IMPLEMENTER NEXT ACTION

```text
IMPLEMENTER_ACTION: HARDEN
BLOCKER_TO_RESOLVE: NARR53-H001
SAME_BRANCH: YES
SAME_PR: YES
NEW_CHECKPOINT: NO
START_5_4: NO
MERGE: NO
LOCK: NO
```

Implementer must:

1. harden the narrative semantic/evidence authority as above;
2. add adversarial bypass tests;
3. preserve the current canonical NOT_SCORE_READY production limitation;
4. preserve the locked 5.2 report authority;
5. keep all product changes inside `sitescore-report/**`;
6. run fresh exact validation after the final product/test/doc change;
7. remove the temporary validation workflow only after successful validation;
8. update `implementer.md` with exact new HEAD / run / job / counts / blocker resolution evidence;
9. STOP for Reviewer re-review.

Reviewer does not merge and does not self-lock.

STOP.
