from __future__ import annotations

from dataclasses import dataclass

from sitescore_metrics import (
    DEFINITIONS,
    POLICIES,
    DerivedMetricMeasurement,
    MeasurementSubject,
    MetricDefinition,
    MetricDerivationPolicy,
    MetricEvidence,
    SubjectKind,
)

from .contracts import CommercialFrame, CommercialFrameCell
from .hashing import semantic_hash
from .validation import text

BENCHMARK_SUBJECT_CONTRACT = "sitescore_benchmarks.commercial_frame_cell"
BENCHMARK_SUBJECT_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class BenchmarkSubjectAdapterPolicy:
    policy_id: str = "commercial-frame-cell-subject-adapter"
    policy_version: str = "1.0"
    subject_contract: str = BENCHMARK_SUBJECT_CONTRACT
    subject_contract_version: str = BENCHMARK_SUBJECT_CONTRACT_VERSION
    evidence_scope_algorithm: str = "ACTUAL_METRIC_EVIDENCE_SCOPE_V1"

    def __post_init__(self) -> None:
        for name in (
            "policy_id", "policy_version", "subject_contract",
            "subject_contract_version", "evidence_scope_algorithm",
        ):
            text(getattr(self, name), name)
        if (self.policy_id, self.policy_version) != (
            "commercial-frame-cell-subject-adapter", "1.0"
        ):
            raise ValueError("unsupported benchmark subject-adapter policy")
        if (self.subject_contract, self.subject_contract_version) != (
            BENCHMARK_SUBJECT_CONTRACT, BENCHMARK_SUBJECT_CONTRACT_VERSION
        ):
            raise ValueError("benchmark subject contract is frozen for V1")
        if self.evidence_scope_algorithm != "ACTUAL_METRIC_EVIDENCE_SCOPE_V1":
            raise ValueError("unsupported benchmark evidence-scope algorithm")

    @property
    def identity_id(self) -> str:
        return semantic_hash(self.semantic_record())

    def semantic_record(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "subject_contract": self.subject_contract,
            "subject_contract_version": self.subject_contract_version,
            "evidence_scope_algorithm": self.evidence_scope_algorithm,
        }


BENCHMARK_SUBJECT_ADAPTER_V1 = BenchmarkSubjectAdapterPolicy()


@dataclass(frozen=True, slots=True)
class BenchmarkMeasurementDistributionPolicy:
    policy_id: str = "benchmark-measurement-distribution"
    policy_version: str = "1.0"
    subject_adapter_policy: BenchmarkSubjectAdapterPolicy = BENCHMARK_SUBJECT_ADAPTER_V1
    completeness_rule: str = "EXACTLY_ONE_ATTEMPT_PER_ELIGIBLE_FRAME_CELL"
    numeric_inclusion_rule: str = "AVAILABLE_SCORE_ELIGIBLE_CALIBRATED_FINITE_VALUE"
    compatibility_rule: str = "EXACT_METHOD_AND_SOURCE_BUNDLE_COMPATIBILITY"

    def __post_init__(self) -> None:
        text(self.policy_id, "policy_id")
        text(self.policy_version, "policy_version")
        if not isinstance(self.subject_adapter_policy, BenchmarkSubjectAdapterPolicy):
            raise TypeError("subject_adapter_policy must be BenchmarkSubjectAdapterPolicy")
        if self.subject_adapter_policy.identity_id != BENCHMARK_SUBJECT_ADAPTER_V1.identity_id:
            raise ValueError("unsupported benchmark subject-adapter semantics")
        if (self.policy_id, self.policy_version) != (
            "benchmark-measurement-distribution", "1.0"
        ):
            raise ValueError("unsupported benchmark measurement/distribution policy")
        if self.completeness_rule != "EXACTLY_ONE_ATTEMPT_PER_ELIGIBLE_FRAME_CELL":
            raise ValueError("benchmark completeness rule is frozen for V1")
        if self.numeric_inclusion_rule != "AVAILABLE_SCORE_ELIGIBLE_CALIBRATED_FINITE_VALUE":
            raise ValueError("benchmark numeric-inclusion rule is frozen for V1")
        if self.compatibility_rule != "EXACT_METHOD_AND_SOURCE_BUNDLE_COMPATIBILITY":
            raise ValueError("benchmark compatibility rule is frozen for V1")

    @property
    def identity_id(self) -> str:
        return semantic_hash(self.semantic_record())

    def semantic_record(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "subject_adapter_policy_id": self.subject_adapter_policy.identity_id,
            "completeness_rule": self.completeness_rule,
            "numeric_inclusion_rule": self.numeric_inclusion_rule,
            "compatibility_rule": self.compatibility_rule,
        }


BENCHMARK_MEASUREMENT_DISTRIBUTION_V1 = BenchmarkMeasurementDistributionPolicy()


def validate_canonical_metric_pair(
    definition: MetricDefinition, policy: MetricDerivationPolicy
) -> None:
    if not isinstance(definition, MetricDefinition):
        raise TypeError("definition must be MetricDefinition")
    if not isinstance(policy, MetricDerivationPolicy):
        raise TypeError("derivation_policy must be MetricDerivationPolicy")
    key = definition.metric_key
    if key not in DEFINITIONS or key not in POLICIES:
        raise ValueError("benchmark metric is not in the canonical V1 registry")
    if definition.identity_id != DEFINITIONS[key].identity_id:
        raise ValueError("benchmark definition does not match canonical V1 metric definition")
    if policy.identity_id != POLICIES[key].identity_id:
        raise ValueError("benchmark derivation policy does not match canonical V1 metric policy")
    if policy.metric_key != key:
        raise ValueError("benchmark metric definition/policy key mismatch")


def assert_frame_cell_target(frame: CommercialFrame, cell: CommercialFrameCell) -> None:
    if not isinstance(frame, CommercialFrame):
        raise TypeError("frame must be CommercialFrame")
    if not isinstance(cell, CommercialFrameCell):
        raise TypeError("frame_cell must be CommercialFrameCell")
    if cell.cell_id not in tuple(c.cell_id for c in frame.cells):
        raise ValueError("benchmark frame cell is foreign to the supplied CommercialFrame")
    if cell.cell_id not in frame.eligible_cell_ids:
        raise ValueError("benchmark measurement attempts require a canonical ELIGIBLE frame cell")


def _evidence_scope_ref(metric_evidence: MetricEvidence) -> str:
    role = metric_evidence.evidence_role
    evidence = metric_evidence.evidence
    try:
        if role == "demographic_snapshot":
            return f"geography:{evidence.geography_ref.geography_id}"
        if role == "isochrone_snapshot":
            return f"catchment:{evidence.catchment_ref}"
        if role == "transit_snapshot":
            return f"transit:{evidence.snapshot_id}"
        if role == "parking_snapshot":
            return f"parking:{evidence.snapshot_id}"
        if role == "competition_snapshot":
            return f"competition:{evidence.snapshot_id}"
        if role == "road_snapshot":
            return f"road:{evidence.snapshot_id}"
    except AttributeError as exc:
        raise ValueError(f"{role} evidence lacks canonical scope") from exc
    raise ValueError("unsupported canonical metric evidence role for benchmark subject adaptation")


def adapt_benchmark_cell_subject(
    frame: CommercialFrame,
    frame_cell: CommercialFrameCell,
    *,
    inputs: tuple[MetricEvidence, ...],
    adapter_policy: BenchmarkSubjectAdapterPolicy = BENCHMARK_SUBJECT_ADAPTER_V1,
) -> MeasurementSubject:
    """Derive BENCHMARK_CELL semantics from actual frame/cell/evidence objects."""
    assert_frame_cell_target(frame, frame_cell)
    if not isinstance(adapter_policy, BenchmarkSubjectAdapterPolicy):
        raise TypeError("adapter_policy must be BenchmarkSubjectAdapterPolicy")
    if adapter_policy.identity_id != BENCHMARK_SUBJECT_ADAPTER_V1.identity_id:
        raise ValueError("unsupported benchmark subject-adapter semantics")
    if not isinstance(inputs, tuple) or not inputs:
        raise ValueError("benchmark subject adaptation requires actual metric evidence")
    if any(not isinstance(item, MetricEvidence) for item in inputs):
        raise TypeError("inputs must contain MetricEvidence")
    input_ids = tuple(item.identity_id for item in inputs)
    if len(input_ids) != len(set(input_ids)):
        raise ValueError("benchmark subject evidence must not contain duplicates")
    payload = (
        ("commercial_frame_cell_id", frame_cell.cell_id),
        ("commercial_frame_id", frame.frame_id),
        ("lattice_cell_id", frame_cell.lattice_cell_id),
    )
    scope_refs = {
        f"benchmark_cell:{frame_cell.cell_id}",
        f"benchmark_frame:{frame.frame_id}",
        *(_evidence_scope_ref(item) for item in inputs),
    }
    return MeasurementSubject(
        SubjectKind.BENCHMARK_CELL,
        adapter_policy.subject_contract,
        adapter_policy.subject_contract_version,
        payload,
        tuple(sorted(scope_refs)),
    )


@dataclass(frozen=True, slots=True)
class BenchmarkCellMeasurement:
    frame: CommercialFrame
    frame_cell: CommercialFrameCell
    measurement: DerivedMetricMeasurement
    measurement_policy: BenchmarkMeasurementDistributionPolicy = BENCHMARK_MEASUREMENT_DISTRIBUTION_V1

    def __post_init__(self) -> None:
        assert_frame_cell_target(self.frame, self.frame_cell)
        if not isinstance(self.measurement, DerivedMetricMeasurement):
            raise TypeError("measurement must be DerivedMetricMeasurement")
        if not isinstance(self.measurement_policy, BenchmarkMeasurementDistributionPolicy):
            raise TypeError("measurement_policy must be BenchmarkMeasurementDistributionPolicy")
        if self.measurement_policy.identity_id != BENCHMARK_MEASUREMENT_DISTRIBUTION_V1.identity_id:
            raise ValueError("unsupported benchmark measurement/distribution semantics")
        validate_canonical_metric_pair(self.measurement.definition, self.measurement.policy)
        expected_subject = adapt_benchmark_cell_subject(
            self.frame,
            self.frame_cell,
            inputs=self.measurement.inputs,
            adapter_policy=self.measurement_policy.subject_adapter_policy,
        )
        if self.measurement.subject.identity_id != expected_subject.identity_id:
            raise ValueError("measurement subject is detached from the actual benchmark frame/cell/evidence")
        if self.measurement.subject.kind is not SubjectKind.BENCHMARK_CELL:
            raise ValueError("benchmark-cell measurement requires BENCHMARK_CELL subject kind")

    @property
    def attempt_id(self) -> str:
        return semantic_hash({
            "frame_id": self.frame.frame_id,
            "frame_cell_id": self.frame_cell.cell_id,
            "lattice_cell_id": self.frame_cell.lattice_cell_id,
            "measurement_id": self.measurement.measurement_id,
            "measurement_policy_id": self.measurement_policy.identity_id,
        })

    @property
    def metric_key(self) -> str:
        return self.measurement.definition.metric_key


def build_benchmark_cell_measurement(
    frame: CommercialFrame,
    frame_cell: CommercialFrameCell,
    measurement: DerivedMetricMeasurement,
    *,
    measurement_policy: BenchmarkMeasurementDistributionPolicy = BENCHMARK_MEASUREMENT_DISTRIBUTION_V1,
) -> BenchmarkCellMeasurement:
    return BenchmarkCellMeasurement(frame, frame_cell, measurement, measurement_policy)


@dataclass(frozen=True, slots=True)
class BenchmarkMetricCompatibility:
    """Comparability dimensions derived from one actual canonical measurement."""
    measurement: DerivedMetricMeasurement

    def __post_init__(self) -> None:
        if not isinstance(self.measurement, DerivedMetricMeasurement):
            raise TypeError("measurement must be DerivedMetricMeasurement")
        validate_canonical_metric_pair(self.measurement.definition, self.measurement.policy)

    @property
    def definition(self):
        return self.measurement.definition

    @property
    def derivation_policy(self):
        return self.measurement.policy

    @property
    def precision_policy(self):
        return self.measurement.precision_policy

    @property
    def unit(self) -> str:
        return self.measurement.metric_value.unit

    @property
    def method_version(self) -> str:
        return self.measurement.method_version

    @property
    def source_bundle_compatibility(self) -> tuple[tuple[str, str], ...]:
        return self.measurement.source_bundle_compatibility

    @property
    def identity_id(self) -> str:
        return semantic_hash({
            "metric_definition_id": self.definition.identity_id,
            "metric_derivation_policy_id": self.derivation_policy.identity_id,
            "measurement_precision_policy_id": self.precision_policy.identity_id,
            "unit": self.unit,
            "method_version": self.method_version,
            "source_bundle_compatibility": self.source_bundle_compatibility,
        })
