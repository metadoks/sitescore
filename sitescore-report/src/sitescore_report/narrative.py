from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal
from weakref import ref

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .domain import (
    ReportDomainModel,
    _json_safe,
    _semantic_record,
    require_canonical_report_domain_model,
)

NARRATIVE_PROMPT_VERSION = "sitescore-narrative-prompt-v2"
NARRATIVE_SCHEMA_VERSION = "sitescore-narrative-v2"
NARRATIVE_FALLBACK_VERSION = "sitescore-narrative-fallback-v2"
NARRATIVE_PROVIDER = "openai"
NARRATIVE_MODEL_ENV = "SITESCORE_NARRATIVE_MODEL_ID"

NARRATIVE_INSTRUCTIONS = """SiteScore narrative selection contract.
Use only the supplied canonical report facts, approved claim IDs, and the exact evidence-key list attached to each approved claim.
Do not write prose. The structured schema contains claim selections only; customer-facing text is rendered later from code-owned versioned templates.
Never calculate or infer a new score, financial outcome, decision, confidence, benchmark, readiness state, empirical conclusion, guarantee, certainty upgrade, or business fact.
Never invent a claim ID, evidence key, missing evidence, or alternate evidence binding.
Select only claim IDs present in approved_claims and echo each claim's evidence_keys exactly and in the supplied order.
Canonical anchors must be echoed exactly from the supplied context.
The model may choose emphasis and ordering among approved claims only.
Return only the strict structured schema requested by the API.
"""

_EXPECTED_COVERAGE_KEYS = frozenset({"demand", "competition", "accessibility", "economics"})
_EXPECTED_INPUT_QUALITY_KEYS = frozenset({"rent", "price", "capacity", "schedule"})

NarrativeSection = Literal[
    "executive_summary",
    "strength",
    "risk",
    "recommendation",
    "caveat",
]


class NarrativeClaimId(str, Enum):
    """Closed semantic vocabulary. Provider prose is never authoritative."""

    EXECUTIVE_CANONICAL_DECISION = "executive.canonical_decision"

    STRENGTH_STRUCTURAL_STRONG = "strength.structural_strong"
    STRENGTH_FINANCIAL_STRONG = "strength.financial_strong"
    STRENGTH_CONFIDENCE_HIGH = "strength.confidence_high"

    RISK_STRUCTURAL_WEAK = "risk.structural_weak"
    RISK_FINANCIAL_NON_VIABLE = "risk.financial_non_viable"
    RISK_HIGH_RENT_BURDEN = "risk.high_rent_burden"
    RISK_SEVERE_RENT_BURDEN = "risk.severe_rent_burden"
    RISK_STRESS_TEST_FAILED = "risk.stress_test_failed"
    RISK_NEGATIVE_BASE_MARGIN = "risk.negative_base_margin"

    RECOMMEND_REVIEW_RENT = "recommendation.review_rent"
    RECOMMEND_REVIEW_DOWNSIDE = "recommendation.review_downside"
    RECOMMEND_REVIEW_COST_REVENUE = "recommendation.review_cost_revenue"
    RECOMMEND_STRUCTURAL_CONSTRAINT = "recommendation.structural_constraint"
    RECOMMEND_REVIEW_CANONICAL_DECISION = "recommendation.review_canonical_decision"

    CAVEAT_EMPIRICAL_VALIDATION_PENDING = "caveat.empirical_validation_pending"
    CAVEAT_LANGUAGE_LAYER = "caveat.language_layer"
    CAVEAT_CONFIDENCE_NOT_HIGH = "caveat.confidence_not_high"
    CAVEAT_INCOMPLETE_EVIDENCE = "caveat.incomplete_evidence"


@dataclass(frozen=True, slots=True)
class _ClaimContract:
    section: NarrativeSection
    evidence_keys: tuple[str, ...]


_CLAIM_CONTRACT: Mapping[NarrativeClaimId, _ClaimContract] = MappingProxyType(
    {
        NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION: _ClaimContract(
            "executive_summary", ("decision.headline", "decision.decision_class")
        ),
        NarrativeClaimId.STRENGTH_STRUCTURAL_STRONG: _ClaimContract(
            "strength", ("decision.structural_band",)
        ),
        NarrativeClaimId.STRENGTH_FINANCIAL_STRONG: _ClaimContract(
            "strength", ("decision.financial_band",)
        ),
        NarrativeClaimId.STRENGTH_CONFIDENCE_HIGH: _ClaimContract(
            "strength", ("confidence.label",)
        ),
        NarrativeClaimId.RISK_STRUCTURAL_WEAK: _ClaimContract(
            "risk", ("decision.structural_band",)
        ),
        NarrativeClaimId.RISK_FINANCIAL_NON_VIABLE: _ClaimContract(
            "risk", ("decision.financial_band",)
        ),
        NarrativeClaimId.RISK_HIGH_RENT_BURDEN: _ClaimContract(
            "risk", ("decision.risk_flags",)
        ),
        NarrativeClaimId.RISK_SEVERE_RENT_BURDEN: _ClaimContract(
            "risk", ("decision.risk_flags",)
        ),
        NarrativeClaimId.RISK_STRESS_TEST_FAILED: _ClaimContract(
            "risk", ("financial.stress_test_failed",)
        ),
        NarrativeClaimId.RISK_NEGATIVE_BASE_MARGIN: _ClaimContract(
            "risk", ("decision.risk_flags",)
        ),
        NarrativeClaimId.RECOMMEND_REVIEW_RENT: _ClaimContract(
            "recommendation", ("decision.risk_flags",)
        ),
        NarrativeClaimId.RECOMMEND_REVIEW_DOWNSIDE: _ClaimContract(
            "recommendation", ("financial.stress_test_failed",)
        ),
        NarrativeClaimId.RECOMMEND_REVIEW_COST_REVENUE: _ClaimContract(
            "recommendation", ("decision.risk_flags",)
        ),
        NarrativeClaimId.RECOMMEND_STRUCTURAL_CONSTRAINT: _ClaimContract(
            "recommendation", ("decision.decision_class", "decision.structural_band")
        ),
        NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION: _ClaimContract(
            "recommendation", ("decision.decision_class",)
        ),
        NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING: _ClaimContract(
            "caveat", ()
        ),
        NarrativeClaimId.CAVEAT_LANGUAGE_LAYER: _ClaimContract("caveat", ()),
        NarrativeClaimId.CAVEAT_CONFIDENCE_NOT_HIGH: _ClaimContract(
            "caveat", ("confidence.label",)
        ),
        NarrativeClaimId.CAVEAT_INCOMPLETE_EVIDENCE: _ClaimContract("caveat", ()),
    }
)


class NarrativeDraftAnchors(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    decision_class: str
    structural_band: str
    financial_band: str
    confidence_label: str
    stress_test_failed: bool
    source_analysis_fingerprint: str


class NarrativePointDraft(BaseModel):
    """Untrusted provider selection from the closed code-owned claim vocabulary."""

    model_config = ConfigDict(extra="forbid", strict=True)

    claim_id: NarrativeClaimId
    evidence_keys: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("evidence_keys")
    @classmethod
    def _unique_evidence_keys(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_keys must be unique")
        return value


class NarrativeDraft(BaseModel):
    """Strict untrusted provider output containing no free-form prose fields."""

    model_config = ConfigDict(extra="forbid", strict=True)

    canonical_anchors: NarrativeDraftAnchors
    executive_summary: list[NarrativePointDraft] = Field(min_length=1, max_length=4)
    strengths: list[NarrativePointDraft] = Field(max_length=12)
    risks: list[NarrativePointDraft] = Field(max_length=12)
    recommendations: list[NarrativePointDraft] = Field(max_length=12)
    caveats: list[NarrativePointDraft] = Field(min_length=1, max_length=12)


@dataclass(frozen=True, slots=True)
class NarrativeCanonicalAnchors:
    decision_class: str
    structural_band: str
    financial_band: str
    confidence_label: str
    stress_test_failed: bool
    source_analysis_fingerprint: str


@dataclass(frozen=True, slots=True)
class NarrativeApprovedClaim:
    claim_id: NarrativeClaimId
    section: NarrativeSection
    evidence_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ApprovedNarrativeContext:
    """Factory-owned bounded context with only currently valid closed claims exposed."""

    _report_domain_model: ReportDomainModel
    canonical_anchors: NarrativeCanonicalAnchors
    facts: Mapping[str, object]
    evidence: Mapping[str, object]
    claims: Mapping[str, NarrativeApprovedClaim]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApprovedNarrativeContext is factory-owned; use build_approved_narrative_context"
        )

    @property
    def report_domain_model(self) -> ReportDomainModel:
        require_approved_narrative_context(self)
        return self._report_domain_model

    def to_dict(self) -> dict[str, Any]:
        require_approved_narrative_context(self)
        return {
            "canonical_anchors": _json_safe(self.canonical_anchors),
            "facts": _json_safe(self.facts),
            "approved_evidence": _json_safe(self.evidence),
            "approved_evidence_keys": sorted(self.evidence),
            "approved_claims": {
                claim_id: _json_safe(claim)
                for claim_id, claim in sorted(self.claims.items())
            },
            "prompt_version": NARRATIVE_PROMPT_VERSION,
            "narrative_schema_version": NARRATIVE_SCHEMA_VERSION,
        }


@dataclass(frozen=True, slots=True)
class NarrativePoint:
    claim_id: NarrativeClaimId
    text: str
    evidence_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NarrativeProvenance:
    generation_mode: Literal["llm", "deterministic_fallback"]
    provider: str
    model_id: str | None
    prompt_version: str
    narrative_schema_version: str
    fallback_version: str | None
    fallback_reason: str | None


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ValidatedReportNarrative:
    """Factory-owned authority rendered only from validated code-owned claim templates."""

    _approved_context: ApprovedNarrativeContext
    provenance: NarrativeProvenance
    executive_summary: str
    strengths: tuple[NarrativePoint, ...]
    risks: tuple[NarrativePoint, ...]
    recommendations: tuple[NarrativePoint, ...]
    caveats: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ValidatedReportNarrative is factory-owned; use build_validated_report_narrative"
        )

    @property
    def approved_context(self) -> ApprovedNarrativeContext:
        require_validated_report_narrative(self)
        return self._approved_context

    def to_dict(self) -> dict[str, Any]:
        require_validated_report_narrative(self)
        return {
            "provenance": _json_safe(self.provenance),
            "executive_summary": self.executive_summary,
            "strengths": _json_safe(self.strengths),
            "risks": _json_safe(self.risks),
            "recommendations": _json_safe(self.recommendations),
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True, slots=True)
class NarrativeProviderConfig:
    model_id: str | None
    provider: str = NARRATIVE_PROVIDER

    @classmethod
    def from_environment(cls) -> "NarrativeProviderConfig":
        model_id = os.environ.get(NARRATIVE_MODEL_ENV)
        if model_id is not None:
            model_id = model_id.strip() or None
        return cls(model_id=model_id)


class NarrativeProviderFailure(RuntimeError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        super().__init__(message or reason)
        self.reason = reason


class NarrativeSemanticError(ValueError):
    pass


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (tuple, list, Mapping)) and not value:
        return False
    return True


def _quality_is_incomplete(domain: ReportDomainModel) -> bool:
    coverage = domain.data_quality.data_coverage
    inputs = domain.data_quality.input_qualities
    if set(coverage) != _EXPECTED_COVERAGE_KEYS:
        return True
    if set(inputs) != _EXPECTED_INPUT_QUALITY_KEYS:
        return True
    for value in tuple(coverage.values()) + tuple(inputs.values()):
        raw = getattr(value, "value", value)
        if str(raw).casefold() in {"missing", "unknown", "degraded"}:
            return True
    return domain.data_quality.data_age_years is None


def _build_evidence(domain: ReportDomainModel) -> Mapping[str, object]:
    evidence: dict[str, object] = {
        "analysis.sector": domain.analysis.sector,
        "category_scores.demand": domain.category_scores.demand,
        "category_scores.competition": domain.category_scores.competition,
        "category_scores.accessibility": domain.category_scores.accessibility,
        "category_scores.economics": domain.category_scores.economics,
        "business_assumptions.monthly_rent": domain.business_assumptions.monthly_rent,
        "business_assumptions.fixed_labor": domain.business_assumptions.fixed_labor,
        "business_assumptions.fixed_overhead": domain.business_assumptions.fixed_overhead,
        "location.base_score": domain.location.base_score,
        "location.penalty_multiplier": domain.location.penalty_multiplier,
        "location.final_score": domain.location.final_score,
        "location.structural_band": domain.location.structural_band,
        "financial.revenue.conservative": domain.financial.revenue.conservative,
        "financial.revenue.base": domain.financial.revenue.base,
        "financial.revenue.optimistic": domain.financial.revenue.optimistic,
        "financial.variable_cost_base": domain.financial.variable_cost_base,
        "financial.contribution_margin_base": domain.financial.contribution_margin_base,
        "financial.fixed_costs": domain.financial.fixed_costs,
        "financial.operating_profit_base": domain.financial.operating_profit_base,
        "financial.break_even_revenue": domain.financial.break_even_revenue,
        "financial.bec_base": domain.financial.bec_base,
        "financial.bec_conservative": domain.financial.bec_conservative,
        "financial.rent_burden_pct": domain.financial.rent_burden_pct,
        "financial.rent_burden_severity": domain.financial.rent_burden_severity,
        "financial.operating_margin_pct": domain.financial.operating_margin_pct,
        "financial.stress_test_failed": domain.financial.stress_test_failed,
        "decision.decision_class": domain.decision.decision_class,
        "decision.structural_band": domain.decision.structural_band,
        "decision.financial_band": domain.decision.financial_band,
        "decision.headline": domain.decision.headline,
        "confidence.label": domain.confidence.label,
        "data_quality.geographic_level": domain.data_quality.geographic_level,
        "provenance.source_analysis_fingerprint": domain.provenance.source_analysis_fingerprint,
    }
    optional = {
        "location.dominant_risk_category": domain.location.dominant_risk_category,
        "financial.break_even_volume": domain.financial.break_even_volume,
        "decision.risk_flags": domain.decision.risk_flags,
        "data_quality.data_age_years": domain.data_quality.data_age_years,
    }
    for key, value in optional.items():
        if _present(value):
            evidence[key] = value
    for key, value in domain.data_quality.data_coverage.items():
        if value is not None:
            evidence[f"data_quality.data_coverage.{key}"] = value
    for key, value in domain.data_quality.input_qualities.items():
        if value is not None:
            evidence[f"data_quality.input_qualities.{key}"] = value
    return MappingProxyType(evidence)


def _claim_is_active(claim_id: NarrativeClaimId, domain: ReportDomainModel) -> bool:
    if claim_id is NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION:
        return True
    if claim_id is NarrativeClaimId.STRENGTH_STRUCTURAL_STRONG:
        return domain.decision.structural_band == "strong"
    if claim_id is NarrativeClaimId.STRENGTH_FINANCIAL_STRONG:
        return domain.decision.financial_band == "strong"
    if claim_id is NarrativeClaimId.STRENGTH_CONFIDENCE_HIGH:
        return domain.confidence.label == "high"
    if claim_id is NarrativeClaimId.RISK_STRUCTURAL_WEAK:
        return domain.decision.structural_band == "weak"
    if claim_id is NarrativeClaimId.RISK_FINANCIAL_NON_VIABLE:
        return domain.decision.financial_band == "non_viable"
    if claim_id is NarrativeClaimId.RISK_HIGH_RENT_BURDEN:
        return "HIGH_RENT_BURDEN" in domain.decision.risk_flags
    if claim_id is NarrativeClaimId.RISK_SEVERE_RENT_BURDEN:
        return "SEVERE_RENT_BURDEN" in domain.decision.risk_flags
    if claim_id is NarrativeClaimId.RISK_STRESS_TEST_FAILED:
        return domain.financial.stress_test_failed is True
    if claim_id is NarrativeClaimId.RISK_NEGATIVE_BASE_MARGIN:
        return "NEGATIVE_BASE_OPERATING_MARGIN" in domain.decision.risk_flags
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_RENT:
        return bool({"HIGH_RENT_BURDEN", "SEVERE_RENT_BURDEN"} & set(domain.decision.risk_flags))
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_DOWNSIDE:
        return domain.financial.stress_test_failed is True
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_COST_REVENUE:
        return "NEGATIVE_BASE_OPERATING_MARGIN" in domain.decision.risk_flags
    if claim_id is NarrativeClaimId.RECOMMEND_STRUCTURAL_CONSTRAINT:
        return domain.decision.structural_band == "weak" or domain.decision.decision_class == "structural_risk"
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION:
        return True
    if claim_id in {
        NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING,
        NarrativeClaimId.CAVEAT_LANGUAGE_LAYER,
    }:
        return True
    if claim_id is NarrativeClaimId.CAVEAT_CONFIDENCE_NOT_HIGH:
        return domain.confidence.label != "high"
    if claim_id is NarrativeClaimId.CAVEAT_INCOMPLETE_EVIDENCE:
        return _quality_is_incomplete(domain)
    raise AssertionError(f"unhandled narrative claim: {claim_id}")


def _render_claim(claim_id: NarrativeClaimId, domain: ReportDomainModel) -> str:
    if claim_id is NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION:
        return f"Canonical decision: {domain.decision.headline}."
    if claim_id is NarrativeClaimId.STRENGTH_STRUCTURAL_STRONG:
        return "The canonical structural band is strong."
    if claim_id is NarrativeClaimId.STRENGTH_FINANCIAL_STRONG:
        return "The canonical financial band is strong."
    if claim_id is NarrativeClaimId.STRENGTH_CONFIDENCE_HIGH:
        return "Canonical confidence is high."
    if claim_id is NarrativeClaimId.RISK_STRUCTURAL_WEAK:
        return "The canonical structural band is weak."
    if claim_id is NarrativeClaimId.RISK_FINANCIAL_NON_VIABLE:
        return "The canonical financial band is non viable."
    if claim_id is NarrativeClaimId.RISK_HIGH_RENT_BURDEN:
        return "Canonical risk flags identify elevated rent burden."
    if claim_id is NarrativeClaimId.RISK_SEVERE_RENT_BURDEN:
        return "Canonical risk flags identify severe rent burden."
    if claim_id is NarrativeClaimId.RISK_STRESS_TEST_FAILED:
        return "The canonical stress-test status indicates failure."
    if claim_id is NarrativeClaimId.RISK_NEGATIVE_BASE_MARGIN:
        return "Canonical risk flags identify a negative base operating margin."
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_RENT:
        return "Review rent assumptions and lease terms before acting."
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_DOWNSIDE:
        return "Review downside operating assumptions before acting."
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_COST_REVENUE:
        return "Review cost and revenue assumptions before acting."
    if claim_id is NarrativeClaimId.RECOMMEND_STRUCTURAL_CONSTRAINT:
        return "Treat the canonical structural condition as a decision constraint."
    if claim_id is NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION:
        return "Review the canonical decision and supporting evidence before acting."
    if claim_id is NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING:
        return "Mathematically validated scoring engine; empirical validation pending."
    if claim_id is NarrativeClaimId.CAVEAT_LANGUAGE_LAYER:
        return "This narrative is a language layer and does not replace canonical report facts."
    if claim_id is NarrativeClaimId.CAVEAT_CONFIDENCE_NOT_HIGH:
        return f"Canonical confidence is {domain.confidence.label}; interpret the narrative conservatively."
    if claim_id is NarrativeClaimId.CAVEAT_INCOMPLETE_EVIDENCE:
        return "Some canonical evidence is unavailable or incomplete."
    raise AssertionError(f"unhandled narrative claim: {claim_id}")


def _build_claims(domain: ReportDomainModel) -> Mapping[str, NarrativeApprovedClaim]:
    claims: dict[str, NarrativeApprovedClaim] = {}
    for claim_id, contract in _CLAIM_CONTRACT.items():
        if not _claim_is_active(claim_id, domain):
            continue
        for key in contract.evidence_keys:
            if key not in _build_evidence(domain):
                raise ValueError(f"active narrative claim lacks required evidence: {claim_id.value}:{key}")
        claims[claim_id.value] = NarrativeApprovedClaim(
            claim_id=claim_id,
            section=contract.section,
            evidence_keys=contract.evidence_keys,
        )
    return MappingProxyType(claims)


def _context_semantics(value: ApprovedNarrativeContext) -> object:
    return (
        _semantic_record(value.canonical_anchors),
        _semantic_record(value.facts),
        _semantic_record(value.evidence),
        _semantic_record(value.claims),
    )


def _narrative_semantics(value: ValidatedReportNarrative) -> object:
    return (
        _semantic_record(value.provenance),
        _semantic_record(value.executive_summary),
        _semantic_record(value.strengths),
        _semantic_record(value.risks),
        _semantic_record(value.recommendations),
        _semantic_record(value.caveats),
    )


def _install_narrative_factories():
    context_bindings: dict[int, tuple[object, ...]] = {}
    narrative_bindings: dict[int, tuple[object, ...]] = {}

    def register_context(value: ApprovedNarrativeContext, domain: ReportDomainModel) -> None:
        object_id = id(value)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            context_bindings.pop(object_id, None)

        context_bindings[object_id] = (
            ref(value, cleanup),
            domain,
            value.canonical_anchors,
            value.facts,
            value.evidence,
            value.claims,
            _context_semantics(value),
        )

    def require_context(value: ApprovedNarrativeContext) -> ApprovedNarrativeContext:
        if not isinstance(value, ApprovedNarrativeContext):
            raise TypeError("value must be ApprovedNarrativeContext")
        binding = context_bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("narrative context is not canonical/factory-owned")
        domain = binding[1]
        require_canonical_report_domain_model(domain)
        if value._report_domain_model is not domain:
            raise ValueError("narrative context report-domain binding integrity violation")
        if value.canonical_anchors is not binding[2]:
            raise ValueError("narrative context anchor identity integrity violation")
        if value.facts is not binding[3] or value.evidence is not binding[4] or value.claims is not binding[5]:
            raise ValueError("narrative context fact/evidence/claim identity integrity violation")
        if _context_semantics(value) != binding[6]:
            raise ValueError("narrative context semantic integrity violation")
        return value

    def build_context(domain_model: ReportDomainModel) -> ApprovedNarrativeContext:
        domain = require_canonical_report_domain_model(domain_model)
        anchors = NarrativeCanonicalAnchors(
            decision_class=domain.decision.decision_class,
            structural_band=domain.decision.structural_band,
            financial_band=domain.decision.financial_band,
            confidence_label=domain.confidence.label,
            stress_test_failed=domain.financial.stress_test_failed,
            source_analysis_fingerprint=domain.provenance.source_analysis_fingerprint,
        )
        facts = _freeze(domain.to_dict())
        evidence = _build_evidence(domain)
        claims = _build_claims(domain)
        require_canonical_report_domain_model(domain)
        value = object.__new__(ApprovedNarrativeContext)
        object.__setattr__(value, "_report_domain_model", domain)
        object.__setattr__(value, "canonical_anchors", anchors)
        object.__setattr__(value, "facts", facts)
        object.__setattr__(value, "evidence", evidence)
        object.__setattr__(value, "claims", claims)
        register_context(value, domain)
        return value

    def register_narrative(
        value: ValidatedReportNarrative,
        context: ApprovedNarrativeContext,
    ) -> None:
        object_id = id(value)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            narrative_bindings.pop(object_id, None)

        narrative_bindings[object_id] = (
            ref(value, cleanup),
            context,
            value.provenance,
            value.strengths,
            value.risks,
            value.recommendations,
            value.caveats,
            _narrative_semantics(value),
        )

    def require_narrative(value: ValidatedReportNarrative) -> ValidatedReportNarrative:
        if not isinstance(value, ValidatedReportNarrative):
            raise TypeError("value must be ValidatedReportNarrative")
        binding = narrative_bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("validated narrative is not canonical/factory-owned")
        context = binding[1]
        require_context(context)
        if value._approved_context is not context:
            raise ValueError("validated narrative context binding integrity violation")
        for current, expected, label in (
            (value.provenance, binding[2], "provenance"),
            (value.strengths, binding[3], "strengths"),
            (value.risks, binding[4], "risks"),
            (value.recommendations, binding[5], "recommendations"),
            (value.caveats, binding[6], "caveats"),
        ):
            if current is not expected:
                raise ValueError(f"validated narrative {label} identity integrity violation")
        if _narrative_semantics(value) != binding[7]:
            raise ValueError("validated narrative semantic integrity violation")
        return value

    def build_final(
        context: ApprovedNarrativeContext,
        draft: NarrativeDraft,
        provenance: NarrativeProvenance,
    ) -> ValidatedReportNarrative:
        approved = require_context(context)
        validate_narrative_draft(approved, draft)
        domain = approved.report_domain_model

        def point(item: NarrativePointDraft) -> NarrativePoint:
            spec = approved.claims[item.claim_id.value]
            return NarrativePoint(
                claim_id=item.claim_id,
                text=_render_claim(item.claim_id, domain),
                evidence_keys=spec.evidence_keys,
            )

        value = object.__new__(ValidatedReportNarrative)
        object.__setattr__(value, "_approved_context", approved)
        object.__setattr__(value, "provenance", provenance)
        object.__setattr__(
            value,
            "executive_summary",
            " ".join(_render_claim(item.claim_id, domain) for item in draft.executive_summary),
        )
        object.__setattr__(value, "strengths", tuple(point(item) for item in draft.strengths))
        object.__setattr__(value, "risks", tuple(point(item) for item in draft.risks))
        object.__setattr__(
            value, "recommendations", tuple(point(item) for item in draft.recommendations)
        )
        object.__setattr__(
            value,
            "caveats",
            tuple(_render_claim(item.claim_id, domain) for item in draft.caveats),
        )
        register_narrative(value, approved)
        return value

    return build_context, require_context, build_final, require_narrative


(
    build_approved_narrative_context,
    require_approved_narrative_context,
    _build_final_validated_narrative,
    require_validated_report_narrative,
) = _install_narrative_factories()
del _install_narrative_factories


def _validate_section(
    approved: ApprovedNarrativeContext,
    items: list[NarrativePointDraft],
    section: NarrativeSection,
) -> None:
    seen: set[NarrativeClaimId] = set()
    for item in items:
        if item.claim_id in seen:
            raise NarrativeSemanticError(f"duplicate narrative claim: {item.claim_id.value}")
        seen.add(item.claim_id)
        spec = approved.claims.get(item.claim_id.value)
        if spec is None:
            raise NarrativeSemanticError(
                f"claim is not authorized by canonical source state: {item.claim_id.value}"
            )
        if spec.section != section:
            raise NarrativeSemanticError(
                f"claim is not authorized for section {section}: {item.claim_id.value}"
            )
        if tuple(item.evidence_keys) != spec.evidence_keys:
            raise NarrativeSemanticError(
                f"claim/evidence binding mismatch: {item.claim_id.value}"
            )
        for key in spec.evidence_keys:
            if key not in approved.evidence or not _present(approved.evidence[key]):
                raise NarrativeSemanticError(
                    f"claim evidence is unavailable: {item.claim_id.value}:{key}"
                )


def validate_narrative_draft(
    context: ApprovedNarrativeContext,
    draft: NarrativeDraft,
) -> NarrativeDraft:
    approved = require_approved_narrative_context(context)
    if not isinstance(draft, NarrativeDraft):
        raise TypeError("draft must be NarrativeDraft")

    anchors = draft.canonical_anchors
    expected = approved.canonical_anchors
    for name in (
        "decision_class",
        "structural_band",
        "financial_band",
        "confidence_label",
        "stress_test_failed",
        "source_analysis_fingerprint",
    ):
        if getattr(anchors, name) != getattr(expected, name):
            raise NarrativeSemanticError(f"canonical anchor mismatch: {name}")

    _validate_section(approved, draft.executive_summary, "executive_summary")
    _validate_section(approved, draft.strengths, "strength")
    _validate_section(approved, draft.risks, "risk")
    _validate_section(approved, draft.recommendations, "recommendation")
    _validate_section(approved, draft.caveats, "caveat")
    return draft


class OpenAIResponsesNarrativeProvider:
    """Responses API adapter. Provider selections remain untrusted until local validation."""

    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def generate(
        self,
        context: ApprovedNarrativeContext,
        config: NarrativeProviderConfig,
    ) -> NarrativeDraft:
        approved = require_approved_narrative_context(context)
        if config.provider != NARRATIVE_PROVIDER:
            raise NarrativeProviderFailure("provider_unconfigured", "unsupported narrative provider")
        if not config.model_id:
            raise NarrativeProviderFailure("provider_unconfigured", "narrative model is not configured")

        client = self._client
        if client is None:
            from openai import OpenAI

            client = OpenAI()

        payload = json.dumps(
            approved.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        try:
            response = client.responses.parse(
                model=config.model_id,
                instructions=NARRATIVE_INSTRUCTIONS,
                input=payload,
                text_format=NarrativeDraft,
                tools=[],
                store=False,
            )
        except ValidationError as exc:
            raise NarrativeProviderFailure("schema_invalid") from exc
        except Exception as exc:
            raise NarrativeProviderFailure("provider_exception") from exc

        status = getattr(response, "status", None)
        if status is not None and status != "completed":
            raise NarrativeProviderFailure("provider_incomplete")
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise NarrativeProviderFailure("provider_refusal_or_empty")
        if isinstance(parsed, NarrativeDraft):
            return parsed
        try:
            return NarrativeDraft.model_validate(parsed, strict=True)
        except ValidationError as exc:
            raise NarrativeProviderFailure("schema_invalid") from exc


def _draft_anchors(context: ApprovedNarrativeContext) -> NarrativeDraftAnchors:
    anchors = context.canonical_anchors
    return NarrativeDraftAnchors(
        decision_class=anchors.decision_class,
        structural_band=anchors.structural_band,
        financial_band=anchors.financial_band,
        confidence_label=anchors.confidence_label,
        stress_test_failed=anchors.stress_test_failed,
        source_analysis_fingerprint=anchors.source_analysis_fingerprint,
    )


def _selection(
    context: ApprovedNarrativeContext,
    claim_id: NarrativeClaimId,
) -> NarrativePointDraft:
    spec = context.claims.get(claim_id.value)
    if spec is None:
        raise ValueError(f"fallback attempted inactive narrative claim: {claim_id.value}")
    return NarrativePointDraft(claim_id=claim_id, evidence_keys=list(spec.evidence_keys))


def build_deterministic_fallback_draft(
    context: ApprovedNarrativeContext,
) -> NarrativeDraft:
    approved = require_approved_narrative_context(context)

    strengths = [
        _selection(approved, claim_id)
        for claim_id in (
            NarrativeClaimId.STRENGTH_STRUCTURAL_STRONG,
            NarrativeClaimId.STRENGTH_FINANCIAL_STRONG,
            NarrativeClaimId.STRENGTH_CONFIDENCE_HIGH,
        )
        if claim_id.value in approved.claims
    ]
    risks = [
        _selection(approved, claim_id)
        for claim_id in (
            NarrativeClaimId.RISK_STRUCTURAL_WEAK,
            NarrativeClaimId.RISK_FINANCIAL_NON_VIABLE,
            NarrativeClaimId.RISK_HIGH_RENT_BURDEN,
            NarrativeClaimId.RISK_SEVERE_RENT_BURDEN,
            NarrativeClaimId.RISK_STRESS_TEST_FAILED,
            NarrativeClaimId.RISK_NEGATIVE_BASE_MARGIN,
        )
        if claim_id.value in approved.claims
    ]
    recommendations = [
        _selection(approved, claim_id)
        for claim_id in (
            NarrativeClaimId.RECOMMEND_REVIEW_RENT,
            NarrativeClaimId.RECOMMEND_REVIEW_DOWNSIDE,
            NarrativeClaimId.RECOMMEND_REVIEW_COST_REVENUE,
            NarrativeClaimId.RECOMMEND_STRUCTURAL_CONSTRAINT,
        )
        if claim_id.value in approved.claims
    ]
    if not recommendations:
        recommendations = [
            _selection(approved, NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION)
        ]

    caveat_ids = [
        NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING,
        NarrativeClaimId.CAVEAT_LANGUAGE_LAYER,
        NarrativeClaimId.CAVEAT_CONFIDENCE_NOT_HIGH,
        NarrativeClaimId.CAVEAT_INCOMPLETE_EVIDENCE,
    ]
    caveats = [
        _selection(approved, claim_id)
        for claim_id in caveat_ids
        if claim_id.value in approved.claims
    ]

    return NarrativeDraft(
        canonical_anchors=_draft_anchors(approved),
        executive_summary=[
            _selection(approved, NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION)
        ],
        strengths=strengths,
        risks=risks,
        recommendations=recommendations,
        caveats=caveats,
    )


def _provenance(
    *,
    mode: Literal["llm", "deterministic_fallback"],
    config: NarrativeProviderConfig,
    fallback_reason: str | None,
) -> NarrativeProvenance:
    return NarrativeProvenance(
        generation_mode=mode,
        provider=config.provider,
        model_id=config.model_id,
        prompt_version=NARRATIVE_PROMPT_VERSION,
        narrative_schema_version=NARRATIVE_SCHEMA_VERSION,
        fallback_version=(NARRATIVE_FALLBACK_VERSION if mode == "deterministic_fallback" else None),
        fallback_reason=fallback_reason,
    )


def build_validated_report_narrative(
    report_domain_model: ReportDomainModel,
    *,
    config: NarrativeProviderConfig | None = None,
    client: object | None = None,
) -> ValidatedReportNarrative:
    domain = require_canonical_report_domain_model(report_domain_model)
    context = build_approved_narrative_context(domain)
    provider_config = config or NarrativeProviderConfig.from_environment()

    if not provider_config.model_id:
        fallback = build_deterministic_fallback_draft(context)
        return _build_final_validated_narrative(
            context,
            fallback,
            _provenance(
                mode="deterministic_fallback",
                config=provider_config,
                fallback_reason="provider_unconfigured",
            ),
        )

    provider = OpenAIResponsesNarrativeProvider(client=client)
    try:
        draft = provider.generate(context, provider_config)
        validate_narrative_draft(context, draft)
    except NarrativeProviderFailure as exc:
        fallback = build_deterministic_fallback_draft(context)
        return _build_final_validated_narrative(
            context,
            fallback,
            _provenance(
                mode="deterministic_fallback",
                config=provider_config,
                fallback_reason=exc.reason,
            ),
        )
    except NarrativeSemanticError:
        fallback = build_deterministic_fallback_draft(context)
        return _build_final_validated_narrative(
            context,
            fallback,
            _provenance(
                mode="deterministic_fallback",
                config=provider_config,
                fallback_reason="semantic_invalid",
            ),
        )

    return _build_final_validated_narrative(
        context,
        draft,
        _provenance(mode="llm", config=provider_config, fallback_reason=None),
    )


__all__ = [
    "NARRATIVE_PROMPT_VERSION",
    "NARRATIVE_SCHEMA_VERSION",
    "NARRATIVE_FALLBACK_VERSION",
    "NARRATIVE_PROVIDER",
    "NARRATIVE_MODEL_ENV",
    "NARRATIVE_INSTRUCTIONS",
    "NarrativeClaimId",
    "NarrativeDraftAnchors",
    "NarrativePointDraft",
    "NarrativeDraft",
    "NarrativeCanonicalAnchors",
    "NarrativeApprovedClaim",
    "ApprovedNarrativeContext",
    "NarrativePoint",
    "NarrativeProvenance",
    "ValidatedReportNarrative",
    "NarrativeProviderConfig",
    "NarrativeProviderFailure",
    "NarrativeSemanticError",
    "build_approved_narrative_context",
    "require_approved_narrative_context",
    "validate_narrative_draft",
    "OpenAIResponsesNarrativeProvider",
    "build_deterministic_fallback_draft",
    "build_validated_report_narrative",
    "require_validated_report_narrative",
]
