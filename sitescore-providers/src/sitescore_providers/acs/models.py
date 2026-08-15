"""Immutable ACS dataset, variable, geography, and statistical evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math
from enum import StrEnum
from typing import Iterable

from sitescore_data import GeographyType
from sitescore_data.schemas.geography import GeographyRef

from .._validation import require_canonical_id, require_nonempty_text, require_optional_nonempty_text
from ..artifacts import ParsedArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from ..identity import RequestFingerprint

ACS_PROVIDER_KEY = "us_census_acs"
ACS_API_BASE_URL = "https://api.census.gov/data"
ACS_MANIFEST_GRAMMAR_VERSION = "v1"
ACS_VARIABLE_MANIFEST_GRAMMAR_VERSION = "v1"
ACS_GEOGRAPHY_COMPATIBILITY_GRAMMAR_VERSION = "v1"
ACS_AGE_POLICY_GRAMMAR_VERSION = "v1"
ACS_EVIDENCE_GRAMMAR_VERSION = "v1"
ACS_REQUEST_MAX_VARIABLES = 50


class ACSProduct(StrEnum):
    DETAILED_TABLES = "detailed_tables"


class ACSVariableRole(StrEnum):
    TOTAL_POPULATION = "total_population"
    AGE_COMPONENT = "age_component"
    HOUSEHOLD_INCOME = "household_income"


class ACSStatisticalValueState(StrEnum):
    VALUE = "value"
    MISSING = "missing"
    SUPPRESSED = "suppressed"
    NOT_APPLICABLE = "not_applicable"
    CONTROLLED = "controlled"
    ANNOTATED = "annotated"
    UNKNOWN_SPECIAL = "unknown_special"


class ACSGeographyRequestState(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


class ACSRowState(StrEnum):
    FOUND = "found"
    NO_DATA = "no_data"


def _reject_mutable_release(value: str, *, field_name: str) -> str:
    require_nonempty_text(value, field_name=field_name)
    lowered = value.lower()
    if "current" in lowered or "latest" in lowered:
        raise ValueError(f"{field_name} must be explicitly pinned; mutable current/latest identity is forbidden")
    return value


def _require_variable_id(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    require_nonempty_text(value, field_name=field_name)
    if any(ch.isspace() for ch in value) or "," in value:
        raise ValueError(f"{field_name} must be one exact ACS variable ID")
    return value


@dataclass(frozen=True, slots=True)
class ACSVariableSpec:
    """Exact ACS estimate/MOE mapping for one neutral demographic semantic."""

    semantic_key: str
    role: ACSVariableRole
    estimate_variable_id: str
    margin_of_error_variable_id: str
    estimate_annotation_variable_id: str | None
    margin_of_error_annotation_variable_id: str | None
    unit: str
    aggregation_group: str | None = None

    def __post_init__(self) -> None:
        require_canonical_id(self.semantic_key, field_name="semantic_key")
        if not isinstance(self.role, ACSVariableRole):
            raise TypeError("role must be an ACSVariableRole")
        _require_variable_id(self.estimate_variable_id, field_name="estimate_variable_id")
        _require_variable_id(self.margin_of_error_variable_id, field_name="margin_of_error_variable_id")
        _require_variable_id(self.estimate_annotation_variable_id, field_name="estimate_annotation_variable_id")
        _require_variable_id(self.margin_of_error_annotation_variable_id, field_name="margin_of_error_annotation_variable_id")
        require_nonempty_text(self.unit, field_name="unit")
        require_optional_nonempty_text(self.aggregation_group, field_name="aggregation_group")
        # ACS Detailed Table metadata uses E/EA/M/MA suffix semantics.  The
        # manifest records exact IDs rather than deriving them, but rejects a
        # role-swapped configuration at construction time.
        if not self.estimate_variable_id.endswith("E") or self.estimate_variable_id.endswith("EA"):
            raise ValueError("estimate_variable_id must use ACS estimate (E) semantics")
        if not self.margin_of_error_variable_id.endswith("M") or self.margin_of_error_variable_id.endswith("MA"):
            raise ValueError("margin_of_error_variable_id must use ACS margin-of-error (M) semantics")
        if self.estimate_annotation_variable_id is not None and not self.estimate_annotation_variable_id.endswith("EA"):
            raise ValueError("estimate_annotation_variable_id must use ACS estimate-annotation (EA) semantics")
        if self.margin_of_error_annotation_variable_id is not None and not self.margin_of_error_annotation_variable_id.endswith("MA"):
            raise ValueError("margin_of_error_annotation_variable_id must use ACS MOE-annotation (MA) semantics")
        estimate_stem = self.estimate_variable_id[:-1]
        if self.margin_of_error_variable_id[:-1] != estimate_stem:
            raise ValueError("estimate and MOE variable IDs must share one ACS variable stem")
        if self.estimate_annotation_variable_id is not None and self.estimate_annotation_variable_id[:-2] != estimate_stem:
            raise ValueError("estimate annotation must bind to the estimate variable stem")
        if self.margin_of_error_annotation_variable_id is not None and self.margin_of_error_annotation_variable_id[:-2] != estimate_stem:
            raise ValueError("MOE annotation must bind to the estimate variable stem")
        ids = self.request_variable_ids
        if len(ids) != len(set(ids)):
            raise ValueError("one ACSVariableSpec must not reuse a variable ID across E/M/EA/MA semantics")
        if self.role is ACSVariableRole.AGE_COMPONENT and self.aggregation_group is None:
            raise ValueError("AGE_COMPONENT variables require an aggregation_group")
        if self.role is not ACSVariableRole.AGE_COMPONENT and self.aggregation_group is not None:
            raise ValueError("only AGE_COMPONENT variables may carry aggregation_group")

    @property
    def request_variable_ids(self) -> tuple[str, ...]:
        return tuple(
            item
            for item in (
                self.estimate_variable_id,
                self.margin_of_error_variable_id,
                self.estimate_annotation_variable_id,
                self.margin_of_error_annotation_variable_id,
            )
            if item is not None
        )


@dataclass(frozen=True, slots=True)
class ACSVariableManifest:
    manifest_id: str
    manifest_version: str
    variables: tuple[ACSVariableSpec, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.manifest_id, field_name="manifest_id")
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        if not isinstance(self.variables, tuple) or not self.variables:
            raise TypeError("variables must be a non-empty tuple")
        for item in self.variables:
            if not isinstance(item, ACSVariableSpec):
                raise TypeError("variables must contain ACSVariableSpec values")
        keys = tuple(item.semantic_key for item in self.variables)
        if len(keys) != len(set(keys)):
            raise ValueError("variable manifest must not repeat semantic_key")
        all_ids = tuple(variable_id for item in self.variables for variable_id in item.request_variable_ids)
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("variable manifest must not reuse ACS variable IDs across semantic specs")
        if sum(item.role is ACSVariableRole.TOTAL_POPULATION for item in self.variables) != 1:
            raise ValueError("variable manifest requires exactly one TOTAL_POPULATION variable")
        if sum(item.role is ACSVariableRole.HOUSEHOLD_INCOME for item in self.variables) != 1:
            raise ValueError("variable manifest requires exactly one HOUSEHOLD_INCOME variable")
        if not any(item.role is ACSVariableRole.AGE_COMPONENT for item in self.variables):
            raise ValueError("variable manifest requires at least one AGE_COMPONENT variable")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical(
            {
                "grammar_version": ACS_VARIABLE_MANIFEST_GRAMMAR_VERSION,
                "canonicalization_version": CANONICALIZATION_VERSION,
                "manifest_id": self.manifest_id,
                "manifest_version": self.manifest_version,
                "variables": tuple(
                    {
                        "semantic_key": item.semantic_key,
                        "role": item.role.value,
                        "estimate_variable_id": item.estimate_variable_id,
                        "margin_of_error_variable_id": item.margin_of_error_variable_id,
                        "estimate_annotation_variable_id": item.estimate_annotation_variable_id,
                        "margin_of_error_annotation_variable_id": item.margin_of_error_annotation_variable_id,
                        "unit": item.unit,
                        "aggregation_group": item.aggregation_group,
                    }
                    for item in sorted(self.variables, key=lambda value: value.semantic_key)
                ),
            }
        )

    @property
    def by_semantic_key(self) -> dict[str, ACSVariableSpec]:
        return {item.semantic_key: item for item in self.variables}


@dataclass(frozen=True, slots=True)
class ACSGeographyCompatibility:
    """Trusted deployment/configuration binding from Census geography evidence to ACS."""

    compatibility_id: str
    compatibility_version: str
    accepted_source_versions: tuple[str, ...]
    supported_geography_types: tuple[GeographyType, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.compatibility_id, field_name="compatibility_id")
        require_nonempty_text(self.compatibility_version, field_name="compatibility_version")
        if not isinstance(self.accepted_source_versions, tuple) or not self.accepted_source_versions:
            raise TypeError("accepted_source_versions must be a non-empty tuple")
        for value in self.accepted_source_versions:
            _reject_mutable_release(value, field_name="accepted_source_version")
        if len(set(self.accepted_source_versions)) != len(self.accepted_source_versions):
            raise ValueError("accepted_source_versions must not contain duplicates")
        if not isinstance(self.supported_geography_types, tuple) or not self.supported_geography_types:
            raise TypeError("supported_geography_types must be a non-empty tuple")
        for value in self.supported_geography_types:
            if not isinstance(value, GeographyType):
                raise TypeError("supported_geography_types must contain GeographyType values")
            if value not in {GeographyType.TRACT, GeographyType.BLOCK_GROUP}:
                raise ValueError("Checkpoint 3.3-3 supports only TRACT and BLOCK_GROUP ACS geographies")
        if len(set(self.supported_geography_types)) != len(self.supported_geography_types):
            raise ValueError("supported_geography_types must not contain duplicates")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical(
            {
                "grammar_version": ACS_GEOGRAPHY_COMPATIBILITY_GRAMMAR_VERSION,
                "canonicalization_version": CANONICALIZATION_VERSION,
                "compatibility_id": self.compatibility_id,
                "compatibility_version": self.compatibility_version,
                "accepted_source_versions": tuple(sorted(self.accepted_source_versions)),
                "supported_geography_types": tuple(sorted(item.value for item in self.supported_geography_types)),
            }
        )


@dataclass(frozen=True, slots=True)
class ACSDatasetManifest:
    manifest_version: str
    dataset_release: str
    vintage: str
    product: ACSProduct
    dataset_identifier: str
    variable_manifest: ACSVariableManifest
    geography_compatibility: ACSGeographyCompatibility
    parser_version: str

    def __post_init__(self) -> None:
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        _reject_mutable_release(self.dataset_release, field_name="dataset_release")
        _reject_mutable_release(self.vintage, field_name="vintage")
        if not isinstance(self.product, ACSProduct):
            raise TypeError("product must be an ACSProduct")
        if self.product is not ACSProduct.DETAILED_TABLES:
            raise ValueError("Checkpoint 3.3-3 supports ACS 5-year Detailed Tables only")
        require_nonempty_text(self.dataset_identifier, field_name="dataset_identifier")
        if self.dataset_identifier.startswith("/") or self.dataset_identifier.endswith("/") or "//" in self.dataset_identifier:
            raise ValueError("dataset_identifier must be a canonical relative Census API dataset path")
        if "current" in self.dataset_identifier.lower() or "latest" in self.dataset_identifier.lower():
            raise ValueError("dataset_identifier must not contain mutable current/latest identity")
        if not isinstance(self.variable_manifest, ACSVariableManifest):
            raise TypeError("variable_manifest must be an ACSVariableManifest")
        if not isinstance(self.geography_compatibility, ACSGeographyCompatibility):
            raise TypeError("geography_compatibility must be an ACSGeographyCompatibility")
        require_nonempty_text(self.parser_version, field_name="parser_version")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical(
            {
                "grammar_version": ACS_MANIFEST_GRAMMAR_VERSION,
                "canonicalization_version": CANONICALIZATION_VERSION,
                "manifest_version": self.manifest_version,
                "dataset_release": self.dataset_release,
                "vintage": self.vintage,
                "product": self.product.value,
                "dataset_identifier": self.dataset_identifier,
                "variable_manifest_identity": str(self.variable_manifest.identity),
                "geography_compatibility_identity": str(self.geography_compatibility.identity),
                "parser_version": self.parser_version,
            }
        )


@dataclass(frozen=True, slots=True)
class ACSAgeCohortSpec:
    cohort_id: str
    age_min_inclusive: int
    age_max_exclusive: int | None
    source_semantic_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.cohort_id, field_name="cohort_id")
        for field_name in ("age_min_inclusive", "age_max_exclusive"):
            value = getattr(self, field_name)
            if value is None and field_name == "age_max_exclusive":
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an int" + (" or None" if field_name == "age_max_exclusive" else ""))
            if value < 0:
                raise ValueError(f"{field_name} must be nonnegative")
        if self.age_max_exclusive is not None and self.age_max_exclusive <= self.age_min_inclusive:
            raise ValueError("age_max_exclusive must be greater than age_min_inclusive")
        if not isinstance(self.source_semantic_keys, tuple) or not self.source_semantic_keys:
            raise TypeError("source_semantic_keys must be a non-empty tuple")
        for key in self.source_semantic_keys:
            require_canonical_id(key, field_name="source_semantic_key")
        if len(set(self.source_semantic_keys)) != len(self.source_semantic_keys):
            raise ValueError("source_semantic_keys must not contain duplicates")


@dataclass(frozen=True, slots=True)
class AgeCohortAggregationPolicy:
    policy_id: str
    policy_version: str
    cohorts: tuple[ACSAgeCohortSpec, ...]
    require_contiguous_intervals: bool = True
    require_all_age_components: bool = True

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if not isinstance(self.cohorts, tuple) or not self.cohorts:
            raise TypeError("cohorts must be a non-empty tuple")
        if not isinstance(self.require_contiguous_intervals, bool) or not isinstance(self.require_all_age_components, bool):
            raise TypeError("age policy flags must be bool values")
        for cohort in self.cohorts:
            if not isinstance(cohort, ACSAgeCohortSpec):
                raise TypeError("cohorts must contain ACSAgeCohortSpec values")
        ordered = tuple(sorted(self.cohorts, key=lambda c: (c.age_min_inclusive, float("inf") if c.age_max_exclusive is None else c.age_max_exclusive, c.cohort_id)))
        if self.cohorts != ordered:
            raise ValueError("cohorts must be in deterministic age interval order")
        keys = tuple(key for cohort in self.cohorts for key in cohort.source_semantic_keys)
        if len(keys) != len(set(keys)):
            raise ValueError("one source age component cannot contribute to multiple cohorts")
        for previous, current in zip(self.cohorts, self.cohorts[1:], strict=False):
            if previous.age_max_exclusive is None:
                raise ValueError("open-ended age cohort must be final")
            if current.age_min_inclusive < previous.age_max_exclusive:
                raise ValueError("age cohort intervals must not overlap")
            if self.require_contiguous_intervals and current.age_min_inclusive != previous.age_max_exclusive:
                raise ValueError("age cohort intervals must be contiguous under this policy")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical(
            {
                "grammar_version": ACS_AGE_POLICY_GRAMMAR_VERSION,
                "canonicalization_version": CANONICALIZATION_VERSION,
                "policy_id": self.policy_id,
                "policy_version": self.policy_version,
                "require_contiguous_intervals": self.require_contiguous_intervals,
                "require_all_age_components": self.require_all_age_components,
                "cohorts": tuple(
                    {
                        "cohort_id": item.cohort_id,
                        "age_min_inclusive": item.age_min_inclusive,
                        "age_max_exclusive": item.age_max_exclusive,
                        "source_semantic_keys": tuple(sorted(item.source_semantic_keys)),
                        "aggregation_rule": "sum_estimates",
                        "derived_moe_rule": "deferred_raw_cell_moes_retained",
                    }
                    for item in self.cohorts
                ),
            }
        )

    def validate_against(self, variable_manifest: ACSVariableManifest) -> None:
        if not isinstance(variable_manifest, ACSVariableManifest):
            raise TypeError("variable_manifest must be an ACSVariableManifest")
        age_specs = {item.semantic_key for item in variable_manifest.variables if item.role is ACSVariableRole.AGE_COMPONENT}
        mapped = {key for cohort in self.cohorts for key in cohort.source_semantic_keys}
        unknown = mapped - age_specs
        if unknown:
            raise ValueError(f"age policy references non-age or unknown semantic keys: {sorted(unknown)}")
        if self.require_all_age_components and mapped != age_specs:
            missing = age_specs - mapped
            raise ValueError(f"age policy must map every age component exactly once; missing={sorted(missing)}")


@dataclass(frozen=True, slots=True)
class ACSGeographyQuery:
    geography_type: GeographyType
    geography_id: str
    for_clause: str
    in_clause: str

    def __post_init__(self) -> None:
        if self.geography_type not in {GeographyType.TRACT, GeographyType.BLOCK_GROUP}:
            raise ValueError("ACSGeographyQuery supports TRACT or BLOCK_GROUP")
        require_nonempty_text(self.geography_id, field_name="geography_id")
        require_nonempty_text(self.for_clause, field_name="for_clause")
        require_nonempty_text(self.in_clause, field_name="in_clause")


@dataclass(frozen=True, slots=True)
class ACSUnsupportedGeography:
    geography_type: GeographyType
    geography_id: str
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.geography_type, GeographyType):
            raise TypeError("geography_type must be a GeographyType")
        require_nonempty_text(self.geography_id, field_name="geography_id")
        require_canonical_id(self.reason_code, field_name="reason_code")


@dataclass(frozen=True, slots=True)
class ACSGeographyRequestResult:
    state: ACSGeographyRequestState
    query: ACSGeographyQuery | None = None
    unsupported: ACSUnsupportedGeography | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, ACSGeographyRequestState):
            raise TypeError("state must be an ACSGeographyRequestState")
        if self.state is ACSGeographyRequestState.SUPPORTED:
            if self.query is None or self.unsupported is not None:
                raise ValueError("SUPPORTED requires only query")
        else:
            if self.unsupported is None or self.query is not None:
                raise ValueError("UNSUPPORTED requires only unsupported condition")


@dataclass(frozen=True, slots=True)
class ACSRequest:
    geography: ACSGeographyQuery
    semantic_keys: tuple[str, ...]
    variable_ids: tuple[str, ...]
    request_fingerprint: RequestFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.geography, ACSGeographyQuery):
            raise TypeError("geography must be an ACSGeographyQuery")
        if not isinstance(self.semantic_keys, tuple) or not self.semantic_keys:
            raise TypeError("semantic_keys must be a non-empty tuple")
        if not isinstance(self.variable_ids, tuple) or not self.variable_ids:
            raise TypeError("variable_ids must be a non-empty tuple")
        if self.variable_ids != tuple(sorted(self.variable_ids)):
            raise ValueError("variable_ids must be in canonical sorted order")
        if len(self.variable_ids) > ACS_REQUEST_MAX_VARIABLES:
            raise ValueError("one ACS request cannot exceed the documented 50-variable limit")
        if not isinstance(self.request_fingerprint, RequestFingerprint):
            raise TypeError("request_fingerprint must be a RequestFingerprint")


@dataclass(frozen=True, slots=True)
class ACSQueryPlan:
    manifest_identity: ContentHash
    geography: ACSGeographyQuery
    requests: tuple[ACSRequest, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest_identity, ContentHash):
            raise TypeError("manifest_identity must be a ContentHash")
        if not isinstance(self.geography, ACSGeographyQuery):
            raise TypeError("geography must be an ACSGeographyQuery")
        if not isinstance(self.requests, tuple) or not self.requests:
            raise TypeError("requests must be a non-empty tuple")
        for request in self.requests:
            if not isinstance(request, ACSRequest):
                raise TypeError("requests must contain ACSRequest values")
            if request.geography != self.geography:
                raise ValueError("all planned requests must use the same geography")


@dataclass(frozen=True, slots=True)
class ACSStatisticalEvidence:
    """One statistical observation. Exact ACS column identity is self-contained.

    dataset_manifest_identity still binds the evidence to the immutable variable
    manifest, but E/M/EA/MA source columns are retained explicitly so consumers
    never need to infer what an ambiguous ``variable_id`` meant.
    """

    semantic_key: str
    estimate_variable_id: str
    margin_of_error_variable_id: str
    estimate_annotation_variable_id: str | None
    margin_of_error_annotation_variable_id: str | None
    request_fingerprint: RequestFingerprint
    estimate: int | float | None
    margin_of_error: int | float | None
    estimate_state: ACSStatisticalValueState
    margin_of_error_state: ACSStatisticalValueState
    estimate_raw_value: str | None
    margin_of_error_raw_value: str | None
    estimate_annotation: str | None
    margin_of_error_annotation: str | None
    geography_type: GeographyType
    geography_id: str
    dataset_release: str
    vintage: str
    dataset_manifest_identity: ContentHash
    raw_content_hash: ContentHash
    parsed_artifact_identity: ContentHash
    aggregation_lineage: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_canonical_id(self.semantic_key, field_name="semantic_key")
        _require_variable_id(self.estimate_variable_id, field_name="estimate_variable_id")
        _require_variable_id(self.margin_of_error_variable_id, field_name="margin_of_error_variable_id")
        _require_variable_id(self.estimate_annotation_variable_id, field_name="estimate_annotation_variable_id")
        _require_variable_id(self.margin_of_error_annotation_variable_id, field_name="margin_of_error_annotation_variable_id")
        if not isinstance(self.request_fingerprint, RequestFingerprint):
            raise TypeError("request_fingerprint must be a RequestFingerprint")
        if not isinstance(self.estimate_state, ACSStatisticalValueState) or not isinstance(self.margin_of_error_state, ACSStatisticalValueState):
            raise TypeError("statistical states must be ACSStatisticalValueState values")
        for name in ("estimate_raw_value", "margin_of_error_raw_value", "estimate_annotation", "margin_of_error_annotation"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a string or None")
        self._validate_statistical_axis(
            value=self.estimate,
            state=self.estimate_state,
            annotation=self.estimate_annotation,
            axis_name="estimate",
        )
        self._validate_statistical_axis(
            value=self.margin_of_error,
            state=self.margin_of_error_state,
            annotation=self.margin_of_error_annotation,
            axis_name="margin_of_error",
        )
        if not isinstance(self.geography_type, GeographyType):
            raise TypeError("geography_type must be a GeographyType")
        require_nonempty_text(self.geography_id, field_name="geography_id")
        _reject_mutable_release(self.dataset_release, field_name="dataset_release")
        _reject_mutable_release(self.vintage, field_name="vintage")
        for value in (self.dataset_manifest_identity, self.raw_content_hash, self.parsed_artifact_identity):
            if not isinstance(value, ContentHash):
                raise TypeError("evidence identity fields must be ContentHash values")
        if not isinstance(self.aggregation_lineage, tuple):
            raise TypeError("aggregation_lineage must be a tuple")
        for item in self.aggregation_lineage:
            require_nonempty_text(item, field_name="aggregation_lineage item")


    @staticmethod
    def _validate_statistical_axis(
        *,
        value: int | float | None,
        state: ACSStatisticalValueState,
        annotation: str | None,
        axis_name: str,
    ) -> None:
        """Enforce state/value/annotation coherence without re-parsing Census sentinels."""

        if state is ACSStatisticalValueState.VALUE:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{axis_name} VALUE state requires a finite numeric value")
            if not math.isfinite(value):
                raise ValueError(f"{axis_name} VALUE state requires a finite numeric value")
            if annotation not in {None, ""}:
                raise ValueError(f"{axis_name} VALUE state cannot carry a non-empty annotation")
            return
        if value is not None:
            raise ValueError(f"{axis_name} non-VALUE state requires value=None")
        if state is ACSStatisticalValueState.ANNOTATED and annotation in {None, ""}:
            raise ValueError(f"{axis_name} ANNOTATED state requires a non-empty annotation")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical(
            {
                "grammar_version": ACS_EVIDENCE_GRAMMAR_VERSION,
                "canonicalization_version": CANONICALIZATION_VERSION,
                "semantic_key": self.semantic_key,
                "estimate_variable_id": self.estimate_variable_id,
                "margin_of_error_variable_id": self.margin_of_error_variable_id,
                "estimate_annotation_variable_id": self.estimate_annotation_variable_id,
                "margin_of_error_annotation_variable_id": self.margin_of_error_annotation_variable_id,
                "request_fingerprint": str(self.request_fingerprint),
                "estimate": self.estimate,
                "margin_of_error": self.margin_of_error,
                "estimate_state": self.estimate_state.value,
                "margin_of_error_state": self.margin_of_error_state.value,
                "estimate_raw_value": self.estimate_raw_value,
                "margin_of_error_raw_value": self.margin_of_error_raw_value,
                "estimate_annotation": self.estimate_annotation,
                "margin_of_error_annotation": self.margin_of_error_annotation,
                "geography_type": self.geography_type.value,
                "geography_id": self.geography_id,
                "dataset_release": self.dataset_release,
                "vintage": self.vintage,
                "dataset_manifest_identity": str(self.dataset_manifest_identity),
                "raw_content_hash": str(self.raw_content_hash),
                "parsed_artifact_identity": str(self.parsed_artifact_identity),
                "aggregation_lineage": self.aggregation_lineage,
            }
        )


@dataclass(frozen=True, slots=True)
class ACSParsedEvidenceResult:
    row_state: ACSRowState
    evidence: tuple[ACSStatisticalEvidence, ...]
    parsed_artifact: ParsedArtifact

    def __post_init__(self) -> None:
        if not isinstance(self.row_state, ACSRowState):
            raise TypeError("row_state must be an ACSRowState")
        if not isinstance(self.evidence, tuple):
            raise TypeError("evidence must be a tuple")
        if self.row_state is ACSRowState.NO_DATA and self.evidence:
            raise ValueError("NO_DATA cannot carry statistical evidence")
        if self.row_state is ACSRowState.FOUND and not self.evidence:
            raise ValueError("FOUND requires statistical evidence")
        if not isinstance(self.parsed_artifact, ParsedArtifact):
            raise TypeError("parsed_artifact must be a ParsedArtifact")


@dataclass(frozen=True, slots=True)
class ACSEvidenceBundle:
    geography_ref: GeographyRef
    manifest_identity: ContentHash
    evidence: tuple[ACSStatisticalEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.geography_ref, GeographyRef):
            raise TypeError("geography_ref must be a GeographyRef")
        if not isinstance(self.manifest_identity, ContentHash):
            raise TypeError("manifest_identity must be a ContentHash")
        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise TypeError("evidence must be a non-empty tuple")
        for item in self.evidence:
            if not isinstance(item, ACSStatisticalEvidence):
                raise TypeError("evidence must contain ACSStatisticalEvidence values")
            if item.geography_type is not self.geography_ref.geography_type or item.geography_id != self.geography_ref.geography_id:
                raise ValueError("all evidence must bind to the bundle GeographyRef")
            if item.dataset_manifest_identity != self.manifest_identity:
                raise ValueError("all evidence must bind to the same dataset manifest")
        keys = tuple(item.semantic_key for item in self.evidence)
        if len(keys) != len(set(keys)):
            raise ValueError("evidence bundle must not contain duplicate semantic keys")
        releases = {(item.dataset_release, item.vintage) for item in self.evidence}
        if len(releases) != 1:
            raise ValueError("evidence bundle must use one dataset release/vintage")
        originating_ids = tuple(
            variable_id
            for item in self.evidence
            for variable_id in (
                item.estimate_variable_id,
                item.margin_of_error_variable_id,
                item.estimate_annotation_variable_id,
                item.margin_of_error_annotation_variable_id,
            )
            if variable_id is not None
        )
        if len(originating_ids) != len(set(originating_ids)):
            raise ValueError("evidence bundle must not contain duplicate originating ACS variable IDs")

    @property
    def by_semantic_key(self) -> dict[str, ACSStatisticalEvidence]:
        return {item.semantic_key: item for item in self.evidence}
