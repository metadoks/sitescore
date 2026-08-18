from __future__ import annotations

from test_report_projection_authority import _run


def test_four_sector_responses_adapter_uses_closed_claim_selection_only():
    _run(r'''
import json
from types import SimpleNamespace
from sitescore_report import (
    NARRATIVE_INSTRUCTIONS,
    NARRATIVE_PROMPT_VERSION,
    NARRATIVE_SCHEMA_VERSION,
    NarrativeClaimId,
    NarrativeDraft,
    NarrativeDraftAnchors,
    NarrativePointDraft,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
    require_validated_report_narrative,
)


def selection(payload, claim_id):
    approved = payload["approved_claims"][claim_id.value]
    return NarrativePointDraft(
        claim_id=claim_id,
        evidence_keys=list(approved["evidence_keys"]),
    )


class FakeResponses:
    def __init__(self):
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        payload = json.loads(kwargs["input"])
        return SimpleNamespace(
            status="completed",
            output_parsed=NarrativeDraft(
                canonical_anchors=NarrativeDraftAnchors(**payload["canonical_anchors"]),
                executive_summary=[selection(payload, NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION)],
                strengths=[],
                risks=[],
                recommendations=[selection(payload, NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION)],
                caveats=[
                    selection(payload, NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING),
                    selection(payload, NarrativeClaimId.CAVEAT_LANGUAGE_LAYER),
                ],
            ),
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


schema_text = json.dumps(NarrativeDraft.model_json_schema(), sort_keys=True)
assert '"text"' not in schema_text
assert "executive_summary" in schema_text
assert "claim_id" in schema_text

for sector in ("coffee", "restaurant", "gym", "beauty"):
    source = build_scored(sector)
    facts = build_canonical_report_facts(source)
    domain = build_report_domain_model(facts)
    client = FakeClient()
    result = build_validated_report_narrative(
        domain,
        config=NarrativeProviderConfig(model_id="test-model"),
        client=client,
    )
    assert require_validated_report_narrative(result) is result
    assert result.approved_context.report_domain_model is domain
    assert result.provenance.generation_mode == "llm"
    assert result.provenance.provider == "openai"
    assert result.provenance.model_id == "test-model"
    assert result.provenance.prompt_version == NARRATIVE_PROMPT_VERSION
    assert result.provenance.narrative_schema_version == NARRATIVE_SCHEMA_VERSION
    assert result.provenance.fallback_reason is None
    assert result.approved_context.canonical_anchors.source_analysis_fingerprint == source.core_result.analysis_fingerprint
    assert result.executive_summary == f"Canonical decision: {source.core_result.decision.headline}."
    assert result.recommendations[0].claim_id is NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION
    assert result.recommendations[0].text == "Review the canonical decision and supporting evidence before acting."

    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["instructions"] == NARRATIVE_INSTRUCTIONS
    assert call["text_format"] is NarrativeDraft
    assert call["tools"] == []
    assert call["store"] is False
    assert "OPENAI_API_KEY" not in call["input"]
    assert "api_key" not in call["input"].lower()
    payload = json.loads(call["input"])
    assert payload["canonical_anchors"]["decision_class"] == source.core_result.decision.decision_class
    assert NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION.value in payload["approved_claims"]
    assert NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION.value in payload["approved_claims"]
    assert all("text" not in claim for claim in payload["approved_claims"].values())
    assert "raw_http" not in repr(payload).lower()
    assert "celery" not in repr(payload).lower()

    view = result.to_dict()
    view["executive_summary"] = "forged"
    view["recommendations"].append({"text": "forged", "evidence_keys": []})
    assert result.executive_summary != "forged"
    assert require_validated_report_narrative(result) is result
''')


def test_context_and_final_authority_reject_copy_forgery_substitution_and_mutation():
    _run(r'''
import copy
import dataclasses
from sitescore_report import (
    ApprovedNarrativeContext,
    ValidatedReportNarrative,
    NarrativeProviderConfig,
    build_approved_narrative_context,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
    require_approved_narrative_context,
    require_validated_report_narrative,
)

source = build_scored("coffee")
domain = build_report_domain_model(build_canonical_report_facts(source))
context = build_approved_narrative_context(domain)
assert require_approved_narrative_context(context) is context

for copier in (copy.copy, copy.deepcopy):
    try:
        candidate = copier(context)
    except Exception:
        continue
    try:
        require_approved_narrative_context(candidate)
    except ValueError:
        pass
    else:
        raise AssertionError("copied context must not gain authority")

manual = object.__new__(ApprovedNarrativeContext)
for name in ("_report_domain_model", "canonical_anchors", "facts", "evidence", "claims"):
    object.__setattr__(manual, name, getattr(context, name))
try:
    require_approved_narrative_context(manual)
except ValueError:
    pass
else:
    raise AssertionError("manual equal-value context must be rejected")

original_anchors = context.canonical_anchors
object.__setattr__(context, "canonical_anchors", dataclasses.replace(original_anchors))
try:
    require_approved_narrative_context(context)
except ValueError:
    pass
else:
    raise AssertionError("equal-value anchor substitution must fail")
object.__setattr__(context, "canonical_anchors", original_anchors)
assert require_approved_narrative_context(context) is context

original_claims = context.claims
object.__setattr__(context, "claims", dict(original_claims))
try:
    require_approved_narrative_context(context)
except ValueError:
    pass
else:
    raise AssertionError("equal-value claim-contract substitution must fail")
object.__setattr__(context, "claims", original_claims)
assert require_approved_narrative_context(context) is context

result = build_validated_report_narrative(domain, config=NarrativeProviderConfig(model_id=None))
assert require_validated_report_narrative(result) is result

for copier in (copy.copy, copy.deepcopy):
    try:
        candidate = copier(result)
    except Exception:
        continue
    try:
        require_validated_report_narrative(candidate)
    except ValueError:
        pass
    else:
        raise AssertionError("copied final narrative must not gain authority")

manual_final = object.__new__(ValidatedReportNarrative)
for name in ("_approved_context", "provenance", "executive_summary", "strengths", "risks", "recommendations", "caveats"):
    object.__setattr__(manual_final, name, getattr(result, name))
try:
    require_validated_report_narrative(manual_final)
except ValueError:
    pass
else:
    raise AssertionError("manual final narrative must be rejected")

other_domain = build_report_domain_model(build_canonical_report_facts(build_scored("gym")))
other_context = build_approved_narrative_context(other_domain)
original_context = result._approved_context
object.__setattr__(result, "_approved_context", other_context)
try:
    require_validated_report_narrative(result)
except ValueError:
    pass
else:
    raise AssertionError("source-context substitution must fail")
object.__setattr__(result, "_approved_context", original_context)
assert require_validated_report_narrative(result) is result

original_summary = result.executive_summary
object.__setattr__(result, "executive_summary", "mutated prose")
try:
    require_validated_report_narrative(result)
except ValueError:
    pass
else:
    raise AssertionError("final semantic mutation must fail")
object.__setattr__(result, "executive_summary", original_summary)
assert require_validated_report_narrative(result) is result
''')


def test_reviewer_h001_adversarial_bypasses_cannot_gain_llm_authority():
    _run(r'''
import json
from types import SimpleNamespace
from sitescore_report import (
    NarrativeClaimId,
    NarrativeDraft,
    NarrativeDraftAnchors,
    NarrativePointDraft,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
)


def domain():
    return build_report_domain_model(build_canonical_report_facts(build_scored("coffee")))


def selection(payload, claim_id, evidence_keys=None):
    approved = payload["approved_claims"].get(claim_id.value)
    keys = list(approved["evidence_keys"]) if approved is not None else []
    if evidence_keys is not None:
        keys = list(evidence_keys)
    return NarrativePointDraft(claim_id=claim_id, evidence_keys=keys)


def valid(payload):
    return NarrativeDraft(
        canonical_anchors=NarrativeDraftAnchors(**payload["canonical_anchors"]),
        executive_summary=[selection(payload, NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION)],
        strengths=[],
        risks=[],
        recommendations=[selection(payload, NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION)],
        caveats=[selection(payload, NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING)],
    )


class FakeResponses:
    def __init__(self, mode):
        self.mode = mode

    def parse(self, **kwargs):
        payload = json.loads(kwargs["input"])
        if self.mode == "unrelated_evidence":
            draft = valid(payload)
            draft.recommendations[0].evidence_keys = ["financial.fixed_costs"]
            return SimpleNamespace(status="completed", output_parsed=draft)
        if self.mode == "source_state_mismatch":
            draft = valid(payload)
            draft.strengths = [NarrativePointDraft(
                claim_id=NarrativeClaimId.RISK_FINANCIAL_NON_VIABLE,
                evidence_keys=["decision.financial_band"],
            )]
            return SimpleNamespace(status="completed", output_parsed=draft)

        anchors = NarrativeDraftAnchors(**payload["canonical_anchors"])
        executive = selection(payload, NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION)
        recommendation = selection(payload, NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION)
        caveat = selection(payload, NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING)
        raw = {
            "canonical_anchors": anchors,
            "executive_summary": [executive],
            "strengths": [],
            "risks": [],
            "recommendations": [recommendation],
            "caveats": [caveat],
        }
        if self.mode == "unsupported_executive":
            raw["executive_summary"] = [{
                "claim_id": NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION,
                "evidence_keys": list(executive.evidence_keys),
                "text": "The area benefits from exceptional transit access.",
            }]
        elif self.mode == "unsupported_caveat":
            raw["caveats"] = [{
                "claim_id": NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING,
                "evidence_keys": [],
                "text": "Local demand will remain resilient through future downturns.",
            }]
        elif self.mode == "empirical_synonym":
            raw["executive_summary"] = [{
                "claim_id": NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION,
                "evidence_keys": list(executive.evidence_keys),
                "text": "The result has been verified against actual marketplace outcomes.",
            }]
        elif self.mode == "guarantee_synonym":
            raw["recommendations"] = [{
                "claim_id": NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION,
                "evidence_keys": list(recommendation.evidence_keys),
                "text": "Success is assured beyond doubt.",
            }]
        return SimpleNamespace(status="completed", output_parsed=raw)


class FakeClient:
    def __init__(self, mode):
        self.responses = FakeResponses(mode)


expected_reasons = {
    "unrelated_evidence": "semantic_invalid",
    "source_state_mismatch": "semantic_invalid",
    "unsupported_executive": "schema_invalid",
    "unsupported_caveat": "schema_invalid",
    "empirical_synonym": "schema_invalid",
    "guarantee_synonym": "schema_invalid",
}
for mode, expected_reason in expected_reasons.items():
    result = build_validated_report_narrative(
        domain(),
        config=NarrativeProviderConfig(model_id="test-model"),
        client=FakeClient(mode),
    )
    assert result.provenance.generation_mode == "deterministic_fallback", mode
    assert result.provenance.fallback_reason == expected_reason, (mode, result.provenance)
    rendered = repr(result.to_dict()).lower()
    assert "exceptional transit" not in rendered
    assert "future downturns" not in rendered
    assert "actual marketplace outcomes" not in rendered
    assert "assured beyond doubt" not in rendered
''')


def test_closed_claim_source_state_and_exact_evidence_contract_is_machine_checkable():
    _run(r'''
from sitescore_report import (
    NarrativeClaimId,
    build_approved_narrative_context,
    build_canonical_report_facts,
    build_report_domain_model,
)

strong_source = build_scored(
    "coffee",
    score=95.0,
    monthly_rent=200.0,
    fixed_labor=200.0,
    fixed_overhead=100.0,
)
strong = build_approved_narrative_context(build_report_domain_model(build_canonical_report_facts(strong_source)))
assert NarrativeClaimId.STRENGTH_STRUCTURAL_STRONG.value in strong.claims
assert strong.claims[NarrativeClaimId.STRENGTH_STRUCTURAL_STRONG.value].evidence_keys == ("decision.structural_band",)

weak_source = build_scored(
    "restaurant",
    score=5.0,
    monthly_rent=500000.0,
    fixed_labor=500000.0,
    fixed_overhead=250000.0,
)
weak = build_approved_narrative_context(build_report_domain_model(build_canonical_report_facts(weak_source)))
assert weak_source.core_result.decision.financial_band == "non_viable"
assert NarrativeClaimId.RISK_FINANCIAL_NON_VIABLE.value in weak.claims
assert NarrativeClaimId.STRENGTH_FINANCIAL_STRONG.value not in weak.claims
assert weak.claims[NarrativeClaimId.RISK_FINANCIAL_NON_VIABLE.value].evidence_keys == ("decision.financial_band",)

low_source = build_scored(
    "gym",
    score=72.0,
    geographic_level=GeographicLevel.UNKNOWN,
    data_age_years=None,
    data_coverage={"demand": CoverageLevel.DEGRADED},
    input_qualities={"rent": InputQuality.DEFAULT},
)
low = build_approved_narrative_context(build_report_domain_model(build_canonical_report_facts(low_source)))
assert low_source.core_result.confidence.label == "low"
assert NarrativeClaimId.STRENGTH_CONFIDENCE_HIGH.value not in low.claims
assert NarrativeClaimId.CAVEAT_CONFIDENCE_NOT_HIGH.value in low.claims
assert NarrativeClaimId.CAVEAT_INCOMPLETE_EVIDENCE.value in low.claims
''')


def test_valid_closed_claims_for_strong_weak_low_confidence_and_risk_states_remain_llm_accepted():
    _run(r'''
import json
from types import SimpleNamespace
from sitescore_report import (
    NarrativeClaimId,
    NarrativeDraft,
    NarrativeDraftAnchors,
    NarrativePointDraft,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
)


def draft_from_all_active(payload):
    sections = {name: [] for name in ("executive_summary", "strength", "risk", "recommendation", "caveat")}
    for claim_id_text, spec in sorted(payload["approved_claims"].items()):
        sections[spec["section"]].append(NarrativePointDraft(
            claim_id=NarrativeClaimId(claim_id_text),
            evidence_keys=list(spec["evidence_keys"]),
        ))
    return NarrativeDraft(
        canonical_anchors=NarrativeDraftAnchors(**payload["canonical_anchors"]),
        executive_summary=sections["executive_summary"],
        strengths=sections["strength"],
        risks=sections["risk"],
        recommendations=sections["recommendation"],
        caveats=sections["caveat"],
    )


class FakeResponses:
    def parse(self, **kwargs):
        payload = json.loads(kwargs["input"])
        return SimpleNamespace(status="completed", output_parsed=draft_from_all_active(payload))


class FakeClient:
    responses = FakeResponses()


sources = [
    build_scored("coffee", score=95.0, monthly_rent=200.0, fixed_labor=200.0, fixed_overhead=100.0),
    build_scored("restaurant", score=5.0, monthly_rent=500000.0, fixed_labor=500000.0, fixed_overhead=250000.0),
    build_scored(
        "gym",
        score=72.0,
        geographic_level=GeographicLevel.UNKNOWN,
        data_age_years=None,
        data_coverage={"demand": CoverageLevel.DEGRADED},
        input_qualities={"rent": InputQuality.DEFAULT},
    ),
]
for source in sources:
    domain = build_report_domain_model(build_canonical_report_facts(source))
    first = build_validated_report_narrative(
        domain,
        config=NarrativeProviderConfig(model_id="test-model"),
        client=FakeClient(),
    )
    second = build_validated_report_narrative(
        domain,
        config=NarrativeProviderConfig(model_id="test-model"),
        client=FakeClient(),
    )
    assert first.provenance.generation_mode == "llm"
    assert first.provenance.fallback_reason is None
    assert first.to_dict() == second.to_dict()
    approved = set(first.approved_context.claims)
    emitted = {
        point.claim_id.value
        for group in (first.strengths, first.risks, first.recommendations)
        for point in group
    }
    assert emitted <= approved
    assert first.executive_summary.startswith("Canonical decision:")
    assert "Mathematically validated scoring engine; empirical validation pending." in first.caveats
''')


def test_provider_failure_schema_failure_and_unconfigured_model_use_deterministic_fallback():
    _run(r'''
from types import SimpleNamespace
from sitescore_report import (
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
)

domain = build_report_domain_model(build_canonical_report_facts(build_scored("coffee")))

unconfigured_a = build_validated_report_narrative(domain, config=NarrativeProviderConfig(model_id=None))
unconfigured_b = build_validated_report_narrative(domain, config=NarrativeProviderConfig(model_id=None))
assert unconfigured_a.provenance.generation_mode == "deterministic_fallback"
assert unconfigured_a.provenance.fallback_reason == "provider_unconfigured"
assert unconfigured_a.to_dict() == unconfigured_b.to_dict()

class RaisingResponses:
    def parse(self, **kwargs): raise TimeoutError("network unavailable")
class RaisingClient:
    responses = RaisingResponses()
provider_error = build_validated_report_narrative(
    domain,
    config=NarrativeProviderConfig(model_id="test-model"),
    client=RaisingClient(),
)
assert provider_error.provenance.fallback_reason == "provider_exception"

class IncompleteResponses:
    def parse(self, **kwargs): return SimpleNamespace(status="incomplete", output_parsed=None)
class IncompleteClient:
    responses = IncompleteResponses()
incomplete = build_validated_report_narrative(
    domain,
    config=NarrativeProviderConfig(model_id="test-model"),
    client=IncompleteClient(),
)
assert incomplete.provenance.fallback_reason == "provider_incomplete"

class EmptyResponses:
    def parse(self, **kwargs): return SimpleNamespace(status="completed", output_parsed=None)
class EmptyClient:
    responses = EmptyResponses()
empty = build_validated_report_narrative(
    domain,
    config=NarrativeProviderConfig(model_id="test-model"),
    client=EmptyClient(),
)
assert empty.provenance.fallback_reason == "provider_refusal_or_empty"

class SchemaResponses:
    def parse(self, **kwargs): return SimpleNamespace(status="completed", output_parsed={"unexpected": "shape"})
class SchemaClient:
    responses = SchemaResponses()
schema = build_validated_report_narrative(
    domain,
    config=NarrativeProviderConfig(model_id="test-model"),
    client=SchemaClient(),
)
assert schema.provenance.fallback_reason == "schema_invalid"

for result in (provider_error, incomplete, empty, schema):
    assert result.provenance.generation_mode == "deterministic_fallback"
    assert result.provenance.provider == "openai"
    assert result.provenance.model_id == "test-model"
    assert result.to_dict()["provenance"]["fallback_version"] == "sitescore-narrative-fallback-v2"
''')


def test_invalid_canonical_domain_is_hard_failure_not_fallback():
    _run(r'''
from sitescore_report import (
    ReportDomainModel,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
)

source = build_scored("coffee")
domain = build_report_domain_model(build_canonical_report_facts(source))
forged = object.__new__(ReportDomainModel)
for name in ("_canonical_facts", "provenance", "analysis", "category_scores", "business_assumptions", "location", "financial", "decision", "confidence", "data_quality"):
    object.__setattr__(forged, name, getattr(domain, name))
try:
    build_validated_report_narrative(
        forged,
        config=NarrativeProviderConfig(model_id=None),
    )
except ValueError:
    pass
else:
    raise AssertionError("invalid canonical report domain must fail hard, not fall back")
''')
