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
-> active code-owned NarrativeClaimId contract
-> untrusted OpenAI Responses API claim selection OR deterministic fallback selection
-> strict schema validation
-> exact claim/state/evidence compatibility validation
-> code-owned versioned text templates
-> ValidatedReportNarrative
```

The LLM is a selector/narrator only. It is not a scoring engine, financial calculator, decision authority, confidence authority, benchmark authority, readiness authority, or source of new business facts.

## Provider boundary

The primary production adapter uses the OpenAI Responses API with strict Pydantic structured output. Runtime package pins are:

```text
openai==3.2.0
pydantic==2.13.4
```

The model ID is deployment configuration (`SITESCORE_NARRATIVE_MODEL_ID`) and generation provenance only. API credentials remain OpenAI client/environment concerns and are never copied into report facts, narrative context, narrative provenance, or prompt payloads. The request supplies no tools.

Provider output is always untrusted until deterministic local validation succeeds.

## Closed semantic claim authority

`NarrativeDraft` contains **no provider-authored prose field**. Every section, including executive summary and caveats, is represented only by closed claim selections:

```text
claim_id: NarrativeClaimId
evidence_keys: exact code-owned list
```

`ApprovedNarrativeContext` exposes only claim IDs whose exact canonical source-state predicate is currently true. Each active claim carries a code-owned section and exact evidence-key tuple. Validation requires:

```text
claim_id is active for this canonical ReportDomainModel
section matches the claim contract
provider evidence_keys exactly equal the code-owned evidence tuple
all required evidence is present
canonical anchors match exactly
```

An unrelated but existing evidence key therefore cannot authorize a claim. A claim valid in another source state cannot be selected. Provider-created claim IDs are impossible because the schema uses a closed enum.

Customer-facing narrative text is rendered **after** validation from deterministic code-owned templates. The provider cannot add a second assertion, synonym bypass, empirical claim, guarantee, certainty upgrade, unsupported transit/location statement, numeric invention, or arbitrary caveat because there is no free-form text surface in the provider schema.

## Deterministic fallback

Provider/model unconfigured state, provider exception, incomplete/refused output, schema-invalid output, anchor mismatch, inactive claim, section mismatch, claim/evidence mismatch, or unavailable evidence activates a deterministic versioned fallback.

Fallback uses the same active closed-claim contract and the same code-owned templates. It does not calculate scores, thresholds, financial outcomes, confidence, readiness, or new business meaning.

Invalid canonical report-domain authority remains a hard failure and is never converted into fallback success.

## Versioned narrative contract

```text
prompt version:   sitescore-narrative-prompt-v2
schema version:   sitescore-narrative-v2
fallback version: sitescore-narrative-fallback-v2
```

The v2 change is the NARR53-H001 hardening: free-form provider prose was removed from all final-authority sections and replaced with a closed machine-checkable claim/state/evidence contract.

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
