# FAZ 4.2 — Canonical Core Analysis Adapter

Status: implementation candidate for independent Reviewer audit.

## Boundary

Canonical input chain:

```text
factory-owned ApplicationCategoryAggregationResult
+ explicit revenue/cost/confidence-quality inputs
-> frozen core CategoryScores
-> frozen core AnalysisInput
-> factory-owned ApplicationCoreAnalysisInput
```

FAZ 4.2 constructs the canonical adapter authority only. It does **not** execute `sitescore.analyze()` or any Revenue, Location, Financial, Decision, Confidence, fingerprint, transport, payment, report, UI, deployment, queue, or n8n path.

## Trusted category consumption

Locked FAZ 4.1 aggregation now exposes a deliberately private internal resolver `_resolve_trusted_application_category_authority`. It first revalidates exact factory identity plus public/nested integrity, then returns only construction-time closure-bound `Sector` and four category values. It is not exported through `sitescore_app.__all__`.

4.1 formulas, frozen core weights, sector mapping and category outputs are unchanged.

## Core authority

The adapter uses the actual frozen `sitescore-core==0.1.0` types:

- `Sector`
- `CategoryScores`
- `AnalysisInput`
- sector revenue-input dataclasses
- `GeographicLevel`
- `CoverageLevel`
- `InputQuality`

No app-owned duplicate validation table or sector/revenue compatibility policy is introduced. Core constructors remain authoritative.

Caller `data_coverage` and `input_qualities` dictionaries are copied before `AnalysisInput` construction. Missing keys are not invented.

## ApplicationCoreAnalysisInput

`ApplicationCoreAnalysisInput` is constructor-blocked and factory-owned. Its closure-private construction record binds the exact upstream category result, trusted sector/categories, exact core `CategoryScores`, exact revenue input plus semantic record, explicit costs/quality inputs, adapter-owned dictionaries plus semantic records, exact core `AnalysisInput`, and a recursive complete semantic record.

Canonical validation fails closed on wrapper redirection, nested core DTO replacement/mutation, mapping mutation, revenue mutation, cost/quality mutation, or upstream 4.1 authority mutation. Public `analysis_input` and `category_result` access is resolver-backed so post-grant mutation cannot be consumed silently.

A valid caller-created raw core `AnalysisInput` remains a DTO, not application execution authority.

## Firewalls

- no new dependency; existing `sitescore-core==0.1.0` reused
- `sitescore-app` version remains `0.1.0`
- no `SECTOR_CATEGORY_WEIGHTS` consumption
- no category recomputation from normalized features
- no `ReadyCategoryScorePayload` authority
- no core `analyze()` execution
- COMB-005 remains `NOT_APPROVED`
- FAZ 4.3 and 4.4 remain NOT_STARTED
