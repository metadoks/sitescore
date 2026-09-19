from __future__ import annotations

from test_report_projection_authority import _run


def test_inactive_closed_claim_with_correct_section_and_evidence_falls_back():
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

source = build_scored(
    "coffee",
    score=95.0,
    monthly_rent=200.0,
    fixed_labor=200.0,
    fixed_overhead=100.0,
)
assert source.core_result.decision.structural_band == "strong"
domain = build_report_domain_model(build_canonical_report_facts(source))

class FakeResponses:
    def parse(self, **kwargs):
        payload = json.loads(kwargs["input"])
        assert NarrativeClaimId.RISK_STRUCTURAL_WEAK.value not in payload["approved_claims"]
        def select(claim_id):
            spec = payload["approved_claims"][claim_id.value]
            return NarrativePointDraft(claim_id=claim_id, evidence_keys=list(spec["evidence_keys"]))
        return SimpleNamespace(
            status="completed",
            output_parsed=NarrativeDraft(
                canonical_anchors=NarrativeDraftAnchors(**payload["canonical_anchors"]),
                executive_summary=[select(NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION)],
                strengths=[],
                risks=[NarrativePointDraft(
                    claim_id=NarrativeClaimId.RISK_STRUCTURAL_WEAK,
                    evidence_keys=["decision.structural_band"],
                )],
                recommendations=[select(NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION)],
                caveats=[select(NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING)],
            ),
        )

class FakeClient:
    responses = FakeResponses()

result = build_validated_report_narrative(
    domain,
    config=NarrativeProviderConfig(model_id="test-model"),
    client=FakeClient(),
)
assert result.provenance.generation_mode == "deterministic_fallback"
assert result.provenance.fallback_reason == "semantic_invalid"
assert "weak" not in result.executive_summary.casefold()
''')
