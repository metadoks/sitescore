# sitescore-report

`sitescore-report==0.2.0` extends the locked FAZ 5.2 canonical report domain with a truth-preserving narrative authority boundary.

Locked analytical authority remains:

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
```

FAZ 5.3 adds only:

```text
canonical ReportDomainModel
-> ApprovedNarrativeContext
-> untrusted OpenAI Responses API draft OR deterministic fallback draft
-> strict schema validation
-> deterministic semantic validation
-> ValidatedReportNarrative
```

The LLM is a narrator/language layer only. It is not a scoring engine, financial calculator, decision authority, confidence authority, benchmark authority, or readiness authority.

## Provider boundary

The primary production adapter uses the OpenAI Responses API with strict Pydantic structured output. Runtime package pins are:

```text
openai==3.2.0
pydantic==2.13.4
```

The model ID is deployment configuration (`SITESCORE_NARRATIVE_MODEL_ID`) and is generation provenance only. API credentials remain OpenAI client/environment concerns and are never copied into report facts, narrative context, narrative provenance, or prompt payloads. The request supplies no tools.

Provider output is always untrusted until deterministic local validation succeeds.

## Local semantic guardrails

The validator requires exact echo of canonical decision/structural/financial/confidence/stress/fingerprint anchors; every insight/recommendation must bind to an available approved evidence key. Unknown or missing evidence is rejected.

The narrative layer rejects obvious contradictions against canonical decision, financial, stress, rent-burden, confidence, and missingness facts. Free-form provider prose may not introduce numeric/currency/percentage literals and may not claim empirical validation, guaranteed outcomes, certain profitability, or risk-free operation.

Provider/schema/semantic failure activates a deterministic versioned fallback built only from exact canonical categorical/status facts. Invalid canonical report-domain authority is a hard failure and is never converted into fallback success.

## Current locked product limitation

Frozen COMB-005 remains not approved, so the real production analysis lifecycle remains:

```text
queued -> running -> not_score_ready
```

FAZ 5.3 does not manufacture a scored report or narrative from that path. Positive scored narrative fixtures exist only in tests through the same upstream SCORE_READY test boundary used by the locked FAZ 5.2 tests.

## Still out of scope

No HTML/CSS template, chart, PDF rendering, object storage, report resource, `report_id`, `analysis_id <-> report` binding, API route, database migration, payment, n8n, or email behavior is introduced here.

See:

- `docs/CHECKPOINT_5_2_CANONICAL_REPORT_DOMAIN.md`
- `docs/CHECKPOINT_5_3_NARRATIVE_INSIGHT_AUTHORITY.md`

> Mathematically validated scoring engine; empirical validation pending.
