# FAZ 5.3 — Narrative / Insight Authority Boundary

## Status

- Package: `sitescore-report==0.2.0`
- Locked analytical baseline: FAZ 5.2 canonical report authority
- Narrative schema: `sitescore-narrative-v1`
- Prompt version: `sitescore-narrative-prompt-v1`
- Fallback version: `sitescore-narrative-fallback-v1`
- Primary provider: OpenAI Responses API
- OpenAI SDK: `openai==3.2.0`
- Local schema validation: `pydantic==2.13.4`
- Product source scope: `sitescore-report/**`
- Database migration: none

> Mathematically validated scoring engine; empirical validation pending.

## Authority chain

FAZ 5.2 remains the sole analytical truth source:

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
```

FAZ 5.3 adds only a language authority chain:

```text
canonical ReportDomainModel
-> require_canonical_report_domain_model(...)
-> build_approved_narrative_context(...)
-> ApprovedNarrativeContext
-> OpenAI Responses API structured draft OR deterministic fallback draft
-> strict Pydantic schema validation
-> deterministic semantic validation
-> factory-owned ValidatedReportNarrative
```

`ApprovedNarrativeContext` and `ValidatedReportNarrative` use the same fail-closed factory-owned identity pattern as the locked report domain. Equal-value copies, manual shells, source substitution and nested semantic mutation do not become authority.

A dictionary, JSON projection, analysis fingerprint, model-version string, caller category score, caller decision, caller financial value, caller confidence value, or forged report-domain shell cannot grant narrative authority.

## Bounded context

The provider receives only a deep-owned projection of the canonical report domain plus a closed approved evidence map. The context contains report-safe facts such as sector, category scores, business assumptions, location, financial result, canonical decision, confidence, data quality, source analysis fingerprint, and model/report provenance.

It does not contain raw provider HTTP payloads, deployment credentials, API keys, database rows, Celery state, arbitrary external request text, or hidden transport state.

Evidence identifiers are code-owned paths. Optional facts are omitted from the approved evidence map when absent. Partial data-quality/input mappings remain partial; no missing key is manufactured as evidence.

## OpenAI Responses API adapter

The production adapter calls the OpenAI Python SDK Responses API through:

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

No web search, file search, remote MCP or function tool is supplied.

The model ID is generation provenance, not business truth. The API credential remains an OpenAI client/environment concern. No raw API credential is copied into prompt input, report facts or narrative provenance.

Tests inject a deterministic fake at the OpenAI client/Responses boundary. CI does not require a paid network call or secret.

## Untrusted draft schema

The provider draft is not authority even after structured-output parsing.

Required sections:

```text
canonical_anchors
executive_summary
strengths[]
risks[]
recommendations[]
caveats[]
```

Canonical anchors echo:

```text
decision_class
structural_band
financial_band
confidence_label
stress_test_failed
source_analysis_fingerprint
```

Strength/risk/recommendation points contain text plus one or more approved evidence keys.

## Deterministic semantic validation

Local validation runs after schema validation and before final narrative authority is minted.

### Anchor equality

Every provider anchor must exactly equal the canonical context anchor.

### Evidence binding

Every referenced evidence key must exist in the context's approved evidence map and refer to a present fact. Unknown keys and absent optional/mapping facts are rejected.

### Decision consistency

The validator rejects explicit upgrades/contradictions such as presenting canonical `dead_end` as a prime/strong opportunity, presenting `tourist_trap` as strong economics, or presenting `structural_risk` as structurally strong.

It does not calculate a second decision matrix.

### Financial consistency

The validator uses canonical financial/result labels and flags only. It rejects claims such as financially strong against `non_viable`, stress-test passed when canonical stress failed, positive operating margin when the canonical sign is negative, or low rent burden when `SEVERE_RENT_BURDEN` is present.

No financial threshold is recomputed in the narrative layer.

### Confidence and missingness

Provider prose cannot upgrade non-high confidence to high certainty. When the canonical data/input context is partial, missing, unknown or degraded, the narrative cannot claim complete evidence/data.

Missing values remain missing.

### Unsupported claims

Provider prose is rejected for claims equivalent to empirical validation, proven market performance, calibration against real-world outcomes, financial guarantee, guaranteed success/profitability, certain profitability or risk-free operation.

### Numeric invention

V1 applies the conservative rule:

```text
free-form provider prose may not contain numeric/currency/percentage literals
```

Canonical numbers remain report facts for later deterministic presentation. The language model is not a source of report numbers.

## Deterministic fallback

Fallback activates for:

```text
provider/model unconfigured
provider/client exception or timeout
provider incomplete response
refusal/empty parsed output
schema-invalid output
unknown/unavailable evidence
canonical-anchor mismatch
semantic contradiction
prohibited empirical/guarantee claim
numeric invention
```

Fallback content uses only already-canonical categorical/status facts such as decision headline/class, structural/financial bands, risk flags, confidence label, stress status and data-quality missingness.

Fallback does not calculate scores, thresholds, BEC, confidence or new business outcomes.

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

Invalid canonical ReportDomainModel/ApprovedNarrativeContext authority is a hard failure. Fallback never bypasses a broken authority chain.

## Prompt contract

The code-owned instructions require the provider to:

```text
use only supplied facts
never calculate or infer a score/financial outcome/decision/confidence/readiness state
never invent missing evidence
never claim empirical validation
never guarantee success or profitability
never output HTML/CSS
never introduce numeric/currency/percentage literals
return only the strict structured schema
bind insights/recommendations to approved evidence keys
```

External caller text cannot replace this instruction asset.

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
