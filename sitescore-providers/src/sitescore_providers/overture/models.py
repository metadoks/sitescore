"""Immutable Overture Places release, taxonomy, evidence, and measurement contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Any

from sitescore_data import AvailabilityState, DataQualityState
from sitescore_data.schemas.common import SourceMetadata

from .._validation import require_canonical_id, require_finite_number, require_nonempty_text, require_optional_nonempty_text
from ..artifacts import ArtifactRef, ParsedArtifact, RawAcquisitionArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from ..identity import ProviderIdentity, RequestFingerprint

OVERTURE_PROVIDER_KEY = "overture_places"
OVERTURE_DOMAIN = "competition"
OVERTURE_DATASET = "overture_places"
OVERTURE_THEME = "places"
OVERTURE_TYPE = "place"
OVERTURE_PARSER_ID = "overture_places_geoparquet_records"
OVERTURE_METHOD_VERSION = "competition_overture_v1"
OVERTURE_RELEASE_MANIFEST_GRAMMAR = "v1"
OVERTURE_TAXONOMY_MAPPING_GRAMMAR = "v1"
OVERTURE_ATTRIBUTION_GRAMMAR = "v1"
OVERTURE_CATCHMENT_POLICY_GRAMMAR = "v1"
OVERTURE_MEASUREMENT_GRAMMAR = "v1"
OVERTURE_TAXONOMY_RESOLUTION_POLICY_GRAMMAR = "v1"
OVERTURE_LIFECYCLE_POLICY_GRAMMAR = "v1"
OVERTURE_DEDUP_POLICY_GRAMMAR = "v1"


def _reject_mutable(value: str, *, field_name: str) -> str:
    require_nonempty_text(value, field_name=field_name)
    lowered = value.lower()
    if "latest" in lowered or "current" in lowered:
        raise ValueError(f"{field_name} must be explicitly pinned; mutable current/latest identity is forbidden")
    return value


def _require_tuple(values: tuple[Any, ...], *, field_name: str) -> tuple[Any, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    return values


@dataclass(frozen=True, slots=True)
class OverturePlacesReleaseManifest:
    manifest_version: str
    data_release: str
    schema_version: str
    taxonomy_id: str
    taxonomy_version: str
    acquisition_id: str
    acquisition_version: str
    parser_version: str
    theme: str = OVERTURE_THEME
    feature_type: str = OVERTURE_TYPE

    def __post_init__(self) -> None:
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        _reject_mutable(self.data_release, field_name="data_release")
        _reject_mutable(self.schema_version, field_name="schema_version")
        require_canonical_id(self.taxonomy_id, field_name="taxonomy_id")
        require_nonempty_text(self.taxonomy_version, field_name="taxonomy_version")
        require_canonical_id(self.acquisition_id, field_name="acquisition_id")
        require_nonempty_text(self.acquisition_version, field_name="acquisition_version")
        require_nonempty_text(self.parser_version, field_name="parser_version")
        if self.theme != OVERTURE_THEME or self.feature_type != OVERTURE_TYPE:
            raise ValueError("Checkpoint 3.3-4 manifest must identify theme=places and type=place")

    @property
    def provider_identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider_key=OVERTURE_PROVIDER_KEY,
            domain=OVERTURE_DOMAIN,
            dataset=OVERTURE_DATASET,
            dataset_release=self.data_release,
            vintage=None,
            schema_version=self.schema_version,
            parser_version=self.parser_version,
            method_version=OVERTURE_METHOD_VERSION,
        )

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": OVERTURE_RELEASE_MANIFEST_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "manifest_version": self.manifest_version,
            "data_release": self.data_release,
            "schema_version": self.schema_version,
            "theme": self.theme,
            "feature_type": self.feature_type,
            "taxonomy_id": self.taxonomy_id,
            "taxonomy_version": self.taxonomy_version,
            "acquisition_id": self.acquisition_id,
            "acquisition_version": self.acquisition_version,
            "parser_version": self.parser_version,
        })


class CommercialSemanticClass(StrEnum):
    RETAIL = "retail"
    FOOD_DRINK = "food_drink"
    PERSONAL_SERVICES = "personal_services"
    CUSTOMER_FACING_RECREATION_FITNESS = "customer_facing_recreation_fitness"
    LODGING = "lodging"
    MALLS_MARKETPLACES = "malls_marketplaces"
    HEALTHCARE = "healthcare"
    PROFESSIONAL_SERVICES = "professional_services"
    AUTOMOTIVE = "automotive"
    PAID_ATTRACTIONS = "paid_attractions"
    STANDALONE_EDUCATION = "standalone_education"
    RELIGIOUS = "religious"
    GOVERNMENT = "government"
    INDUSTRIAL = "industrial"
    OFFICE_ONLY = "office_only"
    TRANSIT = "transit"
    NATURAL_PUBLIC_ATTRACTIONS = "natural_public_attractions"


class CompetitionEligibilityState(StrEnum):
    INCLUDED = "included"
    CONDITIONAL = "conditional"
    EXCLUDED = "excluded"
    UNKNOWN = "unknown"


class TaxonomyMatchField(StrEnum):
    BASIC_CATEGORY = "basic_category"
    PRIMARY = "primary"
    HIERARCHY = "hierarchy"
    ALTERNATE = "alternate"




class AlternateDecisionRole(StrEnum):
    SUPPORTING_ONLY = "supporting_only"


class BasicCategoryFallbackRole(StrEnum):
    FALLBACK_QA = "fallback_qa"


@dataclass(frozen=True, slots=True)
class TaxonomyResolutionPolicy:
    policy_id: str
    policy_version: str
    field_precedence: tuple[TaxonomyMatchField, ...] = (
        TaxonomyMatchField.HIERARCHY,
        TaxonomyMatchField.PRIMARY,
        TaxonomyMatchField.BASIC_CATEGORY,
    )
    alternate_decision_role: AlternateDecisionRole = AlternateDecisionRole.SUPPORTING_ONLY
    basic_category_fallback_role: BasicCategoryFallbackRole = BasicCategoryFallbackRole.FALLBACK_QA
    conflict_semantics: str = "same_precedence_conflict_unknown"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        _require_tuple(self.field_precedence, field_name="field_precedence")
        if self.field_precedence != (TaxonomyMatchField.HIERARCHY, TaxonomyMatchField.PRIMARY, TaxonomyMatchField.BASIC_CATEGORY):
            raise ValueError("Checkpoint 3.3-4 V1 taxonomy precedence is fixed: hierarchy -> primary -> basic_category")
        if self.alternate_decision_role is not AlternateDecisionRole.SUPPORTING_ONLY:
            raise ValueError("ALTERNATE taxonomy matches are supporting-only in canonical V1 resolution")
        if self.basic_category_fallback_role is not BasicCategoryFallbackRole.FALLBACK_QA:
            raise ValueError("basic_category is fallback/QA evidence in canonical V1 resolution")
        if self.conflict_semantics != "same_precedence_conflict_unknown":
            raise ValueError("canonical V1 taxonomy conflict semantics are same-precedence conflict -> UNKNOWN")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": OVERTURE_TAXONOMY_RESOLUTION_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "field_precedence": tuple(x.value for x in self.field_precedence),
            "alternate_decision_role": self.alternate_decision_role.value,
            "basic_category_fallback_role": self.basic_category_fallback_role.value,
            "conflict_semantics": self.conflict_semantics,
        })


@dataclass(frozen=True, slots=True)
class OvertureTaxonomyRule:
    rule_id: str
    match_field: TaxonomyMatchField
    category: str
    semantic_class: CommercialSemanticClass
    eligibility: CompetitionEligibilityState
    condition_id: str | None = None
    conditional_qualifies: bool | None = None

    def __post_init__(self) -> None:
        require_canonical_id(self.rule_id, field_name="rule_id")
        if not isinstance(self.match_field, TaxonomyMatchField):
            raise TypeError("match_field must be a TaxonomyMatchField")
        require_canonical_id(self.category, field_name="category")
        if not isinstance(self.semantic_class, CommercialSemanticClass):
            raise TypeError("semantic_class must be a CommercialSemanticClass")
        if not isinstance(self.eligibility, CompetitionEligibilityState):
            raise TypeError("eligibility must be a CompetitionEligibilityState")
        require_optional_nonempty_text(self.condition_id, field_name="condition_id")
        if self.conditional_qualifies is not None and not isinstance(self.conditional_qualifies, bool):
            raise TypeError("conditional_qualifies must be a bool or None")
        if self.eligibility is CompetitionEligibilityState.CONDITIONAL:
            if self.condition_id is None:
                raise ValueError("CONDITIONAL taxonomy rules require condition_id")
        elif self.condition_id is not None or self.conditional_qualifies is not None:
            raise ValueError("only CONDITIONAL taxonomy rules may carry condition semantics")


@dataclass(frozen=True, slots=True)
class OvertureCompetitionTaxonomyMapping:
    mapping_id: str
    mapping_version: str
    release_manifest_identity: ContentHash
    taxonomy_id: str
    taxonomy_version: str
    resolution_policy: TaxonomyResolutionPolicy
    rules: tuple[OvertureTaxonomyRule, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.mapping_id, field_name="mapping_id")
        require_nonempty_text(self.mapping_version, field_name="mapping_version")
        if not isinstance(self.release_manifest_identity, ContentHash):
            raise TypeError("release_manifest_identity must be a ContentHash")
        require_canonical_id(self.taxonomy_id, field_name="taxonomy_id")
        require_nonempty_text(self.taxonomy_version, field_name="taxonomy_version")
        if not isinstance(self.resolution_policy, TaxonomyResolutionPolicy):
            raise TypeError("resolution_policy must be a TaxonomyResolutionPolicy")
        _require_tuple(self.rules, field_name="rules")
        if not self.rules:
            raise ValueError("taxonomy mapping requires at least one rule")
        for rule in self.rules:
            if not isinstance(rule, OvertureTaxonomyRule):
                raise TypeError("rules must contain OvertureTaxonomyRule values")
        ids = tuple(rule.rule_id for rule in self.rules)
        if len(ids) != len(set(ids)):
            raise ValueError("taxonomy rule_id values must be unique")
        keys = tuple((rule.match_field, rule.category) for rule in self.rules)
        if len(keys) != len(set(keys)):
            raise ValueError("taxonomy mapping must not duplicate one match_field/category pair")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": OVERTURE_TAXONOMY_MAPPING_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "mapping_id": self.mapping_id,
            "mapping_version": self.mapping_version,
            "release_manifest_identity": str(self.release_manifest_identity),
            "taxonomy_id": self.taxonomy_id,
            "taxonomy_version": self.taxonomy_version,
            "resolution_policy_identity": str(self.resolution_policy.identity),
            "rules": tuple({
                "rule_id": r.rule_id,
                "match_field": r.match_field.value,
                "category": r.category,
                "semantic_class": r.semantic_class.value,
                "eligibility": r.eligibility.value,
                "condition_id": r.condition_id,
                "conditional_qualifies": r.conditional_qualifies,
            } for r in sorted(self.rules, key=lambda x: x.rule_id)),
        })


class OvertureOperatingStatus(StrEnum):
    OPEN = "open"
    TEMPORARILY_CLOSED = "temporarily_closed"
    PERMANENTLY_CLOSED = "permanently_closed"
    UNKNOWN = "unknown"



@dataclass(frozen=True, slots=True)
class PlaceLifecyclePolicy:
    policy_id: str
    policy_version: str
    active_statuses: tuple[OvertureOperatingStatus, ...]
    excluded_statuses: tuple[OvertureOperatingStatus, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        for name, values in (("active_statuses", self.active_statuses), ("excluded_statuses", self.excluded_statuses)):
            _require_tuple(values, field_name=name)
            for value in values:
                if not isinstance(value, OvertureOperatingStatus):
                    raise TypeError(f"{name} must contain OvertureOperatingStatus values")
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not contain duplicates")
        if set(self.active_statuses) & set(self.excluded_statuses):
            raise ValueError("active/excluded lifecycle statuses must not overlap")
        if OvertureOperatingStatus.PERMANENTLY_CLOSED not in self.excluded_statuses:
            raise ValueError("permanently_closed must be excluded from active competition evidence")
        if OvertureOperatingStatus.UNKNOWN in self.active_statuses:
            raise ValueError("UNKNOWN operating status must not be silently active")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": OVERTURE_LIFECYCLE_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "active_statuses": tuple(sorted(x.value for x in self.active_statuses)),
            "excluded_statuses": tuple(sorted(x.value for x in self.excluded_statuses)),
        })


@dataclass(frozen=True, slots=True)
class OvertureSourceAttribution:
    dataset: str
    license_id: str | None
    record_id: str | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.dataset, field_name="dataset")
        require_optional_nonempty_text(self.license_id, field_name="license_id")
        require_optional_nonempty_text(self.record_id, field_name="record_id")


@dataclass(frozen=True, slots=True)
class OvertureAttributionManifest:
    manifest_id: str
    manifest_version: str
    release_manifest_identity: ContentHash
    sources: tuple[OvertureSourceAttribution, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.manifest_id, field_name="manifest_id")
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        if not isinstance(self.release_manifest_identity, ContentHash):
            raise TypeError("release_manifest_identity must be a ContentHash")
        _require_tuple(self.sources, field_name="sources")
        for source in self.sources:
            if not isinstance(source, OvertureSourceAttribution):
                raise TypeError("sources must contain OvertureSourceAttribution values")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": OVERTURE_ATTRIBUTION_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "manifest_id": self.manifest_id,
            "manifest_version": self.manifest_version,
            "release_manifest_identity": str(self.release_manifest_identity),
            "sources": tuple({"dataset": x.dataset, "license_id": x.license_id, "record_id": x.record_id}
                             for x in sorted(self.sources, key=lambda s: (s.dataset, s.license_id or "", s.record_id or ""))),
        })


@dataclass(frozen=True, slots=True)
class OverturePlaceEvidence:
    place_id: str
    longitude: float
    latitude: float
    basic_category: str | None
    taxonomy_primary: str | None
    taxonomy_hierarchy: tuple[str, ...]
    taxonomy_alternates: tuple[str, ...]
    operating_status: OvertureOperatingStatus
    confidence: float | None
    source_attributions: tuple[OvertureSourceAttribution, ...]
    release_manifest_identity: ContentHash
    raw_content_hash: ContentHash
    parsed_artifact_identity: ContentHash
    source_ref: str

    def __post_init__(self) -> None:
        require_nonempty_text(self.place_id, field_name="place_id")
        require_finite_number(self.longitude, field_name="longitude")
        require_finite_number(self.latitude, field_name="latitude")
        if not -180 <= float(self.longitude) <= 180:
            raise ValueError("longitude out of range")
        if not -90 <= float(self.latitude) <= 90:
            raise ValueError("latitude out of range")
        require_optional_nonempty_text(self.basic_category, field_name="basic_category")
        require_optional_nonempty_text(self.taxonomy_primary, field_name="taxonomy_primary")
        _require_tuple(self.taxonomy_hierarchy, field_name="taxonomy_hierarchy")
        _require_tuple(self.taxonomy_alternates, field_name="taxonomy_alternates")
        for field_name, values in (("taxonomy_hierarchy", self.taxonomy_hierarchy), ("taxonomy_alternates", self.taxonomy_alternates)):
            for value in values:
                require_canonical_id(value, field_name=f"{field_name} item")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
        if self.taxonomy_primary is not None:
            require_canonical_id(self.taxonomy_primary, field_name="taxonomy_primary")
            if self.taxonomy_hierarchy and self.taxonomy_hierarchy[-1] != self.taxonomy_primary:
                raise ValueError("taxonomy_primary must equal the final hierarchy entry")
        if self.basic_category is not None:
            require_canonical_id(self.basic_category, field_name="basic_category")
        if not isinstance(self.operating_status, OvertureOperatingStatus):
            raise TypeError("operating_status must be an OvertureOperatingStatus")
        if self.confidence is not None:
            require_finite_number(self.confidence, field_name="confidence")
            if not 0 <= float(self.confidence) <= 1:
                raise ValueError("confidence must be between 0 and 1")
        _require_tuple(self.source_attributions, field_name="source_attributions")
        for source in self.source_attributions:
            if not isinstance(source, OvertureSourceAttribution):
                raise TypeError("source_attributions must contain OvertureSourceAttribution")
        for value, name in ((self.release_manifest_identity, "release_manifest_identity"), (self.raw_content_hash, "raw_content_hash"), (self.parsed_artifact_identity, "parsed_artifact_identity")):
            if not isinstance(value, ContentHash):
                raise TypeError(f"{name} must be a ContentHash")
        require_canonical_id(self.source_ref, field_name="source_ref")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "place_id": self.place_id,
            "release_manifest_identity": str(self.release_manifest_identity),
            "raw_content_hash": str(self.raw_content_hash),
            "parsed_artifact_identity": str(self.parsed_artifact_identity),
        })


@dataclass(frozen=True, slots=True)
class TaxonomyEligibilityEvidence:
    place_id: str
    state: CompetitionEligibilityState
    matched_rule_ids: tuple[str, ...]
    semantic_classes: tuple[CommercialSemanticClass, ...]
    conditional_qualifies: bool | None
    mapping_identity: ContentHash

    def __post_init__(self) -> None:
        require_nonempty_text(self.place_id, field_name="place_id")
        if not isinstance(self.state, CompetitionEligibilityState):
            raise TypeError("state must be a CompetitionEligibilityState")
        _require_tuple(self.matched_rule_ids, field_name="matched_rule_ids")
        _require_tuple(self.semantic_classes, field_name="semantic_classes")
        for value in self.matched_rule_ids:
            require_canonical_id(value, field_name="matched_rule_id")
        for value in self.semantic_classes:
            if not isinstance(value, CommercialSemanticClass):
                raise TypeError("semantic_classes must contain CommercialSemanticClass values")
        if self.conditional_qualifies is not None and not isinstance(self.conditional_qualifies, bool):
            raise TypeError("conditional_qualifies must be bool or None")
        if self.state is not CompetitionEligibilityState.CONDITIONAL and self.conditional_qualifies is not None:
            raise ValueError("conditional_qualifies is only valid for CONDITIONAL state")
        if not isinstance(self.mapping_identity, ContentHash):
            raise TypeError("mapping_identity must be a ContentHash")

    @property
    def qualifies(self) -> bool | None:
        if self.state is CompetitionEligibilityState.INCLUDED:
            return True
        if self.state is CompetitionEligibilityState.EXCLUDED:
            return False
        if self.state is CompetitionEligibilityState.CONDITIONAL:
            return self.conditional_qualifies
        return None


@dataclass(frozen=True, slots=True)
class EntityDedupPolicy:
    policy_id: str
    policy_version: str
    identity_field: str = "overture_place_id_exact"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if self.identity_field != "overture_place_id_exact":
            raise ValueError("Checkpoint 3.3-4 supports exact Overture place ID dedup only")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": OVERTURE_DEDUP_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "identity_field": self.identity_field,
        })


class CoverageState(StrEnum):
    SUFFICIENT = "sufficient"
    UNKNOWN = "unknown"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class CompetitionCatchmentScale:
    scale_id: str
    travel_mode: str
    catchment_semantics: str
    travel_cost: float
    travel_cost_unit: str
    area_km2: float
    member_place_ids: tuple[str, ...]
    catchment_artifact_ref: str

    def __post_init__(self) -> None:
        require_canonical_id(self.scale_id, field_name="scale_id")
        require_canonical_id(self.travel_mode, field_name="travel_mode")
        require_canonical_id(self.catchment_semantics, field_name="catchment_semantics")
        require_finite_number(self.travel_cost, field_name="travel_cost")
        require_finite_number(self.area_km2, field_name="area_km2")
        if self.travel_cost <= 0 or self.area_km2 <= 0:
            raise ValueError("travel_cost and area_km2 must be > 0")
        require_nonempty_text(self.travel_cost_unit, field_name="travel_cost_unit")
        _require_tuple(self.member_place_ids, field_name="member_place_ids")
        for item in self.member_place_ids:
            require_nonempty_text(item, field_name="member_place_id")
        if len(set(self.member_place_ids)) != len(self.member_place_ids):
            raise ValueError("member_place_ids must not contain duplicates")
        require_nonempty_text(self.catchment_artifact_ref, field_name="catchment_artifact_ref")


@dataclass(frozen=True, slots=True)
class CompetitionCatchmentPolicy:
    policy_id: str
    policy_version: str
    spatial_predicate_id: str
    spatial_predicate_version: str
    projection_area_policy_id: str
    projection_area_policy_version: str
    scales: tuple[CompetitionCatchmentScale, ...]

    def __post_init__(self) -> None:
        for name in ("policy_id", "spatial_predicate_id", "projection_area_policy_id"):
            require_canonical_id(getattr(self, name), field_name=name)
        for name in ("policy_version", "spatial_predicate_version", "projection_area_policy_version"):
            require_nonempty_text(getattr(self, name), field_name=name)
        _require_tuple(self.scales, field_name="scales")
        if len(self.scales) < 2:
            raise ValueError("competition catchment policy requires at least two scales")
        for item in self.scales:
            if not isinstance(item, CompetitionCatchmentScale):
                raise TypeError("scales must contain CompetitionCatchmentScale values")
        ids = tuple(x.scale_id for x in self.scales)
        if len(ids) != len(set(ids)):
            raise ValueError("scale_id values must be unique")
        modes = {x.travel_mode for x in self.scales}
        if len(modes) != 1:
            raise ValueError("one competition curve must use one travel_mode")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": OVERTURE_CATCHMENT_POLICY_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "spatial_predicate_id": self.spatial_predicate_id,
            "spatial_predicate_version": self.spatial_predicate_version,
            "projection_area_policy_id": self.projection_area_policy_id,
            "projection_area_policy_version": self.projection_area_policy_version,
            "scales": tuple({
                "scale_id": x.scale_id, "travel_mode": x.travel_mode, "catchment_semantics": x.catchment_semantics,
                "travel_cost": x.travel_cost, "travel_cost_unit": x.travel_cost_unit,
            } for x in sorted(self.scales, key=lambda s: (s.travel_cost, s.scale_id))),
        })


@dataclass(frozen=True, slots=True)
class OverturePartitionEvidence:
    partition_id: str
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact
    source_metadata: SourceMetadata
    places: tuple[OverturePlaceEvidence, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.partition_id, field_name="partition_id")
        if not isinstance(self.raw_artifact, RawAcquisitionArtifact):
            raise TypeError("raw_artifact must be RawAcquisitionArtifact")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be ParsedArtifact")
        if self.parsed_artifact.raw_content_hash != self.raw_artifact.content_hash:
            raise ValueError("parsed artifact must bind to raw partition content hash")
        if self.parsed_artifact.parser_id != OVERTURE_PARSER_ID or self.parsed_artifact.parser_version != self.raw_artifact.provider_identity.parser_version:
            raise ValueError("parsed artifact parser identity must bind to Overture provider identity")
        if not isinstance(self.source_metadata, SourceMetadata):
            raise TypeError("source_metadata must be SourceMetadata")
        if self.source_metadata.content_hash != str(self.raw_artifact.content_hash):
            raise ValueError("source metadata content hash must bind to raw partition")
        identity = self.raw_artifact.provider_identity
        if (self.source_metadata.provider != identity.provider_key or self.source_metadata.dataset != identity.dataset
                or self.source_metadata.dataset_release != identity.dataset_release or self.source_metadata.vintage != identity.vintage
                or self.source_metadata.schema_version != identity.schema_version):
            raise ValueError("source metadata semantic identity must bind to raw partition provider identity")
        _require_tuple(self.places, field_name="places")
        for place in self.places:
            if not isinstance(place, OverturePlaceEvidence):
                raise TypeError("places must contain OverturePlaceEvidence")
            if place.raw_content_hash != self.raw_artifact.content_hash or place.parsed_artifact_identity != self.parsed_artifact.identity:
                raise ValueError("place lineage must bind to partition raw/parsed artifacts")
            if place.source_ref != self.source_metadata.source_id:
                raise ValueError("place source_ref must bind to partition SourceMetadata")


@dataclass(frozen=True, slots=True)
class CompetitionBuildEvidence:
    measurement_definition_id: str
    qualifying_entity_ids_by_scale: tuple[tuple[str, tuple[str, ...]], ...]
    source_refs: tuple[str, ...]
    coverage_state: CoverageState

    def __post_init__(self) -> None:
        require_canonical_id(self.measurement_definition_id, field_name="measurement_definition_id")
        if not isinstance(self.coverage_state, CoverageState):
            raise TypeError("coverage_state must be CoverageState")
