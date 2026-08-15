from enum import StrEnum

class SubjectKind(StrEnum):
    SITE = "site"
    BENCHMARK_CELL = "benchmark_cell"

class MeasurementPrecisionMode(StrEnum):
    FULL_BINARY64 = "full_binary64"

class MetricImplementationStatus(StrEnum):
    IMPLEMENTED_CANONICAL = "implemented_canonical"
    STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED = "structurally_supported_but_policy_unresolved"
    PASS_THROUGH_PROVIDER_DERIVED = "pass_through_provider_derived"
    DEFERRED = "deferred"

class DerivationStrategy(StrEnum):
    PASS_THROUGH_PROVIDER_DERIVED = "pass_through_provider_derived"
    UNRESOLVED_ALLOCATION = "unresolved_allocation"
    UNRESOLVED_TARGET_DEFINITION = "unresolved_target_definition"
    UNRESOLVED_DENOMINATOR = "unresolved_denominator"
    UNRESOLVED_REDUCTION = "unresolved_reduction"
