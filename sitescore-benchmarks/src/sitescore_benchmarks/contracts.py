from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

from sitescore_spatial import (
    CanonicalGeometry,
    BoundaryGeometryArtifact,
    CRSIdentity,
    GeometryEngineIdentity,
    GeometryPrecisionPolicy,
    GeometryCanonicalizationPolicy,
    GeometryOperationResult,
    GeographyIdentity,
    GeometryOperation,
    OperationState,
    geometry_from_canonical,
)
from .enums import *
from .hashing import semantic_hash
from .validation import text, sha, finite

POPULATION_DEFINITION = "commercially_evidenced_spatial_alternatives"
POPULATION_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class EqualAreaProjectionPolicy:
    policy_id: str
    policy_version: str
    selection_algorithm: str
    state: ResolutionState
    selected_crs: CRSIdentity | None = None

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        text(self.selection_algorithm, "selection_algorithm")
        if not isinstance(self.state, ResolutionState):
            raise TypeError("state must be ResolutionState")
        if self.selected_crs is not None and not isinstance(self.selected_crs, CRSIdentity):
            raise TypeError("selected_crs must be CRSIdentity")
        # FRAME-H001: 3.4-2 does not define a verified equal-area attestation mechanism.
        # Therefore RESOLVED is intentionally not a constructible production-semantic state.
        if self.state is ResolutionState.RESOLVED:
            raise ValueError("resolved equal-area projection attestation is not available in checkpoint 3.4-2")
        if self.selected_crs is not None:
            raise ValueError("unresolved equal-area projection policy must not carry selected_crs")

    @property
    def identity_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "selection_algorithm": self.selection_algorithm,
            "state": self.state.value,
            "selected_crs_identity_id": None,
        }


@dataclass(frozen=True, slots=True)
class CellResolutionPolicy:
    policy_id: str
    policy_version: str
    state: ResolutionState
    cell_size: float | None = None
    unit: str | None = None

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.state, ResolutionState):
            raise TypeError("state must be ResolutionState")
        if self.state is ResolutionState.RESOLVED:
            if self.cell_size is None or self.unit is None:
                raise ValueError("resolved resolution requires cell_size and unit")
            if finite(self.cell_size, "cell_size") <= 0:
                raise ValueError("cell_size must be >0")
            text(self.unit, "unit")
            if self.unit != "m":
                raise ValueError("V1 square lattice resolution unit must be metres")
        elif self.cell_size is not None or self.unit is not None:
            raise ValueError("unresolved resolution must not carry value")

    @property
    def identity_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "state": self.state.value,
            "cell_size": self.cell_size,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class LatticePolicy:
    policy_id: str
    policy_version: str
    projection_policy: EqualAreaProjectionPolicy
    resolution_policy: CellResolutionPolicy
    cell_shape: CellShape
    anchor_x: float | None
    anchor_y: float | None
    axis_alignment: str
    indexing_algorithm: str
    indexing_version: str
    canonicalization_policy: GeometryCanonicalizationPolicy
    engine_identity: GeometryEngineIdentity

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.projection_policy, EqualAreaProjectionPolicy):
            raise TypeError("projection_policy")
        if not isinstance(self.resolution_policy, CellResolutionPolicy):
            raise TypeError("resolution_policy")
        if not isinstance(self.cell_shape, CellShape):
            raise TypeError("cell_shape")
        text(self.axis_alignment, "axis_alignment")
        text(self.indexing_algorithm, "indexing_algorithm")
        text(self.indexing_version, "indexing_version")
        if self.cell_shape is not CellShape.SQUARE:
            raise ValueError("V1 lattice supports square cells only")
        if self.axis_alignment != "AXIS_ALIGNED":
            raise ValueError("V1 lattice supports AXIS_ALIGNED only")
        if self.indexing_algorithm != "INTEGER_IJ":
            raise ValueError("V1 lattice supports INTEGER_IJ only")
        if not isinstance(self.canonicalization_policy, GeometryCanonicalizationPolicy):
            raise TypeError("canonicalization_policy")
        if not isinstance(self.engine_identity, GeometryEngineIdentity):
            raise TypeError("engine_identity")
        if self.is_resolved:
            if self.anchor_x is None or self.anchor_y is None:
                raise ValueError("resolved lattice requires explicit anchor")
            finite(self.anchor_x, "anchor_x")
            finite(self.anchor_y, "anchor_y")
        elif self.anchor_x is not None or self.anchor_y is not None:
            raise ValueError("unresolved lattice must not smuggle anchor values")

    @property
    def precision_policy(self) -> GeometryPrecisionPolicy:
        return self.canonicalization_policy.precision_policy

    @property
    def is_resolved(self):
        return (
            self.projection_policy.state is ResolutionState.RESOLVED
            and self.resolution_policy.state is ResolutionState.RESOLVED
        )

    @property
    def identity_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "projection_policy_id": self.projection_policy.identity_id,
            "resolution_policy_id": self.resolution_policy.identity_id,
            "cell_shape": self.cell_shape.value,
            "anchor_x": self.anchor_x,
            "anchor_y": self.anchor_y,
            "axis_alignment": self.axis_alignment,
            "indexing_algorithm": self.indexing_algorithm,
            "indexing_version": self.indexing_version,
            "canonicalization_policy_id": self.canonicalization_policy.identity_id,
            "precision_policy_id": self.precision_policy.identity_id,
            "engine_identity_id": self.engine_identity.engine_identity_id,
        }


@dataclass(frozen=True, slots=True)
class LatticeCellArtifact:
    lattice_policy: LatticePolicy
    index_i: int
    index_j: int
    full_cell_geometry: CanonicalGeometry
    area_result: GeometryOperationResult
    derivation_algorithm: str = "SQUARE_INTEGER_IJ"
    derivation_version: str = "1.0"

    def __post_init__(self):
        if not isinstance(self.lattice_policy, LatticePolicy):
            raise TypeError("lattice_policy")
        if not isinstance(self.index_i, int) or isinstance(self.index_i, bool):
            raise TypeError("index_i must be int")
        if not isinstance(self.index_j, int) or isinstance(self.index_j, bool):
            raise TypeError("index_j must be int")
        if not isinstance(self.full_cell_geometry, CanonicalGeometry):
            raise TypeError("full_cell_geometry")
        if not isinstance(self.area_result, GeometryOperationResult):
            raise TypeError("area_result")
        text(self.derivation_algorithm, "derivation_algorithm")
        text(self.derivation_version, "derivation_version")
        if not self.lattice_policy.is_resolved:
            raise ValueError("unresolved lattice cannot produce canonical lattice cells")
        selected_crs = self.lattice_policy.projection_policy.selected_crs
        if selected_crs is None:
            raise ValueError("resolved lattice requires selected equal-area CRS")
        if self.full_cell_geometry.crs_identity.crs_identity_id != selected_crs.crs_identity_id:
            raise ValueError("lattice cell geometry CRS mismatch")
        if self.full_cell_geometry.canonicalization_policy.identity_id != self.lattice_policy.canonicalization_policy.identity_id:
            raise ValueError("lattice cell canonicalization policy mismatch")
        if self.full_cell_geometry.engine_identity_id != self.lattice_policy.engine_identity.engine_identity_id:
            raise ValueError("lattice cell engine mismatch")
        if self.area_result.operation is not GeometryOperation.AREA or self.area_result.state is not OperationState.SUCCESS:
            raise ValueError("lattice cell area_result must be successful AREA")
        if len(self.area_result.input_geometries) != 1 or self.area_result.input_geometries[0].semantic_geometry_id != self.full_cell_geometry.semantic_geometry_id:
            raise ValueError("lattice cell area_result must measure exact full cell geometry")
        if self.area_result.numeric_value is None or self.area_result.numeric_value <= 0 or self.area_result.unit != "m2":
            raise ValueError("lattice cell requires positive m2 area result")
        size = float(self.lattice_policy.resolution_policy.cell_size)
        x0 = float(self.lattice_policy.anchor_x) + self.index_i * size
        y0 = float(self.lattice_policy.anchor_y) + self.index_j * size
        x1, y1 = x0 + size, y0 + size
        geom = geometry_from_canonical(self.full_cell_geometry)
        if geom.geom_type != "Polygon" or len(geom.interiors) != 0:
            raise ValueError("V1 lattice cell must be a simple square Polygon")
        if tuple(float(v) for v in geom.bounds) != (x0, y0, x1, y1):
            raise ValueError("lattice cell geometry does not match anchor/resolution/index")
        corners = {(x0,y0),(x1,y0),(x1,y1),(x0,y1)}
        coords = [(float(x),float(y)) for x,y in geom.exterior.coords]
        if len(coords) != 5 or coords[0] != coords[-1] or set(coords[:-1]) != corners:
            raise ValueError("lattice cell geometry is not the exact derived square")
        expected_area = size * size
        if float(geom.area) != expected_area:
            raise ValueError("lattice cell geometry area does not match resolution")
        if float(self.area_result.numeric_value) != expected_area:
            raise ValueError("lattice cell area_result does not match derived square area")

    @property
    def lattice_index(self) -> str:
        return f"{self.index_i}:{self.index_j}"

    @property
    def full_cell_area(self) -> float:
        return float(self.area_result.numeric_value)

    @property
    def area_unit(self) -> str:
        return self.area_result.unit

    @property
    def lattice_cell_id(self):
        return semantic_hash({
            "lattice_policy_id": self.lattice_policy.identity_id,
            "index_i": self.index_i,
            "index_j": self.index_j,
            "full_cell_geometry_id": self.full_cell_geometry.semantic_geometry_id,
            "area_operation_id": self.area_result.operation_id,
            "derivation_algorithm": self.derivation_algorithm,
            "derivation_version": self.derivation_version,
        })


@dataclass(frozen=True, slots=True)
class FrameBoundaryMembershipPolicy:
    policy_id: str
    policy_version: str
    state: ResolutionState
    method: str | None = None
    method_parameter: float | None = None

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.state, ResolutionState):
            raise TypeError("state")
        if self.state is ResolutionState.RESOLVED:
            if self.method is None:
                raise ValueError("resolved membership policy requires explicit method")
            text(self.method, "method")
            if self.method_parameter is not None:
                finite(self.method_parameter, "method_parameter")
        elif self.method is not None or self.method_parameter is not None:
            raise ValueError("unresolved membership policy must not encode a hidden rule")

    @property
    def identity_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "state": self.state.value,
            "method": self.method,
            "method_parameter": self.method_parameter,
        }


@dataclass(frozen=True, slots=True)
class EvidenceSourceIdentity:
    provider: str
    dataset: str
    release: str
    vintage: str
    schema_version: str
    content_hash: str

    def __post_init__(self):
        for name in ("provider", "dataset", "release", "vintage", "schema_version"):
            text(getattr(self, name), name)
        sha(self.content_hash, "content_hash")
        if self.release.lower() in {"latest", "current", "live", "today", "now"}:
            raise ValueError("mutable release identity forbidden")
        if self.vintage.lower() in {"latest", "current", "live", "today", "now"}:
            raise ValueError("mutable vintage identity forbidden")

    @property
    def identity_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "provider": self.provider,
            "dataset": self.dataset,
            "release": self.release,
            "vintage": self.vintage,
            "schema_version": self.schema_version,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class CommercialEvidenceRecord:
    """Provider-neutral immutable upstream evidence semantics.

    EvidenceSourceIdentity.content_hash is a declared immutable upstream content
    identity/reference. Raw bytes are intentionally not owned by this package.
    """
    evidence_type: str
    source_identity: EvidenceSourceIdentity
    semantic_attributes: tuple[tuple[str, str], ...] = ()
    source_ref: str | None = None

    def __post_init__(self):
        text(self.evidence_type, "evidence_type")
        if not isinstance(self.source_identity, EvidenceSourceIdentity):
            raise TypeError("source_identity must be EvidenceSourceIdentity")
        if self.source_ref is not None:
            text(self.source_ref, "source_ref")
        if not isinstance(self.semantic_attributes, tuple):
            raise TypeError("semantic_attributes must be tuple")
        keys = []
        for pair in self.semantic_attributes:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError("semantic_attributes entries must be (key,value) tuples")
            k, v = pair
            text(k, "semantic attribute key")
            text(v, "semantic attribute value")
            keys.append(k)
        if tuple(keys) != tuple(sorted(set(keys))):
            raise ValueError("semantic_attributes must be unique and canonical-sorted by key")

    @property
    def identity_id(self):
        return semantic_hash({
            "evidence_type": self.evidence_type,
            "source_identity_id": self.source_identity.identity_id,
            "semantic_attributes": self.semantic_attributes,
        })


@dataclass(frozen=True, slots=True)
class CommercialEvidenceClassificationPolicy:
    policy_id: str
    policy_version: str
    state: ResolutionState
    method: str | None = None

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.state, ResolutionState):
            raise TypeError("state")
        # FRAME-H005: no approved commercial ontology/classification method exists in 3.4-2.
        if self.state is ResolutionState.RESOLVED:
            raise ValueError("resolved commercial evidence classification is not available in checkpoint 3.4-2")
        if self.method is not None:
            raise ValueError("unresolved classification policy must not encode a method")

    @property
    def identity_id(self):
        return semantic_hash({"policy_id": self.policy_id, "policy_version": self.policy_version,
                              "state": self.state.value, "method": self.method})


@dataclass(frozen=True, slots=True)
class CommercialEvidenceClassification:
    evidence_record: CommercialEvidenceRecord
    classification_policy: CommercialEvidenceClassificationPolicy
    evidence_class: str | None
    disposition: EvidenceDisposition
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.evidence_record, CommercialEvidenceRecord):
            raise TypeError("evidence_record")
        if not isinstance(self.classification_policy, CommercialEvidenceClassificationPolicy):
            raise TypeError("classification_policy")
        if not isinstance(self.disposition, EvidenceDisposition):
            raise TypeError("disposition")
        exp = _classification(self.classification_policy)
        if (self.evidence_class, self.disposition, self.reason_codes) != exp:
            raise ValueError("classification state disagrees with actual policy semantics")

    @property
    def identity_id(self):
        return semantic_hash({
            "evidence_record_id": self.evidence_record.identity_id,
            "classification_policy_id": self.classification_policy.identity_id,
            "evidence_class": self.evidence_class,
            "disposition": self.disposition.value,
            "reason_codes": self.reason_codes,
        })


def _classification(policy):
    # No production classification ontology/mapping is approved in 3.4-2.
    return None, EvidenceDisposition.UNRESOLVED, ("commercial_evidence_classification_unresolved",)


def classify_commercial_evidence(evidence_record, classification_policy):
    ec, disp, reasons = _classification(classification_policy)
    return CommercialEvidenceClassification(evidence_record, classification_policy, ec, disp, reasons)


@dataclass(frozen=True, slots=True)
class EvidenceCellApplicabilityPolicy:
    policy_id: str
    policy_version: str
    state: ResolutionState
    method: str | None = None

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.state, ResolutionState):
            raise TypeError("state")
        if self.state is ResolutionState.RESOLVED:
            raise ValueError("resolved evidence-cell applicability is not available in checkpoint 3.4-2")
        if self.method is not None:
            raise ValueError("unresolved applicability policy must not encode a method")

    @property
    def identity_id(self):
        return semantic_hash({"policy_id": self.policy_id, "policy_version": self.policy_version,
                              "state": self.state.value, "method": self.method})


@dataclass(frozen=True, slots=True)
class EvidenceCellApplicability:
    classification: CommercialEvidenceClassification
    lattice_cell: LatticeCellArtifact
    applicability_policy: EvidenceCellApplicabilityPolicy
    state: ApplicabilityState
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.classification, CommercialEvidenceClassification):
            raise TypeError("classification")
        if not isinstance(self.lattice_cell, LatticeCellArtifact):
            raise TypeError("lattice_cell")
        if not isinstance(self.applicability_policy, EvidenceCellApplicabilityPolicy):
            raise TypeError("applicability_policy")
        if not isinstance(self.state, ApplicabilityState):
            raise TypeError("state")
        exp = _applicability(self.applicability_policy)
        if (self.state, self.reason_codes) != exp:
            raise ValueError("cell applicability state disagrees with actual policy semantics")

    @property
    def identity_id(self):
        return semantic_hash({
            "classification_id": self.classification.identity_id,
            "lattice_cell_id": self.lattice_cell.lattice_cell_id,
            "applicability_policy_id": self.applicability_policy.identity_id,
            "state": self.state.value,
            "reason_codes": self.reason_codes,
        })


def _applicability(policy):
    return ApplicabilityState.UNRESOLVED, ("evidence_cell_applicability_unresolved",)


def evaluate_evidence_cell_applicability(classification, lattice_cell, applicability_policy):
    state, reasons = _applicability(applicability_policy)
    return EvidenceCellApplicability(classification, lattice_cell, applicability_policy, state, reasons)


@dataclass(frozen=True, slots=True)
class CommercialEvidenceItem:
    classification: CommercialEvidenceClassification
    applicability: EvidenceCellApplicability

    def __post_init__(self):
        if not isinstance(self.classification, CommercialEvidenceClassification):
            raise TypeError("classification")
        if not isinstance(self.applicability, EvidenceCellApplicability):
            raise TypeError("applicability")
        if self.applicability.classification.identity_id != self.classification.identity_id:
            raise ValueError("applicability/classification evidence mismatch")

    @property
    def evidence_type(self):
        return self.classification.evidence_record.evidence_type

    @property
    def evidence_class(self):
        return self.classification.evidence_class

    @property
    def disposition(self):
        return self.classification.disposition

    @property
    def source_identity(self):
        return self.classification.evidence_record.source_identity

    @property
    def source_ref(self):
        return self.classification.evidence_record.source_ref

    @property
    def identity_id(self):
        return semantic_hash({"classification_id": self.classification.identity_id,
                              "applicability_id": self.applicability.identity_id})


@dataclass(frozen=True, slots=True)
class CommercialEvidencePolicy:
    policy_id: str
    policy_version: str
    accepted_positive_classes: tuple[str, ...]
    accepted_exclusion_classes: tuple[str, ...]
    conflict_behavior: str = "UNKNOWN"
    insufficient_evidence_behavior: str = "UNKNOWN"

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        for x in self.accepted_positive_classes + self.accepted_exclusion_classes:
            text(x, "evidence class")
        if tuple(sorted(set(self.accepted_positive_classes))) != tuple(self.accepted_positive_classes):
            raise ValueError("positive classes must be unique canonical sorted")
        if tuple(sorted(set(self.accepted_exclusion_classes))) != tuple(self.accepted_exclusion_classes):
            raise ValueError("exclusion classes must be unique canonical sorted")
        if self.conflict_behavior != "UNKNOWN" or self.insufficient_evidence_behavior != "UNKNOWN":
            raise ValueError("3.4-2 structural policy freezes conflict/insufficient evidence to UNKNOWN")

    @property
    def identity_id(self):
        return semantic_hash({
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "accepted_positive_classes": self.accepted_positive_classes,
            "accepted_exclusion_classes": self.accepted_exclusion_classes,
            "conflict_behavior": self.conflict_behavior,
            "insufficient_evidence_behavior": self.insufficient_evidence_behavior,
        })


@dataclass(frozen=True, slots=True)
class CommercialFrameEvidenceBundle:
    lattice_cell: LatticeCellArtifact
    evidence_policy: CommercialEvidencePolicy
    evidence_items: tuple[CommercialEvidenceItem, ...] = ()

    def __post_init__(self):
        if not isinstance(self.lattice_cell, LatticeCellArtifact):
            raise TypeError("lattice_cell")
        if not isinstance(self.evidence_policy, CommercialEvidencePolicy):
            raise TypeError("evidence_policy")
        if not isinstance(self.evidence_items, tuple) or any(not isinstance(x, CommercialEvidenceItem) for x in self.evidence_items):
            raise TypeError("evidence_items require CommercialEvidenceItem tuple")
        ids = tuple(x.identity_id for x in self.evidence_items)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("evidence items must be unique and canonical-sorted")
        for item in self.evidence_items:
            if item.applicability.lattice_cell.lattice_cell_id != self.lattice_cell.lattice_cell_id:
                raise ValueError("evidence applicability targets a foreign lattice cell")

    @property
    def cell_lattice_id(self):
        return self.lattice_cell.lattice_cell_id

    @property
    def positive_evidence(self):
        return tuple(x for x in self.evidence_items if x.disposition is EvidenceDisposition.POSITIVE)

    @property
    def exclusion_evidence(self):
        return tuple(x for x in self.evidence_items if x.disposition is EvidenceDisposition.EXPLICIT_EXCLUSION)

    @property
    def unresolved_evidence(self):
        return tuple(x for x in self.evidence_items if x.disposition is EvidenceDisposition.UNRESOLVED or x.applicability.state is ApplicabilityState.UNRESOLVED)

    @property
    def bundle_id(self):
        return semantic_hash({
            "cell_lattice_id": self.lattice_cell.lattice_cell_id,
            "evidence_policy_id": self.evidence_policy.identity_id,
            "evidence_item_ids": [x.identity_id for x in self.evidence_items],
        })


@dataclass(frozen=True, slots=True)
class CommercialEligibilityPolicy:
    policy_id: str
    policy_version: str
    evidence_policy: CommercialEvidencePolicy

    def __post_init__(self):
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.evidence_policy, CommercialEvidencePolicy):
            raise TypeError("evidence_policy")

    @property
    def identity_id(self):
        return semantic_hash({"policy_id": self.policy_id, "policy_version": self.policy_version,
                              "evidence_policy_id": self.evidence_policy.identity_id})


@dataclass(frozen=True, slots=True)
class CommercialEligibilityResult:
    evidence_bundle: CommercialFrameEvidenceBundle
    eligibility_policy: CommercialEligibilityPolicy
    state: EligibilityState
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.evidence_bundle, CommercialFrameEvidenceBundle):
            raise TypeError("evidence_bundle")
        if not isinstance(self.eligibility_policy, CommercialEligibilityPolicy):
            raise TypeError("eligibility_policy")
        if not isinstance(self.state, EligibilityState):
            raise TypeError("state")
        if self.eligibility_policy.evidence_policy.identity_id != self.evidence_bundle.evidence_policy.identity_id:
            raise ValueError("eligibility/evidence policy mismatch")
        exp_state, exp_reasons = _eligibility(self.evidence_bundle, self.eligibility_policy)
        if self.state is not exp_state or self.reason_codes != exp_reasons:
            raise ValueError("eligibility state/reasons disagree with actual evidence")

    @property
    def lattice_cell(self):
        return self.evidence_bundle.lattice_cell

    @property
    def identity_id(self):
        return semantic_hash({
            "bundle_id": self.evidence_bundle.bundle_id,
            "eligibility_policy_id": self.eligibility_policy.identity_id,
            "state": self.state.value,
            "reason_codes": self.reason_codes,
        })


def _eligibility(bundle, policy):
    usable = tuple(x for x in bundle.evidence_items
                   if x.applicability.state is ApplicabilityState.APPLICABLE
                   and x.classification.disposition is not EvidenceDisposition.UNRESOLVED)
    pos = any(x.disposition is EvidenceDisposition.POSITIVE
              and x.evidence_class in policy.evidence_policy.accepted_positive_classes for x in usable)
    exc = any(x.disposition is EvidenceDisposition.EXPLICIT_EXCLUSION
              and x.evidence_class in policy.evidence_policy.accepted_exclusion_classes for x in usable)
    if pos and not exc:
        return EligibilityState.ELIGIBLE, ("accepted_positive_evidence",)
    if exc and not pos:
        return EligibilityState.INELIGIBLE, ("authoritative_exclusion_evidence",)
    if pos and exc:
        return EligibilityState.UNKNOWN, ("conflicting_commercial_evidence",)
    return EligibilityState.UNKNOWN, ("insufficient_commercial_evidence",)

@dataclass(frozen=True, slots=True)
class BoundaryIntersectionEvidence:
    full_cell_geometry: CanonicalGeometry
    boundary_artifact: BoundaryGeometryArtifact
    state: DiagnosticState
    intersection_operation: GeometryOperationResult | None = None
    intersection_area: float | None = None
    full_cell_area: float | None = None

    def __post_init__(self):
        if not isinstance(self.full_cell_geometry, CanonicalGeometry):
            raise TypeError("full_cell_geometry")
        if not isinstance(self.boundary_artifact, BoundaryGeometryArtifact):
            raise TypeError("boundary_artifact")
        if not isinstance(self.state, DiagnosticState):
            raise TypeError("state")
        if self.state is DiagnosticState.AVAILABLE:
            if self.intersection_area is None or self.full_cell_area is None:
                raise ValueError("available diagnostic requires intersection_area and full_cell_area")
            ia = finite(self.intersection_area, "intersection_area")
            fa = finite(self.full_cell_area, "full_cell_area")
            if ia < 0 or fa <= 0 or ia > fa:
                raise ValueError("invalid intersection diagnostic values")
            if self.intersection_operation is not None:
                if not isinstance(self.intersection_operation, GeometryOperationResult):
                    raise TypeError("intersection_operation")
                if self.intersection_operation.operation is not GeometryOperation.INTERSECT:
                    raise ValueError("intersection_operation must be INTERSECT")
                expected_inputs = tuple(sorted((
                    self.full_cell_geometry.semantic_geometry_id,
                    self.boundary_artifact.canonical_geometry.semantic_geometry_id,
                )))
                if self.intersection_operation.input_geometry_ids != expected_inputs:
                    raise ValueError("intersection_operation inputs do not match diagnostic cell/boundary")
        else:
            if self.intersection_area is not None or self.full_cell_area is not None or self.intersection_operation is not None:
                raise ValueError("unresolved diagnostic must not fabricate values")

    @property
    def intersection_fraction(self) -> float | None:
        if self.state is not DiagnosticState.AVAILABLE:
            return None
        return float(self.intersection_area) / float(self.full_cell_area)

    @property
    def identity_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "full_cell_geometry_id": self.full_cell_geometry.semantic_geometry_id,
            "boundary_artifact_id": self.boundary_artifact.geometry_artifact_id,
            "state": self.state.value,
            "intersection_operation_id": self.intersection_operation.operation_id if self.intersection_operation else None,
            "intersection_area": self.intersection_area,
            "full_cell_area": self.full_cell_area,
            "intersection_fraction": self.intersection_fraction,
        }


@dataclass(frozen=True, slots=True)
class FrameBoundaryMembership:
    full_cell_geometry: CanonicalGeometry
    boundary_artifact: BoundaryGeometryArtifact
    membership_policy: FrameBoundaryMembershipPolicy
    diagnostic_evidence: BoundaryIntersectionEvidence | None
    state: BoundaryMembershipState
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.full_cell_geometry, CanonicalGeometry):
            raise TypeError("full_cell_geometry")
        if not isinstance(self.boundary_artifact, BoundaryGeometryArtifact):
            raise TypeError("boundary_artifact")
        if not isinstance(self.membership_policy, FrameBoundaryMembershipPolicy):
            raise TypeError("membership_policy")
        if self.diagnostic_evidence is not None:
            if not isinstance(self.diagnostic_evidence, BoundaryIntersectionEvidence):
                raise TypeError("diagnostic_evidence")
            if self.diagnostic_evidence.full_cell_geometry.semantic_geometry_id != self.full_cell_geometry.semantic_geometry_id:
                raise ValueError("membership diagnostic full-cell mismatch")
            if self.diagnostic_evidence.boundary_artifact.geometry_artifact_id != self.boundary_artifact.geometry_artifact_id:
                raise ValueError("membership diagnostic boundary mismatch")
        exp_state, exp_reasons = _membership(self.membership_policy, self.diagnostic_evidence)
        if self.state is not exp_state or self.reason_codes != exp_reasons:
            raise ValueError("membership state/reasons disagree with policy/evidence")

    @property
    def identity_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "full_cell_geometry_id": self.full_cell_geometry.semantic_geometry_id,
            "boundary_artifact_id": self.boundary_artifact.geometry_artifact_id,
            "membership_policy_id": self.membership_policy.identity_id,
            "diagnostic_evidence_id": self.diagnostic_evidence.identity_id if self.diagnostic_evidence else None,
            "state": self.state.value,
            "reason_codes": self.reason_codes,
        }


def _membership(policy, diag):
    if policy.state is ResolutionState.UNRESOLVED:
        return BoundaryMembershipState.UNRESOLVED, ("boundary_membership_policy_unresolved",)
    return BoundaryMembershipState.UNRESOLVED, ("boundary_membership_method_not_implemented",)


@dataclass(frozen=True, slots=True)
class CommercialFrameCell:
    lattice_cell: LatticeCellArtifact
    boundary_membership: FrameBoundaryMembership
    evidence_bundle: CommercialFrameEvidenceBundle
    eligibility: CommercialEligibilityResult
    source_refs: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.lattice_cell, LatticeCellArtifact):
            raise TypeError("lattice_cell")
        if not isinstance(self.boundary_membership, FrameBoundaryMembership):
            raise TypeError("boundary_membership")
        if not isinstance(self.evidence_bundle, CommercialFrameEvidenceBundle):
            raise TypeError("evidence_bundle")
        if not isinstance(self.eligibility, CommercialEligibilityResult):
            raise TypeError("eligibility")
        if self.boundary_membership.full_cell_geometry.semantic_geometry_id != self.full_cell_geometry.semantic_geometry_id:
            raise ValueError("membership/full-cell mismatch")
        if self.evidence_bundle.cell_lattice_id != self.lattice_cell_id:
            raise ValueError("evidence bundle cell mismatch")
        if self.eligibility.evidence_bundle.bundle_id != self.evidence_bundle.bundle_id:
            raise ValueError("eligibility bundle mismatch")
        if tuple(self.source_refs) != tuple(sorted(set(self.source_refs))):
            raise ValueError("source_refs must be canonical-sorted unique")

    @property
    def lattice_policy(self):
        return self.lattice_cell.lattice_policy

    @property
    def lattice_cell_id(self):
        return self.lattice_cell.lattice_cell_id

    @property
    def lattice_index(self):
        return self.lattice_cell.lattice_index

    @property
    def full_cell_geometry(self):
        return self.lattice_cell.full_cell_geometry

    @property
    def full_cell_area(self):
        return self.lattice_cell.full_cell_area

    @property
    def area_unit(self):
        return self.lattice_cell.area_unit

    @property
    def cell_id(self):
        return semantic_hash(self.semantic_record())

    def semantic_record(self):
        return {
            "lattice_cell_id": self.lattice_cell_id,
            "boundary_membership_id": self.boundary_membership.identity_id,
            "evidence_bundle_id": self.evidence_bundle.bundle_id,
            "eligibility_id": self.eligibility.identity_id,
            "source_refs": self.source_refs,
        }


@dataclass(frozen=True, slots=True)
class CommercialFrame:
    benchmark_geography: GeographyIdentity
    boundary_artifact: BoundaryGeometryArtifact
    lattice_policy: LatticePolicy
    membership_policy: FrameBoundaryMembershipPolicy
    eligibility_policy: CommercialEligibilityPolicy
    cells: tuple[CommercialFrameCell, ...]
    state: FrameState
    reason_codes: tuple[str, ...]
    generated_at: datetime | None = field(default=None, compare=False)
    frame_population_definition: str = POPULATION_DEFINITION
    frame_population_version: str = POPULATION_VERSION

    def __post_init__(self):
        if not isinstance(self.benchmark_geography, GeographyIdentity):
            raise TypeError("benchmark_geography")
        if not isinstance(self.boundary_artifact, BoundaryGeometryArtifact):
            raise TypeError("boundary_artifact")
        if self.boundary_artifact.geography_identity.identity_id != self.benchmark_geography.identity_id:
            raise ValueError("frame benchmark geography/boundary artifact mismatch")
        if not isinstance(self.lattice_policy, LatticePolicy):
            raise TypeError("lattice_policy")
        if not isinstance(self.membership_policy, FrameBoundaryMembershipPolicy):
            raise TypeError("membership_policy")
        if not isinstance(self.eligibility_policy, CommercialEligibilityPolicy):
            raise TypeError("eligibility_policy")
        text(self.frame_population_definition, "frame_population_definition")
        text(self.frame_population_version, "frame_population_version")
        if self.frame_population_definition != POPULATION_DEFINITION:
            raise ValueError("frame population definition is frozen")
        ids = tuple(c.cell_id for c in self.cells)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("cells must be unique and canonical-sorted")
        for c in self.cells:
            if not isinstance(c, CommercialFrameCell):
                raise TypeError("cells require CommercialFrameCell")
            if c.lattice_policy.identity_id != self.lattice_policy.identity_id:
                raise ValueError("cell lattice mismatch")
            if c.boundary_membership.membership_policy.identity_id != self.membership_policy.identity_id:
                raise ValueError("cell membership policy mismatch")
            if c.boundary_membership.boundary_artifact.geometry_artifact_id != self.boundary_artifact.geometry_artifact_id:
                raise ValueError("cell membership boundary artifact mismatch")
            if c.boundary_membership.full_cell_geometry.semantic_geometry_id != c.full_cell_geometry.semantic_geometry_id:
                raise ValueError("cell membership/full-cell mismatch")
            if c.eligibility.eligibility_policy.identity_id != self.eligibility_policy.identity_id:
                raise ValueError("cell eligibility policy mismatch")
        exp_state, exp_reasons = _frame_state(self)
        if self.state is not exp_state or self.reason_codes != exp_reasons:
            raise ValueError("frame state/reasons disagree with actual policies/cells")

    @property
    def frame_id(self):
        return semantic_hash(self.semantic_record())

    @property
    def eligible_cell_ids(self):
        return tuple(
            c.cell_id
            for c in self.cells
            if c.eligibility.state is EligibilityState.ELIGIBLE
            and c.boundary_membership.state is BoundaryMembershipState.MEMBER
        )

    def semantic_record(self):
        return {
            "benchmark_geography_id": self.benchmark_geography.identity_id,
            "boundary_artifact_id": self.boundary_artifact.geometry_artifact_id,
            "lattice_policy_id": self.lattice_policy.identity_id,
            "membership_policy_id": self.membership_policy.identity_id,
            "eligibility_policy_id": self.eligibility_policy.identity_id,
            "cell_ids": [c.cell_id for c in self.cells],
            "state": self.state.value,
            "reason_codes": self.reason_codes,
            "frame_population_definition": self.frame_population_definition,
            "frame_population_version": self.frame_population_version,
        }


def _frame_state(frame):
    reasons = []
    if not frame.lattice_policy.is_resolved:
        reasons.append("lattice_policy_unresolved")
    if frame.membership_policy.state is ResolutionState.UNRESOLVED:
        reasons.append("boundary_membership_policy_unresolved")
    if any(c.boundary_membership.state is BoundaryMembershipState.UNRESOLVED for c in frame.cells):
        reasons.append("cell_membership_unresolved")
    if reasons:
        return FrameState.UNRESOLVED, tuple(sorted(set(reasons)))
    return FrameState.STRUCTURAL_ONLY, ("production_membership_semantics_not_approved",)
