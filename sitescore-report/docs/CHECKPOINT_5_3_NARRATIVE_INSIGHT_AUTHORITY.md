# FAZ 5.3 — Narrative / Insight Authority Boundary

## Status

- Package: `sitescore-report==0.2.0`
- Locked analytical baseline: FAZ 5.2 canonical report authority
- Narrative schema: `sitescore-narrative-v2`
- Prompt version: `sitescore-narrative-prompt-v2`
- Fallback version: `sitescore-narrative-fallback-v2`
- Primary provider: OpenAI Responses API
- OpenAI SDK: `openai==3.2.0`
- Local schema validation: `pydantic==2.13.4`
- Product source scope: `sitescore-report/**`
- Database migration: none
- Reviewer hardening: `NARR53-H001` addressed by closed semantic claim authority

> Mathematically validated scoring engine; empirical validation pending.

## Locked analytical authority

FAZ 5.2 remains the sole analytical truth source:

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
```

FAZ 5.3 adds no score, finance, decision, confidence, benchmark or readiness authority.

## Narrative authority chain

```text
canonical ReportDomainModel
-> require_canonical_report_domain_model(...)
-> build_approved_narrative_context(...)
-> ApprovedNarrativeContext
-> canonical-state activation of closed NarrativeClaimId values
-> OpenAI Responses API claim selection OR deterministic fallback claim selection
-> strict Pydantic schema validation
-> exact claim/section/evidence compatibility validation
-> code-owned versioned customer-facing templates
-> factory-owned ValidatedReportNarrative
```

`ApprovedNarrativeContext` and `ValidatedReportNarrative` use the same fail-closed factory-owned identity pattern as the locked report domain. Equal-value copies, manual shells, source substitution, claim-map substitution and semantic mutation do not become authority.

A dictionary, JSON projection, analysis fingerprint, caller category score, caller decision, caller financial value, caller confidence value, or forged report-domain shell cannot grant narrative authority.

## Bounded canonical context

The provider receives only a deep-owned report-safe projection plus:

```text
canonical_anchors
approved_evidence
approved_evidence_keys
approved_claims
prompt_version
narrative_schema_version
```

The context does not contain raw provider HTTP payloads, deployment credentials, API keys, database rows, Celery state, arbitrary external request text, or hidden transport state.

Optional report facts remain absent when absent. Partial data-quality/input mappings remain partial.

## Closed semantic claim contract

`NarrativeClaimId` is a code-owned closed enum. Each claim has a code-owned contract:

```text
claim_id
section
exact evidence_keys tuple
canonical compatibility predicate
code-owned render template
```

Representative claim classes include:

```text
executive.canonical_decision
strength.structural_strong
strength.financial_strong
strength.confidence_high
risk.structural_weak
risk.financial_non_viable
risk.high_rent_burden
risk.severe_rent_burden
risk.stress_test_failed
risk.negative_base_margin
recommendation.review_rent
recommendation.review_downside
recommendation.review_cost_revenue
recommendation.structural_constraint
recommendation.review_canonical_decision
caveat.empirical_validation_pending
caveat.language_layer
caveat.confidence_not_high
caveat.incomplete_evidence
```

The exact vocabulary is implementation-owned and versioned with the narrative schema.

### Canonical state activation

A claim is exposed in `ApprovedNarrativeContext.approved_claims` only when its exact categorical/status predicate is true for the canonical `ReportDomainModel`.

Examples:

```text
strength.structural_strong
requires decision.structural_band == "strong"

risk.financial_non_viable
requires decision.financial_band == "non_viable"

risk.severe_rent_burden
requires SEVERE_RENT_BURDEN in canonical risk flags

risk.stress_test_failed
requires canonical stress_test_failed == true

caveat.confidence_not_high
requires canonical confidence label != "high"
```

These predicates consume already-canonical categorical/status facts. They do not recompute scoring, BEC, financial thresholds, confidence weights, decision thresholds or readiness.

### Exact evidence compatibility

For each selected claim, validation requires:

```text
claim_id is currently active
claim belongs to the submitted section
submitted evidence_keys exactly equal the code-owned tuple
required evidence exists and is present
```

Membership of some unrelated evidence key is not sufficient.

Conceptually invalid:

```text
claim_id = strength.structural_strong
evidence_keys = [financial.fixed_costs]
```

Even though `financial.fixed_costs` can be a real approved fact, it is not the exact evidence contract for the structural claim and therefore cannot authorize it.

## No provider-authored prose authority

NARR53-H001 identified that v1 free-form strings could carry unsupported semantic content while still citing an existing evidence key.

V2 removes that authority surface entirely.

`NarrativeDraft` contains only:

```text
canonical_anchors
executive_summary[] claim selections
strengths[] claim selections
risks[] claim selections
recommendations[] claim selections
caveats[] claim selections
```

Each claim selection contains only:

```text
claim_id: NarrativeClaimId
evidence_keys: list[str]
```

There is **no `text` field** in provider structured output.

Therefore:

- executive summary cannot introduce an unsupported transit/location/business assertion;
- caveats cannot introduce a new arbitrary fact;
- a semantic synonym for empirical validation or a guarantee cannot bypass a phrase blacklist;
- a provider cannot attach extra prose to a valid claim ID;
- a provider cannot mint a second unsupported assertion beside an authorized claim.

Any extra/free-form text field is schema-invalid before semantic authority can be minted.

## Code-owned customer-facing rendering

After claim selection passes local validation, final text is rendered from deterministic code-owned templates.

Examples:

```text
executive.canonical_decision
-> "Canonical decision: <canonical decision headline>."

strength.structural_strong
-> "The canonical structural band is strong."

risk.stress_test_failed
-> "The canonical stress-test status indicates failure."

caveat.empirical_validation_pending
-> "Mathematically validated scoring engine; empirical validation pending."
```

Any dynamic insertion comes from exact canonical categorical/report text already owned by the report domain, not from provider prose.

The model may choose emphasis/order among active claims only.

## OpenAI Responses API adapter

The production adapter calls:

```text
client.responses.parse(..., text_format=NarrativeDraft)
```

The request uses:

```text
model = deployment-configured model ID
instructions = code-owned prompt asset
input = bounded canonical narrative context JSON
text_format = strict Pydantic NarrativeDraft
tools = []
store = false
```

No web search, file search, MCP or function tool is supplied.

The model ID is generation provenance, not business truth. API credentials remain OpenAI client/environment concerns and are not copied into prompt input or narrative provenance.

Tests inject a deterministic fake at the Responses boundary; CI does not require a paid OpenAI call or secret.

## Validation rules

Local validation runs after structured parsing and before final authority.

### Anchor equality

Every provider anchor must exactly equal:

```text
decision_class
structural_band
financial_band
confidence_label
stress_test_failed
source_analysis_fingerprint
```

### Closed claim authority

Every selected claim must be in the canonical context's active `approved_claims` map.

### Section compatibility

A strength claim cannot be submitted as a risk, a caveat claim cannot become an executive summary, and so on.

### Exact evidence binding

Provider evidence-key lists must exactly match the code-owned evidence tuple for the claim. Alternate or unrelated approved evidence is rejected.

### Source-state compatibility

Positive claims unavailable in the exact canonical state are rejected even if their enum value exists globally.

## Deterministic fallback

Fallback activates for:

```text
provider/model unconfigured
provider/client exception or timeout
provider incomplete response
refusal/empty parsed output
schema-invalid output
canonical-anchor mismatch
inactive claim/source-state mismatch
wrong-section claim
claim/evidence mismatch
unavailable required evidence
```

Fallback itself selects only active closed claims and uses the same code-owned rendering templates.

Fallback does not calculate scores, thresholds, BEC, financial outputs, confidence, readiness or new business outcomes.

Provenance distinguishes:

```text
generation_mode = llm | deterministic_fallback
provider
model_id | null
prompt_version
narrative_schema_version
fallback_version | null
fallback_reason | null
```

Invalid canonical `ReportDomainModel` / `ApprovedNarrativeContext` authority is a hard failure. Fallback never bypasses a broken authority chain.

## Prompt contract

The code-owned v2 instructions require the provider to:

```text
select only supplied approved claim IDs
echo each claim's exact evidence-key list
echo canonical anchors exactly
never write prose
never invent a claim ID or evidence binding
never calculate or infer a new analytical/business state
return only the strict structured schema
```

External caller text cannot replace this instruction asset.

## NARR53-H001 adversarial proof obligations

The hardening test suite covers at minimum:

```text
unrelated evidence binding
unsupported executive-summary assertion
unsupported caveat assertion
empirical/proven-real-world synonym injection
guarantee/certainty synonym injection
claim/evidence mismatch
source-state mismatch
```

It also proves valid active claims across representative strong, weak, low-confidence and risk states remain accepted and deterministic.

The key invariant is:

```text
No arbitrary free-form provider assertion can enter ValidatedReportNarrative authority.
```

## Current product limitation

The locked product truth remains:

```text
COMB-005 = NOT_APPROVED
real production lifecycle = queued -> running -> not_score_ready
```

FAZ 5.3 introduces no production SCORE_READY forcing seam and no path that narrates `not_score_ready` as a scored success.

No `analysis_id`, `report_id`, report resource lifecycle or artifact binding is introduced.

## Explicitly deferred

Still outside this checkpoint:

```text
HTML/CSS presentation templates
charts
PDF rendering
object/S3 storage
report lifecycle/resource IDs
API report routes
analysis-to-report durable binding
payments
n8n
email delivery
FAZ 6 behavior
```
