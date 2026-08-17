from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
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

NARRATIVE_PROMPT_VERSION = "sitescore-narrative-prompt-v1"
NARRATIVE_SCHEMA_VERSION = "sitescore-narrative-v1"
NARRATIVE_FALLBACK_VERSION = "sitescore-narrative-fallback-v1"
NARRATIVE_PROVIDER = "openai"
NARRATIVE_MODEL_ENV = "SITESCORE_NARRATIVE_MODEL_ID"

NARRATIVE_INSTRUCTIONS = """SiteScore narrative contract.
Use only the supplied canonical report facts and approved evidence keys.
Never calculate or infer a new score, financial outcome, decision, confidence, benchmark, or readiness state.
Never invent missing evidence or silently replace unknown values with defaults.
Never claim empirical validation, proven market performance, calibration against real-world outcomes, guaranteed success, guaranteed profitability, financial guarantees, certainty, or risk-free outcomes.
Never output HTML or CSS.
Never introduce numeric, currency, or percentage literals in free-form prose.
Return only the strict structured schema requested by the API.
Every strength, risk, and recommendation must cite one or more supplied approved evidence keys.
Canonical anchors must be echoed exactly from the supplied context.
Recommendations are advisory prose only and must not assert a new canonical outcome.
"""

_NUMERIC_LITERAL = re.compile(r"(?:[$€£]\s*)?\d")
_PROHIBITED_CLAIMS = (
    "empirically validated",
    "proven in market",
    "proven in the market",
    "calibrated against real-world outcomes",
    "calibrated against real world outcomes",
    "financial guarantee",
    "guaranteed success",
    "guaranteed profitability",
    "guaranteed profit",
    "certain profitability",
    "risk-free",
    "risk free",
)
_HIGH_CERTAINTY_CLAIMS = (
    "high confidence",
    "highly certain",
    "near certain",
    "near-certain",
    "virtually certain",
)
_COMPLETE_EVIDENCE_CLAIMS = (
    "complete evidence",
    "complete data",
    "all evidence is complete",
    "all inputs are complete",
)
_EXPECTED_COVERAGE_KEYS = frozenset({"demand", "competition", "accessibility", "economics"})
_EXPECTED_INPUT_QUALITY_KEYS = frozenset({"rent", "price", "capacity", "schedule"})


class NarrativeDraftAnchors(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    decision_class: str
    structural_band: str
    financial_band: str
    confidence_label: str
    stress_test_failed: bool
    source_analysis_fingerprint: str


class NarrativePointDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(min_length=1, max_length=1200)
    evidence_keys: list[str] = Field(min_length=1, max_length=12)

    @field_validator("evidence_keys")
    @classmethod
    def _unique_evidence_keys(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_keys must be unique")
        return value


class NarrativeDraft(BaseModel):
    """Strict but still-untrusted structured provider output."""

    model_config = ConfigDict(extra="forbid", strict=True)

    canonical_anchors: NarrativeDraftAnchors
    executive_summary: str = Field(min_length=1, max_length=2400)
    strengths: list[NarrativePointDraft] = Field(max_length=12)
    risks: list[NarrativePointDraft] = Field(max_length=12)
    recommendations: list[NarrativePointDraft] = Field(max_length=12)
    caveats: list[str] = Field(max_length=12)

    @field_validator("caveats")
    @classmethod
    def _non_empty_caveats(cls, value: list[str]) -> list[str]:
        for item in value:
            if not item.strip():
                raise ValueError("caveats may not contain empty text")
        return value


@dataclass(frozen=True, slots=True)
class NarrativeCanonicalAnchors:
    decision_class: str
    structural_band: str
    financial_band: str
    confidence_label: str
    stress_test_failed: bool
    source_analysis_fingerprint: str


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ApprovedNarrativeContext:
    """Factory-owned bounded context derived only from a canonical report domain."""

    _report_domain_model: ReportDomainModel
    canonical_anchors: NarrativeCanonicalAnchors
    facts: Mapping[str, object]
    evidence: Mapping[str, object]

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
            "prompt_version": NARRATIVE_PROMPT_VERSION,
            "narrative_schema_version": NARRATIVE_SCHEMA_VERSION,
        }


@dataclass(frozen=True, slots=True)
class NarrativePoint:
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
    """Factory-owned narrative authority after deterministic semantic validation."""

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


def _context_semantics(value: ApprovedNarrativeContext) -> object:
    return (
        _semantic_record(value.canonical_anchors),
        _semantic_record(value.facts),
        _semantic_record(value.evidence),
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
        if value.facts is not binding[3] or value.evidence is not binding[4]:
            raise ValueError("narrative context fact/evidence identity integrity violation")
        if _context_semantics(value) != binding[5]:
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
        require_canonical_report_domain_model(domain)
        value = object.__new__(ApprovedNarrativeContext)
        object.__setattr__(value, "_report_domain_model", domain)
        object.__setattr__(value, "canonical_anchors", anchors)
        object.__setattr__(value, "facts", facts)
        object.__setattr__(value, "evidence", evidence)
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
        value = object.__new__(ValidatedReportNarrative)
        object.__setattr__(value, "_approved_context", approved)
        object.__setattr__(value, "provenance", provenance)
        object.__setattr__(value, "executive_summary", draft.executive_summary)
        object.__setattr__(
            value,
            "strengths",
            tuple(NarrativePoint(item.text, tuple(item.evidence_keys)) for item in draft.strengths),
        )
        object.__setattr__(
            value,
            "risks",
            tuple(NarrativePoint(item.text, tuple(item.evidence_keys)) for item in draft.risks),
        )
        object.__setattr__(
            value,
            "recommendations",
            tuple(NarrativePoint(item.text, tuple(item.evidence_keys)) for item in draft.recommendations),
        )
        object.__setattr__(value, "caveats", tuple(draft.caveats))
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


def _all_prose(draft: NarrativeDraft) -> tuple[str, ...]:
    return (
        draft.executive_summary,
        *(item.text for item in draft.strengths),
        *(item.text for item in draft.risks),
        *(item.text for item in draft.recommendations),
        *draft.caveats,
    )


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


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(phrase in lowered for phrase in phrases)


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

    for item in (*draft.strengths, *draft.risks, *draft.recommendations):
        for key in item.evidence_keys:
            if key not in approved.evidence:
                raise NarrativeSemanticError(f"unknown or unavailable evidence key: {key}")
            if not _present(approved.evidence[key]):
                raise NarrativeSemanticError(f"evidence key is not present: {key}")

    prose = _all_prose(draft)
    for text in prose:
        if _NUMERIC_LITERAL.search(text):
            raise NarrativeSemanticError("provider prose introduced a numeric/currency/percentage literal")
        lowered = text.casefold()
        if any(claim in lowered for claim in _PROHIBITED_CLAIMS):
            raise NarrativeSemanticError("provider prose contains a prohibited empirical/guarantee claim")

    combined = "\n".join(prose).casefold()
    domain = approved.report_domain_model
    decision = domain.decision
    financial = domain.financial
    confidence_label = domain.confidence.label.casefold()

    if decision.decision_class == "dead_end" and _contains(
        combined,
        ("prime opportunity", "strong opportunity", "strong location", "strong economics"),
    ):
        raise NarrativeSemanticError("narrative contradicts canonical dead_end decision")
    if decision.decision_class == "tourist_trap" and _contains(
        combined,
        ("strong economics", "financially strong", "healthy economics", "financially viable"),
    ):
        raise NarrativeSemanticError("narrative contradicts canonical tourist_trap decision")
    if decision.decision_class == "structural_risk" and _contains(
        combined,
        ("structurally strong", "strong location"),
    ):
        raise NarrativeSemanticError("narrative contradicts canonical structural_risk decision")
    if decision.financial_band == "non_viable" and _contains(
        combined,
        ("financially strong", "strong economics", "financially viable", "healthy economics"),
    ):
        raise NarrativeSemanticError("narrative contradicts canonical non_viable financial band")
    if financial.stress_test_failed and _contains(
        combined,
        ("stress test passed", "passes the stress test", "stress resilient", "stress-resilient"),
    ):
        raise NarrativeSemanticError("narrative contradicts canonical stress-test status")
    if financial.operating_margin_pct < 0 and _contains(
        combined,
        ("positive base operating margin", "positive operating margin"),
    ):
        raise NarrativeSemanticError("narrative contradicts canonical operating-margin sign")
    if "SEVERE_RENT_BURDEN" in decision.risk_flags and _contains(
        combined,
        ("rent burden is low", "low rent burden", "rent burden is healthy"),
    ):
        raise NarrativeSemanticError("narrative contradicts canonical rent-burden risk")

    if confidence_label != "high" and _contains(combined, _HIGH_CERTAINTY_CLAIMS):
        raise NarrativeSemanticError("narrative upgrades canonical confidence")
    if _quality_is_incomplete(domain) and _contains(combined, _COMPLETE_EVIDENCE_CLAIMS):
        raise NarrativeSemanticError("narrative claims complete evidence despite canonical missingness")

    return draft


class OpenAIResponsesNarrativeProvider:
    """Responses API adapter. Provider output remains untrusted until local validation."""

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


def build_deterministic_fallback_draft(
    context: ApprovedNarrativeContext,
) -> NarrativeDraft:
    approved = require_approved_narrative_context(context)
    domain = approved.report_domain_model
    strengths: list[NarrativePointDraft] = []
    risks: list[NarrativePointDraft] = []
    recommendations: list[NarrativePointDraft] = []

    if domain.decision.structural_band == "strong":
        strengths.append(
            NarrativePointDraft(
                text="The canonical structural band is strong.",
                evidence_keys=["decision.structural_band"],
            )
        )
    if domain.decision.financial_band == "strong":
        strengths.append(
            NarrativePointDraft(
                text="The canonical financial band is strong.",
                evidence_keys=["decision.financial_band"],
            )
        )

    risk_flag_text = {
        "HIGH_RENT_BURDEN": "Canonical risk flags identify elevated rent burden.",
        "SEVERE_RENT_BURDEN": "Canonical risk flags identify severe rent burden.",
        "STRESS_TEST_FAILED": "The canonical stress-test status indicates failure.",
        "NEGATIVE_BASE_OPERATING_MARGIN": "Canonical results identify a negative base operating margin.",
    }
    if domain.decision.risk_flags:
        for flag in domain.decision.risk_flags:
            text = risk_flag_text.get(flag, "A canonical risk flag remains active.")
            risks.append(NarrativePointDraft(text=text, evidence_keys=["decision.risk_flags"]))

    if domain.decision.financial_band == "non_viable":
        risks.append(
            NarrativePointDraft(
                text="The canonical financial band is non viable.",
                evidence_keys=["decision.financial_band"],
            )
        )
    if domain.decision.structural_band == "weak":
        risks.append(
            NarrativePointDraft(
                text="The canonical structural band is weak.",
                evidence_keys=["decision.structural_band"],
            )
        )

    if "SEVERE_RENT_BURDEN" in domain.decision.risk_flags or "HIGH_RENT_BURDEN" in domain.decision.risk_flags:
        recommendations.append(
            NarrativePointDraft(
                text="Review rent assumptions and lease terms before acting.",
                evidence_keys=["decision.risk_flags"],
            )
        )
    if "STRESS_TEST_FAILED" in domain.decision.risk_flags:
        recommendations.append(
            NarrativePointDraft(
                text="Review downside operating assumptions before acting.",
                evidence_keys=["decision.risk_flags"],
            )
        )
    if "NEGATIVE_BASE_OPERATING_MARGIN" in domain.decision.risk_flags:
        recommendations.append(
            NarrativePointDraft(
                text="Review cost and revenue assumptions before acting.",
                evidence_keys=["decision.risk_flags"],
            )
        )
    if domain.decision.decision_class == "structural_risk" or domain.decision.structural_band == "weak":
        recommendations.append(
            NarrativePointDraft(
                text="Treat the canonical structural condition as a decision constraint.",
                evidence_keys=["decision.decision_class", "decision.structural_band"],
            )
        )
    if not recommendations:
        recommendations.append(
            NarrativePointDraft(
                text="Review the canonical decision and supporting evidence before acting.",
                evidence_keys=["decision.decision_class"],
            )
        )

    caveats = [
        "Mathematically validated scoring engine; empirical validation pending.",
        "This narrative is a language layer and does not replace canonical report facts.",
    ]
    if domain.confidence.label != "high":
        caveats.append(
            f"Interpret the narrative conservatively because canonical confidence is {domain.confidence.label}."
        )
    if _quality_is_incomplete(domain):
        caveats.append("Some canonical evidence is unavailable or incomplete.")

    return NarrativeDraft(
        canonical_anchors=_draft_anchors(approved),
        executive_summary=f"{domain.decision.headline}. This summary preserves the canonical decision.",
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
    "NarrativeDraftAnchors",
    "NarrativePointDraft",
    "NarrativeDraft",
    "NarrativeCanonicalAnchors",
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
