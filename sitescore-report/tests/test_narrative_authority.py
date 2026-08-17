from __future__ import annotations

from test_report_projection_authority import _run


def test_four_sector_responses_adapter_and_validated_authority():
    _run(r'''
import json
from types import SimpleNamespace
from sitescore_report import (
    NARRATIVE_INSTRUCTIONS,
    NARRATIVE_PROMPT_VERSION,
    NARRATIVE_SCHEMA_VERSION,
    NarrativeDraft,
    NarrativeDraftAnchors,
    NarrativePointDraft,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
    require_validated_report_narrative,
)

class FakeResponses:
    def __init__(self):
        self.calls = []
    def parse(self, **kwargs):
        self.calls.append(kwargs)
        payload = json.loads(kwargs["input"])
        anchors = payload["canonical_anchors"]
        draft = NarrativeDraft(
            canonical_anchors=NarrativeDraftAnchors(**anchors),
            executive_summary="The canonical report supports this narrative without changing the recorded decision.",
            strengths=[NarrativePointDraft(
                text="The canonical structural band supports the recorded location assessment.",
                evidence_keys=["decision.structural_band"],
            )],
            risks=[],
            recommendations=[NarrativePointDraft(
                text="Review the canonical decision and supporting evidence before acting.",
                evidence_keys=["decision.decision_class"],
            )],
            caveats=["Mathematically validated scoring engine; empirical validation pending."],
        )
        return SimpleNamespace(status="completed", output_parsed=draft)

class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()

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
    assert result.approved_context.canonical_anchors.decision_class == source.core_result.decision.decision_class
    assert result.approved_context.canonical_anchors.confidence_label == source.core_result.confidence.label

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
    assert "decision.decision_class" in payload["approved_evidence_keys"]
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
for name in ("_report_domain_model", "canonical_anchors", "facts", "evidence"):
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

result = build_validated_report_narrative(
    domain,
    config=NarrativeProviderConfig(model_id=None),
)
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
    raise AssertionError("nested semantic mutation must fail")
object.__setattr__(result, "executive_summary", original_summary)
assert require_validated_report_narrative(result) is result
''')


def test_semantic_anchor_evidence_prohibited_claim_and_numeric_invention_fallbacks():
    _run(r'''
from types import SimpleNamespace
from sitescore_report import (
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

def valid_draft(payload, *, summary="The canonical decision remains authoritative.", evidence="decision.decision_class"):
    return NarrativeDraft(
        canonical_anchors=NarrativeDraftAnchors(**payload["canonical_anchors"]),
        executive_summary=summary,
        strengths=[],
        risks=[],
        recommendations=[NarrativePointDraft(text="Review the canonical decision before acting.", evidence_keys=[evidence])],
        caveats=["Mathematically validated scoring engine; empirical validation pending."],
    )

class FakeResponses:
    def __init__(self, mode): self.mode = mode
    def parse(self, **kwargs):
        import json
        payload = json.loads(kwargs["input"])
        draft = valid_draft(payload)
        if self.mode == "anchor":
            raw = draft.model_dump()
            raw["canonical_anchors"]["decision_class"] = "forged_decision"
            draft = NarrativeDraft.model_validate(raw)
        elif self.mode == "evidence":
            draft = valid_draft(payload, evidence="data_quality.data_coverage.absent")
        elif self.mode == "empirical":
            draft = valid_draft(payload, summary="This result is empirically validated.")
        elif self.mode == "guarantee":
            draft = valid_draft(payload, summary="This is guaranteed success.")
        elif self.mode == "numeric":
            draft = valid_draft(payload, summary="This opportunity scores 99 percent.")
        return SimpleNamespace(status="completed", output_parsed=draft)
class FakeClient:
    def __init__(self, mode): self.responses = FakeResponses(mode)

for mode in ("anchor", "evidence", "empirical", "guarantee", "numeric"):
    result = build_validated_report_narrative(
        domain(),
        config=NarrativeProviderConfig(model_id="test-model"),
        client=FakeClient(mode),
    )
    assert result.provenance.generation_mode == "deterministic_fallback", mode
    assert result.provenance.fallback_reason == "semantic_invalid", (mode, result.provenance)
    rendered = repr(result.to_dict()).lower()
    assert "99 percent" not in rendered
    assert "guaranteed success" not in rendered
    assert "empirically validated" not in rendered
''')


def test_decision_financial_confidence_and_missingness_contradictions_fallback():
    _run(r'''
from types import SimpleNamespace
from sitescore_report import (
    NarrativeDraft,
    NarrativeDraftAnchors,
    NarrativePointDraft,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
)

class FakeResponses:
    def __init__(self, summary): self.summary = summary
    def parse(self, **kwargs):
        import json
        payload = json.loads(kwargs["input"])
        return SimpleNamespace(status="completed", output_parsed=NarrativeDraft(
            canonical_anchors=NarrativeDraftAnchors(**payload["canonical_anchors"]),
            executive_summary=self.summary,
            strengths=[], risks=[],
            recommendations=[NarrativePointDraft(text="Review the canonical decision before acting.", evidence_keys=["decision.decision_class"])],
            caveats=["Mathematically validated scoring engine; empirical validation pending."],
        ))
class FakeClient:
    def __init__(self, summary): self.responses = FakeResponses(summary)

def narrate(source, summary):
    domain = build_report_domain_model(build_canonical_report_facts(source))
    return build_validated_report_narrative(
        domain,
        config=NarrativeProviderConfig(model_id="test-model"),
        client=FakeClient(summary),
    )

weak = build_scored("restaurant", score=5.0, monthly_rent=500000.0, fixed_labor=500000.0, fixed_overhead=250000.0)
assert weak.core_result.decision.financial_band == "non_viable"
assert weak.core_result.financial.stress_test_failed is True
for summary in ("The location is a prime opportunity.", "The economics are financially strong.", "The stress test passed."):
    result = narrate(weak, summary)
    assert result.provenance.generation_mode == "deterministic_fallback", summary
    assert result.provenance.fallback_reason == "semantic_invalid"

low = build_scored(
    "gym",
    score=72.0,
    geographic_level=GeographicLevel.UNKNOWN,
    data_age_years=None,
    data_coverage={"demand": CoverageLevel.DEGRADED},
    input_qualities={"rent": InputQuality.DEFAULT},
)
assert low.core_result.confidence.label == "low"
for summary in ("This conclusion has high confidence.", "The analysis has complete evidence."):
    result = narrate(low, summary)
    assert result.provenance.generation_mode == "deterministic_fallback", summary
    assert result.provenance.fallback_reason == "semantic_invalid"
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
    assert result.to_dict()["provenance"]["fallback_version"] == "sitescore-narrative-fallback-v1"
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
    build_validated_report_narrative(forged, config=NarrativeProviderConfig(model_id=None))
except ValueError:
    pass
else:
    raise AssertionError("forged report-domain authority must hard fail rather than fallback")
''')
