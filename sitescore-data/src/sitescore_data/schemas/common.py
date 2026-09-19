"""Common immutable data-contract schemas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    PersistenceClass,
    ScoreEligibility,
)
from sitescore_data.validation import (
    require_aware_datetime,
    require_canonical_identifier,
    require_finite_number,
)
from sitescore_data.version import (
    BENCHMARK_SCHEMA_VERSION,
    DATA_FEATURE_CONTRACT_VERSION,
    DATA_SCHEMA_VERSION,
    DATA_SERIALIZATION_VERSION,
    PACKAGE_VERSION,
    READINESS_CONTRACT_VERSION,
)


def _require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    return value


def _require_optional_nonempty_text(
    value: str | None, *, field_name: str
) -> str | None:
    if value is None:
        return None
    return _require_nonempty_text(value, field_name=field_name)


def _require_bool(value: bool, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")
    return value


def _require_unique_canonical_identifiers(
    values: tuple[str, ...], *, field_name: str
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for value in values:
        require_canonical_identifier(value, field_name=f"{field_name} item")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Provider-neutral metadata for one known source identity.

    Package-wide ``source_ref`` / ``source_refs`` values are opaque provenance
    identities and are not guaranteed to resolve to ``SourceMetadata.source_id``.
    This registry is therefore intentionally non-universal.
    """

    source_id: str
    provider: str
    dataset: str
    dataset_release: str | None
    vintage: str | None
    schema_version: str | None
    retrieved_at: datetime
    content_hash: str
    persistence_class: PersistenceClass
    data_quality: DataQualityState
    license_class: str | None = None
    attribution_required: bool = False
    source_reference: str | None = None

    def __post_init__(self) -> None:
        require_canonical_identifier(self.source_id, field_name="source_id")
        _require_nonempty_text(self.provider, field_name="provider")
        _require_nonempty_text(self.dataset, field_name="dataset")
        _require_optional_nonempty_text(
            self.dataset_release, field_name="dataset_release"
        )
        _require_optional_nonempty_text(self.vintage, field_name="vintage")
        _require_optional_nonempty_text(
            self.schema_version, field_name="schema_version"
        )
        require_aware_datetime(self.retrieved_at, field_name="retrieved_at")
        _require_nonempty_text(self.content_hash, field_name="content_hash")
        if not isinstance(self.persistence_class, PersistenceClass):
            raise TypeError("persistence_class must be a PersistenceClass")
        if not isinstance(self.data_quality, DataQualityState):
            raise TypeError("data_quality must be a DataQualityState")
        _require_optional_nonempty_text(self.license_class, field_name="license_class")
        _require_bool(self.attribution_required, field_name="attribution_required")
        _require_optional_nonempty_text(
            self.source_reference, field_name="source_reference"
        )


@dataclass(frozen=True, slots=True)
class DataContractVersions:
    """Version identity for SiteScore data-layer contracts only."""

    package_version: str
    data_schema_version: str
    benchmark_schema_version: str
    data_feature_contract_version: str
    readiness_contract_version: str
    data_serialization_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "package_version",
            "data_schema_version",
            "benchmark_schema_version",
            "data_feature_contract_version",
            "readiness_contract_version",
            "data_serialization_version",
        ):
            _require_nonempty_text(getattr(self, field_name), field_name=field_name)

    @classmethod
    def current(cls) -> "DataContractVersions":
        """Return the deterministic contract versions shipped by this package."""

        return cls(
            package_version=PACKAGE_VERSION,
            data_schema_version=DATA_SCHEMA_VERSION,
            benchmark_schema_version=BENCHMARK_SCHEMA_VERSION,
            data_feature_contract_version=DATA_FEATURE_CONTRACT_VERSION,
            readiness_contract_version=READINESS_CONTRACT_VERSION,
            data_serialization_version=DATA_SERIALIZATION_VERSION,
        )


@dataclass(frozen=True, slots=True)
class MetricValue:
    """State-aware canonical numeric metric.

    ``None`` is never a state.  A missing numeric value must be explained by the
    typed ``availability`` state, while quality, score eligibility, and
    calibration remain independent axes.
    """

    value: int | float | None
    unit: str
    availability: AvailabilityState
    data_quality: DataQualityState
    score_eligibility: ScoreEligibility
    calibration_state: CalibrationState
    is_estimate: bool
    is_proxy: bool
    source_refs: tuple[str, ...]
    method_version: str | None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_nonempty_text(self.unit, field_name="unit")
        if not isinstance(self.availability, AvailabilityState):
            raise TypeError("availability must be an AvailabilityState")
        if not isinstance(self.data_quality, DataQualityState):
            raise TypeError("data_quality must be a DataQualityState")
        if not isinstance(self.score_eligibility, ScoreEligibility):
            raise TypeError("score_eligibility must be a ScoreEligibility")
        if not isinstance(self.calibration_state, CalibrationState):
            raise TypeError("calibration_state must be a CalibrationState")
        _require_bool(self.is_estimate, field_name="is_estimate")
        _require_bool(self.is_proxy, field_name="is_proxy")
        _require_unique_canonical_identifiers(
            self.source_refs, field_name="source_refs"
        )
        _require_optional_nonempty_text(
            self.method_version, field_name="method_version"
        )
        _require_unique_canonical_identifiers(
            self.reason_codes, field_name="reason_codes"
        )

        if self.availability is AvailabilityState.NOT_APPLICABLE:
            if self.score_eligibility is not ScoreEligibility.NOT_APPLICABLE:
                raise ValueError(
                    "NOT_APPLICABLE metrics require NOT_APPLICABLE score eligibility"
                )
            if self.calibration_state is not CalibrationState.NOT_APPLICABLE:
                raise ValueError(
                    "NOT_APPLICABLE metrics require NOT_APPLICABLE calibration state"
                )

        if (
            self.availability is not AvailabilityState.AVAILABLE
            and self.score_eligibility is ScoreEligibility.ELIGIBLE
        ):
            raise ValueError(
                "non-AVAILABLE metrics cannot be score-eligible"
            )

        if self.availability is AvailabilityState.AVAILABLE:
            if self.value is None:
                raise ValueError("AVAILABLE metrics must have a numeric value")
            require_finite_number(self.value, field_name="value")
            if not self.source_refs:
                raise ValueError(
                    "AVAILABLE metrics require at least one source_ref"
                )
            if self.data_quality not in {
                DataQualityState.FULL,
                DataQualityState.DEGRADED,
            }:
                raise ValueError(
                    "AVAILABLE metrics require FULL or DEGRADED data quality"
                )
        else:
            if self.value is not None:
                raise ValueError(
                    f"{self.availability.value} metrics must have value=None"
                )
            allowed_quality = {
                AvailabilityState.MISSING: {DataQualityState.MISSING},
                AvailabilityState.UNAVAILABLE: {DataQualityState.MISSING},
                AvailabilityState.UNKNOWN: {
                    DataQualityState.DEGRADED,
                    DataQualityState.MISSING,
                },
                AvailabilityState.NOT_APPLICABLE: {
                    DataQualityState.NOT_APPLICABLE
                },
            }[self.availability]
            if self.data_quality not in allowed_quality:
                allowed = ", ".join(sorted(item.value for item in allowed_quality))
                raise ValueError(
                    f"{self.availability.value} metrics require data quality in: "
                    f"{allowed}"
                )
